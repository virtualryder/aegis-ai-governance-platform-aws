# Supply-Chain Security — Aegis Governed Agent Platform

> **Status & maturity (read first).** Signed-manifest verification and CI scanning are
> **deployed / in-repo**; SBOM generation, artifact signing of releases, and a base-image policy
> are **planned** for the pilot-hardening phase. Maturity labels (**DA/IO/IT/CC/P**) follow
> [`../GAP-CLOSURE-BACKLOG.md`](../GAP-CLOSURE-BACKLOG.md). This maps to OWASP LLM Top 10 **LLM03
> (supply-chain)** and MITRE ATLAS **ML Supply Chain Compromise**.

The supply chain has two halves: the **platform** software supply chain (IaC, Lambda code, CI) and
the **agent** supply chain (third-party or first-party agents onboarded onto the platform). Aegis
treats agent onboarding itself as a supply-chain gate.

## 1. Signed manifests (agent supply chain)

Every agent ships a manifest that enumerates its scope, grants, budget, grounding, evals, and packs
(schema: [`../../governance/onboarding/agent-manifest.schema.json`](../../governance/onboarding/agent-manifest.schema.json)).
The manifest is signed by a known publisher and the signature is verified at load.

- **Mechanism:** KMS-asymmetric signing (`RSASSA_PSS_SHA_256`). A tampered manifest is rejected.
- **Evidence:** Run 8 created an RSA_2048 SIGN_VERIFY KMS key, signed a manifest, verified
  `valid-manifest: True`, and rejected a tampered manifest with `KMSInvalidSignature`. **DA.**
- **Offline analog:** local-RSA signing + real JSON-Schema validation + a manifest->Cedar compiler
  live in `platform_core/prod/` with unit tests (`demo/test_prod_components.py`). **IO.**

An unsigned manifest, an unknown publisher, or a digest mismatch fails closed at the onboarding
gate and at the gateway load path (minimum-bar point 8).

## 2. CI scanning (platform supply chain)

The pipeline is [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml). Present today:

| Stage | Tool | Scope | Blocking? | Maturity |
|---|---|---|---|---|
| Static Python security | bandit | `platform_core`, `tools` | non-blocking (advisory) | DA |
| IaC security | checkov | `infra/cloudformation` | non-blocking (advisory) | DA |
| IaC lint | cfn-lint | all `infra/**` templates | blocking | DA |
| Byte-compile | compileall | control plane, demo, tools | blocking | DA |
| Acceptance + regression | clean-account acceptance, fail-closed, prod-component, negative-security suites | control plane | blocking | DA/IT |

**Hardening plan:** promote bandit and checkov from advisory to blocking with a documented
suppression policy; add secret scanning (for example gitleaks) to the pull-request path.

## 3. Dependency pinning

- Python test/runtime dependencies are installed explicitly in CI (`jsonschema`, `cryptography`,
  `pyyaml`, `cfn-lint`, `bandit`, `checkov`). **Plan:** move to a fully pinned lockfile
  (hash-pinned `requirements.txt` or equivalent) so builds are reproducible and a compromised
  transitive dependency cannot silently enter. **P.**
- GitHub Actions are pinned to major-version tags today (`@v4`, `@v5`). **Plan:** pin actions to
  commit SHAs to remove tag-mutation risk. **P.**

## 4. SBOM generation plan

Generate a CycloneDX (or SPDX) SBOM per release covering Python dependencies and Lambda
runtime/layers, publish it as a release artifact alongside the signed release, and diff it build
over build to detect unexpected additions. **P.** This gives an auditor a bill of materials and
supports rapid response to a newly disclosed dependency vulnerability.

## 5. Artifact signing (release supply chain)

- **Manifests:** signed today (Run 8). **DA.**
- **Releases (Lambda bundles, IaC packages):** plan to sign release artifacts and verify signatures
  at deploy time; deployment uses **deployment roles, not human credentials**, with change sets and
  rollback alarms (GAP-CLOSURE P0 #8). **P/started.**

## 6. Base-image policy

Lambda functions in the reference stacks use AWS-managed runtimes rather than custom container
images. If a workload requires container images, the policy is: pin to a specific digest (not a
floating tag), pull from a private ECR repository with scan-on-push enabled, rebuild on base-image
CVE, and forbid `latest`. **P** (policy stated; no custom images in the current reference stacks).

## 7. Agent onboarding as a supply-chain gate

The **minimum bar** ([`../../governance/onboarding/MINIMUM-BAR.md`](../../governance/onboarding/MINIMUM-BAR.md))
is the supply-chain admission control for agents. CI rejects and the gateway refuses to load any
agent that fails any of the nine points. The supply-chain-relevant points:

| Point | Gate | Supply-chain effect |
|---|---|---|
| 1 | Declared scope, nothing more | Static analysis diffs code against the manifest; undeclared tool/class fails the build |
| 2/3 | Consequential actions withheld + bound single-use SoD gate | A poisoned tool still cannot execute a consequential action without a valid approval |
| 7 | Masking on, fail-closed | A malicious tool cannot exfiltrate unmasked sensitive data through the boundary |
| 8 | Signed by a known publisher | Unsigned / unknown-publisher / tampered manifest rejected |
| 9 | Pack compatibility | An agent built for one regime cannot silently run where those controls are off |

This is what makes even a third-party add-on safe to deploy: it inherits the customer's identity,
data classes, guardrails, budgets, and audit only after clearing the bar, and it can reach nothing
it did not declare.

## 8. What is proven vs planned

- **Proven (DA):** KMS-asymmetric signed-manifest verify + tamper rejection (Run 8); CI with
  cfn-lint (blocking) and bandit/checkov (advisory); minimum-bar onboarding gate design + schema.
- **Planned (P):** SBOM per release; blocking security scans with suppression policy; hash-pinned
  dependency lockfile; SHA-pinned actions; release-artifact signing + verify-at-deploy; secret
  scanning; base-image policy enforcement if containers are introduced.
