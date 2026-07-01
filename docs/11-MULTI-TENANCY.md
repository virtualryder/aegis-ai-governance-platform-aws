# 11 — Multi-Tenancy

> **Status & maturity (read first).** This document is **Designed**. The Aegis controls
> that back it — append-only audit, WORM evidence, Bedrock Guardrail, the human gate,
> the fail-closed gateway, Cedar authorization, token budgets — are deployed and
> live-validated **as a single-account pilot** (see
> [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md), DEPLOYED-AND-VALIDATED.md). The
> multi-tenant topologies below are the reference design for serving multiple tenants on
> that same governed core; the deployed pilots are single-account. Multi-account
> data-class isolation via Control Tower is documented and not yet deployed.

Aegis serves multiple tenants (agencies, departments, customers, business units) on one
governance core. "Tenant" is orthogonal to "data class": a tenant is *who owns the
workload and the bill*; a data class (public/pii/phi/cji/fti/edu) is *what regime the data
falls under*. Both must be isolated. This doc defines the three tenancy models, their
isolation guarantees, and when to choose each.

## 1. The three models

| Model | Isolation boundary | Blast radius | Cost / operational overhead | Best for |
|---|---|---|---|---|
| **SILO** | AWS account per tenant (Control Tower) | Smallest — account boundary | Highest — an account, baseline, and stack per tenant | Regulated data, sovereignty, few large tenants |
| **POOL** | Shared control plane; per-tenant logical isolation (tenant attribute in Cedar context + per-tenant KMS keys / table + S3 prefixes) | Largest — one plane, many tenants | Lowest — one stack, many tenants | Many small tenants, lower-sensitivity data, cost-sensitive |
| **BRIDGE** | Shared plane for the common tier; siloed accounts for the sensitive tier | Mixed by tier | Medium | Mixed portfolios — a shared road plus a few regulated tenants |

### SILO — account per tenant

Each tenant gets its own AWS account under an AWS Organizations / Control Tower structure
(see [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) on the
account-per-data-class topology). The governance core (this repo's module /
CloudFormation) is deployed once per tenant account. Isolation is the AWS account boundary
itself: separate CMKs, separate DynamoDB/S3, separate IAM, separate audit trail, separate
bill. This is the strongest, simplest-to-reason-about model and the default for regulated
data.

**Isolation guarantee:** hard. No shared data plane; cross-tenant access requires an
explicit, auditable cross-account grant that does not exist by default. A compromise or
runaway in one tenant cannot reach another's data, keys, or budget.

### POOL — shared plane, per-tenant logical isolation

One deployment of the governance core serves many tenants. Isolation is enforced in the
control plane and the data layout rather than by an account boundary:

