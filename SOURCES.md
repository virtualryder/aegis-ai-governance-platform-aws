# SOURCES — Evidence Base for the Aegis Governed Agent Platform

> Every architectural and compliance claim in this repository is grounded in a primary
> or authoritative source listed below. Each source is tagged by evidence tier:
> **[AWS]** = AWS official docs / what's-new / blogs · **[GOV]** = government / regulator /
> standards body · **[PEER]** = peer-reviewed · **[ANALYST/VENDOR]** = analyst or vendor-reported.
> Claims that are *configurable customer responsibility* (not platform-guaranteed) are flagged
> as such in the docs that cite them.
>
> Last verified: 2026-06-30.

## 1. AWS agent platform primitives

- **[AWS] Amazon Bedrock AgentCore is now generally available** (GA 2025-10-13). AgentCore
  Gateway connects to existing **Model Context Protocol (MCP)** servers and turns APIs/Lambda
  into agent tools; supports **IAM and OAuth** authorization; acts as one secure tool endpoint.
  AgentCore Identity adds identity-aware authorization + secure token vault. All AgentCore
  services now support **VPC, AWS PrivateLink, AWS CloudFormation, and resource tagging**.
  https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/
  · https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-is-now-generally-available/
  · https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
- **[AWS] AgentCore compliance validation** — AgentCore is **HIPAA eligible**, **pursuing
  FedRAMP**, and aligns with **HITRUST** and other programs.
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/compliance-validation.html

## 2. Cost attribution, chargeback & token governance

- **[AWS] Manage multi-tenant Amazon Bedrock costs using application inference profiles** —
  application inference profiles (AIPs) attribute Bedrock InvokeModel/Converse costs by
  application/team/workload via **cost allocation tags** that flow to **Cost Explorer** and
  **Cost and Usage Reports (CUR/CUR 2.0)**; use the profile ARN in place of the model ID.
  https://aws.amazon.com/blogs/machine-learning/manage-multi-tenant-amazon-bedrock-costs-using-application-inference-profiles/
- **[AWS] Introducing granular cost attribution for Amazon Bedrock.**
  https://aws.amazon.com/blogs/machine-learning/introducing-granular-cost-attribution-for-amazon-bedrock/
- **[AWS] Track Amazon Bedrock costs by caller identity (IAM principal-based cost allocation).**
  https://aws.amazon.com/blogs/aws-cloud-financial-management/track-amazon-bedrock-costs-by-caller-identity-with-iam-based-cost-allocation/
- **[AWS] Application inference profiles (docs).**
  https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html

## 3. Hallucination control & response validation

- **[AWS] Contextual grounding check** — detects/filters hallucinations in RAG by scoring
  **grounding** and **relevance** (configurable thresholds 0–0.99); blocks or flags responses
  that deviate from retrieved source or don't answer the query.
  https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html
- **[AWS] Automated Reasoning checks in Amazon Bedrock Guardrails** — uses **formal logic /
  mathematical techniques** to validate responses against defined policies; first GenAI
  safeguard to use formal logic to help prevent factual errors from hallucinations.
  https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-automated-reasoning-checks.html
- **[AWS] Guardrails can now detect hallucinations / safeguard custom & third-party FMs.**
  https://aws.amazon.com/blogs/aws/guardrails-for-amazon-bedrock-can-now-detect-hallucinations-and-safeguard-apps-built-using-custom-or-third-party-fms/
- **[AWS] Bedrock Guardrails overview.** https://aws.amazon.com/bedrock/guardrails/

## 4. Sensitive-data discovery & masking (PII / PHI / FTI / CJI)

- **[AWS] Detecting and redacting PII using Amazon Comprehend** — detect PII entities and
  redact by entity type or mask character (English/Spanish).
  https://aws.amazon.com/blogs/machine-learning/detecting-and-redacting-pii-using-amazon-comprehend/
  · https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html
- **[AWS] Common techniques to detect PHI and PII using AWS services** (Comprehend Medical for
  PHI; Macie for S3 discovery). https://aws.amazon.com/blogs/industries/common-techniques-to-detect-phi-and-pii-data-using-aws-services/
- **[AWS] Amazon Macie managed data identifiers** — discover/classify PII, PHI, financial data,
  credentials in S3. https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- **[AWS] Redacting PII with S3 Object Lambda + Comprehend.**
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/tutorial-s3-object-lambda-redact-pii.html

## 5. Public-sector authorization frameworks

- **[GOV] StateRAMP rebranded to GovRAMP (Feb 2025)** — scope expanded to local governments,
  K-12, higher education, and hospitals. https://statetechmagazine.com/article/2025/04/stateramp-rebrands-to-govramp-perfcon
- **[GOV] FedRAMP 20x** — pilot to compress authorization timelines; Phase 1 (Low) produced 13
  authorizations from 27 submissions in FY25 (program still a pilot).
  https://www.compliancepoint.com/cyber-security/comparing-fedramp-and-govramp/
- **[GOV] CJIS Security Policy v6.0** — released **2024-12-27**; audits began **2025-10-01**;
  full compliance ~2027; **MFA mandatory** for all CJI access (remote, cloud, privileged).
  https://www.compassitc.com/blog/cjis-security-policy-v6.0-key-updates-you-need-to-know
  · https://www.naco.org/news/new-fbi-criminal-justice-information-services-cjis-security-rule-requirements
