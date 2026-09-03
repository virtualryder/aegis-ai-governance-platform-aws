#!/usr/bin/env python3
"""Docs hygiene gate (COPILOT-6d, 2026-09-03): every relative link in a tracked Markdown file must
resolve, and no tracked text file may carry UTF-8 mojibake - text that was UTF-8 decoded as cp1252 and
re-encoded (an em dash rendered as "a-circumflex euro-sign em-dash", a middle dot as "A-circumflex middle
dot", ...), seen in MATURITY.yaml and in `gh` output. Run in CI; exit 1 on any finding.

    python tools/check_docs.py                  # report
    python tools/check_docs.py --fix-mojibake   # rewrite the known sequences in place, then report
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# The characters whose UTF-8 bytes, mis-decoded as cp1252 and re-encoded, produce the classic
# mojibake (three bytes shown as "a-circumflex, euro, em-dash" for a real em dash, etc.). Derived at import time so this file never contains the
# broken sequences itself (which would trip the gate on its own source).
_CHARS = "\u2014\u2013\u2018\u2019\u201c\u201d\u2026\u00b7\u2192\u21d2\u2705\u00a0\u00e9\u00e8\u00fc\u00f6\u2264\u2265\u00a7\u00a9"
FIX = {}
for _c in _CHARS:
    try:
        FIX[_c.encode("utf-8").decode("cp1252")] = _c
    except UnicodeDecodeError:
        pass
MOJIBAKE = list(FIX)
SKIP_LINK_PREFIX = ("http://", "https://", "mailto:", "#", "computer://")


def tracked(patterns):
    out = subprocess.run(["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.split("\n") if p]


def main() -> int:
    fix = "--fix-mojibake" in sys.argv
    problems = []
    text_files = tracked(["*.md", "*.yaml", "*.yml", "*.py", "*.txt", "*.toml"])
    for f in text_files:
        try:
            raw = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{f.relative_to(ROOT)}: not valid UTF-8")
            continue
        hits = [m for m in MOJIBAKE if m in raw]
        if hits and fix:
            new = raw
            for m in hits:
                new = new.replace(m, FIX[m])
            f.write_text(new, encoding="utf-8", newline="\n")
            raw = new
            hits = [m for m in MOJIBAKE if m in raw]
        for m in hits:
            line = raw[: raw.index(m)].count("\n") + 1
            problems.append(f"{f.relative_to(ROOT)}:{line}: mojibake {m!r}")
    portfolio_links = 0
    for f in tracked(["*.md"]):
        raw = f.read_text(encoding="utf-8", errors="replace")
        in_code = False
        for n, line in enumerate(raw.split("\n"), 1):
            if line.strip().startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            for m in LINK.finditer(line):
                target = m.group(1)
                if target.startswith(SKIP_LINK_PREFIX) or target.startswith("<"):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                cand = (f.parent / path).resolve()
                if ROOT not in cand.parents and cand != ROOT:
                    portfolio_links += 1     # a sibling-repo (portfolio) link; only checkable with the siblings checked out
                    continue
                if not cand.exists():
                    problems.append(f"{f.relative_to(ROOT)}:{n}: broken link -> {target}")
    if problems:
        print("docs gate: %d problem(s)" % len(problems))
        for p in sorted(problems):
            print("  ", p)
        return 1
    print("docs gate: OK (%d text files, links + encoding clean; %d sibling-repo links not checked here)" % (len(text_files), portfolio_links))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
