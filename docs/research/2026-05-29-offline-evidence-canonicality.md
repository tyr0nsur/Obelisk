# Offline Evidence Canonicality

## Objective

Record which copied-offline artifacts should be treated as canonical evidence, historical
negative evidence, or duplicated local reproductions. This prevents future rounds from
using stale readiness files as promotion inputs.

No files under `/servidor/ark` were edited or deleted for this note.

## Canonical ResourceHandle Posture

`/servidor/ark/workspace-offline/resource-handle-revalidation-20260529/readiness-redacted.json`
is historical negative evidence. It still records useful blockers, but its
`zero_or_missing_fuobjectitem_serial_candidates` result is superseded by the later broad
serial scan.

`/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529` is the current
serial-only evidence. It supports `FUObjectItem+0x8` as an internal serial-backed field
for the current binary hash, but it does not prove public `ResourceHandle` readiness,
lifetime/reuse behavior, post-callback validity, or `UObject+0x8` flag semantics.

Public `ResourceHandle` remains blocked by:

- `uobject_flags_validity_semantics_unproven`
- lifetime/reuse behavior not proven
- no accepted negative samples for `UObject+0x8` masks `0x100` / `0x4000`
- no public ABI, privacy, lifecycle, or SDK consumer gate

## Canonical GObjects Evidence

Use this durable pack as the current canonical static/internal GObjects evidence:

```text
/servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z
```

Its static manifest is internal-only evidence. It does not promote public GObjects,
object identity, `ResourceHandle`, mutation, or return override behavior because
`promotion_gate.ready=false` with `static_only_evidence`.

The following GObjects reconciliation reports are duplicate pairs and should not be
counted as independent evidence:

- `gobjects-reconcile-second-source-20260529T034447Z/gobjects-reconciliation.json`
- `gobjects-reconcile-minimal-second-source-20260529T034612Z/gobjects-reconciliation.json`

and:

- `fuobjectitem-reconciliation-json-20260529T153000Z/gobjects-reconciliation.json`
- `gobjects-fuobjectarray-durable-pack-20260529T051759Z/core-reconciliation/gobjects-reconciliation.json`

Use the copy inside the durable pack when citing the second pair.

## Dry-Run And Scan-Only Inputs

`/servidor/ark/workspace-offline/minimal-second-source-intake-20260529T030027Z/plan.json`
is a plan/scan-only artifact. It is not an executed readiness report and must not be cited
as accepted FName, GObjects, or UFunction promotion evidence.

## Heavy Local Reproductions

Large `ShooterGameServer.objdump`, `ShooterGameServer.strings.txt`, and static xref JSON
files may exist in multiple packs. Treat those as local reproductions tied to the same
binary hash unless the manifest or provenance sidecar proves that a specific copy is the
intended evidence input.

Do not delete large raw cores or binaries merely because they are duplicated. Prune only
after a separate storage decision records which canonical manifests and research notes
replace the duplicate.

