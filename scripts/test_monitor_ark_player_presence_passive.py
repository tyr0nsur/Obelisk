#!/usr/bin/env python3
"""Focused offline tests for the passive ARK player presence monitor."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import NamedTuple


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "monitor_ark_player_presence_passive.sh"
FORBIDDEN_LGSM_COMMANDS = {"details", "monitor", "start", "stop", "restart"}


class MonitorRun(NamedTuple):
    result: subprocess.CompletedProcess[str]
    gamedig_args: str
    lgsm_args: str
    rcon_args: str
    timed_out: bool = False
    captured_files: dict[str, str] | None = None


class PassiveMonitorTests(unittest.TestCase):
    def run_monitor(
        self,
        gamedig_response: str,
        args: list[str] | None = None,
        observer_log: str | dict[str, str] | None = None,
        fake_clock: bool = False,
        env_overrides: dict[str, str] | None = None,
        timeout_seconds: float = 5,
        expect_timeout: bool = False,
        capture_files: list[str] | None = None,
    ) -> MonitorRun:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ark_root = tmp_path / "ark"
            logs_root = tmp_path / "obelisk-logs"
            gamedig_args = tmp_path / "gamedig.args"
            lgsm_args = tmp_path / "lgsm.args"
            rcon_args = tmp_path / "rcon.args"
            fake_bin = tmp_path / "fake-bin"
            fake_clock_file = tmp_path / "fake-clock"
            gamedig = ark_root / "lgsm" / "node_modules" / "gamedig" / "bin" / "gamedig.js"
            rcon_helper = tmp_path / "fake-rcon-helper.js"
            rcon_ini = ark_root / "serverfiles" / "ShooterGame" / "Saved" / "Config" / "LinuxServer" / "GameUserSettings.ini"

            gamedig.parent.mkdir(parents=True)
            rcon_ini.parent.mkdir(parents=True)
            logs_root.mkdir()
            rcon_ini.write_text("[ServerSettings]\nServerAdminPassword=test\n", encoding="utf-8")
            gamedig.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    {
                        for arg in "$@"; do
                            printf '<%s>' "$arg"
                        done
                        printf '\\n'
                    } >> "$GAMEDIG_ARGS_LOG"
                    query_port=""
                    previous_arg=""
                    for arg in "$@"; do
                        if [[ "$previous_arg" == "--port" ]]; then
                            query_port="$arg"
                            break
                        fi
                        previous_arg="$arg"
                    done

                    case "${GAMEDIG_RESPONSE:?}" in
                        zero)
                            printf '%s\\n' '{"name":"Empty Test Server","map":"Ragnarok","numplayers":0,"maxplayers":70}'
                            ;;
                        invalid_game)
                            printf '%s\\n' '{"error":"Invalid game"}'
                            ;;
                        invalid_json)
                            printf '%s\\n' 'not-json'
                            ;;
                        missing_player_count)
                            printf '%s\\n' '{"name":"Ambiguous Test Server","map":"Ragnarok","maxplayers":70}'
                            ;;
                        command_failed)
                            printf '%s\\n' 'query timeout' >&2
                            exit 7
                            ;;
                        players)
                            printf '%s\\n' '{"name":"Active Test Server","map":"Ragnarok","numplayers":3,"maxplayers":70}'
                            ;;
                        players_once)
                            call_count="$(wc -l < "$GAMEDIG_ARGS_LOG" | tr -d ' ')"
                            if [[ "$call_count" -eq 1 ]]; then
                                printf '%s\\n' '{"name":"Active Test Server","map":"Ragnarok","numplayers":3,"maxplayers":70}'
                            else
                                printf '%s\\n' '{"name":"Empty Test Server","map":"Ragnarok","numplayers":0,"maxplayers":70}'
                            fi
                            ;;
                        players_twice_then_zero)
                            call_count="$(wc -l < "$GAMEDIG_ARGS_LOG" | tr -d ' ')"
                            if [[ "$call_count" -le 2 ]]; then
                                printf '%s\\n' '{"name":"Active Test Server","map":"Ragnarok","numplayers":3,"maxplayers":70}'
                            else
                                printf '%s\\n' '{"name":"Empty Test Server","map":"Ragnarok","numplayers":0,"maxplayers":70}'
                            fi
                            ;;
                        theisland_then_ragnarok)
                            call_count="$(wc -l < "$GAMEDIG_ARGS_LOG" | tr -d ' ')"
                            if [[ "$query_port" == "27016" && "$call_count" -eq 2 ]]; then
                                printf '%s\\n' '{"name":"Active TheIsland Test Server","map":"TheIsland","numplayers":1,"maxplayers":70}'
                            elif [[ "$query_port" == "27015" && "$call_count" -eq 3 ]]; then
                                printf '%s\\n' '{"name":"Active Ragnarok Test Server","map":"Ragnarok","numplayers":2,"maxplayers":70}'
                            elif [[ "$query_port" == "27016" ]]; then
                                printf '%s\\n' '{"name":"Empty TheIsland Test Server","map":"TheIsland","numplayers":0,"maxplayers":70}'
                            else
                                printf '%s\\n' '{"name":"Empty Ragnarok Test Server","map":"Ragnarok","numplayers":0,"maxplayers":70}'
                            fi
                            ;;
                        *)
                            printf 'unexpected fake GameDig response: %s\\n' "$GAMEDIG_RESPONSE" >&2
                            exit 64
                            ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            gamedig.chmod(0o755)
            rcon_helper.write_text(
                textwrap.dedent(
                    """\
                    const fs = require('fs');

                    fs.appendFileSync(
                        process.env.RCON_ARGS_LOG,
                        `<port:${process.env.RCON_TEST_PORT}><command:${process.env.RCON_TEST_COMMAND}>\\n`,
                    );

                    switch (process.env.RCON_FAKE_RESPONSE || 'zero') {
                        case 'zero':
                            console.log(JSON.stringify({ command: process.env.RCON_TEST_COMMAND, response: 'No Players Connected' }));
                            break;
                        case 'players':
                            console.log(JSON.stringify({ command: process.env.RCON_TEST_COMMAND, response: '1. Alice, 76561198000000001\\n2. Bob, 76561198000000002' }));
                            break;
                        case 'summary_zero':
                            console.log(JSON.stringify({ ok: true, command: 'ListPlayers', responseKind: 'ListPlayers', responseReceived: true, responseLength: 20, playerCount: 0 }, null, 2));
                            break;
                        case 'summary_players':
                            console.log(JSON.stringify({ ok: true, command: 'ListPlayers', responseKind: 'ListPlayers', responseReceived: true, responseLength: 54, playerCount: 2 }, null, 2));
                            break;
                        case 'summary_by_port':
                            console.log(JSON.stringify({
                                ok: true,
                                command: 'ListPlayers',
                                responseKind: 'ListPlayers',
                                responseReceived: true,
                                responseLength: process.env.RCON_TEST_PORT === '27021' ? 27 : 20,
                                playerCount: process.env.RCON_TEST_PORT === '27021' ? 1 : 0,
                            }, null, 2));
                            break;
                        case 'summary_unknown':
                            console.log(JSON.stringify({ ok: true, command: 'ListPlayers', responseKind: 'ListPlayers', responseReceived: true, responseLength: 17, playerCount: null }, null, 2));
                            break;
                        case 'unknown':
                            console.log(JSON.stringify({ command: process.env.RCON_TEST_COMMAND, response: 'server says maybe' }));
                            break;
                        case 'invalid_json':
                            console.log('not-json');
                            break;
                        case 'command_failed':
                            console.error('rcon failed');
                            process.exit(7);
                            break;
                        case 'timeout':
                            setTimeout(() => {}, 10000);
                            break;
                        default:
                            console.error(`unexpected fake RCON response: ${process.env.RCON_FAKE_RESPONSE}`);
                            process.exit(64);
                    }
                    """
                ),
                encoding="utf-8",
            )

            if observer_log is not None:
                observer_logs = observer_log if isinstance(observer_log, dict) else {"arkserver": observer_log}
                for instance_name, contents in observer_logs.items():
                    instance_log = logs_root / instance_name / "Obelisk.log"
                    instance_log.parent.mkdir(parents=True)
                    instance_log.write_text(contents, encoding="utf-8")

            lgsm_script = textwrap.dedent(
                """\
                #!/usr/bin/env bash
                printf '%s\\n' "$*" >> "$LGSM_ARGS_LOG"

                case "${1:-}" in
                    details|monitor|start|stop|restart)
                        printf 'forbidden lifecycle command: %s\\n' "$1" >&2
                        exit 99
                        ;;
                    *)
                        printf 'unexpected fake LinuxGSM command: %s\\n' "$*" >&2
                        exit 98
                        ;;
                esac
                """
            )
            for instance_name in ("arkserver", "arkserver2"):
                instance = ark_root / instance_name
                instance.write_text(lgsm_script, encoding="utf-8")
                instance.chmod(0o755)

            if fake_clock:
                fake_bin.mkdir()
                fake_clock_file.write_text("1000\n", encoding="utf-8")
                fake_date = fake_bin / "date"
                fake_date.write_text(
                    textwrap.dedent(
                        """\
                        #!/usr/bin/env bash
                        now="$(cat "$FAKE_CLOCK_FILE")"
                        if [[ "${1:-}" == "+%s" ]]; then
                            printf '%s\\n' "$now"
                            exit 0
                        fi
                        if [[ "${1:-}" == "-u" && "${2:-}" == "+%Y-%m-%dT%H:%M:%SZ" ]]; then
                            /bin/date -u -d "@${now}" +%Y-%m-%dT%H:%M:%SZ
                            exit 0
                        fi
                        if [[ "${1:-}" == "-u" && "${2:-}" == "-d" && "${3:-}" == @* ]]; then
                            /bin/date "$@"
                            exit 0
                        fi
                        exec /bin/date "$@"
                        """
                    ),
                    encoding="utf-8",
                )
                fake_date.chmod(0o755)
                fake_sleep = fake_bin / "sleep"
                fake_sleep.write_text(
                    textwrap.dedent(
                        """\
                        #!/usr/bin/env bash
                        seconds="${1:?}"
                        now="$(cat "$FAKE_CLOCK_FILE")"
                        printf '%s\\n' "$((now + seconds))" > "$FAKE_CLOCK_FILE"
                        """
                    ),
                    encoding="utf-8",
                )
                fake_sleep.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "GAMEDIG_ARGS_LOG": str(gamedig_args),
                    "GAMEDIG_RESPONSE": gamedig_response,
                    "LGSM_ARGS_LOG": str(lgsm_args),
                    "RCON_ARGS_LOG": str(rcon_args),
                    "RCON_FAKE_RESPONSE": "zero",
                    "OBELISK_PASSIVE_MONITOR_ARK_ROOT": str(ark_root),
                    "OBELISK_PASSIVE_MONITOR_GAMEDIG": str(gamedig),
                    "OBELISK_PASSIVE_MONITOR_LOG_ROOT": str(logs_root),
                    "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "off",
                    "OBELISK_PASSIVE_MONITOR_RCON_HELPER": str(rcon_helper),
                    "OBELISK_PASSIVE_MONITOR_RCON_INI_PATH": str(rcon_ini),
                }
            )
            if fake_clock:
                env["FAKE_CLOCK_FILE"] = str(fake_clock_file)
                env["PATH"] = f"{fake_bin}:{env['PATH']}"
            if env_overrides:
                env.update(env_overrides)

            resolved_args = [
                item.replace("{tmp}", str(tmp_path))
                for item in (args or ["--once", "arkserver:Ragnarok"])
            ]
            command = [str(SCRIPT), *resolved_args]
            timed_out = False
            if expect_timeout:
                process = subprocess.Popen(
                    command,
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                try:
                    stdout, stderr = process.communicate(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        stdout, stderr = process.communicate(timeout=1)
                    result = subprocess.CompletedProcess(command, 124, stdout, stderr)
                else:
                    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
                    self.fail("monitor exited before the expected test timeout\n" + result.stdout + result.stderr)
            else:
                result = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            captured_files = {}
            for requested_path in capture_files or []:
                resolved_path = Path(requested_path.replace("{tmp}", str(tmp_path)))
                if resolved_path.exists():
                    captured_files[requested_path] = resolved_path.read_text(encoding="utf-8")

            return MonitorRun(
                result=result,
                gamedig_args=gamedig_args.read_text(encoding="utf-8") if gamedig_args.exists() else "",
                lgsm_args=lgsm_args.read_text(encoding="utf-8") if lgsm_args.exists() else "",
                rcon_args=rcon_args.read_text(encoding="utf-8") if rcon_args.exists() else "",
                timed_out=timed_out,
                captured_files=captured_files,
            )

    def assert_success(self, run: MonitorRun) -> None:
        self.assertEqual(run.result.returncode, 0, run.result.stdout + run.result.stderr)

    def assert_uses_ase(self, run: MonitorRun) -> None:
        self.assertIn("<--type><ase>", run.gamedig_args)
        self.assertNotIn("arkse", run.gamedig_args)

    def assert_no_forbidden_lgsm_commands(self, run: MonitorRun) -> None:
        for line in run.lgsm_args.splitlines():
            command = line.split(maxsplit=1)[0] if line.split(maxsplit=1) else ""
            self.assertNotIn(command, FORBIDDEN_LGSM_COMMANDS)

    def assert_query_unknown_not_zero(self, run: MonitorRun) -> str:
        query_lines = [line for line in run.result.stdout.splitlines() if line.startswith("query instance=")]
        self.assertEqual(1, len(query_lines), run.result.stdout)
        self.assertIn("status=unknown", query_lines[0])
        self.assertNotIn("players=0", query_lines[0])
        return query_lines[0]

    def player_presence_context_line(self, run: MonitorRun, instance: str = "arkserver") -> str:
        context_lines = [
            line
            for line in run.result.stdout.splitlines()
            if line.startswith(f"player_presence_context instance={instance} ")
        ]
        self.assertEqual(1, len(context_lines), run.result.stdout)
        return context_lines[0]

    def test_valid_gamedig_zero_reports_zero_players_without_details_fallback(self) -> None:
        run = self.run_monitor("zero")

        self.assert_success(run)
        self.assert_uses_ase(run)
        self.assertIn("status=ok", run.result.stdout)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("process_control=none", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertNotIn("player_presence_detected", run.result.stdout)
        context_line = self.player_presence_context_line(run)
        self.assertIn("presence_detected=false", context_line)
        self.assertIn("no_users_confirmed=false", context_line)
        self.assertIn("unknown_player_context=true", context_line)
        self.assertIn("query_signal=zero", context_line)
        self.assertIn("rcon_signal=disabled", context_line)
        self.assertIn("observer_signal=unavailable_no_log", context_line)
        self.assertIn(
            "unknown_sources=rcon_listplayers_redacted:disabled\\,observer_lifecycle:unavailable_no_log",
            context_line,
        )
        self.assertEqual("", run.lgsm_args)

    def test_emits_monitor_session_and_replacement_metadata(self) -> None:
        run = self.run_monitor(
            "zero",
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_SESSION_ID": "test-passive-session",
                "OBELISK_PASSIVE_MONITOR_REPLACED_PID": "12345",
                "OBELISK_PASSIVE_MONITOR_REPLACEMENT_NOTE": "prior_monitor_completed_linger",
                "OBELISK_PASSIVE_MONITOR_TMUX_SESSION": "obelisk_passive_monitor",
            },
        )

        self.assert_success(run)
        session_lines = [
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_monitor_session ")
        ]
        self.assertEqual(1, len(session_lines), run.result.stdout)
        session_line = session_lines[0]
        self.assertIn("pid=", session_line)
        self.assertIn("session_id=test-passive-session", session_line)
        self.assertIn("tmux_session=obelisk_passive_monitor", session_line)
        self.assertIn("targets=arkserver:Ragnarok:27015", session_line)
        self.assertIn("target_count=1", session_line)
        self.assertIn("replacement_status=active_monitor_reported_metadata_only", session_line)
        self.assertIn("replaced_monitor_pid=12345", session_line)
        self.assertIn("active_monitor_pid=12345", session_line)
        self.assertIn("replacement_requested=false", session_line)
        self.assertIn("old_monitor_action=not_performed_by_passive_monitor", session_line)
        self.assertIn("replacement_policy=never_signal_stop_or_replace_existing_monitor", session_line)
        self.assertIn("active_monitor_policy=metadata_only_never_signal_stop_or_replace", session_line)
        self.assertIn("process_control=none", session_line)
        self.assertIn("evidence_classification=passive_monitor_metadata_non_evidence", session_line)
        self.assertIn("approved_runtime_evidence=false", session_line)
        self.assertIn("ready=false", session_line)
        self.assertEqual("", run.lgsm_args)

    def test_snapshot_monitor_log_path_receives_monitor_transcript(self) -> None:
        monitor_log = "{tmp}/monitor-logs/passive-monitor.log"
        run = self.run_monitor(
            "zero",
            args=[
                "--once",
                "--snapshot-monitor-log",
                monitor_log,
                "arkserver:Ragnarok",
            ],
            capture_files=[monitor_log],
        )

        self.assert_success(run)
        captured_files = run.captured_files or {}
        self.assertIn(monitor_log, captured_files)
        monitor_log_contents = captured_files[monitor_log]
        self.assertIn("passive_monitor_session ", monitor_log_contents)
        self.assertIn("snapshot_monitor_log=", monitor_log_contents)
        self.assertIn("tick utc=", monitor_log_contents)
        self.assertIn("query instance=arkserver", monitor_log_contents)
        self.assertIn("player_presence_context instance=arkserver", monitor_log_contents)
        self.assertEqual(1, monitor_log_contents.count("passive_monitor_session "))
        self.assertEqual("", run.lgsm_args)

    def test_explicit_replacement_request_is_still_metadata_only(self) -> None:
        run = self.run_monitor(
            "zero",
            args=[
                "--once",
                "--active-monitor-pid",
                "45678",
                "--replacement-requested",
                "--replacement-note",
                "operator_started_successor_without_stopping_old_monitor",
                "arkserver:Ragnarok",
            ],
        )

        self.assert_success(run)
        session_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_monitor_session ")
        )
        self.assertIn("replacement_status=explicit_replacement_requested_metadata_only", session_line)
        self.assertIn("active_monitor_pid=45678", session_line)
        self.assertIn("replacement_requested=true", session_line)
        self.assertIn("old_monitor_action=not_performed_by_passive_monitor", session_line)
        self.assertIn("process_control=none", session_line)
        self.assertIn("evidence_classification=passive_monitor_metadata_non_evidence", session_line)
        self.assertIn("approved_runtime_evidence=false", session_line)
        self.assertIn("ready=false", session_line)
        self.assertEqual("", run.lgsm_args)

    def test_active_monitor_pid_is_not_signaled_or_replaced(self) -> None:
        active_monitor = subprocess.Popen(["sleep", "30"])
        try:
            run = self.run_monitor(
                "zero",
                args=[
                    "--once",
                    "--active-monitor-pid",
                    str(active_monitor.pid),
                    "--replacement-requested",
                    "arkserver:Ragnarok",
                ],
            )

            self.assert_success(run)
            self.assertIsNone(active_monitor.poll())
            self.assertIn("active_monitor_pid=", run.result.stdout)
            self.assertIn("old_monitor_action=not_performed_by_passive_monitor", run.result.stdout)
            self.assertIn("process_control=none", run.result.stdout)
            self.assertEqual("", run.lgsm_args)
        finally:
            if active_monitor.poll() is None:
                active_monitor.terminate()
                try:
                    active_monitor.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    active_monitor.kill()
                    active_monitor.wait(timeout=5)

    def test_targets_are_normalized_with_default_ports_and_target_keys(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "--no-details", "arkserver:Ragnarok", "arkserver2:TheIsland"],
        )

        self.assert_success(run)
        session_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_monitor_session ")
        )
        self.assertIn("targets=arkserver:Ragnarok:27015\\,arkserver2:TheIsland:27016", session_line)
        self.assertIn("target_count=2", session_line)
        self.assertIn("target_key=arkserver:Ragnarok:27015", run.result.stdout)
        self.assertIn("target_key=arkserver2:TheIsland:27016", run.result.stdout)
        self.assertIn("presence_detected=false", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_arkserver3_default_query_and_rcon_ports_are_known(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver3:Genesis2"],
            env_overrides={"OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on"},
        )

        self.assert_success(run)
        self.assertIn("targets=arkserver3:Genesis2:27017", run.result.stdout)
        self.assertIn("target_key=arkserver3:Genesis2:27017", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver3", run.result.stdout)
        self.assertIn("rcon_port=27022", run.result.stdout)
        self.assertIn("players_current=0", run.result.stdout)
        self.assertIn("<port:27022><command:ListPlayers>", run.rcon_args)
        self.assertNotIn("player_presence_detected", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_listplayers_detects_presence_when_gamedig_reports_zero(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver3:Genesis2"],
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "players",
            },
        )

        self.assert_success(run)
        self.assertIn("query instance=arkserver3", run.result.stdout)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver3", run.result.stdout)
        self.assertIn("players_current=2", run.result.stdout)
        self.assertIn("rcon_output_redacted=true", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver3 map=Genesis2", run.result.stdout)
        self.assertIn("detection_source=rcon_listplayers_redacted", run.result.stdout)
        self.assertNotIn("Alice", run.result.stdout)
        self.assertNotIn("76561198000000001", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_present_query_zero_surfaces_discrepancy_as_non_evidence(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver:Ragnarok"],
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_players",
            },
        )

        self.assert_success(run)
        self.assertIn("query instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("rcon_port=27020 status=ok players_current=2", run.result.stdout)
        context_line = self.player_presence_context_line(run)
        self.assertIn("presence_detected=true", context_line)
        self.assertIn("query_signal=zero", context_line)
        self.assertIn("rcon_signal=present", context_line)
        self.assertIn("source_discrepancy_detected=true", context_line)
        self.assertIn(
            "discrepant_sources=gamedig_ase_query_zero\\,rcon_listplayers_redacted_present",
            context_line,
        )
        self.assertIn(
            "discrepancy_classification=rcon_present_query_zero_trusted_source_discrepancy_non_evidence",
            context_line,
        )
        self.assertIn("discrepancy_counts_as_approved_runtime_evidence=false", context_line)
        self.assertIn("discrepancy_authorizes_server_operations=false", context_line)
        detection_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("player_presence_detected instance=arkserver map=Ragnarok")
        )
        self.assertIn("detection_source=rcon_listplayers_redacted", detection_line)
        self.assertIn("source_discrepancy_detected=true", detection_line)
        self.assertIn("evidence_classification=passive_player_presence_context_non_evidence", context_line)
        self.assertIn("process_control=none", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("process_control=restart", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_presence_with_gate_only_observer_tail_surfaces_diagnostic_non_evidence(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            """
        )
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver:Ragnarok"],
            observer_log=observer_log,
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_players",
            },
        )

        self.assert_success(run)
        context_line = self.player_presence_context_line(run)
        self.assertIn("presence_detected=true", context_line)
        self.assertIn("query_signal=zero", context_line)
        self.assertIn("rcon_signal=present", context_line)
        self.assertIn("observer_signal=matched_no_accepted_observer_event", context_line)
        self.assertIn(
            "presence_without_lifecycle_start_after_observer_gate=true",
            context_line,
        )
        self.assertIn(
            "diagnostic_condition=presence_without_lifecycle_start_after_observer_gate_non_evidence",
            context_line,
        )
        self.assertIn("process_control=none", context_line)
        self.assertIn("approved_runtime_evidence=false", context_line)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("process_control=restart", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_listplayers_accepts_real_helper_summary_player_count(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "--no-details", "arkserver:Ragnarok:27015", "arkserver2:TheIsland:27016"],
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_by_port",
            },
        )

        self.assert_success(run)
        self.assertIn("targets=arkserver:Ragnarok:27015\\,arkserver2:TheIsland:27016", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver map=Ragnarok query_port=27015 rcon_port=27020", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver2 map=TheIsland query_port=27016 rcon_port=27021", run.result.stdout)
        self.assertIn("rcon_port=27020 status=ok players_current=0", run.result.stdout)
        self.assertIn("rcon_port=27021 status=ok players_current=1", run.result.stdout)
        self.assertNotIn("rcon_port=27020 status=unknown", run.result.stdout)
        self.assertNotIn("rcon_port=27021 status=unknown", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver2 map=TheIsland", run.result.stdout)
        self.assertNotIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("<port:27020><command:ListPlayers>", run.rcon_args)
        self.assertIn("<port:27021><command:ListPlayers>", run.rcon_args)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_listplayers_summary_null_player_count_remains_unknown(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver:Ragnarok"],
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_unknown",
            },
        )

        self.assert_success(run)
        self.assertIn("rcon_listplayers instance=arkserver", run.result.stdout)
        self.assertIn("rcon_port=27020 status=unknown players_current=unknown", run.result.stdout)
        context_line = self.player_presence_context_line(run)
        self.assertIn("rcon_signal=unknown", context_line)
        self.assertIn("unknown_player_context=true", context_line)
        self.assertNotIn("player_presence_detected instance=arkserver", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_invalid_game_is_unknown_not_zero_and_skips_lgsm_details(self) -> None:
        run = self.run_monitor("invalid_game")

        self.assert_success(run)
        self.assert_uses_ase(run)
        query_line = self.assert_query_unknown_not_zero(run)
        self.assertRegex(query_line, r"error=.*Invalid.*game")
        self.assertIn("query_warning", run.result.stdout)
        self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
        self.assertEqual("", run.lgsm_args)
        self.assert_no_forbidden_lgsm_commands(run)

    def test_gamedig_command_failure_is_unknown_not_zero_and_skips_lgsm_details(self) -> None:
        run = self.run_monitor("command_failed")

        self.assert_success(run)
        self.assert_uses_ase(run)
        query_line = self.assert_query_unknown_not_zero(run)
        self.assertIn("rc=7", query_line)
        self.assertIn("error=command_failed", query_line)
        self.assertIn("query_warning", run.result.stdout)
        self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
        self.assertEqual("", run.lgsm_args)
        self.assert_no_forbidden_lgsm_commands(run)

    def test_invalid_gamedig_json_is_unknown_not_zero_and_skips_lgsm_details(self) -> None:
        run = self.run_monitor("invalid_json")

        self.assert_success(run)
        self.assert_uses_ase(run)
        query_line = self.assert_query_unknown_not_zero(run)
        self.assertIn("rc=0", query_line)
        self.assertIn("error=invalid_json", query_line)
        self.assertIn("query_warning", run.result.stdout)
        self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
        self.assertEqual("", run.lgsm_args)
        self.assert_no_forbidden_lgsm_commands(run)

    def test_missing_gamedig_player_count_is_unknown_not_zero_and_skips_lgsm_details(self) -> None:
        run = self.run_monitor("missing_player_count")

        self.assert_success(run)
        self.assert_uses_ase(run)
        query_line = self.assert_query_unknown_not_zero(run)
        self.assertIn("error=missing_player_count", query_line)
        self.assertIn("players_current=unknown", query_line)
        self.assertIn("query_warning", run.result.stdout)
        self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertNotIn("player_presence_detected", run.result.stdout)
        context_line = self.player_presence_context_line(run)
        self.assertIn("presence_detected=false", context_line)
        self.assertIn("no_users_confirmed=false", context_line)
        self.assertIn("unknown_player_context=true", context_line)
        self.assertIn("query_signal=unknown", context_line)
        self.assertIn("rcon_signal=disabled", context_line)
        self.assertIn("observer_signal=unavailable_no_log", context_line)
        self.assertIn(
            "unknown_sources=gamedig_ase_query\\,rcon_listplayers_redacted:disabled\\,observer_lifecycle:unavailable_no_log",
            context_line,
        )
        self.assertEqual("", run.lgsm_args)
        self.assert_no_forbidden_lgsm_commands(run)

    def test_no_details_skips_lgsm_fallback_when_query_is_unknown(self) -> None:
        run = self.run_monitor("invalid_game", args=["--once", "--no-details", "arkserver:Ragnarok"])

        self.assert_success(run)
        self.assert_uses_ase(run)
        query_line = self.assert_query_unknown_not_zero(run)
        self.assertRegex(query_line, r"error=.*Invalid.*game")
        self.assertIn("query_warning", run.result.stdout)
        self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_no_details_never_invokes_lgsm_for_query_errors(self) -> None:
        for response in ("invalid_game", "invalid_json", "missing_player_count", "command_failed"):
            with self.subTest(response=response):
                run = self.run_monitor(
                    response,
                    args=["--once", "--no-details", "arkserver:Ragnarok"],
                )

                self.assert_success(run)
                self.assert_uses_ase(run)
                self.assert_query_unknown_not_zero(run)
                self.assertIn("details_fallback=disabled", run.result.stdout)
                self.assertIn("linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path", run.result.stdout)
                self.assertEqual("", run.lgsm_args)

    def test_valid_gamedig_presence_detects_players_without_details_fallback(self) -> None:
        run = self.run_monitor("players")

        self.assert_success(run)
        self.assert_uses_ase(run)
        self.assertIn("status=ok", run.result.stdout)
        self.assertIn("players=3/70", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("query_port=27015", run.result.stdout)
        self.assertIn("target_key=arkserver:Ragnarok:27015", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_detection_metadata_remains_process_control_none_and_non_evidence(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:02] [warning] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:03] [warning] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor(
            "players",
            args=[
                "--once",
                "--active-monitor-pid",
                "45678",
                "--replacement-requested",
                "arkserver:Ragnarok",
            ],
            observer_log=observer_log,
        )

        self.assert_success(run)
        session_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_monitor_session ")
        )
        observer_tail_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("observer_tail instance=arkserver ")
        )
        self.assertIn("process_control=none", session_line)
        self.assertIn("evidence_classification=passive_monitor_metadata_non_evidence", session_line)
        self.assertIn("approved_runtime_evidence=false", session_line)
        self.assertIn("ready=false", session_line)
        self.assertIn("classification=complete_accepted_observer_event_triplet_candidate_non_evidence", observer_tail_line)
        self.assertIn("evidence_classification=passive_tail_non_evidence", observer_tail_line)
        self.assertIn("approved_runtime_evidence=false", observer_tail_line)
        self.assertIn("ready=false", observer_tail_line)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertNotIn("process_control=restart", run.result.stdout)
        self.assertNotIn("process_control=stop", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("ready=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_valid_gamedig_presence_can_capture_passive_snapshot_once(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [07:00:00] [info] Obelisk Runtime Loaded Native (LD_PRELOAD)
            [07:00:00] [info] ProcessEvent vtable-derived pattern candidates found: 1
            [07:00:00] [info] ProcessEvent candidate[0] = 0x1d34e20
            [07:00:00] [info] Found ProcessEvent at address: 0x1d34e20
            [07:00:00] [info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x7000
            [07:00:00] [info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 and enable-reflection-scanner marker to run the experimental scanner.
            [07:00:00] [warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.
            [07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            """
        )
        run = self.run_monitor(
            "players",
            args=[
                "--once",
                "--no-details",
                "--snapshot-output-root",
                "{tmp}/snapshots",
                "--snapshot-monitor-log",
                "{tmp}/passive-monitor.log",
                "arkserver:Ragnarok",
            ],
            observer_log=observer_log,
        )

        self.assert_success(run)
        self.assert_uses_ase(run)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("passive_snapshot_captured output_dir=", run.result.stdout)
        self.assertIn("detected_instances=arkserver", run.result.stdout)
        self.assertIn("manifest", run.result.stdout)
        snapshot_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_snapshot_captured ")
        )
        self.assertIn("snapshot_action=copy_analyze_only", snapshot_line)
        self.assertIn("snapshot_authorization_source=none_passive_monitor_only", snapshot_line)
        self.assertIn("snapshot_counts_as_approved_runtime_evidence=false", snapshot_line)
        self.assertIn("snapshot_counts_toward_sdk=false", snapshot_line)
        self.assertIn("snapshot_counts_toward_p0_dependency_chain=false", snapshot_line)
        self.assertIn("snapshot_authorizes_server_operations=false", snapshot_line)
        self.assertIn("snapshot_authorizes_runtime_capture=false", snapshot_line)
        self.assertIn("snapshot_authorizes_discord=false", snapshot_line)
        self.assertIn("evidence_classification=passive_snapshot_non_evidence", snapshot_line)
        self.assertIn("approved_runtime_evidence=false", snapshot_line)
        self.assertIn("ready=false", snapshot_line)
        self.assertNotIn("passive_snapshot_failed", run.result.stdout)
        self.assertNotIn("snapshot_counts_as_approved_runtime_evidence=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_snapshot_capture_fires_for_later_target_presence(self) -> None:
        observer_logs = {
            "arkserver": "[07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.\n",
            "arkserver2": "[07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.\n",
        }
        run = self.run_monitor(
            "theisland_then_ragnarok",
            args=[
                "--interval",
                "5",
                "--linger-after-detect",
                "10",
                "--no-details",
                "--snapshot-output-root",
                "{tmp}/snapshots",
                "arkserver:Ragnarok",
                "arkserver2:TheIsland",
            ],
            observer_log=observer_logs,
            fake_clock=True,
        )

        self.assert_success(run)
        snapshot_lines = [
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_snapshot_captured ")
        ]
        self.assertEqual(2, len(snapshot_lines), run.result.stdout)
        self.assertIn("detected_instances=arkserver2", snapshot_lines[0])
        self.assertIn("detected_target_keys=arkserver2:TheIsland:27016", snapshot_lines[0])
        self.assertIn("snapshot_sequence=1", snapshot_lines[0])
        self.assertIn("snapshot_target_count=1", snapshot_lines[0])
        self.assertIn("snapshot_trigger_policy=per_target_new_detection", snapshot_lines[0])
        self.assertIn("detected_instances=arkserver", snapshot_lines[1])
        self.assertIn("detected_target_keys=arkserver:Ragnarok:27015", snapshot_lines[1])
        self.assertIn("snapshot_sequence=2", snapshot_lines[1])
        self.assertIn("snapshot_target_count=1", snapshot_lines[1])
        self.assertIn("snapshot_trigger_policy=per_target_new_detection", snapshot_lines[1])
        self.assertEqual(
            1,
            run.result.stdout.count("player_presence_detected instance=arkserver2 map=TheIsland"),
            run.result.stdout,
        )
        self.assertEqual(
            1,
            run.result.stdout.count("player_presence_detected instance=arkserver map=Ragnarok"),
            run.result.stdout,
        )
        self.assertIn("player_presence_linger_start seconds=10", run.result.stdout)
        self.assertIn("player_presence_linger_extend seconds=10", run.result.stdout)
        self.assertNotIn("passive_snapshot_failed", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("ready=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_default_non_once_monitor_continues_after_per_target_snapshot_capture(self) -> None:
        observer_logs = {
            "arkserver": "[07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.\n",
            "arkserver2": "[07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.\n",
        }
        run = self.run_monitor(
            "players",
            args=[
                "--interval",
                "5",
                "--no-details",
                "--snapshot-output-root",
                "{tmp}/snapshots",
                "arkserver:Ragnarok",
                "arkserver2:TheIsland",
            ],
            observer_log=observer_logs,
            timeout_seconds=3,
            expect_timeout=True,
        )

        self.assertTrue(run.timed_out, run.result.stdout + run.result.stderr)
        snapshot_lines = [
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_snapshot_captured ")
        ]
        self.assertEqual(2, len(snapshot_lines), run.result.stdout)
        self.assertIn("detected_instances=arkserver", snapshot_lines[0])
        self.assertIn("detected_target_keys=arkserver:Ragnarok:27015", snapshot_lines[0])
        self.assertIn("snapshot_sequence=1", snapshot_lines[0])
        self.assertIn("snapshot_target_count=1", snapshot_lines[0])
        self.assertIn("snapshot_trigger_policy=per_target_new_detection", snapshot_lines[0])
        self.assertIn("detected_instances=arkserver2", snapshot_lines[1])
        self.assertIn("detected_target_keys=arkserver2:TheIsland:27016", snapshot_lines[1])
        self.assertIn("snapshot_sequence=2", snapshot_lines[1])
        self.assertIn("snapshot_target_count=1", snapshot_lines[1])
        self.assertIn("snapshot_trigger_policy=per_target_new_detection", snapshot_lines[1])
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver2 map=TheIsland", run.result.stdout)
        self.assertNotIn("passive_snapshot_failed", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("ready=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_snapshot_failure_is_non_authorizing_when_output_path_is_protected(self) -> None:
        run = self.run_monitor(
            "players",
            args=[
                "--once",
                "--no-details",
                "--snapshot-output-root",
                "/servidor/ark/passive-monitor-should-not-write",
                "arkserver:Ragnarok",
            ],
        )

        self.assert_success(run)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        snapshot_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("passive_snapshot_failed ")
        )
        self.assertIn("rc=", snapshot_line)
        self.assertRegex(snapshot_line, r"error=.*protected.*server.*root")
        self.assertIn("snapshot_action=copy_analyze_only", snapshot_line)
        self.assertIn("snapshot_authorization_source=none_passive_monitor_only", snapshot_line)
        self.assertIn("snapshot_counts_as_approved_runtime_evidence=false", snapshot_line)
        self.assertIn("snapshot_counts_toward_sdk=false", snapshot_line)
        self.assertIn("snapshot_counts_toward_p0_dependency_chain=false", snapshot_line)
        self.assertIn("snapshot_authorizes_server_operations=false", snapshot_line)
        self.assertIn("snapshot_authorizes_runtime_capture=false", snapshot_line)
        self.assertIn("snapshot_authorizes_discord=false", snapshot_line)
        self.assertIn("evidence_classification=passive_snapshot_non_evidence", snapshot_line)
        self.assertIn("approved_runtime_evidence=false", snapshot_line)
        self.assertIn("ready=false", snapshot_line)
        self.assertNotIn("passive_snapshot_captured", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("ready=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_linger_after_detect_keeps_follow_up_tick_without_details_fallback(self) -> None:
        run = self.run_monitor(
            "players_once",
            args=[
                "--interval",
                "5",
                "--linger-after-detect",
                "1",
                "--no-details",
                "arkserver:Ragnarok",
            ],
            fake_clock=True,
        )

        self.assert_success(run)
        self.assert_uses_ase(run)
        self.assertEqual(2, run.result.stdout.count("tick utc="), run.result.stdout)
        self.assertEqual(2, len(run.gamedig_args.splitlines()), run.gamedig_args)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("player_presence_linger_start seconds=1", run.result.stdout)
        self.assertIn("target_keys=arkserver:Ragnarok:27015", run.result.stdout)
        self.assertIn("process_control=none", run.result.stdout)
        self.assertIn("player_presence_linger_complete seconds=1", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_repeated_positive_detection_extends_linger_window(self) -> None:
        run = self.run_monitor(
            "players_twice_then_zero",
            args=[
                "--interval",
                "5",
                "--linger-after-detect",
                "10",
                "--no-details",
                "arkserver:Ragnarok",
            ],
            fake_clock=True,
        )

        self.assert_success(run)
        self.assert_uses_ase(run)
        self.assertEqual(4, run.result.stdout.count("tick utc="), run.result.stdout)
        self.assertEqual(4, len(run.gamedig_args.splitlines()), run.gamedig_args)
        self.assertEqual(
            2,
            run.result.stdout.count("player_presence_detected instance=arkserver map=Ragnarok"),
            run.result.stdout,
        )
        self.assertEqual(1, run.result.stdout.count("player_presence_linger_start"), run.result.stdout)
        self.assertIn("player_presence_linger_start seconds=10 until_utc=1970-01-01T00:16:50Z", run.result.stdout)
        self.assertIn(
            "player_presence_linger_extend seconds=10 until_utc=1970-01-01T00:16:55Z",
            run.result.stdout,
        )
        self.assertIn("target_keys=arkserver:Ragnarok:27015", run.result.stdout)
        self.assertIn("player_presence_linger_complete seconds=10", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_once_exits_after_single_tick(self) -> None:
        run = self.run_monitor("zero")

        self.assert_success(run)
        self.assertEqual(1, run.result.stdout.count("tick utc="), run.result.stdout)
        self.assertEqual(1, len(run.gamedig_args.splitlines()), run.gamedig_args)

    def test_observer_delta_includes_lifecycle_diagnostic_candidates(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 target=GameMode.K2_PostLogin fname_index=4943 post_original=true accepted_lifecycle_target=false params_logged=false identity_logged=false evidence_claim=none.
            [05:20:02] [warning] PlayerPrincipalLifecycleDiagnostic function-FName near-miss logging enabled scan_limit=10000 params_logged=false identity_logged=false evidence_claim=none principal_claim=none.
            [05:20:03] [warning] PlayerPrincipalLifecycleDiagnostic route-sampling enabled sample_limit=500 params_logged=false identity_logged=false evidence_claim=none principal_claim=none.
            [05:20:04] [info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=1 fname_index=9999 fname_number=0 post_original=true accepted_lifecycle_target=false reflection_probe=false params_logged=false identity_logged=false evidence_claim=none.
            """
        )
        run = self.run_monitor("zero", observer_log=observer_log)

        self.assert_success(run)
        self.assertIn("observer_tail instance=arkserver status=matched lines=5", run.result.stdout)
        self.assertIn("accepted_observer_event_triplet_candidate_lines=0", run.result.stdout)
        self.assertIn("diagnostic_only_lines=4", run.result.stdout)
        self.assertIn("route_sample_lines=1", run.result.stdout)
        self.assertIn("complete_triplet_candidate=false", run.result.stdout)
        self.assertIn("classification=diagnostic_only_lines_non_evidence", run.result.stdout)
        self.assertIn("evidence_classification=passive_tail_non_evidence", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertIn("ready=false", run.result.stdout)
        self.assertIn("observer instance=arkserver", run.result.stdout)
        self.assertIn("PlayerPrincipalLifecycleObserver enabled", run.result.stdout)
        self.assertIn("PlayerPrincipalLifecycleDiagnostic candidate", run.result.stdout)
        self.assertIn("function-FName near-miss logging enabled", run.result.stdout)
        self.assertIn("route-sampling enabled", run.result.stdout)
        self.assertIn("PlayerPrincipalLifecycleDiagnostic route-sample", run.result.stdout)
        self.assertIn("params_logged=false identity_logged=false evidence_claim=none", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_delta_surfaces_accepted_triplet_as_passive_non_evidence(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:02] [warning] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:03] [warning] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor("zero", observer_log=observer_log)

        self.assert_success(run)
        self.assertIn("observer_tail instance=arkserver status=matched lines=4", run.result.stdout)
        self.assertIn("observer_gate_lines=1", run.result.stdout)
        self.assertIn("raw_observer_event_lines=3", run.result.stdout)
        self.assertIn("accepted_observer_event_triplet_candidate_lines=3", run.result.stdout)
        self.assertIn("rejected_observer_event_line_count=0", run.result.stdout)
        self.assertIn("check_join_rejected_start_candidate_lines=1", run.result.stdout)
        self.assertIn("superseded_handle_new_player_rejected_start_lines=0", run.result.stdout)
        self.assertIn("diagnostic_only_lines=0", run.result.stdout)
        self.assertIn("raw_event_roles=session_start,session_start_rejected,session_end", run.result.stdout)
        self.assertIn("event_roles=session_start,session_start_rejected,session_end", run.result.stdout)
        self.assertIn("latest_raw_observer_event_role=session_end", run.result.stdout)
        self.assertIn("latest_observer_event_role=session_end", run.result.stdout)
        self.assertIn("lifecycle_active_candidate=false", run.result.stdout)
        self.assertIn("complete_triplet_candidate=true", run.result.stdout)
        self.assertIn("observer_event_role_policy=accepted_safe_observer_events_only", run.result.stdout)
        self.assertIn(
            "classification=complete_accepted_observer_event_triplet_candidate_non_evidence",
            run.result.stdout,
        )
        self.assertIn("evidence_classification=passive_tail_non_evidence", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertIn("ready=false", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_delta_does_not_complete_triplet_from_superseded_handle_new_player_rejected_start(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:02] [warning] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            [05:20:03] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=3 target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true accepted_lifecycle_target=false reflection_status=matched diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer params_logged=false identity_logged=false evidence_claim=none.
            [05:20:04] [warning] PlayerPrincipalLifecycleObserver event sequence=4 role=session_end target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver2:TheIsland"],
            observer_log={"arkserver2": observer_log},
        )

        self.assert_success(run)
        observer_tail_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("observer_tail instance=arkserver2 ")
        )
        self.assertIn("status=matched", observer_tail_line)
        self.assertIn("lines=5", observer_tail_line)
        self.assertIn("observer_gate_lines=1", observer_tail_line)
        self.assertIn("raw_observer_event_lines=3", observer_tail_line)
        self.assertIn("accepted_observer_event_triplet_candidate_lines=2", observer_tail_line)
        self.assertIn("rejected_observer_event_line_count=1", observer_tail_line)
        self.assertIn("check_join_rejected_start_candidate_lines=0", observer_tail_line)
        self.assertIn("superseded_handle_new_player_rejected_start_lines=1", observer_tail_line)
        self.assertIn("diagnostic_only_lines=1", observer_tail_line)
        self.assertIn("raw_event_roles=session_start,session_start_rejected,session_end", observer_tail_line)
        self.assertIn("event_roles=session_start,session_end", observer_tail_line)
        self.assertIn("latest_raw_observer_event_role=session_end", observer_tail_line)
        self.assertIn("latest_observer_event_role=session_end", observer_tail_line)
        self.assertIn("lifecycle_active_candidate=false", observer_tail_line)
        self.assertIn("complete_triplet_candidate=false", observer_tail_line)
        self.assertIn("classification=partial_accepted_observer_event_triplet_candidate_non_evidence", observer_tail_line)
        self.assertIn("observer_event_role_policy=accepted_safe_observer_events_only", observer_tail_line)
        self.assertIn("approved_runtime_evidence=false", observer_tail_line)
        self.assertIn("ready=false", observer_tail_line)
        self.assertNotIn("complete_triplet_candidate=true", observer_tail_line)
        self.assertEqual("", run.lgsm_args)

    def test_observer_session_end_only_is_no_start_non_evidence_signal(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:03] [warning] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor(
            "zero",
            observer_log=observer_log,
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_zero",
            },
        )

        self.assert_success(run)
        observer_tail_line = next(
            line
            for line in run.result.stdout.splitlines()
            if line.startswith("observer_tail instance=arkserver ")
        )
        self.assertIn("event_roles=session_end", observer_tail_line)
        self.assertIn("latest_observer_event_role=session_end", observer_tail_line)
        self.assertIn("lifecycle_active_candidate=false", observer_tail_line)
        self.assertIn("complete_triplet_candidate=false", observer_tail_line)
        self.assertIn("session_end_without_session_start_candidate=true", observer_tail_line)
        self.assertIn(
            "classification=session_end_without_session_start_candidate_non_evidence",
            observer_tail_line,
        )
        context_line = self.player_presence_context_line(run)
        self.assertIn("no_users_confirmed=true", context_line)
        self.assertNotIn("player_presence_detected instance=arkserver", run.result.stdout)
        self.assertNotIn("process_control=restart", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_latest_session_start_counts_as_presence_candidate(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor("zero", observer_log=observer_log)

        self.assert_success(run)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("latest_observer_event_role=session_start", run.result.stdout)
        self.assertIn("lifecycle_active_candidate=true", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("detection_source=observer_lifecycle_active_candidate", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertIn("ready=false", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_latest_session_start_detects_presence_when_gamedig_zero_and_rcon_times_out(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver3:Genesis2"],
            observer_log={"arkserver3": observer_log},
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "OBELISK_PASSIVE_MONITOR_RCON_TIMEOUT_SECONDS": "1",
                "RCON_FAKE_RESPONSE": "timeout",
            },
        )

        self.assert_success(run)
        self.assertIn("query instance=arkserver3", run.result.stdout)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("presence_detected=false detection_source=gamedig_ase_query", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver3", run.result.stdout)
        self.assertIn("rcon_port=27022", run.result.stdout)
        self.assertIn("rc=124 status=unknown error=timeout", run.result.stdout)
        self.assertIn("presence_detected=false detection_source=rcon_listplayers_redacted", run.result.stdout)
        self.assertIn("rcon_output_redacted=true", run.result.stdout)
        self.assertIn("<port:27022><command:ListPlayers>", run.rcon_args)
        self.assertIn("latest_observer_event_role=session_start", run.result.stdout)
        self.assertIn("lifecycle_active_candidate=true", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver3 map=Genesis2", run.result.stdout)
        self.assertIn("detection_source=observer_lifecycle_active_candidate", run.result.stdout)
        self.assertIn("process_control=none", run.result.stdout)
        self.assertIn("approved_runtime_evidence=false", run.result.stdout)
        self.assertIn("ready=false", run.result.stdout)
        self.assertNotIn("approved_runtime_evidence=true", run.result.stdout)
        self.assertNotIn("ready=true", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_rcon_zero_suppresses_stale_observer_active_candidate_presence(self) -> None:
        observer_log = textwrap.dedent(
            """\
            [05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
            [05:20:01] [warning] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none.
            """
        )
        run = self.run_monitor(
            "zero",
            args=["--once", "arkserver3:Genesis2"],
            observer_log={"arkserver3": observer_log},
            env_overrides={
                "OBELISK_PASSIVE_MONITOR_RCON_ENABLED": "on",
                "RCON_FAKE_RESPONSE": "summary_zero",
            },
        )

        self.assert_success(run)
        self.assertIn("query instance=arkserver3", run.result.stdout)
        self.assertIn("players=0/70", run.result.stdout)
        self.assertIn("rcon_listplayers instance=arkserver3", run.result.stdout)
        self.assertIn("rcon_port=27022 status=ok players_current=0", run.result.stdout)
        self.assertIn("latest_observer_event_role=session_start", run.result.stdout)
        self.assertIn("lifecycle_active_candidate=true", run.result.stdout)
        context_line = self.player_presence_context_line(run, "arkserver3")
        self.assertIn("presence_detected=false", context_line)
        self.assertIn("query_signal=zero", context_line)
        self.assertIn("rcon_signal=zero", context_line)
        self.assertIn("observer_signal=active_candidate", context_line)
        self.assertIn("detection_source=none", context_line)
        self.assertNotIn("player_presence_detected instance=arkserver3 map=Genesis2", run.result.stdout)
        self.assertNotIn("detection_source=observer_lifecycle_active_candidate", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_tail_reports_each_target_when_logs_are_absent(self) -> None:
        run = self.run_monitor(
            "zero",
            args=["--once", "--no-details", "arkserver:Ragnarok", "arkserver2:TheIsland"],
        )

        self.assert_success(run)
        self.assertIn("observer_tail instance=arkserver status=no_log scan_lines=200 limit=10", run.result.stdout)
        self.assertIn("observer_tail instance=arkserver2 status=no_log scan_lines=200 limit=10", run.result.stdout)
        self.assertEqual(2, len(run.gamedig_args.splitlines()), run.gamedig_args)
        self.assertEqual("", run.lgsm_args)

    def test_detection_linger_transcript_tails_both_targets_without_lgsm_details(self) -> None:
        observer_logs = {
            "arkserver": "[05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=test target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.\n",
            "arkserver2": "[05:20:01] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 target=GameMode.K2_PostLogin fname_index=4943 post_original=true accepted_lifecycle_target=false params_logged=false identity_logged=false evidence_claim=none.\n",
        }
        run = self.run_monitor(
            "players_twice_then_zero",
            args=[
                "--interval",
                "5",
                "--linger-after-detect",
                "1",
                "--no-details",
                "arkserver:Ragnarok",
                "arkserver2:TheIsland",
            ],
            observer_log=observer_logs,
            fake_clock=True,
        )

        self.assert_success(run)
        self.assertEqual(2, run.result.stdout.count("tick utc="), run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver map=Ragnarok", run.result.stdout)
        self.assertIn("player_presence_detected instance=arkserver2 map=TheIsland", run.result.stdout)
        self.assertIn(
            "player_presence_linger_start seconds=1 until_utc=1970-01-01T00:16:41Z detected_instances=arkserver,arkserver2 observer_tail=per_target",
            run.result.stdout,
        )
        self.assertIn(
            "target_keys=arkserver:Ragnarok:27015,arkserver2:TheIsland:27016",
            run.result.stdout,
        )
        self.assertIn(
            "player_presence_linger_complete seconds=1 until_utc=1970-01-01T00:16:41Z observer_tail=per_target",
            run.result.stdout,
        )
        self.assertIn("observer_tail instance=arkserver status=matched lines=1", run.result.stdout)
        self.assertIn("observer_tail instance=arkserver2 status=matched lines=1", run.result.stdout)
        self.assertIn("tail_scope=per_target", run.result.stdout)
        self.assertIn("process_control=none", run.result.stdout)
        self.assertEqual("", run.lgsm_args)

    def test_observer_tail_does_not_copy_unrelated_session_text(self) -> None:
        observer_log = "[05:20:01] [info] unrelated session_start playername=do-not-copy\n"
        run = self.run_monitor("zero", observer_log=observer_log)

        self.assert_success(run)
        self.assertIn("observer_tail instance=arkserver status=no_matching_lines", run.result.stdout)
        self.assertNotIn("playername=do-not-copy", run.result.stdout)
        self.assertEqual("", run.lgsm_args)


if __name__ == "__main__":
    unittest.main()
