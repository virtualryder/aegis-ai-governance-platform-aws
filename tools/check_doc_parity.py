#!/usr/bin/env python3
"""Cross-repo parity: shared files must be identical, required files must exist.

WHY THIS EXISTS (#237)
----------------------
`check_core_parity.py` compares the governed-core PIN across packs. Nothing compared anything else -
and the 2026-09-07/08 remediation created a large surface for exactly that gap to reopen:

  * Eleven files were COPIED into four repositories by hand (the secrets-baseline checker, five
    gate tests, the base-image and gate-config tests, the regeneration procedure, the security
    workflow). Nothing stops one copy being edited and the other three rotting - which is PAR-4's
    fork, in the very files written to detect drift.
  * Housing turned out to have NO security workflow at all (L47), and nothing noticed for a month,
    because PACK-PARITY compares CONTROLS and not the CI that scans for them.
  * The four security workflows were already diverging when this tool was written: benefits and
    Housing ran an extra `docker manifest inspect` step that PV and EDU did not.

Two rules, deliberately different in kind:

    SHARED    the file must be byte-identical across every pack that is expected to have it.
              Line endings are normalised - a CRLF checkout must not read as drift (L36) - but
              nothing else is. A comment that differs IS drift: it means two people fixed the same
              thing twice and one of them will be fixed again next time.

    REQUIRED  the file must EXIST in every pack. This is the Housing case: absence with nobody
              looking.

Pack-specific files (pack.json, prefixes, tenant ids, domain controls) are deliberately not
compared; `docs/PACK-PARITY.md` is where per-pack divergence is recorded.

    python tools/check_doc_parity.py <parent-dir-or-repos...>
"""
import argparse
import hashlib
import os
import pathlib
import sys

PACKS = ["benefits_eligibility_agent", "pharmacovigilance_agent",
         "edu_financial_aid_agent", "Housing_eligibility_agent"]

# Byte-identical across every pack. Each of these was copied by hand; each is a fork waiting.
SHARED = [
    # Line-ending policy. Added 2026-09-08 (L60): three different versions had already
    # drifted across the four packs, which is the L58 shape - copied by hand, nothing
    # comparing the copies. A pack whose line-ending rules differ produces a different
    # working tree from the same commit, so this belongs in SHARED, not in REQUIRED.
    ".gitattributes",
    "tools/check_secrets_baseline.py",
    "tools/check_core_parity.py",
    "tests/test_doc_count_ratios.py",
    "tests/test_core_pin_docs.py",
    "tests/test_secrets_baseline_pin.py",
    "tests/test_policy_provenance.py",
    "tests/test_runtime_gateway_only.py",
    "tests/test_gate_configs_readable.py",
    "tests/test_base_image_freshness.py",
    "tests/test_secrets_baseline_check.py",
    "docs/SECRETS-BASELINE.md",
    ".github/workflows/security.yml",
]

# Must exist. Content is pack-specific, but absence is the L47 defect.
REQUIRED = [
    ".github/workflows/ci.yml",
    ".github/workflows/security.yml",
    ".secrets.baseline",
    ".checkov.baseline",
    "RELEASE",
    "requirements-core.txt",
    "lib/CORE_VERSION",
    "lib/core.lock",
    "ruff.toml",
    "tests/test_doc_counts.py",
    "tests/test_release_consistency.py",
]


def _norm_hash(p):
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _resolve(roots):
    """Accept either a parent directory holding the packs, or the pack paths themselves.

    Case-insensitive on the directory name. The GitHub repository is `EDU_financial_aid_agent`
    and the local working copy is `edu_financial_aid_agent`; a case-sensitive match found three
    packs on the runner and refused - correctly, but for the wrong reason. Matching case-blind
    keeps the refusal meaning "a pack is genuinely absent".
    """
    canon = {n.lower(): n for n in PACKS}
    found = {}
    for root in roots:
        rp = pathlib.Path(root).resolve()
        if rp.is_dir() and rp.name.lower() in canon:
            found[canon[rp.name.lower()]] = rp
            continue
        if not rp.is_dir():
            continue
        for child in rp.iterdir():
            if child.is_dir() and child.name.lower() in canon:
                found.setdefault(canon[child.name.lower()], child)
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="+")
    a = ap.parse_args(argv)

    repos = _resolve(a.roots)
    missing_packs = [p for p in PACKS if p not in repos]
    if missing_packs:
        print("::error::could not find pack(s): %s" % ", ".join(missing_packs))
        print("Refusing to report parity over a subset - a pack that is not compared is exactly "
              "where a divergence hides (this is the L47 shape).")
        return 2

    failures = []

    print("SHARED - byte-identical across all %d packs (line endings normalised)" % len(PACKS))
    for rel in SHARED:
        digests, absent = {}, []
        for name, root in repos.items():
            f = root / rel
            if f.is_file():
                digests.setdefault(_norm_hash(f), []).append(name)
            else:
                absent.append(name)
        if absent:
            failures.append("%s is MISSING from: %s" % (rel, ", ".join(sorted(absent))))
            print("  FAIL  %-46s missing from %s" % (rel, ", ".join(sorted(absent))))
        elif len(digests) > 1:
            groups = " | ".join("%s: %s" % (d[:8], ",".join(sorted(v))) for d, v in digests.items())
            failures.append("%s DIVERGED across packs (%s)" % (rel, groups))
            print("  FAIL  %-46s %s" % (rel, groups))
        else:
            print("  ok    %-46s %s" % (rel, list(digests)[0][:8]))

    print()
    print("REQUIRED - must exist in every pack")
    for rel in REQUIRED:
        absent = sorted(n for n, root in repos.items() if not (root / rel).exists())
        if absent:
            failures.append("%s is MISSING from: %s" % (rel, ", ".join(absent)))
            print("  FAIL  %-46s missing from %s" % (rel, ", ".join(absent)))
        else:
            print("  ok    %-46s present in %d/%d" % (rel, len(repos), len(PACKS)))

    print()
    if failures:
        print("DOC PARITY FAILED - %d divergence(s):" % len(failures))
        for f in failures:
            print("  -", f)
        print()
        print("A shared file that differs is not a style question: it means the same defect was "
              "fixed twice and one copy will be fixed again. Copy the intended version across, or "
              "move the file out of SHARED with a reason.")
        return 1

    print("DOC PARITY OK - %d shared files identical, %d required files present, in all %d packs"
          % (len(SHARED), len(REQUIRED), len(PACKS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
