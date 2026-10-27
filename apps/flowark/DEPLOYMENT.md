# FLOWARK Dashboard Deployment Notes

## Runtime State

Do not commit runtime JSON, logs, secrets, or `node_modules`.

The dashboard keeps mutable state in `server/data/*.json` by default. For production, set `DASHBOARD_DATA_DIR` to a persistent directory outside the git checkout, such as `/var/lib/flowark-dashboard`, and copy `server/data/nodes.example.json` as a starting point for `nodes.json`.

Recommended production paths:

```bash
/opt/flowark-dashboard              # git checkout or release bundle
/etc/flowark-dashboard/dashboard.env
/var/lib/flowark-dashboard          # admins, audit, nodes, tasks, bans, settings
/var/log/flowark-dashboard          # app stdout/stderr when using the systemd unit
```

## Required Production Environment

Set at minimum:

```bash
NODE_ENV=production
HOST=127.0.0.1
JWT_SECRET_KEY=<32+ random characters>
CORS_ORIGINS=https://ark.example.com
TRUST_PROXY_HOPS=1
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
HTTP_REQUEST_TIMEOUT_MS=30000
HTTP_HEADERS_TIMEOUT_MS=10000
HTTP_KEEPALIVE_TIMEOUT_MS=5000
RCON_CONNECT_TIMEOUT_MS=5000
RCON_COMMAND_TIMEOUT_MS=5000
GAMEDIG_TIMEOUT_MS=5000
DISCORD_WEBHOOK_TIMEOUT_MS=3000
```

For first login only, set:

```bash
DASHBOARD_BOOTSTRAP_USERNAME=<owner username>
DASHBOARD_BOOTSTRAP_PASSWORD=<long one-time password>
```

Remove `DASHBOARD_BOOTSTRAP_USERNAME` and `DASHBOARD_BOOTSTRAP_PASSWORD` after the owner account is created.
Production startup rejects known placeholder values for `JWT_SECRET_KEY` and `DASHBOARD_BOOTSTRAP_PASSWORD`; replace every example value before enabling the service.
On the first production startup, the service fails closed if no admin exists and the bootstrap username/password pair is missing or incomplete.

## Build And Install

Create a dedicated service account and install dependencies/build artifacts:

```bash
sudo useradd --system --home /var/lib/flowark-dashboard --shell /usr/sbin/nologin flowark
sudo mkdir -p /opt/flowark-dashboard /etc/flowark-dashboard /var/lib/flowark-dashboard /var/log/flowark-dashboard
sudo chown -R flowark:flowark /var/lib/flowark-dashboard /var/log/flowark-dashboard

cd /opt/flowark-dashboard/server
npm ci --omit=dev

cd /opt/flowark-dashboard/client
npm ci
npm run build
```

Prepare runtime data and environment:

```bash
sudo install -o root -g root -m 0600 /opt/flowark-dashboard/deploy/env/dashboard.env.example /etc/flowark-dashboard/dashboard.env
sudo install -o flowark -g flowark -m 0640 /opt/flowark-dashboard/server/data/nodes.example.json /var/lib/flowark-dashboard/nodes.json
sudo install -o flowark -g flowark -m 0640 /opt/flowark-dashboard/server/data/global_settings.example.json /var/lib/flowark-dashboard/global_settings.json
sudo editor /etc/flowark-dashboard/dashboard.env
sudo /opt/flowark-dashboard/deploy/check-production-env.sh /etc/flowark-dashboard/dashboard.env
```

`dashboard.env` must remain `0600` because it contains the live `JWT_SECRET_KEY` and may temporarily contain first-run bootstrap credentials. It must use the real HTTPS origin, a fresh 32+ character `JWT_SECRET_KEY`, and runtime ARK paths that the `flowark` user can read or write. The HTTP timeout defaults are conservative for nginx reverse-proxy deployments; RCON/GameDig timeout defaults bound slow ARK probes and should only be raised when a known host/network condition requires it.

For plugin runtime inventory, set these optional paths if they differ from the defaults:

```bash
ARK_SCRIPT_ROOTS=/servidor/ark
ARK_CONFIG_ROOTS=/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer
ARK_LOG_ROOTS=/servidor/ark/serverfiles/ShooterGame/Saved/Logs
PLUGIN_MANAGER_OBELISK_ROOT=/servidor/ark/obelisk
PLUGIN_MANAGER_ARKAPI_ROOT=/servidor/ark/ArkApi
```

`nodes.json` is validated against `ARK_SCRIPT_ROOTS`, `ARK_CONFIG_ROOTS`, and `ARK_LOG_ROOTS` at startup. These are comma-separated root allowlists. Any node whose script, INI paths, or log path escapes those roots is ignored, preventing a bad runtime config from executing or editing arbitrary host files.

The dashboard currently treats Obelisk as the Linux ArkApi-equivalent runtime: it can inventory installed `.so` plugins, plugin config directories, per-instance markers, and recent `Obelisk.log` output. It only writes a small allowlist of Obelisk instance marker files and does not upload plugin binaries, restart servers, or execute runtime tooling.

