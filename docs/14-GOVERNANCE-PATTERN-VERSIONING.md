# The Aegis Governance Pattern — versioning & conformance

**Governance once; agents as add-ons.** Aegis defines a governance *contract* — the
**Aegis Governance Pattern (AGP)** — that every agent suite implements once in its
`platform_core`, so individual agents inherit identity, authorization, audit, masking,
approval, and budget controls without re-deriving them. This document is the canonical,
versioned definition of that pattern and the conformance register for the suites that
implement it.

Two version numbers are deliberately distinct:

| Version | What it is | Current | Cadence |
|---|---|---|---|
| **AGP — Aegis Governance Pattern** | The governance *contract* (the controls below and their invariants). What a suite conforms **to**. | **1.0** | Stable; bumped only when a control or invariant is added/changed |
| **platform-core package version** | The *implementation* of AGP in a given repo (`aegis-platform-core`, `slg-agent-platform`, `hpp-agent-platform`, `hcls-agent-platform`, `edu-agent-platform`). | `0.1.0` each | Moves with code; may change without an AGP change |

The pattern is mature (v1.0); the implementations are early (0.x). A CISO reviews the
pattern once; each suite then only has to show it conforms.

## AGP v1.0 — the required controls

A `platform_core` conforms to **AGP 1.0** iff it implements all of the following, each
fail-closed and negative-tested:

1. **Identity (authN).** Verified caller identity via RS256/JWKS JWT verification with an
   alg-confusion guard; identity is taken only from a verified authorizer claim, never from
   request body.
2. **MCP / tool authorization gateway.** A deny-by-default front door: a tool is callable
   only if it is registered in the allow-list; unregistered → deny.
3. **Policy enforcement (least-privilege intersection).** Effective permission =
   grant ∩ entitlement; an agent can never exceed the human it acts for or its declared scope.
4. **Human approval (SoD, single-use).** Consequential actions are withheld in code and
   require a bound, single-use, separation-of-duties approval (approver ≠ requester; replay rejected).
5. **PII/PHI/regulated-data masking.** Fail-closed masking at every log/audit boundary; on
   masker failure, redact rather than leak; unmasked input is never emitted.
6. **Audit (append-only + WORM).** Every decision writes an append-only audit record; the
   audit sink denies mutation at the IAM layer (`Deny dynamodb:UpdateItem/DeleteItem`) and
   durable evidence is written to WORM (S3 Object Lock).
7. **Token budgets.** Per-agent / per-department metering with hard caps enforced by atomic,
   no-oversell conditional writes.
8. **Model gateway + grounding.** Model access is brokered (Bedrock + Guardrails in
   deployment; deterministic analog offline) with grounding/output-schema checks.

The canonical reference implementation of AGP 1.0 is Aegis
[`platform_core/`](../platform_core/) (stdlib-only, laptop-runnable). Each vertical suite
implements the same contract in its own `platform_core` so the logic is readable and testable
without an AWS account; they are deliberate re-implementations of one pattern, not a shared
import.

## Conformance register

Each suite exposes its conformance in two machine-readable places: the platform package's
`__init__.py` (`AEGIS_GOVERNANCE_PATTERN_VERSION`) and its `pyproject.toml`
(`[tool.aegis] governance_pattern`).

| Suite | platform-core package | pkg version | Implements AGP |
|---|---|---|---|
| Aegis (this repo) | `aegis-platform-core` | 0.1.0 | 1.0 (reference) |
| SLG | `slg-agent-platform` | 0.1.0 | 1.0 |
| Healthcare (HPP) | `hpp-agent-platform` | 0.1.0 | 1.0 |
| HCLS / Life Sciences | `hcls-agent-platform` | 0.1.0 | 1.0 |
| Education | `edu-agent-platform` | 0.1.0 | 1.0 |

Verify programmatically:

```python
import aegis_platform_core            # or slg_agent_platform, hpp_agent_platform, ...
print(pkg.__version__)                # implementation version, e.g. "0.1.0"
print(pkg.AEGIS_GOVERNANCE_PATTERN_VERSION)   # contract version, e.g. "1.0"
```

## Change policy

- **AGP minor bump (1.0 → 1.1):** a control is strengthened or an invariant added in a
  backward-compatible way (existing conformant suites still pass). Suites update
  `AEGIS_GOVERNANCE_PATTERN_VERSION` when they adopt it.
- **AGP major bump (1.0 → 2.0):** a control is added or its contract changes such that prior
  implementations are no longer conformant. Requires a migration note here.
- **platform-core package bump:** ordinary code releases; does not require an AGP change.

When AGP changes, update the required-controls list above, bump the version, and record the
migration in [`CHANGELOG.md`](../CHANGELOG.md).
