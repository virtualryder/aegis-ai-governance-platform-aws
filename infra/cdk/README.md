# Governance Core — CDK Authoring App

**Position in the IaC canon (`../CANONICAL-IAC.md`):** CloudFormation remains the
canonical Aegis IaC language. This CDK app is the **authoring layer** for the
governance core — it *synthesizes to* CloudFormation, so the single-source-of-truth
rule is preserved while the whole portfolio converges on one authoring approach:
the four vertical agents already ship Python-CDK apps (identity / gateway / data /
compute stacks), and the platform core now matches them.

- **Parity:** resource-for-resource port of the live-validated
  `../cloudformation/governance-core.yaml` (KMS CMK + confused-deputy guards,
  append-only audit table + explicit IAM deny, TTL'd approval ledger, WORM
  evidence bucket, Bedrock Guardrail with PII/grounding/deny-topic, Cognito pool
  + operator group, least-privilege gateway role, gateway Lambda from the same
  `index.py`). Partition-aware via CDK tokens — same synth deploys to commercial
  and GovCloud.
- **Beyond parity (deliberate):** the platform **Kill Switch** SSM parameter
  (default disengaged) with read/engage IAM managed policies, wired into the
  gateway environment. See `../../docs/ops/KILL-SWITCH.md`.
- **Terraform status:** the parity module in `../terraform/` remains for
  Terraform-standardized adopters (P2, per canon) — it is no longer the
  forward-authoring path.

## Validate offline (no AWS, no CDK CLI)

```bash
pip install -r requirements.txt pytest
python3 -m pytest tests/ -q        # synthesizes in-process; 8 assertions
```

## Deploy

```bash
npm i -g aws-cdk
cdk synth                          # emits the CloudFormation the canon governs
cdk deploy aegis-governance-core \
  -c data_class=pii -c environment=dev -c app_name=aegis
```

> **Honesty note (per MATURITY.yaml discipline):** this CDK app is
> **live-validated**: its synth output was deployed to a clean account as plain
> CloudFormation and every control verified at runtime — canary allow, SSN
> guardrail deny, live Kill Switch engage → deny → SoD release, append-only
> replay refusal, and a WORM delete refusal — recorded as **Run 11** in
> `DEPLOYED-AND-VALIDATED.md` (2026-08-23). It remains synth-validated on every
> CI run by the template assertions in `tests/`.
