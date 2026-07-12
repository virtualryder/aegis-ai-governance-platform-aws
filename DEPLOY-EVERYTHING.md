# Deploy the whole portfolio — one guide

> **For a full step-by-step SA walkthrough on a NEW account** (prerequisites, the landing-zone question,
> Aegis platform → each hero → runtime masking proof → teardown, with every command verified live), use
> **[`SA-DEPLOYMENT-RUNBOOK.md`](SA-DEPLOYMENT-RUNBOOK.md)** — the authoritative runbook. This page is the
> quick portfolio map and offline-first checklist.

*The single, copy-paste-able path from "five repos" to "a governed agent running in your AWS account,"
and how the pieces fit together. Reference accelerator — not an AWS service; deploy into **your** account
after your own security review. See [`NOT-CLAIMS.md`] per repo and [`BRAND-AND-TRADEMARK.md`](BRAND-AND-TRADEMARK.md).*

---

## 1. How the pieces fit together

```
                     ┌─────────────────────────────────────────────┐
                     │  AEGIS — the governance pattern (AGP v1.0)   │
                     │  identity · deny-by-default gateway ·        │
                     │  least-privilege intersection · bound SoD    │
                     │  approval · fail-closed masking ·            │
                     │  append-only+WORM audit · token budget ·     │
                     │  model gateway + grounding                   │
                     └───────────────────────┬─────────────────────┘
                     conforms to AGP v1.0 ▼   (each pack re-implements the SAME contract
                                              in its own platform_core — see AGP-CONFORMANCE.md)
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
   │  HCLS pack   │   SLG pack   │   HPP pack   │   EDU pack   │
   │ life-science │  state/local │ payer/prov.  │  education   │
   │ hero: PV 02  │ hero: 311 01 │ hero: RCM 01 │ hero: SFC 01 │
   └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
          │ each agent deploys via the SAME SAM golden-path pattern ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  One agent in your AWS account: API GW/AgentCore Gateway →    │
   │  MCP authz gateway (Lambda) → Step Functions workflow with a  │
   │  waitForTaskToken human gate → Bedrock+Guardrails (PrivateLink)│
   │  → DynamoDB append-only + S3 Object-Lock audit → CloudWatch   │
   └──────────────────────────────────────────────────────────────┘
```

**The story in one line:** *Aegis is the platform pattern; HCLS/SLG/HPP/EDU are vertical packs that
conform to it; every agent deploys the same governed golden path.* Improve a control once in the
pattern and every pack inherits it. Full map + hero sequencing: [`PORTFOLIO-START-HERE.md`](PORTFOLIO-START-HERE.md).

## 2. Recommended sequence (don't boil the ocean)

Prove **one** governed workflow, then expand. Lead in this order (strongest evidence first):
**Aegis pattern → HCLS Agent 02 (Pharmacovigilance) → SLG Agent 01 (311) → HPP Agent 01 (Revenue-Cycle
Denials) → EDU Agent 01 (only after a clean-account deploy is evidenced).** Why this order + honest
per-pack maturity: [`PORTFOLIO-START-HERE.md`](PORTFOLIO-START-HERE.md).

## 3. Prerequisites (once)

- An **AWS account** (or sandbox OU) you can deploy into, in a **supported Region** where Bedrock + the
  required model + PrivateLink are available. For PHI/CJI, a **BAA** / separated environment as applicable.
- **Amazon Bedrock model access** enabled for the model you'll use.
- An **identity provider** (Okta / Entra / AD) for federated login + the pack's role groups (a pilot can
  start with the authenticated-authorizer path; full IdP federation is engagement work).
- Tooling: **AWS SAM CLI**, **Python 3.11+**, **Node 20+** (for decks), **git**, and AWS credentials configured.

## 4. Step 0 — try everything locally first (no AWS, no API key)

Every pack runs its full governance suite offline, with no credentials. **~1,333 tests pass
portfolio-wide** — Aegis 43 · EDU 201 · SLG 236 · HPP 270 · HCLS 583 — and each count is gated by
`tools/check_maturity.py`, so the number cannot drift from that repo's `MATURITY.yaml` (the canonical
source of truth for every test count in this portfolio).

**HCLS — 583 tests**
```bash
cd hcls-ai-agents
make test              # 583 tests across 20 suites via scripts/run_all_tests.sh
make auth-demo
make neg-demo          # 10/10 governance refusals fire
make eval-agent02      # scored quality gate (PHI-leak threshold = 0)
```

**SLG — 236 tests**
```bash
cd slg-ai-agents
PYTHONPATH=platform_core:. pytest -q    # 236 tests
make neg-demo
make eval-311
```

**HPP — 270 tests**
```bash
cd healthcare_ai_agents
make test              # 270 tests, no API key
make neg-demo
make eval-denial
```

**EDU — 201 tests**
```bash
cd edu-ai-agents
make test              # canonical offline total 201 (see MATURITY.yaml)
make neg-demo
```

**Aegis platform — 43 tests**
```bash
cd aegis-ai-governance-platform-aws
PYTHONPATH=platform_core:. pytest demo platform_core/tests -q    # 43 tests
python demo/clean_account_acceptance.py                          # 18-step offline control walk-through
```

This proves the governed pattern, the 10 refusals, and the scored quality gate **before** any account
exists. Portfolio-wide health check from each repo: `python tools/check_maturity.py` and
`python tools/check_agp_conformance.py`.

## 5. Step 1 — deploy one hero golden path into your account

Each pack ships a **canonical SAM golden path** — one folder, one command, plus smoke test and teardown.
The shape is identical across packs; the exact folder + any bucket params are in each repo's runbook.

