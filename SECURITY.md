# Security Policy

Obelisk is injected into `ShooterGameServer` with `LD_PRELOAD`. Treat runtime hooks,
plugins, config loading, HTTP endpoints, and memory scanners as security-sensitive.

## Supported Versions

Security review currently targets the `main` branch until the first tagged release.

## Reporting

Please do not publish exploitable details in a public issue. Report security concerns by
opening a private advisory on GitHub when available, or by contacting the maintainers
through the repository owner.

Useful reports include:

- Affected commit or release.
- Server/runtime configuration.
- Minimal reproduction steps.
- Logs with secrets removed.
- Whether a plugin, scanner, wrapper, or core runtime path is involved.

## Scope

In scope:

- Unsafe plugin loading or ABI behavior.
- Crashes or memory corruption reachable through documented runtime paths.
- Config parsing that can expose secrets or write outside the intended config root.
- HTTP-capable plugin designs before they are promoted to stable.

Out of scope:

- Cheats against ARK clients.
- Vulnerabilities in ARK, SteamCMD, LinuxGSM, or third-party services unless Obelisk
  materially worsens the impact.
