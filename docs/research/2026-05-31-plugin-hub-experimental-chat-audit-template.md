# Plugin Hub Experimental Chat Audit Template

Date: 2026-05-31

Status: product-planning note; experimental pattern only; not release-supported, not a
command SDK, and not v1 completion evidence.

## Finding

After the three release-supported installed-SDK seed templates (`sdk_minimal_plugin`,
`sdk_descriptor_catalog`, and `sdk_timer_plugin`), the next useful experimental template is
a passive copied-chat audit digest.

Candidate name: `sdk_chat_audit_digest`.

The template would teach plugin authors how to consume a copied callback safely without
claiming command, moderation, or response capability.

## Intended Scope

- Subscribe to copied `ChatMessageEvent`.
- Validate struct size, capability bit, owner token, and callback pointers.
- Keep only bounded local counters: message count, send-mode count, payload-size buckets,
  malformed event count, and optional periodic local digest via process-local timer.
- Redact or avoid storing raw chat text.
- Demonstrate cleanup of callback and timer handles during shutdown.

## Explicit Non-Claims

- Not release-supported.
- No player/sender identity.
- No command router or command parsing contract.
- No permissions/admin.
- No replies, send-chat, broadcast, announcements, or moderation.
- No storage, persistence, or cross-instance correlation.
- No ArkApi/AseApi compatibility or porting claim.
- No SDK v1 completion evidence.

## Rationale

Chat, announcements, MOTD, RCON-adjacent tooling, and command-style plugins are common
demand signals, but almost all useful command behavior is blocked behind identity,
permissions, and a copied response path. A passive audit digest lets authors practice the
safe copied-callback pattern without weakening those blockers.
