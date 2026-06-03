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
rc_smoke_help_output="$(scripts/check_rc_layout_evidence_smoke.sh --help 2>&1)"
after_help_roots="$(count_temp_roots)"
if [[ "${before_help_roots}" != "${after_help_roots}" ]]; then
    printf 'help path leaked release temp roots: before=%s after=%s\n' \
        "${before_help_roots}" "${after_help_roots}" >&2
    exit 1
fi

for expected in \
    "freshly assembled for the intended HEAD" \
    "bool-tail metadata" \
    "do not reuse a historical published-RC root" \
    "v0.1.0-rc.2"; do
    if ! grep -Fq -- "${expected}" <<<"${rc_smoke_help_output}"; then
        printf 'missing RC layout smoke stale-root help text: %s\n%s\n' \
            "${expected}" "${rc_smoke_help_output}" >&2
        exit 1
    fi
done

for expected in \
    "--require-second-source-readiness" \
    "--require-v1-sdk-completion" \
    "--v1-sdk-release-statement" \
    "--allow-cross-ref-second-source-root" \
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

set +e
v1_sdk_statement_without_gate_output="$(
    scripts/check_release_readiness.sh --v1-sdk-release-statement /tmp/obelisk-v1-statement.md 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected v1 release statement without gate to exit 2, got %s\n%s\n' \
        "${status}" "${v1_sdk_statement_without_gate_output}" >&2
    exit 1
fi

if ! grep -Fq -- "--v1-sdk-release-statement requires --require-v1-sdk-completion." <<<"${v1_sdk_statement_without_gate_output}"; then
    printf 'missing v1 statement option validation error\n%s\n' "${v1_sdk_statement_without_gate_output}" >&2
    exit 1
fi

set +e
v1_sdk_completion_without_statement_output="$(scripts/check_release_readiness.sh --require-v1-sdk-completion 2>&1)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected v1 SDK completion without release statement to exit 2, got %s\n%s\n' \
        "${status}" "${v1_sdk_completion_without_statement_output}" >&2
    exit 1
fi

if ! grep -Fq -- "--require-v1-sdk-completion requires --v1-sdk-release-statement." <<<"${v1_sdk_completion_without_statement_output}"; then
    printf 'missing v1 SDK completion release-statement-required error\n%s\n' \
        "${v1_sdk_completion_without_statement_output}" >&2
    exit 1
fi

set +e
v1_sdk_protected_statement_output="$(
    scripts/check_release_readiness.sh \
        --require-v1-sdk-completion \
        --v1-sdk-release-statement /servidor/ark/obelisk/v1-release-statement.md 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected protected v1 release statement path to exit 2, got %s\n%s\n' \
        "${status}" "${v1_sdk_protected_statement_output}" >&2
    exit 1
fi

if ! grep -Fq -- "--v1-sdk-release-statement must not read from protected server root /servidor/ark" <<<"${v1_sdk_protected_statement_output}"; then
    printf 'missing protected v1 release statement path error\n%s\n' \
        "${v1_sdk_protected_statement_output}" >&2
    exit 1
fi

v1_gate_line="$(grep -n 'check_public_sdk_v1_completion.py' scripts/check_release_readiness.sh | head -n1 | cut -d: -f1)"
configure_line="$(grep -n 'cmake -S . -B' scripts/check_release_readiness.sh | head -n1 | cut -d: -f1)"
if [[ -z "${v1_gate_line}" || -z "${configure_line}" || "${v1_gate_line}" -ge "${configure_line}" ]]; then
    printf 'v1 SDK completion gate must run before core configure/build work: gate=%s configure=%s\n' \
        "${v1_gate_line}" "${configure_line}" >&2
    exit 1
fi

if ! grep -Fq -- "Public SDK v1 stable claim gate passed." scripts/check_release_readiness.sh; then
    printf 'missing precise v1 stable-claim pass wording in release gate\n' >&2
    exit 1
fi
if ! grep -Fq -- "Public SDK v1 stable claim gate was not run." scripts/check_release_readiness.sh; then
    printf 'missing precise v1 stable-claim skipped wording in release gate\n' >&2
    exit 1
fi
if grep -Fq -- "Public SDK v1 completion gate completed." scripts/check_release_readiness.sh; then
    printf 'release gate must not use generic v1 completion completed wording\n' >&2
    exit 1
fi
if ! grep -Fq -- "Scoped release-readiness baseline and gameplay/module second-source layout-evidence gates completed." scripts/check_release_readiness.sh; then
    printf 'missing scoped second-source layout-evidence pass wording in release gate\n' >&2
    exit 1
