# 06 — Hallucination Control & Agent Evaluation

> **Status & maturity (read first).** The `[Impl]` / `[Cfg]` tags below describe *design intent
> and the reference implementation* — not production authorization. For the authoritative
> per-control maturity (Designed / Implemented-offline / Deployed-on-AWS / Integration-tested /
> Production-enforced) see [`GAP-CLOSURE-BACKLOG.md`](GAP-CLOSURE-BACKLOG.md). As of 2026-06-30 the
> append-only audit, WORM enablement, Bedrock Guardrail, human gate, and fail-closed gateway are
> **deployed and live-validated on AWS**; Cedar policy enforcement, identity/MFA federation,
> runtime masking, token budgets, and live connectors remain **offline reference or planned**.

> Hallucination control is a board-level trust question, not a model-tuning detail. Aegis layers
> several independent controls so that ungrounded or unsound output is blocked or flagged before a
> human ever acts on it, and every agent must prove its behavior with evals before it can be
> promoted. Grounded in [`../SOURCES.md`](../SOURCES.md) §3 and §8. Controls are marked **[Impl]** =
> platform-implemented or **[Cfg]** = customer-configured.

## 1. Grounding is the primary lever — governed RAG

The single biggest lever on hallucination is **not generating from the model's parametric memory in
the first place.** Aegis routes agents through **governed RAG over a Bedrock Knowledge Base**:
retrieval runs as an **audited read** through the gateway (`kb.search_policy`), security-trimmed to
the caller's entitlements, and the retrieved passages become the **grounding source** every later
check scores the answer against. **[Impl]**

This does two jobs at once. It gives the model a real, current, in-scope source to answer from
instead of inventing one, and it makes every answer **traceable** — "show me the source for this"
has an answer, because the retrieval is logged and the grounding source is known. Routing retrieval
through the gateway means even reads are governed, entitlement-trimmed, and audited (see
[`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) §5).

## 2. Contextual grounding checks (Bedrock Guardrails)

On top of governed RAG, Bedrock Guardrails apply a **contextual grounding check** that detects and
filters hallucinations in RAG by scoring two dimensions, each on a configurable threshold **0–0.99**:

- **Grounding** — is the response factually supported by the retrieved source? A low grounding score
  means the model deviated from or embellished the source.
- **Relevance** — does the response actually answer the user's query, or wander off?

Responses below the configured thresholds are **blocked or flagged** before they reach a human. The
threshold is declared per agent in the manifest (`grounding_threshold`, see
[`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md)) so that high-stakes agents can
demand stricter grounding than low-stakes ones. **[Impl Guardrail wiring / Cfg threshold tuning]**

## 3. Automated reasoning checks (Bedrock Guardrails)

Contextual grounding answers "is this supported by the source?" **Automated reasoning checks** answer
a harder question: "is this *logically and factually sound* against a defined policy?" Bedrock
Guardrails automated reasoning checks use **formal logic and mathematical techniques** to validate
responses against a policy the customer defines. This is the **first GenAI safeguard to use formal
logic to help prevent factual errors from hallucinations** — it can mathematically validate that an
answer is consistent with codified rules rather than relying on probabilistic judgment.

This matters most where rules are precise and an error is consequential: eligibility logic, benefit
rules, regulatory constraints, dosage or pricing rules. The check is configured per pack/agent as
part of the guardrail policy. **[Impl Guardrail wiring / Cfg policy authoring]**

## 4. Keep deterministic decisioning OUTSIDE the LLM

For **regulated decisions**, the soundest hallucination control is to not ask the model to make the
decision at all. Aegis keeps deterministic decisioning engines (eligibility rules, benefit
calculations, statutory thresholds) **outside the LLM** as conventional, testable, auditable code.
The agent gathers context, drafts, and explains, but the actual issue/adjudicate/release/award/transfer
decision is either a deterministic engine or a **human gate** — never a free-generated model output.
This ties directly to the control plane's consequential-action rule (see
[`02-REFERENCE-ARCHITECTURE.md`](02-REFERENCE-ARCHITECTURE.md) §3): consequential actions are
withheld from the agent in code. **[Impl]**

## 5. The eval harness (required by the minimum bar)

