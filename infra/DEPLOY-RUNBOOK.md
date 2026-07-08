# Aegis - Deploy Runbook (governance core + one sample agent)

> **Customer-run.** These templates deploy into **your** AWS account. The Aegis project
> does **not** deploy them for you. The templates are validated offline with `cfn-lint`
> **and have been deployed live** - nine deploy/smoke/teardown runs in a validation
> account (see [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md)).
> This runbook is the exact deploy -> smoke -> teardown sequence to run yourself.

This realizes a minimal, low-cost, **cleanly-removable** subset of the eight stacks in
[`cloudformation/STACKS.md`](cloudformation/STACKS.md): the **security**, **data**, and
**gateway** tiers in `governance-core.yaml`, plus one low-blast-radius **agent** in
`sample-agent.yaml`. It is a demo/proof, not a production deployment (see
[`../docs/10-PRODUCTION-READINESS-RACI.md`](../docs/10-PRODUCTION-READINESS-RACI.md)).

## What gets created

`governance-core.yaml`
- KMS customer-managed CMK (+ alias) with rotation, one per data class.
- DynamoDB `AuditTable` - PAY_PER_REQUEST, SSE-KMS (CMK), PITR on, append-only.
- DynamoDB `ApprovalLedger` - PAY_PER_REQUEST, SSE-KMS, single-use bound approvals.
- S3 `WormEvidence` bucket - Object Lock **enabled**, versioned, SSE-KMS, all public
  access blocked. **No default retention rule** is set, so teardown stays clean.
- Bedrock Guardrail - PII filters (EMAIL/PHONE/US_SSN), contextual grounding +
  relevance thresholds, one denied topic.
- Cognito user pool + a role group (federated identity / JWT).
- `GatewayLambdaRole` - least privilege, **explicit Deny** on `UpdateItem`/`DeleteItem`
  for the audit table (proves append-only), Bedrock + KMS + Logs scoped to ARNs.
- `GatewayFn` (python3.12) - control-plane gateway stub: applies the guardrail and
  writes an audit record.

`sample-agent.yaml`
- Step Functions **Standard** state machine: Classify -> Retrieve -> Draft -> Check ->
  **HumanGate** (`lambda:invoke.waitForTaskToken`) -> Finalize.
- Two inline-Python placeholder Lambdas (a generic worker + a human-gate stub) and
  their least-privilege IAM roles. Imports the core stack's audit table + guardrail
  via `Fn::ImportValue`.

## Prerequisites

1. **AWS credentials** for the target account/region (`aws sts get-caller-identity`
   should succeed). The deploying principal needs permission to create KMS, DynamoDB,
   S3, Bedrock Guardrail, Cognito, IAM (named roles), Lambda, Logs, and Step Functions.
2. **Region** - default `us-east-1`. Override with `export REGION=us-east-1`.
3. **Bedrock model access enabled** in that region for the guardrail + the model id in
   `BedrockModelId` (default `anthropic.claude-3-haiku-20240307-v1:0`). Enable under
   Bedrock console -> Model access. If Bedrock is not enabled the guardrail create and
   smoke-test check 2 will fail.
4. **Tools**: `aws` CLI v2, `python3` (used by the scripts to convert params / empty the
   bucket), and `cfn-lint` for offline validation (`pip install cfn-lint`).

## Command sequence

```bash
cd infra

# 0. Validate offline (no creds needed). validate-template runs only if creds exist.
export REGION=us-east-1
./scripts/validate.sh

# 1. Deploy: governance-core then sample-agent (idempotent; --capabilities NAMED_IAM).
#    Optionally point at an example parameter file for the core stack:
PARAM_FILE=cloudformation/params/enterprise-service-desk.json ./scripts/deploy.sh
#    or:  PARAM_FILE=cloudformation/params/slg-311.json ./scripts/deploy.sh
#    or just: ./scripts/deploy.sh    (uses template defaults)

# 2. Smoke test: status + guardrail + audit-write + append-only DENY + WORM put.
./scripts/smoke_test.sh

# 3. TEAR DOWN IMMEDIATELY when done (cost-safety).
./scripts/teardown.sh
```

Environment overrides honored by all scripts: `REGION`, `CORE_STACK`
(default `aegis-governance-core`), `AGENT_STACK` (default `aegis-sample-agent`),
`APP_NAME`, `ENVIRONMENT`.

## What the smoke test proves

| Check | Asserts |
|---|---|
| 1 | both stacks are `CREATE_COMPLETE` / `UPDATE_COMPLETE` |
| 2 | the Bedrock Guardrail exists (`aws bedrock get-guardrail`) |
| 3 | invoking `GatewayFn` lands an item in `AuditTable` |
| 4 | assuming the gateway role, an `UpdateItem` on that audit record is **DENIED** (append-only) |
| 5 | an object can be written to the WORM evidence bucket |

## Expected cost

**Pennies.** Everything is pay-per-use / serverless and idle-cheap:
- KMS CMK: ~$1/month prorated (the only thing with a standing monthly charge; a few
  cents for a short-lived demo).
- DynamoDB PAY_PER_REQUEST, Lambda, Step Functions Standard, Cognito, S3: effectively
  $0 at demo volumes; you pay per request/execution/GB only.
- Bedrock: you pay only if `GatewayFn` actually invokes a model; the guardrail itself
  has no standing charge.

There are **no NAT gateways, no VPC endpoints, no provisioned capacity, no always-on
compute** in this subset - those heavier `network.yaml`/`edge.yaml` tiers are
intentionally out of scope here. **Tear down immediately after the demo.**

## Clean-teardown design notes

- Every stateful resource uses `DeletionPolicy: Delete` / `UpdateReplacePolicy: Delete`
  - **nothing is `Retain`**.
- The WORM bucket has Object Lock **enabled** (capability) but **no default retention
  rule** and **no COMPLIANCE-mode lock**, so `teardown.sh` can delete all versions and
  delete markers and then drop the bucket. (A production deployment would set a
  GOVERNANCE/COMPLIANCE retention schedule from the pack's `retention` block; that is
  deliberately omitted in this demo so teardown is frictionless.)
- KMS keys use a 7-day `PendingWindowInDays` (shortest allowed) so the key fully
  schedules for deletion quickly and incurs minimal residual cost.
- `teardown.sh` deletes the agent stack first, then empties the bucket, then deletes the
  core stack, then asserts zero `aegis-*` stacks remain.

## Production gap (do not ship this as-is)

This is a **demo subset**. A real deployment adds the remaining STACKS.md tiers
(`network`, `edge`, `agent` runtime/KB, `finops`, `observability`), federates a real
IdP into Cognito, sets the pack-driven Object Lock retention schedule, pins prompt
versions and inference profiles, and goes through third-party testing + authorization
(ATO / GovRAMP / FedRAMP). See the production-readiness RACI in `../docs/`.
