# resident-services-311

Scaffolded Aegis agent for the **slg** pack, owned by **dept-resident-services**,
blast radius **low**.

This package conforms to `governance/onboarding/agent-manifest.schema.json` and
clears the 9-point minimum bar:

1. Declared scope only — tools and data classes are enumerated in the manifest.
2. Consequential action `record.issue_decision` withheld; human-gated only.
3. Bound, single-use, separation-of-duties human gate wired.
4. Grounding KB `kb-slg-policy` + threshold declared.
5. Token budget (hard cap) + inference profile `aip-slg-default`.
6. Eval suite stub covering all required categories.
7. Masking on for every declared data class, fail-closed.
8. Manifest carries a publisher + signature placeholder (sign before deploy).
9. Pack `slg` declared; deploy fails if the pack is not active.

## Layout
- `agent.manifest.yaml` — the signed contract the gateway enforces
- `prompts/system.md` — pinned system prompt
- `evals/suite.md` — eval suite stub
- `runbook.md` — day-2 operations