fi
if ! grep -Fq -- "Scoped release-readiness baseline checks completed; gameplay/module second-source layout-evidence gate was not run." scripts/check_release_readiness.sh; then
    printf 'missing scoped second-source layout-evidence skipped wording in release gate\n' >&2
    exit 1
fi
if grep -Fq -- "Release readiness baseline and gameplay/module second-source promotion checks completed." scripts/check_release_readiness.sh; then
    printf 'release gate must not use generic second-source promotion completed wording\n' >&2
    exit 1
fi
if ! grep -Fq -- "Release gate output is evidence for this exact gate only" scripts/check_release_readiness.sh; then
    printf 'missing release gate final non-claim wording\n' >&2
    exit 1
fi

if ! grep -Fq -- "production libobelisk.so symbol surface checks" <<<"${help_output}"; then
    printf 'missing production symbol-surface help text\n' >&2
    exit 1
fi
for expected in \
    "not live-ops approval" \
    "Plugin Hub readiness/publication" \
    "support-tier activation" \
    "runtime readiness" \
    "stable SDK claim" \
    "v1 SDK completion"; do
    if ! grep -Fq -- "${expected}" <<<"${help_output}"; then
        printf 'missing release gate non-claim help text: %s\n' "${expected}" >&2
        exit 1
    fi
done

if ! grep -Fq -- "ScriptStruct promotion requires explicit opt-in" <<<"${help_output}"; then
    printf 'missing ScriptStruct opt-in help text\n' >&2
    exit 1
fi

for expected in \
    "Defaults to the public RC target sets" \
    "structure-observer-intake" \
    "item-return-only-policy-slice" \
    "chat-message-intake"; do
    if ! grep -Fq -- "${expected}" <<<"${help_output}"; then
        printf 'missing public RC target-set help text: %s\n' "${expected}" >&2
        exit 1
    fi
done

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

for expected in \
    'PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]' \
    'UFUNCTION_SECOND_SOURCE_TARGET_SETS+=("${required_target_set}")'; do
    if ! grep -Fq -- "${expected}" <<<"${second_source_default_block}"; then
        printf 'missing public RC UFunction default logic %s\n%s\n' \
            "${expected}" "${second_source_default_block}" >&2
        exit 1
    fi
done

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
    local PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS=(
        "minimal-second-source-intake"
        "structure-observer-intake"
        "item-return-only-policy-slice"
        "chat-message-intake"
    )
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

assert_ufunction_target_sets_after_defaults \
    "minimal-second-source-intake,structure-observer-intake,item-return-only-policy-slice,chat-message-intake"
assert_ufunction_target_sets_after_defaults \
    "chat-message-intake,minimal-second-source-intake,structure-observer-intake,item-return-only-policy-slice" \
    "chat-message-intake"
assert_ufunction_target_sets_after_defaults \
    "minimal-second-source-intake,item-return-only-policy-slice,structure-observer-intake,chat-message-intake" \
    "minimal-second-source-intake" \
    "item-return-only-policy-slice"

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

production_symbol_function="$(sed -n '/^check_production_runtime_symbols()/,/^}/p' scripts/check_release_readiness.sh)"
if [[ -z "${production_symbol_function}" ]]; then
    printf 'missing production runtime symbol guard\n' >&2
    exit 1
fi
for expected in \
    'nm -C "${runtime_library}"' \
    'PRODUCTION_FORBIDDEN_SYMBOL_PATTERNS[@]' \
    'Production libobelisk.so exposes test-only/internal symbols'; do
    if ! grep -Fq -- "${expected}" <<<"${production_symbol_function}"; then
        printf 'missing production symbol guard logic: %s\n%s\n' \
            "${expected}" "${production_symbol_function}" >&2
        exit 1
    fi
done
for expected in \
    "ForTesting" \
    "SetNextRegistrationIdForTesting" \
    "ApiCapabilitiesForTesting" \
    "SetNextTimerIdForTesting" \
    "SetPluginCallbackCleanupFailure" \
    "SetPluginRetentionFailure" \
    "ClearPluginOwnerLifecycle"; do
    if ! grep -Fq -- "\"${expected}\"" scripts/check_release_readiness.sh; then
        printf 'missing forbidden production symbol pattern: %s\n' "${expected}" >&2
        exit 1
    fi
done
if ! grep -Fq -- 'run_step check_production_runtime_symbols' scripts/check_release_readiness.sh; then
    printf 'release readiness must run the production symbol guard after build\n' >&2
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

