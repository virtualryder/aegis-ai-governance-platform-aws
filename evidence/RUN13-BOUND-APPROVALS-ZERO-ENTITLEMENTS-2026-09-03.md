# Run 13 (2026-09-03) — deployed authorizer: zero tools without an entitlement claim; approvals bound to the full action at consumption

Stacks `aegis-mcp-gateway-r13` (portable reference gateway: API Gateway HTTP API + Cognito JWT authorizer +
the reviewed `platform_core` engine as a Lambda layer, `LedgerTableName=aegis-approval-ledger-test`) and
`aegis-reviewer-r13` (the real reviewer service: Step Functions `waitForTaskToken` human gate, verified-supervisor
role, separation of duties, bound single-use approval ledger), `us-east-1`, account redacted. Collector:
`infra/golden-pilot/ci/collect_evidence.py --reviewer-stack aegis-reviewer-r13` → **PASS** (`control_checks.passed: true`).
Both stacks torn down after the run. Closes Copilot review items 2 and 3 (tasks 130, 131).

## What changed (and why a live run was needed)

| Finding | Before | After (this run proves it) |
|---|---|---|
| COPILOT-3: a token with no `custom:tools` / `scope` claim was granted the whole pilot tool set (`return ents or _DEFAULT_ENTITLEMENTS`) | any authenticated Cognito user could call every tool | entitlements come only from the verified claim; no / empty / malformed claim ⇒ **zero tools**: `tools/list` → HTTP 403, `tools/call` → HTTP 403, audited. The demo default is an explicit template parameter `DemoDefaultEntitlements` (default `"0"`, env `ALLOW_DEFAULT_ENTITLEMENTS`), logged on every use, asserted OFF by `demo/clean_account_acceptance.py` step 18 and by the collector on the deployed function |
| COPILOT-2: `_consume_approval` conditioned only on exists / unconsumed / unexpired / requester — a valid `approval_id` could be replayed with different arguments or against another tool | the reviewer computed `approval_id = sha256(request|agent|tool|args_hash|purpose|requester)` but did not store the binding; the gateway could not check it | the reviewer stores `agent_id, tool_id, args_hash, purpose` on the ledger row; the gateway recomputes the args hash from the actual call (canonical `platform_core.approval_ledger.arguments_hash`, minus `approval_id`) and adds `agent_id = :agent AND tool_id = :tool AND args_hash = :args AND purpose = :purpose` to the **same atomic `ConditionExpression`** as exists / unconsumed / unexpired / requester. Nothing is trusted from the caller |

## Live results over HTTPS

Entitled caller (`custom:tools = "kb.search_policy ticket.create_draft ticket.submit"`):

| Case | Result |
|---|---|
| `kb.search_policy` | ALLOW |
| `ticket.create_draft` with an SSN + email | ALLOW — masked in the response and the audit row |
| `db.drop` (no grant) | DENY (deny: agent 'aegis-mcp-gateway' has no grant for tool 'db.drop') |
| `ticket.submit` (consequential, no approval) | DENY (deny: tool 'ticket.submit' is a consequential action withheld from the agent; a valid human-gate approval is r) |

Caller with **no entitlement claim** (`ci-noclaim`, same pool, valid JWT):

| Case | HTTP | Result |
|---|---|---|
| `tools/list` | 403 | `deny: no entitlement claim on the token - zero tools` |
| `tools/call kb.search_policy` | 403 | `deny: no entitlement claim on the token - zero tools` |

Deployed function `ALLOW_DEFAULT_ENTITLEMENTS` = `0` (demo default OFF).

**Bound approvals** — two approvals issued through the real reviewer service (state machine started with the
canonical `argsHash`, approved by `supervisor-bob` ≠ requester): one for `ticket.submit {"ticket_id": "T-R13"}`,
one for `ticket.create_draft` with the same arguments. Then, as the requester:

| Case | Call | Result |
|---|---|---|
| MODIFIED_ARGS | `ticket.submit {"ticket_id": "T-OTHER"}` + the `ticket.submit` approval | DENY (deny: approval not consumable: unknown, expired, already used, or not bound to this caller + agent + tool + ar) |
| WRONG_TOOL | `ticket.submit {"ticket_id": "T-R13"}` + the `ticket.create_draft` approval | DENY (deny: approval not consumable: unknown, expired, already used, or not bound to this caller + agent + tool + ar) |
| EXACT | `ticket.submit {"ticket_id": "T-R13"}` + its own approval | ALLOW — consumed (`consumed_at`, `consumed_by = requester sub`) |
| REPLAY | the same call again | DENY (deny: approval not consumable: unknown, expired, already used, or not bound to this caller + agent + tool + ar) |

Ledger after the run: the `ticket.submit` row consumed exactly once (`consumed_by` = the requester's Cognito `sub`);
the `ticket.create_draft` row untouched — the wrong-tool attempt did not consume it either.

## Also on this run

- IAM simulation of the deployed Lambda role: `dynamodb:PutItem` allowed, `UpdateItem` / `DeleteItem` **explicitDeny** on the audit table (append-only enforced by IAM).
- Audit scan: the SSN / email never reached the table unmasked.
- Every decision above is a row in `aegis-mcp-audit-test` (`allow` / `deny` + the engine's own reason string).

## Offline counterparts (run in CI on every push)

`infra/golden-pilot/verify_authorizer_engine.py` loads the handler exactly as deployed (from the staged layer, boto3
stubbed with a ledger that evaluates the same ConditionExpression) and asserts: no / malformed claim ⇒ zero tools +
403; `tools/list` = entitlement ∩ grants; modified args / wrong tool / wrong purpose / another requester ⇒ DENY without
consuming; exact ⇒ ALLOW once; replay ⇒ DENY. `demo/clean_account_acceptance.py` step 18 asserts the demo default is
OFF in the template, the handler and every deploy script / workflow.

Machine evidence: `RUN13-BOUND-APPROVALS-ZERO-ENTITLEMENTS-2026-09-03.json` (account ids and approval ids redacted).
