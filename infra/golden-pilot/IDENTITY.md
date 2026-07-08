# Real Identity (task #21) — hardened Cognito + MFA + verified JWT -> Cedar

> Deployed and live-tested on AWS account `<VALIDATION-ACCOUNT-ID>` (real account ID redacted;
> evidence available on request) (us-east-1) on 2026-06-30, then torn down.
> This closes the "MFA off / no app client / no verified role" gap and links identity to the Cedar
> authorization proven in [`GOLDEN-PILOT.md`](GOLDEN-PILOT.md).

## What is real now

- **`cognito-identity.yaml`** — Cognito user pool with **software-token MFA REQUIRED**,
  **AdvancedSecurityMode: ENFORCED**, a strong password policy, an app client with explicit auth
  flows + short-lived tokens (60-min ID/access), and two role groups
  (`service-desk-operator`, `service-desk-supervisor`). Verified live: `MfaConfiguration=ON`,
  `AdvancedSecurityMode=ENFORCED`.
- **Real MFA login end to end** (no shortcuts): admin auth returned an `MFA_SETUP` challenge (proving
  enforcement) -> `associate-software-token` -> TOTP computed from the secret -> `verify-software-token`
  = SUCCESS -> fresh login returned `SOFTWARE_TOKEN_MFA` -> responded with a live TOTP -> received a
  real signed **ID token** carrying `cognito:groups=["service-desk-operator"]`.
- **`verify_jwt.py`** — cryptographic verification the gateway must do: RS256 signature against the
  pool **JWKS**, plus `iss`/`aud`/`exp`/`token_use` and an **alg-confusion guard**; returns the
  verified group. Live results:
  | Case | Result |
  |---|---|
  | Real token, correct iss/aud | **VERIFY OK**, groups=`['service-desk-operator']` |
  | Tampered signature | **rejected** (signature verification failed) |
  | Wrong audience | **rejected** (aud mismatch) |
- **Identity -> authorization loop** (`role_map.json`): the verified `service-desk-operator` group
  maps to `userEntitlements=[kb.search, ticket.draft]`, fed into the Cedar context on Amazon Verified
  Permissions. Live decisions:
  | Request (as verified operator) | Decision |
  |---|---|
  | Read `kb.search` | **ALLOW** |
  | Consequential `ticket.issue` (supervisor-only) | **DENY** |

## Client-supplied roles are never trusted

The gateway derives entitlements only from the cryptographically verified `cognito:groups` claim via
`role_map.json`. A caller cannot self-assert a role.

## Not yet included (tracked in ../../docs/GAP-CLOSURE-BACKLOG.md)

External IdP federation (Entra/Okta) into Cognito, an API Gateway JWT authorizer wired in front of
the gateway Lambda, AgentCore Identity OBO token exchange for scoped downstream calls, token
revocation flows, break-glass, and confused-deputy/privilege-escalation test suite.
