# Connector maturity — the four terms we use (and mean precisely)

*A connector is the adapter between an agent tool call (through the MCP authorization
gateway) and a system of record. "It has a connector" is meaningless unless the maturity
is stated. We use exactly four terms. Do not blur them, and never let a reader infer that a
customer's production system integration exists unless it is explicitly at tier 4.*

| # | Term | What it means | What it proves | What it does NOT prove |
|---|------|---------------|----------------|------------------------|
| 1 | **Fixture** | Deterministic in-repo data (JSON/objects). No network. `CONNECTOR_MODE=fixture`. Default in CI and demos. | The agent graph, the governance deny-paths, and the output logic — with no API key or account. | Nothing about real network, auth, latency, or a real system of record. |
| 2 | **Local HTTP stand-in** | A bundled local reference service that implements the connector's API *shape* over HTTP. Runs on localhost. | The connector's real HTTP path: auth headers, retries, timeouts, error handling, pagination. | It is **not** the vendor's API. Nothing about the vendor's real schema, quirks, or entitlements. |
| 3 | **Live reference connector** | Talks to a **real, external, public / no-BAA** system of record (e.g. openFDA/FAERS, NYC 311 Socrata, College Scorecard). Read-only, fail-closed, governed through the gateway. | The governed pattern works against a **real** system of record, end to end, with real data. | It is a **public** data source, **not** the customer's production system, and read-only. |
| 4 | **Customer production connector** | Integration with the customer's **actual regulated system of record** (Veeva Vault / Argus Safety, Epic, ServiceNow, a SIS/LMS, an X12 835 remittance feed, etc.). Under BAA/contract, human-gated. | Production integration for a specific customer. | **Not present in these repositories.** This is scoped, engagement-owned work performed in the customer's account after their own security review and authorization. |

**The bright line:** everything in these repos is at **tiers 1–3**. **Tier 4 (Veeva, Argus,
Epic, ServiceNow, PowerSchool/Banner/Canvas, an X12/EDI feed, or any named customer system)
is NOT done here** and is never implied to be. A live reference connector (tier 3) proves the
*pattern* against a real public system; it is not a substitute for the customer's production
integration, which is engagement work under the shared-responsibility model.

## Current connector status — this repo

See each repo's own `docs/CONNECTOR-MATURITY.md` and `MATURITY.yaml` for its per-agent connector tiers. Portfolio summary of tier-3 live reference connectors:

| Pack | Hero agent | Live reference connector (tier 3, public) |
|---|---|---|
| HCLS | 02 Pharmacovigilance | openFDA / FAERS |
| SLG | 01 Resident Services / 311 | NYC 311 Socrata |
| EDU | 01 Student & Family Concierge | College Scorecard |
| HPP | 01 Revenue-Cycle Denials | (documented X12 835 scaffold — no public denial API) |
| Aegis | platform | (reference connectors only) |

**Tier 4 (Veeva, Argus, Epic, ServiceNow, PowerSchool/Banner/Canvas, real 835 feeds) is NOT done in any repo** — it is customer-engagement work.

*Maturity for every agent and connector is recorded in machine-readable form in
each repo's `MATURITY.yaml` (this doc is the human-readable companion). If a claim
anywhere reads as stronger than this table, this table and `MATURITY.yaml` govern.*
