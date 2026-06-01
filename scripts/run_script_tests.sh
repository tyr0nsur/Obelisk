#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

usage() {
    cat <<'EOF'
Usage: scripts/run_script_tests.sh [--list-python-files|--python-tests-only|--verify-shell-test-list]

Runs the repository script validation suite.

Options:
  --list-python-files       Print discovered Python scripts/tests under scripts/.
  --python-tests-only       Run Python compile checks and Python tests, then exit.
  --verify-shell-test-list  Fail if scripts/test_*.sh includes an unlisted shell test.
EOF
}

mode="all"
case "${1:-}" in
    "")
        ;;
    --list-python-files)
        mode="list-python-files"
        ;;
    --python-tests-only)
        mode="python-tests-only"
        ;;
    --verify-shell-test-list)
        mode="verify-shell-test-list"
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        printf 'Unknown argument: %s\n' "$1" >&2
        usage >&2
        exit 2
        ;;
esac

if (($# > 1)); then
    printf 'Unexpected extra argument: %s\n' "$2" >&2
    usage >&2
    exit 2
fi

export PYTHONDONTWRITEBYTECODE=1

list_script_files() {
    local pattern="$1"

    find scripts -maxdepth 1 -type f -name "${pattern}" -print | LC_ALL=C sort -u
}

mapfile -t python_scripts < <(list_script_files '*.py')
mapfile -t python_tests < <(list_script_files 'test_*.py')

if [[ "${mode}" == "python-tests-only" && "${OBELISK_RUN_SCRIPT_TESTS_PROBE_ONLY:-0}" == "1" ]]; then
    probe_tests=()
    for test_path in "${python_tests[@]}"; do
        case "${test_path}" in
            scripts/test_*_tmp_untracked_probe.py)
                probe_tests+=("${test_path}")
                ;;
        esac
    done
    python_scripts=("${probe_tests[@]}")
    python_tests=("${probe_tests[@]}")
fi

shell_scripts=(
    scripts/install_obelisk.sh
    scripts/install_obelisk_plugin.sh
    scripts/check_release_readiness.sh
    scripts/check_rc_layout_evidence_smoke.sh
    scripts/check_linuxgsm_wrapper_drift.sh
    scripts/test_check_release_readiness_options.sh
    scripts/test_check_linuxgsm_wrapper_drift.sh
    scripts/test_install_obelisk_plugin.sh
    scripts/test_install_obelisk_layout.sh
    scripts/test_run_script_tests.sh
    scripts/check_obelisk_server_posture.sh
    scripts/test_check_obelisk_server_posture.sh
    scripts/test_check_player_principal_lifecycle_preflight.sh
    scripts/obelisk_supervisor_snapshot.sh
    scripts/obelisk_supervisor_loop.sh
    scripts/test_obelisk_supervisor_snapshot.sh
    scripts/test_linuxgsm_wrapper_markers.sh
    packaging/linuxgsm/ObeliskRun.sh
    packaging/linuxgsm/ObeliskRunDebug.sh
)

is_listed_shell_script() {
    local candidate="$1"
    local listed_path

    for listed_path in "${shell_scripts[@]}"; do
        if [[ "${candidate}" == "${listed_path}" ]]; then
            return 0
        fi
    done
    return 1
}

verify_shell_test_list() {
    local discovered_shell_tests=()
    local test_path
    local missing_tests=()

    mapfile -t discovered_shell_tests < <(list_script_files 'test_*.sh')
    for test_path in "${discovered_shell_tests[@]}"; do
        if ! is_listed_shell_script "${test_path}"; then
            missing_tests+=("${test_path}")
        fi
    done

    if ((${#missing_tests[@]} > 0)); then
        printf 'Discovered shell tests are not listed in run_script_tests.sh:\n' >&2
        printf '  %s\n' "${missing_tests[@]}" >&2
        printf 'Add each intentional test to the explicit shell_scripts list before it can run.\n' >&2
        return 1
    fi
}

check_python_syntax() {
    python3 - "$@" <<'PY'
import pathlib
import sys

failed = False
for filename in sys.argv[1:]:
    path = pathlib.Path(filename)
    try:
        compile(path.read_text(encoding="utf-8"), filename, "exec")
    except SyntaxError as exc:
        print(f"{filename}:{exc.lineno}:{exc.offset}: {exc.msg}", file=sys.stderr)
        failed = True
    except OSError as exc:
        print(f"{filename}: {exc}", file=sys.stderr)
        failed = True

if failed:
    raise SystemExit(1)
PY
}

if [[ "${mode}" == "list-python-files" ]]; then
    printf '%s\n' "${python_scripts[@]}" "${python_tests[@]}" | sort -u
    exit 0
fi

if [[ "${mode}" == "verify-shell-test-list" ]]; then
    verify_shell_test_list
    exit 0
fi

if ((${#python_scripts[@]} > 0)); then
    check_python_syntax "${python_scripts[@]}"
fi

for test_path in "${python_tests[@]}"; do
    python3 -B "${test_path}"
done

if [[ "${mode}" == "python-tests-only" ]]; then
    exit 0
fi

verify_shell_test_list

for script_path in "${shell_scripts[@]}"; do
    bash -n "${script_path}"
done

scripts/test_check_obelisk_server_posture.sh
scripts/test_check_linuxgsm_wrapper_drift.sh
scripts/test_check_release_readiness_options.sh
scripts/test_install_obelisk_plugin.sh
if [[ -f scripts/test_run_script_tests.sh ]]; then
    OBELISK_RUN_SCRIPT_TESTS_PROBE_ONLY=1 bash scripts/test_run_script_tests.sh
fi
scripts/test_obelisk_supervisor_snapshot.sh
scripts/test_linuxgsm_wrapper_markers.sh
