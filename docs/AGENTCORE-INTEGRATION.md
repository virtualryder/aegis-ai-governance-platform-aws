# Aegis × Amazon Bedrock AgentCore — Best-Path Integration & Repositioning

> **One line.** AgentCore now provides the managed **control plane** (Gateway, Identity, Policy,
> Observability, Runtime). Aegis stops re-implementing that plane and becomes the **accountability &
> evidence layer that wraps it** — the four things AgentCore does *not* do, plus the honesty discipline.
> This document is the canonical spec for that shift. Where prose elsewhere competes with AgentCore, this
> page governs.

Status: DESIGN — grounded in AWS documentation (verified 2026-09-02). Supersedes any positioning that
frames Aegis's own gateway/Cedar engine as a differentiator versus AgentCore.

> **STATUS (2026-09-02): ALREADY IMPLEMENTED IN THE PACKS — this is consolidation, not a from-scratch build.**
> The vertical agent packs already run on real AgentCore Gateway + a Cedar Policy engine in ENFORCE,
> stood up as IaC by `cdk/gateway_provider/handler.py` (GA-1) with the Cedar policy set in `policies/*.cedar`,
> and live-validated + torn down (benefits `EP1` 2026-07-27, `ben-val2` 2026-07-28, `ben-demo` 2026-08-24).
> The remaining work is: (1) record this in the platform's canonical `MATURITY.yaml`/README [DONE 2026-09-02];
> (2) a fresh timestamped ENFORCE re-prove on current code; (3) the parity oracle; (4) reposition prose.
> Sections below that read as "adopt/build" describe the *platform-repo reference*, which is roadmap.

---

## 1. Verified AgentCore capabilities (GA vs preview)

| AgentCore service | What it does | Status (2026-09) |
|---|---|---|
| Runtime | Serverless, **session-isolated** agent execution (microVM per session) | **GA** (Oct 2025) |
| Gateway | Turns APIs / Lambda / services into MCP tools; the tool-call choke point | **GA** (Oct 2025) |
| Identity | Agent identity + authN against existing IdPs (Cognito/Okta/Entra) | **GA** (Oct 2025) |
| Memory | Short- and long-term agent memory stores | **GA** (Oct 2025) |
| Observability | OTEL-compatible tracing / metrics / debugging (CloudWatch GenAI) | **GA** (Oct 2025) |
| Code Interpreter / Browser | Sandboxed code + headless browser tools | **GA** (Oct 2025) |
| Registry | Governed catalog of agents / MCP servers / tools | GA |
| **Policy** | **Cedar, default-deny** tool-call authorization enforced *inside Gateway* | **PREVIEW** (Dec 2025) |
| Evaluations | Automated agent assessment | PREVIEW (Dec 2025) |
| Payments | Microtransaction payments with **configurable spending limits** | Available |

**Policy — exactly what it is (this is the finding that matters).** AgentCore Policy sits between the
agent and its tools *through Gateway*, evaluates each invocation against **Cedar** policies with a
**default-deny** posture, uses Cedar partial evaluation to **remove forbidden tools from the agent's tool
list**, and runs control-plane **Cedar Analysis** to catch policy conflicts. That is the same sentence
Aegis's `policy_engine` was written to say. **We concede this layer to AgentCore.**

**But Policy is PREVIEW.** It is not GA, carries no production SLA, and (per AWS's own security blog)
Cedar here expresses conditional/temporal/quantitative/boolean rules — it does **not** express
separation-of-duties, single-use approval, or human-in-the-loop gating. Those remain Aegis's job.

Sources: AgentCore overview; "Why Policy in AgentCore chose Cedar" (AWS Security Blog); "AgentCore now
includes Policy (preview), Evaluations (preview)" (AWS What's New, Dec 2025); AgentCore GA (AWS What's
New, Oct 2025).

---

## 2. The 8 AGP controls → who provides them now

| # | AGP v1.0 control | Provided by AgentCore | Aegis role after integration |
|--:|---|---|---|
| 1 | Identity (MFA + JWT verify) | **Identity** (GA) | Configure/consume; stop maintaining a bespoke authorizer |
| 2 | Deny-by-default gateway | **Gateway + Policy** (Policy=preview) | Adopt; keep reviewed engine as fail-closed fallback + oracle (§3) |
| 3 | Least-privilege intersection | **Policy** Cedar | Author Cedar; contribute intersection patterns |
| 4 | **Bound single-use SoD approval** | ❌ none | **AEGIS OWNS** — approve-signoff Lambda + finalize gate |
| 5 | **Fail-closed masking (mask-before-audit)** | ❌ (Guardrails filters, not fail-closed arch) | **AEGIS OWNS** — Comprehend Medical NER, deny-on-masker-failure |
| 6 | **Append-only + WORM audit (tamper-evident)** | ❌ (Observability is telemetry, not evidence) | **AEGIS OWNS** — DynamoDB hash-chain + S3 Object Lock, IAM-denied Update/Delete |
| 7 | Token budgets / cost control | ~ **Payments** spending limits | Consume Payments where it fits; keep atomic token budget |
| 8 | Model gateway + grounding | Bedrock + Guardrails | Keep guardrail-pinned drafting |

Plus the cross-cutting differentiator AgentCore has no equivalent for: **control mappings** to CJIS v6.0,
IRS Pub 1075, 42 CFR Part 2, GxP/21 CFR Part 11, FERPA — and the **evidence discipline** itself
(`MATURITY.yaml` + `tools/check_maturity.py` drift-checker + verbatim-deny live-run evidence).