The systemd template keeps `/servidor/ark` read-only by default and grants write access only to the known mutable paths used by the panel:

- ARK config INI directory.
- `AllowedCheaterSteamIDs.txt`.
- ARK saved logs, only for log clearing if enabled.
- LGSM config root used by the file manager.
- Obelisk per-instance marker state.

If your deployment uses different paths, update both `dashboard.env` and the `ReadWritePaths=` entries in the unit. Do not grant write access to the whole ARK install tree unless you explicitly accept that a dashboard compromise can modify server binaries, plugin binaries, runtime libraries, and saved data.

The unit also drops Linux capabilities, uses a restrictive `UMask=0077`, hides host devices, isolates temporary and mount namespaces, blocks hostname/clock/kernel/control-group mutation, prevents namespace/SUID/real-time/personality abuse, removes IPC objects on exit, and restricts system-call architectures to the native ABI. It intentionally does not enable `MemoryDenyWriteExecute` because Node/V8 and native modules may require executable memory for normal runtime behavior.

## systemd

The service template is in `deploy/systemd/flowark-dashboard.service`.

```bash
sudo cp /opt/flowark-dashboard/deploy/systemd/flowark-dashboard.service /etc/systemd/system/flowark-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now flowark-dashboard
sudo systemctl status flowark-dashboard
```

The app exposes a minimal unauthenticated healthcheck at `/healthz` and `/api/health`. It returns only `status` and uptime, does not set dashboard cookies, uses `Cache-Control: no-store`, returns JSON, and carries the private-panel `X-Robots-Tag` plus `X-Request-Id` headers. The helper validates those response invariants, accepts either the dashboard base URL or a health endpoint, checks the served FlowARK shell metadata, smoke-tests every hashed JS/CSS asset referenced by the built frontend shell, and confirms missing `/assets/*` chunks return non-cacheable plain `404` responses instead of the SPA shell so stale or misrouted assets are caught before browsers load HTML as modules:

```bash
/opt/flowark-dashboard/deploy/check-dashboard-health.sh
FLOWARK_DASHBOARD_URL=https://ark.example.com /opt/flowark-dashboard/deploy/check-dashboard-health.sh
FLOWARK_DASHBOARD_URL=https://ark.example.com/healthz /opt/flowark-dashboard/deploy/check-dashboard-health.sh
FLOWARK_DASHBOARD_URL=https://ark.example.com/api/health /opt/flowark-dashboard/deploy/check-dashboard-health.sh
```

Owners can also open **Sistema > Diagnósticos del Host** in the dashboard. That view includes a production-readiness checklist for environment mode, bind host, CORS, JWT source, data-directory write access, built client assets, validated maps, owner accounts, and basic ARK script/config permissions.

Unknown `/api/*` paths return JSON 404 responses, while the SPA fallback is limited to `GET`/`HEAD` navigation requests. This keeps API/client errors from being masked as successful HTML responses during deploys or cache refreshes.

After the first owner login, remove these lines from `/etc/flowark-dashboard/dashboard.env` and restart:

```bash
# DASHBOARD_BOOTSTRAP_USERNAME=<removed>
# DASHBOARD_BOOTSTRAP_PASSWORD=<removed>
sudo systemctl restart flowark-dashboard
```

## PM2 Alternative

`systemd` is the recommended production manager, but local/transition deployments can run the same built server with PM2. Use the helper instead of `pm2 start npm -- start`; it validates the production env file, loads key/value pairs into the PM2 process environment without sourcing the file as shell, checks that the frontend build exists, starts `server/server.js` directly so restarts signal the Node process cleanly, and then waits for the dashboard health/frontend-asset smoke check to pass:

```bash
cd /opt/flowark-dashboard
deploy/start-pm2.sh /etc/flowark-dashboard/dashboard.env
pm2 save
```

The PM2 ecosystem file is `deploy/pm2/ecosystem.config.cjs` and keeps the app name `ark-dashboard`. The env file can also be supplied with `FLOWARK_DASHBOARD_ENV=/path/to/dashboard.env deploy/start-pm2.sh`, which is useful for local installs that keep secrets outside `/etc`. If the helper must probe through a reverse proxy instead of the local bind address, set `FLOWARK_DASHBOARD_HEALTH_URL=https://ark.example.com` before running it.

## Reverse Proxy

The nginx templates are in `deploy/nginx/`.

```bash
sudo cp /opt/flowark-dashboard/deploy/nginx/flowark-dashboard.conf /etc/nginx/sites-available/flowark-dashboard.conf
sudo ln -s /etc/nginx/sites-available/flowark-dashboard.conf /etc/nginx/sites-enabled/flowark-dashboard.conf
```

Also include `deploy/nginx/flowark-dashboard-map.conf` inside the nginx `http {}` block, or copy the `map` block into an existing global nginx config.

