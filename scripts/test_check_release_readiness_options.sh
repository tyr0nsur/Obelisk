#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

TEST_TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "${TEST_TEMP_ROOT}"' EXIT

count_temp_roots() {
    find /tmp -maxdepth 1 -type d \
        \( -name 'obelisk-release-check.*' -o -name 'obelisk-layout-check.*' \) \
        2>/dev/null | wc -l
}

before_help_roots="$(count_temp_roots)"
help_output="$(scripts/check_release_readiness.sh --help)"
after_help_roots="$(count_temp_roots)"
if [[ "${before_help_roots}" != "${after_help_roots}" ]]; then
    printf 'help path leaked release temp roots: before=%s after=%s\n' \
        "${before_help_roots}" "${after_help_roots}" >&2
    exit 1
fi

for expected in \
    "--require-second-source-readiness" \
    "--ufunction-second-source-root" \
    "--scriptstruct-second-source-root" \
    "--ufunction-second-source-target-set" \
    "--scriptstruct-second-source-target-set" \
    "--second-source-report-dir" \
    "OBELISK_UFUNCTION_SECOND_SOURCE_ROOT" \
    "OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT" \
    "OBELISK_SECOND_SOURCE_REPORT_DIR"; do
    if ! grep -Fq -- "${expected}" <<<"${help_output}"; then
        printf 'missing help text: %s\n' "${expected}" >&2
        exit 1
    fi
done

if ! grep -Fq -- "ScriptStruct promotion requires explicit opt-in" <<<"${help_output}"; then
    printf 'missing ScriptStruct opt-in help text\n' >&2
    exit 1
fi

if ! grep -Fq -- "temporary directory under the release check root" <<<"${help_output}"; then
    printf 'missing temporary second-source report dir help text\n' >&2
    exit 1
fi

if grep -Fq -- "Defaults to transfer-scriptstruct" <<<"${help_output}"; then
    printf 'help still defaults ScriptStruct second-source gate to transfer-scriptstruct\n' >&2
    exit 1
fi

second_source_default_block="$(
    awk '
        /^if \[\[ "\$\{REQUIRE_SECOND_SOURCE_READINESS\}" == "1" \]\]; then/ { printing = 1 }
        printing { print }
        printing && /^fi$/ { exit }
    ' scripts/check_release_readiness.sh
)"
if [[ -z "${second_source_default_block}" ]]; then
    printf 'missing second-source default target-set block\n' >&2
    exit 1
fi

if ! grep -Fq -- 'UFUNCTION_SECOND_SOURCE_TARGET_SETS=("minimal-second-source-intake")' <<<"${second_source_default_block}"; then
    printf 'missing minimal-second-source-intake UFunction default\n%s\n' \
        "${second_source_default_block}" >&2
    exit 1
fi

if grep -Fq -- 'SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=("transfer-scriptstruct")' <<<"${second_source_default_block}"; then
    printf 'ScriptStruct transfer target set returned as a default\n%s\n' \
        "${second_source_default_block}" >&2
    exit 1
fi

if ! grep -Fq -- '--scriptstruct-second-source-root requires at least one --scriptstruct-second-source-target-set.' <<<"${second_source_default_block}"; then
    printf 'missing ScriptStruct root explicit target-set guard\n%s\n' \
        "${second_source_default_block}" >&2
    exit 1
fi

assert_ufunction_target_sets_after_defaults() {
    local expected_csv="$1"
    shift
    local REQUIRE_SECOND_SOURCE_READINESS=1
    local SCRIPTSTRUCT_SECOND_SOURCE_ROOT=""
    local UFUNCTION_SECOND_SOURCE_TARGET_SETS=("$@")
    local SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=()
    local actual

    eval "${second_source_default_block}"
    actual="$(
        IFS=,
        printf '%s' "${UFUNCTION_SECOND_SOURCE_TARGET_SETS[*]}"
    )"
    if [[ "${actual}" != "${expected_csv}" ]]; then
        printf 'unexpected UFunction target sets after defaults: expected %s got %s\n' \
            "${expected_csv}" "${actual}" >&2
        exit 1
    fi
}

assert_ufunction_target_sets_after_defaults "minimal-second-source-intake"
assert_ufunction_target_sets_after_defaults "buff-compact-intake" "buff-compact-intake"
assert_ufunction_target_sets_after_defaults \
    "minimal-second-source-intake,dino-compact-intake" \
    "minimal-second-source-intake" \
    "dino-compact-intake"