```bash
# HCLS Agent 02 (Pharmacovigilance) — the recommended first deploy
cd hcls-ai-agents/hcls-ai-agents
#   canonical path + runbook:
#   infra/golden-path-02-pharmacovigilance/  +  02-pharmacovigilance-agent/docs/aws-deployment-guide.md
make build-lambdas
make deploy AGENT=02-pharmacovigilance CFN_BUCKET=<your-cfn-bucket> CODE_BUCKET=<your-code-bucket>
```

```bash
# SLG Agent 01 (311)
cd slg-ai-agents/infra/golden-path-311
sam build && sam deploy --guided        # then:
./smoke_test.sh                          # exercises the governed workflow to the human gate
```

```bash
# HPP Agent 01 (Revenue-Cycle Denials)  — requires a BAA for real PHI
cd healthcare_ai_agents
#   per-agent SAM golden path + runbook: 01-revenue-cycle-denial-agent/docs/aws-deployment-guide.md
```

> Prefer the hardened variant where present (`infra/golden-path-*-secure/`): in-VPC Lambdas, PrivateLink,
> customer-managed KMS, S3 Object-Lock WORM, CloudFront/WAF, in one deploy.

## 6. Step 2 — verify in your account

- **Smoke test** the golden path (`./smoke_test.sh`) — the workflow should pause at the `waitForTaskToken`
  human gate and write an append-only audit record.
- **Run the negative demo** (`make neg-demo`) — 10/10 refusals should fire in-account.
- **Run the scored eval** (`make eval-agent02` / `eval-311` / `eval-denial`) — thresholds incl. PHI-leak = 0.
- Collect evidence: `tools/build_release_packet.sh <repo> 1.0.0` assembles the release bundle.

## 7. Step 3 — tear down

```bash
# per golden path
./destroy.sh                 # or: sam delete
```

Each pack's clean-account evidence documents a full deploy → run → teardown with zero residual resources
(`evidence/CLEAN-ACCOUNT-ACCEPTANCE.md`).

## 8. What to hand a reviewer or a customer

| Audience | Give them |
|---|---|
| CIO / CISO / architect | the hero **`ASSURANCE-PACKET.md`** (architecture, controls, evidence, negative results, RACI) + run `make neg-demo` |
| A pilot sponsor | the hero **`PILOT-SOW.md`** (scoped 6–10 week pilot) |
| Finance | the **`AWS-RUN-COST.md`** + the run-cost calculator xlsx (SLG/Aegis) or the ROI calculator (HCLS/EDU/HPP) |
| Ops / GRC | **`OPERATING-MODEL.md`** + **`RELEASE-PACKET.md`** + `AGP-CONFORMANCE.md` |
| Everyone | **`NOT-CLAIMS.md`** + **`BRAND-AND-TRADEMARK.md`** (what we don't claim; how to brand it) |

## 9. Standing caveats (keep true everywhere)

- Private connectivity to **regional** AWS services via PrivateLink; no egress to external AI APIs — **not**
  "data never leaves the VPC."
- **HIPAA-eligible** services under a **signed BAA** with customer controls — **not** "HIPAA-compliant."
  FedRAMP/StateRAMP authorizations belong to the **AWS services** in GovCloud, not to this accelerator.
- Connector tiers: everything here is tiers 1–3; **tier-4 production connectors (Veeva, Argus, Epic,
  ServiceNow, SIS/LMS, real 835 feeds) are engagement work** — see each `docs/CONNECTOR-MATURITY.md`.
- Per-pack deploy evidence is **not uniform** — lead with what each pack has actually proven:
  **HCLS/SLG** have all golden paths deployed → run → torn down in a clean account; **HPP** has Agent 01
  acceptance-gated (02–08 share the template but are not individually clean-account-gated); **EDU** is
  **partial** — golden-path controls (real model, deployed append-only audit, runtime PII masking,
  Cognito JWT) are clean-account-evidenced, but the **full `quickstart.yaml` nested agent stack is not
  yet deploy-validated**. Do not pitch EDU as equivalent to HCLS/SLG until that lands.
- HCLS masking is now **runtime-verified on AWS** (Comprehend Medical `DetectPHI` + Comprehend, masks
  before the audit write, fail-closed — `hcls-ai-agents/infra/golden-path-masking-verification/`). The module is now
  **wired into the HCLS hero pipeline** (masks the narrative prompt before the model, fail-closed —
  2026-07-12, unit-tested; not yet exercised live on AWS). Remaining CISO caveat: Agent 02's real
  Bedrock+Guardrails invocation still runs locally — a real Bedrock+Guardrails hero call on AWS is the
  top next increment for the lead hero.
- The Aegis **MCP authorizer now deploys the reviewed `platform_core` engine** (deny-by-default
  `policy_engine` + fail-closed `masker`) as a Lambda layer — the inline subset is deleted, so the
  deployed artifact is the code the offline suite tests. **Live-verified on a clean account and torn
  down** (stack `aegis-mcp-gateway-b3`, us-east-1, 2026-07-12): ALLOW / ALLOW+masked / DENY / APPROVAL_
  REQUIRED over HTTPS, deny strings verbatim from the reviewed engine
  (`infra/golden-pilot/B3-LIVE-DEPLOY-EVIDENCE.md`).
- Brand: plain-text "Built on AWS"; no AWS logo in customer-facing output; get field approval before
  external use — [`BRAND-AND-TRADEMARK.md`](BRAND-AND-TRADEMARK.md).
