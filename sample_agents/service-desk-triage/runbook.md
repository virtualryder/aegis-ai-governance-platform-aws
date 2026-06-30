# Runbook — service-desk-triage

## Ownership
- Owner / chargeback dept: dept-it
- Compliance pack: enterprise
- Blast radius: low

## Day-2 operations
- Budget alerts fire at 60% / 85% / 100% of the monthly token cap to the owner.
- On a budget hard-cap denial: review usage, request an audited temporary lift
  through the human gate (separation of duties enforced).
- On a grounding/hallucination flag spike: re-check the knowledge base and the
  pinned prompt hash; re-run the eval suite.
- On any model or prompt change: re-run evals before promotion (point 6).

## Incident
- Every allow/deny/pending/error is in the append-only audit (WORM evidence).
- To produce evidence for a review board: export the WORM evidence file and the
  chargeback report for the period in question.
