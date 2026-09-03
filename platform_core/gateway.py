"""gateway — the MCP authorization gateway tying the control plane together.

Implements docs/02-REFERENCE-ARCHITECTURE.md §3: every tool call flows through
    policy_engine -> budget preflight -> (approval if consequential)
        -> scoped-token mint (simulated) -> tool exec -> masked append-only audit

Consequential actions declared in the manifest are WITHHELD and require the
human gate. Every attempt — allow / deny / pending / error — is written to the
append-only audit with masked sensitive fields and full lineage.

Durable intent / outbox ordering (COPILOT-1, 2026-09-03). A side effect must never
run without a durable record that it was authorized, and an audit failure must
never be reported as DENY *after* the side effect happened (the caller would
retry and duplicate a real-world action). So the ALLOW path is:

    1. append AUTHORIZED-INTENT (request, agent, tool, args hash, purpose,
       approval id, idempotency key)      -> fails => DENY, nothing consumed/run
    2. consume the bound single-use approval (consequential only)
    3. execute the connector with the idempotency key (the gateway also
       de-duplicates by that key: a completed key is never executed twice -
       a replay is DENIED with already_completed=True, output not re-served)
    4. append COMPLETED / FAILED           -> fails => INDETERMINATE
       (RECONCILIATION_REQUIRED): the effect happened, the INTENT row is the
       reconciliation anchor, the caller must not retry.

Mirror on the AgentCore path: governed-core finalize_signoff writes INTENT
before COMMITTED and refuses on an unwritable INTENT (benefits DEPLOYMENT-GUIDE).

This is the offline analog of AgentCore Gateway + Policy in AgentCore (Cedar).
No AWS, no network.
"""

from __future__ import annotations

import hashlib
import inspect
import secrets
import time
from dataclasses import dataclass, field

from . import masker
from .approval_ledger import ApprovalError, ApprovalLedger, arguments_hash
from .audit_ledger import AuditLedger
from .chargeback import UsageLedger
from .policy_engine import AuthContext, Decision, Effect, PolicyEngine
from .token_budget import BudgetRegistry


def _hash(s) -> str:
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:16]


def _accepts_idempotency_key(handler) -> bool:
    """True if the connector takes an `idempotency_key` keyword (or **kwargs)."""
    try:
        params = inspect.signature(handler).parameters
    except (TypeError, ValueError):
        return False
    if "idempotency_key" in params:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


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
    idempotency_key: str = ""
    intent_record: object = None    # the AUTHORIZED-INTENT row (reconciliation anchor)
    already_completed: bool = False # replay of a key that reached COMPLETED (never re-executed)

    @property
    def allowed(self) -> bool:
        return self.effect is Effect.ALLOW

    @property
    def reconciliation_required(self) -> bool:
        """The side effect ran but its completion could not be recorded."""
        return self.effect is Effect.INDETERMINATE


