#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

SERVER_ROOT="/servidor/ark"
APPROVED_OFFLINE_WORKSPACE_ROOT="/servidor/ark/workspace-offline"
BUILD_DIR="${OBELISK_BUILD_DIR:-build}"
JOBS="${OBELISK_BUILD_JOBS:-$(nproc)}"
RELEASE_CHECK_ROOT=""
LAYOUT_CHECK_ROOT=""
ALLOW_DIRTY=0
ALLOW_CROSS_REF_SECOND_SOURCE_ROOT=0
REQUIRE_SECOND_SOURCE_READINESS=0
REQUIRE_V1_SDK_COMPLETION=0
V1_SDK_RELEASE_STATEMENT=""
UFUNCTION_SECOND_SOURCE_ROOT="${OBELISK_UFUNCTION_SECOND_SOURCE_ROOT:-}"
SCRIPTSTRUCT_SECOND_SOURCE_ROOT="${OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT:-}"
SECOND_SOURCE_REPORT_DIR="${OBELISK_SECOND_SOURCE_REPORT_DIR:-}"
UFUNCTION_SECOND_SOURCE_TARGET_SETS=()
SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=()
PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS=(
    "minimal-second-source-intake"
    "structure-observer-intake"
    "item-return-only-policy-slice"
    "chat-message-intake"
)
PRODUCTION_FORBIDDEN_SYMBOL_PATTERNS=(
    "ForTesting"
    "SetNextRegistrationIdForTesting"
    "ApiCapabilitiesForTesting"
    "SetNextTimerIdForTesting"
    "MissionCopiedBoolEventDispatcher"
    "MissionCopiedBoolEvent"
    "TransferBAccept"
    "TransferBAcceptEventDispatcher"
    "TransferCopiedBool"
    "ProcessEventTransferReflection"
    "SetPluginCallbackCleanupFailure"
    "SetPluginRetentionFailure"
    "ClearPluginOwnerLifecycle"
)

is_under_path() {
    local path="$1"
    local parent="$2"

    [[ "${path}" == "${parent}" || "${path}" == "${parent}/"* ]]
}

is_approved_offline_workspace_path() {
    local path="$1"
    local resolved_path
    local resolved_workspace

    resolved_path="$(realpath -m "${path}")"
    resolved_workspace="$(realpath -m "${APPROVED_OFFLINE_WORKSPACE_ROOT}")"
    is_under_path "${resolved_path}" "${resolved_workspace}"
}

reject_protected_path() {
    local label="$1"
    local action="$2"
    local path="$3"
    local absolute_path
    local resolved_path

    absolute_path="$(realpath -s -m "${path}")"
    if is_under_path "${absolute_path}" "${SERVER_ROOT}" && \
        ! is_approved_offline_workspace_path "${absolute_path}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${absolute_path}" >&2
        exit 2
    fi

    resolved_path="$(realpath -m "${path}")"
    if is_under_path "${resolved_path}" "${SERVER_ROOT}" && \
        ! is_approved_offline_workspace_path "${resolved_path}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${resolved_path}" >&2
        exit 2
    fi
}

