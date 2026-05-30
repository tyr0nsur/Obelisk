# Post-RC Offline ResourceHandle Priority

## Summary

After the core-first RC gate, the highest-ROI offline reversing path is not another broad
FName, GObjects, or UFunction scan for the current binary hash. Those inputs are already
good enough for internal planning. The remaining ResourceHandle blocker is semantic:
`uobject_flags_validity_semantics_unproven`.

The next useful artifact should narrow when `UObject+0x8` flags require fail-closed
handling while keeping `ResourceHandle`, object identity, lookup, mutation, return
override, and UE lifecycle names unpromoted.

## Recommended Candidate-Only Artifact

Build a fresh `obelisk.uobject-flag-policy-report.v1` with:

- `promotion_ready=false`
- `post_callback_resource_handle_ready=false`
- `0x100` treated only as an internal hard-invalid candidate
- `0x4000` treated only as a strict-invalid or mode-dependent candidate

Use the existing bounded offline path:

```bash
python3 scripts/build_uobject_flag_policy_report.py \
  --binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --weak-helper-caller-mode /servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/weak-helper-caller-mode.redacted.json \
  --window weak_helper_reject_0x100=<tmp-window> \
  --window strict_0x4000_behavior=<tmp-window> \
  --window gobjects_backed_0x4000_skip=<tmp-window> \
  --window gc_static_0x100_support=<tmp-window> \
  --output <tmp-output>/uobject-flag-policy-report.redacted.json

python3 scripts/validate_offline_artifact_gate.py \
  --manifest <tmp-output>/uobject-flag-policy-report.redacted.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json > <tmp-output>/gate-consume.json
```

Keep outputs in `/tmp` or another approved offline root for the first pass. Do not write
new runtime/server artifacts and do not use ReflectionScanner, ptrace, gcore, markers, or
server restarts for this step.

## Non-Claims

This does not promote:

- public `ResourceHandle`
- post-callback object lookup
- public object identity
- GObjects promotion
- mutation or return override
- named UE lifecycle flag semantics

If the consume gate fails, treat the artifact as invalid evidence rather than partially
accepted.

## 2026-05-30 Follow-Up Result

A first pass against the existing redacted weak-helper artifact failed closed because the
artifact did not embed caller rows or source provenance. The raw sidecars already existed
under the offline workspace, so the weak-helper report was regenerated in `/tmp` with
provenance and six caller rows, then consumed by a fresh `uobject-flag-policy-report.v1`
also written under `/tmp`.

Result:

- consume gate: accepted
- promote gate: blocked as expected
- promote blockers: `promote_mode_uobject_flag_policy_candidate_only` and
  `promote_mode_manifest_has_non_claims`
- public helper identifier: `weak_helper_flag_policy_candidate`
- public output: no raw helper addresses, raw UE lifecycle names, object indices, serials,
  pointers, or local paths

This is useful internal ResourceHandle evidence because it narrows the lifecycle/flag
policy blocker, but it remains candidate-only. It still does not promote public
`ResourceHandle`, object lookup, identity, mutation, return override, or named UE lifecycle
semantics.
