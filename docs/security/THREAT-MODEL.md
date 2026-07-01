# Threat Model — Aegis Governed Agent Platform

> **Status & maturity (read first).** This is a STRIDE-based threat model for the Aegis
> reference architecture. Mitigations are labeled with the maturity language from
> [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md): **DA** = deployed-on-AWS and
> live-validated, **IO** = implemented-offline (Python analog), **IT** = integration-tested,
> **CC** = customer-configured, **P** = planned. Where a control is proven live, the specific
> [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md) **Run** is cited as evidence.
> Nothing here asserts a third-party penetration test or an ATO; those remain customer-owned
> (see [`../10-PRODUCTION-READINESS-RACI.md`](../10-PRODUCTION-READINESS-RACI.md) and
> [`PENTEST-SCOPE.md`](PENTEST-SCOPE.md)).

This model is framed against three external references that a reviewer will expect:
**OWASP Top 10 for LLM Applications** (genai.owasp.org), **MITRE ATLAS** (atlas.mitre.org), and
**NIST 800-53 Rev.5** / **NIST AI RMF (AI 600-1) Generative AI Profile** (see
[`../../SOURCES.md`](../../SOURCES.md)). Control ids below (for example `deny-by-default-gateway`)
are the stable ids in [`../../governance/controls/control_mappings.yaml`](../../governance/controls/control_mappings.yaml).

## 1. Scope and method

The system under analysis is the Aegis control plane and the data/evidence tier around it: the
edge, identity, MCP authorization gateway, model tier (Bedrock + Guardrails), data tier
(DynamoDB audit/approvals, S3 WORM, KMS), and governed connectors to systems of record. The
architecture is described in [`../02-REFERENCE-ARCHITECTURE.md`](../02-REFERENCE-ARCHITECTURE.md).

Method: enumerate **trust boundaries**, then **assets**, then walk STRIDE (Spoofing, Tampering,
Repudiation, Information disclosure, Denial of service, Elevation of privilege) plus a set of
**agentic-AI abuse cases** that STRIDE alone does not name well. Each threat is mapped to an
existing control and its maturity, or marked planned. A short residual-risk register closes the
document.

## 2. Trust boundaries

| # | Boundary | What crosses it | Primary controls |
|---|---|---|---|
| TB-1 | **Edge** (public internet -> CDN) | Untrusted client requests | `edge-waf-shield` (WAF managed rules, rate limit, Shield), TLS termination |
| TB-2 | **Identity** (edge -> authenticated principal) | Bearer JWT -> verified identity + role claim | `crypto-identity-mfa` (Cognito + MFA, API GW JWT authorizer, alg-confusion guard) |
| TB-3 | **Control plane / gateway** (agent -> tools/models) | Every model, tool, and retrieval call | `deny-by-default-gateway`, `human-gate`, `token-budgets-chargeback` |
| TB-4 | **Model tier** (gateway -> Bedrock over PrivateLink) | Prompts, retrieved passages, completions | `in-account-inference-guardrails`, `contextual-grounding-automated-reasoning` |
| TB-5 | **Data / evidence tier** (gateway -> DynamoDB/S3/KMS) | Audit writes, approval reservations, evidence | `append-only-audit-worm`, `kms-cmk-dataclass-isolation`, `masking-fail-closed` |
| TB-6 | **Connector** (gateway -> system of record) | Consequential actions against external SaaS/API | governed connector (idempotency + saga), scoped OBO token |

Data-class isolation (CJI / FTI / PHI / EDU / public) is a cross-cutting boundary realized as
account/VPC/key separation; it multiplies TB-4 through TB-6 per class.

## 3. Assets

| Asset | Sensitivity | Where it lives | Impact if compromised |
|---|---|---|---|
| Regulated data (PII / PHI / FTI / CJI / EDU / card) | Highest | Connector systems of record; transiently in prompts/RAG | Regulatory breach, disclosure liability |
| Audit records | High (integrity) | DynamoDB append-only audit tables | Loss of accountability; failed review board / OIG audit |
| Approval tokens / ledger | High (integrity) | DynamoDB approval ledger (single-use, TTL) | Unauthorized consequential action |
| Identity tokens (JWT) | High | In transit; short-lived | Impersonation, confused-deputy |
| KMS CMKs (per data class) | Highest | AWS KMS | Mass decryption across a data class |
| Cedar policies / agent manifests | High (integrity) | AVP / policy store; signed manifests | Silent privilege expansion |
| Model outputs | Medium-High | Model tier -> caller | Exfiltration channel, hallucinated action |
| Token/cost budget state | Medium | DynamoDB reservation table | Runaway spend, budget denial-of-wallet |

