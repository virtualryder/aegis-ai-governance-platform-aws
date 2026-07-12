# CI deploy-evidence - B3 MCP gateway (reviewed engine)

Stack `aegis-mcp-gateway-ci` in `us-east-1` (account redacted). Machine-captured; deploy -> verify -> teardown.

| Control | Evidence | Result |
|---|---|---|
| Deny-by-default authz | reviewed engine returned ALLOW / DENY / APPROVAL over HTTPS | PASS |
| Fail-closed masking | SSN/email redacted in response + audit row | PASS |
| Append-only audit (IAM) | PutItem allowed; Update/DeleteItem denied by IAM simulation | PASS |

```json
{
  "dynamodb:PutItem": "allowed",
  "dynamodb:UpdateItem": "explicitDeny",
  "dynamodb:DeleteItem": "explicitDeny"
}
```

> Sample captured from a real run on 2026-07-12; account IDs redacted by the collector. This is a
> checked-in reference — every pipeline run regenerates its own copy and uploads it as a run artifact.
