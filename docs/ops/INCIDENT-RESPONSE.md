# Incident Response Runbook — Aegis Governed Agent Platform

> **Status & maturity (read first).** Incident response is a **day-2 operational commitment** the
> customer/Delivery Partner owns (RACI item 13,
> [`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md)). This runbook gives the
> structure, detection sources, and two worked playbooks (key compromise, prompt-injection
> incident) a pilot adopts and staffs. Detection and containment mechanisms cited as live are proven
> in [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md).

## 1. Severity levels

| Sev | Definition | Example | Response |
|---|---|---|---|
| **SEV-1** | Confirmed compromise or regulated-data exposure | KMS key compromise; exfiltration of PII/PHI/FTI/CJI | Immediate; incident commander + executive + legal |
| **SEV-2** | Control failure without confirmed exposure | Fail-open regression; approval-replay success; audit-write failures | Urgent; on-call + security lead |
| **SEV-3** | Degradation / anomaly | Guardrail-intervention spike; grounding-score drop; DLQ growth | Same-day; on-call |
| **SEV-4** | Low-impact / informational | Single anomalous deny; transient throttle | Triage in normal ops |

## 2. Detection sources

| Source | Signals |
|---|---|
| CloudTrail | Unexpected control-plane API calls; IAM/KMS/policy changes; root activity |
| GuardDuty | Threat findings (credential exfiltration, anomalous API, recon) |
| Security Hub | Aggregated standard findings; posture regressions |
| AWS Config | Resource non-compliance (public S3, disabled logging, drift) |
| Guardrail metrics | Intervention rate spike; PII-filter hits; denied-topic hits |
| Audit anomalies | Deny surge; approval-replay attempts; audit-write failures; unusual data-class access |
| CloudWatch / X-Ray | Latency/error SLO breach; DLQ depth; circuit-breaker opens |

Continuous-monitoring wiring maps to `continuous-monitoring` (CA-7, SI-4, AU-6) in
[`../../governance/controls/control_mappings.yaml`](../../governance/controls/control_mappings.yaml).

## 3. Lifecycle

1. **Detect & declare** — an alarm or report opens an incident; assign severity + incident commander.
2. **Triage** — scope blast radius using CloudTrail + the append-only audit (which cannot have been
   tampered with — Runs 1, 6); identify affected data class, agents, tokens, keys.
3. **Contain** — apply the least-disruptive control that stops the bleeding (section 4).
4. **Eradicate** — remove the root cause (revoke, rotate, patch, disable, fix fail-open path).
5. **Recover** — restore service; verify controls green; watch for recurrence.
6. **Post-incident review** — blameless PIR; feed findings to the gap-closure backlog.

## 4. Containment actions (least-disruptive first)

| Action | How | When |
|---|---|---|
| **Revoke tokens** | Invalidate/rotate the affected principal's session; shorten JWT lifetime; force re-auth via Cognito | Suspected token theft / confused-deputy |
| **Disable a tool in the registry** | Mark the tool/connector revoked; the gateway denies it at load and at runtime (manual circuit breaker) | Tool poisoning / misbehaving connector |
| **Freeze consequential actions** | Halt the human-gate release path; queued actions hold; no consequential step runs without a valid bound approval anyway (Runs 2, 5) | Suspected approval-flow abuse |
| **KMS key disable** | Disable the affected per-class CMK to halt decryption across that data class | Confirmed key compromise (SEV-1) |
| **KMS key rotate** | Rotate the CMK; re-encrypt as needed | Post-containment eradication |
| **Isolate agent** | Disable the agent's manifest/identity so it cannot authorize | Compromised agent |
| **Break-glass WORM handling** | Evidence is immutable; a legitimate emergency retrieval or teardown uses the authorized break-glass principal with `s3:BypassGovernanceRetention` (pilot GOVERNANCE profile). **Production COMPLIANCE profile forbids deletion before expiry even by root** — evidence cannot be destroyed to cover an incident | Only under authorized, audited break-glass; the bypass itself is logged |

Every containment action is itself an audited, accountable decision. Disabling a CMK stops
decryption but does not delete data or evidence; WORM evidence remains intact through any incident.

## 5. Comms

- **Internal:** incident channel; incident commander owns updates on a fixed cadence by severity.
- **External / regulatory:** legal and privacy determine breach-notification obligations per regime
  (HIPAA, CJIS, IRS 1075, FERPA, state law). Notification timelines are regime-specific and
  customer-owned; this runbook does not assert a specific deadline.
- **Customer/tenant:** notify affected agent owners and data-class owners.

## 6. Playbook A — key compromise (SEV-1)

1. **Detect:** GuardDuty credential-exfiltration finding, or CloudTrail showing anomalous KMS use.
2. **Triage:** identify which per-class CMK (CJI/FTI/PHI/EDU/public) and what it protects; pull the
   append-only audit for decisions in the window (tamper-evident, Run 1).
3. **Contain:** **disable the affected CMK** (halts decryption for that data class); revoke/rotate
   any exposed downstream credentials; freeze consequential actions for affected agents.
4. **Eradicate:** rotate the CMK; rotate any grants/roles referencing it; verify no long-lived
   credentials exist (scoped per-call tokens are the design — confirm no drift).
5. **Recover:** re-enable service on the rotated key; confirm SSE-KMS reads/writes succeed; verify
   WORM evidence intact (it cannot have been deleted).
6. **PIR:** how was the key exposed; tighten key policy, add/verify data-key caching limits, confirm
   least-privilege on KMS grants.

## 7. Playbook B — prompt-injection incident (SEV-2/3)

1. **Detect:** guardrail denied-topic/PII spike, an anomalous tool-attempt pattern in the audit, or
   a report that an agent attempted something out of scope.
2. **Triage:** pull the agent's audit lineage. Confirm the **blast radius was bounded by design**:
   the deny-by-default gateway means injection cannot exceed the caller's grants, and any
   consequential action still required a valid bound approval (Runs 2, 3, 5). Determine whether the
   injection source was user input or retrieved (RAG) content.
3. **Contain:** if a specific tool or connector is implicated, **disable it in the registry**; if a
   KB source is poisoned, remove it from the grounding set; tighten the guardrail denied topics.
4. **Eradicate:** add the injection pattern to the eval suite (prompt-injection category); re-run
   evals; adjust grounding threshold or masking as indicated.
5. **Recover:** re-enable the tool/KB once evals pass at `min_pass_rate`; monitor guardrail metrics.
6. **PIR:** confirm no unauthorized consequential action occurred (audit is authoritative), record
   the pattern, and update model-risk validation.

## 8. Post-incident review

Every SEV-1/SEV-2 gets a blameless PIR: timeline, detection latency, containment effectiveness,
root cause, and action items. Action items land in [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md).
Recurring themes (for example a fail-open regression) become new negative-security tests
(`demo/test_negative_security.py`, `demo/test_fail_closed.py`) so the same incident cannot recur
undetected. The audit trail's append-only + WORM properties (Runs 1, 6) mean the incident record
itself cannot be quietly altered after the fact.
