"""Gate: the portfolio-facing documents must name the packs the work is actually in.

WHY THIS EXISTS
---------------
On 2026-09-08 an audit counted repository mentions in the four portfolio-facing documents:

    README.md                        13 mentions of the July-2026 packs,  2 of the governed packs
    PORTFOLIO-START-HERE.md           4                                   0
    PORTFOLIO-EXECUTIVE-SUMMARY.md    5                                   0
    PORTFOLIO-MATURITY-SCORECARD.md   1                                   0

Every live gate, tag, evidence record and parity matrix since 2026-08 concerns
benefits_eligibility_agent, pharmacovigilance_agent, edu_financial_aid_agent and
Housing_eligibility_agent. The front door named none of them, and README described the portfolio as
"a single, review-as-one solution" of five repositories — four of which carry none of the controls
this repo documents. A CISO following that instruction would have reviewed the wrong four repos.

The documents now describe two tiers explicitly. This gate keeps the front door pointing at Tier 1.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

GOVERNED_PACKS = [
    "benefits_eligibility_agent",
    "pharmacovigilance_agent",
    "edu_financial_aid_agent",
    "Housing_eligibility_agent",
]

# The documents a reader lands on first. Each must name every Tier-1 pack.
FRONT_DOOR = ["README.md", "PORTFOLIO-START-HERE.md"]


def test_the_front_door_documents_name_every_governed_pack():
    problems = []
    for name in FRONT_DOOR:
        p = ROOT / name
        if not p.exists():
            problems.append("%s is missing" % name)
            continue
        text = p.read_text(encoding="utf-8")
        missing = [pack for pack in GOVERNED_PACKS if pack not in text]
        if missing:
            problems.append("%s does not name %s" % (name, ", ".join(missing)))
    assert not problems, (
        "the portfolio front door does not name the packs the work is in:\n  "
        + "\n  ".join(problems)
        + "\n\nEvery live gate, tag and evidence record since 2026-08 is in those repos. A front "
          "door that names only the July-2026 packs sends a reviewer to the wrong four."
    )


def test_the_review_as_one_claim_is_not_restated():
    """The specific sentence that made this actively misleading must not come back.

    "1 of 5 that form a single, review-as-one solution" told a reviewer to approve the Tier-2 packs
    together with the control plane, as though they carried its controls. They do not.
    """
    offenders = []
    for name in FRONT_DOOR + ["PORTFOLIO-EXECUTIVE-SUMMARY.md", "PORTFOLIO-MATURITY-SCORECARD.md"]:
        p = ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for phrase in ("review-as-one solution", "one solution, five repositories",
                       "1 of 5 that form a single"):
            # The documents explain the retraction and quote the phrase once. That is the only
            # allowed occurrence, and it must sit inside the retraction paragraph - checked over a
            # small window because the sentence wraps across lines in the markdown source.
            lines = text.splitlines()
            for n, line in enumerate(lines):
                if phrase not in line:
                    continue
                window = " ".join(lines[max(0, n - 3): n + 4])
                if "earlier revision" in window:
                    continue
                offenders.append("%s:%d %r restated outside its retraction" % (name, n + 1, phrase))
    assert not offenders, "\n  ".join(sorted(set(offenders)))


# The two long portfolio documents were NOT rewritten - they describe Tier 2 and are dated
# 2026-07-28. Rewriting them would have meant re-verifying several hundred claims about repos this
# campaign has not touched. They carry a currency banner instead, which is honest and cheap; this
# gate makes sure the banner cannot be dropped while the stale body stays.

TIER2_DOCS = ["PORTFOLIO-EXECUTIVE-SUMMARY.md", "PORTFOLIO-MATURITY-SCORECARD.md"]


def test_the_tier2_documents_carry_their_currency_banner():
    problems = []
    for name in TIER2_DOCS:
        p = ROOT / name
        if not p.exists():
            problems.append("%s is missing" % name)
            continue
        head = "".join(p.read_text(encoding="utf-8").splitlines(True)[:30])
        if "this document describes TIER 2 only" not in head:
            problems.append("%s lost its Tier-2 currency banner (must be within the first 30 lines)"
                            % name)
    assert not problems, (
        "\n  ".join(problems)
        + "\n\nThese documents are dated 2026-07-28 and describe the July-2026 packs. Without the "
          "banner a reader takes their test counts and maturity ratings as statements about the "
          "governed packs, which they are not."
    )
