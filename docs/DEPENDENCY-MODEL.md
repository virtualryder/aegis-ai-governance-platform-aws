# Dependency model — who owns what, what is pinned how, what runs where

*One authoritative answer to the question the Copilot review (2026-09-03, item 5) asked: "the platform
repo calls `platform_core` the canonical reference implementation of AGP 1.0, while everything that is
live on AgentCore runs on `governed-core` — which is it?" Both are true, for different jobs. This page
is the single place that says so, and every README below points here.*

## 1. The boxes

```
 ┌────────────────────────────────────────────────────────────────────────────────────────────┐
 │  AGP 1.0 — the Aegis Governance Pattern (the CONTRACT)             docs/14-GOVERNANCE-… │
 │  8 required controls, each fail-closed + negative-tested.  Owner: THIS repo (WOGplatform)  │
 └──────────────┬──────────────────────────────────────────┬──────────────────────────────────┘
                │ conformance oracle                       │ conformance oracle
 ┌──────────────▼──────────────────────┐    ┌──────────────▼──────────────────────────────────┐
 │  platform_core  (WOGplatform)       │    │  governed-core  (github.com/virtualryder/        │
 │  OFFLINE reference implementation   │    │  governed-core, Apache-2.0)                      │
 │  of AGP 1.0: gateway, policy engine │    │  the SHARED CONTROL PLANE the agent packs RUN ON │
 │  (9-clause predicate), approval     │    │  AgentCore Gateway interceptor, Cedar controls,  │
 │  ledger, masker, audit chain,       │    │  evidence (hash chain + WORM), sign-off gate,    │
 │  budgets, model gateway, kill switch│    │  tenancy, telemetry, kill switch, budget meter   │
 │  version 0.2.0 (this repo)          │    │  version 1.9.0 (tag + GitHub release + wheel)    │
 │  stdlib-only, laptop-runnable       │    │  Lambda + Runtime code, hash-pinned per pack     │
 └──────────────┬──────────────────────┘    └──────────────┬──────────────────────────────────┘
                │ shipped as a Lambda LAYER                 │ pinned wheel (URL + sha256) and
                │ into the reference stacks                 │ a byte-level lock of the mirrored lib/
 ┌──────────────▼──────────────────────┐    ┌──────────────▼──────────────────────────────────┐
 │  Reference stacks (WOGplatform)     │    │  Agent packs (their own repos)                   │
 │  infra/golden-pilot  mcp-gateway    │    │  benefits_eligibility_agent   core 1.9.0  LIVE   │
 │   (API GW + Cognito JWT + reviewed  │    │  pharmacovigilance_agent      core 1.9.0  LIVE   │
 │   engine, fixture tool execution)   │    │  edu_financial_aid_agent      core 1.5.0         │
 │  infra/cdk  aegis-governance-core   │    │  Housing_eligibility_agent    core 1.4.0         │
 │   (STUB gateway: audit+guardrail+   │    │  each: manifest, tools, Cedar policies, CDK      │
 │   kill switch; Budgets; WORM; KMS)  │    │  (real AgentCore Runtime + Gateway + Policy)     │
 └─────────────────────────────────────┘    └──────────────────────────────────────────────────┘
```

Two implementations of one contract, on purpose:

