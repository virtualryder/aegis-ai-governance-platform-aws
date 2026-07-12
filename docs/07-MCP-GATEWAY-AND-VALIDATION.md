# 07 — MCP Gateway, Tool Registration & Validation/Invalidation

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> How agents reach tools, how every tool is registered and validated before any agent may use it, and
> how a compromised or deprecated tool is revoked platform-wide. The gateway is the single secure
> endpoint through which every tool call flows. Grounded in [`../SOURCES.md`](../SOURCES.md) §1.
> Controls are marked **[Impl]** = platform-implemented or **[Cfg]** = customer-configured.

## 1. The gateway — one secure tool endpoint

On AWS this is **Amazon Bedrock AgentCore Gateway** (GA 2025-10-13). AgentCore Gateway connects
agents to existing **Model Context Protocol (MCP)** servers and turns **APIs and Lambda functions
into agent tools**, with **IAM and OAuth** authorization, exposed as **one secure tool endpoint**.
**AgentCore Identity** adds identity-aware authorization and a secure token vault, and all AgentCore
services support **VPC, AWS PrivateLink, CloudFormation, and resource tagging**.

In Aegis the gateway is also the **authorization control plane** described in
[`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) §3: every model call, tool call, and
retrieval is brokered here. An agent never holds a long-lived credential to a downstream system and
never talks to an MCP server directly — it asks the gateway, which decides, mints a scoped token, and
records the attempt. The repo ships a readable policy engine you can run and test offline; in
production you deploy AgentCore Gateway (or API Gateway + a Cedar/OPA authorizer) so the analog is the
tested artifact, not just the model. **[Impl gateway logic / Cfg AgentCore deployment]**

## 2. The tool registry — nothing is reachable until it is registered

**Every MCP server and every tool is registered in the gateway tool registry — with scopes and
validation rules — before any agent may reference it.** An agent manifest can only grant tools by
their registered `id` (e.g. `accela.read_permit`, `kb.search_policy`); CI rejects an agent that
references an unregistered tool, just as it rejects one that exceeds its declared scope (see
[`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md) §2). The registry is the
allow-list: if it is not in the registry, it does not exist to any agent. **[Impl]**

Each registry entry records, at minimum:

| Field | Purpose |
|---|---|
| `id` | The stable tool identifier agents grant against |
| `server` | The MCP server / API / Lambda backing the tool |
| `scopes` | The discrete capabilities (e.g. `read`, `write`, `issue`) the tool exposes |
| `schema` | The input/output contract the gateway validates calls against |
| `auth` | IAM role or OAuth scope used to reach the backend |
| `data_classes` | Which data classes (CJI/FTI/PHI/EDU/public) the tool may touch |
| `provenance` | Publisher + signature / image digest of the tool definition |
| `status` | `active`, `deprecated`, or `revoked` (drives fail-closed behavior) |

## 3. Tool validation — what must pass before a tool goes `active`

A tool is admitted to the registry only after it clears validation. These are gates, not guidelines:

1. **Schema / contract validation.** The tool publishes a typed input/output schema; the gateway
   validates every call's arguments and the tool's response against it. Malformed or out-of-contract
   calls are rejected before they reach the backend. **[Impl]**
2. **Scope declaration.** Every capability the tool exposes is declared as a discrete scope. A tool
   that can both read and write declares both; an agent must grant each scope explicitly. There is no
   implicit "all access." **[Impl]**
3. **Allow-listing.** Only registered servers/tools are reachable. The gateway operates
   **deny-by-default** — an unknown tool id, an unknown server, or an undeclared scope is denied. **[Impl]**
4. **Signature / provenance.** The tool definition (and, for packaged tools, its image/artifact) is
   signed by a known publisher; the gateway verifies provenance at registration and at load, the same
   way it verifies a signed agent manifest. **[Impl/Cfg publisher trust]**
5. **Data-class compatibility.** The tool's declared `data_classes` must be compatible with the
   environment's active packs and the agent's classification; a tool that touches PHI cannot be used
   by an agent or in an environment not cleared for PHI. **[Impl]**

## 4. Per-call scoped token minting

When the gateway permits a call, it computes `permitted ⇔ agent grant ∩ user entitlement`
(least-privilege as an *intersection* — the agent can never exceed the human it acts for) and then
mints a **scoped, per-call token** for exactly that tool and scope. The token is **short-lived and
single-use**; it is never a long-lived credential and never broader than the one call. This is
AgentCore Identity's identity-aware authorization and token vault in production. The result: even a
fully compromised agent process holds no standing credential to any backend — only momentary,
narrowly-scoped tokens the gateway chose to issue. **[Impl]**

## 5. Invalidation & revocation — failing closed on a bad tool

The flip side of registration is revocation. When a tool or MCP server is **compromised,
mis-behaving, or deprecated**, it must be removable platform-wide in one action:

- **Status flip to `revoked`.** Setting a registry entry to `revoked` (or `deprecated`) takes effect
  at the gateway immediately. Because every call is brokered, no agent can route around it — the next
  call to that tool is denied regardless of what any agent manifest grants. **[Impl]**
- **Token revocation.** Outstanding scoped tokens for the revoked tool/server are invalidated via the
  AgentCore Identity token vault, so in-flight or cached tokens stop working. **[Impl/Cfg]**