## 4. STRIDE analysis

### 4.1 Spoofing (identity)

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Client forges a role by supplying it in the request body | Roles are taken only from the cryptographically verified `cognito:groups` claim; client-supplied roles are never trusted | **DA** — Run 4, Run 7 |
| Stolen/replayed bearer token | Short-lived JWT; issuer/audience/expiry checked at API GW authorizer and re-checked at the gateway | **DA** — Run 7 (401 on missing/garbage token); **IT** — Run 4 (tampered signature / wrong audience rejected) |
| Agent impersonates a human to a downstream tool | Distinct agent vs human identity; scoped per-call OBO token so the agent acts *as* the user for exactly one call | **P/CC** — OBO exchange documented, not yet wired (GAP-CLOSURE P0 #4) |

### 4.2 Tampering (integrity)

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Agent alters or deletes its own audit history | PutItem-only IAM with explicit `UpdateItem`/`DeleteItem` deny; conditional writes | **DA** — Run 1 (IAM policy simulation: Put=allow, Update/Delete=explicitDeny) |
| Evidence object edited or deleted after the fact | S3 Object Lock WORM; retention actually applied | **DA** — Run 6 (GOVERNANCE retention applied; delete denied AccessDenied) |
| Tampered agent manifest expands scope | KMS-asymmetric signature verified at load; tamper rejected | **DA** — Run 8 (KMSInvalidSignature on tampered manifest) |
| Modified Cedar policy silently grants access | Cedar policies STRICT-validated, default-deny, machine-analyzable before enforcement | **DA** — Run 3 (STRICT-validated policy store, live decisions) |

### 4.3 Repudiation

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Actor denies making a consequential decision | Every tool attempt (allow/deny/pending/error) recorded with lineage; approval bound to tool+args+requester+reviewer | **DA** — Run 2, Run 5 (full approval audit chain) |
| Approver denies approving | Bound, single-use approval written via DynamoDB conditional write, audited with reviewer identity | **DA** — Run 5 |

### 4.4 Information disclosure

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Sensitive data leaks into a prompt, log, or audit field | Boundary masking (Comprehend / Comprehend Medical / Macie / card / biometric), fail-closed | **IO** — regex analog live; Comprehend/Macie not yet wired at runtime (GAP-CLOSURE) |
| Model receives unmasked sensitive data | In-account Bedrock over PrivateLink + Guardrail PII filters on input/output | **DA** — Run 1 (Guardrail READY, PII filters EMAIL/PHONE/SSN) |
| Cross-data-class read (e.g. `phi` served to a `public`-cleared caller) | Data-class boundary clause in the authorization predicate | **DA** — Run 3 (wrong-data-class -> DENY) |
| Cross-tenant / cross-class key reuse | KMS CMK per data class; CJI/FTI in isolated accounts | **DA (key)** — Run 1 (per-class CMK); **P** — multi-account isolation documented, not deployed |

### 4.5 Denial of service

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Volumetric / L3-L4 flood at the edge | AWS Shield + WAF rate limiting | **CC** — `edge-waf-shield` (customer-tuned) |
| Application-layer request flood | WAF managed rules + rate-based rules; API Gateway throttling | **CC** |
| Denial-of-wallet (runaway token spend) | Atomic token-budget reservation; over-cap rejected before spend | **DA** — Run 8 (over-cap ConditionalCheckFailed, no oversell) |

### 4.6 Elevation of privilege

| Threat | Mitigation | Maturity / evidence |
|---|---|---|
| Agent invokes a tool it was not granted | Deny-by-default: `permitted = agent grant INTERSECT user entitlement`; undeclared tool denied | **DA** — Run 3 (unpermitted `ticket.issue` -> DENY) |
| Agent executes a consequential action without approval | Consequential actions withheld in code; reachable only through the human gate | **DA** — Run 2 (Finalize did not run until task token sent) |
| Reviewer with insufficient role approves | Reviewer role verified from claims; wrong role -> 403 | **DA** — Run 5 (wrong-role -> 403 DENY) |

## 5. Agentic-AI abuse cases

These are the cases STRIDE under-describes and that OWASP LLM Top 10 / MITRE ATLAS name directly.

| # | Abuse case | OWASP-LLM / ATLAS framing | Mitigation | Maturity / evidence |
|---|---|---|---|---|
| A-1 | **Prompt injection** (direct or via retrieved content) coerces the agent to misuse a tool | LLM01 Prompt Injection; ATLAS "LLM Prompt Injection" | Deny-by-default gateway means injection cannot exceed the caller's grants; consequential actions still require a human gate; Guardrail denied topics; contextual grounding on RAG | **DA (gateway/gate/guardrail)** — Runs 1,2,3; **CC** — injection eval tuning is customer-owned |
| A-2 | **Confused deputy / privilege escalation** — agent tricked into acting with authority it holds but the caller does not | LLM06 Excessive Agency; ATLAS "Privilege Escalation" | Least-privilege intersection binds the agent to the caller's entitlement; scoped per-call OBO token | **DA (intersection)** — Run 3; **P** — OBO token exchange planned |
| A-3 | **Tool poisoning** — a malicious or altered tool/MCP server enters the registry | LLM03 Supply-chain; ATLAS "ML Supply Chain Compromise" | Signed manifests (KMS-asymmetric), minimum-bar onboarding gate, registry validation/revocation | **DA (signing)** — Run 8; see [`SUPPLY-CHAIN-SECURITY.md`](SUPPLY-CHAIN-SECURITY.md) |
| A-4 | **Unbounded spend** — attacker drives cost via long/looping generations | LLM10 Unbounded Consumption | Hard token cap enforced by atomic reservation before spend; alert thresholds; AWS Budgets | **DA** — Run 8 |
| A-5 | **Approval replay** — a consumed approval token is re-submitted | LLM06 Excessive Agency (control bypass) | Single-use, TTL-bound approval; DynamoDB conditional write; replay -> 404 already-consumed | **DA** — Run 5 (replay -> 404), Run 7 |
| A-6 | **Exfiltration via model output** — sensitive data smuggled out in a completion | LLM02 Sensitive Information Disclosure | Guardrail PII filters on output; grounding check; boundary masking before the model | **DA (guardrail)** — Run 1; **IO** — masking analog |
| A-7 | **Alg-confusion on JWT** (`alg:none` / RS256->HS256 downgrade) | ATLAS "Valid Accounts" / auth bypass | Explicit algorithm allowlist and alg-confusion guard in JWT verification | **IT** — Run 4 (`verify_jwt.py` alg-confusion guard; tampered/downgraded rejected) |
| A-8 | **Audit tampering** — actor edits history to hide an action | ATLAS "Defense Evasion" / repudiation | Append-only IAM (explicit Update/Delete deny) + S3 WORM | **DA** — Run 1, Run 6 |
| A-9 | **Ungrounded consequential action** — agent acts on a hallucinated fact | LLM09 Misinformation; NIST AI RMF Confabulation | Contextual grounding + automated reasoning; `UngroundedConsequentialAction` denied topic | **DA** — Run 1 (denied topic live; grounding 0.80 / relevance 0.75) |

## 6. Residual risk register

The following risks are **not fully mitigated today** and are tracked honestly.

| ID | Residual risk | Why it remains | Owner / next step |
|---|---|---|---|
| RR-1 | Runtime masking gap | Comprehend/Macie not yet wired; only regex analog runs | Delivery Partner / Customer — wire runtime masking (GAP-CLOSURE) |
| RR-2 | No OBO delegation yet | Agent-as-user token exchange planned, not deployed | Delivery Partner — implement OBO (P0 #4) |
| RR-3 | Single-account demo | Multi-account data-class isolation documented, not deployed | Customer — Control Tower landing zone |
| RR-4 | No third-party pen test | Independent testing is customer/engagement-owned | Customer — commission test ([`PENTEST-SCOPE.md`](PENTEST-SCOPE.md)) |
| RR-5 | Live connector is a fixture | Governed connector proven on DynamoDB SoR; real SaaS is a credentials change | Delivery Partner — Run 9 pattern to real endpoint |
| RR-6 | Guardrail/injection tuning | Thresholds and red-team tuning are workflow-specific | Customer — model-risk validation |

