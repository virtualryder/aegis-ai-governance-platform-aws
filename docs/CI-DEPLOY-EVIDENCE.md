# Reproducible CI deploy-evidence

*Replaces single-operator, hand-run deploy attestation with a hands-off pipeline that deploys → tests
the live controls → captures machine evidence → tears down, on demand and weekly.*

## What it proves (every run)

The workflow [`.github/workflows/golden-pilot-deploy-evidence.yml`](../.github/workflows/golden-pilot-deploy-evidence.yml)
deploys the B3 MCP-gateway golden path (the deployed authorizer **is** the reviewed `platform_core`
engine, shipped as a Lambda layer), then runs [`infra/golden-pilot/ci/collect_evidence.py`](../infra/golden-pilot/ci/collect_evidence.py),
which fails the job unless **all** of these hold on the *live* stack:

| Control | How it's proven in-account | 
|---|---|
| Deny-by-default authorization | reviewed engine returns **ALLOW** (`kb.search_policy`), **DENY** (`db.drop` — deny-by-default), **APPROVAL_REQUIRED** (`ticket.submit` — human gate) over HTTPS; deny strings are `platform_core.policy_engine`'s own messages |
| Fail-closed masking | `ticket.create_draft` with an SSN + email returns them redacted (`[SSN-REDACTED]`, `[EMAIL-REDACTED]`) in the response **and** the audit row |
| Append-only audit (IAM-enforced) | `iam:SimulatePrincipalPolicy` on the deployed Lambda role: `dynamodb:PutItem` = **allowed**, `UpdateItem`/`DeleteItem` = **explicitDeny** |

Evidence is written to `evidence-ci/deploy-evidence.json` + `evidence-ci/SUMMARY.md`, uploaded as a run
artifact, and account IDs are redacted (`<ACCOUNT>`) before write. The stack is always torn down, even on
failure. A live sample from an actual run is checked in at
[`infra/golden-pilot/evidence-ci/`](../infra/golden-pilot/evidence-ci/).

## One-time setup (OIDC — no long-lived keys in CI)

1. Deploy the OIDC deploy-role once (raw CloudFormation), scoped to this repo:
   ```bash
   aws cloudformation deploy \
     --stack-name aegis-golden-pilot-ci-role \
     --template-file infra/golden-pilot/ci/oidc-deploy-role.yaml \
     --capabilities CAPABILITY_NAMED_IAM \
     --parameter-overrides GitHubOrg=<org> GitHubRepo=aegis-ai-governance-platform-aws GitHubRef=refs/heads/main \
     --region us-east-1
   # If the GitHub OIDC provider already exists in the account, add: CreateOIDCProvider=false
   ```
2. Read the role ARN and add it as a repo secret named **`AWS_DEPLOY_ROLE_ARN`**:
   ```bash
   aws cloudformation describe-stacks --stack-name aegis-golden-pilot-ci-role \
     --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue" --output text
   ```
3. Run the workflow from the Actions tab (`workflow_dispatch`), or wait for the weekly schedule.

Until the secret exists the workflow is inert (it never triggers on push), so adding these files changes
nothing about your normal CI.

## Security notes (honest)

- The deploy role can create IAM roles (the stack ships its own append-only Lambda role), so it is
  privileged by nature. It is mitigated three ways: OIDC short-lived tokens (no stored keys), the trust
  policy is scoped to `repo:<org>/<repo>:ref:<branch>`, and `MaxSessionDuration` is 1 hour. Tighten
  `GitHubRef` to a single branch for production.
- The golden path itself is cheap (no VPC): API Gateway HTTP API + one Lambda + a PAY_PER_REQUEST table +
  a Cognito pool, up and down in ~3 minutes per run.

## Status

**Verified live (2026-07-12):** the collector ran against a real `aegis-mcp-gateway-ci` deploy in
`us-east-1` and reported `control_checks.passed: true` (append-only IAM = `explicitDeny` on Update/Delete,
masking fired, all four decisions correct), then the stack was torn down with zero residual. The GitHub
Actions wiring runs these exact steps under an OIDC role — the only thing left to a maintainer is applying
the role template and adding the secret.