reject_non_release_second_source_target_set() {
    local target_set="$1"
    local label="$2"
    local normalized_target_set
    local classification
    local classification_status

    normalized_target_set="${target_set,,}"
    if [[ "${normalized_target_set}" == *nextgen* || "${normalized_target_set}" == *plugin-hub* ]]; then
        if [[ "${normalized_target_set}" == *planning* || "${normalized_target_set}" == *guidance* ]]; then
            printf '%s is planning/guidance-only and cannot be used as a release readiness %s target set.\n' \
                "${target_set}" "${label}" >&2
            printf 'Promote a separate release/public target set through the documented SDK and second-source gates instead.\n' >&2
            exit 2
        fi
    fi

    set +e
    classification="$(
        python3 - "${target_set}" <<'PY'
import pathlib
import sys

repo_root = pathlib.Path.cwd()
sys.path.insert(0, str(repo_root / "scripts"))

from reflection_target_sets import target_set_readiness_classification

try:
    print(target_set_readiness_classification(sys.argv[1]))
except KeyError:
    raise SystemExit(3)
PY
    )"
    classification_status=$?
    set -e

    if [[ "${classification_status}" -ne 0 ]]; then
        printf '%s is not a known %s target set.\n' "${target_set}" "${label}" >&2
        printf 'Use scripts/compare_reflection_snapshots.py --list-target-sets to inspect the classified target sets.\n' >&2
        exit 2
    fi

    if [[ "${classification}" == "release_readiness" ]]; then
        return
    fi

    if [[ "${classification}" == "planning_only" ]]; then
        printf '%s is planning/guidance-only and cannot be used as a release readiness %s target set.\n' \
            "${target_set}" "${label}" >&2
    elif [[ "${classification}" == "internal_layout_only" ]]; then
        printf '%s is internal/layout-only and cannot be used as a release readiness %s target set.\n' \
            "${target_set}" "${label}" >&2
    else
        printf '%s is %s and cannot be used as a release readiness %s target set.\n' \
            "${target_set}" "${classification}" "${label}" >&2
    fi
    printf 'Promote a separate release/public target set through the documented SDK and second-source gates instead.\n' >&2
    exit 2
}

add_ufunction_second_source_target_set() {
    local target_set="$1"

    reject_non_release_second_source_target_set "${target_set}" "UFunction"
    UFUNCTION_SECOND_SOURCE_TARGET_SETS+=("${target_set}")
}

add_scriptstruct_second_source_target_set() {
    local target_set="$1"

    reject_non_release_second_source_target_set "${target_set}" "ScriptStruct"
    SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS+=("${target_set}")
}

validate_second_source_report_dir() {
    local report_dir="$1"

    reject_protected_path "--second-source-report-dir" "write under" "${report_dir}"

    local report_dir_abs
    local repo_abs
    report_dir_abs="$(realpath -m "${report_dir}")"
    repo_abs="$(realpath -m "${REPO_ROOT}")"
    if [[ "${report_dir_abs}" == "${repo_abs}" || "${report_dir_abs}" == "${repo_abs}/"* ]]; then
        if [[ "${report_dir_abs}" == "${repo_abs}" ]]; then
            printf 'Second-source report dir inside the repository must be ignored: %s\n' \
                "${report_dir}" >&2
            exit 2
        fi

        local report_dir_rel
        report_dir_rel="${report_dir_abs#${repo_abs}/}"
        if ! git check-ignore -q -- "${report_dir_rel}" && \
            ! git check-ignore -q -- "${report_dir_rel}/"; then
            printf 'Second-source report dir inside the repository must be ignored: %s\n' \
                "${report_dir}" >&2
            exit 2
        fi
    fi
}

validate_second_source_root_commit() {
    local label="$1"
    local root="$2"

    if [[ "${ALLOW_CROSS_REF_SECOND_SOURCE_ROOT}" == "1" || -z "${root}" ]]; then
        return
    fi

    local head
    head="$(git rev-parse HEAD)"

    python3 - "${label}" "${root}" "${head}" <<'PY'
import json
import pathlib
import sys

label, root_text, head = sys.argv[1:4]
root = pathlib.Path(root_text)
paths = [root] if root.is_file() else sorted(path for path in root.rglob("*.snapshot.json") if path.is_file())
errors = []

if not paths:
    errors.append(f"{label} contains no *.snapshot.json files: {root}")

for path in paths:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot load snapshot JSON: {exc}")
        continue

    evidence = payload.get("evidence")
    commit = evidence.get("obelisk_commit") if isinstance(evidence, dict) else None
    if not isinstance(commit, str) or len(commit) < 7:
        errors.append(f"{path}: evidence.obelisk_commit must be a commit prefix")
        continue
    if not head.startswith(commit):
        errors.append(f"{path}: evidence.obelisk_commit {commit!r} does not match current HEAD {head[:12]}")

if errors:
    print(
        f"{label} must be regenerated for the current validated HEAD, or rerun with "
        "--allow-cross-ref-second-source-root for explicit historical tag recovery.",
        file=sys.stderr,
    )
    for error in errors[:8]:
        print(error, file=sys.stderr)
    if len(errors) > 8:
        print(f"... {len(errors) - 8} more error(s)", file=sys.stderr)
    raise SystemExit(2)
PY
}

