# AWS Support case: CloudTrail "Trails per region" increase

**Status:** drafted 2026-09-09, **not submitted**. It could not be filed programmatically —
see "Why this is not automated" below. Paste it into the AWS console to submit.

**Where:** AWS Console → Support → Create case → *Service limit increase*
(direct link: https://console.aws.amazon.com/support/home#/case/create)

---

## Case fields

| Field | Value |
|---|---|
| Case type | Service limit increase |
| Limit type | CloudTrail |
| Region | US East (N. Virginia) / us-east-1 |
| Limit name | Trails per region |
| Current limit | 5 |
| Requested limit | **10** |
| Severity | Low / General guidance |

**Subject**

    Increase CloudTrail "Trails per region" from 5 to 10 in us-east-1

**Body**

> We run a governance and audit-evidence platform for LLM workloads on Amazon Bedrock
> AgentCore. Each deployed compliance overlay pack requires **two** CloudTrail trails:
>
>   1. an account-wide **capture-all** management-events trail, and
>   2. a **data-events** trail writing to an S3 Object Lock (WORM) bucket, which is the
>      tamper-evident audit record an auditor is shown.
>
> The two trails are separate by design: the WORM data-events trail must have a retention
> and deletion posture that the general management trail does not, so they cannot be merged
> without weakening the evidence claim.
>
> In us-east-1 we currently hold 5 trails: one general management trail, one for the shared
> governance core, and two per deployed pack. At the default limit of 5 we cannot run two
> overlay packs concurrently in a single account, and our full-portfolio validation gate —
> which deploys a pack from zero, exercises it, and tears it down — fails at
> `CreateTrail` with:
>
>     Invalid request provided: User: <account> already has 5 trails in us-east-1.
>     (Service: CloudTrail, Status Code: 400)
>
> A limit of 10 covers the shared core plus four overlay packs with headroom for one
> concurrent validation run. We are not asking for an increase in event volume or data
> events — only the number of distinct trail configurations.

---

## Why this is not automated

Both programmatic routes are closed on this account:

- **Service Quotas** lists the limit as `cloudtrail / L-1568E18E "Trails per region" = 5`
  with **`Adjustable: false`**, so `request-service-quota-increase` is refused.
- **The AWS Support API** (`aws support create-case`) requires a Business or Enterprise
  support plan; this account returns `SubscriptionRequiredException`.

So a human has to submit it in the console. Everything needed is above.

---

## What it unblocks, and what it does not

**Unblocks:** running the benefits full-portfolio gate while another pack stays deployed.
On 2026-09-09 the gate reached `ben-fp2-observability` and rolled back on this exact limit,
with four of the five trails held by live deployments (pharmacovigilance ×2,
`aegis-governance-core` ×1, and one pre-existing management trail).

**Does not fix, and should not be described as fixing:** anything about the governance
controls themselves. This is a service quota, not a defect. It was found only because the
policy-name collision above it was fixed first — the gate had never previously got far
enough to reach the observability stack.

**Interim measure taken instead:** the live pharmacovigilance deployment was torn down
(operator-approved) to free two trail slots. That is a workaround, not a resolution — a
customer running two overlay packs in one account hits the same wall on their first deploy,
which is why the quota increase is worth filing regardless.
