"""CI coverage gate — every test file in the repo must actually be EXECUTED by CI.

WHY THIS EXISTS: `ci.yml` named its test steps one file at a time (`python demo/test_fail_closed.py`,
`demo/test_prod_components.py`, `demo/test_negative_security.py`). Five test files were therefore never
run on any push:

    demo/test_acceptance.py
    demo/test_evidence_vault.py
    platform_core/tests/test_agp_conformance.py
    platform_core/tests/test_masker_ner.py
    platform_core/tests/test_no_status_drift.py

They passed — but nothing proved that on an ongoing basis, while the repo advertised continuous
validation of exactly those controls (AGP conformance, PII masking, evidence-vault integrity, and the
status-drift gate). A hand-listed set of test steps silently drops any test file added later.

This gate fails the build whenever a test file exists that no CI step names.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

# Test files deliberately outside CI, each with a stated reason. Keep this empty unless there is one.
EXCLUDED: set[str] = set()


def _test_files():
    out = set()
    for p in ROOT.rglob("test_*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".git/", ".venv/", "node_modules/")) or "__pycache__" in rel:
            continue
        out.add(rel)
    return out


def _executed_paths():
    """Paths actually passed to `python` / `pytest` in the workflow — not any substring of the file.

    Substring matching is too loose. `demo` appears in a `compileall platform_core demo tools` step,
    which made every file under demo/ look covered even after its real test step was deleted. (That
    bug was in the first version of this gate and was caught by deliberately breaking ci.yml.)
    """
    wf = CI_WORKFLOW.read_text(encoding="utf-8")
    paths = set()
    for line in wf.splitlines():
        if "pytest" not in line and "python " not in line:
            continue
        if "compileall" in line:      # compiles sources; does not execute tests
            continue
        for tok in re.split(r"[\s'\"]+", line):
            if tok.startswith("-") or "=" in tok:
                continue
            if tok.endswith(".py") or "/" in tok:
                paths.add(tok.strip().rstrip(":"))
    return paths


def test_ci_runs_every_test_file():
    """A test file no CI step executes is a test file that never runs."""
    assert CI_WORKFLOW.exists(), ".github/workflows/ci.yml is missing"
    executed = _executed_paths()
    assert executed, "could not parse any executed paths out of ci.yml"

    uncovered = []
    for rel in sorted(_test_files()):
        if rel in EXCLUDED:
            continue
        # Covered if CI executes the file itself, or a directory that contains it.
        parts = rel.split("/")
        ancestors = {"/".join(parts[:i]) for i in range(1, len(parts))}
        if rel not in executed and not (ancestors & executed):
            uncovered.append(rel)

    assert not uncovered, (
        "these test files are never executed by ci.yml (add a step, or add them to EXCLUDED with a "
        f"reason): {uncovered}")