- **Tenant attribute in the authorization context.** Every request carries a verified
  `tenant_id` (from the JWT claim, never client-supplied). The Cedar policy predicate (see
  [`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) §3) gains a clause:
  `AND resource.tenant == principal.tenant`. A call that crosses tenants is denied
  by default, like any other authorization failure, and the denial is audited.
- **Per-tenant KMS keys.** Each tenant's data is encrypted under its own CMK, so key
  policy is a second, independent isolation layer beneath the application check.
- **Per-tenant table / item partitioning.** Either a table-per-tenant or a shared table
  with `tenant_id` as the partition-key prefix and a leading-key IAM condition
  (`dynamodb:LeadingKeys`) so a tenant's credentials can only touch its own items.
- **Per-tenant S3 prefixes.** Evidence and artifacts live under `s3://…/<tenant_id>/…`
  with prefix-scoped IAM, on top of per-tenant KMS.

**Isolation guarantee:** logical, defense-in-depth (authorization + key + IAM
partitioning). Strong, but it depends on correct policy and layout rather than an account
wall — hence not the default for the most sensitive classes.

### BRIDGE — shared common tier, siloed sensitive tier

A hybrid: run a POOL plane for the common, lower-sensitivity workloads and break out SILO
accounts for tenants (or data classes) that require an account boundary. A tenant can even
span both — its `public`/`pii` agents on the shared plane, its `cji`/`phi` agents in a
dedicated account — routed by data class. This gives most of POOL's economics while
keeping the regulated slice hard-isolated.

## 2. Data-class × tenant matrix

Tenancy and data class compose. The recommended default per cell:

| Data class \ Tenant model | SILO | POOL | BRIDGE |
|---|---|---|---|
| public | Fine (overkill) | **Recommended** | Common tier |
| pii | Recommended | Acceptable with per-tenant KMS + strict Cedar | Common or siloed by tenant risk |
| phi | **Recommended** | Discouraged | **Siloed tier** |
| cji | **Required** | Not acceptable | **Siloed tier** |
| fti | **Required** | Not acceptable | **Siloed tier** |
| edu | Recommended | Acceptable for low-risk (with consent controls) | Common or siloed |

Rule of thumb: **the more regulated the data class, the harder the isolation** — CJI and
FTI drive an account boundary regardless of tenant size.

## 3. Per-tenant token budgets & chargeback

Multi-tenancy makes the FinOps model in
[`05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md) a
first-class isolation control, not just an accounting one.

- **SILO:** the account boundary *is* the cost boundary. Consolidated billing plus the
  per-account cost-allocation tags (`dept`, `app`, `data_class`, `pack`) give per-tenant
  chargeback with no ambiguity.
- **POOL:** the `tenant` tag is added to each Bedrock application inference profile
  alongside `dept`/`team`/`app`/`data_class`/`pack`. Every `InvokeModel` is tagged with
  its tenant at the source, so Cost Explorer / the CUR produce a per-tenant chargeback
  report even though the plane is shared. The gateway token meter is keyed by
  `(tenant, agent)`, so caps and denials are per-tenant.
- **BRIDGE:** siloed tenants bill by account; pooled tenants bill by tenant tag; the two
  reports consolidate.

Per-tenant hard caps are the primary **noisy-neighbor** economic control (next section).

## 4. Noisy-neighbor controls (POOL / BRIDGE common tier)

A shared plane must stop one tenant from degrading another:

- **Per-tenant token caps** enforced fail-closed in the gateway before spend — a runaway
  tenant is throttled/denied at its own cap, not the pool's.
- **Per-tenant concurrency / rate limits** at the API Gateway (usage plans / throttling)
  and Lambda reserved concurrency, so one tenant cannot exhaust request capacity.
- **Bedrock throughput isolation** — application inference profiles per tenant, and
  provisioned throughput for large tenants where cross-tenant on-demand contention is a
  risk.
- **Per-tenant DynamoDB capacity behaviour** — PAY_PER_REQUEST absorbs spikes; watch for
  hot partitions and consider per-tenant tables for the largest tenants.
- **Budget-breach isolation** — a tenant hitting its cap denies only its own calls; the
  denial is audited and an alert fires to that tenant's owner.

## 5. Tenant onboarding / offboarding

**Onboarding**
1. Choose the model from the data-class × tenant matrix (regulated → SILO/BRIDGE).
2. SILO: vend a Control Tower account, apply the account baseline, deploy the governance
   core (Terraform module or CloudFormation) with the tenant's `department`/`pack`. POOL:
   provision the tenant's CMK, table/prefix partitioning, `tenant_id` claim mapping in the
   IdP federation, Cedar entities, and inference profile with the `tenant` tag.
3. Register the tenant's agents through the agent-onboarding standard
   ([`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md)) — signed
   manifests, budgets, purposes, data classes.
4. Set the tenant's token caps and alert thresholds; verify a test call is audited under
   the correct `tenant_id` and charged to the correct tag.

**Offboarding**
1. Disable the tenant's identity federation and revoke agent grants (deny-by-default takes
   over immediately).
2. Export the tenant's audit + evidence to their custody (WORM objects are immutable by
   design; export copies, honor retention).
3. SILO: decommission or hand over the account per the exit plan. POOL: delete the
   tenant's items/prefixes after retention, then schedule the tenant CMK for deletion
   (rendering residual ciphertext unrecoverable — crypto-shredding).
4. Produce the final chargeback statement from the CUR.

## 6. When to choose which

- **Regulated data (CJI, FTI, PHI) → SILO** (or the siloed tier of BRIDGE). The account
  boundary is the control a review board expects; don't defend logical isolation for these
  classes when an account wall is available.
- **Many small, lower-sensitivity tenants → POOL.** Best economics and operational
  simplicity; lean on per-tenant KMS + Cedar `tenant` clause + IAM leading-key conditions
  + per-tenant caps.
- **Mixed portfolio → BRIDGE.** Most tenants ride the shared road; the few regulated ones
  get their own accounts. This is the common end-state for a platform selling into
  multiple regimes.

Migration path: a tenant can start POOL and be promoted to SILO (its own account) as its
data sensitivity or scale grows — the governance core is the same module either way, which
is what makes the promotion low-friction.
