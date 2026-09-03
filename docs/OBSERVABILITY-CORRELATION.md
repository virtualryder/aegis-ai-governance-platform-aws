# Phase 110 — Full transparency: every API call, the model's reasoning, and the WORM evidence, joined by session / trace id, tagged per tenant

Status: **design 2026-09-02 → implemented in governed-core 1.7.0 + benefits (see the evidence link at the end)**.
Grounded in the AWS documentation cited inline; nothing here relies on undocumented behaviour.

## The question this answers

For any case, in any tenant: *show me every API call that touched it, what the model saw and reasoned,
which tool was called with what (masked) input, what every governed control decided, and prove that the
WORM record for each step is the same event.* One key set joins all of it.

## Where each signal already lives (AWS-managed) and its native identifiers

| Signal | Emitted by | Lands in | Native identifiers |
|---|---|---|---|
| **Agent reasoning + tool-call spans** (`invoke_agent`, event-loop cycles, model invoke, `execute_tool`) with `gen_ai.*` attributes and message events | AgentCore **Runtime** via ADOT (`opentelemetry-instrument`, `aws-opentelemetry-distro`) + the Strands tracer (`scope.name = strands.telemetry.tracer`) | `/aws/bedrock-agentcore/runtimes/<agent_id>-<endpoint>` (streams `spans`, `runtime-logs`) and the account-wide `aws/spans` (Transaction Search) | `traceId`, `spanId`, `attributes.session.id` (**mandatory** — set from the `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` header; ADOT propagates it downstream), `gen_ai.request.model`, `gen_ai.usage.*`, `gen_ai.tool.name` / `gen_ai.tool.call.id` |
| **Every gateway request** (initialize, tools/list, tools/call → target) + Cedar decisions | AgentCore **Gateway** vended logs (log type `APPLICATION_LOGS`, optional `TRACES`) | `/aws/vendedlogs/bedrock-agentcore/gateway/APPLICATION_LOGS/<gateway-id>` (CloudWatch Logs delivery) | request id, `mcp-session-id`, `traceparent` / `X-Amzn-Trace-Id` (supported request headers) |
| **Every model invocation** (`Converse`/`ConverseStream`/`InvokeModel*`) with the **exact request/response body** (≤100 KB inline, larger to S3) | **Bedrock model invocation logging** (account+region level, `PutModelInvocationLoggingConfiguration`) | CloudWatch log group + S3 bucket of the deployment's choosing | `requestId`, `modelId`, `identity.arn`, **`requestMetadata`** (≤16 caller-supplied key/values, filterable) |
| **Every governed tool execution** (mask, assess, draft, audit, sign-off …) | Lambda targets (our code) | `/aws/lambda/<prefix>-<tool>` | `aws_request_id`, `_X_AMZN_TRACE_ID` |
| **The deterministic workflow** | Step Functions (X-Ray tracing on, execution data off) | execution history; `/aws/states/<prefix>…` | execution ARN, `traceHeader` |
| **The immutable record** | governed-core `evidence.record_event` | per-tenant hash-chained ledger + Object-Lock vault | `audit_id`, `case_id`, `seq`, `chain_hash` |

## The join keys (what phase 110 adds)

Nothing above is joinable *across* rows by default: the WORM record does not know the trace, the model log
does not know the tenant or case, the tool Lambda does not know the agent session. Phase 110 threads one
**correlation set** through every hop and stamps it on every row:

```
tenant           derived (never requested) — the signed tenant pair of phase 107
session_id       AgentCore Runtime session (X-Amzn-Bedrock-AgentCore-Runtime-Session-Id → span attr session.id)
trace_id/span_id W3C traceparent of the calling span (ADOT injects it on the runtime's outbound MCP HTTP call)
mcp_session_id   the gateway's MCP session
execution_arn    the Step Functions execution (workflow hop) — $$.Execution.Id
request_id       the Lambda invocation (aws_request_id) / the Bedrock requestId (model hop)
case_id          the business key
```

How each hop obtains it (all derived at a trusted boundary, none typed by the model or caller):

