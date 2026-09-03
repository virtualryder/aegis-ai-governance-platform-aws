#!/usr/bin/env bash
# Assemble the release packet for one version into release/<version>/ - the pinned, collected snapshot
# of exactly what CI runs (COPILOT-6, 2026-09-03: the previous packet doc named a script that did not
# exist and tools the workflows never ran). Every tool that is missing locally is recorded as SKIPPED
# in MANIFEST.md rather than silently omitted; CI (ci.yml + security.yml) is the authoritative run.
#
#   bash tools/build_release_packet.sh 0.2.0
set -uo pipefail
cd "$(dirname "$0")/.."
VER="${1:?version, e.g. 0.2.0}"
OUT="release/$VER"
mkdir -p "$OUT"
MAN="$OUT/MANIFEST.md"
{
  echo "# Release packet - aegis-platform-core $VER"
  echo
  echo "Commit \`$(git rev-parse HEAD)\` · tag \`$(git describe --tags --exact-match 2>/dev/null || echo '(untagged)')\` · assembled $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "AGP contract: 1.0 (AGP-CONFORMANCE.md). VERSION file: $(cat VERSION)."
  echo
  echo "| Artifact | Command | Result |"
  echo "|---|---|---|"
} > "$MAN"

run() {  # run <artifact> <outfile> <command...>
  local name="$1" out="$2"; shift 2
  if "$@" > "$OUT/$out" 2>&1; then echo "| $name | \`$*\` | PASS (\`$out\`) |" >> "$MAN"
  else echo "| $name | \`$*\` | **FAIL/SKIPPED** - see \`$out\` |" >> "$MAN"; fi
}
have() { command -v "$1" >/dev/null 2>&1; }

export PYTHONPATH="platform_core:."
run "Offline test suite (60)" test-report.txt python -m pytest demo platform_core/tests -q
run "Clean-account acceptance walk-through (19 steps, offline)" acceptance.txt python demo/clean_account_acceptance.py
run "Negative-security suite" negative-security.txt python demo/test_negative_security.py
run "Durable intent / outbox ordering" outbox.txt python -m pytest demo/test_outbox.py -q
run "MATURITY drift gate" maturity.txt python tools/check_maturity.py
run "Deployed authorizer == reviewed engine" authorizer.txt bash -c "cd infra/golden-pilot && bash prepare_layer.sh && python verify_authorizer_engine.py"
run "platform_core wheel (clean-venv install + import)" wheel.txt bash tools/check_wheel.sh "$OUT/dist"
if have bandit;   then run "Bandit SAST (vs .bandit-baseline.json)" bandit.txt bandit -r . --severity-level medium --confidence-level medium --skip B101 -x ./node_modules,./.git,./venv,./release -b .bandit-baseline.json -q; else echo "| Bandit SAST | bandit | SKIPPED (not installed; CI security.yml runs it) |" >> "$MAN"; fi
if have pip-audit; then run "pip-audit (hash-pinned lock)" pip-audit.txt pip-audit -r platform_core/requirements-lock.txt --require-hashes; else echo "| pip-audit | pip-audit | SKIPPED (not installed; CI security.yml runs it, BLOCKING) |" >> "$MAN"; fi
if have detect-secrets; then run "detect-secrets (vs .secrets.baseline)" secrets.txt detect-secrets scan --baseline .secrets.baseline; else echo "| detect-secrets | detect-secrets | SKIPPED (not installed; CI security.yml runs it, BLOCKING) |" >> "$MAN"; fi
if have cfn-lint;  then run "cfn-lint (CloudFormation + golden-pilot)" cfn-lint.txt cfn-lint infra/cloudformation/*.yaml infra/golden-pilot/*.yaml; else echo "| cfn-lint | cfn-lint | SKIPPED (not installed; CI ci.yml iac job runs it) |" >> "$MAN"; fi
if have checkov;   then run "Checkov (IaC, soft-fail in CI)" checkov.txt checkov -d infra --framework cloudformation --compact --soft-fail; else echo "| Checkov | checkov | SKIPPED (not installed; CI security.yml runs it, soft-fail) |" >> "$MAN"; fi
if have semgrep;   then run "Semgrep p/ci (report-only in CI)" semgrep.txt semgrep --config p/ci --quiet; else echo "| Semgrep | semgrep | SKIPPED (not installed; CI security.yml runs it, report-only) |" >> "$MAN"; fi
if have cyclonedx-py; then run "SBOM (CycloneDX)" sbom.json cyclonedx-py requirements platform_core/requirements-lock.txt; else echo "| SBOM (CycloneDX) | cyclonedx-py | SKIPPED (not installed; CI security.yml produces the sbom-cyclonedx artifact) |" >> "$MAN"; fi
cp DEPLOYED-AND-VALIDATED.md NOT-CLAIMS.md CHANGELOG.md AGP-CONFORMANCE.md MATURITY.yaml "$OUT/" 2>/dev/null || true
cp -r evidence "$OUT/evidence" 2>/dev/null || true
{
  echo
  echo "Live-deploy evidence (deployed -> exercised over HTTPS -> torn down): \`DEPLOYED-AND-VALIDATED.md\` Runs 1-13 and"
  echo "the GitHub Actions \`golden-pilot-deploy-evidence\` run linked there (reproducible, OIDC, tag-scoped)."
  echo "Known limitations: \`NOT-CLAIMS.md\`. Upgrade notes: \`CHANGELOG.md\`."
} >> "$MAN"
echo "release packet: $OUT (see $MAN)"
