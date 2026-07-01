# Operational Readiness — Aegis Governed Agent Platform

> **Status & maturity (read first).** Day-2 operations is honestly assessed as *mostly absent*
> today in [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md) and is a blocker for a
> production pilot. This document establishes the SLO/SLI targets, operating standards, and
> resilience plans a pilot must adopt. Where a mechanism is already proven live it cites the
> [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md) Run; otherwise it is a target
> the customer/Delivery Partner owns (RACI item 13,
> [`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md)). Reviewed against the
> **AWS Well-Architected Framework** and the **Agentic AI Lens** as the day-2 review checklist.

## 1. SLOs and SLIs

Targets below are **pilot starting points**; the customer ratifies them in the pilot SOW.

| SLO | SLI (how measured) | Pilot target |
|---|---|---|
| Availability (control plane) | Successful authorized requests / total, from CloudWatch + API GW metrics | 99.5% monthly |
| Decision latency (authorize + guardrail) | p95 gateway end-to-end latency (X-Ray) | p95 < 1.5s (excluding model generation) |
| Model-call success | Non-throttled, non-error Bedrock invocations / total | 99% |
| Approval SLA (human gate) | Time from gate-pause to reviewer decision | p90 < 4 business hours; hard timeout escalates |
| Audit-write success | Audit PutItem success / decisions | 100% (audit-write failure fails the consequential/sensitive action closed) |

SLIs are emitted from CloudWatch metrics, API Gateway access logs, and X-Ray traces
([`../02-REFERENCE-ARCHITECTURE.md`](../02-REFERENCE-ARCHITECTURE.md) §8). Error budgets are tracked
per SLO; budget burn triggers a change freeze on the affected component.

## 2. Expected volumes and concurrency

Sizing is workload-specific; the pilot captures actuals during shadow/canary. Planning defaults for
a single service-desk-style agent:

| Dimension | Planning default | Notes |
|---|---|---|
| Requests | 1-5 req/s steady, 20 req/s peak | Per pilot agent; scale is per-account |
| Concurrent executions | Lambda reserved concurrency per function | Set to protect downstream + budget |
| Consequential actions | Small fraction of total | Each routes to the human gate; queue depth is the constraint |
| Model tokens | Bounded by `budget.monthly_token_cap` | Hard cap enforced before spend (Run 8) |

The atomic budget-reservation table serializes concurrent reservations so parallel calls cannot
oversell the cap (Run 8). Lambda reserved/provisioned concurrency is the primary knob for protecting
downstream systems and staying within service quotas.

## 3. Service quotas and throttling behavior

| Service | Quota to watch | Behavior at limit | Mitigation |
|---|---|---|---|
| Amazon Bedrock | Per-model requests-per-minute and tokens-per-minute (account/region) | `ThrottlingException` | Retry with backoff; task-based routing (cheap model to classify); request quota increase |
| AgentCore Gateway/Runtime | Per-service limits (VPC/PrivateLink/CFN supported) | Throttle/error | Provision headroom; monitor; quota increase |
| Lambda | Concurrent executions | Throttle | Reserved concurrency + DLQ |
| DynamoDB | On-demand or provisioned throughput | `ProvisionedThroughputExceeded` | On-demand tables; exponential backoff |
| API Gateway | Account/stage rate + burst | 429 | Stage throttling tuned to SLO |
| KMS | Requests-per-second per key | Throttle | Data-key caching where safe |

Throttling is treated as a *retryable* condition, never as an authorization result: a throttled
authorization or guardrail call still resolves to **deny** (fail-closed), it does not fall through
to allow.

## 4. Retry, idempotency, and saga compensation

The connector standard is proven in Run 9 and is the reference for all downstream integrations:

- **Idempotency:** every consequential downstream call carries an `idempotency_key`; a repeat with
  the same key returns the original result and writes no duplicate (Run 9: two `create_ticket` calls
  -> same ticket, `idempotent:true`, single row).
- **Saga compensation:** downstream steps run inside a Step Functions saga with an explicit
  `Catch -> Compensate` path; a downstream failure voids the partial effect (Run 9: failure ->
  ticket voided, `FAILED (CompensatedRollback)`, no orphan/duplicate).
- **Retry standard:** transient errors (throttling, 5xx, timeouts) retry with exponential backoff
  and jitter and a bounded attempt count; non-transient errors do not retry and route to the DLQ.

## 5. DLQ and circuit breakers

- **Dead-letter queues:** async invocations and connector calls have SQS DLQs; DLQ depth is alarmed
  and drained by an operator runbook. A message in the DLQ never silently disappears.
- **Circuit breakers:** repeated downstream failures open a breaker for that tool/connector so the
  agent fails fast (and closed) rather than hammering a failing system; the breaker half-opens on a
  timer. A tool can also be disabled in the registry (see
  [`INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md)) as a manual breaker.

