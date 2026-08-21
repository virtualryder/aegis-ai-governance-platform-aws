# Agent Onboarding Runbook — From Idea to Governed, Observable, Live

> **Who this is for.** The department team building an agent, and the platform team reviewing it.
> **What it assumes.** The Aegis control plane is already deployed (`SA-DEPLOYMENT-RUNBOOK.md` /
> `infra/cdk/`), the IdP is federated, and the relevant vertical pack is installed.
> **How long it takes.** 1–2 weeks per agent once the platform exists. You will author roughly
> **six artifacts** and write **zero lines of observability code** — dashboards, audit,
> masking, budgets, and kill-switch coverage are inherited from the platform.
>
> Companion documents: `governance/onboarding/MINIMUM-BAR.md` (the nine gates),
> `governance/onboarding/agent-manifest.schema.json` (the contract),
> `docs/04-AGENT-ONBOARDING-STANDARD.md` (the standard), `CUSTOMER-DELIVERY-CHECKLIST.md`
> (the handoff gate), `docs/ops/KILL-SWITCH.md` (the drill).

---

## Step 0 · Scope with the business owner (half a day — do this before any code)

Sit with the department that owns the workflow. Leave the meeting with five things written down:

1. **Purpose statement** — one sentence: what the agent does and for whom.
2. **The consequential-action list** — every issue / adjudicate / release / award / transfer
   the workflow contains. These will be *withheld from the agent's own tool grants* and
   reachable only through the human gate (Minimum Bar, gate 2). Naming them first is the
   single most important act of governance in the whole process.
3. **Data classes touched** — PII, FERPA, PHI, CJI, financial. Classification drives masking,
   retention, and policy selection automatically.
4. **Disposition roles** — who approves consequential actions (must be a *different human*
   than the requester — separation of duties), and how deep review goes per verdict class.
5. **Budget** — a monthly token cap and whether the cap is hard (deny at limit) or soft
   (alert and continue). Regulated workloads default to hard.

## Step 1 · Copy the governed template (30 minutes)

Start from the governed hero-agent template (or the closest existing hero agent — benefits,
financial aid, housing, pharmacovigilance). The template already carries the gateway wiring,
append-only audit calls, fail-closed masking, the human-gate state machine, and the CDK
stacks. **Do not start from an empty repo** — an agent that grows up outside the template
spends its whole life being retrofitted.

## Step 2 · Author the manifest (half a day)

One YAML file declares everything the agent is allowed to be. Every block below is required —
the schema (`agent-manifest.schema.json`) and CI reject a manifest missing any of them:

```yaml
kind: Agent
metadata:
  name: benefits-eligibility
  description: SNAP/Medicaid/TANF pre-screening with caseworker sign-off
  classification: [PII, FINANCIAL]        # data classes — drives masking/retention/policy
grants:
  tools: [lookup_fpl, screen_applicant]   # EVERYTHING the agent may call — nothing else loads
  consequential: [submit_determination]   # reachable ONLY through the human gate
grounding:
  source: fpl_reference_data              # the authority the agent must cite
  grounding_threshold: 0.85
  relevance_threshold: 0.80
budget:
  monthly_token_cap: 5000000
  cap_behavior: hard                      # regulated default: deny at cap
  alert_thresholds: [0.6, 0.85, 1.0]
evals:
  suite: tests/
  min_pass_rate: 1.0
human_gate:
  mode: step_functions_wait_for_task_token
  separation_of_duties: true
  approval_ttl_seconds: 3600
pack: SLG                                 # vertical pack compatibility (gate 9)
signing:
  publisher: your-team
  algorithm: rsassa-pss-sha256
  signature: null                         # null until Step 6 — the delivery gate blocks null
```

## Step 3 · Author the Cedar policies (half a day, with the business owner)

Policies encode the owner's actual rules. Three patterns cover most agents (working examples
in the pharmacovigilance repo's `policies/`):

- **Permit-with-intersection** — allow a tool only when both the agent grant AND the acting
  human's role permit it (`pv_reviewer_permit.cedar`).
- **Mask-before-X** — forbid a step until masking has run on the inputs
  (`mask_before_assess.cedar`, `mask_before_draft.cedar`).
- **No-self-X** — separation of duties: the requester can never be the approver
  (`no_self_submit.cedar`, `no_self_causality_commit.cedar`).

Rule of thumb: if the business owner says "except when…", that's a policy, not a code branch.