merge_function="$(sed -n '/^merge_second_source_status()/,/^}/p' scripts/check_release_readiness.sh)"
if [[ -z "${merge_function}" ]]; then
    printf 'missing merge_second_source_status function\n' >&2
    exit 1
fi
eval "${merge_function}"

validation_function="$(sed -n '/^validate_second_source_readiness_json()/,/^}/p' scripts/check_release_readiness.sh)"
if [[ -z "${validation_function}" ]]; then
    printf 'missing validate_second_source_readiness_json function\n' >&2
    exit 1
fi
eval "${validation_function}"

readiness_function="$(sed -n '/^run_second_source_readiness()/,/^}/p' scripts/check_release_readiness.sh)"
if [[ -z "${readiness_function}" ]]; then
    printf 'missing run_second_source_readiness function\n' >&2
    exit 1
fi
eval "${readiness_function}"
if ! grep -Fq -- '--fail-on-readiness-gaps --json > "${report_path}"' <<<"${readiness_function}"; then
    printf 'JSON second-source report path must use promotion gate mode\n%s\n' \
        "${readiness_function}" >&2
    exit 1
fi
if ! grep -Fq -- 'run_step "${command[@]}" --fail-on-readiness-gaps' <<<"${readiness_function}"; then
    printf 'text second-source report path must use promotion gate mode\n%s\n' \
        "${readiness_function}" >&2
    exit 1
fi
if ! grep -Fq -- 'validate_second_source_readiness_json "${report_path}" "${target_set}" "${label}"' <<<"${readiness_function}"; then
    printf 'second-source readiness must validate the JSON report\n%s\n' \
        "${readiness_function}" >&2
    exit 1
fi
if ! grep -Fq -- 'SECOND_SOURCE_REPORT_DIR="${RELEASE_CHECK_ROOT}/second-source-readiness-reports"' scripts/check_release_readiness.sh; then
    printf 'missing temporary second-source report dir default under release check root\n' >&2
    exit 1
fi

second_source_report_dir_default_block="$(
    awk '
        /^if \[\[ "\$\{REQUIRE_SECOND_SOURCE_READINESS\}" == "1" && -z "\$\{SECOND_SOURCE_REPORT_DIR\}" \]\]; then/ { printing = 1 }
        printing { print }
        printing && /^fi$/ { exit }
    ' scripts/check_release_readiness.sh
)"
if [[ -z "${second_source_report_dir_default_block}" ]]; then
    printf 'missing second-source report dir default block\n' >&2
    exit 1
fi

assert_second_source_report_dir_default() {
    local REQUIRE_SECOND_SOURCE_READINESS=1
    local RELEASE_CHECK_ROOT="${TEST_TEMP_ROOT}/release-root-default"
    local SECOND_SOURCE_REPORT_DIR=""

    eval "${second_source_report_dir_default_block}"
    if [[ "${SECOND_SOURCE_REPORT_DIR}" != "${RELEASE_CHECK_ROOT}/second-source-readiness-reports" ]]; then
        printf 'unexpected second-source report dir default: %s\n' "${SECOND_SOURCE_REPORT_DIR}" >&2
        exit 1
    fi
}

assert_second_source_report_dir_default

protected_path_helpers="$(
    awk '
        /^SERVER_ROOT=/ { print; next }
        /^APPROVED_OFFLINE_WORKSPACE_ROOT=/ { print; next }
        /^is_under_path\(\)/ { printing = 1 }
        /^while \[\[/ { printing = 0 }
        printing { print }
    ' scripts/check_release_readiness.sh
)"
if [[ -z "${protected_path_helpers}" ]]; then
    printf 'missing protected path helpers\n' >&2
    exit 1
fi
eval "${protected_path_helpers}"

assert_merged_status() {
    local current="$1"
    local next="$2"
    local expected="$3"
    local actual
    actual="$(merge_second_source_status "${current}" "${next}")"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'merge_second_source_status %s %s: expected %s got %s\n' \
            "${current}" "${next}" "${expected}" "${actual}" >&2
        exit 1
    fi
}

assert_merged_status 0 0 0
assert_merged_status 0 2 2
assert_merged_status 2 0 2
assert_merged_status 2 1 1
assert_merged_status 1 2 1
assert_merged_status 2 2 2

write_readiness_json() {
    local path="$1"
    local body="$2"

    printf '%s\n' "${body}" > "${path}"
}

assert_readiness_json_validates() {
    local path="${TEST_TEMP_ROOT}/valid-readiness.json"

    write_readiness_json "${path}" '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}'
    validate_second_source_readiness_json \
        "${path}" \
        "minimal-second-source-intake" \
        "ufunction-minimal-second-source-intake"
}

assert_readiness_json_rejected() {
    local name="$1"
    local body="$2"
    local expected="$3"
    local path="${TEST_TEMP_ROOT}/${name}.json"
    local output

    write_readiness_json "${path}" "${body}"
    set +e
    output="$(
        validate_second_source_readiness_json \
            "${path}" \
            "minimal-second-source-intake" \
            "ufunction-minimal-second-source-intake" 2>&1
    )"
    status=$?
    set -e

    if [[ "${status}" -eq 0 ]]; then
        printf 'expected readiness JSON validation to reject %s\n' "${name}" >&2
        exit 1
    fi
    if ! grep -Fq -- "${expected}" <<<"${output}"; then
        printf 'missing readiness JSON validation error for %s\n%s\n' "${name}" "${output}" >&2
        exit 1
    fi
}

