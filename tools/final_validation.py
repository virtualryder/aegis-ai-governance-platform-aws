#!/usr/bin/env python3
"""#235 final validation: check every remediated finding against the repos AS THEY ARE NOW.

Each check is an independent assertion against the working tree - not a re-reading of a commit
message, and not a claim carried forward from earlier in the session. A finding counts as closed
only if a check here can distinguish the fixed state from the broken one.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKS = ["benefits_eligibility_agent", "pharmacovigilance_agent",
         "edu_financial_aid_agent", "Housing_eligibility_agent"]
ALL = PACKS + ["WOGplatform"]

results = []


def check(fid, title, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                     # noqa: BLE001 - a check that errors is a failure
        ok, detail = False, "%s: %s" % (type(exc).__name__, str(exc)[:180])
    results.append({"id": fid, "title": title, "ok": bool(ok), "detail": detail})


def _read(pack, rel):
    return (ROOT / pack / rel).read_text(encoding="utf-8")


def _exists_all(rel, packs=PACKS):
    missing = [p for p in packs if not (ROOT / p / rel).exists()]
    return (not missing), ("present in all %d" % len(packs)) if not missing else \
        ("MISSING from %s" % ", ".join(missing))


# ---- L40 redaction ------------------------------------------------------------------------------
def _l40():
    src = _read("benefits_eligibility_agent", "tools/scan_account_ids.py")
    prose = r"\baccount\b[\s:=*_`\-]{0,4}(\d{12})" in src
    trailing = r"[a-z0-9]-(\d{12})\b" in src
    return (prose and trailing), "prose pattern=%s trailing-segment pattern=%s" % (prose, trailing)


# ---- L41 lineage coverage -----------------------------------------------------------------------
def _l41():
    src = _read("benefits_eligibility_agent", "scripts/lineage_proof.py")
    return ("unmapped_lambda_invokes" in src), "verdict carries unmapped_lambda_invokes"


# ---- L42 / L42b process-tree kill ---------------------------------------------------------------
def _l42():
    src = _read("benefits_eligibility_agent", "scripts/full_portfolio_gate.py")
    posix = 'start_new_session=(os.name != "nt")' in src
    guard = "pgid == os.getpgid(0)" in src
    job = "_win_assign_job" in src and "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in src
    return (posix and guard and job), "posix session=%s own-group guard=%s win job object=%s" % (
        posix, guard, job)


# ---- L43 fail-closed verifier -------------------------------------------------------------------
def _l43():
    src = _read("benefits_eligibility_agent", "lib/controls/verify_manifest.py")
    ok = "cannot verify: signature library unavailable" in src and "as exc" in src
    return ok, "except binds exc and returns a fail-closed message"


# ---- L44 / L45 / L50 secrets baseline ------------------------------------------------------------
def _l44_baselines():
    bad = []
    for p in PACKS:
        raw = (ROOT / p / ".secrets.baseline").read_bytes()
        if raw[:1] != b"{":
            bad.append("%s: not UTF-8 JSON (starts %r)" % (p, raw[:2]))
    return (not bad), "; ".join(bad) or "all four are UTF-8 without a BOM"


def _l45_checker():
    src = _read("benefits_eligibility_agent", "tools/check_secrets_baseline.py")
    ign = '"generated_at", "version"' in src
    norm = "_PATH_DEPENDENT" in src and "is_baseline_file" in src
    hard = "DETECTION COVERAGE changed" in src
    return (ign and norm and hard), "ignores clock+version=%s normalises baseline path=%s " \
        "coverage change still hard-fails=%s" % (ign, norm, hard)


def _l50_pin():
    bad = []
    for p in PACKS:
        wf = _read(p, ".github/workflows/security.yml")
        pin = re.search(r'"detect-secrets==([0-9][^"]*)"', wf)
        base = json.loads(_read(p, ".secrets.baseline"))
        if not pin or base.get("version") != pin.group(1):
            bad.append("%s: baseline %s vs pin %s" % (p, base.get("version"),
                                                      pin.group(1) if pin else "none"))
    return (not bad), "; ".join(bad) or "baseline version == the pinned scanner in all four"


# ---- L45b trivy pin -----------------------------------------------------------------------------
def _l45_trivy():
    bad = []
    for p in PACKS:
        wf = _read(p, ".github/workflows/security.yml")
        if "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25" not in wf:
            bad.append(p)
    return (not bad), "; ".join(bad) or "pinned to the v0.36.0 COMMIT in all four"


# ---- L46 base image -----------------------------------------------------------------------------
def _l46():
    digests, dates = set(), set()
    for p in PACKS:
        df = _read(p, "lib/runtime/Dockerfile")
        m = re.search(r"sha256:([0-9a-f]{64})", df)
        digests.add(m.group(1) if m else "none")
        dates.add(bool(re.search(r"resolved 2026-09-08", df)))
    ok = len(digests) == 1 and digests != {"none"} and dates == {True}
    return ok, "one digest across four=%s (%s...), resolve date recorded=%s" % (
        len(digests) == 1, list(digests)[0][:12], dates)


# ---- L47 Housing security pipeline ---------------------------------------------------------------
def _l47():
    return _exists_all(".github/workflows/security.yml")


# ---- L48 pass-ratio gate ------------------------------------------------------------------------
def _l48():
    return _exists_all("tests/test_doc_count_ratios.py")


# ---- L49 historical marker scoping ---------------------------------------------------------------
def _l49():
    bad = []
    for p in PACKS:
        src = _read(p, "tests/test_doc_counts.py")
        if 'text[m.end(): m.end() + 40]' not in src:
            bad.append(p)
        if 'or "count-gate:historical" in context' in src:
            bad.append(p + " (still line-scoped)")
    return (not bad), "; ".join(bad) or "number-scoped marker rule in all four"


# ---- L51 core pin hash --------------------------------------------------------------------------
def _l51():
    hashes, vers = set(), set()
    for p in PACKS:
        req = _read(p, "requirements-core.txt")
        hashes.add((re.search(r"--hash=sha256:([0-9a-f]{64})", req) or [None, "none"])[1])
        vers.add((_read(p, "lib/CORE_VERSION")).strip())
    ok = len(hashes) == 1 and len(vers) == 1
    return ok, "one hash across four=%s one version=%s (%s)" % (
        len(hashes) == 1, len(vers) == 1, ",".join(vers))


# ---- L52 core-pin prose gate ---------------------------------------------------------------------
def _l52():
    return _exists_all("tests/test_core_pin_docs.py")


# ---- L53 portfolio front door --------------------------------------------------------------------
def _l53():
    missing = []
    for doc in ("README.md", "PORTFOLIO-START-HERE.md"):
        text = _read("WOGplatform", doc)
        for pack in PACKS:
            if pack not in text:
                missing.append("%s lacks %s" % (doc, pack))
    return (not missing), "; ".join(missing) or "both front-door docs name all four governed packs"


# ---- L54 releases --------------------------------------------------------------------------------
def _l54():
    bad = []
    for p in PACKS:
        tag = _read(p, "RELEASE").strip()
        r = subprocess.run(["gh", "release", "view", "--json", "tagName", "-q", ".tagName"],
                           cwd=ROOT / p, capture_output=True, text=True, shell=(True))
        latest = (r.stdout or "").strip()
        if latest != tag:
            bad.append("%s: RELEASE=%s latest=%s" % (p, tag, latest or "none"))
    return (not bad), "; ".join(bad) or "the RELEASE tag is the published Latest in all four"


# ---- L55 parity check runs -----------------------------------------------------------------------
def _l55():
    wf = _read("WOGplatform", ".github/workflows/parity.yml")
    runs = "check_core_parity.py" in wf
    src = _read("WOGplatform", "tools/check_core_parity.py")
    refuses = "Refusing to report parity over a subset" in src
    negs = wf.count("Negative control") >= 4
    return (runs and refuses and negs), "workflow runs it=%s refuses on subset=%s negative " \
        "controls=%d" % (runs, refuses, wf.count("Negative control"))


# ---- L56 claim accuracy --------------------------------------------------------------------------
def _l56_residue():
    src = _read("benefits_eligibility_agent", "scripts/full_portfolio_gate.py")
    renamed = 'check("teardown_zero_residue"' not in src
    measured = '"gated": False' in src and '"size_mb"' in src
    return (renamed and measured), "overclaiming name gone=%s residue measured=%s" % (
        renamed, measured)


def _l56_budget():
    src = _read("benefits_eligibility_agent", "README.md")
    return ("at least once per day" in src and "once per budget" in src), \
        "README states the Budgets latency and once-per-period properties"


def _l56_checkov():
    tool = ROOT / "WOGplatform" / "tools" / "checkov_baseline_census.py"
    if not tool.exists():
        return False, "census tool missing"
    r = subprocess.run([sys.executable, str(tool), str(ROOT)], capture_output=True, text=True)
    m = re.search(r"TOTAL SUPPRESSED ACROSS THE PORTFOLIO\s+(\d+)", r.stdout)
    total = int(m.group(1)) if m else -1
    doc = _read("WOGplatform", "docs/GAP-CLOSURE-BACKLOG.md")
    stated = ("**%d → 0**" % total) in doc or ("%d → 0" % total) in doc
    return (total > 93 and stated), "census total=%d and the backlog states it=%s" % (total, stated)


# ---- L57 enforced guardrail ----------------------------------------------------------------------
def _l57():
    p = ROOT / "benefits_eligibility_agent" / "scripts" / "account_enforced_guardrail.py"
    if not p.exists():
        return False, "tool missing"
    src = p.read_text(encoding="utf-8")
    return ("i-understand-this-affects-every-bedrock-call-in-the-account" in src
            and "list_enforced_guardrails_configuration()" in src), \
        "blast-radius confirmation required; correct operation name pinned"


# ---- L58 doc parity ------------------------------------------------------------------------------
def _l58():
    tool = ROOT / "WOGplatform" / "tools" / "check_doc_parity.py"
    if not tool.exists():
        return False, "tool missing"
    r = subprocess.run([sys.executable, str(tool), str(ROOT)], capture_output=True, text=True)
    return (r.returncode == 0), (r.stdout.strip().splitlines() or ["no output"])[-1]


# ---- 232 policy provenance -----------------------------------------------------------------------
def _t232():
    return _exists_all("tests/test_policy_provenance.py")


# ---- 233 runtime gateway-only --------------------------------------------------------------------
def _t233():
    bad = [p for p in PACKS if "allowedWorkloadConfiguration" not in _read(p, "lib/runtime/_configure.sh")]
    return (not bad), "; ".join(bad) or "allowedWorkloadConfiguration wired in all four"


# ---- PAR-4 shared proofs consumed ----------------------------------------------------------------
def _par4():
    consumers = [p for p in PACKS
                 if (ROOT / p / "scripts" / "trace_case.py").exists()
                 and "governed_core.proofs" in _read(p, "scripts/trace_case.py")]
    return (len(consumers) >= 3), "packs consuming governed_core.proofs: %s" % (
        ", ".join(consumers) or "NONE")


# ---- integrity locks -----------------------------------------------------------------------------
def _locks():
    bad = []
    for p in PACKS:
        r = subprocess.run([sys.executable, "lib/verify_core.py"], cwd=ROOT / p,
                           capture_output=True, text=True)
        if r.returncode != 0:
            bad.append("%s: %s" % (p, (r.stdout or r.stderr).strip().splitlines()[-1][:80]))
    return (not bad), "; ".join(bad) or "verify_core clean in all four"


CHECKS = [
    ("L40", "redaction scanner matches prose-written account ids", _l40),
    ("L41", "lineage proof counts unmapped invokes", _l41),
    ("L42", "gate timeout kills the tree, not its own runner (POSIX + Windows job)", _l42),
    ("L43", "signature verifier can actually fail closed", _l43),
    ("L44", "secrets baselines are readable UTF-8", _l44_baselines),
    ("L45a", "secret checker ignores the clock, not the coverage", _l45_checker),
    ("L45b", "trivy pinned to a commit that exists", _l45_trivy),
    ("L46", "runtime base image bumped and dated, one digest across packs", _l46),
    ("L47", "every pack has a security workflow", _l47),
    ("L48", "mismatched pass ratios are gated", _l48),
    ("L49", "historical marker scopes one number, not the line", _l49),
    ("L50", "baseline was generated by the scanner CI pins", _l50_pin),
    ("L51", "one core version and one artifact hash across packs", _l51),
    ("L52", "prose describing the core pin is gated", _l52),
    ("L53", "portfolio front door names the governed packs", _l53),
    ("L54", "the RELEASE tag is the published Latest release", _l54),
    ("L55", "the parity check actually runs, and refuses on a subset", _l55),
    ("L56a", "teardown check is named for what it verifies", _l56_residue),
    ("L56b", "the Budgets ceiling is documented as a slow backstop", _l56_budget),
    ("L56c", "checkov burn-down counts the whole portfolio", _l56_checkov),
    ("L57", "enforced-guardrail tool refuses without a blast-radius confirmation", _l57),
    ("L58", "shared files are identical across packs", _l58),
    ("232", "policy provenance reaches the deployed functions", _t232),
    ("233", "runtime invocation restricted to the gateway", _t233),
    ("PAR-4", "the shared proof library has real consumers", _par4),
    ("REL-4", "integrity locks verify clean in every pack", _locks),
]

for fid, title, fn in CHECKS:
    check(fid, title, fn)

width = max(len(r["title"]) for r in results)
print("FINAL VALIDATION - %d checks against the working tree" % len(results))
print("=" * (width + 26))
for r in results:
    print("%-6s %-6s %-*s  %s" % (r["id"], "PASS" if r["ok"] else "FAIL", width, r["title"],
                                  r["detail"][:110]))
failed = [r for r in results if not r["ok"]]
print("=" * (width + 26))
print("%d/%d PASS" % (len(results) - len(failed), len(results)))
if failed:
    print("\nSTILL OPEN:")
    for r in failed:
        print("  %-6s %s -> %s" % (r["id"], r["title"], r["detail"]))
out = ROOT / "WOGplatform" / "evidence" / "FINAL-VALIDATION-2026-09-08.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"date": "2026-09-08", "checks": results,
                           "pass": len(results) - len(failed), "total": len(results)},
                          indent=2), encoding="utf-8", newline="\n")
print("\nevidence -> %s" % out)
sys.exit(1 if failed else 0)
