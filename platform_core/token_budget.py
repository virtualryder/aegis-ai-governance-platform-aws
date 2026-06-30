"""token_budget — per-agent/department running token meter with hard/soft caps.

Implements docs/05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md §3: a real-time budget
check on every call that REJECTS or THROTTLES over-budget calls *before* spend
occurs (fail-closed on budget), plus threshold alerts at e.g. 60/85/100%.

Production: the gateway maintains the meter and AWS Budgets is a second
account-level guardrail. This is the offline analog — an in-process meter.

Key concepts:
    - monthly_token_cap   hard ceiling on input+output tokens
    - cap_behavior        'hard' DENIES over-budget calls; 'soft' WARNS, allows
    - alert_thresholds    fractions of the cap that fire one-time alerts
    - preflight()         called BEFORE spend; returns a BudgetDecision
    - commit()            records actual spend after a successful call
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    used_before: int
    requested: int
    cap: int
    cap_behavior: str
    throttled: bool = False
    fired_alerts: list = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(self.cap - self.used_before, 0)


class BudgetMeter:
    """A running token meter for one agent/department budget line."""

    def __init__(
        self,
        agent_id: str,
        dept: str,
        monthly_token_cap: int,
        cap_behavior: str = "hard",
        alert_thresholds=None,
        inference_profile: str = "",
    ):
        if monthly_token_cap < 1:
            raise ValueError("monthly_token_cap must be >= 1")
        if cap_behavior not in ("hard", "soft"):
            raise ValueError("cap_behavior must be 'hard' or 'soft'")
        self.agent_id = agent_id
        self.dept = dept
        self.cap = int(monthly_token_cap)
        self.cap_behavior = cap_behavior
        self.alert_thresholds = sorted(alert_thresholds or [0.6, 0.85, 1.0])
        self.inference_profile = inference_profile
        self.used = 0
        self._alerts_fired: set[float] = set()

    # ----- preflight (before spend) ------------------------------------- #
    def preflight(self, estimated_tokens: int) -> BudgetDecision:
        """Decide whether a call estimated at `estimated_tokens` may proceed.

        This is the FinOps preflight clause of the policy predicate. It does NOT
        mutate the meter — call commit() after a successful spend.
        """
        if estimated_tokens < 0:
            raise ValueError("estimated_tokens must be >= 0")
        projected = self.used + estimated_tokens
        would_breach = projected > self.cap

        fired = self._peek_alerts(projected)

        if would_breach and self.cap_behavior == "hard":
            return BudgetDecision(
                allowed=False,
                reason=(
                    f"budget_exceeded: hard cap {self.cap:,} tokens for "
                    f"agent '{self.agent_id}' (dept '{self.dept}') would be "
                    f"breached: {self.used:,} used + {estimated_tokens:,} "
                    f"requested = {projected:,}"
                ),
                used_before=self.used,
                requested=estimated_tokens,
                cap=self.cap,
                cap_behavior=self.cap_behavior,
                throttled=False,
                fired_alerts=fired,
            )

        if would_breach and self.cap_behavior == "soft":
            return BudgetDecision(
                allowed=True,
                reason=(
                    f"budget_soft_over_cap: soft cap {self.cap:,} exceeded "
                    f"(projected {projected:,}); allowing with alert"
                ),
                used_before=self.used,
                requested=estimated_tokens,
                cap=self.cap,
                cap_behavior=self.cap_behavior,
                throttled=True,  # soft over-cap == throttle/warn signal
                fired_alerts=fired,
            )

        return BudgetDecision(
            allowed=True,
            reason="budget_ok",
            used_before=self.used,
            requested=estimated_tokens,
            cap=self.cap,
            cap_behavior=self.cap_behavior,
            throttled=False,
            fired_alerts=fired,
        )

    # ----- commit (after spend) ----------------------------------------- #
    def commit(self, actual_tokens: int) -> list:
        """Record actual spend; return any alert thresholds newly crossed."""
        if actual_tokens < 0:
            raise ValueError("actual_tokens must be >= 0")
        self.used += actual_tokens
        crossed = self._peek_alerts(self.used)
        newly = [t for t in crossed if t not in self._alerts_fired]
        self._alerts_fired.update(newly)
        return newly

    def _peek_alerts(self, level: int) -> list:
        frac = level / self.cap if self.cap else 0.0
        return [t for t in self.alert_thresholds if frac >= t]

    @property
    def utilization(self) -> float:
        return self.used / self.cap if self.cap else 0.0


class BudgetRegistry:
    """Holds one BudgetMeter per agent and exposes preflight/commit by id."""

    def __init__(self):
        self._meters: dict[str, BudgetMeter] = {}

    def register_from_manifest(self, manifest: dict) -> BudgetMeter:
        md = manifest.get("metadata", {})
        bd = manifest.get("budget", {})
        meter = BudgetMeter(
            agent_id=md.get("id", "unknown"),
            dept=md.get("owner", "unknown"),
            monthly_token_cap=int(bd.get("monthly_token_cap", 1)),
            cap_behavior=bd.get("cap_behavior", "hard"),
            alert_thresholds=bd.get("alert_thresholds"),
            inference_profile=bd.get("inference_profile", ""),
        )
        self._meters[meter.agent_id] = meter
        return meter

    def register(self, meter: BudgetMeter) -> BudgetMeter:
        self._meters[meter.agent_id] = meter
        return meter

    def get(self, agent_id: str) -> BudgetMeter:
        if agent_id not in self._meters:
            raise KeyError(f"no budget meter registered for agent '{agent_id}'")
        return self._meters[agent_id]

    def preflight(self, agent_id: str, estimated_tokens: int) -> BudgetDecision:
        return self.get(agent_id).preflight(estimated_tokens)

    def commit(self, agent_id: str, actual_tokens: int) -> list:
        return self.get(agent_id).commit(actual_tokens)