assert_readiness_json_validates
assert_readiness_json_rejected \
    "fake-ready-minimal" \
    '{"promotion_gate":{"ready":true}}' \
    "schema must be obelisk.reflection-snapshot-readiness.v1"
assert_readiness_json_rejected \
    "wrong-target-set" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["buff-compact-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "target_sets must include minimal-second-source-intake"
assert_readiness_json_rejected \
    "blocked-ready" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": [{"reason": "fake"}]},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "promotion_gate.blockers must be empty"
assert_readiness_json_rejected \
    "zero-targets" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {"targets": 0}
}' \
    "totals.targets must be greater than 0"
assert_readiness_json_rejected \
    "missing-target-sets" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "target_sets must include minimal-second-source-intake"
assert_readiness_json_rejected \
    "top-level-only-ready" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  }
}' \
    "modules must be a non-empty list"
assert_readiness_json_rejected \
    "wrong-module-schema-for-ufunction-label" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "scriptstruct",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "modules[0].schema must be ufunction"
assert_readiness_json_rejected \
    "wrong-target-schema-for-ufunction-label" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.scriptstruct-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "modules[0].target_details[0].target must start with obelisk.ufunction-chain.snapshot.v1:"

assert_scriptstruct_readiness_json_validates() {
    local path="${TEST_TEMP_ROOT}/valid-scriptstruct-readiness.json"

    write_readiness_json "${path}" '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["transfer-scriptstruct"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "scriptstruct",
    "module": "sdk_transfers",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
      "path": "sha/sdk_transfers/PrimalLocalProfile.ARKTributeDino.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}'
    validate_second_source_readiness_json \
        "${path}" \
        "transfer-scriptstruct" \
        "scriptstruct-transfer-scriptstruct"
}

assert_scriptstruct_readiness_json_rejected() {
    local path="${TEST_TEMP_ROOT}/wrong-scriptstruct-target-prefix.json"
    local output

    write_readiness_json "${path}" '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["transfer-scriptstruct"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "scriptstruct",
    "module": "sdk_transfers",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
      "path": "sha/sdk_transfers/PrimalLocalProfile.ARKTributeDino.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}'
    set +e
    output="$(
        validate_second_source_readiness_json \
            "${path}" \
            "transfer-scriptstruct" \
            "scriptstruct-transfer-scriptstruct" 2>&1
    )"
    status=$?
    set -e

    if [[ "${status}" -eq 0 ]]; then
        printf 'expected scriptstruct readiness JSON validation to reject wrong target prefix\n' >&2
        exit 1
    fi
    if ! grep -Fq -- "target must start with obelisk.scriptstruct-chain.snapshot.v1:" <<<"${output}"; then
        printf 'missing scriptstruct target prefix validation error\n%s\n' "${output}" >&2
        exit 1
    fi
}

assert_scriptstruct_readiness_json_validates
assert_scriptstruct_readiness_json_rejected

run_step() {
    "$@"
}

