# Aegis Portfolio — Solution Architect Deployment Runbook

*The single, follow-along runbook to stand up the **Aegis governance platform** and **one governed hero
agent per vertical** in a **new AWS account**, prove the controls fire live, and tear everything down.
Every command below was executed on a clean account (`us-east-1`) and verified end-to-end — deploy →
run → destroy. This is a **scoped, synthetic-data pilot** runbook, not a production authorization.*

> **What "governed hero" means:** each vertical ships one deep, clean-account-validated agent plus
> governed scaffolds. You deploy the platform pattern once, then the hero(es) you want to demo. Don't
> deploy all 40 scaffolds — that's not the motion. Lead with the heroes.

---

## 0. What you will deploy

| Order | Component | Repo | Mechanism | Wall-clock |
|--:|---|---|---|--:|
| 1 | **Aegis platform** — deny-by-default authorization core (Verified Permissions / Cedar) | `aegis-ai-governance-platform-aws` | raw CloudFormation | ~3 min |
| 2 | **HCLS hero** — Pharmacovigilance ICSR intake (Agent 02) | `hcls-ai-agents` | SAM | ~6 min |
| 3 | **SLG hero** — Resident Services / 311 (Agent 01) | `slg-ai-agents` | SAM | ~5 min |
| 4 | **HPP hero** — Revenue-Cycle Denials (Agent 01) | `healthcare_ai_agents` | SAM (private VPC) | ~12 min |
| 5 | **EDU hero** — Student & Family Concierge (Agent 01) | `edu-ai-agents` | raw CloudFormation | ~3 min |
| + | **Runtime PII/PHI masking proof** (Comprehend Medical) | `hcls-ai-agents/infra/golden-path-masking-verification` | raw CloudFormation | ~3 min |
| + | **MCP authorizer = reviewed engine** (B3 — `platform_core` as a Lambda layer) | `aegis-ai-governance-platform-aws/infra/golden-pilot` | SAM | ~3 min |

Pick the subset you need. For a first leadership demo, **Aegis + one hero (HCLS Pharmacovigilance) +
the masking proof** is the strongest, cheapest story.

---

## 1. Prerequisites (do this once)

### 1.1 Does a landing zone need to be in place first?
**No — not for a scoped, synthetic-data pilot.** A single clean **sandbox account** (or a dedicated
sandbox OU) is sufficient, and that is what this runbook assumes. Everything deploys inside one account
and one Region.

**For production / real regulated data, yes** — a multi-account **AWS Control Tower** landing zone
(management + log-archive + audit + workload accounts, org SCPs, centralized CloudTrail, GuardDuty,
config rules) is the recommended foundation, but it is **customer-owned and out of scope for these
repos**. Don't let a landing-zone discussion block a synthetic-data pilot; it's a production prerequisite,
not a pilot one.

### 1.2 The account & Region
- A **clean AWS account** (or sandbox OU) you can deploy into and tear down freely.
- A **Region where Amazon Bedrock, the chosen model, PrivateLink, and Comprehend Medical are available**
  — `us-east-1` is the reference. (Comprehend Medical is not in every Region; check first.)
- For real PHI/CJI later: a **signed AWS BAA** and an appropriately separated environment. Not needed for
  synthetic data.

