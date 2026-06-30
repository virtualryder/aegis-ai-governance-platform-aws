# Aegis — Governance Control Plane: Live Laptop Demo

> The artifact a salesperson runs **live in front of a customer**. It exercises
> the entire Aegis governance control plane end to end on a laptop — **no AWS,
> no API key, no network, Python standard library only**. It is the offline test
> analog of the production enforcement path (AgentCore Gateway + Policy in
> AgentCore / Amazon Verified Permissions, Cedar) described in
> [`docs/02-REFERENCE-ARCHITECTURE.md`](docs/02-REFERENCE-ARCHITECTURE.md) §3.

## Run it (one command)

```bash
python3 demo/clean_account_acceptance.py
```

It prints a `PASS`/`FAIL` line per step and **exits non-zero if any step fails**.
A green run is the whole pitch: every governance promise, demonstrated, in ~1s.

Optional (bonus) pytest path — same assertions, if `pytest` is installed:

```bash
pytest demo/test_acceptance.py
```

## What each step proves

| # | Step | What it proves to the customer |
|---|------|--------------------------------|
| 1 | register one agent | An agent is admitted only via a **schema-validated, signed manifest** (the contract). |
| 2 | register one MCP tool | Tools are registered in the **gateway tool registry**; nothing undeclared is reachable. |
| 3 | load one KB fixture | A **grounding source** is wired before any generation against a system of record. |
| 4 | invoke the model gateway | **Profile allowlist + prompt-version pin + JSON-schema validation + contextual grounding** — and an ungrounded answer is **flagged as a hallucination**. |
| 5 | enforce max_tokens / budget | An over-budget call is **denied before spend** (FinOps preflight, fail-closed on budget). |
| 6 | DENY unauthorized tool | **Deny-by-default**: a tool outside grant ∩ entitlement is refused. |
| 7 | DENY wrong data class | **Data-class boundary**: a `cji` call against a `[public, pii]` agent is refused. |
| 8 | require approval (high risk) | A **consequential action is withheld in code** and routed to the human gate. |
| 9 | BLOCK self-approval | **Separation of duties**: reviewer == requester is rejected. |
| 10 | approve through a reviewer | A different reviewer approves; the token is **bound** to the exact action. |
| 11 | execute the approved action ONCE | The exact approved action runs once; a **scoped per-call token** is minted (OBO/STS analog). |
| 12 | REJECT a replay | The consumed, **single-use** approval cannot be replayed (DynamoDB conditional-write analog). |
| 13 | immutable audit | The audit is **hash-chained and append-only**; a mutation attempt **raises**. |
| 14 | export WORM evidence | A sealed, read-only **WORM evidence file** (S3 Object Lock analog) is written. |
| 15 | populate usage ledger | Real reads accrue usage; **SSN/email are masked**, and masking **fails closed**. |
| 16 | chargeback report | Per-department **chargeback CSV** with application-inference-profile tags (dept/team/app/data_class/pack). |
| 17 | clean teardown | `demo_out/` artifacts are removed for a repeatable demo. |

## Expected output (tail)

```
[PASS] step 16: produce a chargeback report (per-dept, AIP tags)
            -> demo_out/chargeback.csv (calls=4 tokens=5,000 cost=$0.0150)

dept            app                   data_class pack         calls      tokens   cost_usd
------------------------------------------------------------------------------------------
dept-it         service-desk-triage   public     enterprise       4       5,000     0.0150
------------------------------------------------------------------------------------------
TOTAL                                                                4       5,000     0.0150

[PASS] step 17: clean teardown of demo_out
============================================================
  RESULT: 18/18 steps passed, 0 failed
============================================================
```

The demo writes evidence under `./demo_out/` during the run (audit.jsonl,
evidence.worm.json, chargeback.csv) and tears it down at the end. Step 17 stays
green on restricted/virtualized mounts that forbid unlink — it still issues the
real deletion (which removes the files on a normal filesystem).

## Add an agent in one command

The platform is "easy to add agents after it is up." The scaffolder generates a
**conformant** agent package and validates it against the schema before writing:

```bash
python3 tools/add_agent.py --id billing-inquiry --owner dept-finance \
    --pack enterprise --blast-radius low
```

This writes `sample_agents/billing-inquiry/` with:

```
agent.manifest.yaml   # conforms to governance/onboarding/agent-manifest.schema.json
prompts/system.md     # pinned system prompt
evals/suite.md        # eval stub: accuracy, refusal, fairness, prompt_injection, a11y, grounding
runbook.md            # day-2 operations
README.md             # how it clears the 9-point minimum bar
```

Two ready-made sample agents ship in `sample_agents/`:
- `service-desk-triage` — enterprise pack, low blast radius
- `resident-services-311` — slg pack, low blast radius

## What's inside (the control plane)

All under [`platform_core/`](platform_core/), pure Python, stdlib only:

| Module | Control |
|--------|---------|
| `policy_engine.py` | The deny-by-default **ALLOW-iff predicate** (arch §3): auth, grant∩entitlement, purpose, data-class boundary, consent, residency, budget, approval. |
| `masker.py` | **Fail-closed** deterministic masking (SSN, email, phone, Luhn-checked card, MRN, student-id). |
| `token_budget.py` | Per-agent/department **token meter**, hard/soft caps, threshold alerts, preflight. |
| `approval_ledger.py` | **Bound, single-use, separation-of-duties** approvals; replay-proof. |
| `audit_ledger.py` | **Append-only, hash-chained** audit; immutable; WORM export. |
| `chargeback.py` | Per-department usage aggregation → **chargeback CSV** with AIP-style tags. |
| `model_gateway.py` | Offline deterministic model: **profile allowlist, task routing, prompt pin, schema validation, grounding/hallucination** check. |
| `gateway.py` | The **MCP authorization gateway**: policy → budget → approval → scoped-token mint → tool exec → masked append-only audit. |
| `manifest_loader.py` | Stdlib-only YAML/JSON manifest loader + pragmatic schema validation. |

No third-party dependencies. No `boto3`. No network. Runs on stock Python 3.
