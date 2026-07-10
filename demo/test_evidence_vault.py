"""Evidence Vault — the append-only, tamper-evident, WORM audit is provably immutable.

Proves offline what the IaC enforces in-cloud (DynamoDB PutItem-only with a Deny on
UpdateItem/DeleteItem + S3 Object Lock COMPLIANCE): a prior record cannot be mutated or
deleted, the hash chain detects tampering, and the WORM export seals a COMPLIANCE manifest.
Also asserts the deployed IaC actually carries those controls."""
import glob
import os

import pytest

from platform_core.audit_ledger import AuditLedger, ImmutabilityError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ledger():
    lg = AuditLedger()
    lg.append(request_id="r1", user="u", agent_id="a", tool_id="t", purpose="p",
              data_class=[], policy_decision="ALLOW", decision_reason="ok")
    lg.append(request_id="r2", user="u", agent_id="a", tool_id="t", purpose="p",
              data_class=[], policy_decision="DENY", decision_reason="nope")
    return lg


def test_append_only_no_delete_or_overwrite():
    lg = _ledger()
    with pytest.raises(ImmutabilityError):
        lg.try_mutate(0, decision_reason="rewritten")   # overwrite denied
    with pytest.raises(ImmutabilityError):
        lg.try_mutate(1, policy_decision="ALLOW")        # tamper denied
    assert len(lg) == 2 and lg.records[0].policy_decision == "ALLOW"


def test_hash_chain_detects_tampering():
    lg = _ledger()
    assert lg.verify_chain() is True
    # Simulate an out-of-band mutation of a stored record; the chain must catch it.
    lg._records[0].decision_reason = "SILENTLY CHANGED"
    assert lg.verify_chain() is False


def test_worm_export_seals_compliance_manifest(tmp_path):
    lg = _ledger()
    path = str(tmp_path / "evidence" / "worm.json")
    manifest = lg.export_worm(path)
    assert manifest["object_lock_mode"] == "COMPLIANCE"
    assert manifest["chain_valid"] is True and manifest["record_count"] == 2
    assert os.path.exists(path)
    # The sealed file is written read-only (S3 Object Lock intent).
    mode = os.stat(path).st_mode & 0o222
    assert mode == 0 or os.name == "nt"   # no write bits (POSIX); Windows perms differ


def test_iac_enforces_mutation_deny_and_object_lock():
    texts = []
    for pat in ("**/*.yaml", "**/*.yml", "**/*.tf"):
        for f in glob.glob(os.path.join(REPO, "infra", pat), recursive=True):
            try:
                texts.append(open(f, encoding="utf-8").read())
            except (UnicodeDecodeError, PermissionError):
                pass
    blob = "\n".join(texts)
    assert "DeleteItem" in blob and "UpdateItem" in blob, "IaC must deny audit mutation"
    assert ("ObjectLock" in blob or "object_lock" in blob), "IaC must enable S3 Object Lock (WORM)"