### 1.3 Enable Bedrock model access (5 min, in the console)
Bedrock → **Model access** → enable an **active** Anthropic Claude model (e.g. `Claude Sonnet 4.5`) and,
for the hero output-guardrail path, create/enable a **Bedrock Guardrail**. Verify from the CLI:
```bash
aws bedrock list-inference-profiles --region us-east-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId,'claude-sonnet-4')].[inferenceProfileId,status]"
```
> **Gotcha (seen live):** some older model IDs are now **Legacy** and Bedrock refuses to serve them
> ("marked by provider as Legacy…"). Use a current profile like
> `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. The repos' default model IDs are being refreshed;
> override with the pack's `BedrockModelId` / `ModelId` parameter if you hit this.

### 1.4 Tooling on the deploy workstation
| Tool | Why | Notes |
|---|---|---|
| **AWS CLI v2** | everything | `aws configure` with a deploy identity (see 1.5) |
| **AWS SAM CLI** | HCLS/SLG/HPP heroes | v1.16x+ |
| **Python 3.12** | `sam build` runtime match | Lambdas target `python3.12`; **3.13/3.14 will not build them** — install 3.12 |
| **git**, **make**, **a Unix shell** | layer staging / SAM makefile steps | On **Windows**: install Python 3.12 + `make` (e.g. `winget install Python.Python.3.12 ezwinports.make`) and put **Git's `usr\bin`** on `PATH` so `sam build` finds `sh`/`cp` |
| **jq**, **curl** | HPP acceptance test | Unix tools; Git Bash on Windows |

> **Windows note (learned the hard way):** without Python 3.12, `make`, and Git's Unix tools on `PATH`,
> the SAM heroes won't build. With them, all four SAM/CFN heroes build and deploy on Windows exactly as
> on Linux. The SLG layer was converted off a Unix-only Makefile to a portable pre-staged layer so this
> now "just works" cross-platform.

### 1.5 Deploy identity (IAM)
Use an admin-equivalent role **in the sandbox** (simplest for a pilot), or a scoped deploy role with:
CloudFormation, IAM (create roles/policies), Lambda, S3, DynamoDB, KMS, Cognito, Step Functions, API
Gateway, EC2/VPC (for the HPP private-VPC hero), Secrets Manager, **Verified Permissions**, and
**Comprehend / Comprehend Medical**. For production, scope this down and run it from a CI pipeline
(recommended — see §7).

### 1.6 Cost & teardown discipline
A full run of all five heroes + the masking proof, deployed and immediately torn down, is on the order
of **a few dollars** (PrivateLink endpoint-hours on the HPP VPC hero dominate). **Tear down every stack
when done** (§6). Set a budget alarm before you start.

---

## 2. Step 1 — Prove it offline first (no AWS, no keys)

Establish trust before spending a cent. Each repo runs its full governance suite offline
(**~1,333 tests portfolio-wide**, machine-checked by `tools/check_maturity.py`):
```bash
# example: life sciences
cd hcls-ai-agents && make test         # 583 tests
make neg-demo                          # 10/10 governance refusals fire
python tools/check_maturity.py         # asserts the count can't drift from MATURITY.yaml
```
Per-repo counts and the exact offline commands are in `DEPLOY-EVERYTHING.md` §4. Watching `make neg-demo`
(unauth / alg:none / wrong-role / replay / tamper / mask-fail / budget all REFUSE) is the most
persuasive two minutes you can show a CISO before any account exists.

---

## 3. Step 2 — Deploy the Aegis platform (authorization core)

The platform's deny-by-default authorization core deploys as an **Amazon Verified Permissions / Cedar**
policy store and proves live ALLOW/DENY decisions. Raw CloudFormation — no build step.
```bash
cd aegis-ai-governance-platform-aws/infra/golden-pilot
REGION=us-east-1; STACK=aegis-golden-pilot-avp
aws cloudformation deploy --stack-name $STACK --template-file avp-cedar.yaml --region $REGION
PSID=$(aws cloudformation describe-stacks --stack-name $STACK --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='PolicyStoreId'].OutputValue" --output text)

# three live authorization decisions — expect ALLOW, DENY, DENY
bash run_authz_tests.sh          # deploys, runs the 3 decisions, and tears the store down
```
**Verified live:** `1 legit read → ALLOW`, `2 unpermitted tool → DENY`, `3 wrong data class → DENY`.
That is deny-by-default with least-privilege intersection, enforced by AWS-managed Cedar — not app code.

> The broader golden pilot (`GOLDEN-PILOT.md`) adds the MCP gateway, Cognito identity, WORM evidence, and
> the reviewer service. For a first demo the AVP/Cedar core above is the crisp, cheap proof of the
> authorization model.

### 3b. (Optional) Deploy the MCP authorizer that runs the *reviewed* engine (B3)

The portable MCP gateway now ships the **reviewed `platform_core` engine as a Lambda layer** — the
deployed authorizer *is* the code the offline suite tests (deny-by-default `policy_engine` + fail-closed
`masker`), not an inline subset. Cross-platform SAM (pre-staged layer, no makefile):
```bash
cd aegis-ai-governance-platform-aws/infra/golden-pilot
bash prepare_layer.sh                      # stage platform_core into layer/python (Windows: py -3.12 stage_layer.py)
sam build -t mcp-gateway.yaml
sam deploy -t .aws-sam/build/template.yaml --stack-name aegis-mcp-gateway-b3 \
  --region us-east-1 --capabilities CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset
