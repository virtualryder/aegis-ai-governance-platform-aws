#!/usr/bin/env python3
"""Docs hygiene gate (COPILOT-6d, 2026-09-03): every relative link in a tracked Markdown file must
resolve, and no file may carry UTF-8 mojibake (' Â· ', 'â€”', 'â†’' ... - text that was UTF-8 decoded as
cp1252 and re-encoded, seen in MATURITY.yaml and in `gh` output). Run in CI; exit 1 on any finding.

    python tools/check_docs.py            # report
    python tools/check_docs.py --fix-mojibake   # rewrite the known sequences in place, then report
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
MOJIBAKE = ["â€”", "â€“", "â€˜", "â€™", "â€œ", "â€\x9d", "â€¦", "Â·", "â†’", "â‡’", "âœ…", "Â ", "Ã©", "Ã¨", "Ã¼", "Ã¶", "â‰¤", "â‰¥", "Â§", "Â©"]
FIX = {"â€”": "—", "â€“": "–", "â€˜": "‘", "â€™": "’", "â€œ": "“", "â€\x9d": "”", "â€¦": "…", "Â·": "·", "â†’": "→",
       "â‡’": "⇒", "âœ…": "✅", "Â ": " ", "Ã©": "é", "Ã¨": "è", "Ã¼": "ü", "Ã¶": "ö", "â‰¤": "≤", "â‰¥": "≥", "Â§": "§", "Â©": "©"}
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
                if not cand.exists():
                    problems.append(f"{f.relative_to(ROOT)}:{n}: broken link -> {target}")
    if problems:
        print("docs gate: %d problem(s)" % len(problems))
        for p in sorted(problems):
            print("  ", p)
        return 1
    print("docs gate: OK (%d text files, links + encoding clean)" % len(text_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