preflight_ufunction_second_source_readiness() {
    if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" != "1" ]]; then
        return
    fi

    if [[ -z "${UFUNCTION_SECOND_SOURCE_ROOT}" ]]; then
        echo "--require-second-source-readiness requires --ufunction-second-source-root for the public RC UFunction target sets." >&2
        exit 2
    fi

    local command=(
        python3 scripts/compare_reflection_snapshots.py
        --base-root tests/fixtures/ufunction_snapshots
        --candidate-root "${UFUNCTION_SECOND_SOURCE_ROOT}"
        --readiness-report
    )
    local target_set
    for target_set in "${UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}"; do
        command+=(--target-set "${target_set}")
    done
    command+=(--fail-on-readiness-gaps --json)

    local report_path
    report_path="$(mktemp /tmp/obelisk-ufunction-second-source-preflight.XXXXXX.json)"
    local status
    set +e
    "${command[@]}" >"${report_path}"
    status=$?
    set -e

    if [[ "${status}" -ne 0 ]]; then
        printf 'UFunction second-source root failed pre-build readiness metadata preflight for requested target sets.\n' >&2
        python3 - "${report_path}" <<'PY' >&2 || true
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        report = json.load(handle)
except (OSError, json.JSONDecodeError):
    raise SystemExit(0)

promotion_gate = report.get("promotion_gate")
blockers = promotion_gate.get("blockers") if isinstance(promotion_gate, dict) else None
if not isinstance(blockers, list):
    raise SystemExit(0)

for blocker in blockers[:8]:
    if not isinstance(blocker, dict):
        continue
    reason = blocker.get("reason", "<unknown>")
    count = blocker.get("count")
    if isinstance(count, int):
        print(f"UFunction second-source preflight blocker: {reason} (count={count})")
    else:
        print(f"UFunction second-source preflight blocker: {reason}")
    targets = blocker.get("targets")
    if isinstance(targets, list):
        for target in targets[:8]:
            print(f"  target: {target}")
PY
        rm -f "${report_path}"
        printf 'Regenerate the root for the intended release ref with complete artifact identity, current BoolProperty tail metadata, and unambiguous target-set coverage.\n' >&2
        exit "${status}"
    fi

    rm -f "${report_path}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        --allow-cross-ref-second-source-root)
            ALLOW_CROSS_REF_SECOND_SOURCE_ROOT=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: scripts/check_release_readiness.sh [--allow-dirty] [--require-second-source-readiness]
                                          [--require-v1-sdk-completion]
                                          [--v1-sdk-release-statement <path>]
                                          [--allow-cross-ref-second-source-root]
                                          [--ufunction-second-source-root <path>]
                                          [--scriptstruct-second-source-root <path>]
                                          [--ufunction-second-source-target-set <name>]
                                          [--scriptstruct-second-source-target-set <name>]
                                          [--second-source-report-dir <path>]

Runs the local release-readiness baseline gate. It owns build, CTest, script tests,
production libobelisk.so symbol surface checks, install/SDK dry-runs, read-only CLI
status, and clean-tree validation. By default the command fails if tracked or untracked
non-ignored files are present before or after validation. Ignored build/cache directories
are allowed. Gameplay/module second-source promotion gates run only when
--require-second-source-readiness is supplied.
The v1 complete-SDK claim gate runs only when --require-v1-sdk-completion is supplied.
Passing this gate is not live-ops approval, Plugin Hub readiness/publication,
support-tier activation, runtime readiness, a stable SDK claim, or v1 SDK completion
unless the exact additional gate says so.

Options:
  --allow-dirty                     Permit a dirty worktree while developing the release gate itself.
  --allow-cross-ref-second-source-root
                                    Permit second-source snapshots whose evidence.obelisk_commit
                                    does not match the current validated HEAD. Intended only for
                                    explicit historical tag recovery.
  --require-second-source-readiness Fail if focused reflection promotion target sets lack complete
                                    second-source evidence.
  --require-v1-sdk-completion       Fail unless docs/public_sdk_surfaces.json allows a complete
                                    v1.0 SDK claim. This is separate from baseline release readiness.
  --v1-sdk-release-statement        Reviewed v1 SDK release statement naming excluded/post-v1 blockers.
  --ufunction-second-source-root    Candidate UFunction snapshot root for second-source promotion.
  --scriptstruct-second-source-root Candidate ScriptStruct snapshot root for second-source promotion.
  --ufunction-second-source-target-set
                                    UFunction target set to gate. Repeat for each promoted module.
                                    Defaults to the public RC target sets:
                                    minimal-second-source-intake,
                                    structure-observer-intake,
                                    item-return-only-policy-slice, and chat-message-intake.
  --scriptstruct-second-source-target-set
                                    ScriptStruct target set to gate. Repeat for each promoted module.
                                    No default; ScriptStruct promotion requires explicit opt-in.
  --second-source-report-dir        Directory where JSON second-source readiness reports are written.
                                    Defaults to a temporary directory under the release check root.
  -h, --help                        Show this help.

Environment alternatives:
  OBELISK_UFUNCTION_SECOND_SOURCE_ROOT
  OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT
  OBELISK_SECOND_SOURCE_REPORT_DIR
EOF
            exit 0
            ;;
        --require-second-source-readiness)
            REQUIRE_SECOND_SOURCE_READINESS=1
            shift
            ;;
        --require-v1-sdk-completion)
            REQUIRE_V1_SDK_COMPLETION=1
            shift
            ;;
        --v1-sdk-release-statement)
            V1_SDK_RELEASE_STATEMENT="${2:?--v1-sdk-release-statement requires a path}"
            shift 2
            ;;
        --ufunction-second-source-root)
            UFUNCTION_SECOND_SOURCE_ROOT="${2:?--ufunction-second-source-root requires a path}"
            shift 2
            ;;
        --scriptstruct-second-source-root)
            SCRIPTSTRUCT_SECOND_SOURCE_ROOT="${2:?--scriptstruct-second-source-root requires a path}"
            shift 2
            ;;
        --second-source-report-dir)
            SECOND_SOURCE_REPORT_DIR="${2:?--second-source-report-dir requires a path}"
            shift 2
            ;;
        --ufunction-second-source-target-set)
            add_ufunction_second_source_target_set "${2:?--ufunction-second-source-target-set requires a name}"
            shift 2
            ;;
        --scriptstruct-second-source-target-set)
            add_scriptstruct_second_source_target_set "${2:?--scriptstruct-second-source-target-set requires a name}"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -n "${UFUNCTION_SECOND_SOURCE_ROOT}${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}${SECOND_SOURCE_REPORT_DIR}" \
    || "${#UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}" -gt 0 \
    || "${#SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS[@]}" -gt 0 ]]; then
    second_source_options_present=1
