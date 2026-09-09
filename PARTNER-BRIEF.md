# Aegis — Partner Brief

*Prepared 2026-09-08. Every figure here is traceable to a file or a run in these repositories.
Where something has not been proven, this document says so in the same sentence as the claim.*

---

## 1. The one-paragraph version

Aegis is a **deny-by-default governance control plane for LLM agents on AWS**. It puts Cedar
authorization, PII masking proven by signature, per-tenant cost ceilings, a kill switch, and a WORM
audit ledger *in front of* the model rather than inside the prompt — so the governance cannot be
talked out of by the agent it governs. It has been deployed from zero and torn down repeatedly on a
real AWS account, most recently passing a 15-check full-portfolio gate with a live AgentCore Runtime.

**It is a reference architecture, not a product.** There is no SLA, no support contract, no managed
release train. And every piece of evidence in it was produced by its author on the author's own
account — which the repository names, in its own words, as *"the single biggest credibility gap in
the project."*

**That gap is the reason to talk to a partner, and it is the specific thing we are asking a partner
to close.**

---

## 2. What is actually proven

One tree — `benefits_eligibility_agent` at tag `v0.6.0-pilot-rc1` — passed a **15/15 full-portfolio
gate on 2026-09-07**, from an empty environment, with two tenants and a real AgentCore Runtime, then
tore down. Evidence: `evidence/FULL-PORTFOLIO-GATE-2026-09-07.json`.

| Proven live | What it demonstrates |
|---|---|
| Cedar ENFORCE at the AgentCore Gateway | A missing or malformed entitlement claim grants **zero** tools, not all of them |
| Signed `sanitized_ref` | Masking is proven cryptographically; a caller-supplied `deidentified: true` is refused |
| Pass-by-reference | Raw case text never crosses workflow state |
| Human sign-off | `waitForTaskToken`; approver identity re-verified; approver ≠ requester |
| Kill switch | One SSM parameter halts the governed path everywhere; engage/disengage is IAM-attributed and WORM-audited |
| Per-tenant budget | Reserve-before / commit-after on every model call; refuses **before** the spend at runtime, gateway and drafter |
| Unified lineage | CloudTrail invocations reconciled against audit lines in both directions |
| Runtime on IaC role | Least-privilege execution role from CDK, never the toolkit's auto-generated one; IMDSv2 required |
| Guardrail enforcement | IAM requires the exact guardrail ARN — a call without it is denied, not merely unguarded |
| Teardown | Zero CloudFormation stack residue; account model-logging restored |

Supporting the above: ~400 offline tests per pack, five **blocking** CI security gates
(bandit, detect-secrets, checkov, CodeQL, trivy), and a cross-repo parity workflow that runs daily
and proves its own fallibility on every execution.

---

## 3. What is not proven — read this before any customer conversation

These are not hedges. Each one is a specific thing a customer's auditor will ask about.

1. **All evidence is author-produced on one AWS account.** The repo ships
   `docs/INDEPENDENT-VERIFICATION.md` precisely because an earlier reviewer discounted the evidence
   on those grounds. No third party has run it.
2. **`main` is 23 commits and 53 files ahead of the gated tag**, including 18 files under
   `scripts/`, `lib/` and `cdk/`. The 15/15 result describes the tag. It does not describe today's
   tree.
3. **No real system of record has ever been governed.** The only external connector
   (`verify_income`) is deliberately not deployed and is not a Gateway target. Every live run
   governed tools over **synthetic data**.
4. **Evidence immutability has never been tested in the mode an auditor requires.** Every gate ran
   S3 Object Lock in **GOVERNANCE** mode with 1-day retention so the environment could be torn down;
   teardown itself uses `BypassGovernanceRetention`. **COMPLIANCE** mode (7-year) is IaC only.
5. **One of four packs is live-proven.** Pharmacovigilance and financial-aid wire every control but
   are offline-gated only; housing wires **3 of 17** and has never had an AgentCore-era live gate.
6. **Account-wide prevention is incomplete.** There is no AWS Organization, so no SCP. A
   non-governed principal calling Bedrock directly is **detected**, not prevented. (An account-level
   enforced guardrail — which needs no Organization — is available and deliberately not applied.)
7. **488 checkov findings are baselined** across the portfolio: Lambda concurrency limits, DLQs, VPC
   attachment, log-group and env KMS, DynamoDB CMK and PITR.
8. **No penetration test, DR exercise, or SLO** has been run.
9. **Policy provenance** in the audit record landed 2026-09-08 and is still
   **configuration-asserted only** — no live deployment has yet written a row carrying it.
