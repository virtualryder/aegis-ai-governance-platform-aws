# B3 â€” Live layer-backed authorizer deploy (evidence)

**Date:** 2026-07-12 Â· **Account:** 111122223333 Â· **Region:** us-east-1 Â·
**Stack:** `aegis-mcp-gateway-b3` (deployed â†’ live-tested â†’ torn down, zero residual).

This records the live clean-account run that closes the last B3 gap: the deployed MCP
authorizer is now the **reviewed `platform_core` engine**, delivered as a Lambda layer â€”
not the previous inline governance subset (deleted).

## What was deployed

`sam build` + `sam deploy` of `mcp-gateway.yaml` created, in one stack:

| Resource | Type | Note |
|---|---|---|
| `PlatformCoreLayer` | `AWS::Lambda::LayerVersion` | the reviewed `platform_core` engine (15 modules), pre-staged by `prepare_layer.sh` |
| `McpFunction` | `AWS::Lambda::Function` | `gateway-src/handler.py`, imports `platform_core.policy_engine` + `platform_core.masker` from the layer |
| `McpFunctionRole` | `AWS::IAM::Role` | append-only: `dynamodb:PutItem` Allow, `UpdateItem`/`DeleteItem` **Deny** |
| `AuditTable` | `AWS::DynamoDB::Table` | `aegis-mcp-audit-dev`, append-only audit sink |
| `HttpApi` + `JwtAuthorizer` | API Gateway HTTP API | `POST /mcp`, Cognito JWT authorizer |
| `UserPool` / `UserPoolClient` | Cognito | identity for the live call |

Endpoint: `https://hksawbo02f.execute-api.us-east-1.amazonaws.com/mcp`

## Live results (authenticated over HTTPS with a Cognito ID token)

Every decision below is the **reviewed engine's own output** â€” the deny/gate strings are
`platform_core.policy_engine`'s verbatim messages (the deleted inline subset used different
wording), which is the proof the deployed artifact *is* the reviewed engine.

| # | MCP `tools/call` | Decision | Evidence it came from the reviewed engine |
|---|---|---|---|
| 1 | `kb.search_policy` | **ALLOW** | 9-clause predicate satisfied (granted âˆ© entitled, purpose, data-class, budget) |
| 2 | `ticket.create_draft` (summary with SSN + email) | **ALLOW + masked** | reviewed `masker` redacted â†’ `Resident SSN [SSN-REDACTED] email [EMAIL-REDACTED] â€¦` in both the response and the audit row |
| 3 | `db.drop` | **DENY** | `deny: agent 'aegis-mcp-gateway' has no grant for tool 'db.drop'` â€” deny-by-default |
| 4 | `ticket.submit` (no approval) | **APPROVAL_REQUIRED** | `deny: tool 'ticket.submit' is a consequential action withheld from the agent; a valid human-gate approval is required` |

## Append-only audit (DynamoDB scan of `aegis-mcp-audit-dev`)

Five records written; the sensitive one is stored **masked** â€” the reviewed fail-closed masker
ran before the write:

```
tool                 decision  detail
*                    allow     tools/list
kb.search_policy     allow     {"query": "privacy policy"}
ticket.create_draft  allow     {"summary": "Resident SSN [SSN-REDACTED] email [EMAIL-REDACTED] card 4111 1111 1111 1111 needs help"}
db.drop              deny      agent 'aegis-mcp-gateway' has no grant for tool 'db.drop'
ticket.submit        deny      approval_required: tool 'ticket.submit' is a consequential action withheld from the agent; a valid human-gate approval is required
```

(The card number carries the `card` data class, which this tool does not declare â€” `public,pii` â€”
so it is correctly out of scope for masking on this path; SSN/email are `pii` and were masked.)

## Teardown

`sam delete --stack-name aegis-mcp-gateway-b3 --no-prompts` â†’
`describe-stacks` returns *"Stack ... does not exist"*. Zero residual resources (Cognito pool +
user, audit table, Lambda, layer, HTTP API all removed with the stack).

## Reproduce

```bash
cd infra/golden-pilot
./prepare_layer.sh          # stage the reviewed engine into layer/python/ (or: py -3.12 stage_layer.py on Windows)
sam build -t mcp-gateway.yaml
sam deploy -t .aws-sam/build/template.yaml --stack-name aegis-mcp-gateway-b3 \
  --region us-east-1 --capabilities CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset
# mint a Cognito ID token, POST MCP tools/call to the McpEndpoint, then:
sam delete --stack-name aegis-mcp-gateway-b3 --no-prompts
```
