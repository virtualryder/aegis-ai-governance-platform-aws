# 13 — Cost Model: Aegis Platform Core (Monthly AWS Run Cost)
### Pilot vs Production, us-east-1 on-demand list prices

> **MODEL ASSUMPTION — illustrative estimate** built from published us-east-1 on-demand list
> prices as of mid-2026; prices and token economics change frequently; validate with the AWS
> Pricing Calculator and your AWS account team before quoting. **Bedrock token volume is the
> dominant, workload-dependent variable** — every Bedrock line below is the sensitivity driver.
> No figure here is a quote.

This models the run cost of the **Aegis platform core** — the governed control plane (MCP
gateway, Cedar authorization, human-approval service, masking, WORM audit, token budgets) plus
the Bedrock inference of the agents it governs. It complements
[`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md) (how spend is
allocated per department) and [`12-COMMERCIAL-PACKAGING.md`](12-COMMERCIAL-PACKAGING.md) (what an
engagement costs). This file answers: *what does the platform cost AWS-side, per month, to run?*

---

## Scenario assumptions

| Assumption | **Pilot** (1 governed agent, one dept) | **Production** (platform + governed agent portfolio) |
|---|---|---|
| Governed requests/month (through the MCP gateway) | ~10,000 | ~500,000 |
| Active users (MAU) | ~50 | ~2,000 |
| Bedrock tokens/month (governed agents, aggregate) | ~5M input + ~1M output | ~250M input + ~50M output |
| Model class | Mid-tier Claude (Sonnet-class): ~$3.00/M input, ~$15.00/M output tokens `[MODEL ASSUMPTION]` | same |
| Architecture | The validated serverless golden path (API Gateway → Lambda gateway → Cedar/AVP → Step Functions approvals → Bedrock), private-by-default (VPC interface endpoints even in pilot) | same, plus production hardening (NAT, WAF, CloudFront) |
| Per-request shape | ~2 API calls, ~5 Lambda invocations (gateway, authorizer, masker, connector, audit), ~15 Step Functions state transitions (approval workflows), ~10 DynamoDB writes + 20 reads (audit, budgets, approval state) | same |

Note: agent-suite verticals (slg / edu / healthcare / hcls) carry their own suite TCO models;
this model is the platform-core view. When Aegis governs one of those suites, use the suite
model for inference volume and this model for the control-plane baseline — don't double-count
the Bedrock line.

## Monthly cost estimate (us-east-1, on-demand list, mid-2026)

| Line item | Basis | **Pilot ($/mo)** | **Production ($/mo)** |
|---|---|---:|---:|
| **Bedrock inference** ← *sensitivity driver* | Sonnet-class; 5M in + 1M out (pilot) / 250M in + 50M out (prod) | **30** | **1,500** |
| Bedrock Guardrails ← *scales with request volume* | Content filters, prompt-side; ~2 text units/request @ ~$0.75/1K units | 15 | 750 |
| Lambda | ~5 invocations/request; 512 MB × ~800 ms | 1 | 17 |
| API Gateway (HTTP API) | ~2 calls/request @ ~$1.00/M (JWT authorizer path) | 1 | 1 |
| Step Functions (Standard) | ~15 state transitions/request (approval + saga flows) @ ~$25/M | 4 | 188 |
| DynamoDB (on-demand) | ~10 WRU + 20 RRU/request (audit, atomic token budgets, approvals) + storage | 1 | 11 |
| S3 + Object Lock (WORM audit) | 5 GB pilot / 200 GB prod + requests | 2 | 7 |
| KMS | $1/CMK (4 pilot / 6 prod — audit, manifest-signing, data keys) + ~20 requests/request @ $0.03/10K | 5 | 36 |
| Cognito | MAU-based (~$0.015/MAU); 50 pilot / 2,000 prod (MFA pool as validated) | 1 | 30 |
| CloudWatch | Logs ingest + metrics + dashboards (audit-heavy control plane logs more) | 3 | 75 |
| VPC interface endpoints | ~$7.30/endpoint-mo + data; 5 endpoints pilot / 8 prod (Bedrock, KMS, STS, Logs, AVP…) | 36 | 68 |
| NAT Gateway | Prod only; ~$33/mo + ~100 GB processed | — | 37 |
| WAF | Prod only; web ACL + 5 rules + request fees on the gateway endpoint | — | 11 |
| CloudFront | Prod only; reviewer/operator UI distribution, low-GB tier | — | 10 |
| **TOTAL** | | **~$99/mo** | **~$2,741/mo** |

**Sensitivity (one line):** 2× Bedrock token volume ≈ **+$1,500/mo** at production scale
(inference is ~55% of the production total); the governance baseline (everything else,
~$1.2K/mo) is comparatively flat — that flatness is the FinOps argument for a shared control
plane. Amazon Verified Permissions per-authorization fees are folded into the gateway
assumptions; re-check AVP request pricing at your authorization-call volume.

Rounding: whole dollars; sub-dollar lines shown as $1. Annualized production: ~$32.9K/yr.

## What's NOT included

- Personnel (platform operators, approvers/reviewers, security team)
- ProServe / SI partner delivery fees (see `12-COMMERCIAL-PACKAGING.md`, `PILOT-SOW-TEMPLATE.md`)
- Data egress at scale (cross-account CUR delivery, bulk export)
- AWS enterprise support plan (typically 3–10% of spend)
- Non-prod environments (dev/test/staging — commonly +30–60% of the prod infra baseline)
- Multi-account / multi-tenant topology (per [`11-MULTI-TENANCY.md`](11-MULTI-TENANCY.md), a
  per-tenant spoke re-pays the isolation baseline — VPC endpoints, KMS, audit — per tenant)

## Chargeback hook

Per [`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md): the Bedrock
line is attributable per department via application inference profiles + cost-allocation tags;
the governance baseline is a shared platform cost — allocate it by governed-request share or as
a flat platform fee. This table gives the CFO the two numbers that conversation needs.

---

*Related: [`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md) ·
[`12-COMMERCIAL-PACKAGING.md`](12-COMMERCIAL-PACKAGING.md) · `Aegis-ROI-Worksheet.xlsx` (repo
root) · [`PILOT-SOW-TEMPLATE.md`](PILOT-SOW-TEMPLATE.md)*