10. **Gateway-only runtime invocation (RT-4) was tested live on 2026-09-09 and reverted to
    opt-in.** It works — and in this topology it leaves the agent with no permitted invoker, because
    the only allowed workload type is an AgentCore Gateway and the gateway sits *downstream* of the
    runtime. Four gate checks failed on `Transaction token required`. R4-2 is mitigated where it
    actually bites: at the gateway, by the Cedar `mask_before_*` policies, which forbid the
    consequential tool actions unless the payload is de-identified, whoever makes the call. The
    restriction remains available (`RT4_GATEWAY_ONLY=1`) for a deployment where the runtime *is* a
    gateway target; that posture is unit-tested, not live-proven.

---

## 4. Does it satisfy an auditor?

`benefits_eligibility_agent/docs/AUDIT-READINESS.md` is a real control-to-evidence matrix mapping
obligations (due process, confidentiality, de-identification, separation of duties, encryption,
audit immutability) to the specific test or log that demonstrates each.

**Honest read: the control *design* is audit-grade. The control *evidence* is not yet.**

| An auditor asks | Today |
|---|---|
| Is every consequential action recorded? | Yes — append-only ledger, hash chain, written before the side effect |
| Can the record be altered? | IAM Deny on update/delete and on Object-Lock bypass — **but proven only in GOVERNANCE mode** |
| Can you prove completeness of capture? | Within the governed path, yes. Account-wide, detective only (no SCP) |
| Who approved this action, and were they distinct from the requester? | Yes — identity re-verified at sign-off |
| Which policy version decided this case? | **Only as of 2026-09-08, and not yet in a live run** |
| Was PII removed before the model saw it? | Yes, proven by signature rather than asserted |
| Who verified all this? | **The author. That is the gap.** |

---

## 5. Recommended positioning with the partner

**Do not position this as a product, a solution, or something a customer can deploy against
regulated data.** It is none of those, and a partner SA will find that out in an hour.

**Position it as: a governance control plane that is further along than anything they will have
built themselves, with a named list of what remains and a protocol for verifying it.**

The specific ask:

> *"We have a deny-by-default governance layer for Bedrock agents that has been live-gated end to
> end on our own account. All of the evidence is ours, which means none of it counts. We want your
> SA to run the independent verification protocol in a clean account — it is scripted, it takes
> about half a day, and it either reproduces our results or it does not. If it reproduces, we have
> joint evidence and a concrete list of the five things that stand between it and a customer pilot.
> If it does not, you have saved us both a customer conversation."*

That ask is credible because it is falsifiable, cheap for the partner, and converts our weakest
point into their contribution.

**What to say it is good for today:** architecture workshops, a CISO/AO conversation about what
governed agent access *should* look like, and a supervised pilot on synthetic or de-identified data.

**What to say it is not ready for:** production, real regulated data, or any claim of account-wide
non-bypassable governance.

---

## 6. The path to a customer pilot

**Before the partner meeting (days, not weeks):**

| # | Item | Why it matters in that meeting |
|---|---|---|
| 1 | Re-gate `main` and cut a tag the evidence describes | The first technical question will be "is what you're showing me the thing you tested?" |
| 2 | One COMPLIANCE-mode Object Lock deployment in a throwaway account (EV-1) | This is the auditor's question; it is cheap and it is currently unanswered |
| 3 | This brief + the architecture diagram | Both attached |

**Before a customer pilot (the joint work programme):**

| # | Item | Owner |
|---|---|---|
| 4 | **Independent verification run by the partner's SA** in a clean account | Partner — this is the headline deliverable |
| 5 | One **real read-only system-of-record** connector governed end to end | Joint |
| 6 | Live re-gate of the remaining packs; housing uplift from 3/17 | Us |
| 7 | AWS **Organization + SCP** perimeter, or an explicit compensating-control statement the customer's AO will accept | Customer/partner account team |
| 8 | Checkov burn-down from 488 to a justified residual | Us |
| 9 | Penetration test, DR exercise, SLO and incident-response runbook walkthrough | Partner/customer |
| 10 | MFA + enterprise IdP federation re-proven on the current tree | Us |

**The honest framing of that table:** items 1–3 are ours and are days of work. Item 4 is the one
that changes the credibility of everything else, and only a partner can do it. Items 5–10 are a
genuine engagement, not a checklist — which is the point of bringing a partner in.

---

## 7. Attached

- `docs/AEGIS-ARCHITECTURE-VERIFIED-2026-09-08.drawio` — as-deployed architecture. Line style
  encodes verification status: solid = live-verified in the 15/15 gate, dashed = IaC-asserted only,
  dotted = not deployed. The footer restates what the diagram does not claim.
- `docs/PACK-PARITY.md` — which controls each pack actually wires, generated from their sources.
- `docs/GAP-CLOSURE-BACKLOG.md` — 59 recorded findings with what each invalidated.
- `NOT-CLAIMS.md` — the honesty boundary. If any wording anywhere reads as stronger, that page governs.
