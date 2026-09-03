# Aegis — Infrastructure as Code

> **This is the canonical deployment path for Aegis** (see [`CANONICAL-IAC.md`](CANONICAL-IAC.md);
> `terraform/` is a parity reference). The deployable core here — `cloudformation/governance-core.yaml` + `sample-agent.yaml` and the
> `golden-pilot/` stacks — is real and has been **deployed live** (ten deploy/smoke/teardown runs;
> see [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md),
> [`DEPLOY-RUNBOOK.md`](DEPLOY-RUNBOOK.md), and the proof pack
> [`../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`](../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md)). The full eight-tier decomposition described in
> [`cloudformation/STACKS.md`](cloudformation/STACKS.md) is the target layout; the network and edge
> tiers now also ship as **minimal, cfn-lint-clean reference stacks** (`network.yaml`, `edge.yaml` —
> cfn-lint-clean, not yet live-run), and the remaining tiers are still **planned, not yet present**
> as templates (list below). The architecture itself is in
> [`../docs/02-REFERENCE-ARCHITECTURE.md`](../docs/02-REFERENCE-ARCHITECTURE.md).

## What's here

What is actually on disk in this directory:

```
infra/
  README.md                  # this file
  DEPLOY-RUNBOOK.md          # customer-run deploy -> smoke -> teardown sequence
  CANONICAL-IAC.md           # which IaC artifact is canonical for each capability
  cloudformation/            # AWS CloudFormation (primary; AgentCore supports CFN)
    STACKS.md                # one-page description of every stack tier (incl. planned ones)
    governance-core.yaml     # DEPLOYABLE: KMS CMK, append-only audit table, approval ledger,
                             #   WORM evidence bucket, Bedrock Guardrail, Cognito, gateway fn
    network.yaml             # REFERENCE (cfn-lint-clean): private VPC + PrivateLink interface
                             #   endpoints (bedrock-runtime/kms/logs/sts/secretsmanager/states)
                             #   + S3/DynamoDB gateway endpoints
    edge.yaml                # REFERENCE (cfn-lint-clean): regional WAFv2 Web ACL (AWS managed
                             #   common + known-bad-inputs + per-IP rate limit)
    sample-agent.yaml        # DEPLOYABLE: Step Functions agent workflow with human gate
    params/                  # example parameter files
      enterprise-service-desk.json
      slg-311.json
  golden-pilot/              # deployable pilot stacks + docs (identity, AVP/Cedar authz,
                             #   reviewer service/API, governed connector, WORM evidence)
    GOLDEN-PILOT.md, IDENTITY.md, REVIEWER-SERVICE.md, CONNECTOR-PILOT.md
    cognito-identity.yaml, avp-cedar.yaml, reviewer-service.yaml, reviewer-api.yaml,
    connector-pilot.yaml, evidence-worm.yaml
    authz/                   # Cedar authorization test fixtures
    run_authz_tests.sh, verify_jwt.py, role_map.json, real_permit.json
  scripts/                   # deploy.sh, smoke_test.sh, teardown.sh, validate.sh
  terraform/                 # Terraform equivalent of the governance core
    README.md
    modules/governance_core/ # main.tf, outputs.tf, index.py
    environments/dev-commercial/main.tf
    environments/dev-govcloud/main.tf
```

### Planned (not yet present)

The remaining STACKS.md tiers do not exist as templates yet; they are customer-engagement work:
`agent.yaml` (agent runtime + inference-profile binding), `finops.yaml` (application inference
profiles, cost tags, budgets), `observability.yaml` (CloudTrail, GuardDuty, Security Hub, Config,
X-Ray), and the matching Terraform modules beyond `governance_core`. (The security/data/gateway
tiers are realized today inside `governance-core.yaml` rather than as separate templates; the
network and edge tiers now ship as the minimal reference `network.yaml` / `edge.yaml` above —
cfn-lint-clean but not yet part of a live deploy run.)

- **CloudFormation + Terraform parity (goal).** Some customers standardize on one or the other;
  the governance core exists in both dialects today, and the planned tiers will keep the same
  decomposition and parameters so a pack deploys identically in either.