Set `server_name`, certificate paths, and `CORS_ORIGINS` to the same HTTPS origin. Keep `HOST=127.0.0.1` so the Node process is only reachable through nginx, and expose only 80/443 from the host firewall. The TLS server block emits `Strict-Transport-Security: max-age=15552000`; do not enable it for a hostname until HTTPS is stable for that dashboard origin.

The nginx template forwards `X-Request-Id` from `$request_id`; the backend preserves sane upstream ids and generates one when missing. It also forwards the original host, port, protocol, and client address headers expected by the reverse-proxy deployment. This gives a single correlation id across nginx access logs, dashboard responses, and backend diagnostics.

## Log Rotation

The logrotate template is in `deploy/logrotate/flowark-dashboard`.

```bash
sudo cp /opt/flowark-dashboard/deploy/logrotate/flowark-dashboard /etc/logrotate.d/flowark-dashboard
```

The template uses `copytruncate` because the service keeps stdout/stderr file descriptors open.

## Runtime Data Backups

Prepare `DASHBOARD_DATA_DIR` before first production start or after manual restore. This creates the data and backup directories, rejects unsafe entries, and normalizes dashboard data to `0700` directories plus `0600` files:

```bash
sudo -u flowark DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard \
  FLOWARK_DASHBOARD_BACKUP_DIR=/var/lib/flowark-dashboard/backups \
  /opt/flowark-dashboard/deploy/manage-dashboard-data.sh prepare
```

Back up `DASHBOARD_DATA_DIR` regularly. The helper below creates unique restrictive `0600` tarballs plus matching `.sha256` integrity files in a `0700` backup directory and excludes the nested `backups/` directory:

```bash
sudo -u flowark DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard \
  FLOWARK_DASHBOARD_BACKUP_DIR=/var/lib/flowark-dashboard/backups \
  /opt/flowark-dashboard/deploy/manage-dashboard-data.sh backup
```

List and restore backups:

```bash
/opt/flowark-dashboard/deploy/manage-dashboard-data.sh list /var/lib/flowark-dashboard/backups
sudo systemctl stop flowark-dashboard
sudo -u flowark /opt/flowark-dashboard/deploy/manage-dashboard-data.sh restore \
  /var/lib/flowark-dashboard/backups/flowark-dashboard-data-YYYYMMDDTHHMMSSZ.tar.gz \
  /var/lib/flowark-dashboard --force
sudo systemctl start flowark-dashboard
```

Prune old backups after a successful backup. This keeps the newest 14 archives:

```bash
sudo -u flowark /opt/flowark-dashboard/deploy/manage-dashboard-data.sh prune \
  /var/lib/flowark-dashboard/backups 14
```

Treat these archives as sensitive: they can include dashboard password hashes, audit history, map paths, settings, bans, and runtime metadata.
Backups refuse to archive symlinks, hardlinks, FIFOs, devices, and other special source entries so every produced archive stays compatible with the restore safety policy.
Restores reject path traversal and any archive entry that is not a regular file or directory, so a crafted backup cannot plant links, FIFOs, devices, or other special files into the dashboard data directory.
When a matching `.sha256` file exists beside an archive, restore verifies it before extraction and refuses corrupted archives.

## Template Verification

Before deploying a new checkout, run the full local gate:

```bash
cd /opt/flowark-dashboard
bash deploy/check-production-ready.sh
```

To include the live env file in that gate, pass it explicitly or set `FLOWARK_DASHBOARD_ENV`:

```bash
FLOWARK_DASHBOARD_ENV=/etc/flowark-dashboard/dashboard.env bash deploy/check-production-ready.sh
```

Before copying deployment templates to `/etc`, run:

```bash
cd /opt/flowark-dashboard
bash deploy/check-deploy-templates.sh
```

The full gate runs server syntax/tests, production dependency audits with `npm audit --omit=dev`, client tests/lint/build, and deployment-template checks. The template verifier checks `systemd`, logrotate, and nginx templates when the relevant local tools are installed. For nginx it generates a temporary self-signed certificate and rewrites test ports so the check does not need root.

Validate the real production env file before restarting the service:

```bash
sudo /opt/flowark-dashboard/deploy/check-production-env.sh /etc/flowark-dashboard/dashboard.env
```

The env verifier fails on placeholders, short JWT secrets, non-HTTPS/localhost CORS origins, non-loopback Node binds, incomplete bootstrap credentials, and non-production `NODE_ENV`.

## Secret Rotation

If `server/jwt_secret.txt`, `server/data/admins.json`, `server/data/nodes.json`, ARK passwords, or dashboard credentials were ever pushed or backed up outside this host, rotate:

- `JWT_SECRET_KEY`
- dashboard admin passwords
- ARK `ServerAdminPassword`, `ServerPassword`, and `SpectatorPassword`
- Discord webhook URLs
- any RCON passwords stored in runtime node config

Use the dashboard secret-rotation UI or `POST /api/config/secrets` for ARK config secrets.
