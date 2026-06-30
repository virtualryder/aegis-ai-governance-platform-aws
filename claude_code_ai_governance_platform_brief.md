# Claude Code Brief: AWS Whole-of-Enterprise AI Governance Platform

## Goal
Create a standalone repository named `aws-ai-governance-platform` that becomes the governed substrate for public sector, healthcare/life sciences, education, and enterprise AI agents on AWS.

The platform must be separate from agent catalogs. Agents such as SLG, HCLS, EDU, or enterprise agents should install as add-on packages that inherit identity, authorization, audit, masking, model governance, cost controls, approval workflows, and compliance evidence.

## Product thesis
The agent is not the product. The product is the governance substrate that makes agents deployable, auditable, explainable, controlled, and expandable.

## Target users
- CIO / CEO: wants one enterprise standard for moving AI from pilots to production.
- CISO: wants provable identity, authorization, audit, data isolation, retention, and incident evidence.
- Director of architecture: wants a reusable AWS pattern, IaC, integration contracts, and no one-off bots.
- Program owners: want workflow improvement without allowing AI to make consequential decisions.
- FinOps / CFO: wants token budgets, showback/chargeback, usage controls, and predictable cost.

## Required repository structure

```text
aws-ai-governance-platform/
  README.md
  docs/
    ARCHITECTURE.md
    DEPLOYMENT-MODELS.md
    COMPLIANCE-CONTROL-MAPPINGS.md
    PRODUCTION-READINESS-RACI.md
    AGENT-ONBOARDING-STANDARD.md
    SECURITY-THREAT-MODEL.md
    GTM-STORY.md
    CISO-BRIEFING.md
    CIO-BRIEFING.md
    ARCHITECTURE-DEEP-DIVE.md
  contracts/
    agent.schema.json
    tool.schema.json
    model_profile.schema.json
    data_class.schema.json
    control_mapping.schema.json
    approval_policy.schema.json
    cost_policy.schema.json
  platform_core/
    registry/
      agent_registry.py
      tool_registry.py
      model_registry.py
      data_class_registry.py
    policy/
      cedar_compiler.py
      avp_client.py
      policy_simulator.py
      examples/
    gateway/
      mcp_gateway.py
      agentcore_adapter.py
      scoped_token_service.py
      tool_invocation_proxy.py
    approvals/
      reviewer_api.py
      approval_ledger.py
      stepfunctions_callbacks.py
      e_signature.py
    data_protection/
      pii_masker.py
      phi_masker.py
      fti_masker.py
      cji_masker.py
      ferpa_masker.py
      tokenization.py
      retrieval_security_trimming.py
    model_gateway/
      bedrock_router.py
      guardrails.py
      prompt_registry.py
      grounding_verifier.py
      schema_validator.py
      hallucination_checks.py
    evidence/
      compliance_event_bus.py
      audit_ledger.py
      worm_exporter.py
      evidence_package.py
    finops/
      token_budget_manager.py
      inference_profile_manager.py
      usage_ledger.py
      chargeback_reporter.py
    onboarding/
      scaffold_agent.py
      validate_agent_package.py
      risk_tier_classifier.py
  infra/
    cloudformation/
      control-tower-baseline.yaml
      network-private-endpoints.yaml
      ai-governance-core.yaml
      agentcore-gateway.yaml
      verified-permissions.yaml
      bedrock-logging.yaml
      evidence-ledger.yaml
      finops-dashboard.yaml
      reviewer-service.yaml
    terraform/
      modules/
        governance_core/
        agent_runtime/
        private_network/
        evidence/
        finops/
        industry_pack/
  industry_packs/
    slg/
      controls.yaml
      data_classes.yaml
      policy_templates/
    healthcare/
    life_sciences/
    education/
    enterprise/
  sample_agents/
    resident_services_311/
    revenue_cycle_denials/
    student_form_intake/
  tests/
    unit/
    integration/
    security_negative/
    policy_simulation/
    hallucination_eval/
    finops/
    clean_account_acceptance/
  .github/workflows/
    ci.yml
    security.yml
    clean-account-deploy.yml
```

