# Object Identity and ResourceHandle v1 Blocker

## Summary

The SDK map already excludes raw UE pointers, lookup, and `ResourceHandle` from many
surfaces, but object identity is a cross-cutting blocker and should be treated as its own
SDK design lane before any public API relies on post-callback object correlation.

This is planning guidance only. It adds a `post-v1` completion blocker to
`public_sdk_surfaces.json`, does not promote an object identity API, and does not change
v1 completion status or stable claim eligibility.

## Why It Matters

Object identity affects multiple high-demand SDK families:

- structures: ownership, limits, build placement, no-collision policy;
- inventory/items: item handles, mutation, rewards, kits;
- dinos and tribes: ownership, policy, colors/cosmetics, carry rules;
- buffs/status and missions/transfers: event correlation across callbacks;
- economy/mobility: rewards, homes, teleport, safe zones, and area policy.

Without a proven lifecycle contract, a copied callback cannot safely expose a stable object
handle, lookup key, or post-callback reference. Current public surfaces must continue to
use copied/redacted scalar data and metadata descriptors only.

## Required Future Evidence

Before any public object identity/lookup lane exists, Obelisk needs:

- lifecycle and invalidation semantics for UObject-backed identities;
- reuse/wraparound behavior and negative samples for stale objects;
- callback-scope vs post-callback validity rules;
- privacy and redaction boundaries for owner/player/tribe-related identity;
- owner-token scoped lookup/cleanup policy if lookup is ever exposed;
- ABI layout and installed-SDK consumer coverage;
- explicit exclusions for raw UE pointers, raw params, FName/GObjects indices, and direct
  mutation.

Until then, `ResourceHandle`, object lookup, and persistent object identity remain blocked
across structures, inventory, dinos, tribes, buffs, missions, transfers, economy, mobility,
and area-policy work.

## Next Offline Cohort

The next useful offline-only package is a negative-sample cohort for zero-serial
`FUObjectItem` entries from the existing two cores. Current redacted serial scans show a
clear gap: `rejected_sample_count=0`, while both cores include many serial-zero entries.

Use existing offline artifacts only:

- `/servidor/ark/workspace-offline/resource-handle-nonzero-revalidation-20260529T060741Z/readiness-redacted.json`
- `/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/vanilla-serial-scan.redacted.json`
- `/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/second_source-serial-scan.redacted.json`
- `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
- `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`

The candidate cohort should record object items with non-null object pointers and
`FUObjectItem+0x8 == 0` as stale/invalid handle evidence, contrasted with known positive
samples such as index `50834` with serial `1001`. This still does not prove UObject flag
validity semantics, runtime reuse/wraparound behavior, public lookup, or `ResourceHandle`
promotion.

## 2026-06-01 Zero-Serial Negative Cohort Candidate

Added `scripts/build_resource_handle_zero_serial_negative_samples.py` to make the next
negative-sample package reproducible from the two copied cores without broad rediscovery.
The helper scans index order only through the known positive anchor by default
(`--anchor-index 50834`) and treats `FUObjectItem+0x8` as a candidate `uint32` serial
field. It emits candidate-only JSON with `status=candidate_blocked`; it does not expose
lookup, mutation, public `ResourceHandle`, or runtime lifecycle semantics.

Command run:

```bash
python3 scripts/build_resource_handle_zero_serial_negative_samples.py \
  --core vanilla=/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --core second_source=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --core-sha256 vanilla=56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb \
  --core-sha256 second_source=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78 \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --anchor-index 50834 \
  --negative-limit 8
```

Result: `deterministic_negative_cohort=true` for both sources. Each source scanned
`50835` indices, saw `50835` non-null candidate UObjects, collected the first 8
zero-serial negative samples, and found the positive anchor at index `50834` with
serial `1001`.

| source | core sha256 | fname table | zero-serial cohort | positive anchor |
| --- | --- | --- | --- | --- |
| vanilla | `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb` | `0x5a94660` | indexes `0..7`, all `membership=candidate-uobject`, `item_dword_0x8=0` | index `50834`, `LinkerLoad`, `item_dword_0x8=1001`, `item_dword_0xC=116` |
| second_source | `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78` | `0x3dff0660` | indexes `0..7`, all `membership=candidate-uobject`, `item_dword_0x8=0` | index `50834`, `LinkerLoad`, `item_dword_0x8=1001`, `item_dword_0xC=114` |

The first 8 zero-serial names/classes are stable across both cores:
`/Script/CoreUObject` (`Package`), `Object` (`Class`), `/Script/ShooterGame`
(`Package`), `AhoCorasickMatch` (`Class`), `/Script/Engine` (`Package`), `Actor`
(`Class`), `Controller` (`Class`), and `/Script/AIModule` (`Package`).

Remaining blockers are unchanged: this cohort is useful negative evidence for a
fail-closed serial contract, but it does not prove stale-object lifecycle behavior,
serial reuse or wraparound, UObject flag validity semantics, callback-scope validity,
owner-token cleanup, public lookup, or ABI-safe `ResourceHandle` promotion.