install_python3_stub() {
    local stub_dir="$1"

    mkdir -p "${stub_dir}"
    cat > "${stub_dir}/python3" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-" ]]; then
    exec "${REAL_PYTHON3}" "$@"
fi

if [[ "${1:-}" == "scripts/compare_reflection_snapshots.py" ]]; then
    if [[ " $* " == *" --json "* ]]; then
        printf '%s\n' "${STUB_READINESS_JSON}"
    else
        printf 'readiness targets=1 comparable=1 blocked=0 second_source_status=compared gate_mode=second_source_promotion\n'
        printf 'promotion_gate ready=true blockers=none\n'
    fi
    exit "${STUB_COMPARE_STATUS:-0}"
fi

exec "${REAL_PYTHON3}" "$@"
EOF
    chmod +x "${stub_dir}/python3"
}

assert_run_second_source_uses_temp_report_dir_and_validates_json() {
    local stub_dir="${TEST_TEMP_ROOT}/stub-bin-valid"
    local old_path="${PATH}"
    local output

    install_python3_stub "${stub_dir}"
    RELEASE_CHECK_ROOT="${TEST_TEMP_ROOT}/release-root-valid"
    SECOND_SOURCE_REPORT_DIR="${RELEASE_CHECK_ROOT}/second-source-readiness-reports"
    REAL_PYTHON3="$(command -v python3)"
    STUB_READINESS_JSON='{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "promotion_gate": {"ready": true, "blockers": []},
  "target_sets": ["minimal-second-source-intake"],
  "totals": {
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source_accepted": 1,
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0
  },
  "modules": [{
    "schema": "ufunction",
    "module": "sdk_inventory",
    "targets": 1,
    "comparable": 1,
    "blocked": 0,
    "second_source": {"accepted": 1, "rejected": 0, "inconclusive": 0, "missing": 0},
    "target_details": [{
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}'
    export REAL_PYTHON3 STUB_READINESS_JSON
    mkdir -p "${RELEASE_CHECK_ROOT}"
    PATH="${stub_dir}:${PATH}"

    set +e
    output="$(
        run_second_source_readiness \
            "ufunction-minimal-second-source-intake" \
            tests/fixtures/ufunction_snapshots \
            "minimal-second-source-intake" \
            "" 2>&1
    )"
    status=$?
    set -e
    PATH="${old_path}"

    if [[ "${status}" -ne 0 ]]; then
        printf 'expected valid stubbed second-source readiness to pass, got %s\n%s\n' \
            "${status}" "${output}" >&2
        exit 1
    fi
    if [[ ! -f "${SECOND_SOURCE_REPORT_DIR}/ufunction-minimal-second-source-intake-second-source-readiness.json" ]]; then
        printf 'expected second-source readiness JSON under temporary report dir\n%s\n' "${output}" >&2
        exit 1
    fi
}

assert_run_second_source_rejects_fake_ready_json() {
    local stub_dir="${TEST_TEMP_ROOT}/stub-bin-fake"
    local old_path="${PATH}"
    local output

    install_python3_stub "${stub_dir}"
    RELEASE_CHECK_ROOT="${TEST_TEMP_ROOT}/release-root-fake"
    SECOND_SOURCE_REPORT_DIR="${RELEASE_CHECK_ROOT}/second-source-readiness-reports"
    REAL_PYTHON3="$(command -v python3)"
    STUB_READINESS_JSON='{"promotion_gate":{"ready":true}}'
    export REAL_PYTHON3 STUB_READINESS_JSON
    mkdir -p "${RELEASE_CHECK_ROOT}"
    PATH="${stub_dir}:${PATH}"

    set +e
    output="$(
        run_second_source_readiness \
            "ufunction-minimal-second-source-intake" \
            tests/fixtures/ufunction_snapshots \
            "minimal-second-source-intake" \
            "" 2>&1
    )"
    status=$?
    set -e
    PATH="${old_path}"

    if [[ "${status}" -eq 0 ]]; then
        printf 'expected fake ready JSON to fail despite zero compare exit\n%s\n' "${output}" >&2
        exit 1
    fi
    if ! grep -Fq -- "schema must be obelisk.reflection-snapshot-readiness.v1" <<<"${output}"; then
        printf 'missing fake ready JSON validation failure\n%s\n' "${output}" >&2
        exit 1
    fi
}

assert_run_second_source_uses_temp_report_dir_and_validates_json
assert_run_second_source_rejects_fake_ready_json

assert_protected_path_rejected() {
    local label="$1"
    local action="$2"
    local path="$3"
    local expected="$4"
    local output

    set +e
    output="$(reject_protected_path "${label}" "${action}" "${path}" 2>&1)"
    status=$?
    set -e
    if [[ "${status}" -ne 2 ]]; then
        printf 'expected protected path rejection for %s, got %s\n%s\n' \
            "${path}" "${status}" "${output}" >&2
        exit 1
    fi
    if ! grep -Fq -- "${expected}" <<<"${output}"; then
        printf 'missing protected path rejection text for %s\n%s\n' "${path}" "${output}" >&2
        exit 1
    fi
}

assert_path_not_rejected_by_prefix_only() {
    local path="$1"
    local output

    set +e
    output="$(reject_protected_path "--second-source-report-dir" "write under" "${path}" 2>&1)"
    status=$?
    set -e
    if [[ "${status}" -ne 0 ]]; then
        printf 'prefix-only path was over-blocked: %s\n%s\n' "${path}" "${output}" >&2
        exit 1
    fi
}

assert_protected_path_rejected \
    "--ufunction-second-source-root" \
    "read from" \
    "/servidor/ark/obelisk/snapshots" \
    "--ufunction-second-source-root must not read from protected server root /servidor/ark"

assert_protected_path_rejected \
    "--second-source-report-dir" \
    "write under" \
    "/servidor/ark/obelisk/reports" \
    "--second-source-report-dir must not write under protected server root /servidor/ark"

assert_protected_path_rejected \
    "--second-source-report-dir" \
    "write under" \
    "/servidor/ark/symlink-out/reports" \
    "--second-source-report-dir must not write under protected server root /servidor/ark"

with_symlink_dir="$(mktemp -d "${TEST_TEMP_ROOT}/symlink.XXXXXX")"
ln -s /servidor/ark/obelisk/snapshots "${with_symlink_dir}/snapshots"
assert_protected_path_rejected \
    "--scriptstruct-second-source-root" \
    "read from" \
    "${with_symlink_dir}/snapshots" \
    "--scriptstruct-second-source-root must not read from protected server root /servidor/ark"
assert_path_not_rejected_by_prefix_only "/servidor/ark-not-live/reports"
assert_path_not_rejected_by_prefix_only "/servidor/ark/workspace-offline/reports"

before_error_roots="$(count_temp_roots)"
set +e
error_output="$(scripts/check_release_readiness.sh --ufunction-second-source-root /tmp/obelisk-candidate 2>&1)"
status=$?
set -e
after_error_roots="$(count_temp_roots)"

if [[ "${before_error_roots}" != "${after_error_roots}" ]]; then
    printf 'option error path leaked release temp roots: before=%s after=%s\n' \
        "${before_error_roots}" "${after_error_roots}" >&2
    exit 1
fi

if [[ "${status}" -ne 2 ]]; then
    printf 'expected option validation to exit 2, got %s\n%s\n' "${status}" "${error_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${error_output}"; then
    printf 'missing second-source option validation error\n%s\n' "${error_output}" >&2
    exit 1
fi

set +e
target_set_error_output="$(
    scripts/check_release_readiness.sh \
        --ufunction-second-source-target-set buff-compact-intake 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected target-set validation to exit 2, got %s\n%s\n' \
        "${status}" "${target_set_error_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${target_set_error_output}"; then
    printf 'missing target-set option validation error\n%s\n' "${target_set_error_output}" >&2
    exit 1
fi

set +e
scriptstruct_root_without_target_output="$(
    scripts/check_release_readiness.sh \
        --require-second-source-readiness \
        --scriptstruct-second-source-root /tmp/obelisk-scriptstruct-snapshots 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected scriptstruct root without target-set validation to exit 2, got %s\n%s\n' \
        "${status}" "${scriptstruct_root_without_target_output}" >&2
    exit 1
fi

if ! grep -Fq -- "--scriptstruct-second-source-root requires at least one --scriptstruct-second-source-target-set." <<<"${scriptstruct_root_without_target_output}"; then
    printf 'missing scriptstruct root without target-set validation error\n%s\n' \
        "${scriptstruct_root_without_target_output}" >&2
    exit 1
fi

set +e
report_dir_output="$(
    scripts/check_release_readiness.sh \
        --require-second-source-readiness \
        --second-source-report-dir second-source-reports 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected in-repo report dir validation to exit 2, got %s\n%s\n' \
        "${status}" "${report_dir_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source report dir inside the repository must be ignored" <<<"${report_dir_output}"; then
    printf 'missing in-repo report dir validation error\n%s\n' "${report_dir_output}" >&2
    exit 1
fi

echo "test_check_release_readiness_options passed"
