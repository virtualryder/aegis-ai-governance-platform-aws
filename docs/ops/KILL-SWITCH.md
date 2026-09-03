# The Kill Switch — Named Platform Containment Control

> **What it is.** The one-command answer to the question every SLG/EDU/regulated buyer asks:
> *"If an agent misbehaves, can you stop everything, right now, and prove you did?"*
> Yes: engage the Kill Switch and the authorization gateway denies **every** tool call —
> before masking, before policy, before budgets, before approvals — and writes each denial
> and the switch state change itself to the append-only audit. Containment precedes evaluation.
>
> Implemented in [`platform_core/kill_switch.py`](../../platform_core/kill_switch.py), wired as the
> **first check** in [`platform_core/gateway.py`](../../platform_core/gateway.py) `call()`, and
> negative-tested in [`demo/test_kill_switch.py`](../../demo/test_kill_switch.py).

## Design rules (each proven by a test)

| Rule | Behavior | Test |
|---|---|---|
| Containment outranks everything | Engaged switch denies all calls as the gateway's first check — even a consequential action carrying a valid, bound approval; even a payload that would have failed masking | `test_engaged_switch_denies_everything_first` |
| Easy to engage, deliberate to release | `engage(actor, reason)` is one call; `disengage` **requires a different actor** than the engager (separation of duties) | `test_separation_of_duties_on_release` |
| The incident timeline writes itself | ENGAGE and DISENGAGE are both appended to the audit ledger with actor, reason, timestamp; every denied call carries `kill_switch_engaged` in its reason | `test_state_changes_are_audited` |
| Reversible | Disengage restores normal deny-by-default authorization — no redeploy, no restart | `test_separation_of_duties_on_release` |
| Backwards compatible | A gateway constructed without a switch behaves exactly as before | `test_no_switch_configured_behaves_normally` |

Engaging also zeroes every registered budget meter (belt and suspenders — a caller that
somehow bypassed the gateway check still fails its budget preflight).

## Production mapping

`platform_core` is the offline analog. In a deployed environment the engaged flag lives in a
**single SSM parameter** (e.g. `/aegis/kill-switch`) read by the gateway with a short-TTL cache
(≤ 30 s), so one `aws ssm put-parameter` call — or one button in the operator console — contains
the whole platform within seconds. The parameter is KMS-encrypted, its writes are CloudTrail-logged,
and IAM restricts `PutParameter` on it to the incident-response role (engage) and a *distinct*
security-lead role (disengage), preserving separation of duties in IAM itself.

```
Engage   : aws ssm put-parameter --name /aegis/kill-switch --value '{"engaged":true,"actor":"secops_oncall","reason":"SEV-1 …"}' --overwrite
Disengage: aws ssm put-parameter --name /aegis/kill-switch --value '{"engaged":false,"actor":"security_lead","reason":"contained; reviewed"}' --overwrite
```

## Where it is actually wired today (2026-09-03 — LIVE on BOTH paths)

| Path | Kill Switch state | Evidence |
|---|---|---|
| **Platform reference stack** (`aegis-governance-core`, CDK): the gateway Lambda reads `/aegis/kill-switch` **first**, 15 s TTL cache, **fail-closed if unreadable**, denies with `guardrail_action=KILL_SWITCH` and writes the denial to the append-only audit; engage/read IAM managed policies (value-based SoD is runbook-enforced there — IAM cannot inspect a parameter value) | **LIVE + validated** — engaged → canary 403 within one cache TTL, disengaged → allow, both audited (`DEPLOYED-AND-VALIDATED.md` Run 11) | platform `infra/cdk/governance_core/governance_core_stack.py`, `DEPLOYED-AND-VALIDATED.md` |
| **Agent packs on AgentCore** (benefits, governed-core **1.8.0**): the pack's own `/ben-<env>-eligibility/kill-switch` (+ optionally the platform-wide parameter, `-c global_kill_switch=/aegis/kill-switch`) is read FIRST by the gateway REQUEST interceptor (403 + `DENIED` WORM record in the acting tenant's ledger), by every tool Lambda (`telemetry.instrument` → `KillSwitchEngaged`, so the workflow stops at its next state) and by the Runtime (new invocations refused; a running session stops at its next model call). Engage / disengage = two `AWS_IAM` function URLs, one managed policy each; the actor is the IAM-verified caller and the controller refuses same-identity release (`DENIED` record); every state change is a `COMMITTED` row in the base ledger's `KILL-SWITCH` chain | **LIVE + validated 2026-09-03** — `scripts/kill_switch_proof.py` **29/29 PASS** on `ben-mt5` (2 tenants, real AgentCore Runtime): time-to-effect at the gateway **13.9 s**; interceptor 403 + per-tenant DENIED records; direct tool invoke and a Step Functions execution fail with `KillSwitchEngaged` at the first state; a new runtime invocation refused and a **running session stopped mid-session**; engage-only role refused at the disengage URL by IAM, over-privileged identity refused releasing its own engagement (DENIED record), second identity releases; base-ledger `KILL-SWITCH` chain hash-linked with WORM copies; full recovery; 0-unexpected-errors sweep after. `benefits/evidence/AGENTCORE-KILL-SWITCH-2026-09-03.md` | governed-core `controls/kill_switch.py`, `kill_switch_control.py`; benefits `cdk/ben_stacks/compute_stack.py`, `lib/runtime/agent.py`, `DEPLOYMENT-GUIDE.md` §1c |

