# Changelog

All notable changes to Aegis are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/).
Aegis has not yet cut a `1.0.0` release; everything below the `Unreleased`
heading describes the current state of the `main` branch.

## [Unreleased]

### Added
- **Aegis Governance Pattern (AGP) versioning** (`docs/14-GOVERNANCE-PATTERN-VERSIONING.md`).
  Formalizes the "governance once, agents as add-ons" model: AGP **v1.0** is the versioned
  governance contract (the eight required controls); `platform_core` is now a versioned package
  (`aegis-platform-core` 0.1.0, `pyproject.toml`) and the canonical reference implementation of
  AGP 1.0. `platform_core.__init__` exposes `__version__` and `AEGIS_GOVERNANCE_PATTERN_VERSION`;
  a conformance test (`platform_core/tests/test_agp_conformance.py`) guards it. The SLG, HPP,
  HCLS, and EDU suites each declare AGP-1.0 conformance in their platform `__init__` and
  `pyproject.toml` (`[tool.aegis] governance_pattern = "1.0"`) with matching conformance tests.

- **Governance control-plane core** (`platform_core/`) — an offline, stdlib-only
  analog of the production AWS control plane:
  - deny-by-default policy engine (`policy_engine.py`) implementing the
    ALLOW-iff predicate: authenticated user, agent grant, user entitlement,
    purpose limitation, data-class isolation, consent, residency, FinOps budget,
    and human-gate approval;
  - authorization gateway (`gateway.py`) brokering every tool call through
    policy → budget preflight → approval → scoped-token mint → tool exec →
    masked append-only audit;
  - fail-closed boundary masking (`masker.py`), immutable/WORM audit ledger,
    single-use human-gate approval ledger, per-agent token budgets, and a
    chargeback/usage ledger.
- **Compliance packs** (`packs/`) mapping controls to CJI, FTI, PHI, FERPA/EDU,
  and PII regimes.
- **Agent onboarding** (`governance/onboarding/`) — the minimum bar, an example
  schema-validated agent manifest, and a manifest loader/validator.
- **FinOps design** — per-agent/department token budgets with hard/soft caps,
  threshold alerts, and per-department chargeback reporting.
- **Offline demo** (`demo/clean_account_acceptance.py`) — an 18-step, no-AWS,
  no-network, no-API-key clean-account acceptance run exercising the entire
  control plane end to end with PASS/FAIL per step.
- **Deployable Infrastructure-as-Code** (`infra/cloudformation/`) — a
  CloudFormation governance core stack plus a sample-agent stack, with
  parameter files, **live-validated on AWS**.
- **Add-agent tooling** (`tools/add_agent.py`) for onboarding new agents.
- **Repository hygiene** — `LICENSE` (Apache-2.0), `SECURITY.md`,
  `CONTRIBUTING.md`, `.github/CODEOWNERS`, and a GitHub Actions CI workflow
  (`.github/workflows/ci.yml`) running the acceptance demo, `cfn-lint`, and
  non-blocking `bandit` / `checkov` scans.

### Security

- **Fail-closed hardening of the offline gateway.** A review found the gateway
  could return a fabricated success (`{"ok": true}`) when **no tool handler was
  registered**, instead of denying. The gateway is now default-deny everywhere:
  - an unregistered tool is denied with reason `tool-not-registered`;
  - if boundary masking cannot run, the call is denied (`masking_fail_closed`);
  - if the policy engine cannot evaluate, the call is denied
    (`policy_eval_fail_closed`);
  - if the append-only audit write fails on a consequential or sensitive call,
    the call is denied (`audit_fail_closed`).
- Added `demo/test_fail_closed.py` regression tests covering unregistered-tool
  deny, masking-failure deny, and the registered happy path.

### Notes

- Aegis is a **reference platform**: it has **not** received an ATO and has
  **not** been independently penetration-tested. See `SECURITY.md` and
  `docs/10-PRODUCTION-READINESS-RACI.md`.

[Unreleased]: https://github.com/virtualryder/aegis/commits/main
