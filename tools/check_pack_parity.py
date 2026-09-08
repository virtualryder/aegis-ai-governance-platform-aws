#!/usr/bin/env python3
"""Pack parity matrix: which platform controls are actually WIRED (IaC) in each vertical pack.

"Pins governed-core 1.10.1" is true for every pack, but the library being pinned is not the same as the
controls being wired into the pack's CDK. This tool greps each pack's CDK for the constructs that carry
each control and writes docs/PACK-PARITY.md from what it finds - so the matrix cannot drift from the code
by hand. Run from the WOGplatform checkout with the sibling packs beside it:

    python tools/check_pack_parity.py            # print the matrix
    python tools/check_pack_parity.py --write    # regenerate docs/PACK-PARITY.md
    python tools/check_pack_parity.py --check    # exit 1 if docs/PACK-PARITY.md is stale (CI, packs present)

A pack that is not checked out is reported as "n/a" (CI without the siblings still passes)."""
import argparse
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACKS = [("benefits", "benefits_eligibility_agent"), ("pharmacovigilance", "pharmacovigilance_agent"),
         ("edu_financial_aid", "edu_financial_aid_agent"), ("housing", "Housing_eligibility_agent")]
# control -> (regex over the pack's cdk/*stacks*/*.py + cdk/app.py + lib/runtime/agent.py, minimum hits, what it means)
CONTROLS = [
    ("Hybrid multi-tenant (interceptor, per-tenant data stacks)", r"tenant_interceptor|TenantInterceptor", 2, "governed-core 1.6"),
    ("Kill switch (SSM parameter, engage/disengage function URLs)", r"kill_switch|KillSwitch", 4, "governed-core 1.8"),
    ("Per-tenant token + USD budget, AWS Budgets ceiling", r"budgets_table|UsdCeiling|Aegis/Budget", 3, "governed-core 1.9"),
    ("Model-invocation logging (transparency)", r"model_logging|ModelInvocationLogging", 2, "phase 110"),
    ("Runtime input contract + guardrail on the runtime model", r"def validate_input", 1, "RT-1 / RT-3"),
    ("Runtime execution role as IaC", r"_runtime_execution_role|RuntimeExecutionRole", 2, "RT-2 / RT-3"),
    ("#168 capture-all trail + unified lineage (WORM)", r"LineageStack|CaptureWorm|capture_all", 2, "governed-core 1.10.0"),
    ("Enforcement perimeter (endpoint policy, bypass alarm, CMK invocation store)", r"GovernedDrafterOnly|perimeter-bypass|_perimeter_bypass_alarm", 2, "2026-09-05 review"),
    ("Output guardrail as IaC + grounded drafter (#166/#190)", r"CfnGuardrail|guardrail_config", 2, "2026-09-05"),
    ("WAFv2 on the Cognito front door (#170)", r"CfnWebACL|WebAcl", 2, "2026-09-05"),
    ("Authoritative Cedar context resolver (#3)", r"authoritative_context|authz_table", 2, "governed-core 1.10.1"),
    # Fourth review R4-3 (2026-09-06): "a guardrail is present" (Null check) is not "THE guardrail" - the
    # allow must name the exact guardrail ARN and an explicit Deny must refuse every other/absent value.
    ("Exact-guardrail model IAM (allow + explicit deny, scoped models)", r"BedrockExactGuardrail|DenyOtherOrNoGuardrail", 2, "2026-09-06 R4-3"),
    # The perimeter Cedar profile itself (-c perimeter=1): the #160/#161 gates the resolver feeds.
    ("Perimeter Cedar profile (#160/#161 gates, -c perimeter=1)", r"_PERIMETER_INPUT_FIELDS|perimeter=perimeter", 2, "2026-09-06 PAR-1"),
    # CHK-1 (2026-09-06): the trail that proves nobody but the gateway touched the evidence was itself
    # delivering into a CDK-default bucket with NO properties at all. The control is the DECLARED,
    # hardened log bucket - and the Log4j managed rule group on the auth Web ACL alongside it.
    ("Hardened evidence-trail log bucket + Log4j WAF group", r"WormDataEventsLogs|KnownBadInputsRuleSet", 2, "2026-09-06 CHK-1"),
    # L20 (2026-09-06): decision-relevant flags extracted from free text must be NEGATION-AWARE.
    # A bare token match set categorical eligibility from an application reading "no TANF", which
    # skips the income test entirely. One shared lib/controls/negation.py, not a copy per pack -
    # a copy is exactly how this class of bug comes back.
    ("Negation-aware decision-flag extraction (L20)", r"negation\.asserted", 1, "2026-09-06 L20"),
    ("Zero-egress private network mode (VPC endpoints)", r"NetworkStack|network_mode", 2, "Gate-B / L9"),
    ("MFA-required identity mode + threat protection", r"identity_mode|Mfa\.REQUIRED", 2, "Gate-B"),
]


