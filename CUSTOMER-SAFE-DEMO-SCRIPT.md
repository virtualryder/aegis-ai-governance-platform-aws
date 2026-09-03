# Customer-Safe Demo Script

*A repeatable 15–20 minute demo an AWS SA or the field can run for a customer, using only synthetic
data and neutral branding. It shows the governance controls firing live — the thing customers actually
need to believe. No API keys, no PHI/PII, no AWS account required for the offline portion.*

> **Branding:** use the customer-safe public track — plain-text "Built on AWS", no AWS logo, no claim
> of AWS endorsement. See `BRAND-AND-TRADEMARK.md`. Everything below uses synthetic fixtures.

---

## Setup (2 min)
```bash
cd hcls-ai-agents            # or slg-ai-agents / healthcare_ai_agents / edu-ai-agents
pip install -e platform_core && pip install langgraph
```
Say: *"This runs entirely offline on synthetic data. What you're about to see is not a chatbot demo —
it's the governance layer that lets an agent touch a regulated workflow safely."*

## Act 1 — the happy path, governed (4 min)
```bash
make demo                    # or: cd 02-pharmacovigilance-agent && python demo/... (per repo)
```
Narrate the flow as it prints: **verified identity → deny-by-default gateway → least-privilege
intersection → the agent drafts → the consequential action pauses at the human gate → a reviewer
approves with a bound, single-use token → the action commits → an immutable audit record is written,
with PHI/PII masked.** Point out: *"the agent never had authority the human didn't; the write could
not happen without a bound approval; every step is on an append-only ledger."*

## Act 2 — the controls refuse bad behavior (6 min) — the money slide
```bash
make neg-demo                # 10 negative controls; all should REFUSE
```
Call out each refusal as it fires:
1. **Unauthenticated call** → denied.
2. **`alg:none` / forged token** → rejected (identity is verified, not trusted).
3. **Wrong role** → denied by least-privilege intersection.
4. **Unregistered tool** → deny-by-default.
5. **Self-approval** → separation-of-duties violation.
6. **Replayed approval** → single-use, rejected.
7. **Tampered arguments** → approval is bound to the exact args.
8. **Masking failure** → fails closed (redacts, doesn't leak).
9. **Audit-write failure** → fails closed (denies, doesn't proceed).
10. **Token-budget exceeded** → denied before spend.

Say: *"This is what 'governed' means. Each of these is the exact failure a CISO or regulator worries
about, and each one fails safe."*

## Act 3 — it's real infrastructure, and honest (4 min)
- Show `MATURITY.yaml` + run `python tools/check_maturity.py` → *"the maturity claims are machine-checked; they can't drift from reality."*
- Open a golden-path `template.yaml` → *"cfn-lint-clean SAM: private VPC, PrivateLink to Bedrock, Cognito authorizer, WORM audit. One command to deploy, one to tear down."*
- Open `DO-NOT-CLAIM.md` → *"here's what we will not claim — no ATO, no HITRUST, the AI is deterministic by default, connectors are tier-3 reads. We lead with what's proven."*

## Optional Act 4 — live on AWS (customer account, +10 min)
```bash
cd infra/golden-path-01-revenue-cycle && ./deploy.sh && ./acceptance_test.sh && ./destroy.sh
```
Watch the acceptance test prove ALLOW / PENDING / bypass-blocked / SoD / replay / tamper against real
Cognito + Step Functions + DynamoDB, then tear down. Cost is < a few dollars (see `AWS-RUN-COST.md`).

## Close (1 min)
*"The pattern is the same across public sector, healthcare, life sciences, and education. Pick one
low-blast-radius workflow — pharmacovigilance intake, 311, denial drafting, student concierge — and we
run a scoped pilot on synthetic or de-identified data with these controls on, then expand once you
trust it."*

## Do / Don't
- **Do** lead with the negative demo (Act 2) — it's the most persuasive.
- **Do** stay on synthetic data and neutral branding.
- **Don't** imply the agents are deeply reasoning AI — the story is *governed workflows*.
- **Don't** claim AWS endorsement, ATO, HITRUST, or a live production connector.
