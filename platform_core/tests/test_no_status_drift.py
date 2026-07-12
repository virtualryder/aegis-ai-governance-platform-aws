"""CI drift gate — every CURRENT-state doc must agree with MATURITY.yaml on the test count.
Historical files (changelogs, deploy evidence, review/action plans) cite point-in-time numbers on
purpose and are excluded. Fails the build on drift so a stale headline can never ship."""
import glob
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CURRENT = re.compile(r"(\d[\d,]{1,6})\s*(?:\*\*)?\s*(?:automated\s+)?tests?\b", re.I)
HIST = re.compile(r"(?:→|-+>|–>|\bwas\b|\bgrew\b|\bfrom\b|\$)")
SKIP_FILES = {"CHANGELOG.md", "SUITE-STATUS.md", "CLEAN-ACCOUNT-ACCEPTANCE.md", "TCO-MODEL.md",
              "SOW-TEMPLATE.md", "CONTROL-EVIDENCE.md", "DEPLOY-EVERYTHING.md",
              "PORTFOLIO-START-HERE.md", "PORTFOLIO-CONNECTOR-MATURITY.md", "COMMIT-MANIFEST.md"}
SKIP_MARKERS = ("ACTION-PLAN", "REVIEW", "REMEDIATION", "DEPLOY-NOTES", "GOLDEN-PATH-DEPLOY",
                "DECK-SOURCES")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv"}
# Portfolio-level docs (runbook, scorecard, summary, packet) legitimately cite sibling repos'
# canonical counts and the portfolio total. Allow that exact canonical set so those docs pass the
# gate while a STALE number (e.g. a leftover 1,326 or EDU's old 197) still fails.
# Canonical offline counts verified 2026-07-12 — UPDATE THIS SET when any repo's count changes:
#   Aegis 43 · EDU 201 · SLG 236 · HPP 270 · HCLS 580 (576 root-collect) · portfolio total 1,330.
PORTFOLIO = {201, 236, 270, 576, 580, 1330}


def _total():
    m = re.search(r"offline_total:\s*(\d+)", open(os.path.join(REPO, "MATURITY.yaml"), encoding="utf-8").read())
    return int(m.group(1))


def test_no_test_count_drift():
    total = _total()
    findings = []
    for md in glob.glob(os.path.join(REPO, "**", "*.md"), recursive=True):
        parts = md.split(os.sep)
        base = os.path.basename(md)
        if (any(s in parts for s in SKIP_DIRS) or base in SKIP_FILES
                or any(k in base.upper() for k in SKIP_MARKERS)):
            continue
        try:
            lines = open(md, encoding="utf-8").read().splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue
        for i, ln in enumerate(lines, 1):
            if HIST.search(ln):
                continue
            for num in CURRENT.findall(ln):
                n = int(num.replace(",", ""))
                if 50 <= n <= 4000 and n != total and n not in PORTFOLIO:
                    findings.append(f"{os.path.relpath(md, REPO)}:{i} cites '{num} tests' (MATURITY.yaml={total}, not in canonical portfolio set)")
    assert not findings, "status drift vs MATURITY.yaml:\n  " + "\n  ".join(findings)
