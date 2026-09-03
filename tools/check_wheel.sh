#!/usr/bin/env bash
# COPILOT-6 (2026-09-03): prove the platform_core wheel is a real package - build it, install it in a
# CLEAN venv (no repo on sys.path), import platform_core + platform_core.prod and exercise one decision.
# Before this, `[tool.setuptools.packages.find] include = ["platform_core*"]` inside platform_core/
# discovered nothing and the wheel shipped zero modules. CI runs this on every push.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-dist}"
rm -rf "$OUT"
python -m pip install -q build
python -m build --wheel --outdir "$OUT" platform_core
WHEEL="$(ls "$OUT"/aegis_platform_core-*.whl)"
VENV="$(mktemp -d)/venv"
python -m venv "$VENV"
if [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"; else PY="$VENV/Scripts/python.exe"; fi
"$PY" -m pip install -q "$WHEEL"                 # bare install: the stdlib-only control plane
"$PY" -m pip install -q "${WHEEL}[prod]"         # + the prod extra (cryptography, jsonschema, boto3)
cd /tmp   # away from the repo so the import can only come from the installed wheel
"$PY" - <<'PYEOF'
import platform_core, platform_core.prod, os
from platform_core import gateway, policy_engine, masker, approval_ledger, audit_ledger, token_budget, chargeback, kill_switch, model_gateway, manifest_loader
from platform_core.prod import cedar_compiler, manifest_signing, manifest_validator, budget_manager_ddb
assert "site-packages" in platform_core.__file__, platform_core.__file__
eng = policy_engine.PolicyEngine()
ctx = policy_engine.AuthContext(user="u", authenticated=True, user_entitlements={"kb.read"}, agent_id="a", tool_id="db.drop",
                                scope="read", purpose="lookup", data_classes=["public"], region="us-east-1",
                                consent_present=True, approval_valid=False)
d = eng.evaluate(ctx, {"metadata": {"id": "a", "classification": ["public"]}, "grants": {"tools": [{"id": "kb.read", "scope": "read", "data_classes": ["public"]}], "consequential": []}})
assert d.effect is policy_engine.Effect.DENY, d
assert hasattr(policy_engine.Effect, "INDETERMINATE")
print("wheel OK:", os.path.basename(platform_core.__file__), "->", platform_core.__file__)
PYEOF
echo "wheel installs and imports from a clean venv: $WHEEL"
sha256sum "$WHEEL"
