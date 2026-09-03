# CI deploy-evidence — B3 MCP gateway (reviewed engine)

Stack `aegis-mcp-gateway-ci-33799042751` in `us-east-1` (account redacted). Machine-captured; deploy → verify → teardown.

| Control | Evidence | Result |
|---|---|---|
| Deny-by-default authz | reviewed engine returned ALLOW / DENY / APPROVAL over HTTPS | PASS |
| Zero tools without an entitlement claim | no-claim caller: tools/list 403, tools/call 403; ALLOW_DEFAULT_ENTITLEMENTS=0 | PASS |
| Approval bound to the full action at consumption | modified args / wrong tool / replay refused; exact action allowed once | not exercised |
| Fail-closed masking | SSN/email redacted in response + audit row | PASS |
| Append-only audit (IAM) | PutItem allowed; Update/DeleteItem denied by IAM simulation | PASS |

```json
{
  "dynamodb:PutItem": "allowed",
  "dynamodb:UpdateItem": "explicitDeny",
  "dynamodb:DeleteItem": "explicitDeny"
}
```
