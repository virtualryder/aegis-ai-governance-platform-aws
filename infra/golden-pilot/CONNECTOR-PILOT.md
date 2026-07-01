# Governed Connector + Saga Rollback (task #20 tail)

> Deployed + live-tested on AWS (us-east-1) 2026-07-01, then torn down. A system of record (a ticket
> store) reached ONLY through a governed connector Lambda with **idempotency** and an append-only
> audit, wrapped in a Step Functions **saga with automatic compensation (rollback)**. This stands in
> for a real SaaS connector (e.g. ServiceNow); swapping the DynamoDB system-of-record for a live API
> is a credentials/endpoint change, not an architecture change.

## What is real now (`connector-pilot.yaml`)

- **Idempotent writes** — the connector claims the caller's `idempotency_key` with a DynamoDB
  conditional put before writing the system of record; a retry with the same key returns the SAME
  ticket and does not create a duplicate.
- **Saga with compensation** — `CreateTicket -> RiskyNotify` with a `Catch` to `Compensate`
  (void/rollback the ticket) when the downstream step fails.
- **Append-only audit** of every step (before/after/failed/compensated/idempotent-hit).

## Live results (2026-07-01)

- **Idempotency:** two `create_ticket` calls with `idempotency_key=idem-b` both returned
  `TICK-e378e4fb22` (2nd: `idempotent:true`); the tickets table holds a single row. Audit:
  `create_ticket_before -> create_ticket_after -> create_ticket_idempotent_hit`.
- **Happy path saga (c1):** execution **SUCCEEDED**; ticket `TICK-68dea0893b` **open**. Audit:
  `create_ticket_before -> create_ticket_after -> downstream_ok`.
- **Failure -> rollback saga (c2):** downstream failed; the saga caught it and ran compensation;
  execution ended **FAILED (CompensatedRollback)** and ticket `TICK-b3b4e6eb2c` is **voided**. Audit:
  `create_ticket_before -> create_ticket_after -> downstream_failed -> compensated`.

The tickets system of record ended with exactly: c1 open, b1 open (one, not two), c2 voided — the
governed connector never left an orphaned or duplicated write.

## Still open for a full customer pilot (tracked P1/P2)

A real external SaaS connector (ServiceNow/CRM) with OAuth/OBO credentials in Secrets Manager, its
tool contract registered in the gateway tool registry, and an operator **web dashboard** over the
evidence tables (this pilot proves the evidence via table scans / an evidence report rather than a UI).
