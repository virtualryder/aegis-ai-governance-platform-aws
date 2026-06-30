# The Aegis Minimum Bar

> The floor every agent — first-party or third-party add-on — must clear before it can touch a
> system of record. These are **gates, not guidelines**: CI rejects any agent that fails any item,
> and the gateway refuses to load one whose manifest does not satisfy the bar at runtime.
>
> Companion docs: [`../../docs/04-AGENT-ONBOARDING-STANDARD.md`](../../docs/04-AGENT-ONBOARDING-STANDARD.md)
> (the standard), [`agent-manifest.schema.json`](agent-manifest.schema.json) (the contract),
> [`example-agent.manifest.yaml`](example-agent.manifest.yaml) (a conformant example).

Clearing the bar is what makes an agent **portable** across every Aegis environment: once it meets
the floor, it inherits the customer's identity, data classes, guardrails, budgets, packs, and audit
with no per-customer governance re-build.

---

## The 9 points

### 1. Declared scope, nothing more
- **Rule.** The manifest enumerates *every* tool / MCP server (`grants.tools[]`) and *every* data
  class (`metadata.classification[]`) the agent may use. The agent may use nothing else.
- **Why.** Scope is enforced, not trusted. An agent that can silently reach an undeclared tool or
  data class is an unbounded blast radius and an un-auditable least-privilege story.
- **How CI enforces it.** Static analysis of the agent code resolves every tool invocation and
  data-class touch and diffs it against the manifest; any tool id or class not present in
  `grants`/`classification` fails the build. The gateway additionally denies undeclared calls at
  runtime as defense in depth.

### 2. Consequential actions withheld in code
- **Rule.** Any issue / adjudicate / release / award / transfer action is **absent** from
  `grants.tools[]` and appears only under `grants.consequential[]`; it is reachable solely through
  the human gate.
- **Why.** "Can the AI act on its own?" must be answerable with *no*. Withholding the action in code
  (not just policy) is what makes that answer hold up in a security review.
- **How CI enforces it.** A test asserts that no id listed in `grants.consequential[]` is also an
  executable grant, and a negative test proves the agent cannot invoke a consequential tool without a
  valid, bound approval token.

### 3. A bound, single-use, separation-of-duties human gate
- **Rule.** Every consequential action is wired to a human gate (`human_gate.mode` ≠ `none`) whose
  approval token is bound to the exact tool + arguments, single-use, expiring, and approved by
  someone other than the requestor (`human_gate.separation_of_duties: true`).
- **Why.** A reusable or unbound approval is a forgeable approval. Separation of duties prevents
  self-approval. (GxP / 21 CFR Part 11 additionally require e-signature-grade attributability —
  `human_gate.esignature_grade: true`.)
- **How CI enforces it.** A gate-integration test replays an approval token against a *different*
  tool/argument set and asserts rejection; replays an already-consumed token and asserts rejection;
  and asserts requestor ≠ approver.

### 4. A declared grounding source and threshold
- **Rule.** `grounding.knowledge_base` names at least one Bedrock Knowledge Base and
  `grounding.grounding_threshold` is set (0–0.99). No ungrounded free-generation against a system of
  record.
- **Why.** Grounding is the single biggest lever on hallucination and on "show me the source." A
  contextual-grounding threshold blocks answers that drift from retrieved source.
- **How CI enforces it.** Schema validation requires both fields and constrains the threshold to
  0–0.99; an eval-grounding check confirms responses below the threshold are blocked, not returned.

### 5. A token budget with a hard cap and an inference profile
- **Rule.** `budget.monthly_token_cap` is set and `budget.inference_profile` names a Bedrock
  application inference profile. `budget.alert_thresholds[]` is declared.
- **Why.** No unbounded spend ("token maxing"), and all spend is attributable to an owning
  department for chargeback. See [`../../docs/05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md`](../../docs/05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md).
- **How CI enforces it.** Schema validation requires the cap, profile, and thresholds; a check
  confirms all inference is routed through the inference-profile ARN (never a raw model id) so 100% of
  spend is tagged at source.

### 6. An eval suite that passes at the declared rate
- **Rule.** `evals.suite` exists and passes at ≥ `evals.min_pass_rate`, covering accuracy, refusal,
  fairness (four-fifths), prompt-injection resistance, and accessibility for user-facing output.
- **Why.** Promotion must be earned by measured behavior, not asserted. Re-running on model/prompt
  change catches regressions before they reach production.
- **How CI enforces it.** The eval runner executes the suite and fails the build if the pass rate is
  below `min_pass_rate` or if any required category is missing.

### 7. Masking on for every declared data class, fail-closed
- **Rule.** For every class in `metadata.classification[]`, the boundary masker (Comprehend /
  Comprehend Medical / Macie / card / biometric entity sets, per the active pack) is enabled, and if
  masking cannot run the boundary **denies** rather than leaks.
- **Why.** Sensitive data (PII/PHI/FTI/CJI/EDU/card) must never land in a prompt, a log, or the audit
  unmasked. Fail-closed is what turns "we mask" into a guarantee.
- **How CI enforces it.** A boundary test feeds synthetic sensitive payloads per declared class and
  asserts redaction; a fault-injection test disables the masker and asserts the boundary denies.

### 8. The manifest is signed by a known publisher
- **Rule.** `signing.publisher` is a trusted publisher and `signing.signature` is a valid detached
  signature over the manifest.
- **Why.** An unsigned or tampered manifest cannot be trusted to describe the agent it ships with.
  The gateway verifies the signature at load.
- **How CI enforces it.** CI verifies the signature against the publisher's trusted key and fails on
  an unknown publisher, a missing signature, or a manifest digest mismatch.

### 9. Pack compatibility
- **Rule.** `metadata.packs[]` declares the compliance overlay packs the agent requires; deploy
  fails if a required pack is not active in the target environment.
- **Why.** An agent built for HIPAA controls must not silently run somewhere those controls are off.
  Declaring required packs makes the deployment refuse an incompatible environment.
- **How CI enforces it.** A pre-deploy check intersects `metadata.packs[]` with the packs active in
  the target environment and fails the deploy on any missing pack; classification is also checked
  against what the active packs permit.

---

## How to test locally

The bar is meant to be runnable offline against synthetic data before anything is deployed.

```bash
# 1. Validate the manifest against the JSON Schema (draft 2020-12).
#    Any standard validator works; example with check-jsonschema:
pipx run check-jsonschema \
  --schemafile governance/onboarding/agent-manifest.schema.json \
  path/to/agent.manifest.yaml

# 2. Run the minimum-bar gate (points 1-9) against the agent.
#    This is the same gate CI runs; it returns non-zero on any failure.
aegis onboard verify path/to/agent --packs slg

# 3. Run the eval suite and confirm the declared pass rate.
aegis evals run path/to/agent/evals --min-pass-rate 0.95

# 4. Dry-run the gateway with the manifest loaded against the local
#    policy engine (no AWS calls) to exercise scope, human-gate, and
#    masking fail-closed behavior with synthetic payloads.
aegis gateway dry-run --manifest path/to/agent.manifest.yaml --fixtures fixtures/
```

A green local run is necessary but not sufficient: promotion to a real environment still runs the
sandbox → shadow/canary → promote flow in
[`../../docs/04-AGENT-ONBOARDING-STANDARD.md`](../../docs/04-AGENT-ONBOARDING-STANDARD.md) §3.

> The `aegis` CLI is a skeleton in this reference repo; the commands above document the intended
> contract so authors know exactly what each gate checks.
