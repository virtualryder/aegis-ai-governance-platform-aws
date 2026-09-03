# Aegis — CloudFormation Stacks (one-page reference)

> The eight stacks that make up a standalone governed agent, mirroring the tiers in
> [`../../docs/02-REFERENCE-ARCHITECTURE.md`](../../docs/02-REFERENCE-ARCHITECTURE.md). `governance-core.yaml`,
> `network.yaml`, and `edge.yaml` ship as **minimal, cfn-lint-clean reference stacks** here (to harden and
> extend, not turnkey production); the remaining tiers are documented stubs. This page fixes purpose, key
> resources, and which **pack parameters** and **manifest fields** drive each one. Deploy order is in
> [`../README.md`](../README.md).

Partition note: every stack parameterizes the partition (`aws` vs `aws-us-gov`) and region so the
same template deploys to commercial or GovCloud.

---

## `network.yaml` — Network foundation  ✅ *shipped (minimal reference)*
- **Purpose.** Private network the agent and control plane run in; keeps inference and tool traffic off the public internet.
- **Key resources.** `AWS::EC2::VPC`, private/public subnets, route tables, NAT, `AWS::EC2::VPCEndpoint` (PrivateLink) for Bedrock and AWS APIs, security groups.
- **Pack-driven.** `data_classes` → number/shape of isolated VPCs/subnets (CJI and FTI get isolated networks); `regions` → partition/region.
- **Manifest-driven.** `metadata.classification` informs which isolated network segment the agent lands in.

## `security.yaml` — Keys, identity policy, masking & guardrails
- **Purpose.** Cryptographic and authorization substrate: a KMS CMK per data class, IAM roles, the masking entity sets, and the Bedrock Guardrail policy.
- **Key resources.** `AWS::KMS::Key` (one per data class CMK: CJI/FTI/PHI/EDU/card/npi/public), `AWS::IAM::Role`/`Policy` (deny-by-default, append-only audit role), Bedrock Guardrail (`AWS::Bedrock::Guardrail`) with PII filters, denied topics, **contextual grounding** and **automated reasoning** config, Comprehend/Comprehend Medical/Macie enablement.
- **Pack-driven.** `masking_entities` → which Comprehend/Comprehend Medical/Macie/card/biometric sets are enabled and `fail_closed`; `guardrail_profile` → grounding/relevance thresholds, automated_reasoning on/off, denied_topics; `data_classes` → set of CMKs; `controls_profile` → which control ids must resolve.
- **Manifest-driven.** `grounding.grounding_threshold` / `relevance_threshold` override the guardrail thresholds per agent (strictest-wins with the pack).

## `data.yaml` — Audit & evidence (append-only + WORM)
- **Purpose.** Tamper-evident audit and immutable evidence store.
- **Key resources.** `AWS::DynamoDB::Table` (append-only audit; PutItem-only IAM with explicit Update/Delete deny, conditional writes), `AWS::S3::Bucket` with **Object Lock (WORM)** and a retention configuration, SSE-KMS using the per-data-class CMKs from `security.yaml`.
- **Pack-driven.** `retention` → S3 Object Lock mode (COMPLIANCE/GOVERNANCE) and retention period; `data_classes` → bucket/table partitioning per class (e.g. SUD segregated audit).
- **Manifest-driven.** audit fields recorded per agent decision; masked-field set from `metadata.classification`.

## `edge.yaml` — Edge protection  ✅ *shipped (minimal reference)*
- **Purpose.** Public attack-surface protection inherited by every agent.
- **Key resources.** `AWS::CloudFront::Distribution`, `AWS::WAFv2::WebACL` (OWASP managed rules + rate limit; **deployed in `us-east-1`** for CloudFront scope), AWS Shield.
- **Pack-driven.** `regions` (origin region) and any regime-specific WAF rule additions; all packs inherit the edge baseline.
- **Manifest-driven.** generally pack/global, not per-agent.

## `gateway.yaml` — MCP authorization gateway (the product)
- **Purpose.** The deny-by-default broker for every model/tool/retrieval call: identity re-validation, least-privilege intersection, scoped per-call tokens, token-budget check, human gate, append-only audit write.
- **Key resources.** AgentCore Gateway (or `AWS::ApiGateway`/`ApiGatewayV2` + a Cedar/OPA policy authorizer Lambda), `AWS::Cognito::UserPool` + federated IdP, `AWS::StepFunctions::StateMachine` for the human gate (`waitForTaskToken`), the tool registry.
- **Pack-driven.** `controls_profile` → which gateway controls are enforced; `guardrail_profile` → grounding enforcement at the broker.
- **Manifest-driven.** `grants.tools` / `grants.consequential` → policy (what's permitted vs human-gated); `human_gate.mode`, `separation_of_duties`, `esignature_grade` → gate wiring; `metadata.packs` → required-pack pre-deploy check.

## `agent.yaml` — Agent runtime + grounding
- **Purpose.** The agent's execution environment, bound to its inference profile and grounding KB.
- **Key resources.** AgentCore Runtime (or `AWS::StepFunctions` + `AWS::Lambda`), Bedrock **Knowledge Base** binding for governed RAG, inference invoked through the **application inference profile ARN** (never a raw model id).
- **Pack-driven.** `guardrail_profile` attached to inference; `data_classes` allowed.
- **Manifest-driven.** `grounding.knowledge_base` → KB binding; `budget.inference_profile` → profile ARN used at call time; `evals` gate must pass before promotion.

## `finops.yaml` — Token budgets & chargeback
- **Purpose.** Make spend visible, capped, and attributable per department.
- **Key resources.** Bedrock **application inference profiles** (`AWS::Bedrock::ApplicationInferenceProfile`) carrying cost-allocation tags (`dept`, `team`, `app`, `data_class`, `pack`), `AWS::Budgets::Budget` with threshold actions, SNS alert topic; the gateway's real-time token meter enforces hard caps before spend.
- **Pack-driven.** `pack` tag value; data-class caps from the budget policy.
- **Manifest-driven.** `budget.monthly_token_cap`, `budget.inference_profile`, `budget.alert_thresholds`, `budget.cap_behavior`; `metadata.owner`/`team` → tag values.

## `observability.yaml` — Monitoring & posture
- **Purpose.** Continuous monitoring and end-to-end trace of agent execution.
- **Key resources.** `AWS::CloudTrail::Trail`, GuardDuty detector, Security Hub + standards, AWS Config recorder/rules, X-Ray tracing.
- **Pack-driven.** `controls_profile` includes `continuous-monitoring` (required by CJIS v6.0 and others); Config rules per regime.
- **Manifest-driven.** trace/segment tagging by agent id and owner.