else
    second_source_options_present=0
fi

if [[ "${second_source_options_present}" == "1" \
    && "${REQUIRE_SECOND_SOURCE_READINESS}" != "1" ]]; then
    echo "Second-source roots, target sets, or report dirs require --require-second-source-readiness." >&2
    exit 2
fi

if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" ]]; then
    for required_target_set in "${PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}"; do
        target_set_present=0
        for target_set in "${UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}"; do
            if [[ "${target_set}" == "${required_target_set}" ]]; then
                target_set_present=1
                break
            fi
        done
        if [[ "${target_set_present}" == "0" ]]; then
            UFUNCTION_SECOND_SOURCE_TARGET_SETS+=("${required_target_set}")
        fi
    done
    if [[ -n "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}" && "${#SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS[@]}" -eq 0 ]]; then
        echo "--scriptstruct-second-source-root requires at least one --scriptstruct-second-source-target-set." >&2
        exit 2
    fi
fi

if [[ -n "${UFUNCTION_SECOND_SOURCE_ROOT}" ]]; then
    reject_protected_path "--ufunction-second-source-root" "read from" "${UFUNCTION_SECOND_SOURCE_ROOT}"
    validate_second_source_root_commit "--ufunction-second-source-root" "${UFUNCTION_SECOND_SOURCE_ROOT}"
