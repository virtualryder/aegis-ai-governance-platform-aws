"""budget_manager_ddb — concurrency-safe token-budget RESERVATION.

The offline token_budget.BudgetMeter does preflight() then commit() as two
steps, which can OVERSELL under concurrency (two callers both preflight at 90%
of a cap, both proceed, both commit -> 180%). Production needs an ATOMIC
reserve: a single conditional write that only succeeds if the new running total
stays within the cap.

Two implementations with identical semantics:

  (a) DynamoDBBudget.reserve(table, budget_key, tokens, cap)
        one conditional UpdateItem:
            SET used = if_not_exists(used, :z) + :n
            ConditionExpression: attribute_not_exists(used)
                                 OR used <= :cap - :n
        Over-budget => ConditionalCheckFailedException => denied. Concurrent
        reservations cannot oversell because DynamoDB serializes the conditional
        update per item.

  (b) InMemoryBudget — a pure-Python analog with the same atomic check for
      offline tests (no boto3, no AWS).

reserve(...) returns a ReserveResult(allowed, used_after, ...). Fail closed:
any error => denied.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class ReserveResult:
    allowed: bool
    reason: str
    used_before: int
    requested: int
    used_after: int
    cap: int

    @property
    def remaining(self) -> int:
        return max(self.cap - self.used_after, 0)


def _validate(tokens: int, cap: int) -> None:
    if tokens < 0:
        raise ValueError("tokens must be >= 0")
    if cap < 0:
        raise ValueError("cap must be >= 0")


# --------------------------------------------------------------------------- #
# (b) Pure-Python in-memory analog (offline tests)
# --------------------------------------------------------------------------- #
class InMemoryBudget:
    """Atomic in-memory reservation with the same semantics as the DDB impl.

    A lock makes the read-check-write atomic, mirroring DynamoDB's per-item
    serialization of a conditional UpdateItem.
    """

    def __init__(self):
        self._used: dict[str, int] = {}
        self._lock = threading.Lock()

    def used(self, budget_key: str) -> int:
        with self._lock:
            return self._used.get(budget_key, 0)

    def reserve(
        self, budget_key: str, tokens: int, cap: int
    ) -> ReserveResult:
        """Atomically reserve `tokens` if the new total stays <= cap.

        Returns ReserveResult(allowed=False) without mutating state when the
        reservation would exceed the cap (the analog of a
        ConditionalCheckFailedException => denied). Fail closed on any error.
        """
        try:
            _validate(tokens, cap)
        except Exception as exc:  # noqa: BLE001 - fail closed
            return ReserveResult(False, f"invalid: {exc}", 0, tokens, 0, cap)

        with self._lock:
            before = self._used.get(budget_key, 0)
            after = before + tokens
            if after > cap:
                return ReserveResult(
                    allowed=False,
                    reason=(
                        f"budget_exceeded: reservation of {tokens} on used "
                        f"{before} would exceed cap {cap}"
                    ),
                    used_before=before,
                    requested=tokens,
                    used_after=before,  # unchanged: reservation refused
                    cap=cap,
                )
            self._used[budget_key] = after
            return ReserveResult(
                allowed=True,
                reason="reserved",
                used_before=before,
                requested=tokens,
                used_after=after,
                cap=cap,
            )


# --------------------------------------------------------------------------- #
# (a) DynamoDB implementation (production; single conditional UpdateItem)
# --------------------------------------------------------------------------- #
class DynamoDBBudget:
    """Concurrency-safe reservation via a single conditional DynamoDB UpdateItem.

    The table is keyed by a single string partition key (default 'budget_key').
    A reservation is one UpdateItem that adds :n to `used` only if the resulting
    total stays within the cap; DynamoDB serializes concurrent conditional
    updates per item, so two reservations can never oversell.
    """

    def __init__(self, dynamodb_client=None, key_name: str = "budget_key"):
        self._client = dynamodb_client
        self.key_name = key_name

    def _client_or_default(self):
        if self._client is not None:
            return self._client
        import boto3  # pragma: no cover - real AWS

        return boto3.client("dynamodb")

    def reserve(
        self, table: str, budget_key: str, tokens: int, cap: int
    ) -> ReserveResult:
        """Reserve `tokens` against `budget_key` in `table`, capped at `cap`.

        Emits a single conditional UpdateItem:
            SET used = if_not_exists(used, :z) + :n
            ConditionExpression:
                attribute_not_exists(used) OR used <= :cap_minus_n
        Over-budget => ConditionalCheckFailedException => denied. Fail closed on
        any other error.
        """
        try:
            _validate(tokens, cap)
        except Exception as exc:  # noqa: BLE001 - fail closed
            return ReserveResult(False, f"invalid: {exc}", 0, tokens, 0, cap)

        client = self._client_or_default()
        try:
            resp = client.update_item(
                TableName=table,
                Key={self.key_name: {"S": budget_key}},
                UpdateExpression="SET used = if_not_exists(used, :z) + :n",
                ConditionExpression=(
                    "attribute_not_exists(used) OR used <= :cap_minus_n"
                ),
                ExpressionAttributeValues={
                    ":z": {"N": "0"},
                    ":n": {"N": str(tokens)},
                    ":cap_minus_n": {"N": str(cap - tokens)},
                },
                ReturnValues="UPDATED_NEW",
            )
            used_after = int(resp["Attributes"]["used"]["N"])
            return ReserveResult(
                allowed=True,
                reason="reserved",
                used_before=used_after - tokens,
                requested=tokens,
                used_after=used_after,
                cap=cap,
            )
        except Exception as exc:  # noqa: BLE001 - includes ConditionalCheckFailed
            name = type(exc).__name__
            # boto3 surfaces the condition failure as a ClientError whose
            # error code is 'ConditionalCheckFailedException'.
            is_cond = "ConditionalCheckFailed" in name
            resp = getattr(exc, "response", None)
            if isinstance(resp, dict):
                code = resp.get("Error", {}).get("Code", "")
                is_cond = is_cond or code == "ConditionalCheckFailedException"
            reason = (
                f"budget_exceeded: reservation of {tokens} would exceed cap {cap}"
                if is_cond
                else f"reserve_error_fail_closed: {exc}"
            )
            return ReserveResult(False, reason, 0, tokens, 0, cap)