assert_second_source_root_commit_validation() {
    local candidate_root="${TEST_TEMP_ROOT}/cross-ref-ufunction-root"
    local output

    mkdir -p "${candidate_root}/7e7ded49e0c6/sdk_chat"
    cp \
        "tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json" \
        "${candidate_root}/7e7ded49e0c6/sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json"
    python3 - "${candidate_root}/7e7ded49e0c6/sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["evidence"]["obelisk_commit"] = "0000000"
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

    ALLOW_CROSS_REF_SECOND_SOURCE_ROOT=0
    set +e
    output="$(validate_second_source_root_commit "--ufunction-second-source-root" "${candidate_root}" 2>&1)"
    status=$?
    set -e
    if [[ "${status}" -ne 2 ]]; then
        printf 'expected cross-ref second-source root rejection, got %s\n%s\n' \
            "${status}" "${output}" >&2
        exit 1
    fi
    if ! grep -Fq -- "--allow-cross-ref-second-source-root" <<<"${output}"; then
        printf 'missing cross-ref override guidance\n%s\n' "${output}" >&2
        exit 1
    fi

    ALLOW_CROSS_REF_SECOND_SOURCE_ROOT=1
    validate_second_source_root_commit "--ufunction-second-source-root" "${candidate_root}"
}

assert_second_source_root_commit_validation

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
  "evidence_scope": "second_source_layout_evidence_only",
  "not_promoted_surfaces": ["ObeliskApi.RegisterCommandResponseCallback"],
  "non_claims": ["layout evidence only; not public SDK readiness"],
  "promotion_gate": {
    "ready": true,
    "blockers": [],
    "ready_scope": "layout_only",
    "layout_ready": true,
    "promotion_ready": false,
    "public_sdk_ready": false,
    "runtime_ready": false
  },
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
    "thin-ready-without-layout-boundary" \
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
      "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
      "path": "sha/sdk_inventory/PrimalItem.CanUse.json",
      "comparable": true,
      "block_reasons": [],
      "second_source_status": "accepted"
    }]
  }]
}' \
    "promotion_gate.ready_scope must be layout_only"
assert_readiness_json_rejected \
    "wrong-target-set" \
    '{
  "schema": "obelisk.reflection-snapshot-readiness.v1",
  "gate_mode": "second_source_promotion",
  "second_source_status": "compared",
  "evidence_scope": "second_source_layout_evidence_only",
  "not_promoted_surfaces": ["ObeliskApi.RegisterCommandResponseCallback"],
  "non_claims": ["layout evidence only; not public SDK readiness"],
  "promotion_gate": {
    "ready": true,
    "blockers": [],
    "ready_scope": "layout_only",
    "layout_ready": true,
    "promotion_ready": false,
    "public_sdk_ready": false,
    "runtime_ready": false
  },
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
  "evidence_scope": "second_source_layout_evidence_only",
  "not_promoted_surfaces": ["ObeliskApi.RegisterCommandResponseCallback"],
  "non_claims": ["layout evidence only; not public SDK readiness"],
  "promotion_gate": {
    "ready": true,
    "blockers": [],
    "ready_scope": "layout_only",
    "layout_ready": true,
    "promotion_ready": false,
    "public_sdk_ready": false,
    "runtime_ready": false
  },
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
  "evidence_scope": "second_source_layout_evidence_only",
  "not_promoted_surfaces": ["ObeliskApi.RegisterTransferPolicyCallback"],
  "non_claims": ["layout evidence only; not public SDK readiness"],
  "promotion_gate": {
    "ready": true,
    "blockers": [],
    "ready_scope": "layout_only",
    "layout_ready": true,
    "promotion_ready": false,
    "public_sdk_ready": false,
    "runtime_ready": false
  },
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
  "evidence_scope": "second_source_layout_evidence_only",
  "not_promoted_surfaces": ["ObeliskApi.RegisterCommandResponseCallback"],
  "non_claims": ["layout evidence only; not public SDK readiness"],
  "promotion_gate": {
    "ready": true,
    "blockers": [],
    "ready_scope": "layout_only",
    "layout_ready": true,
    "promotion_ready": false,
    "public_sdk_ready": false,
    "runtime_ready": false
  },
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

