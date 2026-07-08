# Aegis — Auditor & GRC Assurance Packet

**Cover sheet and curated index for an auditor, security reviewer, or GRC assessor.**
This packet does not duplicate content. It points to the artifacts already in this
repository, organized under standard assurance headings. Every link is relative to the
repository root.

---

## 1. Purpose & scope

Aegis is the **whole-of-government / whole-of-enterprise governance control plane** for AI
agents, built on AWS. This packet exists so a reviewer can answer a security or compliance
questionnaire directly from repository artifacts.

> **Honesty line.** Aegis is a **reference accelerator, not an ATO'd product and not a
> compliance certification.** It ships control *design* and reference IaC. Authorization to
> operate, control operation, evidence generation on live systems, and accountability for
> compliance are **customer-owned**. See the maturity matrix in [`../README.md`](../README.md)
> for what is Implemented (offline reference / deployed IaC) vs. Configurable (customer-owned).

---

## 2. Architecture & data-flow diagrams

- Platform reference architecture — [`../docs/diagrams/aegis-platform-architecture.svg`](../docs/diagrams/aegis-platform-architecture.svg) ([PNG](../docs/diagrams/aegis-platform-architecture.png))
- MCP gateway authorization flow (every request / token / approval / deny path) — [`../docs/diagrams/mcp-gateway-auth-flow.svg`](../docs/diagrams/mcp-gateway-auth-flow.svg) ([PNG](../docs/diagrams/mcp-gateway-auth-flow.png))
- Full reference architecture narrative — [`../docs/02-REFERENCE-ARCHITECTURE.md`](../docs/02-REFERENCE-ARCHITECTURE.md)
- Security architecture — [`../docs/security/SECURITY-ARCHITECTURE.md`](../docs/security/SECURITY-ARCHITECTURE.md)

## 3. Threat model & abuse cases

- STRIDE threat model, abuse cases, threat → control → file — [`../docs/security/THREAT-MODEL.md`](../docs/security/THREAT-MODEL.md)

## 4. Control mappings

- NIST 800-53 / NIST AI RMF mapping and per-regime overlay packs — [`../docs/03-COMPLIANCE-OVERLAY-PACKS.md`](../docs/03-COMPLIANCE-OVERLAY-PACKS.md)
- Compliance evidence index (control → evidence artifact) — [`../docs/security/COMPLIANCE-EVIDENCE-INDEX.md`](../docs/security/COMPLIANCE-EVIDENCE-INDEX.md)
- Regime overlay packs (declarative control bundles) — [`../packs/`](../packs/): `slg` (GovRAMP/FedRAMP, CJIS v6.0, IRS Pub 1075), `education` (FERPA, COPPA), `healthcare-lifesciences` (HIPAA/HITECH, 42 CFR Part 2, GxP / 21 CFR Part 11, HITRUST), `enterprise` (SOC 2, PCI DSS, ISO 27001)
- Governance controls (code) — [`../governance/controls/`](../governance/controls/)

## 5. Identity, authorization & human-in-the-loop controls

- Enforcement sequence and deny-by-default gateway — [`../docs/security/SECURITY-ARCHITECTURE.md`](../docs/security/SECURITY-ARCHITECTURE.md)
- MCP gateway authorization & validation — [`../docs/07-MCP-GATEWAY-AND-VALIDATION.md`](../docs/07-MCP-GATEWAY-AND-VALIDATION.md)
- Agent onboarding minimum bar / signed manifests — [`../docs/04-AGENT-ONBOARDING-STANDARD.md`](../docs/04-AGENT-ONBOARDING-STANDARD.md), [`../governance/onboarding/`](../governance/onboarding/)

## 6. Data protection (encryption, masking, WORM audit, residency)

- Encryption & logging matrix (KMS CMK per data class, WORM audit, log routing) — [`../docs/security/ENCRYPTION-AND-LOGGING-MATRIX.md`](../docs/security/ENCRYPTION-AND-LOGGING-MATRIX.md)
- Residency: data stays in the customer's AWS account/region; residency guarantees are **customer-owned** (region pinning, endpoint policy) — see the encryption/logging matrix and overlay packs.

## 7. Deployment evidence

- Clean-account acceptance run — [`../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`](../evidence/CLEAN-ACCOUNT-ACCEPTANCE.md)
- Deployed-and-validated record (live AWS evidence: KMS, CloudTrail, WORM bucket) — [`../DEPLOYED-AND-VALIDATED.md`](../DEPLOYED-AND-VALIDATED.md)

## 8. Security testing (pen-test, CI gates, SBOM)

- Penetration-test scope & rules of engagement — [`../docs/security/PENTEST-SCOPE.md`](../docs/security/PENTEST-SCOPE.md) — *execution is customer-owned*
- Supply-chain security (dependency policy, provenance) — [`../docs/security/SUPPLY-CHAIN-SECURITY.md`](../docs/security/SUPPLY-CHAIN-SECURITY.md)
- CI security gates — [`../.github/`](../.github/) workflows
- SBOM: not present as a static artifact — **customer-owned**, generated per build/release (see supply-chain security doc for the recommended CycloneDX/SPDX pipeline).

## 9. Shared-responsibility / RACI

- Production-readiness & RACI (reference vs. customer-owned split) — [`../docs/10-PRODUCTION-READINESS-RACI.md`](../docs/10-PRODUCTION-READINESS-RACI.md)
- Operational readiness & incident response — [`../docs/ops/OPS-READINESS.md`](../docs/ops/OPS-READINESS.md), [`../docs/ops/INCIDENT-RESPONSE.md`](../docs/ops/INCIDENT-RESPONSE.md)

## 10. Known limitations & maturity

- Capability maturity matrix — [`../README.md`](../README.md) (§ "Capability maturity matrix")
- Gap-closure backlog — [`../docs/GAP-CLOSURE-BACKLOG.md`](../docs/GAP-CLOSURE-BACKLOG.md)

## 11. Contact & reporting

- Vulnerability reporting via **GitHub Security Advisories** (repository *Security* tab →
  *Report a vulnerability*) — see [`../SECURITY.md`](../SECURITY.md). Do not open public issues
  for security reports.

---

*Reference accelerator — not an AWS service, not AWS-supported software, not a compliance
certification, and not production-ready for regulated data without customer-specific
engineering, testing, authorization, and operational ownership.*
