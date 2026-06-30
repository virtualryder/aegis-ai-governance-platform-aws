"""approval_ledger — bound, single-use, separation-of-duties human approvals.

Implements the human gate from docs/02-REFERENCE-ARCHITECTURE.md §3.4 and
minimum-bar point 3. An approval token is BOUND to the exact
(agent, tool, arguments-hash, purpose, requester, reviewer, expiry); it is
single-use; the reviewer MUST differ from the requester (separation of duties);
and a REPLAY of a consumed or expired token is rejected.

Production: a DynamoDB conditional write records consumption so a replay fails.
This is the offline analog — an in-memory dict simulating that conditional
write (consume() is atomic w.r.t. the 'consumed' flag).

Flow:
    request_approval(...)  -> a PENDING approval bound to the action
    approve(approval_id, reviewer)  -> APPROVED (enforces reviewer != requester)
    consume(approval_id, agent, tool, args, purpose)  -> True ONCE, then rejects
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field


def arguments_hash(arguments) -> str:
    """Stable hash of tool arguments (order-independent for dicts)."""
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ApprovalError(Exception):
    """Raised on any approval-ledger rule violation (SoD, replay, binding)."""


@dataclass
class Approval:
    approval_id: str
    agent_id: str
    tool_id: str
    args_hash: str
    purpose: str
    requester: str
    reviewer: str = ""
    status: str = "pending"  # pending | approved | consumed | rejected | expired
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    consumed_at: float = 0.0
    separation_of_duties: bool = True

    def is_expired(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self.expires_at != 0.0 and now > self.expires_at


class ApprovalLedger:
    """In-memory ledger simulating a DynamoDB conditional-write approval store."""

    def __init__(self):
        self._store: dict[str, Approval] = {}

    # ----- request ------------------------------------------------------ #
    def request_approval(
        self,
        agent_id: str,
        tool_id: str,
        arguments,
        purpose: str,
        requester: str,
        ttl_seconds: int = 3600,
        separation_of_duties: bool = True,
    ) -> Approval:
        approval = Approval(
            approval_id="apr_" + secrets.token_hex(8),
            agent_id=agent_id,
            tool_id=tool_id,
            args_hash=arguments_hash(arguments),
            purpose=purpose,
            requester=requester,
            expires_at=time.time() + ttl_seconds if ttl_seconds else 0.0,
            separation_of_duties=separation_of_duties,
        )
        self._store[approval.approval_id] = approval
        return approval

    # ----- approve (separation of duties enforced here) ----------------- #
    def approve(self, approval_id: str, reviewer: str) -> Approval:
        ap = self._get(approval_id)
        if ap.is_expired():
            ap.status = "expired"
            raise ApprovalError(f"approval {approval_id} has expired")
        if ap.status != "pending":
            raise ApprovalError(
                f"approval {approval_id} is '{ap.status}', cannot approve"
            )
        if ap.separation_of_duties and reviewer == ap.requester:
            raise ApprovalError(
                f"separation_of_duties violation: reviewer '{reviewer}' must "
                f"differ from requester '{ap.requester}' (self-approval blocked)"
            )
        ap.reviewer = reviewer
        ap.status = "approved"
        return ap

    # ----- consume (single-use, bound, replay-proof) -------------------- #
    def consume(
        self,
        approval_id: str,
        agent_id: str,
        tool_id: str,
        arguments,
        purpose: str,
    ) -> Approval:
        """Atomically consume an approved token for the EXACT bound action.

        Simulates a DynamoDB conditional write: succeeds only if status is
        'approved'; flips it to 'consumed' so any replay is rejected.
        """
        ap = self._get(approval_id)

        if ap.is_expired():
            ap.status = "expired"
            raise ApprovalError(f"approval {approval_id} has expired (replay/expiry)")
        if ap.status == "consumed":
            raise ApprovalError(
                f"approval {approval_id} already consumed "
                f"(replay rejected, single-use)"
            )
        if ap.status != "approved":
            raise ApprovalError(
                f"approval {approval_id} is '{ap.status}', not approved"
            )

        # Binding checks: the token is valid ONLY for the exact action.
        if ap.agent_id != agent_id:
            raise ApprovalError("approval not bound to this agent")
        if ap.tool_id != tool_id:
            raise ApprovalError("approval not bound to this tool")
        if ap.purpose != purpose:
            raise ApprovalError("approval not bound to this purpose")
        if ap.args_hash != arguments_hash(arguments):
            raise ApprovalError(
                "approval not bound to these arguments (arguments-hash mismatch)"
            )

        # Atomic consume.
        ap.status = "consumed"
        ap.consumed_at = time.time()
        return ap

    def get(self, approval_id: str) -> Approval:
        return self._get(approval_id)

    def _get(self, approval_id: str) -> Approval:
        if approval_id not in self._store:
            raise ApprovalError(f"unknown approval id '{approval_id}'")
        return self._store[approval_id]