## Step 4 · Implement tools and evals (2–4 days — the actual build)

- Implement **only** the tools the manifest declares. CI statically diffs the code's tool
  calls against `grants` and fails on any undeclared call; the gateway denies them at runtime
  as defense in depth.
- Consequential actions are implemented as gated workflow steps, **absent** from the agent's
  own callable tools.
- Write the eval suite the manifest declares: accuracy on the domain task, refusal behavior,
  prompt-injection resistance, and the three mandatory negative tests every agent carries —
  unauthorized tool → deny; self-approval → deny; replayed approval → deny.

## Step 5 · Clear the bar locally (an hour)

```bash
# schema + bar conformance
python -c "from prod.manifest_validator import validate_manifest; print(validate_manifest('agents/<name>/manifest.yaml'))"
# full test suite
PYTHONPATH=platform_core:. python -m pytest tests/ -q
```

Fix everything before review — the CI gates are the same checks, they just fail in public.

## Step 6 · Sign, then pass the delivery gate (an hour)

- Sign the manifest with the publisher key (`platform_core/prod/manifest_signing.py`;
  RSASSA-PSS-SHA-256 locally, or the KMS asymmetric path in production).
- Run the delivery gate — it refuses placeholder credentials (`ChangeMe-*`), demo-grade
  retention (GOVERNANCE mode / short windows on regulated classes), and unsigned manifests:

```bash
python -c "from prod.manifest_validator import delivery_check; ok, errs = delivery_check('agents/<name>/manifest.yaml'); print(ok, errs)"
```

Set real retention per record class with Legal/records management — the table in
`CUSTOMER-DELIVERY-CHECKLIST.md` is the starting point.

## Step 7 · Deploy (30 minutes)

Four small stacks, rendered from the manifest, in order:

```bash
cdk deploy <name>-identity   # roles, groups, federation hooks
cdk deploy <name>-gateway    # tool registrations, policy attachment
cdk deploy <name>-data       # tables/buckets under the pack's KMS key
cdk deploy <name>-compute    # the agent runtime + human-gate state machine
```

Register the agent with the platform gateway (its manifest is loaded and verified at
registration — an unsigned or bar-failing manifest refuses to load).

## Step 8 · Inherit observability (zero code — verify, don't build)

The platform provides these the moment the agent registers. Verify each exists; write none:

| You get | Where | Because |
|---|---|---|
| Operations dashboard | CloudWatch (from `ops/cloudwatch-dashboard.json`) | Gateway emits per-agent metrics |
| Hash-chained audit of every action | DynamoDB audit table (+ WORM evidence bucket) | The gateway writes it; IAM forbids edits |
| PII/PHI masking | Bedrock Guardrail + platform masker | Fail-closed at the prompt and audit boundaries |
| Budget alarms + chargeback | CloudWatch alarms at 60/85/100% + usage ledger | The manifest's `budget` block |
| Kill-switch coverage | Platform-wide | Every registered agent obeys it — no opt-in |

## Step 9 · Go-live drills (half a day — do not skip)

1. **Canary** — a benign request → ALLOW, audit row present.
2. **Deny-by-default** — an undeclared tool → DENY, audited.
3. **Human gate** — a consequential action without approval → PENDING; with a self-approval →
   DENY; with a second human's approval → proceeds exactly once (replay → DENY).
4. **Kill switch** — engage → canary DENIES → release with a *different identity* → allows.
5. **Parallel-run** — real cases with 100% human review until the eval pass rate and the
   owner's comfort agree; then dial review depth per verdict class.

File the drill outputs in the WORM evidence bucket. Add the agent to `MATURITY.yaml` with an
honest tier — the drift-checker will hold every future claim to it.

## Go-live checklist (condensed)

- [ ] Consequential actions named by the owner and absent from `grants.tools`
- [ ] Manifest complete (all blocks) and schema-valid
- [ ] Cedar policies reviewed by the business owner and security
- [ ] Eval suite green at the declared pass rate; three mandatory negatives pass
- [ ] Manifest signed; publisher recorded
- [ ] Delivery gate green (no placeholders, real retention per record class)
- [ ] Four stacks deployed; agent registered with the gateway
- [ ] Dashboard, alarms, chargeback verified (inherited, not built)
- [ ] All five drills executed; evidence filed to WORM
- [ ] `MATURITY.yaml` entry added; sign-offs recorded

---

*The economics this runbook exists to deliver: the second agent costs a manifest. So does the
tenth.*
