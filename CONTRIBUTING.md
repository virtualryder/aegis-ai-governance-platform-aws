# Contributing to Aegis

Thanks for your interest in improving Aegis. Aegis is a governance control plane
for high-sensitivity agentic workloads, so contributions are held to a high bar:
the point of the platform is that **mandatory controls fail closed**, and every
change has to preserve that invariant.

Please read this document, `SECURITY.md`, and
[`governance/onboarding/MINIMUM-BAR.md`](governance/onboarding/MINIMUM-BAR.md)
before opening a pull request.

## Ground Rules

1. **Every agent must pass the minimum bar.** Any new or modified agent manifest
   must satisfy every point of
   [`governance/onboarding/MINIMUM-BAR.md`](governance/onboarding/MINIMUM-BAR.md)
   (identity, least-privilege grants, purpose limitation, data-class isolation,
   consent, residency, budget, human gate, fail-closed masking, immutable
   audit). A change that lets an agent skip a mandatory control will be rejected.
2. **All mandatory controls fail closed.** If a control cannot be affirmatively
   satisfied — unregistered tool, masking unavailable, policy cannot evaluate,
   audit write fails on a sensitive/consequential call — the correct behavior is
   **DENY**, never a silent allow. Do not introduce fail-open paths.
3. **No secrets, no live credentials, no customer data** in the repo, tests, or
   fixtures. The offline modules are stdlib-only and must stay network-free.

## Branch Model

We use a lightweight trunk-based flow:

- `main` is always releasable and protected. Direct pushes are not allowed.
- Branch off `main` using a descriptive, prefixed name:
  - `feat/<short-description>` — new capability
  - `fix/<short-description>` — bug fix
  - `docs/<short-description>` — documentation only
  - `chore/<short-description>` — tooling, CI, refactors
- Open a pull request back into `main`. At least one CODEOWNER review is
  required (see `.github/CODEOWNERS`), and CI must be green.
- Keep PRs small and focused. Rebase on `main` rather than merging it back in.

## Before You Open a PR

Run these locally from the repo root and make sure they pass:

```bash
# 1. The full governance control-plane acceptance demo must exit 0.
python3 demo/clean_account_acceptance.py

# 2. The fail-closed regression tests must pass.
python3 demo/test_fail_closed.py

# 3. Lint every CloudFormation template.
pip install cfn-lint
cfn-lint infra/cloudformation/*.yaml
```

CI runs the same steps (see `.github/workflows/ci.yml`) plus non-blocking
`bandit` and `checkov` scans. A PR that breaks the acceptance demo or the
fail-closed tests will not be merged.

## Commit Messages — Conventional Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`.
Examples:

```
fix(gateway): deny unregistered tools instead of returning ok (fail closed)
feat(policy): add FERPA consent clause for edu data class
docs(security): document ATO / pen-test status
```

Breaking changes must include a `!` after the type/scope
(e.g. `feat(policy)!: ...`) or a `BREAKING CHANGE:` footer.

## Reviews and Merging

- Squash-merge is preferred so `main` history reads as one Conventional Commit
  per change.
- Update `CHANGELOG.md` under the `Unreleased` section for any user-visible or
  security-relevant change.
- Security-sensitive changes should reference the fail-closed principle in the
  PR description and explain how the change preserves default-deny.

By contributing you agree that your contributions are licensed under the
Apache License 2.0 (see `LICENSE`).
