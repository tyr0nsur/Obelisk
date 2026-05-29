#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

probe="scripts/test_000_tmp_untracked_probe.py"
marker="scripts/test_000_tmp_untracked_probe.executed"
shell_probe="scripts/test_999_tmp_unlisted_shell.sh"
shell_marker="scripts/test_999_tmp_unlisted_shell.executed"
unknown_stdout="/tmp/obelisk-run-script-tests-unknown.out"
unknown_stderr="/tmp/obelisk-run-script-tests-unknown.err"
shell_guard_stdout="/tmp/obelisk-run-script-tests-shell-guard.out"
shell_guard_stderr="/tmp/obelisk-run-script-tests-shell-guard.err"
cleanup() {
    rm -f \
        "${probe}" \
        "${marker}" \
        "${shell_probe}" \
        "${shell_marker}" \
        "${unknown_stdout}" \
        "${unknown_stderr}" \
        "${shell_guard_stdout}" \
        "${shell_guard_stderr}"
}
trap cleanup EXIT

if git ls-files --error-unmatch "${probe}" >/dev/null 2>&1; then
    printf 'probe path unexpectedly tracked: %s\n' "${probe}" >&2
    exit 1
fi
if git ls-files --error-unmatch "${shell_probe}" >/dev/null 2>&1; then
    printf 'shell probe path unexpectedly tracked: %s\n' "${shell_probe}" >&2
    exit 1
fi
if [[ -e "${probe}" || -e "${marker}" || -e "${shell_probe}" || -e "${shell_marker}" ]]; then
    printf 'stale run_script_tests probe state exists: %s %s %s %s\n' \
        "${probe}" \
        "${marker}" \
        "${shell_probe}" \
        "${shell_marker}" >&2
    exit 1
fi

cat >"${probe}" <<PY
#!/usr/bin/env python3
from pathlib import Path
Path("${marker}").write_text("executed\\n", encoding="utf-8")
Path("${probe}").unlink(missing_ok=True)
print("untracked probe executed")
PY

listed="$(scripts/run_script_tests.sh --list-python-files)"
if ! grep -Fxq "${probe}" <<<"${listed}"; then
    printf 'run_script_tests.sh did not list untracked python test %s\n%s\n' "${probe}" "${listed}" >&2
    exit 1
fi

if [[ -e "${marker}" ]]; then
    printf 'run_script_tests.sh --list-python-files executed probe: %s\n' "${probe}" >&2
    exit 1
fi

if scripts/run_script_tests.sh "${probe}" >"${unknown_stdout}" 2>"${unknown_stderr}"; then
    printf 'run_script_tests.sh accepted unsupported explicit path argument: %s\n' "${probe}" >&2
    exit 1
fi
if ! grep -Fq "Unknown argument: ${probe}" "${unknown_stderr}"; then
    printf 'run_script_tests.sh did not explain unsupported explicit path argument\n' >&2
    cat "${unknown_stderr}" >&2
    exit 1
fi

cat >"${shell_probe}" <<SH
#!/usr/bin/env bash
set -euo pipefail
printf 'executed\n' > "${shell_marker}"
SH

if scripts/run_script_tests.sh --verify-shell-test-list >"${shell_guard_stdout}" 2>"${shell_guard_stderr}"; then
    printf 'run_script_tests.sh accepted unlisted shell test: %s\n' "${shell_probe}" >&2
    exit 1
fi
if ! grep -Fq 'Discovered shell tests are not listed in run_script_tests.sh' "${shell_guard_stderr}"; then
    printf 'run_script_tests.sh did not explain unlisted shell test discovery\n' >&2
    cat "${shell_guard_stderr}" >&2
    exit 1
fi
if ! grep -Fq "${shell_probe}" "${shell_guard_stderr}"; then
    printf 'run_script_tests.sh did not name unlisted shell test %s\n' "${shell_probe}" >&2
    cat "${shell_guard_stderr}" >&2
    exit 1
fi
if [[ -e "${shell_marker}" ]]; then
    printf 'run_script_tests.sh executed unlisted shell test: %s\n' "${shell_probe}" >&2
    exit 1
fi
rm -f "${shell_probe}" "${shell_marker}"

scripts/run_script_tests.sh --python-tests-only >/dev/null
if [[ ! -e "${marker}" ]]; then
    printf 'run_script_tests.sh --python-tests-only did not execute untracked python test %s\n' "${probe}" >&2
    exit 1
fi
rm -f "${probe}" "${marker}"

echo "test_run_script_tests passed"
