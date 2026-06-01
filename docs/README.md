# Obelisk Documentation

Use this index to enter the project from the right angle. Obelisk is a Linux runtime and
C SDK track for ARK: Survival Evolved server modding; public docs should stay focused
on contributors, plugin authors, operators, and reproducible research.

## Contributor

- `../README.md`: project overview, current status, and quick start.
- `../CONTRIBUTING.md`: local development, review expectations, and contribution flow.
- `STATUS.md`: current release scope and known limitations.
- `RELEASE.md`: release readiness gates and RC scope.
- `SDK_V1_COMPATIBILITY.md`: SDK v1 compatibility target, promoted surfaces, and exclusions.
- `ARCHITECTURE.md`: runtime and SDK architecture.
- `OFFLINE_ARTIFACT_PACKS.md`: contributor runbook for normalized offline evidence packs.

## Plugin Author

Start with the plugin architecture, installed examples, SDK v1 compatibility map, and
public SDK surface inventory when deciding what a plugin can honestly build today. Plugin
Hub documents are parked planning references until the complete SDK blocker chain is
resolved. The current installed-SDK foundation examples, not active Plugin Hub work, are
lifecycle/config/logging, descriptor/catalog consumers, and process-local timers. Copied chat parsers and
`GameplayPolicyEvent` auditors are experimental pattern examples only, not production
command/chat/policy SDKs. Anything that needs identity, lookup, mutation,
replies/send-chat, permissions, storage, RCON, inventory/item APIs, or structure
enforcement stays blocked until promoted.

- `PLUGIN_ARCHITECTURE.md`: plugin lifecycle, ABI rules, examples, and promotion gates.
- `public_sdk_surfaces.json`: machine-readable SDK surface inventory and v1 release boundaries.
- `oBaseEvents.md`: first-party reference plugin notes.
- `../examples/README.md`: installed-SDK consumer examples, including
  `sdk_minimal_plugin`, `sdk_descriptor_catalog`, and `sdk_timer_plugin`.
- `../include/obelisk/ObeliskApi.h`: public C ABI header.
- `PLUGIN_HUB_FOUNDATION_V1.md` and `PLUGIN_HUB_CAPABILITY_MATRIX.md`: archived planning
  references only; do not use them as the active SDK build queue.

## Operator

- `INSTALL.md`: install layout and runtime configuration.
- `OPERATOR_CLI.md`: operator commands and status checks.
- `SERVER_RESTORE.md`: recovery notes for ARK server configuration drift.
- `VERSIONING.md`: version and compatibility policy.

## Researcher

- `research/README.md`: research note format and index.
- `public_gameplay_events.json`: promoted and RC gameplay-event scope.
- `archive/README.md`: archived historical plans that should not drive current work.
