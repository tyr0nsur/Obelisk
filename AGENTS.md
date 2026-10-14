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
