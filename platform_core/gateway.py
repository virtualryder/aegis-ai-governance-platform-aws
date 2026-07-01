"""gateway — the MCP authorization gateway tying the control plane together.

Implements docs/02-REFERENCE-ARCHITECTURE.md §3: every tool call flows through
    policy_engine -> budget preflight -> (approval if consequential)
        -> scoped-token mint (simulated) -> tool exec -> masked append-only audit

Consequential actions declared in the manifest are WITHHELD and require the
human gate. Every attempt — allow / deny / pending / error — is written to the
append-only audit with masked sensitive fields and full lineage.

This is the offline analog of AgentCore Gateway + Policy in AgentCore (Cedar).
No AWS, no network.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from . import masker
from .approval_ledger import ApprovalError, ApprovalLedger
from .audit_ledger import AuditLedger
from .chargeback import UsageLedger
from .policy_engine import AuthContext, Decision, Effect, PolicyEngine
from .token_budget import BudgetRegistry


def _hash(s) -> str:
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:16]


@dataclass
class ToolCall:
    user: str
    authenticated: bool
    user_entitlements: set
    agent_id: str
    tool_id: str
    scope: str
    purpose: str
    data_classes: list
    region: str
    arguments: dict = field(default_factory=dict)
    payload: str = ""               # text that must be masked at the boundary
    consent_present: bool = False
    approval_id: str = ""           # set for consequential actions
    estimated_tokens: int = 1000
    model_profile: str = ""
    prompt_version: str = ""
    retrieved_source_ids: list = field(default_factory=list)
    grounded: bool = None
    cost_per_1k_usd: float = 0.003


@dataclass
class GatewayResult:
    effect: Effect
    reason: str
    output: object = None
    audit_record: object = None
    scoped_token: str = ""
    masked_payload: str = ""

    @property
    def allowed(self) -> bool:
        return self.effect is Effect.ALLOW


class AuthorizationGateway:
    """The single broker every agent tool call passes through."""

    def __init__(
        self,
        audit: AuditLedger,
        budgets: BudgetRegistry,
        approvals: ApprovalLedger,
        usage: UsageLedger,
        policy: PolicyEngine | None = None,
    ):
        self.audit = audit
        self.budgets = budgets
        self.approvals = approvals
        self.usage = usage
        self.policy = policy or PolicyEngine()
        self._tools = {}   # tool_id -> callable(arguments) -> output
        self._agents = {}  # agent_id -> manifest

    # ----- registration ------------------------------------------------- #
    def register_agent(self, manifest: dict) -> None:
        self._agents[manifest["metadata"]["id"]] = manifest
        self.budgets.register_from_manifest(manifest)

    def register_tool(self, tool_id: str, handler) -> None:
        self._tools[tool_id] = handler

    # ----- the brokered call -------------------------------------------- #
    def call(self, tc: ToolCall) -> GatewayResult:
        request_id = "req_" + secrets.token_hex(6)
        manifest = self._agents.get(tc.agent_id)
        if manifest is None:
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision="ERROR", decision_reason="unregistered agent",
            )
            return GatewayResult(Effect.DENY, "unregistered agent", audit_record=rec)

        # --- boundary masking, FAIL CLOSED ------------------------------ #
        masked_payload = ""
        masked_fields: list = []
        try:
            # Pass the payload through verbatim. A None payload models a masker
            # that cannot run -> mask_report raises -> the boundary fails closed.
            mres = masker.mask_report(tc.payload, tc.data_classes)
            masked_payload = mres.masked_text
            masked_fields = mres.masked_fields
        except masker.MaskingError as exc:
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision="DENY",
                decision_reason=f"masking_fail_closed: {exc}",
            )
            return GatewayResult(
                Effect.DENY, f"masking_fail_closed: {exc}", audit_record=rec
            )

        # --- FinOps budget preflight ------------------------------------ #
        budget_ok, budget_reason = True, "budget_ok"
        try:
            bd = self.budgets.preflight(tc.agent_id, tc.estimated_tokens)
            budget_ok, budget_reason = bd.allowed, bd.reason
        except KeyError as exc:
            budget_ok, budget_reason = False, f"no budget meter: {exc}"

        # --- validate an approval if one is supplied -------------------- #
        approval_valid = False
        if tc.approval_id:
            try:
                # peek without consuming: check it is approved + bound
                ap = self.approvals.get(tc.approval_id)
                approval_valid = (
                    ap.status == "approved"
                    and not ap.is_expired()
                    and ap.agent_id == tc.agent_id
                    and ap.tool_id == tc.tool_id
                )
            except ApprovalError:
                approval_valid = False

        # --- policy predicate (deny-by-default) ------------------------- #
        ctx = AuthContext(
            user=tc.user,
            authenticated=tc.authenticated,
            user_entitlements=set(tc.user_entitlements),
            agent_id=tc.agent_id,
            tool_id=tc.tool_id,
            scope=tc.scope,
            purpose=tc.purpose,
            data_classes=tc.data_classes,
            region=tc.region,
            consent_present=tc.consent_present,
            approval_valid=approval_valid,
            budget_ok=budget_ok,
            budget_reason=budget_reason,
        )
        try:
            decision: Decision = self.policy.evaluate(ctx, manifest)
        except Exception as exc:  # noqa: BLE001 - policy fault must fail closed
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose,
                data_class=tc.data_classes, policy_decision="DENY",
                decision_reason=f"policy_eval_fail_closed: {exc}",
                masked_fields=masked_fields,
            )
            return GatewayResult(
                Effect.DENY, f"policy_eval_fail_closed: {exc}",
                audit_record=rec, masked_payload=masked_payload,
            )

        # --- non-allow paths: audit and return ------------------------- #
        if decision.effect is not Effect.ALLOW:
            policy_decision = (
                "APPROVAL_REQUIRED"
                if decision.effect is Effect.APPROVAL_REQUIRED
                else "DENY"
            )
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision=policy_decision, decision_reason=decision.reason,
                model_profile=tc.model_profile, prompt_version=tc.prompt_version,
                retrieved_source_ids=tc.retrieved_source_ids,
                input_hash=_hash(tc.arguments), approval_id=tc.approval_id,
                masked_fields=masked_fields, grounded=tc.grounded,
            )
            return GatewayResult(
                decision.effect, decision.reason,
                audit_record=rec, masked_payload=masked_payload,
            )

        # --- consequential: consume the bound, single-use approval ------ #
        consequential = set(manifest.get("grants", {}).get("consequential", []))
        if tc.tool_id in consequential:
            try:
                self.approvals.consume(
                    tc.approval_id, tc.agent_id, tc.tool_id,
                    tc.arguments, tc.purpose,
                )
            except ApprovalError as exc:
                rec = self.audit.append(
                    request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                    tool_id=tc.tool_id, purpose=tc.purpose,
                    data_class=tc.data_classes, policy_decision="DENY",
                    decision_reason=f"approval_consume_failed: {exc}",
                    approval_id=tc.approval_id, masked_fields=masked_fields,
                )
                return GatewayResult(
                    Effect.DENY, f"approval_consume_failed: {exc}", audit_record=rec
                )

        # --- default-deny: a tool with no registered handler cannot run - #
        # The gateway is fail-closed: policy may ALLOW, but if nothing is
        # actually wired to service the call we DENY rather than fabricate
        # a success. This closes the offline fail-open where an unregistered
        # tool returned {"ok": True}.
        handler = self._tools.get(tc.tool_id)
        if handler is None:
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose,
                data_class=tc.data_classes, policy_decision="DENY",
                decision_reason="tool-not-registered",
                approval_id=tc.approval_id, masked_fields=masked_fields,
            )
            return GatewayResult(
                Effect.DENY, "tool-not-registered",
                audit_record=rec, masked_payload=masked_payload,
            )

        # --- mint a scoped, per-call token (simulated OBO/STS) ---------- #
        scoped_token = self._mint_scoped_token(tc)

        # --- execute the tool ------------------------------------------- #
        try:
            output = handler(tc.arguments)
            exec_error = None
        except Exception as exc:  # noqa: BLE001 - boundary must capture all
            output, exec_error = None, str(exc)

        # --- commit spend + usage ledger -------------------------------- #
        tokens_in = tc.estimated_tokens
        tokens_out = 0
        cost_usd = (tc.estimated_tokens / 1000.0) * tc.cost_per_1k_usd
        try:
            self.budgets.commit(tc.agent_id, tc.estimated_tokens)
        except KeyError:
            pass

        meter = None
        try:
            meter = self.budgets.get(tc.agent_id)
        except KeyError:
            pass
        md = manifest.get("metadata", {})
        self.usage.record(
            agent_id=tc.agent_id,
            dept=md.get("owner", "unknown"),
            team=md.get("team", "default"),
            app=tc.agent_id,
            data_class=(tc.data_classes[0] if tc.data_classes else "public"),
            pack=(md.get("packs", ["none"]) or ["none"])[0],
            inference_profile=(meter.inference_profile if meter else ""),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )

        # --- masked append-only audit ----------------------------------- #
        # If the audit write fails on a consequential or sensitive call we
        # DENY: an unauditable side effect is not permitted (fail closed).
        consequential = set(manifest.get("grants", {}).get("consequential", []))
        sensitive = bool(set(tc.data_classes or []) - {"public"})
        try:
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision=("ERROR" if exec_error else "ALLOW"),
                decision_reason=(exec_error or decision.reason),
                model_profile=tc.model_profile, prompt_version=tc.prompt_version,
                retrieved_source_ids=tc.retrieved_source_ids,
                input_hash=_hash(tc.arguments), output_hash=_hash(output),
                approval_id=tc.approval_id, tokens_in=tokens_in,
                tokens_out=tokens_out, cost_usd=cost_usd,
                masked_fields=masked_fields, grounded=tc.grounded,
            )
        except Exception as exc:  # noqa: BLE001 - audit fault handling
            if tc.tool_id in consequential or sensitive:
                return GatewayResult(
                    Effect.DENY, f"audit_fail_closed: {exc}",
                    masked_payload=masked_payload,
                )
            raise

        if exec_error:
            return GatewayResult(
                Effect.DENY, f"tool_exec_error: {exec_error}",
                audit_record=rec, masked_payload=masked_payload,
            )

        return GatewayResult(
            Effect.ALLOW, decision.reason, output=output,
            audit_record=rec, scoped_token=scoped_token,
            masked_payload=masked_payload,
        )

    def _mint_scoped_token(self, tc: ToolCall) -> str:
        """Simulate an AgentCore Identity OBO / STS scoped, per-call token.

        Never a long-lived credential: bound to user+agent+tool+scope+nonce and
        short-lived. Returned to the caller for the single downstream call only.
        """
        nonce = secrets.token_hex(6)
        material = f"{tc.user}|{tc.agent_id}|{tc.tool_id}|{tc.scope}|{int(time.time())}|{nonce}"
        return "scoped_" + hashlib.sha256(material.encode()).hexdigest()[:24]