class AuthorizationGateway:
    """The single broker every agent tool call passes through."""

    def __init__(
        self,
        audit: AuditLedger,
        budgets: BudgetRegistry,
        approvals: ApprovalLedger,
        usage: UsageLedger,
        policy: PolicyEngine | None = None,
        kill_switch=None,            # KillSwitch | None — platform containment
    ):
        self.audit = audit
        self.budgets = budgets
        self.approvals = approvals
        self.usage = usage
        self.policy = policy or PolicyEngine()
        self.kill_switch = kill_switch
        self._tools = {}   # tool_id -> callable(arguments[, idempotency_key]) -> output
        self._agents = {}  # agent_id -> manifest
        # Outbox: idempotency keys that reached COMPLETED. The offline analog
        # of the DynamoDB conditional put on the intent table; a key that already
        # completed is answered from here and NEVER executed again.
        self._completed = {}

    # ----- registration ------------------------------------------------- #
    def register_agent(self, manifest: dict) -> None:
        self._agents[manifest["metadata"]["id"]] = manifest
        self.budgets.register_from_manifest(manifest)

    def register_tool(self, tool_id: str, handler) -> None:
        """Register a connector. A connector that accepts `idempotency_key` receives the
        gateway's key on every call (mandatory for real connectors — see
        infra/golden-pilot/CONNECTOR-PILOT.md); one that does not is still protected by
        the gateway-level de-duplication in call()."""
        self._tools[tool_id] = (handler, _accepts_idempotency_key(handler))

    @staticmethod
    def idempotency_key(agent_id: str, tool_id: str, arguments, approval_id: str, request_id: str) -> str:
        """One key per authorized action: a consequential call is keyed by its single-use
        approval (so a retry after INDETERMINATE can never execute twice), any other
        call by its request id."""
        material = "|".join([agent_id, tool_id, arguments_hash(arguments), approval_id or request_id])
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]

    # ----- the brokered call -------------------------------------------- #
    def call(self, tc: ToolCall) -> GatewayResult:
        request_id = "req_" + secrets.token_hex(6)

        # --- KILL SWITCH: containment precedes evaluation ---------------- #
        # An engaged switch denies EVERYTHING — before masking, policy,
        # budgets, or approvals. Nothing outranks containment. See
        # platform_core/kill_switch.py and docs/ops/KILL-SWITCH.md.
        if self.kill_switch is not None and getattr(self.kill_switch, "engaged", False):
            reason = getattr(self.kill_switch, "reason", "") or "engaged"
            rec = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision="DENY",
                decision_reason=f"kill_switch_engaged: {reason}",
            )
            return GatewayResult(
                Effect.DENY, f"kill_switch_engaged: {reason}", audit_record=rec
            )

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

        # --- outbox de-duplication: a completed key never runs twice ---- #
        # Checked BEFORE policy / budget / approval. A key that already reached
        # COMPLETED is a replay - after an INDETERMINATE answer or a hostile
        # re-submission alike - and is DENIED without touching the connector.
        # Single-use means single response too: the recorded output is not
        # re-served; the INTENT/COMPLETED rows (same key) are the reconciliation
        # record. `already_completed` tells a reconciling caller not to retry.
        idem_key = self.idempotency_key(
            tc.agent_id, tc.tool_id, tc.arguments, tc.approval_id, request_id)
        if idem_key in self._completed:
            reason = ("already_completed: single-use approval already consumed and the action "
                      "executed once; replay refused, not re-executed")
            try:
                rec = self.audit.append(
                    request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                    tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                    policy_decision="DENY", decision_reason=reason,
                    input_hash=_hash(tc.arguments), approval_id=tc.approval_id,
                    masked_fields=masked_fields, idempotency_key=idem_key,
                )
            except Exception:  # noqa: BLE001 - a refusal needs no new side effect
                rec = None
            return GatewayResult(
                Effect.DENY, reason, audit_record=rec, masked_payload=masked_payload,
                idempotency_key=idem_key, already_completed=True,
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

        # (The bound single-use approval is consumed AFTER the AUTHORIZED-INTENT
        # record is durable and only for a registered connector - see below.)

        # --- default-deny: a tool with no registered handler cannot run - #
        # The gateway is fail-closed: policy may ALLOW, but if nothing is
        # actually wired to service the call we DENY rather than fabricate
        # a success. This closes the offline fail-open where an unregistered
        # tool returned {"ok": True}.
        registered = self._tools.get(tc.tool_id)
        if registered is None:
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
        handler, accepts_key = registered
        consequential = set(manifest.get("grants", {}).get("consequential", []))
        is_consequential = tc.tool_id in consequential

        # --- 1. AUTHORIZED-INTENT, durable BEFORE any consume / execute -- #
        # If this write fails nothing has happened yet, so DENY is truthful and
        # a retry is safe: no approval consumed, no connector called.
        try:
            intent = self.audit.append(
                request_id=request_id, user=tc.user, agent_id=tc.agent_id,
                tool_id=tc.tool_id, purpose=tc.purpose, data_class=tc.data_classes,
                policy_decision="INTENT",
                decision_reason=f"authorized_intent: {decision.reason}",
                model_profile=tc.model_profile, prompt_version=tc.prompt_version,
                retrieved_source_ids=tc.retrieved_source_ids,
                input_hash=_hash(tc.arguments), approval_id=tc.approval_id,
                masked_fields=masked_fields, grounded=tc.grounded,
                idempotency_key=idem_key,
            )
        except Exception as exc:  # noqa: BLE001 - intent must be durable first
            return GatewayResult(
                Effect.DENY, f"audit_fail_closed: intent not durable, nothing executed: {exc}",
                masked_payload=masked_payload, idempotency_key=idem_key,
            )

        # --- 2. consequential: consume the bound, single-use approval --- #
        if is_consequential:
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
                    idempotency_key=idem_key,
                )
                return GatewayResult(
                    Effect.DENY, f"approval_consume_failed: {exc}",
                    audit_record=rec, intent_record=intent, idempotency_key=idem_key,
                )

        # --- mint a scoped, per-call token (simulated OBO/STS) ---------- #
        scoped_token = self._mint_scoped_token(tc)

        # --- 3. execute the connector with the idempotency key ---------- #
        try:
            if accepts_key:
                output = handler(tc.arguments, idempotency_key=idem_key)
            else:
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

        # --- 4. COMPLETED / FAILED record ------------------------------- #
        # The side effect has ALREADY happened. If this write fails the truthful
        # answer is INDETERMINATE (reconciliation required from the INTENT row),
        # never DENY - a DENY here would invite a retry and a duplicate action.
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
                idempotency_key=idem_key,
            )
        except Exception as exc:  # noqa: BLE001 - completion not durable
            if exec_error is None:
                # Recorded in the outbox so a retry with the same key is answered
                # from here and never executed again.
                self._completed[idem_key] = True
            return GatewayResult(
                Effect.INDETERMINATE,
                f"reconciliation_required: side effect executed, completion record not durable: {exc}",
                output=output, intent_record=intent, scoped_token=scoped_token,
                masked_payload=masked_payload, idempotency_key=idem_key,
            )

        if exec_error:
            return GatewayResult(
                Effect.DENY, f"tool_exec_error: {exec_error}",
                audit_record=rec, intent_record=intent,
                masked_payload=masked_payload, idempotency_key=idem_key,
            )

        self._completed[idem_key] = True
        return GatewayResult(
            Effect.ALLOW, decision.reason, output=output,
            audit_record=rec, intent_record=intent, scoped_token=scoped_token,
            masked_payload=masked_payload, idempotency_key=idem_key,
        )

    def _mint_scoped_token(self, tc: ToolCall) -> str:
        """Simulate an AgentCore Identity OBO / STS scoped, per-call token.

        Never a long-lived credential: bound to user+agent+tool+scope+nonce and
        short-lived. Returned to the caller for the single downstream call only.
        """
        nonce = secrets.token_hex(6)
        material = f"{tc.user}|{tc.agent_id}|{tc.tool_id}|{tc.scope}|{int(time.time())}|{nonce}"
        return "scoped_" + hashlib.sha256(material.encode()).hexdigest()[:24]
