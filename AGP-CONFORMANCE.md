# AGP v1.0 Conformance — Aegis (canonical reference)

**This pack conforms to the Aegis Governance Pattern (AGP) v1.0.** AGP is the governance *contract*
(8 controls, each fail-closed and negative-tested) that every suite implements once in its
`platform_core`, so agents inherit identity, authorization, audit, masking, approval, budget, and
grounding without re-deriving them. The canonical, versioned contract lives in the Aegis repo:
`docs/14-GOVERNANCE-PATTERN-VERSIONING.md`.

- **Contract version implemented:** AGP **1.0**
- **Implementation package:** `aegis-platform-core` (version declared in `MATURITY.yaml` / `pyproject.toml`)
- **Machine-readable claim:** `import aegis_platform_core; aegis_platform_core.AEGIS_GOVERNANCE_PATTERN_VERSION == "1.0"`

*Two versions are distinct: the **pattern** (AGP 1.0 — what a CISO reviews once) and this pack's
**implementation** (early 0.x). A reviewer approves the pattern once; each suite then shows it conforms.*

## The 8 required controls — implemented and proven here

| AGP v1.0 control | Implemented by | Proven by |
|---|---|---|
| 1. Identity (authN) — verified RS256/JWKS JWT; alg-confusion guarded; identity only from a verified claim | gateway + verified claims | `demo/test_negative_security.py` |
| 2. MCP / tool authorization gateway — deny-by-default; unregistered tool → deny | `gateway.py` (deny-by-default) | `demo/test_negative_security.py` |
| 3. Least-privilege intersection — effective = agent grant ∩ user entitlement | `policy_engine.py` | `platform_core/tests/test_agp_conformance.py` |
| 4. Human approval (SoD, single-use) — consequential acts withheld in code; bound, single-use, approver ≠ requester | `approval_ledger.py` | `demo/test_negative_security.py` |
| 5. PII/PHI/regulated-data masking — fail-closed at every log/audit boundary | `masker.py` | `demo/test_fail_closed.py` |
| 6. Audit (append-only + WORM) — every decision recorded; IAM deny on mutate; S3 Object Lock | `audit_ledger.py` | `demo/test_acceptance.py` |
| 7. Token budgets — per-agent hard cap enforced before spend | `token_budget.py` | `platform_core/tests` / `demo` |
| 8. Model gateway + grounding — brokered model access; grounding / output-schema checks | `model_gateway.py` | `demo/test_acceptance.py` |

Aegis is the canonical AGP 1.0 reference implementation; `test_agp_conformance.py` is its conformance test.

> Conformance is about the **control being present, fail-closed, and negative-tested** — not about
> production-readiness. See [`NOT-CLAIMS.md`](NOT-CLAIMS.md) for what this pack does not claim, and
> [`MATURITY.yaml`](MATURITY.yaml) for per-agent maturity and deployment evidence.