# mint a Cognito ID token for the created pool/client, then POST MCP tools/call to the McpEndpoint output:
#   kb.search_policy        -> ALLOW
#   ticket.create_draft     -> ALLOW + masked (SSN/email redacted in response AND append-only audit)
#   db.drop                 -> DENY  (deny-by-default)
#   ticket.submit (no appr) -> APPROVAL_REQUIRED (human gate)
sam delete --stack-name aegis-mcp-gateway-b3 --no-prompts
```
**Verified live (2026-07-12)** on a clean account and torn down zero-residual; the deny/gate strings
returned over HTTPS are `platform_core.policy_engine`'s verbatim messages — proof the deployed authorizer
is the reviewed engine. Full record: `infra/golden-pilot/B3-LIVE-DEPLOY-EVIDENCE.md`.

---

## 4. Step 3 — Deploy the governed heroes

Each hero follows the same shape: **build → deploy → verify outputs → (run the control demo) → destroy.**
Deploy only the ones you're demoing.

### 4.1 HCLS — Pharmacovigilance (Agent 02) — *recommended first hero*
```bash
cd hcls-ai-agents/infra/golden-path-02-pharmacovigilance
bash prepare_layer.sh                                  # stage platform_core+governance into layer/python
sam build                                              # python3.12
TOKEN=$(python -c "import secrets;print(secrets.token_hex(32))")
sam deploy --stack-name hcls-02 --region us-east-1 --resolve-s3 --no-confirm-changeset \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides "Environment=dev ConnectorMode=fixture TokenSecret=$TOKEN"
aws cloudformation describe-stacks --stack-name hcls-02 --region us-east-1 --query "Stacks[0].Outputs"
# ^ Verified live: GuardrailId (a real Bedrock Guardrail), GatewayUrl, UserPoolId,
#   PendingApprovalsTableName (SoD), StateMachineArn (human gate), AuditTableName.
./destroy.sh hcls-02      # or: aws cloudformation delete-stack --stack-name hcls-02
```

### 4.2 SLG — Resident Services / 311 (Agent 01)
```bash
cd slg-ai-agents/infra/golden-path-311
bash prepare_layer.sh          # portable pre-staged layer (no makefile) — builds on Win/mac/Linux
sam build
sam deploy --stack-name slg-311 --region us-east-1 --resolve-s3 --no-confirm-changeset \
  --capabilities CAPABILITY_IAM --parameter-overrides "Environment=dev ConnectorMode=fixture"
./smoke_test.sh slg-311        # starts a run, waits at the human gate, mints a BOUND approval, asserts SUCCEEDED
./destroy.sh slg-311
```
The smoke test proves the **waitForTaskToken human gate + single-use SoD approval** end-to-end.

### 4.3 HPP — Revenue-Cycle Denials (Agent 01) — *private-VPC hero*
```bash
cd healthcare_ai_agents/infra/golden-path-01-revenue-cycle
bash build.sh                  # vendors platform_core into src/, then sam build
sam deploy --stack-name hpp-gp01 --region us-east-1 --resolve-s3 --no-confirm-changeset \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides "Environment=dev WormMode=GOVERNANCE WormRetentionDays=1"   # see WORM note
./acceptance_test.sh hpp-gp01 us-east-1     # 10-stage: ALLOW/PENDING/bypass-blocked/SoD/replay/tamper/…
./teardown.sh hpp-gp01
```
> **WORM note:** the default `WormMode=COMPLIANCE` (2555-day retention) makes the audit S3 bucket
> **undeletable for 7 years** — that's the point in production, but for a throwaway pilot set
> `WormMode=GOVERNANCE WormRetentionDays=1` so teardown is clean (an empty bucket deletes; if the
> acceptance test wrote WORM objects, empty them with a governance-bypass first).
> **Teardown note:** this hero puts Lambdas in a private VPC; AWS releases the Lambda ENIs on a
> ~15–20 min delay, so `DELETE_IN_PROGRESS` can linger — it completes on its own.

### 4.4 EDU — Student & Family Concierge (Agent 01)
Raw CloudFormation, inline Lambda — no build step.
```bash
cd edu-ai-agents
aws cloudformation deploy --stack-name edu-concierge --region us-east-1 \
  --template-file infra/cloudformation/golden-path-lambda.template.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ModelId=us.anthropic.claude-sonnet-4-5-20250929-v1:0