- **[GOV] MFA for CJIS: NIST IR 8523.** https://csrc.nist.gov/News/2025/mfa-for-cjis-nist-ir-8523

## 6. Healthcare & life-sciences regimes

- **[AWS] HIPAA compliance for generative AI solutions on AWS** — Bedrock/AgentCore are
  HIPAA-eligible (HIPAA Eligible Services Reference); a signed **BAA** + customer-implemented
  controls are required. "HIPAA-eligible" ≠ "HIPAA-compliant."
  https://aws.amazon.com/blogs/industries/hipaa-compliance-for-generative-ai-solutions-on-aws/
  · https://aws.amazon.com/compliance/hipaa-compliance/
- **[AWS] GxP / 21 CFR Part 11 & EU Annex 11 on AWS.** https://aws.amazon.com/compliance/gxp-part-11-annex-11/
- **[AWS] A guide to building AI agents in GxP environments** (Computer Software Assurance,
  risk-based validation). https://aws.amazon.com/blogs/machine-learning/a-guide-to-building-ai-agents-in-gxp-environments/
- **[AWS] GxP Systems on AWS (whitepaper).** https://d1.awsstatic.com/whitepapers/compliance/Using_AWS_in_GxP_Systems.pdf

## 7. Education regimes

- **[GOV] Amended COPPA Rule (2025)** — effective **2025-06-23**, compliance deadline
  **2026-04-22**; expands "personal information" to **biometric identifiers** (voiceprints,
  facial patterns); shifts to **opt-in** parental consent; requires a written security program.
  https://www.loeb.com/en/insights/publications/2025/05/childrens-online-privacy-in-2025-the-amended-coppa-rule
- **[GOV] FERPA & AI** — feeding student records to general-purpose AI without an agreement can
  be an unauthorized disclosure; school-official exception requires direct control + data limits.
  https://www.nea.org/sites/default/files/2025-06/5.1-ai-policy-overview-of-federal-regulations-final.pdf

## 8. AI risk management

- **[GOV] NIST AI 600-1 — AI RMF Generative AI Profile** (2024-07-26). 12 risk areas including
  **Confabulation** (hallucination), **Data Privacy**, **Information Integrity**, **Information
  Security**; 200+ suggested actions across **Govern / Map / Measure / Manage**.
  https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
  · https://www.nist.gov/itl/ai-risk-management-framework
- **[GOV] NIST AI RMF 1.0** (base framework). https://www.nist.gov/itl/ai-risk-management-framework

## 10. Policy engine, landing zone & scoped delegation (added 2026-06-30, verified)

- **[AWS] Policy in Amazon Bedrock AgentCore** — a deterministic enforcement layer that evaluates
  **every agent-to-tool request against Cedar policies**, applied **outside the agent's reasoning
  loop** at the AgentCore Gateway; policies can be authored in Cedar or generated from plain English,
  validated against the gateway schema, and analyzed before enforcement. **Cedar is the same policy
  language behind Amazon Verified Permissions.** This is the canonical production authorization path.
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
  · https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/
  · https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-in-amazon-bedrock-agentcore/
- **[AWS] Amazon Verified Permissions** — managed Cedar authorization service (the externalized
  policy model the local engine mirrors). https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/what-is-avp.html
- **[AWS] AgentCore Identity / on-behalf-of (OBO) token exchange** — scoped, short-lived downstream
  credentials so an agent acts as the user without long-lived secrets.
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html
- **[AWS] AWS Control Tower** — multi-account landing zone with guardrails; the basis for
  account-per-data-class isolation. https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html
- **[AWS] Bedrock model invocation logging** — capture full request/response + token metrics to
  CloudWatch/S3 (feeds the usage ledger). https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
- **[AWS] Bedrock sensitive information (PII) filters in Guardrails.**
  https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html
- **[AWS] Bedrock VPC interface endpoints (PrivateLink).**
  https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html
- **[AWS] S3 Object Lock (WORM).** https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **[GOV] DOJ ADA Title II Interim Final Rule (eff. 2026-04-20)** — extends web/mobile accessibility
  compliance: **State/local entities with population ≥50,000 → April 26, 2027**; **<50,000 or special
  districts → April 26, 2028**; technical standard **WCAG 2.1 Level AA**.
  https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web
- **[GOV] FBI CJIS Security Policy v6.0 (PDF, 2024-12-27).**
  https://le.fbi.gov/file-repository/cjis_security_policy_v6-0_20241227.pdf
- **[GOV] IRS Publication 1075 (FTI safeguards).** https://www.irs.gov/pub/irs-pdf/p1075.pdf
- **[AWS] AWS GovRAMP.** https://aws.amazon.com/compliance/govramp/

## 9. Inherited evidence base (predecessor repo: virtualryder/slg-ai-agents)

The SLG accelerator that this platform generalizes carries its own grounded citation set
(`SOURCES.md`, `decks/DECK-SOURCES.md`) for SLG workflow pain/ROI figures (DOJ OIP FOIA backlog,
KFF Medicaid unwinding, CMS call-center metrics, NASCIO state-CIO priorities, Gartner self-service
economics, named state/county deployments). Those figures are reused only where this platform's
docs cite SLG outcomes, and remain labeled by evidence tier on-slide.
