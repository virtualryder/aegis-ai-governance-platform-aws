# Runtime Security Evidence — capture runbook

*Some security proofs can only be produced by a **deployed** stack — they are screenshots/exports from
a running account, not text you can write. This runbook is the honest home for them: it says exactly
what to capture, how, and where it lands, so the evidence is **one deploy + one command away** instead
of being fabricated. Until captured, these items stay marked "pending clean-account capture" in the
hero `SECURITY-EVIDENCE-PACK.md`.*

> Reference accelerator — not an AWS service. Run against **your** account after your own security
> review. See each repo's `NOT-CLAIMS.md`.

## What must be captured at deploy time (and why it can't be written now)

| Proof | Why it needs a live stack | Captured by |
|---|---|---|
| **Runtime PHI/PII/CJI masking** | You must show a *real* audit record with sensitive fields masked | `--audit-table` scan → confirm no raw identifiers |
| **Bedrock Guardrails blocking** | You must show a real invoke that Guardrails *refused* | guardrail config + a blocked-input invoke screenshot |
| **Locked egress** | You must show the Network Firewall *allowed* the one FQDN and *dropped* others | `--log-group` NFW alert logs (allow + drop) |
| **IAM Access Analyzer** | Findings only exist against real deployed IAM | `accessanalyzer list-findings` |
| **CloudWatch alarms + dashboard** | Alarms/dashboards only exist once deployed | `describe-alarms` + dashboard JSON + screenshot |
| **WORM immutability** | You must show an overwrite of an Object-Lock object is *denied* | `--audit-bucket` overwrite probe → expect `AccessDenied` |
| **Human gate paused execution** | Only visible in a real Step Functions run | screenshot of the execution at `waitForTaskToken` |
| **Teardown** | Proof of zero residual resources | `destroy.sh` output |

## How to capture (one command + a few screenshots)

```bash
# 1. Deploy a hero golden path (see DEPLOY-EVERYTHING.md). Then:
tools/collect_runtime_evidence.sh \
  --stack <cfn-stack-name> --region <region> \
  --audit-table <audit-ddb-table> --audit-bucket <worm-evidence-bucket> \
  --guardrail-id <bedrock-guardrail-id> --log-group <nfw-alert-log-group> \
  --out evidence/runtime/$(date +%F)

# 2. Add the manual screenshots the MANIFEST lists (dashboard, blocked invoke, paused execution, teardown).
```

The script writes `evidence/runtime/<date>/` with a `MANIFEST.md`. Every item is either **captured**
(file saved) or **NOT CAPTURED** (with the reason) — it never fabricates a proof. Fold the folder into
the tagged release via `tools/build_release_packet.sh`.

## What is already proven offline (no deploy needed)

The following are already covered by code + tests and do **not** wait on a deploy — cite them now:

- **Deny-by-default authorization, least-privilege intersection, human approval (SoD, single-use),
  scoped tokens, fail-closed masking (control exercised), audit-write fail-closed, budget** — the
  10-point `demo/negative_demo.py` (CI-gated).
- **Audit immutability / WORM intent** — `test_evidence_vault.py` (append-only API + `try_mutate` raises;
  IaC denies `UpdateItem`/`DeleteItem` + S3 Object Lock).
- **End-to-end authorization chain** — `demo/demo_auth.py` (IdP → token exchange → intersection → SoD → audit).
- **Scored output quality** (incl. PHI-leak = 0) — the per-hero `make eval-*`.

The runtime runbook fills the gap between "the control is implemented and negative-tested" and "the
control was observed operating in a real account."
