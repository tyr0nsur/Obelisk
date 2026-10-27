# Current Obelisk development

Read `docs/REBOOT_2026-10-13.md` for the current operator-requested scope.
The implemented prototype and pending client acceptance are described in
`docs/OPING_PROTOTYPE.md`; preserve the distinction between startup and gameplay.

The operator now explicitly targets the public ASE branch for an Epic Games
361.8 client, with Steam/Epic support. Migrate the private adapter to the actual
public-branch Linux executable; crossplay does not prove branch compatibility.
The preaquatica installation and duplicate recovery/build artifacts must be
removed once their replacements validate. Keep one active installation and
build, the original project ZIP, and useful evidence/tools. Do not update or
remove another production service as part of this cleanup.

The active goal is a small native Linux plugin demonstrated in ARK: `/ping`
with a reply to the originating session. Preserve the recovered work and reuse
its useful runtime pieces. Historical planning and certificate checks remain
historical context; they are not prerequisites for developing this prototype.
Do not use document-only tests or SDK completion ratios as evidence of gameplay.

The operator now requests an ObeliskNative suite with equivalent useful ASE
ArkApi functionality and fast migration. Build original native implementations,
compare observable contracts using primary references and preserve license
notices for any reused component. Windows DLL ABI compatibility is not implied.
The source stays private; the public repository contains presentation and metrics.
The operator explicitly requests gameplay parity across the ASE ArkApi ecosystem
with original ObeliskNative implementations and no copied upstream plugin or
framework source. Use published documentation and observable behavior to specify
contracts; do not incorporate upstream implementation code. Freeze the researched
catalog by date/resource ID, track missing documentation separately, and measure
commands, permissions, limits, persistence and failure behavior per feature.
Implemented foundations and static native proofs do not establish full parity.
Historical restrictions on new seed plugins or using ArkApi as a compatibility
target are superseded by this explicit scope. Preserve exact-command legacy
behavior; argument matching must be opt-in. Permission/economy storage can be
developed privately, but must not turn observed IDs into authenticated accounts
or advertise game actions without a verified native binding.

The sole current test server is in `/servidor/ark/obelisk-lab/server`, public
Steam build 21241282, native dedicated-server version 361.7. Its actual SHA256 is
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
The private native adapter is verified for that executable. The previous
`951a5977...` preaquatica installation has been removed. Historical reflection
scanners/layouts remain disabled despite the archive/public hash coincidence;
verify each feature from the executable and specific runtime observations.

Keep UE pointers and layouts in the private Linux adapter. Public plugin data
should have documented lifetimes. The initial command milestone is demonstrated;
the operator now explicitly requests safe plugin start/pause/resume/stop/reload.
Keep native hooks resident. Plugin unloading requires cooperative opt-in,
closed admission, drained callbacks/cleanup and a fresh load generation; retain
the library on failure. Worker-thread timers must not call UE gameplay functions.

Use focused build/tests and recorded runtime evidence. The first required
gameplay acceptance test needs a real client: command, targeted reply,
two-player distinction, and disconnected-session rejection. Do not infer it
from a timer, injection, static decompilation, or fixture success.

# Current ecosystem integration (27 October 2026)

The operator now requests the whole ecosystem under the ObeliskNative brand:
Runtime, Hub, Panel and versioned Artifacts, with a proposed freemium offer.
Reuse the recovered FlowArk source in apps/flowark; legacy paths/variables are
compatibility details. Current scope and acceptance are in
docs/OBELISKNATIVE_ECOSYSTEM.md and docs/ECOSYSTEM_VALIDATION_2026-10-27.md.
Keep the 157 external references distinct from six implemented native modules.
The local panel is separate from the stopped ARK lab; configured RCON is not
verified connectivity. Never infer authenticated Steam/Epic identity from an
observed native ID. Signed experimental artifacts do not establish gameplay
acceptance and must not activate a running server automatically.
