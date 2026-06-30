"""Aegis platform_core — the governance control plane, offline test analog.

A small, readable, pure-Python implementation of the Aegis MCP authorization
gateway and its supporting controls. NO third-party dependencies — standard
library only. This is the "offline test analog" referenced in
docs/02-REFERENCE-ARCHITECTURE.md §3: production enforcement runs on AgentCore
Policy / Amazon Verified Permissions (Cedar); this package lets a salesperson
run the exact governance behavior live on a laptop with no AWS and no network.

Modules:
    manifest_loader  -- stdlib-only YAML/JSON manifest loader + schema check
    policy_engine    -- the deny-by-default ALLOW-iff predicate (arch §3)
    masker           -- fail-closed deterministic PII/PHI/card/etc. masking
    token_budget     -- per-agent/department token meter + hard/soft caps
    approval_ledger  -- bound, single-use, separation-of-duties approvals
    audit_ledger     -- append-only, immutable audit + WORM evidence export
    chargeback       -- per-department usage aggregation -> chargeback CSV
    model_gateway    -- offline deterministic model w/ grounding + schema check
    gateway          -- the MCP authorization gateway tying it all together
"""

__all__ = [
    "manifest_loader",
    "policy_engine",
    "masker",
    "token_budget",
    "approval_ledger",
    "audit_ledger",
    "chargeback",
    "model_gateway",
    "gateway",
]

__version__ = "1.0.0"