def scan(pack_dir):
    files = []
    cdk = os.path.join(pack_dir, "cdk")
    for d in os.listdir(cdk) if os.path.isdir(cdk) else []:
        if d.endswith("stacks") and os.path.isdir(os.path.join(cdk, d)):
            files += [os.path.join(cdk, d, f) for f in os.listdir(os.path.join(cdk, d)) if f.endswith(".py")]
    for extra in (os.path.join(cdk, "app.py"), os.path.join(pack_dir, "lib", "runtime", "agent.py")):
        if os.path.exists(extra):
            files.append(extra)
    # Not every control lives in the CDK. L20 (negation-aware extraction) is a property of the TOOL
    # handlers and the shared lib/controls modules they import, so those are part of the corpus too.
    # Widening the corpus cannot silently flip an existing row: the matrix is regenerated and
    # diffed whenever this list changes.
    for d in (os.path.join(pack_dir, "lib", "controls"),):
        if os.path.isdir(d):
            files += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".py")]
    agents = os.path.join(pack_dir, "agents")
    for a in sorted(os.listdir(agents)) if os.path.isdir(agents) else []:
        t = os.path.join(agents, a, "tools")
        if os.path.isdir(t):
            files += [os.path.join(t, f) for f in os.listdir(t) if f.endswith(".py")]
    text = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in files)
    return {name: len(re.findall(pat, text)) >= n for name, pat, n, _ in CONTROLS}


def build(base):
    rows, present, pinned = {}, {}, {}
    for label, d in PACKS:
        p = os.path.join(base, d)
        present[label] = os.path.isdir(os.path.join(p, "cdk"))
        rows[label] = scan(p) if present[label] else {}
        # 2026-09-08: READ the pinned core, do not hardcode it. The prose below used to state a
        # literal "1.10.1"; the packs moved to 1.11.1 and this page went on saying 1.10.1 while
        # --check reported OK, because the generator and the file agreed on a claim that was wrong
        # about the world. A generated document can only be self-consistent; it is honest only if
        # every fact in it is read from the thing it describes.
        try:
            pinned[label] = open(os.path.join(p, "lib", "CORE_VERSION"),
                                 encoding="utf-8").read().strip()
        except OSError:
            pinned[label] = None
    return rows, present, pinned


# Which pack has actually been LIVE-gated on the AgentCore-era control set, as opposed to having it
# wired. Kept as data next to the matrix rather than as an adjective inside it, because "wired" is
# computed from the sources and "live-proven" is a fact about a run that no source scan can see.
LIVE_PROVEN = {
    "benefits": "**LIVE-gated** - full-portfolio gate 15/15 from zero (`v0.6.0-pilot-rc1`).",
    "pharmacovigilance": "**Offline-gated only** - last live gate ran on governed-core 1.9.0; a live "
                         "re-gate is REL-5.",
    "edu_financial_aid": "**Offline-gated only** - last live gate ran on governed-core 1.9.0; a live "
                         "re-gate is REL-5.",
    "housing": "**No AgentCore-era live gate has ever run on this pack** (last live validation "
               "2026-07-24, EP1/Gate-B).",
}


def _proof_note(label):
    return LIVE_PROVEN.get(label, "Live-proof status not recorded - state it before quoting this row.")


def _pin_sentence(pinned):
    """State the pinned core as it ACTUALLY is, and say so loudly if the packs disagree."""
    seen = sorted({v for v in pinned.values() if v})
    if not seen:
        return ("**Why this page exists (honesty).** The pinned governed-core version could not be "
                "read from any pack, so it is not stated here rather than guessed. Pinning the "
                "*library* is not the same as")
    if len(seen) == 1:
        return ("**Why this page exists (honesty).** Every pack pins governed-core %s, but pinning "
                "the *library* is not the same as" % seen[0])
    disagree = ", ".join("%s %s" % (k, v) for k, v in sorted(pinned.items()) if v)
    return ("**Why this page exists (honesty).** The packs DISAGREE on the pinned governed-core "
            "version (%s), which `tools/check_core_parity.py` fails on. Pinning the *library* is "
            "not the same as" % disagree)


