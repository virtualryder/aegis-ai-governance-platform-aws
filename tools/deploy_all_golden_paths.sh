#!/usr/bin/env bash
#
# deploy_all_golden_paths.sh
# -----------------------------------------------------------------------------
# Portfolio deploy driver for the 5-repo AI-agent portfolio that lives side by
# side under a common review root (default: the parent directory of the repo
# that contains this script, i.e. /root/review).
#
# For each discovered "golden path" (a directory that ships an infra
# template.yaml plus the standard deploy.sh / smoke_test.sh / destroy.sh
# lifecycle scripts) it runs the canonical lifecycle:
#
#       ./deploy.sh   (or: sam build && sam deploy)      -- stand it up
#         -> ./acceptance_test.sh  (or ./smoke_test.sh)  -- prove it works
#           -> ./destroy.sh                              -- always tear it down
#
# SAFETY MODEL
# ------------
#   * DRY-RUN IS THE DEFAULT. With no flags the script performs ZERO AWS calls.
#     It only prints what it WOULD deploy and runs `cfn-lint` on every template
#     it finds, so it is safe to run anywhere (no credentials, no cost).
#   * A real deploy requires the explicit --execute flag. Without --execute the
#     script will never invoke sam / aws / deploy.sh / destroy.sh.
#   * Teardown is guaranteed: once a path's deploy is attempted, an EXIT trap
#     runs destroy.sh even if the smoke/acceptance test fails or the script is
#     interrupted (Ctrl-C). This prevents orphaned, billable stacks.
#
# The script is idempotent: re-running it re-lints (dry-run) or re-deploys via
# the underlying idempotent `sam deploy` (CloudFormation change sets), and
# always finishes by destroying what it created in that run.
#
# USAGE
# -----
#   ./deploy_all_golden_paths.sh [options]
#
#   --execute            Perform REAL deploys/tests/teardown against AWS.
#                        Omit this (the default) for a safe dry-run + lint.
#   --region <region>    AWS region to target (default: $AWS_REGION or us-east-1).
#   --only <glob>        Only process paths whose label (repo/path-name) matches
#                        the shell glob, e.g. --only 'slg-ai-agents/*' or
#                        --only '*311*'. May be repeated implicitly via a broad
#                        glob. Default: '*' (all).
#   --root <dir>         Portfolio review root to scan (default: auto-detected
#                        parent of this repo, override with $REVIEW_ROOT).
#   --keep               (execute mode) Do NOT run destroy.sh after tests. Use
#                        with care -- leaves live stacks behind.
#   --list               Just list the discovered golden paths and exit.
#   -h | --help          Show this help and exit.
#
# EXIT STATUS
#   0  all selected paths succeeded (or dry-run lint was clean)
#   1  one or more paths failed (lint errors in dry-run, or deploy/test failure)
# -----------------------------------------------------------------------------

set -uo pipefail

# ---------------------------------------------------------------------------
# Resolve locations
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# tools/ -> repo root -> portfolio review root
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults / option parsing
# ---------------------------------------------------------------------------
EXECUTE=0
KEEP=0
LIST_ONLY=0
REGION="${AWS_REGION:-us-east-1}"
ONLY_GLOB='*'
REVIEW_ROOT="${REVIEW_ROOT:-$DEFAULT_ROOT}"

usage() { sed -n '2,55p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --execute) EXECUTE=1; shift ;;
    --region)  REGION="${2:?--region needs a value}"; shift 2 ;;
    --only)    ONLY_GLOB="${2:?--only needs a glob}"; shift 2 ;;
    --root)    REVIEW_ROOT="${2:?--root needs a dir}"; shift 2 ;;
    --keep)    KEEP=1; shift ;;
    --list)    LIST_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option '$1' (try --help)" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Pretty logging helpers
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  C_BOLD=$'\033[1m'; C_RED=$'\033[31m'; C_GRN=$'\033[32m'
  C_YEL=$'\033[33m'; C_CYA=$'\033[36m'; C_RST=$'\033[0m'
else
  C_BOLD=""; C_RED=""; C_GRN=""; C_YEL=""; C_CYA=""; C_RST=""
