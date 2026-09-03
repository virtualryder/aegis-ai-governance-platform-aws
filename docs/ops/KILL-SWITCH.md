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

## Where it is actually wired today (2026-09-02 inventory — read before showing a customer)

There are TWO deployed request paths and the Kill Switch is wired into only one of them.

| Path | Kill Switch state | Evidence |
|---|---|---|
| **Platform reference stack** (`aegis-governance-core`, CDK): the gateway Lambda reads `/aegis/kill-switch` **first**, 15 s TTL cache, **fail-closed if unreadable**, denies with `guardrail_action=KILL_SWITCH` and writes the denial to the append-only audit; engage/read IAM managed policies | **LIVE + validated** — engaged → canary 403 within one cache TTL, disengaged → allow, both audited (`DEPLOYED-AND-VALIDATED.md` Run 11) | platform `infra/cdk/governance_core/governance_core_stack.py`, `DEPLOYED-AND-VALIDATED.md` |
| **Agent packs on AgentCore** (benefits `v0.3.0-pilot-rc1`: AgentCore Gateway + Cedar policy engine + REQUEST interceptor + tool Lambdas + Runtime): **nothing reads the switch.** The pack's deny-by-default is Cedar; there is no single flag that stops it | **NOT WIRED** — the fast stops below are manual API calls, not one command, and none of them is recorded in the pack's WORM ledger by design | this table |

### Fast stops available TODAY in the AgentCore path (all manual, all reversible, time-to-effect measured or estimated)

| # | Action | Scope | Time to effect | Who | Audited where | Reversal |
|---|---|---|---|---|---|---|
| A1 | Add a Cedar `forbid(principal, action, resource)` policy to the pack's policy engine (`create-policy`, engine already ENFORCE) | every tool call through the gateway, every identity | seconds after the policy reaches ACTIVE (~10–60 s) | anyone with `bedrock-agentcore:CreatePolicy` on the engine | CloudTrail (control plane); each denied call is visible in the gateway request log; **not** in the WORM ledger | delete the policy |
| A2 | Delete the gateway's Lambda targets (`delete-gateway-target`) or the gateway | tool calls | ~seconds; re-create takes minutes (the CDK provider re-attaches) | gateway admin | CloudTrail | `cdk deploy` |
| A3 | Disable the Runtime endpoint / delete the runtime (`delete-agent-runtime`) | the agent (model calls stop; tools stay reachable to other callers) | seconds | runtime admin | CloudTrail | relaunch (~3 min CodeBuild) |
| A4 | Lambda reserved concurrency = 0 on the tool functions | tools (workflow + gateway) | immediate | Lambda admin | CloudTrail; invocations throttle (visible as Throttles metric) | remove the reservation |
| A5 | IAM: deny `bedrock:InvokeModel*` on the runtime/tool roles | model calls | immediate on next call | IAM admin | CloudTrail | remove the deny |

None of A1–A5 is separation-of-duties-protected, none writes an ENGAGE/DISENGAGE record into the hash-chained
ledger, and A2/A3 are destructive to state (sessions, sign-off waits). They are what an operator can do
*right now*; they are not "the Kill Switch".

### The build to make the Kill Switch real for the packs (tracked as a task)

The pack already has two components that see every request before anything else runs: the gateway
**REQUEST interceptor** (every `tools/call`) and the **runtime agent** (every model call). Wiring the
platform's own design in there:

1. Interceptor: read `/aegis/kill-switch` (short-TTL cache, **fail-closed if unreadable**), on `engaged`
   return the 403 deny **and** `write_audit` an `INTENT/DENIED kill_switch` record into the tenant's WORM
   ledger (correlation keys included) — containment precedes evaluation, and the denial is evidence.
2. Tool Lambdas (workflow hop, no interceptor): the same check in `telemetry.instrument` before the handler
   runs, so an in-flight Step Functions execution stops at its next state.
3. Runtime: check before each model call; refuse the session with the same audited reason.
4. Engage/disengage: the platform's SSM parameter + the two IAM managed policies (engage-only /
   disengage-only identities) — SoD in IAM, exactly as the reference stack does; every state change lands
   in the ledger via `write_audit`.
5. Live gate: engage → every tool call and the runtime refused within ≤ 30 s, WORM shows ENGAGE + the
   denials, `trace_case` shows them under the session; disengage by a *different* identity → allowed again.

Until that lands, the honest customer sentence is: "The platform reference gateway has a live, audited,
fail-closed Kill Switch; the AgentCore agent packs can be stopped in seconds by policy or infrastructure
actions (A1–A5) but do not yet have the one-command, audited switch — it is the next build."

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
