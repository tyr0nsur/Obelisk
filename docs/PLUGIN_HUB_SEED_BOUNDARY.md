# Plugin Hub Seed Boundary

Plugin Hub work is parked until the complete Obelisk SDK blocker chain is resolved.
Read this file only as archived boundary guidance for future Plugin Hub examples or module
categories; it is not an active work queue before SDK completion.

Plugin Hub seeds are not the Obelisk v1 SDK. A seed can teach a narrow, reviewed pattern
without promoting the blocked gameplay/API surface that a full plugin ecosystem will
eventually need.

## Required Labels

Every proposal must use one label:

- `release-supported seed`: uses only lifecycle/config/logging, descriptor/catalog reads, or
  process-local timers from the current public C ABI.
- `experimental pattern`: passively consumes copied `ChatMessageEvent` or
  `GameplayPolicyEvent` data as a labeled example, without production support.
- `blocked backlog`: depends on a v1 blocker or unpromoted gameplay/module surface.

Seed README, package metadata, and public seed docs must declare exactly one support tier
with `Support tier: <tier>`. Review must fail if that text claims v1 readiness,
ArkApi/AseApi compatibility, commands, permissions, identity, send-chat/replies, mutation,
storage, inventory, or structure support outside the declared tier.

## Parked Release-Supported Seed Classes

When Plugin Hub work resumes after SDK completion, release-supported seeds remain limited
to:

- lifecycle, config, logging, metadata, and shutdown hygiene;
- descriptor/catalog consumers;
- process-local owner-token timers.

These seeds must build against the installed SDK component and avoid private Obelisk
headers, raw UE pointers, raw `ProcessEvent` params, ArkApi implementation patterns,
mutation, return override, object lookup, and cross-process runtime state.

## Experimental Patterns

Copied chat and copied gameplay-policy examples may be useful patterns, but they do not
promote commands, permissions, sender identity, replies, send-chat, moderation, blocking,
Inventory SDK, StructureEvents SDK, policy enforcement, mutation, or return override.

## Blocked Backlog

Keep these as design notes, evidence plans, or guardrails until their promotion gates
exist: commands, permissions, RCON/operator ingress, storage/webhooks, economy, shops,
kits, homes, teleport, safe zones, inventory/items mutation, structures, dinos, tribes,
missions, transfers, buffs, player services, persistence, and gameplay/module timers.

## Demand Dictionaries

ArkApi/AseApi names and local `NextGenPlugins` clones can justify priority and inform
familiar category/workflow shape. They do not provide compatibility, source clearance,
ABI, schemas, parsers, constants, offsets, layouts, vtables, control flow, return
semantics, or implementations. Obelisk surfaces must be rebuilt through Linux-native
reflection evidence, copied C ABI contracts, and runtime safety gates.

## v1 Rule

No seed, installed example, package-shape check, copied chat notification, copied policy
event, or Plugin Hub document is evidence that Obelisk v1 is complete. A v1 claim is
allowed only when `docs/public_sdk_surfaces.json` and the v1 release gate allow it.
