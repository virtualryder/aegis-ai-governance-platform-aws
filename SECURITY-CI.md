# Security CI — scanners, and the report-only -> blocking path

*This repo runs a standardized security harness (`.github/workflows/security.yml`): **Bandit** (Python
SAST), **pip-audit** (dependency CVEs), **detect-secrets** (secret scan), **Semgrep** (SAST rulesets),
**Checkov** (IaC), and a **CycloneDX SBOM**. Aligns with AGP conformance ([`AGP-CONFORMANCE.md`](AGP-CONFORMANCE.md))
and the release packet ([`RELEASE-PACKET.md`](RELEASE-PACKET.md)).*

## Current policy

| Scanner | Status | Basis |
|---|---|---|
| **Bandit** (SAST) | **BLOCKING** | vs committed `.bandit-baseline.json` — a NEW medium+ finding fails CI; baselined findings don't |
| **detect-secrets** | **BLOCKING** | vs committed `.secrets.baseline` — a NEW unbaselined secret fails CI |
| **pip-audit** (deps) | **BLOCKING** | deps are hash-pinned in `platform_core/requirements-lock.txt`; pip-audit runs against that lockfile with the `\|\| true` dropped, so a known-vulnerable dependency fails CI |
| **Semgrep** (SAST rulesets) | report-only | flips to blocking once a ruleset (e.g. `p/ci`) is pinned + triaged |
| **Checkov** (IaC) | soft-fail | pre-existing reference-template findings surfaced, not blocking (harden templates, then remove `--soft-fail`) |
| **CycloneDX SBOM** | artifact | published every run |

The committed baselines record the CURRENT findings (audit `.secrets.baseline` with
`detect-secrets audit` to confirm the entries are false positives). New findings block the build.
EDU's `security.yml` is the enforcing reference; HCLS additionally runs a broader report-only
supply-chain job in `ci.yml` (gitleaks, Trivy, Terraform validate) — `security.yml` is the blocking gate.

### How to enforce the remaining scanners

Bandit, detect-secrets, and **pip-audit** are now blocking (see table above). The remaining two —
Semgrep and Checkov — are still report-only/soft-fail; the recipe for each:

| Scanner | Status | Make it blocking |
|---|---|---|
| **Bandit** | ✅ blocking | `bandit -r . --severity-level medium --confidence-level medium --skip B101 -f json -o .bandit-baseline.json`, commit the baseline, then run with `-b .bandit-baseline.json` and drop `\|\| true`. New medium+ findings then fail CI; baselined ones don't. |
| **detect-secrets** | ✅ blocking | `detect-secrets scan > .secrets.baseline`, **audit** it (`detect-secrets audit .secrets.baseline`) to mark the known false positives (`.env.example` placeholders, prompt SHA hashes), commit it, then run `--baseline .secrets.baseline` and drop `\|\| true`. |
| **pip-audit** | ✅ blocking | **Done:** dependencies are hash-pinned into `platform_core/requirements-lock.txt` (`pip-compile --generate-hashes`) and pip-audit runs against it with the `\|\| true` dropped, so a known-vulnerable dependency fails CI. |
| **Semgrep** | report-only | Pin a ruleset (e.g. `p/ci`, `p/python`), triage, then drop `\|\| true`. |
| **Checkov** | soft-fail | Harden the reference templates, then remove `--soft-fail` to enforce on IaC misconfigurations. |

## Dependency lockfiles

`platform_core/requirements-lock.txt` (hash-pinned) **now ships**, so pip-audit and the SBOM run
against exact, reproducible versions and pip-audit is **blocking** against that lockfile (the
`|| true` was dropped). The stdlib-only core plus its optional prod deps (`jsonschema`,
`cryptography`) are pinned there.

## Where the evidence goes

A tagged release collects these outputs into `release/<version>/` via `tools/build_release_packet.sh`
([`RELEASE-PACKET.md`](RELEASE-PACKET.md)). Runtime security proofs (masking, Guardrails, egress,
Access Analyzer, CloudWatch alarms, WORM) are captured at deploy time — see the hero
`SECURITY-EVIDENCE-PACK.md` and `RUNTIME-EVIDENCE-RUNBOOK.md`.
