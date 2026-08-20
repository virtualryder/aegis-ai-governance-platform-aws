"""manifest_validator — REAL JSON Schema (Draft 2020-12) manifest validation.

Replaces the "good-enough subset" checks in platform_core/manifest_loader.py
with authoritative validation of an agent manifest against
governance/onboarding/agent-manifest.schema.json using the `jsonschema`
library and the Draft 2020-12 dialect the schema declares.

Fail-closed contract: any schema violation, unreadable manifest, unreadable or
malformed schema, or unexpected error => (False, [errors]). Only a fully
conformant manifest returns (True, []).

    validate_manifest(path_or_dict) -> (ok: bool, errors: list[str])
"""

from __future__ import annotations

import json
import os
from typing import Union

try:
    import yaml  # PyYAML: manifests are authored in YAML
except Exception:  # pragma: no cover - yaml is a hard dep in practice
    yaml = None

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


# Resolve the canonical schema shipped in the repo.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DEFAULT_SCHEMA_PATH = os.path.join(
    _REPO_ROOT, "governance", "onboarding", "agent-manifest.schema.json"
)


def load_schema(schema_path: str = DEFAULT_SCHEMA_PATH) -> dict:
    """Load and return the manifest JSON Schema. Raises on failure."""
    with open(schema_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_manifest(path_or_dict: Union[str, dict]) -> dict:
    """Coerce a path (YAML/JSON) or dict into a manifest dict. Raises on fault."""
    if isinstance(path_or_dict, dict):
        return path_or_dict
    if not isinstance(path_or_dict, str):
        raise TypeError(
            f"manifest must be a path or dict, got {type(path_or_dict).__name__}"
        )
    with open(path_or_dict, "r", encoding="utf-8") as fh:
        text = fh.read()
    # Try YAML first (a superset of JSON); fall back to strict JSON.
    if yaml is not None:
        data = yaml.safe_load(text)
    else:  # pragma: no cover
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("manifest did not parse to a mapping/object")
    return data


def _format_error(err) -> str:
    """Render a jsonschema ValidationError as a stable, human-readable string."""
    location = "/".join(str(p) for p in err.absolute_path) or "<root>"
    return f"{location}: {err.message}"


def validate_manifest(
    path_or_dict: Union[str, dict],
    schema_path: str = DEFAULT_SCHEMA_PATH,
) -> tuple[bool, list]:
    """Validate a manifest against the Draft 2020-12 schema. Fail closed.

    Returns (True, []) only when the manifest is fully conformant; otherwise
    (False, [error strings]). Never raises: any fault becomes a rejection.
    """
    # Load the schema; a broken schema must fail closed, not pass everything.
    try:
        schema = load_schema(schema_path)
    except Exception as exc:  # noqa: BLE001 - fail closed
        return False, [f"schema_load_error: {exc}"]

    # Ensure the validator itself is valid (guards against schema drift).
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return False, [f"schema_invalid: {exc.message}"]
    except Exception as exc:  # noqa: BLE001 - fail closed
        return False, [f"schema_invalid: {exc}"]

    # Load the manifest.
    try:
        manifest = _load_manifest(path_or_dict)
    except Exception as exc:  # noqa: BLE001 - fail closed
        return False, [f"manifest_load_error: {exc}"]

    # Validate; collect ALL errors deterministically.
    try:
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(manifest),
            key=lambda e: (list(e.absolute_path), e.message),
        )
    except Exception as exc:  # noqa: BLE001 - fail closed
        return False, [f"validation_error: {exc}"]

    if errors:
        return False, [_format_error(e) for e in errors]
    return True, []


# --------------------------------------------------------------------------- #
# Customer-delivery gate — fail-closed checks that dev conveniences never ship.
# Works on BOTH manifest dialects: the onboarding contract
# (apiVersion/kind/metadata/...) and the governed-hero deploy manifest
# (agent/identity/engine/gateway/...). See CUSTOMER-DELIVERY-CHECKLIST.md.
# --------------------------------------------------------------------------- #
_PLACEHOLDER_MARKERS = ("changeme", "change-me", "change_me")
_MIN_DELIVERY_RETENTION_DAYS = 30


def _walk_strings(node, path=""):
    """Yield (path, value) for every string in a nested manifest structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}/{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def delivery_check(path_or_dict: Union[str, dict]) -> tuple[bool, list]:
    """Customer-delivery gate. Returns (ok, [errors]); fail closed on faults.

    Blocks delivery when the manifest still carries development conveniences:
      * placeholder credentials (any string containing a ChangeMe marker);
      * demo-grade audit retention (GOVERNANCE mode or retention below
        _MIN_DELIVERY_RETENTION_DAYS days) — production retention is set per
        the record class (see CUSTOMER-DELIVERY-CHECKLIST.md);
      * an unsigned manifest (signing.signature missing/empty/null) when a
        signing block is declared.
    """
    try:
        manifest = _load_manifest(path_or_dict)
    except Exception as exc:  # noqa: BLE001 - fail closed
        return False, [f"manifest_load_error: {exc}"]

    errors: list = []

    # 1 — placeholder credentials anywhere in the manifest.
    for path, value in _walk_strings(manifest):
        low = value.lower()
        if any(m in low for m in _PLACEHOLDER_MARKERS):
            errors.append(
                f"placeholder_credential: {path} still contains a ChangeMe "
                "marker — rotate all credentials before delivery"
            )

    # 2 — demo-grade audit retention.
    audit = manifest.get("audit") or {}
    if isinstance(audit, dict) and audit:
        mode = str(audit.get("object_lock_mode", "")).upper()
        try:
            days = int(audit.get("retention_days", 0))
        except (TypeError, ValueError):
            days = 0
        if mode and mode != "COMPLIANCE":
            errors.append(
                f"audit_retention: object_lock_mode={mode or '<unset>'} — "
                "delivery requires COMPLIANCE mode per the record class"
            )
        if days < _MIN_DELIVERY_RETENTION_DAYS:
            errors.append(
                f"audit_retention: retention_days={days} is demo-grade — set "
                "per the record-class table in CUSTOMER-DELIVERY-CHECKLIST.md"
            )

    # 3 — unsigned manifest.
    signing = manifest.get("signing") or {}
    if isinstance(signing, dict) and signing:
        sig = signing.get("signature")
        if not sig or (isinstance(sig, str) and not sig.strip()):
            errors.append(
                "unsigned_manifest: signing.signature is empty — sign with "
                "platform_core/prod/manifest_signing.py before delivery"
            )

    return (len(errors) == 0), errors