- **Deny-listing.** A revoked server/tool is added to an explicit deny-list that overrides any
  allow-list grant, so a stale manifest cannot resurrect it. **[Impl]**
- **Fail closed.** If the gateway cannot verify a tool's provenance, validate its schema, or reach its
  authorization decision, it **denies rather than allows**. Unavailability is treated as "deny," never
  "allow." **[Impl]**
- **Audit.** Every revocation, every subsequent denied call, and the reason are written to the
  append-only audit, so revocation itself is evidence (see
  [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) §6). **[Impl]**

Because revocation is enforced at the single broker rather than in each agent, the **blast radius of a
compromised tool is one registry flip**, not a hunt across every agent that might reference it.

## 6. Onboarding a new tool or MCP server

New tools follow the same one-at-a-time discipline as agents (see
[`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md) §3). New MCP servers/tools are
registered in the gateway tool registry **with their scopes and validation rules before any agent may
reference them.**

```
Author tool definition (schema + scopes + data classes + provenance)
  → Register in gateway tool registry (status: candidate)
  → Validate: schema · scope declaration · allow-list · signature/provenance · data-class compat
  → Wire backend auth (IAM role / OAuth scope) + secure token vault
  → Promote to status: active
  → Agents may now grant the tool by id in their manifests (CI enforces declared scope)
  → Day-2: deprecate or revoke via status flip; tokens revoked; deny-list updated; audited
```

New **models** onboard analogously: registered, given an inference profile + guardrail policy, and
referenced by profile ARN — so adding or swapping a model is a config change, not a re-architecture.

## 7. Who cares & why

- **CISO:** every tool is allow-listed, schema-validated, scope-declared, and signed; agents hold no
  standing credentials, only per-call scoped tokens; a compromised tool is revoked platform-wide in
  one action and the gateway fails closed. NIST 800-53 AC-3, AC-6, AU-2; supply-chain provenance.
- **Architect:** one broker, one registry, one validation pipeline — tools are inherited and governed,
  not integrated ad hoc per agent.
- **ISV / department building a tool:** a single, published contract (schema + scopes + provenance) to
  build toward; clearing it makes the tool usable by any agent in any Aegis environment.
- **CIO:** tool sprawl becomes a managed, revocable inventory instead of a credential-leak surface.

## 8. Honest limits

**Update (Run 10, 2026-07-07):** the portable MCP gateway pattern is now live-validated end-to-end —
`infra/golden-pilot/mcp-gateway.yaml` deploys an API Gateway HTTP API (`POST /mcp`) with a Cognito
JWT authorizer in front of a Lambda MCP JSON-RPC 2.0 server (deny-by-default tool allow-list,
a human-approval gate that now **validates the consequential-tool `approval_id` against the
reviewer-service ledger with an atomic single-use consume bound to the calling identity**
(`requester == sub`) — an arbitrary, replayed, expired, or unbound string is denied, and the gate
fails closed if no ledger is wired, so it is no longer presence-only — fail-closed masking,
append-only audit with IAM-level Update/Delete deny). All allow and deny paths were exercised live
over HTTPS; see
`DEPLOYED-AND-VALIDATED.md` Run 10.

**Update (B3, 2026-07-12): the deployed authorizer now IS the reviewed engine.** The inline
governance subset (a hand-rolled tool allow-list dict + a one-line SSN/email regex) has been
**deleted** from `mcp-gateway.yaml`. The authorizer Lambda now imports the **reviewed `platform_core`
engine from a Lambda layer**: its authorization decision comes from `platform_core.policy_engine` (the
full 9-clause ALLOW-iff predicate — the same code the offline suite tests) and its boundary masking
from `platform_core.masker` (fail-closed). The layer's `python/platform_core` is pre-staged from the
single source of truth (`../../platform_core`) by `prepare_layer.sh`, so the deployed engine cannot
drift from the offline-tested one. Deploy is the proven cross-platform SAM path:

```bash
cd infra/golden-pilot
./prepare_layer.sh          # stage the reviewed engine into layer/python/ (no make, no Docker)
sam build                   # packages gateway-src/ + the layer
sam deploy --guided         # (optionally pass LedgerTableName=<reviewer ledger> for the human gate)
```

The template is cfn-lint-clean. **This layer-backed authorizer was live-redeployed and validated on a
clean account (2026-07-12)** — stack `aegis-mcp-gateway-b3`, account 864217980669, us-east-1, then torn
down with zero residual. Over HTTPS with a Cognito ID token the reviewed engine returned **ALLOW**
(`kb.search_policy`), **ALLOW + masked** (`ticket.create_draft` — the reviewed masker redacted SSN/email
in both the response and the append-only audit row), **DENY** (`db.drop` — deny-by-default), and
**APPROVAL_REQUIRED** (`ticket.submit` — human gate). The deny/gate strings are
`platform_core.policy_engine`'s verbatim messages, proving the deployed authorizer *is* the reviewed
engine. Full record: [`../infra/golden-pilot/B3-LIVE-DEPLOY-EVIDENCE.md`](../infra/golden-pilot/B3-LIVE-DEPLOY-EVIDENCE.md).

What remains beyond that: deploying **AgentCore Gateway** as the managed production control plane and
building **at least one live connector** end-to-end are customer-engagement work; connectors here are
fixtures. Publisher-trust roots and OAuth/IdP integration for backend authorization are
customer-configured. These items are tracked in
[`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
