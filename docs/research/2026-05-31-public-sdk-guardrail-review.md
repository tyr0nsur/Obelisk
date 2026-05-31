# Public SDK Guardrail Review: Planning/Internal Module Evidence

Date: 2026-05-31
Scope: `agent-skills/obelisk-github-research-workflow/SKILL.md` and
`agent-skills/obelisk-continuous-learning/SKILL.md` only.

## Finding

The current guardrails partially prevent accidental public SDK promotion for reflected
gameplay/module surfaces, but they do not explicitly block public messaging that
describes Mission, Dino, Buff, or Structure planning-only work or internal evidence as
public SDK availability.

Observed protections:

- `obelisk-github-research-workflow` requires reflected gameplay/module promotion PRs to
  name promoted second-source target sets explicitly.
- `obelisk-github-research-workflow` says runtime-observer summaries are review artifacts
  only, and module-level field aggregates are not promotable layouts.
- `obelisk-continuous-learning` requires incomplete evidence packs to remain marked as
  `hypothesis` or `research-candidate`, not `fact`.
- Community updates are gated and must not include speculative reversing notes or routine
  internal status.

Gap:

- Neither reviewed skill states the release/public-communication invariant directly:
  planning-only module names, internal research notes, observer summaries, field
  aggregates, hypotheses, research candidates, or second-source gaps must not be
  announced as public SDK surface for Mission, Dino, Buff, Structure, or adjacent module
  families.

## Recommended Guardrail

Add a release/public-SDK wording rule, preferably backed by
`scripts/test_public_sdk_guardrails.py`, that rejects public docs or announcement text
claiming Mission, Dino, Buff, or Structure SDK availability unless the same change names
the promoted second-source target set and passes the release promotion gate.

Suggested rule shape:

- Allowed: "planning", "research-candidate", "internal evidence", "observer review",
  "not public SDK".
- Blocked: module-family wording that implies public SDK availability, support,
  release, beta readiness, or documented API surface without explicit promotion evidence.

## Validation Suggested

Run the existing public SDK guardrail test, if present, after adding explicit fixtures for
Mission, Dino, Buff, and Structure wording. The test should include at least one blocked
public-announcement example and one allowed internal/planning-only example per module
family.

## Adoption

The follow-up integration tightened `scripts/test_public_sdk_guardrails.py` so public
docs/examples reject positive claims for Mission, Dino, Buff, and Structure SDK/API/surface
availability unless the surrounding wording is explicitly blocked, internal, planning-only,
or otherwise non-promotional. `obelisk-github-research-workflow` now carries the matching
lead rule for docs, release notes, community updates, and Plugin Hub planning.
