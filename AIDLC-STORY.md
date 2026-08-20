# The AI-DLC Story — How This Portfolio Was Built

*The build methodology behind Aegis and the four vertical agents, written down as a positioning
asset: the portfolio is both the product of an AI-driven development lifecycle and the proof that
the lifecycle produces governable software. Pair with slide 10 of the SLG/EDU positioning deck.*

---

## The claim

One architect, an AI pair, and a disciplined loop produced: a governed-agent control plane
(8-control versioned contract, 55 negative tests), four working vertical agents on one template
(benefits, financial aid, housing, pharmacovigilance), per-agent CDK deployment stacks, runbooks,
GTM collateral, and clean-account runtime evidence. Not a demo — a reviewable, CI-gated portfolio.

That is the AI-DLC pitch in one breath: **AI gives you the velocity; the lifecycle keeps the
velocity honest.**

## The loop (what ~30 iterations per agent actually looked like)

1. **Requirements as conversation.** Each agent began as a domain interview with the AI pair —
   what does a caseworker actually sign off on? what makes an ICSR "serious"? — iterated until the
   manifest (tools, data classes, consequential actions, sign-off roles) wrote itself.
2. **Build small, test negative.** Every capability landed with the test that proves its
   *fail-closed* behavior — not "does it work" but "does it refuse correctly." Deny-by-default is
   a test suite before it is a slogan.
3. **Review from hostile angles.** Repeated adversarial passes — security, compliance, domain,
   "explain this to a CISO" — each producing a written review with a verdict and a prioritized
   action plan (the reviews ship in the repos). Findings became commits; commits closed findings.
4. **Gate with CI, not discipline.** The loop's speed made overclaiming the real risk, so the
   guardrails moved into CI: a coverage test fails the build if any test file is silently skipped;
   a drift-checker fails it if prose claims a different test count than what collects; tag-bound
   claims pin every "validated" statement to a release.
5. **Prove live, keep the evidence.** Clean-AWS-account deploys of the platform and agents, with
   the deploy/invoke/prove logs retained as an evidence pack — the difference between "we believe"
   and "we ran it."

## The honesty system (the part that generalizes)

The most reusable artifact isn't code — it's the honesty machinery an AI-velocity project needs:

- **`MATURITY.yaml`** — machine-readable single source of truth for what is proven; prose defers
  to it, and a checker enforces the deference.
- **`NOT-CLAIMS.md` / `DO-NOT-CLAIM.md`** — the boundary written down before anyone is tempted.
- **Connector maturity tiers** — every integration labeled live / reference / stubbed, so "it
  integrates with X" always has a defined meaning.
- **Review documents in-repo** — the hostile passes are part of the deliverable, not internal.

## Why customers should care

- **It models the operating rhythm we're proposing.** Onboarding an agent to the platform *is*
  this loop: converse the requirements into a manifest, negative-test the policies, review
  adversarially, gate in CI, prove in a clean account.
- **It converts AI velocity into auditability** — the failure mode agencies fear most about AI
  development (confident, unverifiable output) is exactly what the gates eliminate.
- **It is reproducible by their teams.** Nothing in the loop requires a platform team of twenty —
  it requires the gates, and the gates are in the repo.

*Working note (internal): the ~30-iterations figure is the honest order of magnitude from the
build history; keep it qualitative in customer settings unless counting commits for a specific
agent. This document follows the customer-safe collateral track — neutral branding, plain-text
"Built on AWS."*