## Core platform modules

### 1. Agent Registry
Every agent must register:
- agent_id
- owning business unit
- accountable human owner
- risk tier
- allowed purposes
- data classes handled
- model profiles allowed
- tools allowed
- required approvals
- eval datasets
- red-team test pack
- cost center
- retention schedule
- deployment status

### 2. Tool Registry / MCP Catalog
Every tool must declare:
- tool_id
- system of record
- agency or enterprise owner
- data classes accessed
- read/write capability
- allowed purposes
- required user entitlement
- required approval tier
- transaction threshold
- idempotency key requirement
- rollback/compensation handler
- audit schema
- connector endpoint
- MCP schema

### 3. Policy Engine
Implement authorization as:

```text
ALLOW iff:
  authenticated_user is valid
  AND agent grant permits tool
  AND user entitlement permits tool
  AND declared purpose is allowed
  AND data class boundary is satisfied
  AND consent exists when required
  AND residency boundary is satisfied
  AND cost/token budget is available
  AND approval exists when required
```

Use Amazon Verified Permissions / Cedar as the canonical production policy engine. Python policy logic may remain only as a local test analog. Add a compiler from `agent.yaml` and `tool.yaml` into Cedar policies.

### 4. AgentCore / MCP Gateway
Use Amazon Bedrock AgentCore Gateway as the canonical tool gateway where available. Provide a portable API Gateway + Lambda proxy fallback for regions or features that are unavailable.

Gateway must enforce:
- authenticated ingress
- scoped outbound authorization
- tool schema validation
- idempotency
- PII/PHI/FTI/CJI masking at logging boundaries
- audit event creation before and after the tool call
- no direct connector access from agents

### 5. Approval Service
Create a real reviewer service, not a local script:
- reviewer authenticates through customer IdP
- reviewer must have required role
- separation of duties enforced
- approval is bound to exact agent, tool, arguments hash, purpose, requester, reviewer, and expiration
- consumed approval token is recorded durably using DynamoDB conditional write
- approval/rejection creates evidence event
- Step Functions `waitForTaskToken` flow is supported

### 6. Model Gateway
Centralize all Bedrock calls:
- approved model profiles only
- per-agent model allowlist
- task-based routing: small model for classify, stronger model for drafting
- mandatory Guardrails policy in production
- max_tokens enforced by budget manager
- prompt version pinned
- JSON schema validation for structured outputs
- hallucination/grounding verifier
- retry/fallback model policy
- model invocation logging enabled to CloudWatch or S3

### 7. Hallucination and quality controls
Implement layered controls:
- only retrieve from curated, access-controlled KBs
- require citations to retrieved chunks for claims
- flag numbers, dates, fees, laws, policy statements, and agency names without evidence
- run Bedrock Guardrails contextual grounding where supported
- validate output against schema
- compare answer to source snippets
- confidence threshold blocks automation
- human gate for any resident, patient, student, benefit, permit, safety, revenue, or legal-impacting output
- log unsupported-claim metrics

### 8. Data protection
Implement deterministic baseline masking plus optional AWS-native detection:
- PII: SSN, address, phone, email, DL, account IDs
- PHI: patient identifiers, MRN, dates, health plan IDs
- FTI: SSN/EIN/tax forms/taxpayer IDs
- CJI: case numbers, incident IDs, officer names where policy requires
- FERPA: student ID, DOB, guardian details
- PCI: PAN via Luhn, tokenized payment connector only

Masking must fail closed: never log raw sensitive data if masking fails.

### 9. Evidence ledger
Every decision and tool call must create a durable, queryable evidence package:
- request_id
- case_id
- user identity
- agent_id
- tool_id
- purpose
- data class
- policy decision
- model id/profile
- prompt version
- retrieved source IDs
- input/output hashes
- approval ID and reviewer
- token/cost metrics
- tool response ID
- rollback/compensation status
- retention period

Use EventBridge for event routing, DynamoDB conditional writes for append-only ledger, and S3 Object Lock for immutable evidence exports.