fi
log()  { printf '%s\n' "$*"; }
info() { printf '%s==>%s %s\n' "$C_CYA" "$C_RST" "$*"; }
warn() { printf '%s[warn]%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s[FAIL]%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
ok()   { printf '%s[ ok ]%s %s\n' "$C_GRN" "$C_RST" "$*"; }

# ---------------------------------------------------------------------------
# Tooling probes
# ---------------------------------------------------------------------------
HAVE_CFN_LINT=0
if command -v cfn-lint >/dev/null 2>&1; then HAVE_CFN_LINT=1; fi

# ---------------------------------------------------------------------------
# Discover golden paths.
# A golden path = any directory under <repo>/infra whose name matches
# 'golden-path*' or 'golden-pilot' AND that contains a template.yaml.
# We emit "label<TAB>absdir" where label is "<repo>/<path-dir-name>".
# ---------------------------------------------------------------------------
discover_paths() {
  # Portable: find candidate dirs, then filter to those with a template.yaml.
  find "$REVIEW_ROOT" \
        -type d \( -name 'golden-path*' -o -name 'golden-pilot' \) \
        2>/dev/null | sort | while read -r d; do
    [ -f "$d/template.yaml" ] || continue          # must ship a deployable stack
    repo="${d#$REVIEW_ROOT/}"; repo="${repo%%/*}"   # first path component = repo
    label="${repo}/$(basename "$d")"
    printf '%s\t%s\n' "$label" "$d"
  done
}

# Collect selected paths (respecting --only) into parallel arrays.
LABELS=(); DIRS=()
while IFS=$'\t' read -r label dir; do
  [ -z "$label" ] && continue
  # shellcheck disable=SC2053  -- intentional glob match
  case "$label" in
    $ONLY_GLOB) LABELS+=("$label"); DIRS+=("$dir") ;;
    *) : ;;
  esac
done < <(discover_paths)

if [ "${#LABELS[@]}" -eq 0 ]; then
  err "No golden paths matched --only '$ONLY_GLOB' under $REVIEW_ROOT"
  exit 1
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
log "${C_BOLD}Portfolio golden-path deploy driver${C_RST}"
log "  review root : $REVIEW_ROOT"
log "  region      : $REGION"
log "  filter      : --only '$ONLY_GLOB'  (${#LABELS[@]} path(s) matched)"
if [ "$EXECUTE" -eq 1 ]; then
  log "  mode        : ${C_RED}${C_BOLD}EXECUTE (real AWS calls)${C_RST}"
else
  log "  mode        : ${C_GRN}DRY-RUN (lint only, no AWS calls)${C_RST}"
fi
log "  cfn-lint    : $( [ "$HAVE_CFN_LINT" -eq 1 ] && echo present || echo 'MISSING (dry-run lint skipped)')"
log ""

if [ "$LIST_ONLY" -eq 1 ]; then
  info "Discovered golden paths:"
  for i in "${!LABELS[@]}"; do log "  - ${LABELS[$i]}  (${DIRS[$i]})"; done
  exit 0
fi

# ---------------------------------------------------------------------------
# Per-path processing
# ---------------------------------------------------------------------------
RESULT_LABELS=(); RESULT_STATUS=(); RESULT_SECS=(); RESULT_NOTE=()
OVERALL_RC=0

# lint_dir <dir>: run cfn-lint on every CFN template in the dir. Sets LINT_RC.
lint_dir() {
  local dir="$1" rc=0 f
  LINT_RC=0
  if [ "$HAVE_CFN_LINT" -ne 1 ]; then
    warn "cfn-lint not installed; skipping static validation for $dir"
    return 0
  fi
  # Lint every *.yaml/*.yml that looks like a CloudFormation/SAM template.
  while IFS= read -r f; do
    grep -lqE 'AWSTemplateFormatVersion|Transform:.*Serverless|Type: *AWS::' "$f" 2>/dev/null || continue
    log "    cfn-lint $(basename "$f")"
    if ! cfn-lint "$f"; then rc=1; fi
  done < <(find "$dir" -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) | sort)
  LINT_RC=$rc
  return 0
}

# Deploy-mode teardown trap target (set per path just before deploy).
CUR_DIR=""; CUR_LABEL=""; TEARDOWN_ARMED=0
teardown() {
  # Called on normal completion of a path AND from the EXIT/INT trap.
  [ "$TEARDOWN_ARMED" -eq 1 ] || return 0
  TEARDOWN_ARMED=0
  if [ "$KEEP" -eq 1 ]; then
    warn "--keep set: leaving stack for '$CUR_LABEL' up (manual teardown required)"
    return 0
  fi
  info "teardown '$CUR_LABEL' (always runs, even after failure)"
  if [ -x "$CUR_DIR/destroy.sh" ] || [ -f "$CUR_DIR/destroy.sh" ]; then
    ( cd "$CUR_DIR" && AWS_REGION="$REGION" bash destroy.sh ) \
      && ok "destroyed '$CUR_LABEL'" \
      || err "destroy.sh FAILED for '$CUR_LABEL' -- CHECK FOR ORPHANED STACK"
  else
    warn "no destroy.sh in $CUR_DIR; attempting best-effort 'sam delete'"
    ( cd "$CUR_DIR" && AWS_REGION="$REGION" sam delete --no-prompts --region "$REGION" ) \
      || warn "sam delete not run/failed for '$CUR_LABEL'"
  fi
}
# On interrupt or unexpected exit while a deploy is armed, still tear down.
trap 'teardown' INT TERM
trap 'teardown' EXIT

