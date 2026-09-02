# Support model — honest status

*Read with `NOT-CLAIMS.md`. This page states plainly what support does and does not exist today, so no
reviewer mistakes a reference accelerator for a supported product.*

## Today (reference accelerator)

There is **no support model**: no SLA, no hotfix path, no managed release train, no on-call, no
security-patch cadence, and no owning support team. This repository is a reference architecture and
implementation accelerator. AWS Support does not cover this code (it is not an AWS service). Adopters
fork it, review it, and own what they run. This is the correct posture for discovery, architecture
workshops, envisioning, and scoped pilots — and it is the reason "platform for customers, plural" is
**not** claimed today.

## What "customers, plural" would require (roadmap gate)

Before Aegis can honestly be offered to multiple customers as a supported product, the following must
exist and be real (not asserted):

- **Versioned releases** with a published changelog and upgrade path (the `governed-core` pinned wheel
  is the mechanism; a release cadence and deprecation policy are not yet defined).
- **Security-patch cadence** with a stated response time for CVEs in dependencies and in the platform.
- **A hotfix path** and a defined **SLA** (response/restore targets) for named severity levels.
- **An owning team** accountable for the above, with escalation and on-call.
- **Support tooling**: intake, ticketing, and a status/advisory channel.

Until each of these is real, support stays an `out_of_repo` item in `MATURITY.yaml`, and the public
story is the **per-customer engagement accelerator** (single-tenant, delivered and hardened in the
customer's own account), not a multi-tenant supported SaaS.

## Interim: per-customer engagement support

In an engagement, support is scoped in the SOW (`Aegis-Pilot-SOW-Template.docx`): the delivery team
supports the specific pilot deployment for the pilot term, in the customer's account, under agreed terms.
That is engagement support, not a product SLA — and it is described as such.