**The pitch, restated:** *Aegis is the accountability and evidence layer that wraps AgentCore* — bound
SoD approval, fail-closed masking, WORM evidence, and regulator control mappings — not a control plane
that competes with Gateway/Policy/Identity.

---

## 3. How we adopt Policy while it is preview (the responsible path)

We do **not** put a preview service in the sole enforcement path for regulated data. Instead:

1. **AgentCore Gateway + Policy** become the primary, managed tool-authz choke point (Cedar default-deny).
2. The **reviewed `platform_core.policy_engine`** stays deployed as (a) a **fail-closed fallback** if
   Policy is unavailable in-region, and (b) a **conformance oracle**: every request is decided by both,
   and a **parity check** asserts AgentCore-Cedar == reviewed-engine. Divergence fails CI, exactly like
   the existing drift-checker.
3. When Policy reaches **GA**, the fallback becomes optional and the oracle stays as the parity test.

This makes the preview status a *strength* in the story: we can show AgentCore Policy and our reviewed
engine agreeing, decision-for-decision, on the same live traffic.

---

## 4. One live AgentCore run (the proof that converts the claim)

Run the benefits path end-to-end on AgentCore with the same discipline as the ten existing runs:

- **AgentCore Gateway** exposes the benefits tools as MCP; **Identity** issues the agent identity.
- **AgentCore Policy** (Cedar) authorizes each tool call, default-deny.
- **Aegis** supplies the SoD approval gate (approve-signoff → finalize), fail-closed masking before the
  audit write, and the WORM hash-chained ledger.
- **Observability** trace + Aegis WORM entry captured for one clean case and one denied/injection case.
- Output: `evidence/AGENTCORE-LIVE-<date>.md` with verbatim Cedar deny strings and the WORM markers,
  proving **deployed == reviewed** for the AgentCore path. Add an `agentcore` block to `MATURITY.yaml`.

---

## 5. Multi-tenancy / multi-account (the gate for "customers, plural")

AgentCore closes most of this gap natively:

- **Runtime session isolation** (microVM per session) gives per-tenant compute isolation for free.
- **Per-tenant Cedar scope**: tenant id as a Cedar principal/context attribute; one policy set, scoped
  decisions. `forbid` overrides `permit`, so cross-tenant access is deny-by-construction.
- **Per-tenant WORM partitions**: audit ledger partition key = tenant; S3 Object Lock prefix per tenant.
- **Multi-account**: one control-plane account + per-tenant workload accounts via AWS Organizations;
  cross-account roles scoped by tenant.

**Business-model gate — DECIDED 2026-09-02 (David):** near-term model is the **per-customer engagement
accelerator** (single-tenant, scoped deploy in each customer's own AWS account); the multi-tenant SaaS
is the **roadmap** story. Both paths now exist in the benefits pack as CDK switches, and the
multi-tenant path is **BUILT and LIVE-VALIDATED (2026-09-02, later the same day)** — the note that
"until multi-tenancy is built MATURITY.yaml must keep it out_of_repo" no longer applies:

| Phase | What | Proof |
|---|---|---|
| 107 runtime/session isolation + tenant derivation | shared control plane, per-tenant DataStacks, gateway REQUEST interceptor injects an HMAC-signed tenant derived from the verified identity (`tenant_<id>` group); every Lambda verifies before routing | benefits `evidence/AGENTCORE-MULTITENANT-E2E-2026-09-02.md` (2 tenants) |
| 108 per-tenant Cedar scope | `require_tenant` forbid (multi-tenant only) refuses un-tenanted identities; cross-tenant deny proven (0 tools + 403 verbatim) | same |
| 109 per-tenant WORM partitions | governed-core 1.6.0 routes the canonical evidence writer, exactly-once marker and approvals register to `<prefix>-<tenant>-…` + the tenant's own Object-Lock vault, on the gateway AND the workflow hop, fail-closed | benefits `evidence/AGENTCORE-MULTITENANT-AUDIT-2026-09-02.md` (12/12) |
| 110 full transparency | one correlation set (tenant · session · trace · request · case) across runtime spans, gateway rows, tool-Lambda lines, model-invocation bodies and the WORM record; masked-before-model measured | benefits `evidence/AGENTCORE-OBSERVABILITY-2026-09-02.md` (real Runtime, 13/13 per tenant) |
| 111 live gate | two-tenant end-to-end | PASSED (see `MULTI-TENANT-SAAS-DESIGN.md`) |

What is still NOT built for a SaaS: multi-account (Organizations) tenancy, tenant onboarding
automation and billing/metering, an operator console, and a named design partner — these stay
engagement/roadmap items and `MATURITY.yaml` says so. The public story remains "per-customer
accelerator, multi-tenant SaaS on the roadmap (live-validated prototype)".

---

## 6. Canonical repo & lineage

`aegis-ai-governance-platform-aws` (this repo) is the **canonical control plane** and the definition of
AGP v1.0; the four vertical packs conform to it. Shared enforcement logic is consumed as the
**governed-core pinned wheel** (single reviewed engine, versioned, imported — never forked per pack), so
"deployed == reviewed" holds across the portfolio. This document is the canonical AgentCore-integration
spec; `MATURITY.yaml` remains the machine-readable source of truth for maturity claims.

## 7. Support model (honesty item)

This remains a reference accelerator, not a supported product: no SLA, no hotfix path (see `NOT-CLAIMS.md`).
For "customers plural," a support model (versioned releases, security-patch cadence, an owning team) is a
prerequisite, tracked as `out_of_repo` until it exists. We do not claim it before it is real.
