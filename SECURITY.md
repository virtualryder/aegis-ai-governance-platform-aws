# Security Policy

Aegis is a governance control plane whose entire reason for existing is to keep
high-sensitivity workloads (CJI, FTI, PHI, FERPA/EDU, PII) inside enforceable
boundaries. We take the security of the platform, and of anyone evaluating it,
seriously.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report suspected vulnerabilities privately so we can triage and remediate before
details are public:

Report vulnerabilities privately via GitHub Security Advisories: use the *Security*
tab → *Report a vulnerability* on this repository. Please do not open public issues
for security reports.

Please include:

- a description of the issue and the component affected
  (e.g. `platform_core/gateway.py`, `policy_engine`, a CloudFormation template);
- steps to reproduce or a proof of concept;
- the impact you believe it has (bypass of a mandatory control, data leak
  across a data-class boundary, fail-open behavior, etc.);
- any suggested remediation.

We aim to acknowledge a report within **3 business days** and to provide a
remediation plan or mitigation within **30 days**, depending on severity. We
will credit reporters who wish to be acknowledged once a fix is released.

## Supported Versions

Aegis is a **reference platform under active development** and has not yet cut a
stable, semantically versioned release. Until a `1.0.0` tag exists, only the
`main` branch (the latest `Unreleased` state — see `CHANGELOG.md`) receives
security fixes. Forks and pinned snapshots are the responsibility of the
operator who deployed them.

| Version        | Supported          |
| -------------- | ------------------ |
| `main` (latest)| :white_check_mark: |
| older commits  | :x:                |

## Security Design Principle: Fail Closed

Every **mandatory control in Aegis fails closed**. This is a design invariant,
not a best-effort behavior:

- The authorization gateway is **deny-by-default**. A call is allowed only if
  *every* clause of the policy predicate is affirmatively satisfied
  (authenticated user, agent grant, user entitlement, purpose, data-class
  boundary, consent, residency, budget, and human-gate approval when required).
- If a requested tool has **no registered handler**, the call is **denied**
  (`tool-not-registered`) rather than returning a fabricated success.
- If **boundary masking** cannot run, the call is **denied**
  (`masking_fail_closed`) so sensitive data can never leak unmasked into a
  prompt, log, or audit record.
- If the **policy engine cannot evaluate**, the call is **denied**
  (`policy_eval_fail_closed`).
- If the **append-only audit write fails** on a consequential or sensitive
  call, the call is **denied** (`audit_fail_closed`): an unauditable side
  effect is not permitted.

If you find any code path where a **mandatory** control can fail *open* — that
is, allow an action that should have been denied — treat it as a security
vulnerability and report it via the private channel above.

## Assurance Status — Please Read

Aegis is a **reference implementation intended for evaluation, demonstration,
and architecture review**. It is **not** a production-authorized system:

- It has **not received an Authority to Operate (ATO)** under FedRAMP, DoD IL,
  StateRAMP, or any agency authorization process.
- It has **not undergone an independent penetration test** or third-party
  security assessment.
- The offline `platform_core/` modules are an **offline analog** of the
  production AWS control plane (AgentCore Gateway/Identity/Policy, Amazon
  Verified Permissions, Comprehend/Macie, S3 Object Lock, etc.) and use
  simulated tokens and deterministic regex masking, not the production services.

Before any production or authority-boundary use, complete the readiness and
accountability work tracked in
[`docs/10-PRODUCTION-READINESS-RACI.md`](docs/10-PRODUCTION-READINESS-RACI.md),
including independent assessment, penetration testing, and the ATO process
appropriate to the target environment and data classes.