fi
if [[ -n "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}" ]]; then
    reject_protected_path "--scriptstruct-second-source-root" "read from" "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}"
    validate_second_source_root_commit "--scriptstruct-second-source-root" "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}"
fi
if [[ -n "${SECOND_SOURCE_REPORT_DIR}" ]]; then
    validate_second_source_report_dir "${SECOND_SOURCE_REPORT_DIR}"
fi
if [[ -n "${V1_SDK_RELEASE_STATEMENT}" && "${REQUIRE_V1_SDK_COMPLETION}" != "1" ]]; then
    echo "--v1-sdk-release-statement requires --require-v1-sdk-completion." >&2
    exit 2
fi
if [[ "${REQUIRE_V1_SDK_COMPLETION}" == "1" && -z "${V1_SDK_RELEASE_STATEMENT}" ]]; then
    echo "--require-v1-sdk-completion requires --v1-sdk-release-statement." >&2
    exit 2
fi
if [[ -n "${V1_SDK_RELEASE_STATEMENT}" ]]; then
    reject_protected_path "--v1-sdk-release-statement" "read from" "${V1_SDK_RELEASE_STATEMENT}"
fi
preflight_ufunction_second_source_readiness

cleanup() {
    if [[ "${OBELISK_KEEP_RELEASE_CHECK_ROOTS:-0}" != "1" ]]; then
        if [[ -n "${RELEASE_CHECK_ROOT}" ]]; then
            rm -rf "${RELEASE_CHECK_ROOT}"
        fi
        if [[ -n "${LAYOUT_CHECK_ROOT}" ]]; then
            rm -rf "${LAYOUT_CHECK_ROOT}"
        fi
    else
        printf 'keeping release check roots:\n  %s\n  %s\n' "${RELEASE_CHECK_ROOT}" "${LAYOUT_CHECK_ROOT}"
    fi
}
trap cleanup EXIT

RELEASE_CHECK_ROOT="$(mktemp -d /tmp/obelisk-release-check.XXXXXX)"
LAYOUT_CHECK_ROOT="$(mktemp -d /tmp/obelisk-layout-check.XXXXXX)"
if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" && -z "${SECOND_SOURCE_REPORT_DIR}" ]]; then
    SECOND_SOURCE_REPORT_DIR="${RELEASE_CHECK_ROOT}/second-source-readiness-reports"
fi

run_step() {
    printf '\n==> %s\n' "$*"
    "$@"
}

if [[ "${REQUIRE_V1_SDK_COMPLETION}" == "1" ]]; then
    run_step python3 scripts/check_public_sdk_v1_completion.py \
        --release-statement "${V1_SDK_RELEASE_STATEMENT}"
fi