write_minimal_only_ufunction_second_source_root() {
    local root="$1"
    local base_root="tests/fixtures/ufunction_snapshots/7e7ded49e0c6"
    local rel_path

    for rel_path in \
        "sdk_inventory/PrimalItem.CanUse.snapshot.json" \
        "sdk_inventory/PrimalItem.AllowRemoteAddToInventory.snapshot.json" \
        "sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json" \
        "sdk_structures/PrimalStructure.IsAllowedToDemolish.snapshot.json"; do
        mkdir -p "${root}/7e7ded49e0c6/$(dirname "${rel_path}")"
        cp "${base_root}/${rel_path}" "${root}/7e7ded49e0c6/${rel_path}"
    done

    python3 - "${root}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for path in root.rglob("*.snapshot.json"):
    payload = json.loads(path.read_text(encoding="utf-8"))
    evidence = payload["evidence"]
    evidence["artifact_sha256"] = "2" * 64
    evidence["capture_id"] = "second_source_minimal_only"
    evidence["evidence_pack_id"] = "second_source_minimal_only_pack"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

assert_public_rc_report_state() {
    local report_path="$1"
    local target_set="$2"
    local expected_ready="$3"
    local expected_accepted="$4"
    local expected_inconclusive="$5"

    python3 - \
        "${report_path}" \
        "${target_set}" \
        "${expected_ready}" \
        "${expected_accepted}" \
        "${expected_inconclusive}" <<'PY'
import json
import sys

report_path, target_set, expected_ready_text, expected_accepted_text, expected_inconclusive_text = sys.argv[1:6]
with open(report_path, "r", encoding="utf-8") as handle:
    report = json.load(handle)

expected_ready = expected_ready_text == "true"
expected_accepted = int(expected_accepted_text)
expected_inconclusive = int(expected_inconclusive_text)
errors = []

if target_set not in report.get("target_sets", []):
    errors.append(f"target_sets missing {target_set}")
promotion_gate = report.get("promotion_gate", {})
if promotion_gate.get("ready") is not expected_ready:
    errors.append(f"promotion_gate.ready expected {expected_ready}")
totals = report.get("totals", {})
if totals.get("second_source_accepted") != expected_accepted:
    errors.append(f"second_source_accepted expected {expected_accepted}")
if totals.get("second_source_inconclusive") != expected_inconclusive:
    errors.append(f"second_source_inconclusive expected {expected_inconclusive}")
if not expected_ready:
    blocker_reasons = {
        blocker.get("reason")
        for blocker in promotion_gate.get("blockers", [])
        if isinstance(blocker, dict)
    }
    if "inconclusive_second_source" not in blocker_reasons:
        errors.append("missing inconclusive_second_source blocker")

if errors:
    for error in errors:
        print(f"{target_set} report state invalid: {error}", file=sys.stderr)
    raise SystemExit(1)
PY
}

assert_minimal_only_ufunction_root_does_not_satisfy_public_rc_target_sets() {
    local candidate_root="${TEST_TEMP_ROOT}/minimal-only-ufunction-second-source"
    local REQUIRE_SECOND_SOURCE_READINESS=1
    local SCRIPTSTRUCT_SECOND_SOURCE_ROOT=""
    local PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS=(
        "minimal-second-source-intake"
        "structure-observer-intake"
        "item-return-only-policy-slice"
        "chat-message-intake"
    )
    local UFUNCTION_SECOND_SOURCE_TARGET_SETS=()
    local SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=()
    local target_set
    local output
    local report_path
    local second_source_status=0

    write_minimal_only_ufunction_second_source_root "${candidate_root}"
    eval "${second_source_default_block}"

    RELEASE_CHECK_ROOT="${TEST_TEMP_ROOT}/release-root-minimal-only-rc"
    SECOND_SOURCE_REPORT_DIR="${RELEASE_CHECK_ROOT}/second-source-readiness-reports"
    mkdir -p "${RELEASE_CHECK_ROOT}"

    for target_set in "${UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}"; do
        set +e
        output="$(
            run_second_source_readiness \
                "ufunction-${target_set}" \
                tests/fixtures/ufunction_snapshots \
                "${target_set}" \
                "${candidate_root}" 2>&1
        )"
        status=$?
        set -e
        second_source_status="$(merge_second_source_status "${second_source_status}" "${status}")"

        report_path="${SECOND_SOURCE_REPORT_DIR}/ufunction-${target_set}-second-source-readiness.json"
        if [[ ! -f "${report_path}" ]]; then
            printf 'expected public RC second-source report for %s\n%s\n' \
                "${target_set}" "${output}" >&2
            exit 1
        fi

        case "${target_set}" in
            minimal-second-source-intake)
                if [[ "${status}" -ne 0 ]]; then
                    printf 'minimal-only UFunction second source should satisfy only minimal RC target set, got %s\n%s\n' \
                        "${status}" "${output}" >&2
                    exit 1
                fi
                assert_public_rc_report_state "${report_path}" "${target_set}" true 4 0
                ;;
            structure-observer-intake)
                if [[ "${status}" -eq 0 ]]; then
                    printf 'minimal-only UFunction second source unexpectedly satisfied structure observer RC target set\n%s\n' \
                        "${output}" >&2
                    exit 1
                fi
                assert_public_rc_report_state "${report_path}" "${target_set}" false 2 4
                ;;
            item-return-only-policy-slice)
                if [[ "${status}" -eq 0 ]]; then
                    printf 'minimal-only UFunction second source unexpectedly satisfied item return RC target set\n%s\n' \
                        "${output}" >&2
                    exit 1
                fi
                assert_public_rc_report_state "${report_path}" "${target_set}" false 0 3
                ;;
            chat-message-intake)
                if [[ "${status}" -eq 0 ]]; then
                    printf 'minimal-only UFunction second source unexpectedly satisfied chat message RC target set\n%s\n' \
                        "${output}" >&2
                    exit 1
                fi
                assert_public_rc_report_state "${report_path}" "${target_set}" false 0 1
                ;;
            *)
                printf 'unexpected public RC UFunction target set in minimal-only guardrail: %s\n' \
                    "${target_set}" >&2
                exit 1
                ;;
        esac
    done

    if [[ "${second_source_status}" -eq 0 ]]; then
        printf 'minimal-only UFunction second source unexpectedly satisfied all public RC target sets\n' >&2
        exit 1
    fi
}

