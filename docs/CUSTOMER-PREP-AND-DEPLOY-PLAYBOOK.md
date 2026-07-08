# Customer Prep & Deploy Playbook

*How to prepare for a customer conversation and deploy a governed pilot with them, step by step, with
the reasoning behind each step. Fast in-room version: [`DAVES-CHEAT-SHEET.md`](DAVES-CHEAT-SHEET.md).
Proof log: [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md). Honesty/RACI:
[`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).*

> **Frame everything honestly:** Aegis is a **live-validated reference platform, not an authorized
> product.** Pilots run on **synthetic data** until the customer's security review clears production
> data (and, for healthcare, a signed AWS BAA). Say this out loud early — the candor is what makes the
> rest of the claims believable.

## Part A — Prep for the conversation

### A1. Qualify before you book the room
Get three facts: (a) a real, painful, **low-blast-radius** workflow (IT service desk, resident/311, HR
helpdesk — reversible, high-volume, clear ROI); (b) their industry -> the compliance pack
(`packs/slg | education | healthcare-lifesciences | enterprise`); (c) their IdP (Entra / Okta /
PingFederate / Login.gov). **Why:** the pitch only lands if slide one names *their* workflow and *their*
regime. Never lead with benefits adjudication, public safety, treatment, or records release.

### A2. Tailor the deck (don't present all 24 slides)
Exec core (slides 1-10) + the **"Proven on AWS — nine live runs"** slide + Appendix A (CISO/architect).
Swap the vertical example to theirs. **Why:** a 30-minute exec meeting needs ~12 slides; the proof
slide is what separates you from vendors who only have a diagram.

### A3. Leave-behinds by persona (all already in the repo)
- **CISO** -> `Aegis-CISO-One-Pager.docx` + `docs/security/THREAT-MODEL.md` + `10-PRODUCTION-READINESS-RACI.md`
- **CFO** -> `Aegis-ROI-Worksheet.xlsx` (edit inputs to their volumes live)
- **Architect** -> `docs/02-REFERENCE-ARCHITECTURE.md` + `docs/security/SECURITY-ARCHITECTURE.md`
- **CEO / sponsor** -> `DEPLOYED-AND-VALIDATED.md` (the nine runs)
- **The skeptic** -> `DEPLOYED-AND-VALIDATED.md` (the nine runs)

### A4. Rehearse two demos
- **Laptop demo (cannot fail):** `python demo/clean_account_acceptance.py` — 18/18 green, no AWS/API key.
- **Live proof (2 min):** `infra/golden-pilot/run_authz_tests.sh` — Cedar ALLOW/DENY on Verified Permissions.
**Why:** the laptop demo removes demo-gods risk; the live run answers "is this real?" on the spot.

### A5. Pre-load the four CISO answers
Verbatim in `docs/08-GTM-AND-POSITIONING.md` §5 and on the cheat sheet. The room-winner: *"Can the AI
act on its own? No — consequential actions are withheld in code and proven absent by a test."*

### Meeting flow (60-90 min)
Pilot trap (5) -> the insight: governance is the product (5) -> what it is, 5 layers (5) -> live proof
+ reproduce one run (10) -> their workflow mapped to a golden path (10) -> compliance pack + CISO Q&A
(15) -> ROI worksheet with their numbers (10) -> the ask: a fixed-scope paid pilot (10).

## Part B — Deploying WITH the customer, step by step (and why)

A land-and-expand pilot **in the customer's own AWS account**, synthetic data first. Each phase maps
to repo artifacts so nothing is hand-waved.

**Phase 0 — Discovery & architecture workshop (0.5-1 day).** Map their IdP, data classes, the one
workflow, and the success metric; select the compliance pack. **Why:** the pack drives regions, KMS
topology, retention, and masking sets — getting it wrong restarts security review. *Output:* a filled
scope + a signed [`PILOT-SOW-TEMPLATE.md`](PILOT-SOW-TEMPLATE.md).

**Phase 1 — Prerequisites in their account (0.5 day).** Confirm region (commercial vs GovCloud),
enable Bedrock model access, provision a **deployment IAM role** (not a human admin), pick a dedicated
pilot account (ideally under Control Tower). **Why:** a scoped role + isolated account is the first
thing their security team checks, and it keeps the pilot cleanly removable.

**Phase 2 — Governance core (30 min).** `infra/scripts/deploy.sh` -> `governance-core.yaml`, then
`smoke_test.sh`. Stands up KMS CMK per data class, append-only audit, S3 WORM, Bedrock Guardrail,
Cognito, the fail-closed gateway. **Why:** the paved road every future agent inherits — identity /
audit / masking / guardrails built once. This reproduces Run 1 (proven), not an experiment.

**Phase 3 — Real identity (0.5 day).** Federate their IdP into Cognito, enforce MFA, map their groups
to roles (`infra/golden-pilot/role_map.json`), stand up the API Gateway + JWT authorizer. **Why:**
"client-supplied roles are never trusted" becomes true only when their real directory drives the Cedar
context (Runs 4 + 7).

**Phase 4 — Golden-pilot agent (0.5 day).** Deploy `sample-agent.yaml` or scaffold theirs with
`tools/add_agent.py`; attach the pack; wire the **reviewer service** for the one consequential action.
**Why:** proves human gate + deny-by-default + audit on *their* workflow (Runs 2 + 3 + 5).

**Phase 5 — One real system of record, in a sandbox (1-3 days — the long pole).** Register their
ServiceNow / CRM / 311 sandbox as a gateway tool with **idempotency + rollback** (Run 9 pattern),
credentials in Secrets Manager. Read + draft first; the write is human-gated. **Why:** this is the
single biggest line item and what turns a demo into a pilot — everything else is fast because it is
already built.

**Phase 6 — Prove the outcome + turn on FinOps (1-2 days).** Run the workflow on synthetic data
against the success metric; switch on the **application inference profile + token budgets** so spend is
attributed and capped (Run 8). **Why:** the CFO funds expansion only when they see per-department cost
and an outcome number — this is where the ROI worksheet becomes their real data.

**Phase 7 — Evidence package + security review (parallel).** Produce the run log +
`docs/security/COMPLIANCE-EVIDENCE-INDEX.md` (controls -> NIST 800-53 -> evidence) and hand the CISO
the threat model + pen-test scope. **Why:** you sign the shared-responsibility RACI here — the gate to
production data.

**Phase 8 — Promote or tear down.** Time-boxed PoV -> `teardown.sh` leaves zero residue (proven nine
times). Funding production -> begin the **customer-owned** ATO/GovRAMP path (or AWS BAA for
healthcare), move the reference gateway to AgentCore Gateway/Policy, and land agent #2 on the same
road. **Why:** land-and-expand — every new agent is days, not a project, and each is sellable as an
add-on.

## Ground rules (state and hold)
Synthetic data until security review + (healthcare) a signed BAA · costs are pennies in pilot, torn
down when idle · you promise a **governed pilot, not an authorization** · the connector is a stand-in
until their sandbox is wired.

## What you need FROM them
A pilot AWS account + deployment role · Bedrock model access enabled · IdP federation metadata · a
**sandbox** instance of the target system · synthetic/representative data · a named business owner +
approver for the workflow.

## Artifact map (what to open at each step)
| Step | Repo artifact |
|---|---|
| Qualify / pack | `packs/*/pack.yaml`, `docs/03-COMPLIANCE-OVERLAY-PACKS.md` |
| Deck / talk track | `Aegis-Master-Deck.pptx`, `docs/08-GTM-AND-POSITIONING.md`, `DAVES-CHEAT-SHEET.md` |
| Deploy core | `infra/cloudformation/governance-core.yaml`, `infra/scripts/{deploy,smoke_test,teardown}.sh` |
| Identity | `infra/golden-pilot/cognito-identity.yaml`, `reviewer-api.yaml`, `verify_jwt.py`, `role_map.json` |
| Agent + gate | `infra/cloudformation/sample-agent.yaml`, `tools/add_agent.py`, `infra/golden-pilot/reviewer-service.yaml` |
| Connector | `infra/golden-pilot/connector-pilot.yaml` |
| FinOps | `docs/05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`, `platform_core/prod/` |
| Evidence / security | `DEPLOYED-AND-VALIDATED.md`, `docs/security/`, `docs/ops/` |
| Commercials | `docs/12-COMMERCIAL-PACKAGING.md`, `Aegis-ROI-Worksheet.xlsx`, `PILOT-SOW-TEMPLATE.md` |

## Audience note
`DAVES-CHEAT-SHEET.md` and this playbook are **internal (Dave / AE)** — they contain talk tracks and
"do not promise" lines. Customer-facing artifacts are the **Pilot SOW**, CISO one-pager, leadership
brief, ROI worksheet, and the architecture/security docs.
