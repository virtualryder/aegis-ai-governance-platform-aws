# Multi-tenant SaaS design — HYBRID model (decided 2026-09-02, David)

> Shared **control plane**, per-tenant **data**. One AgentCore gateway + Cedar engine + Runtime serve
> many tenants; each tenant's regulated data lives in its own DynamoDB tables + S3 Object Lock
> bucket/prefix + its own hash chain. Cross-tenant access is **forbid-by-construction in Cedar AND
> physically separated in storage** — strong isolation for CJIS/FTI/PHI, real SaaS economics on the
> control plane. This spec governs the phased build (tasks 107–111).

Starting point: today each customer is a full **silo** (one stack set per deployment, `tenant` a pinned
context value → `TENANT_ID` env). Hybrid keeps the control-plane stacks shared and adds a lightweight
**per-tenant data stack**, with `tenant` derived from a **verified JWT claim**, never pinned.

## Layer split

| Layer | Shared (control plane) | Per-tenant (isolated) |
|---|---|---|
| Identity | One Cognito pool | tenant carried as `custom:tenant` claim + a `tenant/<id>` group; caseworker groups nested under tenant |
| Gateway + Policy | One AgentCore gateway + one Cedar engine (ENFORCE) | tenant surfaced to Cedar as a **principal tag / context attribute** |
| Runtime | One AgentCore Runtime | **session isolation per tenant** (microVM per session; tenant bound at session start) |
| Compute (tool Lambdas) | Shared functions | tenant read from the **verified claim** at call time; every data path keyed by tenant |
| Workflow | One state machine | tenant in execution input; carried on every task |
| Data — DynamoDB | — | **per-tenant tables** `ben-<env>-<tenant>-{audit-ledger,cases,pending-approvals}` |
| Data — WORM/S3 | — | **per-tenant Object Lock** bucket (or dedicated prefix + scoped bucket policy) |
| Audit hash chain | — | **per-tenant chain head** (a tenant's ledger is an independent tamper-evident chain) |
| KMS | Platform CMK for control plane | optional **per-tenant CMK** for data at rest |

## Phase 107 — Runtime session isolation per tenant
- Bind tenant at AgentCore **Runtime** session creation so each tenant runs in an isolated microVM session.
- Replace the pinned `TENANT_ID` env with **tenant-from-verified-claim** in the compute layer; the claim
  is authorized by Cedar (no claim / bad tenant → deny).
- Add a **tenant-provisioning** path: onboarding a tenant creates its Cognito group + per-tenant data stack.
- **Gate:** a session for tenant A can only ever resolve tenant A's stores; unit test + `cdk synth` green.

## Phase 108 — Per-tenant Cedar policy scope
- Add `tenant` as a Cedar **context/principal attribute**; condition every `permit` on
  `principal.tenant == context.tenant` (and resource tenant). Add an explicit **`no_cross_tenant`** forbid
  (forbid-wins), so cross-tenant tool calls are denied even if a permit is mis-scoped.
- Extend the **parity oracle** to assert AgentCore-Cedar == reviewed engine for cross-tenant denials.
- **Gate:** Cedar analysis clean; parity oracle passes on cross-tenant cases.

## Phase 109 — Per-tenant WORM audit partitions
- Per-tenant DynamoDB audit tables (or partition key = tenant) + per-tenant **Object Lock** prefix/bucket;
  a tenant's IAM role can read/write **only** its partition/prefix (deny others).
- Per-tenant **hash-chain head**; a tenant's ledger verifies independently.
- **Gate:** a tenant role is IAM-denied on another tenant's ledger/prefix (negative test); chain verifies per tenant.

## Phase 110 — Full transparency / observability (every API + the model's reasoning)
- **AgentCore Observability** (OTEL/GenAI spans): the agent's reasoning + **every** tool call as spans.
- **Bedrock model-invocation logging**: all data the model touches, **masked before the model**.
- **WORM evidence**: the tamper-evident record of each governed action.
- **Correlate** all three by one `session/trace id`, **tagged with tenant** → per-tenant, end-to-end view of
  every API call across every AgentCore component. Four independent captures per governed action.
- **Gate:** for one action, show the OTEL trace + the invocation log (masked) + the WORM entry, same id, one tenant.

## Phase 111 — Live multi-tenant validation gate (end-to-end)
Deploy the shared control plane + two tenants (A, B). Prove, live and torn down:
1. **Cross-tenant deny** — tenant A's caseworker cannot reach tenant B's data (Cedar `no_cross_tenant` fires; IAM denies the store).
2. **Per-tenant WORM isolation** — A's and B's ledgers are separate, each verifies independently.
3. **Full observability** — every API call + the model's reasoning is captured and correlated per tenant.
4. Everything working as expected; residual swept.

## Migration & compatibility
- The existing **silo** path stays valid (per-customer accelerator). Hybrid is an additive **multi-tenant
  deploy mode**; `tenant` pinned = 1-tenant silo is the degenerate case of the same code.
- AgentCore Policy is AWS-preview → the reviewed engine stays fail-closed fallback + parity oracle throughout.
