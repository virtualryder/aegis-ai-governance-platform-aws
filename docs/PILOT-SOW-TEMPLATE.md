# Aegis Governed-Agent Pilot — Statement of Work (TEMPLATE)

*Customer-facing. Fill the [bracketed] fields with the customer AE + solutions architect. This scopes
a fixed, low-risk pilot of the Aegis governed-agent platform in the customer's AWS account.*

---

**Customer:** [Customer / Agency name]  **Sponsor:** [name, title]  **Prepared by:** [your name]
**Date:** [YYYY-MM-DD]  **Pilot window:** [start] to [end] (target 2-4 weeks)
**AWS account:** [dedicated pilot account id]  **Region:** [us-east-1 | AWS GovCloud us-gov-west-1]
**Compliance pack:** [slg | education | healthcare-lifesciences | enterprise]

## 1. Objective
Prove, in the customer's own AWS account, that one **low-blast-radius** AI-agent workflow can run under
full governance — verified identity, deny-by-default authorization, a human gate for consequential
actions, masking, append-only + WORM audit, hallucination controls, and per-department cost
attribution — and measure it against one agreed outcome. This is a **governed pilot, not a production
authorization**.

## 2. Pilot use case
[e.g., IT service-desk assistant: read-only knowledge retrieval + draft ticket; ticket submission is
human-gated.] Chosen because it is **reversible, high-volume, decision-support, and has a clear ROI**.

## 3. Success criteria (acceptance)
- [ ] Governed golden path deployed; smoke test passes.
- [ ] Verified IdP login (MFA) issues a token whose role drives authorization.
- [ ] Authorized action ALLOWED; out-of-scope tool / wrong data class DENIED.
- [ ] Consequential action holds at the human gate; runs only after a supervisor approval; replay rejected.
- [ ] Every step produces an append-only audit record; evidence exported to WORM.
- [ ] Outcome metric measured: [e.g., >= X% deflection | >= Y% cycle-time reduction] on synthetic data.
- [ ] Per-department token spend visible + a hard cap enforced.
- [ ] Signed shared-responsibility (RACI) with no open blockers for the pilot scope.

## 4. Data policy
**Synthetic or representative data only** for the pilot. No production PII / PHI / FTI / CJI / student
data until the customer's security review clears it (and, for healthcare, a signed AWS BAA is in place).

## 5. Scope
**In scope:** governance core; one compliance pack; IdP federation + MFA; one agent; the reviewer
(human-approval) service; one **sandbox** connector to [system]; masking; token budgets/chargeback;
audit + WORM evidence; a deploy/teardown runbook and evidence package.
**Out of scope:** ATO / GovRAMP / FedRAMP authorization; independent penetration test; production data
or production system-of-record writes; multi-account/multi-tenant rollout; a custom operator dashboard
UI; additional agents beyond the one pilot workflow.

## 6. Architecture (summary)
Edge/WAF -> Cognito (federated IdP + MFA) -> API Gateway JWT authorizer -> governed MCP gateway
(deny-by-default Cedar / Verified Permissions, human gate, token budgets, append-only audit) ->
Amazon Bedrock + Guardrails -> KMS-encrypted data + S3 Object Lock WORM -> sandbox connector with
idempotency + saga rollback. Full detail: `docs/02-REFERENCE-ARCHITECTURE.md`.

## 7. Timeline & workstreams
| Phase | Days | Owner |
|---|---|---|
| 0 Discovery & architecture workshop | [0.5-1] | Joint |
| 1 Account prerequisites (role, Bedrock, region) | [0.5] | Customer + delivery |
| 2 Governance core deploy + smoke test | [0.5] | Delivery |
| 3 IdP federation + MFA + authorizer | [0.5] | Joint |
| 4 Pilot agent + reviewer service | [0.5] | Delivery |
| 5 Sandbox connector (idempotency + rollback) | [1-3] | Joint |
| 6 Outcome run + FinOps (budgets/chargeback) | [1-2] | Delivery |
| 7 Evidence package + security review | [parallel] | Joint |
| 8 Readout + promote/teardown decision | [0.5] | Joint |

## 8. Staffing
**Delivery:** [1 solutions architect + 1 engineer]. **Customer:** a business owner + approver for the
workflow, an IdP admin, an AWS account admin, and a security reviewer.

## 9. Prerequisites from the customer
Dedicated pilot AWS account + a deployment IAM role; Bedrock model access enabled; IdP federation
metadata; a sandbox instance of [system]; synthetic/representative data; named owner + approver.

## 10. Cost
**AWS infrastructure:** ~$[low — serverless, pay-per-use; torn down when idle] for the pilot window.
**Professional services:** $[fixed pilot fee]. **Platform license:** [waived for pilot | $X]. Figures
are placeholders to be set commercially; see `docs/12-COMMERCIAL-PACKAGING.md`.

## 11. Exit criteria & production-conversion path
At readout, either (a) **tear down** cleanly (zero residual resources) if it was a time-boxed proof, or
(b) **convert to production**: begin the customer-owned ATO/GovRAMP path (or AWS BAA for healthcare),
move the reference gateway to AgentCore Gateway/Policy, and land the next agent on the same governed
road (land-and-expand).

## 12. Assumptions & limitations
Aegis is a **live-validated reference platform, not an AWS-authorized/ATO'd product**. The pilot
demonstrates the control plane and the one workflow; authorization, third-party testing, and
production data are subsequent, customer-owned steps. See `docs/10-PRODUCTION-READINESS-RACI.md`.

**Signatures:** Customer [____________ / date]   Delivery [____________ / date]