validate_second_source_readiness_json() {
    local report_path="$1"
    local target_set="$2"
    local label="$3"

    python3 - "${report_path}" "${target_set}" "${label}" <<'PY'
import json
import sys

report_path, target_set, label = sys.argv[1:4]
errors = []

if label.startswith("ufunction-"):
    expected_module_schema = "ufunction"
    expected_target_prefix = "obelisk.ufunction-chain.snapshot.v1:"
elif label.startswith("scriptstruct-"):
    expected_module_schema = "scriptstruct"
    expected_target_prefix = "obelisk.scriptstruct-chain.snapshot.v1:"
else:
    expected_module_schema = None
    expected_target_prefix = None

try:
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
except (OSError, json.JSONDecodeError) as exc:
    print(f"{label} readiness JSON could not be loaded: {exc}", file=sys.stderr)
    raise SystemExit(1)

if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
    errors.append("schema must be obelisk.reflection-snapshot-readiness.v1")

if report.get("gate_mode") != "second_source_promotion":
    errors.append("gate_mode must be second_source_promotion")

if report.get("second_source_status") != "compared":
    errors.append("second_source_status must be compared")

promotion_gate = report.get("promotion_gate")
if not isinstance(promotion_gate, dict):
    errors.append("promotion_gate must be an object")
else:
    if promotion_gate.get("ready") is not True:
        errors.append("promotion_gate.ready must be true")
    if promotion_gate.get("blockers") != []:
        errors.append("promotion_gate.blockers must be empty")
    if promotion_gate.get("ready_scope") != "layout_only":
        errors.append("promotion_gate.ready_scope must be layout_only")
    if promotion_gate.get("layout_ready") is not True:
        errors.append("promotion_gate.layout_ready must be true")
    if promotion_gate.get("promotion_ready") is not False:
        errors.append("promotion_gate.promotion_ready must be false")
    if promotion_gate.get("public_sdk_ready") is not False:
        errors.append("promotion_gate.public_sdk_ready must be false")
    if promotion_gate.get("runtime_ready") is not False:
        errors.append("promotion_gate.runtime_ready must be false")

if report.get("evidence_scope") != "second_source_layout_evidence_only":
    errors.append("evidence_scope must be second_source_layout_evidence_only")

not_promoted_surfaces = report.get("not_promoted_surfaces")
if not isinstance(not_promoted_surfaces, list) or not not_promoted_surfaces:
    errors.append("not_promoted_surfaces must be a non-empty list")

non_claims = report.get("non_claims")
if not isinstance(non_claims, list) or not non_claims:
    errors.append("non_claims must be a non-empty list")

target_sets = report.get("target_sets")
if not isinstance(target_sets, list) or target_set not in target_sets:
    errors.append(f"target_sets must include {target_set}")

totals = report.get("totals")
if not isinstance(totals, dict):
    errors.append("totals must be an object")
else:
    required_total_fields = (
        "targets",
        "comparable",
        "blocked",
        "second_source_accepted",
        "second_source_rejected",
        "second_source_inconclusive",
        "second_source_missing",
    )
    for field in required_total_fields:
        if type(totals.get(field)) is not int:
            errors.append(f"totals.{field} must be an integer")

    targets = totals.get("targets")
    comparable = totals.get("comparable")
    blocked = totals.get("blocked")
    accepted = totals.get("second_source_accepted")
    rejected = totals.get("second_source_rejected")
    inconclusive = totals.get("second_source_inconclusive")
    missing = totals.get("second_source_missing")
    if type(targets) is int and targets <= 0:
        errors.append("totals.targets must be greater than 0")
    if type(targets) is int and type(comparable) is int and comparable != targets:
        errors.append("totals.comparable must equal totals.targets")
    if type(blocked) is int and blocked != 0:
        errors.append("totals.blocked must be 0")
    if type(targets) is int and type(accepted) is int and accepted != targets:
        errors.append("totals.second_source_accepted must equal totals.targets")
    if type(rejected) is int and rejected != 0:
        errors.append("totals.second_source_rejected must be 0")
    if type(inconclusive) is int and inconclusive != 0:
        errors.append("totals.second_source_inconclusive must be 0")
    if type(missing) is int and missing != 0:
        errors.append("totals.second_source_missing must be 0")

modules = report.get("modules")
if not isinstance(modules, list) or not modules:
    errors.append("modules must be a non-empty list")
else:
    module_sums = {
        "targets": 0,
        "comparable": 0,
        "blocked": 0,
        "second_source_accepted": 0,
        "second_source_rejected": 0,
        "second_source_inconclusive": 0,
        "second_source_missing": 0,
    }
    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            errors.append(f"modules[{index}] must be an object")
            continue
        if expected_module_schema is not None and module.get("schema") != expected_module_schema:
            errors.append(f"modules[{index}].schema must be {expected_module_schema}")
        for field in ("targets", "comparable", "blocked"):
            value = module.get(field)
            if type(value) is not int:
                errors.append(f"modules[{index}].{field} must be an integer")
            else:
                module_sums[field] += value
        second_source = module.get("second_source")
        if not isinstance(second_source, dict):
            errors.append(f"modules[{index}].second_source must be an object")
        else:
            for status in ("accepted", "rejected", "inconclusive", "missing"):
                value = second_source.get(status)
                if type(value) is not int:
                    errors.append(f"modules[{index}].second_source.{status} must be an integer")
                else:
                    module_sums[f"second_source_{status}"] += value
        details = module.get("target_details")
        if not isinstance(details, list) or not details:
            errors.append(f"modules[{index}].target_details must be a non-empty list")
            continue
        if type(module.get("targets")) is int and len(details) != module["targets"]:
            errors.append(f"modules[{index}].target_details length must equal module targets")
        for detail_index, detail in enumerate(details):
            if not isinstance(detail, dict):
                errors.append(f"modules[{index}].target_details[{detail_index}] must be an object")
                continue
            if detail.get("comparable") is not True:
                errors.append(f"modules[{index}].target_details[{detail_index}].comparable must be true")
            if detail.get("block_reasons") != []:
                errors.append(f"modules[{index}].target_details[{detail_index}].block_reasons must be empty")
            if detail.get("second_source_status") != "accepted":
                errors.append(
                    f"modules[{index}].target_details[{detail_index}].second_source_status must be accepted"
                )
            if expected_target_prefix is not None and not str(detail.get("target", "")).startswith(
                expected_target_prefix
            ):
                errors.append(
                    f"modules[{index}].target_details[{detail_index}].target must start with "
                    f"{expected_target_prefix}"
                )

    if isinstance(totals, dict):
        total_to_module_sum = {
            "targets": "targets",
            "comparable": "comparable",
            "blocked": "blocked",
            "second_source_accepted": "second_source_accepted",
            "second_source_rejected": "second_source_rejected",
            "second_source_inconclusive": "second_source_inconclusive",
            "second_source_missing": "second_source_missing",
        }
        for total_field, module_field in total_to_module_sum.items():
            if type(totals.get(total_field)) is int and totals[total_field] != module_sums[module_field]:
                errors.append(f"totals.{total_field} must match module sums")

if errors:
    for error in errors:
        print(f"{label} readiness JSON invalid: {error}", file=sys.stderr)
    raise SystemExit(1)
PY
}

