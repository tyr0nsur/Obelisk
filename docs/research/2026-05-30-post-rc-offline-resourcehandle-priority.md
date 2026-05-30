# Post-RC Offline ResourceHandle Priority

## Summary

After the core-first RC gate, the highest-ROI offline reversing path is not another broad
FName, GObjects, or UFunction scan for the current binary hash. Those inputs are already
good enough for internal planning. The remaining ResourceHandle blocker is semantic:
`uobject_flags_validity_semantics_unproven`.

The next useful artifact should narrow when `UObject+0x8` flags require fail-closed
handling while keeping `ResourceHandle`, object identity, lookup, mutation, return
override, and UE lifecycle names unpromoted.

Current state: use `InternalUObjectRevalidationCandidate` as the internal design label
for this work. Do not call it `ResourceHandle` in code, APIs, or plugin-facing docs until
post-callback lifetime, reuse, privacy, and rejection semantics are proven by a separate
promotion gate.

## Recommended Candidate-Only Artifact

Build a fresh `obelisk.uobject-flag-policy-report.v1` with:

- `promotion_ready=false`
- `post_callback_resource_handle_ready=false`
- `0x100` treated only as an internal hard-invalid candidate
- `0x4000` treated only as a strict-invalid or mode-dependent candidate
- no mutation-window-only evidence treated as lookup, identity, lifecycle, or mutation
  safety

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
- mutation safety or mutation APIs from flag transition windows
- `0x4000` as a universal rejection flag outside reviewed helper modes

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

## Fail-Closed Contract Clarification

Any future internal revalidation prototype must remain frame-local and fail closed. The
only acceptable internal shape before promotion is:

- Name: `InternalUObjectRevalidationCandidate`, not `ResourceHandle`.
- Lifetime: valid only inside the same hook/callback frame for copied-data decisions; it
  must reject post-callback lookup.
- Inputs: internal index/serial evidence plus binary SHA and consumed artifact identity;
  never expose UE pointers, GObjects indices, serials, class/name/outer values, or lookup
  tokens to plugins.
- Acceptance checks: supported SHA, accepted consume gate, coherent GObjects evidence,
  in-bounds chunk/item, readable `FUObjectItem`, nonzero serial, serial match at the
  current candidate slot, non-null `UObject*`, and plausible membership.
- Flag policy: reject `UObject+0x8 & 0x100`; reject `UObject+0x8 & 0x4000` by default.
  Tolerating `0x4000` requires a specific reviewed helper mode proving that mode; absence
  of that proof is rejection.
- Output: a copied boolean/reason or Obelisk-owned copied data only. No identity,
  persistent handle, public lookup, mutation, return override, or raw UE object escape.

`mutation_windows` or flag transition reports may show where bits are set or cleared, but
they do not prove lookup safety, mutation authority, post-callback lifetime, public
validity semantics, or a public lifecycle name. Keep `promotion_ready=false`,
`public_resource_handle_ready=false`, and `post_callback_resource_handle_ready=false`
until a separate promotion contract supplies negative runtime samples, lifecycle/reuse
policy, and privacy-safe lookup semantics.

## Current Canonical Input

Use the durable rich-provenance refresh as the current canonical internal static input:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/
```

The pack now includes `artifact-pack.manifest.json` and `SHA256SUMS`. Its consume gate is
accepted, its promote gate remains blocked, and the manifest explicitly keeps public
ResourceHandle, public GObjects, object identity, post-callback lookup, lifecycle names,
mutation, return override, and SDK exposure as non-claims.

Superseded inputs should stay historical only:

- `/servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-static-negative-regenerated-20260529T1910Z/`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-semantic-decompiler-20260529T155658Z/uobject-flag-semantic-correlation.json`

Do not rerun broad FName, GObjects, or core scans for this path unless the binary hash
changes or new evidence contradicts the canonical pack.