| | `platform_core` (this repo) | `governed-core` (its own repo) |
|---|---|---|
| **Job** | The **reference implementation and conformance oracle** for AGP 1.0: the readable, dependency-free version of every control that a reviewer (CISO, auditor, AWS) can run on a laptop, plus the **fail-closed fallback + parity oracle** while AgentCore Policy is AWS-preview | The **production control plane** the agent packs import and run on AgentCore — Gateway interceptor, tool-Lambda decorators, evidence writer, sign-off gate, tenancy routing, kill switch, budget meter |
| **Runs where** | Offline (`demo/`, `platform_core/tests`); as a Lambda **layer** in the portable reference gateway (`infra/golden-pilot/mcp-gateway.yaml`, live-validated: B3, Run 10, Run 13) | In every pack's tool Lambdas, the gateway REQUEST interceptor and the AgentCore Runtime image (live-validated: benefits EP1 → mt6, 2026-07-27 → 2026-09-03) |
| **Executes real side effects?** | No — the portable reference gateway executes **fixtures** (`[fixture] … executed`); the one real connector proof is the DynamoDB system-of-record connector (Run 9, 2026-07-01) | Yes — the packs' tools (Comprehend masking, Bedrock drafting, DynamoDB stores, Step Functions workflow) are real; consequential commits stay behind the human gate |
| **Owner / repo** | `virtualryder/aegis-ai-governance-platform-aws` (this repo), `platform_core/` | `virtualryder/governed-core` (public, Apache-2.0) |
| **Version** | `VERSION` + `platform_core/pyproject.toml` (**0.2.0** from 2026-09-03; 0.1.0 before) | `pyproject.toml` (**1.9.0**); every version is a git tag **and** a GitHub release carrying the CI-built wheel |
| **How a consumer pins it** | The layer is staged **byte-for-byte from `platform_core/`** by `infra/golden-pilot/prepare_layer.sh`; `verify_authorizer_engine.py` proves the deployed authorizer is that code | `requirements-core.txt`: `governed-core @ <release wheel URL> --hash=sha256:…` (`pip --require-hashes`); the Runtime image pins the same wheel; `lib/core.lock` (`lib/verify_core.py`, CI) is a byte-level lock of the pack's mirrored `lib/` so nothing drifts silently; `lib/CORE_VERSION` names the version |
| **Release discipline** | tags + GitHub releases from 2026-09-03 (`v0.2.0`); `CHANGELOG.md` | tag → GitHub release → CI wheel with sha256 (since 1.3.1) |
| **Conformance proof** | `platform_core/tests/test_agp_conformance.py` + `AGP-CONFORMANCE.md` (control → module → negative test) | The packs' live gates: `evidence/AGENTCORE-*.md` in each pack (isolation, audit routing, observability, kill switch, budget) |

## 2. Decision: keep both — `platform_core` is the oracle, `governed-core` is the product

Recorded 2026-09-03 after the Copilot review. **`platform_core` is not retired into `governed-core`.**

- The **contract** (AGP 1.0) needs a reference a reviewer can read end-to-end without AWS. `platform_core`
  is ~2 500 lines of stdlib Python (+ ~700 in `prod/`) with 60 offline tests; `governed-core` is Lambda / AgentCore code that
  only makes sense deployed. Folding one into the other would either strip the reviewable reference of
  its independence or burden the runtime core with laptop-only concerns.
- AgentCore **Policy is AWS-preview**. Until it is GA, the deny-by-default decision on the AgentCore
  path is made by Cedar in AgentCore **and** re-affirmed by the same predicate offline as a parity
  oracle (`docs/AGENTCORE-INTEGRATION.md` §"what stays"). That oracle is `platform_core.policy_engine`.
- Where the two implement the *same* control, the **ordering and semantics are mirrored and
  cross-cited**, and a change in one must land in the other (see §4). Examples: single-use bound
  approvals (`approval_ledger.consume` ↔ `approve_signoff` + `finalize_signoff` approval-path check);
  kill switch (`kill_switch.py` ↔ `controls/kill_switch.py`); durable intent / outbox
  (`gateway.py` INTENT → execute → COMPLETED/INDETERMINATE ↔ `AuditIntent` → `FINAL#` marker →
  `COMMITTED`, `GATEWAY-MODES.md`).

What this means for a partner: **the thing to productise is `governed-core` + the packs.** `platform_core`
and the two reference stacks are the *specification and its proof*, not a second product.

## 3. Compatibility matrix (what has actually run together)