FN=$(aws cloudformation describe-stacks --stack-name edu-concierge --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)   # if exported
# invoke with a PII-bearing record and confirm masking + append-only audit, then:
aws cloudformation delete-stack --stack-name edu-concierge --region us-east-1
```
**Verified live:** real Sonnet inference, student PII masked before persistence
(`[SSN-REDACTED]/[EMAIL-REDACTED]/[SID-REDACTED]`), append-only audit record written. *(The template's
account-ARN and default-model fixes must be applied — see the EDU patch.)*

---

## 5. Step 4 — Prove runtime PII/PHI masking on AWS (Comprehend Medical)

The single most compliance-load-bearing control, verified live. See
`hcls-ai-agents/infra/golden-path-masking-verification/README.md` for the full copy-paste; in short:
```bash
cd hcls-ai-agents/infra/golden-path-masking-verification
aws cloudformation create-stack --stack-name aegis-masking-verify --region us-east-1 \
  --template-body file://template.yaml --capabilities CAPABILITY_NAMED_IAM
# upload synthetic_phi_record.txt to the stack's DataBucket, then:
aws lambda invoke --function-name aegis-masking-verify --region us-east-1 \
  --cli-binary-format raw-in-base64-out --payload '{"s3_key":"synthetic_phi_record.txt"}' out.json
cat out.json     # Comprehend Medical DetectPHI + Comprehend DetectPiiEntities → masked BEFORE audit write
# empty bucket + delete stack to tear down
```
**Verified live:** 7 PHI + 7 PII entities detected and redacted; only masked text persisted; fail-closed.
See `EVIDENCE.md`.

---

## 6. Step 5 — Tear everything down (avoid cost)

```bash
for s in hcls-02 slg-311 hpp-gp01 edu-concierge aegis-masking-verify; do
  aws cloudformation delete-stack --stack-name $s --region us-east-1; done
# aegis-golden-pilot-avp tears itself down inside run_authz_tests.sh
```
Confirm each is gone (`describe-stacks` → *does not exist*). Teardown gotchas: **empty S3 buckets
first**; the **HPP VPC** takes ~15–20 min (Lambda ENI release); **COMPLIANCE WORM** buckets won't delete
(that's by design). A portfolio driver that does deploy→smoke→**guaranteed-teardown** with a safe
`--dry-run` default lives at `tools/deploy_all_golden_paths.sh`.

---

## 7. Production hardening (customer-owned — name it, don't hide it)

Beyond a synthetic-data pilot, the customer owns: a **Control Tower landing zone** + org SCPs; **IdP
federation** (SAML/OIDC) into Cognito; a **real Bedrock+Guardrails hero invocation with
masking-before-prompt** and site-tuned regex ID patterns; a **live tier-4 connector** (Veeva/Argus, X12
835, Epic/Availity, SIS/LMS); a **penetration test**; **DR + monitoring** ops; a **CI pipeline** that
deploys → tests → captures **independent, reproducible** CloudTrail/IAM-simulation evidence (replacing
single-operator attestation); and the applicable **ATO/HITRUST/FedRAMP** authorization. These are the
P1/P2 roadmap, not pilot blockers.

---

## 8. What to hand a CIO / CISO
`PORTFOLIO-EXECUTIVE-SUMMARY.md` (10-min front door) · `PORTFOLIO-MATURITY-SCORECARD.md` (what's proven)
· `AWS-INTERNAL-REVIEW-PACKET.md` (verify-it-works) · `DO-NOT-CLAIM.md` (the honesty boundary) · this
runbook · the hero's `EVIDENCE.md` files. Lead with the negative demo and the masking evidence; frame
the ask as **buy-off to run discovery + architecture workshops + scoped synthetic-data pilots**, with a
clear P1 roadmap to real-data readiness.