No agent reaches a system of record without passing an **eval suite** at its declared rate
(`min_pass_rate`, default 0.95; see [`04-AGENT-ONBOARDING-STANDARD.md`](04-AGENT-ONBOARDING-STANDARD.md)
§2). The required dimensions:

| Eval dimension | What it measures | Why it's a gate |
|---|---|---|
| **Accuracy** | Correctness against a labeled gold set, with grounding-source checks | Catches confabulation before promotion |
| **Refusal** | The agent declines out-of-scope, unsupported, or ungrounded requests instead of inventing | Refusal is a feature, not a failure |
| **Fairness / four-fifths** | Outcome parity across protected groups (four-fifths / 80% rule) | Surfaces disparate impact before it ships |
| **Prompt-injection resistance** | Robustness to instructions hidden in retrieved content or user input | Tool/data boundaries hold under attack |
| **Accessibility** | User-facing output meets accessibility requirements | Required for public-facing agents |

Evals are **re-run on any model or prompt change** as a day-2 drift control, so swapping a model or
editing a prompt cannot silently regress behavior.

## 6. The trust pipeline (in text)

Every agent answer that could reach a person passes through this chain. A failure at any stage
blocks, flags, or routes to a human rather than returning an unsound answer:

```
User request
  → Gateway: re-validate identity, least-privilege intersection, scope check         [block if out of scope]
  → Governed RAG: audited, entitlement-trimmed retrieval from the Knowledge Base      [grounding source captured]
  → Bedrock model (in-account, over PrivateLink) drafts an answer from the source
  → Guardrails — input/output:
        · PII/sensitive-info filters                                                  [mask / block]
        · Contextual grounding check (grounding + relevance, 0–0.99)                  [block/flag if below threshold]
        · Automated reasoning check (formal logic vs defined policy)                  [block/flag if unsound]
  → Consequential action? → NOT generated by the model → deterministic engine OR human gate
  → Append-only audit record (allow / deny / flagged) with grounding lineage          [evidence]
```

The principle: **the model proposes; governed retrieval grounds it; guardrails validate it;
deterministic logic or a human decides it; the audit records it.**

## 7. Mapping to the NIST AI RMF GenAI Profile

These controls map directly to risks named in **NIST AI 600-1, the AI RMF Generative AI Profile**
(SOURCES.md §8):

| Aegis control | NIST AI RMF GenAI risk | Function |
|---|---|---|
| Governed RAG + grounding source capture | **Confabulation** (hallucination), **Information Integrity** | Map / Measure |
| Contextual grounding check (grounding + relevance) | **Confabulation**, **Information Integrity** | Measure / Manage |
| Automated reasoning check (formal logic) | **Confabulation**, **Information Integrity** | Measure / Manage |
| Deterministic decisioning outside the LLM + human gate | **Confabulation**, Human-AI Configuration | Manage |
| Eval harness (accuracy, refusal, fairness, injection, a11y) | **Confabulation**, **Information Security**, fairness/harmful bias | Measure |
| Append-only audit with grounding lineage | **Information Integrity** | Measure |

## 8. Who cares & why

- **CEO / Agency head / Board:** "Can we trust what the agent says?" — Yes, because nothing reaches a
  person without being grounded in an auditable source and validated by guardrails, and consequential
  decisions are never the model's to make.
- **CISO:** grounding + automated reasoning + prompt-injection evals are documented, testable
  controls that map to NIST AI RMF and survive a security review.
- **Regulated decision owner (benefits, health, finance):** deterministic logic and formal-logic
  validation keep statutory rules out of probabilistic generation.
- **Architect:** one grounding pattern, one guardrail policy shape, one eval harness — inherited by
  every agent, not rebuilt per agent.

## 9. Honest limits

Contextual grounding and automated reasoning reduce but do not eliminate hallucination; thresholds
and policies are **customer-configured** and need tuning per workflow. Automated reasoning checks are
only as good as the policy the customer authors. Eval gold sets and fairness baselines are
customer-owned data-quality work. Guardrail and red-team tuning, plus accessibility testing, are
tracked as shared-responsibility items in
[`10-PRODUCTION-READINESS-RACI.md`](10-PRODUCTION-READINESS-RACI.md).