def render(rows, present, pinned):
    hdr = "| Control (wired in the pack's CDK / runtime) | Since | " + " | ".join(l for l, _ in PACKS) + " |"
    sep = "|---|---|" + "|".join("---" for _ in PACKS) + "|"
    out = ["# Pack parity — which platform controls are actually WIRED per pack", "",
           "Generated by `tools/check_pack_parity.py` from the packs' CDK + runtime sources on %s. Do not edit by hand." % datetime.date.today().isoformat(), "",
           _pin_sentence(pinned),
           "*wiring* the controls it provides into the pack's own IaC. A ✅ means the construct is in the pack's CDK/runtime",
           "(IaC-asserted); whether it is also **live-proven** is recorded per pack in its `VALIDATED_RELEASE.md` (the packs",
           "carry no `MATURITY.yaml` of their own — only this repo does, and it covers the platform).",
           "A ❌ means the control is **absent** in that pack — not \"pending validation\", absent.", "",
           hdr, sep]
    for name, _, _, since in CONTROLS:
        cells = []
        for l, _ in PACKS:
            cells.append("n/a" if not present[l] else ("✅" if rows[l].get(name) else "❌"))
        out.append("| %s | %s | %s |" % (name, since, " | ".join(cells)))
    out += ["", "## Reading the matrix (computed)", ""]
    for l, _ in PACKS:
        if not present[l]:
            out.append("- **%s**: not checked out beside this repo." % l); continue
        missing = [n for n, _, _, _ in CONTROLS if not rows[l].get(n)]
        if not missing:
            # 2026-09-08: this said "(lead pack; live-gated ...)" for EVERY pack with a full row, so
            # the generated page called PV and EDU live-gated lead packs. They are neither: all
            # controls WIRED, none live-proven since governed-core 1.9.0. Wired-vs-proven is the
            # distinction this whole page exists to make, and the summary line was erasing it.
            out.append("- **%s**: every control is wired. %s" % (l, _proof_note(l)))
        else:
            out.append("- **%s**: %d of %d wired. **Absent:** %s." % (l, len(CONTROLS) - len(missing), len(CONTROLS), "; ".join(missing)))
    _versions = sorted({v for v in pinned.values() if v})
    _relver = _versions[0] if len(_versions) == 1 else "the pinned core"
    out += ["", "Backlog: **PAR-1** (PV/EDU 2026-09-05 controls), **PAR-2** (Housing full uplift), then **REL-5** live re-gates on %s" % _relver,
            "so a live gate proves the same control set everywhere (`docs/GAP-CLOSURE-BACKLOG.md`).", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.dirname(ROOT), help="directory holding the pack checkouts (default: parent of this repo)")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rows, present, pinned = build(a.base)
    if not any(present.values()):
        # Until 2026-09-08 this returned 0 with "nothing to verify (OK)". The platform repo's CI
        # never checks the packs out, so the step named "no-op when the packs are not checked out"
        # had ALWAYS passed without verifying anything - the same defect as the checkov job that
        # synthesized zero templates (L44b) and the parity check nothing ran (L55). It refuses now;
        # the real invocation lives in .github/workflows/parity.yml, which clones the packs first.
        print("::error::check_pack_parity: no pack checkouts found beside this repo. Refusing to "
              "report the matrix as verified when it compared nothing - clone the packs (see "
              ".github/workflows/parity.yml) or pass --base.")
        return 2
    doc = render(rows, present, pinned)
    target = os.path.join(ROOT, "docs", "PACK-PARITY.md")
    if a.write:
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(doc)
        print("wrote", target)
        return 0
    if a.check:
        cur = open(target, encoding="utf-8").read() if os.path.exists(target) else ""
        strip = lambda s: re.sub(r"on \d{4}-\d{2}-\d{2}\.", "", s)
        if strip(cur) != strip(doc):
            print("check_pack_parity: docs/PACK-PARITY.md is STALE - run tools/check_pack_parity.py --write")
            return 1
        print("check_pack_parity: OK (matrix matches the packs' sources)")
        return 0
    print(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