1. **Runtime → model.** `agent.py` binds `session.id`, `tenant`, `case_id`, `requester` as Strands
   `trace_attributes` (they appear on every span of the invocation) and as OTEL baggage, and injects the
   same keys as **`requestMetadata`** on every `Converse` call through a botocore event hook on the
   Bedrock client — so the model-invocation log row carries `tenant`/`session_id`/`case_id` and can be
   filtered per tenant without reading bodies. Join to the span: `requestId` ↔ the span's `aws.request_id`
   (botocore instrumentation) and the timestamps within the same `session.id`.
2. **Runtime → gateway → tool.** ADOT puts `traceparent` on the runtime's outbound HTTP; the gateway
   passes request headers to the **REQUEST interceptor** (`passRequestHeaders`), which — next to the
   signed tenant pair — injects **`__aegis_trace`** (`trace_id`, `span_id`, `session_id` from the `baggage`
   header, `mcp_session_id`) into the tool arguments. This is *observability* context, not authorization:
   the tenant stays the only signed, trusted field. The gateway's own log row carries the same request
   headers.
3. **Tool Lambda.** `telemetry.bind(event, context)` (governed-core 1.7.0) reads `__aegis_trace`, the
   Lambda `aws_request_id`, `_X_AMZN_TRACE_ID`, the bound tenant and (workflow hop) `__aegis_execution`
   into a request-scoped context; every handler emits **one structured JSON log line**
   (`aegis.call`) with the full key set, tool name, masked-argument digest and outcome — every API call
   the platform makes is therefore visible in CloudWatch with the same keys.
4. **WORM record.** `evidence.record_event` stamps a **`correlation`** block (the key set above) into the
   logical record *before* hashing, so the ledger row and its Object-Lock copy carry the join keys and
   are tamper-evident for them too (an altered trace id breaks the chain).
5. **Workflow hop.** Every Lambda payload carries `__aegis_execution.$ = $$.Execution.Id` (always
   available, no input dependency); the execution's X-Ray `traceHeader` links the Lambda traces.

## Per-tenant tagging

Every span (`trace_attributes.tenant`), every model log row (`requestMetadata.tenant`), every Lambda log
line and every WORM record carries `tenant`; per-tenant Logs Insights and per-tenant evidence exports
need no joins. The tenant is the *derived* one — a spoofed value cannot reach any of these rows because
each hop re-derives it from the signed pair or the verified token.

## "Masked before the model" — provable

The model-invocation log holds the exact Converse request body. Phase 110's correlation tool checks every
row for the case against the PII canary set (SSN/DOB/name/address from the synthetic case) and reports
`masked_before_model: true/false` per invocation — the transparency claim is measured, not asserted.

## The correlation tool

`benefits scripts/trace_case.py --env <env> --case-id <id> [--tenant <t>]` builds one timeline for a case:
WORM records (per-tenant ledger) → their `correlation` keys → Logs Insights over the runtime span/log
groups (`session.id`), the gateway `APPLICATION_LOGS`, the Lambda groups (`aegis.call` lines), Step
Functions history, and the model-invocation log group (`requestMetadata.case_id`), merged by time with
the join keys shown per row. Output: JSON + Markdown; it is the artefact an auditor is handed.

## Validation gate (phase 110 exit)

Offline: unit tests for the interceptor injection, `telemetry.bind`, the `correlation` block in the hashed
record, the `aegis.call` log line, the `requestMetadata` hook, and the timeline builder on captured
fixtures. Live: one runtime invocation per tenant; `trace_case.py` must show, for each, ≥1 `invoke_agent`
span with `session.id`+`tenant`, every tool call as gateway row + Lambda `aegis.call` line + WORM record
sharing `trace_id`/`session_id`, ≥1 model-invocation row with `requestMetadata.tenant`, and
`masked_before_model: true` for all of them; the other tenant's timeline must be empty for that case.

## Sources (AWS documentation)

- AgentCore observability configuration — log groups, `aws/spans`, Transaction Search, session header,
  ADOT env, supported headers (`traceparent`, `X-Amzn-Trace-Id`, `mcp-session-id`):
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
- Span/event schema and required `session.id`, Strands scope and `gen_ai.*` attributes:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/understanding-input-spans.html
- Bedrock model invocation logging — operations, fields, `requestMetadata`, 100 KB inline / S3 overflow:
  https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
- `Converse.requestMetadata` — ≤16 entries, key/value ≤256 chars:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
- Strands `trace_attributes` and emitted spans:
  https://strandsagents.com/docs/user-guide/observability-evaluation/traces/