### Design decisions on the AgentCore path (grounded in AWS documentation)

- **Parameter Store, not AppConfig.** One JSON flag per deployment, read with `GetParameter`. AWS AppConfig is the purpose-built feature-flag service (immediate disable "without rolling back the deployment", CloudWatch-alarm auto-rollback) and remains a valid future home; Parameter Store was kept for parity with the reference stack and because a containment flag needs no deployment strategy, validator or gradual rollout. Throughput: the default is **40 TPS shared across `GetParameter`/`GetParameters`/`GetParametersByPath`** (higher-throughput option: 10,000 TPS for `GetParameter`, billed per interaction) — with a 15 s cache per warm execution environment the pack reads a few times a minute, not per call.
- **Cache, fail-closed.** AWS's documented pattern for Lambda reads is the **Parameters and Secrets Lambda Extension** (in-process cache, default TTL 300 s); the pack implements the same idea in-process with a containment-grade 15 s TTL, and treats an unreadable or malformed value as **engaged**.
- **Interceptor short-circuit.** A REQUEST interceptor that returns `transformedGatewayResponse` makes the gateway "respond with that content immediately" — the target is never invoked (AgentCore Gateway interceptor types doc).
- **IAM-verified actor + SoD.** For a function URL with `AuthType: AWS_IAM`, Lambda populates `requestContext.authorizer.iam.userArn` / `userId` / `accountId` (Lambda dev guide, "Invoking function URLs"), so the recorded actor is never self-declared; two functions ⇒ two `lambda:InvokeFunctionUrl` grants ⇒ IAM separation of duties, plus the in-code same-identity refusal (exact ARN or same assumed role) that IAM alone cannot express.

### Fast stops still available (manual, CloudTrail-logged) — for a deployment on a core < 1.8.0

| # | Action | Scope | Time to effect | Who | Audited where | Reversal |
|---|---|---|---|---|---|---|
| A1 | Add a Cedar `forbid(principal, action, resource)` policy to the pack's policy engine (`create-policy`, engine already ENFORCE) | every tool call through the gateway, every identity | seconds after the policy reaches ACTIVE (~10–60 s) | anyone with `bedrock-agentcore:CreatePolicy` on the engine | CloudTrail (control plane); each denied call is visible in the gateway request log; **not** in the WORM ledger | delete the policy |
| A2 | Delete the gateway's Lambda targets (`delete-gateway-target`) or the gateway | tool calls | ~seconds; re-create takes minutes (the CDK provider re-attaches) | gateway admin | CloudTrail | `cdk deploy` |
| A3 | Disable the Runtime endpoint / delete the runtime (`delete-agent-runtime`) | the agent (model calls stop; tools stay reachable to other callers) | seconds | runtime admin | CloudTrail | relaunch (~3 min CodeBuild) |
| A4 | Lambda reserved concurrency = 0 on the tool functions | tools (workflow + gateway) | immediate | Lambda admin | CloudTrail; invocations throttle (visible as Throttles metric) | remove the reservation |
| A5 | IAM: deny `bedrock:InvokeModel*` on the runtime/tool roles | model calls | immediate on next call | IAM admin | CloudTrail | remove the deny |

None of A1–A5 is separation-of-duties-protected or writes an ENGAGE/DISENGAGE record into the hash-chained
ledger; A2/A3 are destructive to state. They remain the fallback for packs not yet on governed-core 1.8.0.

### Drill (quarterly) — AgentCore path

1. Responder (engage-only role): `POST {reason}` to `KillSwitchEngageUrl` → 200, `state.engaged=true`, `audit.stored=true`.
2. Within 15 s: a caseworker's `tools/list` → 403 "containment engaged"; a runtime invocation → `guardrail_action: KILL_SWITCH`.
3. Responder tries `KillSwitchDisengageUrl` → 403 from IAM (no `InvokeFunctionUrl` on that function).
4. Security lead (disengage-only role): `POST {reason}` → 200, `state.engaged=false`, `state.released.engaged_by` = the responder's ARN.
5. Verify the base ledger's `KILL-SWITCH` chain has ENGAGE + DISENGAGE `COMMITTED` and each tenant ledger has the `DENIED` calls; `trace_case.py` shows them under the session.

## Relationship to the incident runbook

The Kill Switch is the **containment step** for SEV-1/SEV-2 in
[`INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md): engage first, investigate second, disengage only
after the security lead signs off. Drill it quarterly (engage → verify a canary call is denied →
disengage with the second identity → verify the audit holds all three events).

## AGP versioning note

AGP v1.0 defines 8 controls; the Kill Switch composes two of them (deny-by-default gateway,
token budgets) into a **named, one-command containment control** with SoD on release. It is
**proposed for AGP v1.1 as control 9 ("Containment")** — proposed here, adopted only through the
versioning process in [`../14-GOVERNANCE-PATTERN-VERSIONING.md`](../14-GOVERNANCE-PATTERN-VERSIONING.md).
Until adopted, packs may cite it as a platform capability, not an AGP requirement.
