"""platform_core.prod — production-grade replacements for the offline analogs.

The base platform_core modules are deliberately offline/no-AWS so the demo runs
anywhere. This subpackage swaps the "good-enough" approximations for the real
components a production deployment uses:

    manifest_validator  real JSON Schema (Draft 2020-12) validation via jsonschema
    cedar_compiler      agent manifest -> Cedar policy + AVP Cedar-JSON schema
    manifest_signing    cryptographic signed-manifest verify (RSA-PSS / AWS KMS)
    budget_manager_ddb  concurrency-safe token-budget reservation (DynamoDB + sim)

Every component FAILS CLOSED: any error in validation, verification, or
reservation results in rejection, never a silent allow.
"""

from __future__ import annotations

__all__ = [
    "manifest_validator",
    "cedar_compiler",
    "manifest_signing",
    "budget_manager_ddb",
]
