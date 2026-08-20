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