## 6. Backup, restore, RTO/RPO

| Store | Protection | RPO | RTO (pilot target) |
|---|---|---|---|
| DynamoDB audit / approvals / budget | Point-in-time recovery (PITR) enabled | <= 5 min (PITR) | < 1 hour to restore a table |
| S3 WORM evidence | Object Lock + versioning; COMPLIANCE profile in prod | 0 (immutable, versioned) | Immediate (objects not deletable) |
| Cedar policies / manifests | Versioned in source control + signed | Last commit | Redeploy from IaC |
| IaC / Lambda code | Source control | Last commit | Redeploy via runbook |

PITR is enabled on the audit table (Run 1). Restore procedures are exercised as part of pilot
onboarding, not assumed. The append-only + WORM design means evidence integrity survives a restore:
you can recover the table, but you can never rewrite history.

## 7. Regional-failure plan

The reference deployment is single-region (CloudFront-scoped WAF must live in `us-east-1`; GovCloud
for High-impact/CJI/FTI). A regional-failure posture for a pilot:

- **Evidence durability:** cross-region replication of the WORM evidence bucket and a cross-account
  log archive (production profile) so audit/evidence survives a regional event.
- **Recovery model:** infrastructure-as-code redeploy into a secondary region from the same
  templates; DynamoDB restore from PITR or global tables if the RPO warrants it.
- **Honest current state:** multi-region and multi-account isolation are **documented, not
  deployed** (residual risk RR-3). A pilot chooses a single region and accepts that failure mode, or
  funds the multi-region build.

## 8. Model-outage and fallback policy

The **Model Gateway** ([`../02-REFERENCE-ARCHITECTURE.md`](../02-REFERENCE-ARCHITECTURE.md) §4)
centralizes all Bedrock access and enforces an **approved model-profile allowlist per agent** plus a
**retry/fallback model policy**:

- On throttling or a transient model error, retry with backoff, then fall back to an approved
  alternate model profile on the allowlist (never to an unapproved or out-of-account model).
- Fallback stays within the guardrail and budget envelope; a fallback model is still masked, still
  guarded, still audited, still capped.
- If no allowed model is available, the call **fails closed** (deny), it does not proceed ungoverned.
- Prompt versions are hash-pinned and drift-failing, so a fallback cannot silently change behavior.

## 9. Cost alarms

- **AWS Budgets** alarms per department/agent, aligned to `budget.alert_thresholds[]` in the agent
  manifest, with the hard `monthly_token_cap` enforced at the gateway before spend (Run 8).
- Cost-allocation tags on application inference profiles flow to Cost Explorer / CUR for
  chargeback reconciliation (RACI item 14). A budget breach alarms finance and the agent owner and
  can trip the gateway to throttle/deny over-budget calls.

## 10. Model and prompt drift monitoring; eval-rerun triggers

- **Drift monitoring:** model-invocation logging + the grounding/relevance scores are tracked over
  time; a sustained drop in grounding scores or a rise in guardrail interventions is an alarm.
- **Eval-rerun triggers:** the eval suite (minimum-bar point 6) is re-run automatically on any
  **model version change**, **prompt-version change**, **guardrail policy change**, or **pack
  change**. A promotion is blocked if the suite falls below `evals.min_pass_rate`
  ([`../06-HALLUCINATION-AND-EVALUATION.md`](../06-HALLUCINATION-AND-EVALUATION.md),
  [`../../governance/onboarding/MINIMUM-BAR.md`](../../governance/onboarding/MINIMUM-BAR.md)).

## 11. Well-Architected + Agentic AI Lens review

The pilot runs a **Well-Architected Framework Review** across the six pillars (Operational
Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability) and
applies the **AWS Well-Architected Agentic AI Lens** for agent-specific concerns: authorization
outside the reasoning loop, human-in-the-loop for consequential actions, grounding/hallucination
control, tool/registry governance, token-budget control, and end-to-end auditability. The lens is
the day-2 review checklist; findings feed the gap-closure backlog. This is a design-time and
recurring review, not a one-time gate.

## 12. What is proven vs to-build

- **Proven live (DA):** atomic budget cap (Run 8), idempotency + saga compensation (Run 9), PITR on
  audit (Run 1), WORM durability (Run 6), fail-closed on control-path errors (Run 2).
- **To-build for pilot (CC/P):** dashboards and alarms wired to the SLOs above, DLQ/circuit-breaker
  operationalization, restore drills, multi-region/multi-account resilience, drift dashboards, and
  the Well-Architected + Agentic AI Lens review cadence.