process_path() {
  local label="$1" dir="$2"
  local start=$SECONDS status note secs

  log "${C_BOLD}----------------------------------------------------------------${C_RST}"
  info "path: ${C_BOLD}${label}${C_RST}"
  log  "      dir: $dir"

  # ---- DRY-RUN: describe + lint only, never touch AWS --------------------
  if [ "$EXECUTE" -ne 1 ]; then
    log "    would run: deploy.sh -> $( [ -f "$dir/acceptance_test.sh" ] && echo acceptance_test.sh || echo smoke_test.sh ) -> destroy.sh"
    log "    templates present:"
    find "$dir" -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) -printf '      - %f\n' | sort
    lint_dir "$dir"
    if [ "${LINT_RC:-0}" -eq 0 ]; then
      status="LINT-OK"; note="dry-run"
    else
      status="LINT-ERR"; note="cfn-lint errors"; OVERALL_RC=1
    fi
    secs=$(( SECONDS - start ))
    RESULT_LABELS+=("$label"); RESULT_STATUS+=("$status")
    RESULT_SECS+=("$secs"); RESULT_NOTE+=("$note")
    [ "$status" = "LINT-OK" ] && ok "$label lint clean (${secs}s)" || err "$label lint errors (${secs}s)"
    return 0
  fi

  # ---- EXECUTE: real lifecycle with guaranteed teardown ------------------
  CUR_DIR="$dir"; CUR_LABEL="$label"

  # 1) deploy
  info "deploy '$label'"
  TEARDOWN_ARMED=1   # arm teardown as soon as we START a deploy
  local deploy_rc=0
  if [ -f "$dir/deploy.sh" ]; then
    ( cd "$dir" && AWS_REGION="$REGION" bash deploy.sh ) || deploy_rc=$?
  else
    ( cd "$dir" && AWS_REGION="$REGION" sam build \
        && AWS_REGION="$REGION" sam deploy --region "$REGION" \
             --capabilities CAPABILITY_IAM --resolve-s3 --no-confirm-changeset ) || deploy_rc=$?
  fi

  local test_rc=0
  if [ "$deploy_rc" -ne 0 ]; then
    err "deploy FAILED for '$label' (rc=$deploy_rc)"
    status="DEPLOY-ERR"; note="deploy rc=$deploy_rc"
  else
    ok "deployed '$label'"
    # 2) acceptance test preferred, else smoke test
    local test_script=""
    if   [ -f "$dir/acceptance_test.sh" ]; then test_script=acceptance_test.sh
    elif [ -f "$dir/smoke_test.sh" ];      then test_script=smoke_test.sh; fi
    if [ -n "$test_script" ]; then
      info "test '$label' via $test_script"
      ( cd "$dir" && AWS_REGION="$REGION" bash "$test_script" ) || test_rc=$?
    else
      warn "no acceptance/smoke test in $dir"
    fi
    if [ "$test_rc" -eq 0 ]; then
      ok "tests passed '$label'"; status="OK"; note="deploy+test"
    else
      err "tests FAILED for '$label' (rc=$test_rc)"; status="TEST-ERR"; note="test rc=$test_rc"
    fi
  fi

  # 3) teardown ALWAYS (even if deploy/test failed above)
  teardown

  [ "$status" = "OK" ] || OVERALL_RC=1
  secs=$(( SECONDS - start ))
  RESULT_LABELS+=("$label"); RESULT_STATUS+=("$status")
  RESULT_SECS+=("$secs"); RESULT_NOTE+=("$note")
}

for i in "${!LABELS[@]}"; do
  process_path "${LABELS[$i]}" "${DIRS[$i]}"
done

# Disarm the EXIT trap's teardown (all paths already torn down individually).
TEARDOWN_ARMED=0

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
log ""
log "${C_BOLD}================ SUMMARY ================${C_RST}"
printf '%-48s %-11s %6s  %s\n' "PATH" "STATUS" "TIME" "NOTE"
for i in "${!RESULT_LABELS[@]}"; do
  st="${RESULT_STATUS[$i]}"
  color="$C_GRN"
  case "$st" in *ERR*) color="$C_RED" ;; LINT-OK|OK) color="$C_GRN" ;; *) color="$C_YEL" ;; esac
  printf '%-48s %s%-11s%s %5ss  %s\n' \
    "${RESULT_LABELS[$i]}" "$color" "$st" "$C_RST" "${RESULT_SECS[$i]}" "${RESULT_NOTE[$i]}"
done
log "${C_BOLD}========================================${C_RST}"
if [ "$OVERALL_RC" -eq 0 ]; then
  ok "All ${#RESULT_LABELS[@]} path(s) succeeded."
else
  err "One or more paths failed. See summary above."
fi
exit "$OVERALL_RC"
