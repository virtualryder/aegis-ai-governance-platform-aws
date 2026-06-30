# Aegis — Infrastructure as Code (skeleton)

> **This is a skeleton.** The stack files described here are stubs to be completed during a
> customer engagement. The purpose of this directory is to fix the *layout*, the *decomposition*,
> the *deploy order*, and *how a compliance pack parameterizes a deployment* — so the templates can
> be filled in without re-litigating the architecture. The architecture itself is in
> [`../docs/02-REFERENCE-ARCHITECTURE.md`](../docs/02-REFERENCE-ARCHITECTURE.md).

## What's here

Two IaC dialects, kept at parity, across two cloud partitions:

```
infra/
  cloudformation/        # AWS CloudFormation templates (primary; AgentCore supports CFN)
    STACKS.md            # one-page description of every stack
    edge.yaml            # (stub) CloudFront + WAF + Shield
    network.yaml         # (stub) VPC, subnets, PrivateLink endpoints
    security.yaml        # (stub) KMS CMKs per data class, IAM, guardrail wiring
    data.yaml            # (stub) DynamoDB append-only audit, S3 Object Lock (WORM)
    gateway.yaml         # (stub) MCP authorization gateway (AgentCore Gateway / APIGW + policy)
    agent.yaml           # (stub) agent runtime + inference-profile binding
    finops.yaml          # (stub) application inference profiles, cost-allocation tags, budgets
    observability.yaml   # (stub) CloudTrail, GuardDuty, Security Hub, Config, X-Ray
  terraform/             # Terraform equivalents, same decomposition (stubs)
    modules/{edge,network,security,data,gateway,agent,finops,observability}/
    envs/{commercial,govcloud}/
```

- **CloudFormation + Terraform parity.** Some customers standardize on one or the other; both
  express the same stacks and parameters so a pack deploys identically in either.
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

## Deploy order

Stacks have dependencies; deploy in this order (reverse to tear down):

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

These templates are intentionally stubs. Live connectors, production identity integration,
third-party security testing, and authorization (ATO / GovRAMP / FedRAMP) are customer-engagement
work — see [`../docs/10-PRODUCTION-READINESS-RACI.md`](../docs/10-PRODUCTION-READINESS-RACI.md).
