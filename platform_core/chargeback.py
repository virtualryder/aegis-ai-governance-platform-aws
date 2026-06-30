"""chargeback — per-department usage aggregation and chargeback report.

Implements docs/05-FINOPS-TOKEN-BUDGETS-CHARGEBACK.md §2: aggregate the usage
ledger by department/cost-center using application-inference-profile-style tags
(dept / team / app / data_class / pack) and emit a chargeback report. Production
sources this from Cost Explorer / CUR; this offline analog sources it from the
in-process usage ledger the model gateway populates.

Public API:
    UsageLedger            -- collects per-call usage events with AIP tags
    write_chargeback_csv() -- writes demo_out/chargeback.csv grouped by dept/app
    render_table()         -- returns a printable ASCII table for the demo
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class UsageEvent:
    agent_id: str
    dept: str
    team: str
    app: str
    data_class: str
    pack: str
    inference_profile: str
    tokens_in: int
    tokens_out: int
    cost_usd: float

    @property
    def tokens_total(self) -> int:
        return self.tokens_in + self.tokens_out


class UsageLedger:
    """Append-only collection of usage events tagged like Bedrock AIPs."""

    def __init__(self):
        self._events: list[UsageEvent] = []

    def record(self, **fields) -> UsageEvent:
        ev = UsageEvent(**fields)
        self._events.append(ev)
        return ev

    @property
    def events(self) -> list:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)


# Group by the cost-allocation tag tuple that AIPs carry.
_GROUP_KEYS = ("dept", "team", "app", "data_class", "pack")


def _aggregate(ledger: UsageLedger):
    rows = defaultdict(
        lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
    )
    for ev in ledger.events:
        key = (ev.dept, ev.team, ev.app, ev.data_class, ev.pack)
        r = rows[key]
        r["calls"] += 1
        r["tokens_in"] += ev.tokens_in
        r["tokens_out"] += ev.tokens_out
        r["cost_usd"] += ev.cost_usd
    return rows


def write_chargeback_csv(ledger: UsageLedger, path: str) -> dict:
    """Write the chargeback CSV grouped by AIP tags; return totals."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = _aggregate(ledger)
    totals = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

    header = list(_GROUP_KEYS) + [
        "calls",
        "tokens_in",
        "tokens_out",
        "tokens_total",
        "cost_usd",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for key in sorted(rows.keys()):
            r = rows[key]
            tokens_total = r["tokens_in"] + r["tokens_out"]
            writer.writerow(
                list(key)
                + [
                    r["calls"],
                    r["tokens_in"],
                    r["tokens_out"],
                    tokens_total,
                    f"{r['cost_usd']:.4f}",
                ]
            )
            for k in totals:
                totals[k] += r[k]
        writer.writerow(
            ["TOTAL", "", "", "", ""]
            + [
                totals["calls"],
                totals["tokens_in"],
                totals["tokens_out"],
                totals["tokens_in"] + totals["tokens_out"],
                f"{totals['cost_usd']:.4f}",
            ]
        )
    totals["tokens_total"] = totals["tokens_in"] + totals["tokens_out"]
    return totals


def render_table(ledger: UsageLedger) -> str:
    """Return a compact ASCII chargeback table for live display."""
    rows = _aggregate(ledger)
    lines = []
    hdr = f"{'dept':<16}{'app':<22}{'data_class':<11}{'pack':<12}{'calls':>6}{'tokens':>12}{'cost_usd':>11}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    g_calls = g_tokens = 0
    g_cost = 0.0
    for key in sorted(rows.keys()):
        dept, team, app, data_class, pack = key
        r = rows[key]
        tokens = r["tokens_in"] + r["tokens_out"]
        g_calls += r["calls"]
        g_tokens += tokens
        g_cost += r["cost_usd"]
        lines.append(
            f"{dept:<16}{app:<22}{data_class:<11}{pack:<12}"
            f"{r['calls']:>6}{tokens:>12,}{r['cost_usd']:>11.4f}"
        )
    lines.append("-" * len(hdr))
    lines.append(
        f"{'TOTAL':<16}{'':<22}{'':<11}{'':<12}{g_calls:>6}{g_tokens:>12,}{g_cost:>11.4f}"
    )
    return "\n".join(lines)
