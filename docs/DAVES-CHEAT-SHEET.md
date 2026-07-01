# Dave's Cheat Sheet — Aegis customer conversation

*Keep this open in the meeting. One screen. Full prep: [`CUSTOMER-PREP-AND-DEPLOY-PLAYBOOK.md`](CUSTOMER-PREP-AND-DEPLOY-PLAYBOOK.md).*

## The one-liner
> Aegis is the **governance layer that makes any AI agent deployable in a regulated environment** —
> build the paved road once on AWS, and every agent inherits identity, authorization, audit,
> compliance, hallucination control, and chargeback. **The agent isn't the product; the governance is.**

## Open with their pain (the pilot trap)
"You don't need another AI pilot. You need a governance substrate so you can approve **one** safe
pattern, then onboard agents one at a time with evidence your CISO, auditor, and program leaders can
defend." Then: the blocker was never the model — it's identity, authorization, audit, data isolation,
hallucination risk, cost control, and *who has authority to act*.

## The four CISO answers (say verbatim)
- **"Can the AI act on its own?"** No. Consequential actions are **withheld in code** and run only
  after a **bound, single-use, separation-of-duties** human approval. (Show Run 2 / 5 / 7.)
- **"Can I trust identity?"** Cryptographically verified JWT (RS256 vs JWKS, iss/aud/exp, alg-confusion
  guard); client-supplied roles are never trusted. (Run 4.)
- **"Will the audit hold up?"** Append-only DynamoDB + S3 Object Lock **WORM**; deletion proven denied.
  (Run 6.)
- **"Where does data go?"** In-account Bedrock over PrivateLink, mandatory Guardrails, masking fails
  closed. (Runs 1 / 3.)

## Proof — nine live AWS runs (deployed, exercised, torn down)
1 Governance core (KMS/audit/WORM/Guardrail/Cognito/gateway) · 2 Human gate holds the action ·
3 Cedar authz (Verified Permissions) ALLOW+2 DENY + real Bedrock · 4 Cognito MFA + JWT verify ·
5 Reviewer: role + SoD + single-use · 6 WORM delete denied · 7 API Gateway + JWT authorizer
(401 → authorized approve) · 8 KMS-signed manifests + atomic budgets (no oversell) ·
9 Governed connector: idempotency + saga rollback. **Evidence:** `DEPLOYED-AND-VALIDATED.md`.

## Two demos
- **Safe (always works):** `python demo/clean_account_acceptance.py` — 18/18 green, no AWS, no API key.
- **Real (2 min):** `infra/golden-pilot/run_authz_tests.sh` — live Cedar ALLOW/DENY on Verified Permissions.

## Objection handling
- *"Is it production-ready?"* → "It's a **live-validated** control platform, not yet an ATO'd product.
  Live connectors, ATO/GovRAMP, and third-party pen test are scoped engagement work — that candor is
  why the rest is credible." (Point to `docs/10-PRODUCTION-READINESS-RACI.md`.)
- *"Why not a model vendor's console?"* → "A console gives you none of this: least-privilege
  intersection, a human gate withheld in code, WORM audit, per-department chargeback, or a compliance
  pack that survives a review board."
- *"Lock-in?"* → "Customer-owned, readable, AWS-native implementation; no proprietary Aegis runtime."

## Per-persona leave-behind
CISO → `Aegis-CISO-One-Pager.docx` · CFO → `Aegis-ROI-Worksheet.xlsx` (edit to their numbers live) ·
Architect → `docs/02` + `docs/security/SECURITY-ARCHITECTURE.md` · Sponsor → `Aegis-Leadership-Status-Brief.docx`.

## The ask
A **fixed-scope, paid pilot** in their AWS account: one low-blast-radius workflow (IT service desk /
311 / HR helpdesk), synthetic data, ~2–4 weeks. Discovery → deploy governed golden path → prove one
outcome → sign the RACI → land-and-expand.

## Do NOT promise
An ATO/authorization · production PII/PHI/CJI in the pilot (synthetic only until security review; BAA
for healthcare) · a live third-party SaaS connector on day one (pattern is proven; their sandbox gets
wired in Phase 5) · a dashboard UI (evidence is via the audit tables / evidence report today).
