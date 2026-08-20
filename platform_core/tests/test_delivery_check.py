"""Negative tests for the customer-delivery gate (prod/manifest_validator.delivery_check).

Proves dev conveniences cannot reach a customer: placeholder credentials,
demo-grade audit retention, and unsigned manifests each block delivery, and a
production-shaped manifest passes.
"""

from __future__ import annotations

import copy

from prod.manifest_validator import delivery_check

CLEAN = {
    "agent": {"slug": "example", "title": "Example", "industry": "SLG"},
    "identity": {
        "pool_name": "ex-pool",
        "users": [{"name": "reviewer", "password": "${EX_REVIEWER_PW}", "in_group": True}],
    },
    "audit": {"object_lock_mode": "COMPLIANCE", "retention_days": 1825},
    "signing": {
        "publisher": "virtualryder",
        "algorithm": "rsassa-pss-sha256",
        "signature": "MEUCIQDx-real-signature-bytes",
    },
}


def test_clean_manifest_passes():
    ok, errors = delivery_check(copy.deepcopy(CLEAN))
    assert ok, errors


def test_placeholder_credentials_block_delivery():
    m = copy.deepcopy(CLEAN)
    m["identity"]["users"][0]["password"] = "ChangeMe-Reviewer1!"
    ok, errors = delivery_check(m)
    assert not ok
    assert any("placeholder_credential" in e for e in errors)


def test_demo_retention_blocks_delivery():
    m = copy.deepcopy(CLEAN)
    m["audit"] = {"object_lock_mode": "GOVERNANCE", "retention_days": 1}
    ok, errors = delivery_check(m)
    assert not ok
    assert any("object_lock_mode=GOVERNANCE" in e for e in errors)
    assert any("retention_days=1" in e for e in errors)


def test_unsigned_manifest_blocks_delivery():
    m = copy.deepcopy(CLEAN)
    m["signing"]["signature"] = None
    ok, errors = delivery_check(m)
    assert not ok
    assert any("unsigned_manifest" in e for e in errors)


def test_load_fault_fails_closed():
    ok, errors = delivery_check("/nonexistent/manifest.yaml")
    assert not ok
    assert any("manifest_load_error" in e for e in errors)