run_second_source_readiness() {
    local label="$1"
    local base_root="$2"
    local target_set="$3"
    local candidate_root="$4"

    local command=(
        python3 scripts/compare_reflection_snapshots.py
        --base-root "${base_root}"
        --readiness-report
        --target-set "${target_set}"
    )
    if [[ -n "${candidate_root}" ]]; then
        command+=(--candidate-root "${candidate_root}")
    fi

    mkdir -p "${SECOND_SOURCE_REPORT_DIR}"
    local report_path="${SECOND_SOURCE_REPORT_DIR}/${label}-second-source-readiness.json"
    set +e
    "${command[@]}" --fail-on-readiness-gaps --json > "${report_path}"
    local report_status=$?
    set -e
    if [[ "${report_status}" -eq 0 ]]; then
        printf 'wrote %s\n' "${report_path}"
    else
        printf 'wrote %s (gate exit=%s)\n' "${report_path}" "${report_status}"
    fi

    set +e
    validate_second_source_readiness_json "${report_path}" "${target_set}" "${label}"
    local validation_status=$?
    set -e

    set +e
    run_step "${command[@]}" --fail-on-readiness-gaps
    local text_status=$?
    set -e

    local readiness_status=0
    readiness_status="$(merge_second_source_status "${readiness_status}" "${report_status}")"
    readiness_status="$(merge_second_source_status "${readiness_status}" "${validation_status}")"
    readiness_status="$(merge_second_source_status "${readiness_status}" "${text_status}")"
    return "${readiness_status}"
}

merge_second_source_status() {
    local current_status="$1"
    local next_status="$2"

    if [[ "${next_status}" -eq 0 ]]; then
        printf '%s\n' "${current_status}"
        return
    fi
    if [[ "${current_status}" -eq 0 ]]; then
        printf '%s\n' "${next_status}"
        return
    fi
    if [[ "${current_status}" -eq 1 || "${next_status}" -eq 1 ]]; then
        printf '1\n'
        return
    fi
    printf '%s\n' "${current_status}"
}

