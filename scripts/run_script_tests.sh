#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

mapfile -t python_scripts < <(git ls-files 'scripts/*.py' | sort)
if ((${#python_scripts[@]} > 0)); then
    python3 -m py_compile "${python_scripts[@]}"
fi

mapfile -t python_tests < <(git ls-files 'scripts/test_*.py' | sort)
for test_path in "${python_tests[@]}"; do
    python3 "${test_path}"
done

shell_scripts=(
    scripts/install_obelisk.sh
    scripts/install_obelisk_plugin.sh
    scripts/check_release_readiness.sh
    scripts/test_check_release_readiness_options.sh
    scripts/test_install_obelisk_plugin.sh
    scripts/test_install_obelisk_layout.sh
    scripts/check_obelisk_server_posture.sh
    scripts/test_check_obelisk_server_posture.sh
    scripts/obelisk_supervisor_snapshot.sh
    scripts/obelisk_supervisor_loop.sh
    scripts/test_obelisk_supervisor_snapshot.sh
    scripts/test_linuxgsm_wrapper_markers.sh
    packaging/linuxgsm/ObeliskRun.sh
    packaging/linuxgsm/ObeliskRunDebug.sh
)

for script_path in "${shell_scripts[@]}"; do
    bash -n "${script_path}"
done

scripts/test_check_obelisk_server_posture.sh
scripts/test_check_release_readiness_options.sh
scripts/test_install_obelisk_plugin.sh
scripts/test_obelisk_supervisor_snapshot.sh
scripts/test_linuxgsm_wrapper_markers.sh