- **Commercial + GovCloud.** Commercial (US Moderate) for general workloads; **AWS GovCloud (US)**
  for High-impact / CJI / FTI. CloudFront-scoped WAF is always deployed in `us-east-1`. IaC parity
  is maintained across partitions; ARNs and partition strings (`aws` vs `aws-us-gov`) are
  parameterized.

## Deployment model: standalone-agent-first

Aegis deploys **one governed agent at a time**. A single invocation stands up a complete, isolated
stack — its own VPC, edge, Cognito, KMS CMKs, WORM audit, gateway, and agent runtime — with **no
platform dependency**. You grow the platform agent-by-agent rather than building a monolith first.

When you are ready for whole-of-government / whole-of-enterprise orchestration, a coordination layer
(durable saga with compensation, consent ledger, compliance event bus) composes the already-governed
agents across departments. The same standalone agents become saga steps unchanged — no
re-architecture.

## How a pack parameterizes a deploy

A compliance overlay pack (`packs/<pack>/pack.yaml`) is the input that turns the generic stacks into
a regime-correct deployment. At deploy time the pack supplies:

| Pack field | Drives |
|---|---|
| `regions` | which partition/region the stacks deploy to (commercial vs GovCloud) |
| `data_classes` | how many KMS CMKs and isolated accounts/VPCs `security.yaml`/`network.yaml` create |
| `masking_entities` | the Comprehend / Comprehend Medical / Macie / card / biometric entity sets `security.yaml` enables, and the fail-closed flag |
| `guardrail_profile` | the Bedrock Guardrail policy `security.yaml`/`agent.yaml` attaches (grounding threshold, automated reasoning on/off, denied topics) |
| `retention` | S3 Object Lock mode + retention schedule in `data.yaml` |
| `controls_profile` | which control ids (from `governance/controls/control_mappings.yaml`) must be present; pre-deploy check fails if any is missing |

The **agent manifest** (`governance/onboarding/agent-manifest.schema.json`) supplies the per-agent
parameters on top of the pack: tool grants, grounding KB, token cap, inference profile, human-gate
mode, and the packs the agent requires. Deploy fails if a required pack is not active in the target
environment (minimum bar point 9).

## Deploy order (target decomposition)

This is the dependency order for the full eight-tier layout (most tiers are still planned — see
above; today `governance-core.yaml` covers security/data/gateway in one stack). Deploy in this
order (reverse to tear down):

1. **network** — VPC, subnets, route tables, PrivateLink endpoints. (Foundational; everything runs here.)
2. **security** — KMS CMKs per data class, IAM roles/policies, Bedrock Guardrail policy. (Needs the VPC; everything else references the keys/roles.)
3. **data** — DynamoDB append-only audit table, S3 Object Lock (WORM) buckets. (Needs CMKs from `security`.)
4. **edge** — CloudFront + WAF + Shield. (WAF web ACL in `us-east-1` for CloudFront scope.)
5. **gateway** — MCP authorization gateway (AgentCore Gateway or API Gateway + policy authorizer). (Needs identity, network, security, data.)
6. **agent** — agent runtime + inference-profile binding + grounding KB wiring. (Needs the gateway and finops profiles.)
7. **finops** — application inference profiles, cost-allocation tags, budgets/alerts. (Can deploy alongside/just before `agent`; the agent binds the profile ARN.)
8. **observability** — CloudTrail, GuardDuty, Security Hub, Config, X-Ray. (Deploy early in long-lived envs; listed last because it observes the rest.)

> In practice `observability` and `finops` are often deployed early and once per account, while
> `network`→`security`→`data`→`edge`→`gateway`→`agent` is the per-agent standalone path.

## Status

The governance core and golden-pilot stacks are deployable and have been validated live (see
[`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md)). The remaining tiers listed under
**Planned (not yet present)** are not written yet. Live connectors, production identity
integration, third-party security testing, and authorization (ATO / GovRAMP / FedRAMP) are
customer-engagement work — see
[`../docs/10-PRODUCTION-READINESS-RACI.md`](../docs/10-PRODUCTION-READINESS-RACI.md).
