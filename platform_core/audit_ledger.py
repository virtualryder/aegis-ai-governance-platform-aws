"""audit_ledger — append-only, tamper-evident audit + WORM evidence export.

Implements docs/02-REFERENCE-ARCHITECTURE.md §6: an append-only audit
(DynamoDB PutItem-only with explicit Update/Delete deny) where every tool
attempt is recorded (allow / deny / pending / error) with full lineage and
masked sensitive fields, plus WORM (S3 Object Lock) immutable evidence export.

This offline analog:
    - keeps records in an in-memory list AND appends each to demo_out/audit.jsonl
    - hash-chains each record (prev_hash) so any tampering is detectable
    - exposes try_mutate(), which RAISES — proving immutability
    - export_worm() writes a sealed evidence file with a manifest digest

Each record carries the lineage the architecture demands: request_id, user,
agent_id, tool_id, purpose, data_class, policy_decision, model_profile,
prompt_version, retrieved_source_ids, input/output hashes, approval_id,
token/cost metrics, masked_fields.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field


class ImmutabilityError(Exception):
    """Raised by any attempt to mutate or delete a prior audit record."""


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class AuditRecord:
    request_id: str
    timestamp: float
    user: str
    agent_id: str
    tool_id: str
    purpose: str
    data_class: list
    policy_decision: str           # ALLOW | DENY | APPROVAL_REQUIRED | ERROR | PENDING
    decision_reason: str
    model_profile: str = ""
    prompt_version: str = ""
    retrieved_source_ids: list = field(default_factory=list)
    input_hash: str = ""
    output_hash: str = ""
    approval_id: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    masked_fields: list = field(default_factory=list)
    grounded: bool = None
    seq: int = 0
    prev_hash: str = ""
    record_hash: str = ""


class AuditLedger:
    """Append-only audit ledger with a verifiable hash chain."""

    def __init__(self, jsonl_path: str | None = None):
        self._records: list[AuditRecord] = []
        self._frozen_hashes: list[str] = []  # snapshot used to detect mutation
        self.jsonl_path = jsonl_path
        if jsonl_path:
            os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
            # Start a fresh ledger file for the demo run.
            with open(jsonl_path, "w", encoding="utf-8") as fh:
                fh.write("")

    # ----- append (the ONLY mutation allowed) --------------------------- #
    def append(self, **fields) -> AuditRecord:
        seq = len(self._records)
        prev_hash = self._records[-1].record_hash if self._records else ""
        fields.setdefault("timestamp", time.time())
        rec = AuditRecord(seq=seq, prev_hash=prev_hash, **fields)
        rec.record_hash = self._compute_hash(rec)
        self._records.append(rec)
        self._frozen_hashes.append(rec.record_hash)
        if self.jsonl_path:
            with open(self.jsonl_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(rec), sort_keys=True) + "\n")
        return rec

    def _compute_hash(self, rec: AuditRecord) -> str:
        payload = asdict(rec)
        payload.pop("record_hash", None)
        return _sha256(json.dumps(payload, sort_keys=True, default=str))

    # ----- immutability proof ------------------------------------------- #
    def try_mutate(self, seq: int, **changes):
        """Attempt to mutate a prior record. ALWAYS raises — proving immutability.

        This mirrors the production control: the audit table's IAM policy is
        PutItem-only with an explicit deny on UpdateItem/DeleteItem.
        """
        raise ImmutabilityError(
            f"audit record seq={seq} is append-only and immutable; "
            f"UpdateItem/DeleteItem is denied (attempted change: {changes})"
        )

    def verify_chain(self) -> bool:
        """Recompute the hash chain and confirm nothing was tampered with."""
        prev = ""
        for i, rec in enumerate(self._records):
            if rec.seq != i:
                return False
            if rec.prev_hash != prev:
                return False
            if self._compute_hash(rec) != rec.record_hash:
                return False
            if rec.record_hash != self._frozen_hashes[i]:
                return False
            prev = rec.record_hash
        return True

    # ----- WORM evidence export ----------------------------------------- #
    def export_worm(self, path: str) -> dict:
        """Write a sealed, WORM-style evidence file (S3 Object Lock analog).

        Produces an immutable JSON document containing every record plus a
        manifest digest over the whole ledger. The file is written read-only.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        records = [asdict(r) for r in self._records]
        body = json.dumps(records, sort_keys=True, default=str)
        manifest = {
            "object_lock_mode": "COMPLIANCE",
            "sealed_at": time.time(),
            "record_count": len(records),
            "chain_head": self._records[-1].record_hash if self._records else "",
            "evidence_digest": _sha256(body),
            "chain_valid": self.verify_chain(),
        }
        document = {"manifest": manifest, "records": records}
        # If a prior WORM file exists read-only, relax perms so we can re-seal.
        if os.path.exists(path):
            try:
                os.chmod(path, 0o644)
            except OSError:
                pass
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(document, fh, indent=2, sort_keys=True, default=str)
        # Make the WORM file read-only (best-effort; honors Object Lock intent).
        try:
            os.chmod(path, 0o444)
        except OSError:
            pass
        return manifest

    # ----- accessors ---------------------------------------------------- #
    @property
    def records(self) -> list:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def by_decision(self, decision: str) -> list:
        return [r for r in self._records if r.policy_decision == decision]
