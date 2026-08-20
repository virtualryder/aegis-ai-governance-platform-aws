"""kill_switch — the named, platform-wide containment control.

The one-command answer to "can you stop every agent right now?": when the
Kill Switch is ENGAGED, the authorization gateway denies every tool call —
before masking, before policy, before budgets, before approvals — and writes
the denial to the append-only audit. Containment precedes evaluation.

Design rules (all negative-tested in tests/test_kill_switch.py):

  * Fail-closed precedence. The gateway checks the switch FIRST. An engaged
    switch denies even a consequential action carrying a valid, bound
    approval — nothing outranks containment.
  * Separation of duties on release. The actor who engaged the switch cannot
    disengage it; a second identity must. (Engaging is deliberately easy;
    releasing is deliberately deliberate.)
  * Every state change is audited. engage() and disengage() both append to
    the audit ledger with actor, reason, and timestamp — the incident
    timeline writes itself.
  * Budget zeroing on engage. Engaging also zeroes every registered budget
    meter (belt and suspenders: even a caller that somehow bypassed the
    gateway check fails its budget preflight).

Production mapping (see docs/ops/KILL-SWITCH.md): the engaged flag lives in
an SSM parameter (e.g. /aegis/kill-switch) with a short-TTL cache in the
gateway; this module is the offline analog, consistent with the rest of
platform_core.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class KillSwitchError(Exception):
    """Raised on an invalid kill-switch state transition."""


@dataclass
class _StateChange:
    action: str          # "ENGAGE" | "DISENGAGE"
    actor: str
    reason: str
    at: float


@dataclass
class KillSwitch:
    """Platform-wide containment switch. Default: disengaged."""

    audit: object = None                 # AuditLedger (optional, duck-typed)
    budgets: object = None               # BudgetRegistry (optional)
    _engaged: bool = False
    _engaged_by: str = ""
    _reason: str = ""
    history: list = field(default_factory=list)

    # ------------------------------------------------------------------ #
    @property
    def engaged(self) -> bool:
        return self._engaged

    @property
    def reason(self) -> str:
        return self._reason

    # ------------------------------------------------------------------ #
    def engage(self, actor: str, reason: str) -> None:
        """Engage containment. Idempotent; audited; zeroes budgets."""
        if not actor or not reason:
            raise KillSwitchError("engage requires an actor and a reason")
        self._engaged = True
        self._engaged_by = actor
        self._reason = reason
        self.history.append(_StateChange("ENGAGE", actor, reason, time.time()))
        self._audit("ENGAGE", actor, reason)
        self._zero_budgets()

    def disengage(self, actor: str, reason: str) -> None:
        """Release containment. Requires a DIFFERENT actor than engage (SoD)."""
        if not self._engaged:
            raise KillSwitchError("kill switch is not engaged")
        if not actor or not reason:
            raise KillSwitchError("disengage requires an actor and a reason")
        if actor == self._engaged_by:
            raise KillSwitchError(
                "separation of duties: the engaging actor "
                f"({self._engaged_by!r}) cannot disengage"
            )
        self._engaged = False
        self.history.append(_StateChange("DISENGAGE", actor, reason, time.time()))
        self._audit("DISENGAGE", actor, reason)
        self._engaged_by = ""
        self._reason = ""

    # ------------------------------------------------------------------ #
    def _audit(self, action: str, actor: str, reason: str) -> None:
        if self.audit is None:
            return
        try:
            self.audit.append(
                request_id=f"killswitch_{action.lower()}_{int(time.time()*1000)}",
                user=actor,
                agent_id="__platform__",
                tool_id="kill_switch",
                purpose=f"{action}: {reason}",
                data_class=[],
                policy_decision=action,
                decision_reason=f"kill_switch_{action.lower()}: {reason}",
            )
        except Exception:  # noqa: BLE001 — auditing must never block containment
            pass

    def _zero_budgets(self) -> None:
        if self.budgets is None:
            return
        try:
            zero = getattr(self.budgets, "zero_all", None)
            if callable(zero):
                zero()
        except Exception:  # noqa: BLE001 — budget zeroing is belt-and-suspenders
            pass
