# AWS Internal Review Packet

*For an AWS SA / specialist / leader reviewing the portfolio for internal enablement and go-to-market.
Everything here is verifiable in minutes. This packet answers: does it work as prescribed, is the
evidence real, and how does it fit AWS's own primitives?*

---

## 1. What to look at, in order (≤ 30 minutes)
1. [`PORTFOLIO-EXECUTIVE-SUMMARY.md`](PORTFOLIO-EXECUTIVE-SUMMARY.md) — the 10-minute story.
2. [`PORTFOLIO-MATURITY-SCORECARD.md`](PORTFOLIO-MATURITY-SCORECARD.md) — what is / isn't validated.
3. This packet — how to verify and how it maps to AWS.
4. One hero golden path (e.g. `hcls-ai-agents/infra/golden-path-02-pharmacovigilance/`) — read `template.yaml` + `acceptance`/`smoke_test.sh`.
5. [`DO-NOT-CLAIM.md`](DO-NOT-CLAIM.md) — the honesty boundary.

## 2. Verify it works as prescribed (offline, no AWS, no keys)
Each repo runs its full suite with no credentials. Representative commands:
```bash
# platform
cd aegis-ai-governance-platform-aws && PYTHONPATH=platform_core:. pytest demo platform_core/tests -q
python demo/clean_account_acceptance.py          # 18-step control walk-through, offline

# a vertical (life sciences)
cd hcls-ai-agents && make test                    # 580 tests via scripts/run_all_tests.sh
make neg-demo                                      # 10/10 governance refusals fire
python tools/check_maturity.py                    # asserts the maturity count is honest
```
Expected: **~1,326 offline tests green portfolio-wide** (Aegis 43 · EDU 197 · SLG 236 · HPP 270 ·
HCLS 580 — each canonical in that repo's `MATURITY.yaml`), negative-control demos firing on
unauthenticated / wrong-role / replay / tamper / mask-fail / budget, and the drift-checker exiting 0.
*(A plain root `pytest` may report a lower number per repo — e.g. HCLS collects 576 because the openFDA
live test skips and suites run in isolated processes; `run_all_tests.sh` is the authoritative runner and
`MATURITY.yaml` is canonical.)*

## 3. Verify it deploys as prescribed (clean AWS account)
The supported path is the per-agent **SAM golden paths** (`infra/golden-path-*/`):
```bash
cd hcls-ai-agents/infra/golden-path-02-pharmacovigilance
./deploy.sh            # sam build && deploy: private VPC, PrivateLink to Bedrock/KMS/Logs/STS,
                       #   Cognito JWT authorizer, authenticated reviewer service, WORM audit
./smoke_test.sh        # exercises the governed workflow end-to-end
./destroy.sh           # clean teardown
```
Prerequisites are documented per path (Python 3.12 for `sam build`, Bedrock model access, region).
The HPP Agent-01 golden path additionally ships a 10-stage `acceptance_test.sh` that provisions two
Cognito users and **proves ALLOW / PENDING / bypass-blocked / SoD / replay / tamper** — this is the
thing to run in a workshop and watch the human gate hold.

## 4. How it maps to AWS
- **AWS services (all GA):** Amazon Bedrock + Guardrails, Cognito, Step Functions (`waitForTaskToken`
  human gate), DynamoDB, S3 Object Lock (WORM), KMS (per-data-class CMKs), API Gateway, PrivateLink,
  Secrets Manager, CloudWatch. GovCloud-parameterized (partition/region).
- **Well-Architected (Security pillar) intent:** least privilege, encryption at rest with CMKs,
  private connectivity, immutable audit, secrets management, blocking supply-chain CI.
- **Bedrock AgentCore:** Aegis is the **governance overlay + vertical packs** on top of AgentCore's
  managed Gateway / Identity / Policy(Cedar) / Evaluations. It models both the managed-AgentCore path
  and a portable API-GW+Cognito path (the portable path is the live-validated default). See the
  AgentCore-overlay slide/one-pager.

## 5. Evidence integrity
- `MATURITY.yaml` is machine-checked by `tools/check_maturity.py` (CI-enforced) — the maturity table
  cannot silently drift from the test count.
- Release evidence is real: the previously false-passing HCLS packet was quarantined and regenerated
  with real tool output and a real SBOM; the builder now **fails** on a missing tool rather than
  marking it ✓.
- Clean-account acceptance reports are sanitized (account IDs redacted) and specific (stack lifecycle,
  CloudTrail windows). *Independent, non-self-attested capture for the lead hero is a recommended
  next increment for a broader GTM sign-off.*

## 6. Honest gaps a reviewer will (correctly) note — and the response
| Observation | Response |
|---|---|
| "The agents are mostly deterministic — where's the AI?" | Correct and disclosed. The governance is the product; each hero has one real Bedrock path. Adding a model-in-the-loop demo on the lead hero is the top next increment. |
| "One hero + scaffolds, not 40 agents." | Deliberate. Low-blast-radius sequencing; the scorecard says so. |
| "Connectors are tier-3 public reads." | Correct. Tier-4 live systems of record are engagement work, flagged everywhere. |
| "Is HCLS masking actually proven on AWS?" | Not yet. HCLS PHI/PII masking + Bedrock/Guardrails are implemented and unit-tested but **not runtime-verified in the clean-account evidence path** (disclosed in HCLS `MATURITY.yaml` and the scorecard). EDU *does* have runtime PII masking evidenced on AWS. A runtime masking + Guardrails proof on the HCLS lead hero is the top next increment. |
| "Is EDU as deploy-ready as HCLS/SLG?" | No. EDU golden-path controls are clean-account-evidenced, but the full `quickstart.yaml` nested agent stack is not yet deploy-validated. Lead with HCLS/SLG; treat EDU deploy evidence as partial. |
| "Why not just AgentCore?" | Aegis is the regulated-industry overlay (intersection authz, bound SoD approvals, WORM evidence, compliance packs) AgentCore's horizontal primitives don't provide. |

## 7. Recommendation for AWS
Approve for **internal enablement + customer architecture workshops now**, and **scoped
synthetic-data pilots** on the heroes. For a broader go-to-market motion, fund three increments on one
lead hero: (a) a real Bedrock+Guardrails path with masking-before-model, (b) one live tier-4
connector, (c) independent captured deploy evidence.
