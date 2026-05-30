# ResourceHandle Flag Policy Candidate

## Objective

Consolidate the current small-JSON ResourceHandle evidence into a short
`flag-policy-candidate` matrix. This note is deliberately narrow: it uses only the existing
weak-helper caller-mode redacted JSON and the ResourceHandle nonzero readiness JSON, with no
live-server run, GitHub action, binary scan, or new static analysis.

Workflow caveat: this candidate is superseded for current workflow by the 2026-05-30
post-RC, UObject flag-policy, and artifact-identity notes. Keep it as historical evidence
only.

## Environment

- Date: 2026-05-29
- Obelisk commit: `9696863c01598252583de1153288aa75693640c9`
- Runtime posture: no live server, no restart, no marker change, no live path input.
- Evidence scope: existing small offline JSON artifacts only.

## Evidence Inputs

| Input | Path | SHA256 | Scope |
| --- | --- | --- | --- |
| Weak-helper caller mode | `/servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/weak-helper-caller-mode.redacted.json` | `197d40ef0fbc6ec7cc65b8b932bd00f8eeac5c960f43f59f5bbef653e2183d14` | Accepted internal static evidence for mode-dependent helper behavior. |
| ResourceHandle nonzero readiness | `/servidor/ark/workspace-offline/resource-handle-nonzero-revalidation-20260529T060741Z/readiness-redacted.json` | `152adb6641272cb51001033f71a9e43a2495723c766f7dd0136eda0a9435f7dc` | Accepted offline readiness summary for GObjects field coherence and nonzero serial samples. |

## Flag Policy Candidate Matrix

| Policy candidate | JSON evidence | Current interpretation | Promotion status |
| --- | --- | --- | --- |
| `gobjects_serial_membership_ready` | `gobjects_coherent_field_window_proven=true`, `accepted_sample_count=32`, `membership_pass_count=32`, `serial_candidate_nonzero_count=32`, `serial_candidate_missing_count=0` | GObjects field coherence and nonzero serial presence are no longer the primary blocker for an internal handle candidate on this evidence set. | Internal evidence only. |
| `weak_helper_c70_mode_rule_candidate` | Helper `0x1d56c70` has complete direct-call coverage `6/6`; reviewed callers set `sil=1`; nonzero `rax` is the kept-or-valid path; helper rules include `0x100 -> null_always` and `0x4000 -> null_when_sil_zero`. | This is the strongest current flag-policy clue: a mode-dependent pointer-or-null helper can inform a fail-closed internal policy candidate. | Candidate only; UE lifecycle flag names are not promoted. |
| `weak_helper_b60_not_validity_policy` | Helper `0x1d56b60` has complete direct-call coverage `4/4`, but reviewed callers use `sil=0`, `dl=1`, and pairwise boolean comparison mode. | Do not use `0x1d56b60` as proof that `0x100` or `0x4000` directly encode public validity semantics. | Rejected as standalone public validity evidence. |
| `post_callback_lookup_not_ready` | ResourceHandle readiness JSON reports `post_callback_resource_handle_ready=false`; blockers contain `uobject_flags_validity_semantics_unproven`. Weak-helper JSON reports `promotion_gate_ready=false` and remaining blockers including `static_only_evidence`, `no_named_lifecycle_semantics`, `no_rejected_runtime_object_samples`, and `public_resourcehandle_policy_missing`. | The real blocker is flag and lifecycle semantics: when an object must fail closed, whether a serial/index pair can be used after a callback, and which lifecycle states invalidate lookup. | Blocked. Keep `post_callback_resource_handle_ready=false`. |

## Accepted Weak-Helper Workflow Boundary

Accepting the weak-helper polarity workflow means only that bounded, redacted
weak-helper/caller-mode artifacts can narrow the internal `0x100` / `0x4000` flag-policy
candidate for this binary hash. It is not `ResourceHandle` promotion. Keep
`post_callback_resource_handle_ready=false`, do not publish UE lifecycle flag names, and do
not derive public object identity or persistent lookup from this evidence. Promotion still
requires rejected object samples plus an independent, version-matched lifecycle/lookup
contract.

## Result

`FName`, GObjects field coherence, and nonzero serial candidates are not the main remaining
blocker for this ResourceHandle thread. The remaining blocker is semantic: a public or
post-callback `ResourceHandle` policy still lacks named lifecycle semantics, rejected object
examples, and a fail-closed lookup contract backed by more than static/helper-mode evidence.

This note does not promote:

- `ResourceHandle`;
- post-callback lookup;
- mutation;
- return override;
- UE lifecycle flag names;
- public SDK object identity.

`post_callback_resource_handle_ready=false` remains the only safe policy state.

## Commands

```bash
jq . /servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/weak-helper-caller-mode.redacted.json
jq . /servidor/ark/workspace-offline/resource-handle-nonzero-revalidation-20260529T060741Z/readiness-redacted.json
sha256sum \
  /servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/weak-helper-caller-mode.redacted.json \
  /servidor/ark/workspace-offline/resource-handle-nonzero-revalidation-20260529T060741Z/readiness-redacted.json
python3 -m unittest scripts/test_research_doc_guardrails.py scripts/test_secret_guardrails.py
```

## Next Steps

- Keep ResourceHandle work centered on flag/lifecycle semantics, not broader FName/GObjects
  discovery.
- Next cheap experiment: build a table from the existing weak-helper caller-mode JSON that
  lists each reviewed `0x1d56c70` direct caller, the constant masks it checks, the `sil`
  mode, and the caller's keep/null branch. The table should test only the narrow policy
  claim already implied here: `0x100` is a fail-closed reject mask for this helper mode,
  while `0x4000` cannot be named as a universal reject mask without a `sil=0` caller in
  the same helper family. Emit this as `caller_rows`, an internal name-free table of
  reviewed static caller windows only; it is policy-candidate evidence, not a
  `ResourceHandle` unlock.
- Require rejected object samples and named lifecycle meaning before any post-callback
  handle policy changes.
- Treat additional serial/GObjects packs as strengthening internal evidence only unless
  they also resolve the lifecycle blocker.

Success criterion: every reviewed `0x1d56c70` caller agrees with the same keep/null rule
for `0x100` under `sil=1`, and no row requires assigning a public UE lifecycle name to the
flag. This would narrow `uobject_flags_validity_semantics_unproven` to missing rejected
runtime object samples and missing public lifecycle names, without promoting post-callback
lookup.

Failure criterion: any reviewed caller contradicts the `0x100` fail-closed interpretation,
or the table needs an unproven lifecycle-name assumption to explain the branch. In that
case, keep `uobject_flags_validity_semantics_unproven` fully blocking and do not derive a
ResourceHandle lookup policy from the helper evidence.
