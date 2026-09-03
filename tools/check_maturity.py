#!/usr/bin/env python3
"""check_maturity — portfolio drift-checker for MATURITY.yaml's test count.

MATURITY.yaml is the single source of truth for this repo's maturity claims
(see the header of that file). One of those claims is `tests.offline_total`:
the number of automated tests that ship in the repo. It is easy for that
headline to drift as tests are added or removed. This tool closes the loop:
it re-collects the test suite named by `tests.reproduce` and compares the
ACTUAL collected count against the DECLARED `offline_total`.

Usage:
    python tools/check_maturity.py            # verify; exit 1 on drift
    python tools/check_maturity.py --update   # rewrite offline_total to actual

Stdlib-only. Resolves the repo root as the parent of tools/, so it works from
any working directory. Runs pytest via the current interpreter (sys.executable)
so it honours whatever venv invoked it.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATURITY = os.path.join(REPO_ROOT, "MATURITY.yaml")

# Fallback if tests.reproduce cannot be parsed for target paths.
DEFAULT_TARGETS = ["demo", "platform_core/tests"]

_OFFLINE_TOTAL_RE = re.compile(r"^(\s*offline_total:\s*)(\d+)(.*)$", re.MULTILINE)
_REPRODUCE_RE = re.compile(r"^\s*reproduce:\s*(.+?)\s*$", re.MULTILINE)
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def read_maturity() -> str:
    with open(MATURITY, encoding="utf-8") as fh:
        return fh.read()


def declared_total(text: str) -> int:
    m = _OFFLINE_TOTAL_RE.search(text)
    if not m:
        raise SystemExit("check_maturity: could not find `offline_total:` in MATURITY.yaml")
    return int(m.group(2))


def parse_reproduce(text: str):
    """Return (targets, extra_env) parsed from tests.reproduce.

    The reproduce line looks like:
        "PYTHONPATH=platform_core:. pytest demo platform_core/tests -q"
    We collect env assignments (VAR=val) that precede `pytest`, then take the
    tokens after `pytest` up to the first flag as the target paths.
    """
    m = _REPRODUCE_RE.search(text)
    if not m:
        return list(DEFAULT_TARGETS), {}

    line = m.group(1).strip().strip('"').strip("'")
    tokens = line.split()

    extra_env: dict[str, str] = {}
    i = 0
    # Leading VAR=val assignments (e.g. PYTHONPATH=...).
    while i < len(tokens) and _ENV_ASSIGN_RE.match(tokens[i]):
        key, _, val = tokens[i].partition("=")
        extra_env[key] = val
        i += 1

    # Skip up to and including the `pytest` (or `python -m pytest`) token.
    while i < len(tokens) and tokens[i] not in ("pytest",):
        i += 1
    if i < len(tokens) and tokens[i] == "pytest":
        i += 1

    targets = []
    while i < len(tokens) and not tokens[i].startswith("-"):
        targets.append(tokens[i])
        i += 1

    return (targets or list(DEFAULT_TARGETS)), extra_env


def _build_env(extra_env: dict) -> dict:
    env = dict(os.environ)
    # Normalise PYTHONPATH so `platform_core:.` resolves against the repo root
    # regardless of the caller's cwd.
    reproduce_pp = extra_env.get("PYTHONPATH", "platform_core:.")
    parts = []
    for entry in reproduce_pp.split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        parts.append(entry if os.path.isabs(entry) else os.path.join(REPO_ROOT, entry))
    existing = env.get("PYTHONPATH", "")
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def collect_count(targets, extra_env) -> int:
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", *targets]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=_build_env(extra_env),
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    lines = out.splitlines()

    # Primary: one node id per line, each containing "::".
    node_ids = [ln for ln in lines if "::" in ln]
    if node_ids:
        return len(node_ids)

    # Fallback for pytest's compact "-q" collect output ("path.py: N" lines),
    # emitted by newer pytest when no node ids are printed.
    total = 0
    matched = False
    for ln in lines:
        fm = re.match(r"^\S+:\s+(\d+)\s*$", ln)
        if fm:
            total += int(fm.group(1))
            matched = True
    if matched:
        return total

    # Last resort: "N test(s) collected" summary line.
    for ln in lines:
        sm = re.search(r"(\d+)\s+tests?\s+collected", ln)
        if sm:
            return int(sm.group(1))

    sys.stderr.write(
        "check_maturity: could not parse pytest --collect-only output:\n" + out + "\n"
    )
    raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="rewrite offline_total in MATURITY.yaml to the actual collected count",
    )
    args = parser.parse_args()

    text = read_maturity()
    declared = declared_total(text)
    targets, extra_env = parse_reproduce(text)
    actual = collect_count(targets, extra_env)

    print(f"MATURITY.yaml offline_total (declared): {declared}")
    print(f"collected tests (actual):               {actual}")
    print(f"targets:                                {' '.join(targets)}")

    if declared == actual:
        print("OK: no MATURITY drift.")
        return 0

    if args.update:
        new_text = _OFFLINE_TOTAL_RE.sub(
            lambda m: f"{m.group(1)}{actual}{m.group(3)}", text, count=1
        )
        with open(MATURITY, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        print(f"UPDATED: offline_total {declared} -> {actual} in MATURITY.yaml")
        return 0

    print(
        f"MATURITY drift: MATURITY.yaml declares {declared} tests but "
        f"{actual} are collected. Run `python tools/check_maturity.py --update` "
        f"(or fix the suite) to reconcile."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
