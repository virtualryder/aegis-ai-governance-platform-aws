# Gateway modes — portable (validated default) vs. managed AgentCore

*Which MCP/tool-authorization gateway to deploy, stated precisely so a reviewer isn't misled. The
governed decision/least-privilege/token/audit semantics are identical across modes; what differs is
the AWS service that hosts them. Reference accelerator — see `NOT-CLAIMS.md`.*

## The two modes

| Mode | What it is | Status here |
|---|---|---|
| **Portable — API Gateway + Cognito JWT authorizer** | An API Gateway (HTTP/REST) with a Cognito/JWT (or IAM/SigV4) authorizer in front of the connector Lambdas; the deny-by-default policy, scoped tokens, approvals, and audit run in the Lambda control plane. | **The validated, supported default.** This is the path that was deployed and exercised in a clean account. Use it for pilots. |
| **Managed — Amazon Bedrock AgentCore Gateway + Identity** | AWS-managed gateway that maps each tool to an AgentCore Gateway *target* with AgentCore Identity for inbound/outbound auth. | **Optional / customer-specific, experimental here.** The reference registration ships (`infra/.../agentcore-gateway.yaml`) but the managed path is **not** presented as validated until it has the same clean-account evidence as the portable path. |

**Say it this way:** *"Portable API Gateway + Cognito JWT is the validated default; the managed
AgentCore path is optional and customer-specific unless separately evidenced."*

## Inbound authorization (who is calling)

- **Supported:** a verified **JWT** (Cognito / federated IdP) **or IAM** (SigV4). Identity is taken only
  from the verified authorizer claim, never from the request body.
- **AWS caution — `AUTHENTICATE_ONLY` only authenticates; it does NOT enforce authorization policies.**
  Authenticating a caller is not authorizing an action. This gateway **always authorizes**
  (deny-by-default, least-privilege intersection) *after* authentication — proven by the 12-case
  `test_mcp_authz_matrix.py`.
- **"No Authorization" is development/testing only and must never be used in production.** AWS says
  the same for AgentCore. There is no un-gated path to a system of record here.

## Outbound authorization (what the gateway presents to the system of record)

- **Supported patterns:** IAM, the caller's IAM credentials, **OAuth grants, token exchange /
  on-behalf-of**, token passthrough, and API keys. This gateway mints a **short-lived, per-call,
  tool-scoped credential** (the offline analog of AgentCore Identity / STS); the connector presents it
  to the system of record — no standing service account.
- **"No authorization" outbound is less secure and not recommended** (AWS). This gateway does not offer
  an un-credentialed outbound path — the negative-test matrix proves a call without a valid scoped
  credential is refused (case #11).

## Side-effect ordering (durable intent / outbox) — both modes

A governed gateway must never (a) run a side effect without a durable record that it was authorized,
or (b) answer **DENY** for an action that already happened — a caller that hears "no" retries, and a
real-world action happens twice. Copilot's 2026-09-03 review found exactly (b) in the reference engine
(`platform_core/gateway.py`: consume approval → execute → audit → DENY on audit failure). The order is now:

| Step | Reference engine (`platform_core/gateway.py`) | AgentCore packs (governed-core, benefits) |
|---|---|---|
| 1. Authorized intent, durable **before** anything | `INTENT` row (request, agent, tool, args hash, purpose, approval id, **idempotency key**); write fails ⇒ `DENY` (nothing consumed, nothing run — a retry is safe) | Step Functions `AuditIntent` state → `write_audit` writes the `INTENT` evidence record before `HumanSignoff` (`benefits cdk/ben_stacks/workflow_stack.py`) |
| 2. Consume the bound single-use approval | `approval_ledger.consume()` (agent, tool, args hash, purpose) | `approve_signoff` consumes; `finalize_signoff` re-verifies the approval **path** (G2) |
| 3. Execute with the idempotency key | the connector receives `idempotency_key=`; the gateway keeps an outbox of completed keys and **refuses a replay** (`already_completed=True`) — never executes twice | `finalize_signoff._exactly_once_marker`: conditional `FINAL#<case>` put **before** the commit record; a repeat returns the original submission (`idempotent: true`) |
| 4. Completion, durable | `ALLOW`/`ERROR` row with the same key; write fails ⇒ **`INDETERMINATE`** (`reconciliation_required`), never `DENY` | `COMMITTED` record; write fails ⇒ `committed:false` with the `FINAL#` marker in place (the workflow's `FinalizeOk` routes it to `ManualReview`); a retry is idempotent |

Proof: `demo/test_outbox.py` (intent-write failure ⇒ handler not called + approval not consumed;
completion-write failure ⇒ `INDETERMINATE` + one execution + replay refused; the key on both rows; an
unregistered consequential tool no longer burns the approval). The connector contract — accept
`idempotency_key` — is the governed-connector rule in `infra/golden-pilot/CONNECTOR-PILOT.md`.

## What is actually evidenced

- **Portable path:** deployed + exercised in a clean account (identity → deny-by-default → scoped token
  → connector → bound approval → append-only audit). See `evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`.
- **AgentCore path:** reference registration only; mark experimental until it carries the same evidence.

> Do not present the managed AgentCore path as production-validated unless the runtime evidence
> (`RUNTIME-EVIDENCE-RUNBOOK.md`) has been captured for it specifically.
