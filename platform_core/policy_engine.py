"""policy_engine — the deny-by-default ALLOW-iff authorization predicate.

This is the authoritative control from docs/02-REFERENCE-ARCHITECTURE.md §3.
A call is ALLOWED iff EVERY clause holds:

    ALLOW iff:
      authenticated_user is valid
      AND agent grant permits the tool
      AND user entitlement permits the tool        # least-privilege intersection
      AND declared purpose is allowed              # purpose limitation
      AND data-class boundary is satisfied         # CJI/FTI/PHI/EDU/public isolation
      AND consent exists when required             # 42 CFR Pt 2 / COPPA / FERPA
      AND residency boundary is satisfied          # region / GovCloud vs commercial
      AND token/cost budget is available           # FinOps preflight
      AND a valid approval exists when required     # human gate

The engine returns ALLOW, DENY(reason), or APPROVAL_REQUIRED. It is
DEFAULT-DENY: any clause that cannot be affirmatively satisfied denies.

The engine is deliberately pure (no I/O): it takes a Decision context and the
agent manifest plus side registries (entitlements, consent, budget) and returns
a structured Decision. The gateway orchestrates I/O around it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Effect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass
class AuthContext:
    """Everything the predicate needs to decide one tool call."""
    user: str
    authenticated: bool
    user_entitlements: set          # tool ids the human is entitled to
    agent_id: str
    tool_id: str
    scope: str                      # requested scope: read/write/execute/admin
    purpose: str
    data_classes: list              # data classes this call touches
    region: str                     # caller/target region
    consent_present: bool = False
    approval_valid: bool = False    # a valid bound approval has been supplied
    budget_ok: bool = True          # FinOps preflight result
    budget_reason: str = "budget_ok"


@dataclass
class Decision:
    effect: Effect
    reason: str
    clause: str = ""                # which clause drove a non-ALLOW result
    checks: dict = field(default_factory=dict)  # per-clause pass/fail trace

    @property
    def allowed(self) -> bool:
        return self.effect is Effect.ALLOW


# Purposes the platform recognizes as legitimate (purpose limitation).
DEFAULT_ALLOWED_PURPOSES = {
    "triage",
    "classify",
    "draft_response",
    "summarize",
    "lookup",
    "resident_intake",
    "policy_search",
    "decision_support",
}

# Data classes that REQUIRE consent before they may be processed.
CONSENT_REQUIRED_CLASSES = {"sud", "edu", "phi"}

# Data classes that must be processed only in GovCloud regions (residency).
GOVCLOUD_ONLY_CLASSES = {"cji", "fti"}
GOVCLOUD_REGIONS = {"us-gov-west-1", "us-gov-east-1"}


class PolicyEngine:
    def __init__(
        self,
        allowed_purposes=None,
        consent_required_classes=None,
        govcloud_only_classes=None,
        govcloud_regions=None,
    ):
        self.allowed_purposes = set(allowed_purposes or DEFAULT_ALLOWED_PURPOSES)
        self.consent_required_classes = set(
            consent_required_classes
            if consent_required_classes is not None
            else CONSENT_REQUIRED_CLASSES
        )
        self.govcloud_only_classes = set(
            govcloud_only_classes
            if govcloud_only_classes is not None
            else GOVCLOUD_ONLY_CLASSES
        )
        self.govcloud_regions = set(govcloud_regions or GOVCLOUD_REGIONS)

    # ----- the predicate ------------------------------------------------ #
    def evaluate(self, ctx: AuthContext, manifest: dict) -> Decision:
        checks: dict[str, bool] = {}

        md = manifest.get("metadata", {})
        grants = manifest.get("grants", {})
        grant_tools = {
            t["id"]: t for t in grants.get("tools", []) if isinstance(t, dict)
        }
        consequential = set(grants.get("consequential", []) or [])
        declared_classes = set(md.get("classification", []) or [])

        def deny(clause: str, reason: str) -> Decision:
            checks[clause] = False
            return Decision(Effect.DENY, reason, clause=clause, checks=checks)

        # 1. authenticated_user is valid
        if not ctx.authenticated or not ctx.user:
            return deny("authenticated_user", "authenticated_user invalid or missing")
        checks["authenticated_user"] = True

        # 2. agent grant permits the tool (executable grants only; consequential
        #    tools are WITHHELD and must go through the human gate)
        if ctx.tool_id in consequential and ctx.tool_id not in grant_tools:
            # Consequential action -> requires a valid approval (human gate).
            if not ctx.approval_valid:
                checks["agent_grant"] = True
                checks["approval"] = False
                return Decision(
                    Effect.APPROVAL_REQUIRED,
                    f"tool '{ctx.tool_id}' is a consequential action withheld from "
                    f"the agent; a valid human-gate approval is required",
                    clause="approval",
                    checks=checks,
                )
            # An approval is present -> the human gate satisfies the grant.
            checks["agent_grant"] = True
        else:
            if ctx.tool_id not in grant_tools:
                return deny(
                    "agent_grant",
                    f"agent '{ctx.agent_id}' has no grant for tool '{ctx.tool_id}'",
                )
            grant = grant_tools[ctx.tool_id]
            if not _scope_satisfies(grant.get("scope", ""), ctx.scope):
                return deny(
                    "agent_grant",
                    f"requested scope '{ctx.scope}' exceeds granted scope "
                    f"'{grant.get('scope')}' for tool '{ctx.tool_id}'",
                )
            checks["agent_grant"] = True

        # 3. user entitlement permits the tool (least-privilege intersection)
        if ctx.tool_id not in ctx.user_entitlements:
            return deny(
                "user_entitlement",
                f"user '{ctx.user}' is not entitled to tool '{ctx.tool_id}' "
                f"(permitted = grant ∩ entitlement)",
            )
        checks["user_entitlement"] = True

        # 4. declared purpose is allowed (purpose limitation)
        if ctx.purpose not in self.allowed_purposes:
            return deny(
                "purpose",
                f"declared purpose '{ctx.purpose}' is not an allowed purpose",
            )
        checks["purpose"] = True

        # 5. data-class boundary is satisfied (isolation)
        call_classes = set(ctx.data_classes or [])
        undeclared = call_classes - declared_classes
        if undeclared:
            return deny(
                "data_class_boundary",
                f"data class(es) {sorted(undeclared)} not declared in agent "
                f"classification {sorted(declared_classes)}",
            )
        # Per-tool data-class restriction, if present.
        grant = grant_tools.get(ctx.tool_id)
        if grant and grant.get("data_classes"):
            tool_allowed = set(grant["data_classes"])
            over = call_classes - tool_allowed
            if over:
                return deny(
                    "data_class_boundary",
                    f"data class(es) {sorted(over)} exceed tool "
                    f"'{ctx.tool_id}' permitted classes {sorted(tool_allowed)}",
                )
        checks["data_class_boundary"] = True

        # 6. consent exists when required
        if (call_classes & self.consent_required_classes) and not ctx.consent_present:
            return deny(
                "consent",
                f"consent required for class(es) "
                f"{sorted(call_classes & self.consent_required_classes)} but not present",
            )
        checks["consent"] = True

        # 7. residency boundary is satisfied
        if (call_classes & self.govcloud_only_classes) and (
            ctx.region not in self.govcloud_regions
        ):
            return deny(
                "residency",
                f"class(es) {sorted(call_classes & self.govcloud_only_classes)} "
                f"must run in GovCloud {sorted(self.govcloud_regions)}, "
                f"not region '{ctx.region}'",
            )
        checks["residency"] = True

        # 8. token/cost budget is available (FinOps preflight)
        if not ctx.budget_ok:
            return deny("budget", ctx.budget_reason)
        checks["budget"] = True

        # 9. a valid approval exists when required (already handled in clause 2
        #    for consequential tools; here we re-affirm for any approval-bearing
        #    consequential call).
        if ctx.tool_id in consequential and not ctx.approval_valid:
            checks["approval"] = False
            return Decision(
                Effect.APPROVAL_REQUIRED,
                f"valid approval required for consequential tool '{ctx.tool_id}'",
                clause="approval",
                checks=checks,
            )
        checks["approval"] = True

        return Decision(Effect.ALLOW, "all clauses satisfied", checks=checks)


_SCOPE_RANK = {"read": 1, "write": 2, "execute": 2, "admin": 3}


def _scope_satisfies(granted: str, requested: str) -> bool:
    """A granted scope satisfies a request if it is at least as privileged.

    read < write == execute < admin. (write and execute are siblings; a write
    grant does not satisfy an execute request and vice versa unless admin.)
    """
    if granted == requested:
        return True
    if granted == "admin":
        return True
    # read-only requests are satisfied by any higher grant
    if requested == "read" and _SCOPE_RANK.get(granted, 0) >= 1:
        return True
    return False
