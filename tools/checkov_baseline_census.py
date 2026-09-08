#!/usr/bin/env python3
"""Count every checkov finding suppressed by a baseline, ACROSS THE WHOLE PORTFOLIO.

WHY THIS EXISTS
---------------
CHK-1 has been tracked since 2026-09-05 as a burn-down of "93 check-instances across 10 platform
templates". That number is real and it is the wrong number: it counts `WOGplatform/infra/.checkov
.baseline` only. The four governed packs carry their own baselines, and nothing ever added them up.

    WOGplatform/infra                  93   (10 templates)
    benefits_eligibility_agent        105   ( 5 templates)
    pharmacovigilance_agent           110   ( 5 templates)
    edu_financial_aid_agent           113   ( 5 templates)
    Housing_eligibility_agent          67   ( 4 templates)   <- added 2026-09-08 with SEC-1
    ------------------------------------------------------
    TOTAL                             488

So the burn-down was reporting 19% of its own scope. A suppressed finding in a pack's synthesized
CloudFormation is exactly as unremediated as one in the platform's - and there are four times more
of them.

This tool exists so the figure is COMPUTED rather than remembered. Run it before quoting a CHK-1
number anywhere.

    python tools/checkov_baseline_census.py <repo-or-parent-dir> [...]
"""
import argparse
import collections
import json
import os
import sys


def _count(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    per_check = collections.Counter()
    templates = doc.get("failed_checks") or []
    for tmpl in templates:
        for finding in tmpl.get("findings") or []:
            for cid in finding.get("check_ids") or []:
                per_check[cid] += 1
    return sum(per_check.values()), len(templates), per_check


def _find(roots):
    out = []
    for root in roots:
        if os.path.isfile(root):
            out.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in {".git", "node_modules", ".venv", "cdk.out", "__pycache__"}
                           and not d.startswith("cdk.out-")]
            if ".checkov.baseline" in filenames:
                out.append(os.path.join(dirpath, ".checkov.baseline"))
    return sorted(set(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="+", help="repos, or a parent directory holding them")
    ap.add_argument("--expect-total", type=int, default=None,
                    help="fail if the portfolio total differs (use this to pin a doc's number)")
    a = ap.parse_args(argv)

    files = _find(a.roots)
    if not files:
        print("::error::no .checkov.baseline found under: %s" % ", ".join(a.roots))
        print("Refusing to report a portfolio total over zero baselines - that is how the 93 "
              "figure came to describe one repo out of five.")
        return 2

    total, rollup = 0, collections.Counter()
    print("%-56s %6s  %s" % ("BASELINE", "CHECKS", "TEMPLATES"))
    for f in files:
        n, t, per = _count(f)
        total += n
        rollup.update(per)
        print("%-56s %6d  %d" % (f, n, t))
    print("%-56s %6d" % ("TOTAL SUPPRESSED ACROSS THE PORTFOLIO", total))

    print()
    print("BY CHECK (the burn-down's actual work queue)")
    for cid, n in rollup.most_common():
        print("  %-16s %4d" % (cid, n))

    if a.expect_total is not None and total != a.expect_total:
        print()
        print("::error::portfolio total is %d, the quoted figure is %d. Update the docs (CHK-1) or "
              "explain the difference - a burn-down that counts a subset reports progress it has "
              "not made." % (total, a.expect_total))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