assert_minimal_only_ufunction_root_does_not_satisfy_public_rc_target_sets

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

assert_report_dir_validates() {
    local path="$1"
    local output

    set +e
    output="$(validate_second_source_report_dir "${path}" 2>&1)"
    status=$?
    set -e
    if [[ "${status}" -ne 0 ]]; then
        printf 'expected report dir to validate: %s\n%s\n' "${path}" "${output}" >&2
        exit 1
    fi
}

assert_report_dir_rejected() {
    local path="$1"
    local expected="$2"
    local output

    set +e
    output="$(validate_second_source_report_dir "${path}" 2>&1)"
    status=$?
    set -e
    if [[ "${status}" -ne 2 ]]; then
        printf 'expected report dir rejection for %s, got %s\n%s\n' \
            "${path}" "${status}" "${output}" >&2
        exit 1
    fi
    if ! grep -Fq -- "${expected}" <<<"${output}"; then
        printf 'missing report dir rejection text for %s\n%s\n' "${path}" "${output}" >&2
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
assert_report_dir_validates "local/release-readiness-options-test"
assert_report_dir_validates "local/release-readiness-options-test/"
assert_report_dir_rejected \
    "second-source-reports" \
    "Second-source report dir inside the repository must be ignored"
assert_report_dir_rejected \
    "." \
    "Second-source report dir inside the repository must be ignored"

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
        --ufunction-second-source-target-set minimal-second-source-intake 2>&1
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
report_dir_without_gate_output="$(
    scripts/check_release_readiness.sh \
        --second-source-report-dir /tmp/obelisk-second-source-reports 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected report-dir validation to exit 2, got %s\n%s\n' \
        "${status}" "${report_dir_without_gate_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${report_dir_without_gate_output}"; then
    printf 'missing report-dir option validation error\n%s\n' "${report_dir_without_gate_output}" >&2
    exit 1
fi

set +e
env_root_without_gate_output="$(
    OBELISK_UFUNCTION_SECOND_SOURCE_ROOT=/tmp/obelisk-candidate \
        scripts/check_release_readiness.sh 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected env root validation to exit 2, got %s\n%s\n' \
        "${status}" "${env_root_without_gate_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${env_root_without_gate_output}"; then
    printf 'missing env root option validation error\n%s\n' "${env_root_without_gate_output}" >&2
    exit 1
fi

set +e
env_report_dir_without_gate_output="$(
    OBELISK_SECOND_SOURCE_REPORT_DIR=/tmp/obelisk-second-source-reports \
        scripts/check_release_readiness.sh 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected env report-dir validation to exit 2, got %s\n%s\n' \
        "${status}" "${env_report_dir_without_gate_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${env_report_dir_without_gate_output}"; then
    printf 'missing env report-dir option validation error\n%s\n' "${env_report_dir_without_gate_output}" >&2
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