check_clean_tree() {
    if [[ "${ALLOW_DIRTY}" == "1" ]]; then
        return
    fi

    local status
    status="$(git status --porcelain --untracked-files=normal)"
    if [[ -n "${status}" ]]; then
        printf 'Release readiness requires a clean worktree. Current changes:\n%s\n' "${status}" >&2
        exit 1
    fi
}

check_production_runtime_symbols() {
    local runtime_library="${BUILD_DIR}/libobelisk.so"

    if [[ ! -f "${runtime_library}" ]]; then
        printf 'Production runtime library missing after build: %s\n' "${runtime_library}" >&2
        exit 1
    fi
    if ! command -v nm >/dev/null 2>&1; then
        echo "Release readiness requires nm to inspect production libobelisk.so symbols." >&2
        exit 1
    fi

    local symbol_dump
    symbol_dump="$(nm -C "${runtime_library}")"

    local pattern
    local forbidden_matches=""
    for pattern in "${PRODUCTION_FORBIDDEN_SYMBOL_PATTERNS[@]}"; do
        if grep -F -- "${pattern}" <<<"${symbol_dump}" >/dev/null; then
            forbidden_matches+="${pattern}"$'\n'
        fi
    done

    if [[ -n "${forbidden_matches}" ]]; then
        printf 'Production libobelisk.so exposes test-only/internal symbols:\n%s' \
            "${forbidden_matches}" >&2
        exit 1
    fi
}

check_clean_tree
run_step cmake -S . -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DOBELISK_BUILD_EXPERIMENTAL_PLUGINS=OFF
run_step cmake --build "${BUILD_DIR}" -j"${JOBS}"
run_step check_production_runtime_symbols
run_step ctest --test-dir "${BUILD_DIR}" --output-on-failure
run_step scripts/run_script_tests.sh
run_step python3 scripts/check_item_return_only_readiness.py --json
run_step python3 scripts/check_inventory_action_fixture_boundary.py --json
if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" ]]; then
    second_source_status=0
    for target_set in "${UFUNCTION_SECOND_SOURCE_TARGET_SETS[@]}"; do
        set +e
        run_second_source_readiness \
            "ufunction-${target_set}" \
            tests/fixtures/ufunction_snapshots \
            "${target_set}" \
            "${UFUNCTION_SECOND_SOURCE_ROOT}"
        status=$?
        set -e
        second_source_status="$(merge_second_source_status "${second_source_status}" "${status}")"
    done
    for target_set in "${SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS[@]}"; do
        set +e
        run_second_source_readiness \
            "scriptstruct-${target_set}" \
            tests/fixtures/scriptstruct_snapshots \
            "${target_set}" \
            "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}"
        status=$?
        set -e
        second_source_status="$(merge_second_source_status "${second_source_status}" "${status}")"
    done
    if [[ "${second_source_status}" -ne 0 ]]; then
        exit "${second_source_status}"
    fi
fi
run_step env OBELISK_BUILD_DIR="${BUILD_DIR}" scripts/test_install_obelisk_layout.sh "${LAYOUT_CHECK_ROOT}"
run_step scripts/obelisk.py --root "${LAYOUT_CHECK_ROOT}" status
run_step scripts/install_obelisk.sh --build-dir "${BUILD_DIR}" --dry-run "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so" "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oProcessTimer/oProcessTimer.so" "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oDescriptorCatalog/oDescriptorCatalog.so" "${RELEASE_CHECK_ROOT}"
run_step git diff --check

printf '\n==> git status --short --ignored\n'
git status --short --ignored
check_clean_tree

if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" ]]; then
    printf '\nScoped release-readiness baseline and gameplay/module second-source layout-evidence gates completed.\n'
else
    printf '\nScoped release-readiness baseline checks completed; gameplay/module second-source layout-evidence gate was not run.\n'
fi
if [[ "${REQUIRE_V1_SDK_COMPLETION}" == "1" ]]; then
    printf 'Public SDK v1 stable claim gate passed.\n'
else
    printf 'Public SDK v1 stable claim gate was not run.\n'
fi
printf 'Release gate output is evidence for this exact gate only; it does not grant live-ops approval, Plugin Hub readiness/publication, support-tier activation, runtime readiness, stable SDK claims, or v1 SDK completion.\n'