| governed-core | What it added | Packs pinned to it (tag → date) | Platform state at the time |
|---|---|---|---|
| 1.4.0 | GA-5 duplicate-submission protection in `signoff_register` | benefits `v0.2.0-pilot-rc1` (2026-08-03); Housing `v0.9.6` | platform_core 0.1.0; Run 10 portable gateway live |
| 1.5.0 | finalize verifies the **approval path** (SoD + consumed-by-approve_signoff), fail-closed | pharmacovigilance `v0.2.0-pilot-rc1`, edu_financial_aid `v0.2.0-pilot-rc1` (2026-09-02) | Run 11: CDK reference stack + kill switch live |
| 1.6.0 | hybrid multi-tenant routing (per-tenant ledger, WORM vault, approvals register) | benefits main (2026-09-02, `AGENTCORE-MULTITENANT-AUDIT` 12/12) | `docs/MULTI-TENANT-SAAS-DESIGN.md` |
| 1.7.0 / 1.7.1 | one correlation set through every hop; interceptor reads MCP `_meta` trace context | benefits `v0.3.0-pilot-rc1` (2026-09-03) — `AGENTCORE-OBSERVABILITY`, `AGENTCORE-111-GATE` | Run 12: full-observability wave |
| 1.8.0 | kill switch on the AgentCore path (containment precedes evaluation) | benefits main (2026-09-03) — `AGENTCORE-KILL-SWITCH` 29/29 | `docs/ops/KILL-SWITCH.md` |
| **1.9.0** | per-tenant token + USD budget meter | **benefits main (2026-09-03)** — `AGENTCORE-BUDGET` 24/24 | `docs/TOKEN-BUDGETS-AND-COST-CEILINGS.md`; platform_core 0.2.0 (outbox ordering, zero-default entitlements, bound approvals at consumption — Run 13) |
| 1.9.0 | (same core) — first non-lead pack to re-pin and re-gate all four SaaS/containment/budget controls | **benefits `v0.4.0-pilot-rc1` (2026-09-03)** — kill switch + budget on the tag; **pharmacovigilance `v0.3.0-pilot-rc1` (2026-09-03)** — from-zero two-tenant gate: isolation 12/12, transparency 13/13 per tenant, canary 0, kill switch 29/29, budget 24/24, regression sweep 0 (`pharmacovigilance_agent/evidence/AGENTCORE-*-2026-09-03.*`) | GAP-1 of the 2026-09-03 platform review |

Rules of the matrix: a pack's tag names exactly one governed-core version (`requirements-core.txt`);
a pack on an older core is **not wrong**, it is **behind** — the EDU pack (1.5.0) and Housing (1.4.0) lack
multi-tenant routing, correlation, kill switch and budget until they re-pin and re-run their gates; PV
caught up to 1.9.0 on 2026-09-03 (GAP-1). Benefits is the lead pack; the others follow it.

**Known cross-pack wart (to reconcile at the next governed-core bump).** The shared runtime
(`lib/runtime/_launch.sh` / `_obs_setup.sh`) derives the deployment PREFIX from the SSM path. PV's
1.9.0 tree carries the *generic* derivation (strips any pack suffix — `-eligibility` / `-pharmacovigilance`
/ `-aid`), gated live in the PV 2026-09-03 run; benefits' released `v0.4.0-pilot-rc1` tree still carries
the `-eligibility`-specific derivation it was gated with. Both are internally lock-consistent at their own
`core.lock`, and functionally identical for benefits, but the shared runtime is therefore **not byte-identical
across packs at 1.9.0**. The generic runtime is the correct canonical form; it lands in governed-core with the
next version bump (GAP-4), at which point benefits/PV/EDU/Housing re-pin to it and the mirrored `lib/runtime`
is reconciled under one version number.

## 4. Change protocol (so the two never silently diverge)

1. A control change lands in **governed-core** first (tag, release, wheel) when it is a runtime
   behaviour, or in **platform_core** first when it is a contract clarification — and the same PR
   (or a paired one) updates the other side and cites the counterpart in the docstring.
2. The pack that proves it live re-pins (`requirements-core.txt` hash, `lib/regen_core_lock.py`) and
   records the gate in `evidence/`; MATURITY.yaml here gets the `agentcore.<control>_live` record.
3. `AGP-CONFORMANCE.md` row for the control names both implementations' tests.
4. The AGP version moves only when a control or invariant is **added or changed** — an implementation
   fix (like the 2026-09-03 outbox ordering) does not bump AGP 1.0.

## 5. Related warts, stated plainly

- **Two gateway implementations** (the partner deck's "wart #1"): the portable reference gateway
  (`platform_core` layer, API Gateway + Cognito) and the AgentCore Gateway interceptor (`governed-core`).
  They are the *oracle* and the *product*; they are not both products. Feature work goes to the second.
- The CDK `aegis-governance-core` stack deploys a **stub** gateway Lambda (audit + guardrail + kill
  switch) — it exists to validate the platform primitives (WORM, KMS, Budgets, CloudTrail, kill switch
  SoD policies) as IaC, not to serve tool calls. Labelled as such in `infra/cdk/README.md` and
  MATURITY (COPILOT-7).
- `platform_core/prod/` (Cedar compiler, KMS-signed manifests, atomic budgets) is **OFFLINE + unit-tested**
  except where the matrix above says otherwise; the AgentCore packs use AgentCore's own Cedar engine.