### 10. Token budgets and chargeback
Implement a FinOps layer:
- application inference profiles per department/agent/environment
- cost allocation tags: department, agency, agent_id, environment, cost_center, use_case
- token preflight estimator
- max_tokens enforcement
- TPM/RPM quota awareness
- per-user, per-agent, per-department budget policy
- usage ledger populated from model invocation logs and runtime metrics
- QuickSight/Athena dashboards for showback and chargeback
- anomaly detection and budget alarms

### 11. Industry packs
Create overlays, not forks.

Each pack must define:
- data classes
- required controls
- default retention
- required approvals
- masking rules
- evidence package requirements
- deployment boundary guidance
- compliance mappings

Initial packs:
- SLG/Public Sector: GovRAMP/FedRAMP, CJIS, IRS 1075, DPPA, ADA Title II, NIST AI RMF
- Healthcare: HIPAA/HITECH, MARS-E/ARC-AMPE, minimum necessary, BAA assumptions
- Life Sciences: 21 CFR Part 11, GxP/CSA, validation evidence, e-signature linkage
- Education: FERPA, ADA, student data access, age-appropriate privacy controls
- Enterprise: SOC 2, ISO 27001, PCI, privacy, model risk

## Agent onboarding contract
Each add-on agent must ship:

```text
agent.yaml
policy.cedar
tools.mcp.json
prompts/
evals/
red_team/
data_contracts/
threat_model.md
runbook.md
cost_model.yaml
acceptance_tests/
```

No agent may publish unless tests prove:
- least privilege
- data-class isolation
- policy denial paths
- no unauthorized consequential action
- no raw sensitive data in logs/prompts/audit
- hallucination/grounding threshold
- human approval for high-risk actions
- rollback/idempotency for writes
- cost attribution
- evidence package completeness

## Clean-account acceptance test
A release cannot be called deployable until automation proves:

```text
Deploy into a clean AWS account
→ configure IdP or test identity provider
→ register one agent
→ register one MCP tool
→ load one knowledge base fixture
→ invoke model through model gateway
→ enforce max_tokens and budget
→ deny unauthorized tool call
→ deny wrong data class
→ require approval for high-risk action
→ block self-approval
→ approve through reviewer service
→ execute exact approved action once
→ reject replay
→ create immutable audit evidence
→ export WORM evidence package
→ populate usage ledger
→ produce chargeback report
→ run teardown cleanly
```

## First customer positioning
Lead with one low-blast-radius workflow:
- SLG: Resident services / 311 or IT service desk
- Healthcare: Revenue-cycle appeal drafting
- Education: Student form intake or IT/service desk
- Enterprise: HR or IT service management knowledge assistant

Do not lead with benefits adjudication, public safety operational decisions, treatment recommendations, records release, permit issuance, or contract awards until the platform has completed security review, validation, live connector testing, and customer authorization.

## Go-to-market package to generate
- Executive deck
- CISO security briefing
- Director of architecture deep-dive
- Control mapping matrix
- Shared responsibility/RACI
- Agent onboarding guide
- Cost/chargeback model
- ROI worksheet
- Pilot SOW template
- Deployment runbook
- Clean-account acceptance report template
- Objection handling guide

## Primary sources to cite in docs
- Amazon Bedrock AgentCore Gateway: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html
- Amazon Bedrock AgentCore Identity / OBO tokens: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html
- Amazon Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- Bedrock sensitive information filters: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html
- Bedrock contextual grounding checks: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html
- Bedrock PrivateLink: https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html
- Bedrock application inference profiles: https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html
- Bedrock model invocation logging: https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
- Bedrock runtime metrics and token metrics: https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html
- AWS Control Tower: https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html
- Amazon Verified Permissions: https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/what-is-avp.html
- S3 Object Lock: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- AWS GovRAMP: https://aws.amazon.com/compliance/govramp/
- NIST AI RMF / GenAI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- DOJ ADA Title II accessibility extension: https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web
- FBI CJIS Security Policy v6.0: https://le.fbi.gov/file-repository/cjis_security_policy_v6-0_20241227.pdf
- IRS Pub 1075: https://www.irs.gov/pub/irs-pdf/p1075.pdf
