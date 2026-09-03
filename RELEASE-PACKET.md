# Release Packet — Aegis (platform)

*What ships with a tagged release, so a customer, an assessor, or an AWS reviewer gets a repeatable
evidence bundle — not just source. A release packet is assembled per version into `release/<version>/`.
Reference accelerator — see [`NOT-CLAIMS.md`](NOT-CLAIMS.md); this is evidence, not a certification.*

## Versioning (two numbers)

- **AGP (governance contract):** **1.0** — the controls in [`AGP-CONFORMANCE.md`](AGP-CONFORMANCE.md).
- **Implementation package (`aegis-platform-core`):** semantic version, moves with code (may change without an AGP change).

A release records both. A CISO reviews AGP once; each release shows the implementation still conforms.

## What a release packet contains

Reconciled 2026-09-03 (COPILOT-6) to **exactly what the workflows run** — `ci.yml` (python job, iac job,
release job on tags) and `security.yml`. Nothing below is listed that CI does not execute.

| Artifact | What it proves | Produced by (CI step) | Gate |
|---|---|---|---|
| **Test report** | The 60-test offline suite passes (no API key, no AWS); the doc-count / status-drift / CI-coverage gates hold | `ci.yml` → `pytest platform_core/tests demo/test_acceptance.py demo/test_evidence_vault.py demo/test_kill_switch.py demo/test_outbox.py`, `demo/test_fail_closed.py`, `demo/test_prod_components.py`, `demo/test_negative_security.py`, `demo/clean_account_acceptance.py` (19 steps) | blocking |
| **MATURITY drift gate** | `MATURITY.yaml` agrees with the suite | `ci.yml` → `tools/check_maturity.py` | blocking |
| **Deployed authorizer = reviewed engine** | The golden-pilot Lambda handler decides with `platform_core.policy_engine` + masks with `platform_core.masker` from the staged layer; zero-default entitlements; approvals bound at consumption | `ci.yml` → `prepare_layer.sh` + `verify_authorizer_engine.py`; every tracked `*.sh` is LF + `bash -n`-clean | blocking |
| **Package (wheel)** | `aegis-platform-core-<ver>` builds, installs in a clean venv and imports (`platform_core` + `platform_core.prod` with the `prod` extra); sha256 recorded | `ci.yml` → `tools/check_wheel.sh`; artifact `platform_core-wheel` (`RELEASE-HASHES.txt`); on a `v*` tag the **release job** attaches the wheel + hashes to the GitHub release | blocking |
| **SAST (Bandit)** | No new medium+ findings vs the committed baseline | `security.yml` → `bandit … -b .bandit-baseline.json` | blocking |
| **Dependency audit (pip-audit)** | No known-vulnerable dependencies in the hash-pinned lock | `security.yml` → `pip-audit -r platform_core/requirements-lock.txt` | blocking |
| **Secret scan (detect-secrets)** | No new secrets vs `.secrets.baseline` | `security.yml` → `detect-secrets` | blocking |
| **IaC lint (cfn-lint)** | CloudFormation + golden-pilot templates are valid | `ci.yml` iac job → `cfn-lint infra/cloudformation/*.yaml infra/golden-pilot/*.yaml` | blocking |
| **IaC scan (Checkov)** | IaC misconfiguration report | `security.yml` → `checkov -d infra --soft-fail` | report-only |
| **SAST rulesets (Semgrep)** | `p/ci` ruleset report | `security.yml` → `semgrep --config p/ci` | report-only |
| **SBOM (CycloneDX)** | Software bill of materials for the pinned lock | `security.yml` → `cyclonedx-py`; artifact `sbom-cyclonedx` | artifact |
| **Live deploy evidence** | The golden path deployed, controls exercised over HTTPS, torn down | `golden-pilot-deploy-evidence.yml` (OIDC, weekly + on demand, from `main` or a tag) → artifact `deploy-evidence-<run>`; hand-run records in `DEPLOYED-AND-VALIDATED.md` (Runs 1–13) | blocking on the evidence run |
| **Known limitations / upgrade notes** | Honest scope; what changed | `NOT-CLAIMS.md`, `CHANGELOG.md` | — |

Not run by CI (and therefore **not** claimed by a packet): gitleaks (detect-secrets is used instead),
Terraform validate, Trivy. If one of those is required by a customer, add the step first, then the row.

## How to assemble one

```bash
bash tools/build_release_packet.sh 0.2.0
# -> release/0.2.0/MANIFEST.md + the artifacts above; tools missing locally are recorded as SKIPPED,
#    never silently omitted. CI is the authoritative run; the packet is its pinned, collected snapshot.
```

Releases are git tags `vX.Y.Z` with a GitHub release carrying the wheel + `RELEASE-HASHES.txt` (adopted
2026-09-03 with `v0.2.0`; `governed-core` has done this since 1.3.1 — see `docs/DEPENDENCY-MODEL.md`).

## Upgrade notes

Each release appends to [`CHANGELOG.md`](CHANGELOG.md). If a release adopts a new **AGP** version, the
migration note lives in the Aegis versioning doc (`docs/14-GOVERNANCE-PATTERN-VERSIONING.md`) and is
referenced here. Package-only releases (no AGP change) note code changes and any config/env deltas.

> A release packet is **evidence for a specific commit**, not a promise of production-readiness. The
> customer still owns validation, IdP integration, production connectors, and operations
> (see [`OPERATING-MODEL.md`](OPERATING-MODEL.md)).
