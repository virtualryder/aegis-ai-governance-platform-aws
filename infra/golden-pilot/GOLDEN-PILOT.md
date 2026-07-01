# Golden Pilot (in progress) — real Cedar authorization + real Bedrock

> Task #20. This is the first end-to-end-real slice: **authorization enforced by Cedar on Amazon
> Verified Permissions** (the production analog of `platform_core/policy_engine.py`) and a **real
> Amazon Bedrock invocation**. Both were deployed and live-tested on AWS account 864217980669
> (us-east-1) on 2026-06-30, then torn down. Full record in [`../../DEPLOYED-AND-VALIDATED.md`](../../DEPLOYED-AND-VALIDATED.md).

## What is real now

- **`avp-cedar.yaml`** — CloudFormation for a STRICT-validated Verified Permissions **policy store**
  with a Cedar **schema** (Agent principal, Tool resource, `InvokeTool` action + context) and a
  default-deny **permit** policy implementing least-privilege as an *intersection* plus purpose
  limitation and a data-class boundary:

  ```cedar
  permit ( principal is Aegis::Agent, action == Aegis::Action::"InvokeTool", resource is Aegis::Tool )
  when {
    principal.grants.contains(resource.id) &&           // agent grant
    context.userEntitlements.contains(resource.id) &&   // AND user entitlement (intersection)
    resource.allowedPurposes.contains(context.purpose) &&
    context.userDataClasses.contains(resource.dataClass)
  };
  ```

- **`run_authz_tests.sh`** — deploys the store, runs three live `is-authorized` decisions, tears down.
  Live results (2026-06-30):
  | Case | Request | Decision |
  |---|---|---|
  | 1 | Legit read: agent-granted + user-entitled + right purpose + `public` | **ALLOW** |
  | 2 | Consequential `ticket.issue` not in agent grants (user entitled) | **DENY** |
  | 3 | `kb.search` tagged `phi`, user cleared only for `public` | **DENY** |

## Honest scope — what this pilot slice does NOT yet include

Still required for a full "customer-deployable golden pilot" (tracked in
[`../../docs/GAP-CLOSURE-BACKLOG.md`](../../docs/GAP-CLOSURE-BACKLOG.md), tasks #20–#25): real IdP
federation + MFA, AgentCore Gateway wiring, an AgentCore-Policy (not just AVP) enforcement point, a
real KB + retrieval, a real sandbox connector (e.g. ServiceNow), the reviewer UI for the human gate,
token-budget enforcement at runtime, an operator dashboard, and an evidence report.

## Gotcha for operators

Pass the `is-authorized` request as explicit `--principal/--action/--resource/--context/--entities`
`file://` flags. Some CLI proxies silently drop `--cli-input-json`, which yields a false DENY (no
determining policy, no errors) because the request body never reaches AVP.
