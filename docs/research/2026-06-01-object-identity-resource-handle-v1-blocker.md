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
