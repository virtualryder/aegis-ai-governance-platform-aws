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
- **DONE 2026-09-02 (governed-core 1.6.0, cross-repo).** `tenancy` + `tenant_interceptor` were promoted into
  the core (pinned by hash); the canonical evidence writer routes `AUDIT_TABLE` → `<prefix>-<tenant>-audit-ledger`
  and the WORM copy → `WORM_BUCKET_TEMPLATE.format(tenant)` (`<prefix>-<tenant>-worm-<account>`); the
  exactly-once `FINAL#` marker and the pending-approvals register route the same way. Fail-closed: no verified
  signed tenant binding ⇒ `stored:false`, never a write into the shared base ledger. The Step Functions hop
  (no interceptor) carries the HMAC-signed pair in the execution input, threaded into all 11 Lambda payloads;
  each Lambda re-verifies it; an execution without the pair fails at the first state. Ingestion boundary:
  `ingest` derives the tenant from a VERIFIED Cognito access token of a tenant member and mints the pair.
  **Live-proven** (env `mt2`, 12/12): benefits `evidence/AGENTCORE-MULTITENANT-AUDIT-2026-09-02.md`.

## Phase 110 — Full transparency / observability (every API + the model's reasoning)
- **AgentCore Observability** (OTEL/GenAI spans): the agent's reasoning + **every** tool call as spans.
- **Bedrock model-invocation logging**: all data the model touches, **masked before the model**.
- **WORM evidence**: the tamper-evident record of each governed action.
- **Correlate** all three by one `session/trace id`, **tagged with tenant** → per-tenant, end-to-end view of
  every API call across every AgentCore component. Four independent captures per governed action.
- **Gate:** for one action, show the OTEL trace + the invocation log (masked) + the WORM entry, same id, one tenant.
- **Design + join keys (2026-09-02):** [`OBSERVABILITY-CORRELATION.md`](OBSERVABILITY-CORRELATION.md).
- **DONE / LIVE-PROVEN 2026-09-02** (env `mt3`, 2 tenants, 13/13 each, real AgentCore Runtime): governed-core 1.7.1
  `telemetry.py`; benefits `evidence/AGENTCORE-OBSERVABILITY-2026-09-02.md`.

## Phase 111 — Live multi-tenant validation gate (end-to-end) — **PASSED 2026-09-02** (env `mt`, 2 tenants; see benefits `evidence/AGENTCORE-MULTITENANT-E2E-2026-09-02.md`)
Deploy the shared control plane + two tenants (A, B). Prove, live and torn down:
1. **Cross-tenant deny** — tenant A's caseworker cannot reach tenant B's data (Cedar `no_cross_tenant` fires; IAM denies the store).
2. **Per-tenant WORM isolation** — A's and B's ledgers are separate, each verifies independently.
3. **Full observability** — every API call + the model's reasoning is captured and correlated per tenant.
4. Everything working as expected; residual swept.

## Migration & compatibility
- The existing **silo** path stays valid (per-customer accelerator). Hybrid is an additive **multi-tenant
  deploy mode**; `tenant` pinned = 1-tenant silo is the degenerate case of the same code.
- AgentCore Policy is GA (2026-03-03) → the reviewed engine stays as a defense-in-depth parity oracle + offline/outage fallback.

## Routing correction — how the tenant reaches the tool (2026-09-02, from the probe)

**Finding (AWS docs):** AgentCore Gateway does **not** pass the caller's JWT claims to a Lambda function
target. The target Lambda receives only the tool input args (the `inputSchema` values) plus gateway
metadata in `context.client_context.custom` (`bedrockAgentCoreGatewayId`, `...ToolName`,
`...AwsRequestId`, …) — **no `sub`, no `cognito:groups`, no `custom:tenant`.** So a tool Lambda cannot
derive the tenant from the claim directly; the claim never arrives.

**Corrected mechanism — request Lambda interceptor.** AgentCore Gateway supports a **request Lambda
interceptor** that runs *after* inbound auth and *before* the target, and is passed "the original
request payload and headers, including the validated JWT and its embedded claims." It can extract
`custom:tenant` from the validated JWT and **inject** it into the request the target receives (a
reserved header / payload field). This is the trusted boundary that keeps "tenant is DERIVED, never
REQUESTED": the interceptor (not the model, not the request body) sets the tenant, from the
gateway-validated identity.

**What changes vs. what stays:**
- STAYS: `tenancy.route_store` + the per-tenant `DataStack` naming + the request-scoped context — all still correct.
- CHANGES: the SOURCE feeding `set_request_claims` is the **interceptor-injected** tenant, read from the
  reserved field the interceptor set — not JWT claims read from the Lambda event (which don't exist).
  The tool Lambda entrypoint reads the injected tenant and calls `set_request_claims({"custom:tenant": <injected>})`;
  a model-supplied `tenant`/tenant-header is scrubbed (same discipline as the token_boundary credential scrub).

**Revised phase-107 remainder (supersedes items 1–2 of the earlier list):**
1. **Gateway request interceptor Lambda** — derive `custom:tenant` from the validated JWT, inject it as a
   reserved field; wire it on the gateway (the `gateway_provider` custom resource gains interceptor config).
2. **Tool Lambda entrypoint** — read the injected tenant, `set_request_claims`, scrub any model-supplied tenant.
3. `app.py` per-tenant `DataStack` provisioning + compute IAM to `<prefix>-*` stores (unchanged).
4. `governed_core` audit/WORM writer consumes `route_store` (cross-repo, unchanged).

Interceptor GA/preview status is unconfirmed in the docs read; verify availability in-region before the
two-tenant live gate. If interceptors are not available, the fallback is per-tenant gateways (each
tenant's gateway pins `TENANT_ID`) — stronger isolation, less "single shared control plane."

## Interceptor availability + config (verified 2026-09-02, account 111122223333)

`bedrock-agentcore-control` `CreateGateway` **accepts `interceptorConfigurations`** (boto3 1.43.46) —
the request-interceptor mechanism is available in-region, so the shared-control-plane hybrid is
buildable (no per-tenant-gateway fallback needed). Shape:

```
interceptorConfigurations: [{
  interceptor: { lambda: { arn: <interceptor-lambda-arn> } },
  interceptionPoints: [ "<point>" ],          # the request (pre-target) point
  inputConfiguration: {
    passRequestHeaders: true,                  # REQUIRED so the interceptor sees the validated JWT
    payloadFilter: { exclude: [ ... ] }
  }
}]
```

**Build spec for the tenant interceptor:**
- A small `tenant-interceptor` Lambda: reads the validated JWT from the passed request headers, decodes
  `custom:tenant`, and injects it into the outbound request as a reserved field/header the target reads
  (never trusts a model-supplied tenant). Fail-closed: no tenant claim -> reject.
- `gateway_provider` (the CFN custom resource) adds `interceptorConfigurations` to its `create_gateway`
  call with `passRequestHeaders: true`, pointing at that Lambda ARN.
- Tool Lambda entrypoints read the injected tenant and call `tenancy.set_request_claims({"custom:tenant": <injected>})`.

This is the corrected item 1 of the phase-107 remainder; items 2-4 (app.py per-tenant provisioning,
compute IAM, governed-core audit routing) are unchanged.
