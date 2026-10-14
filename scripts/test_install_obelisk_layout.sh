#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/test_install_obelisk_layout.sh <clean-install-root>

Validates the installer, installed runtime layout, CMake SDK package, and installed SDK
package-shape consumer examples. Pass a fresh empty absolute install root, such as one
created with mktemp -d /tmp/obelisk-layout-check.XXXXXX. The test performs a backup
reinstall, so reusing a populated root can leave stale backup artifacts that make the
result unclear.

Options:
  -h, --help  Show this help.
EOF
}

case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
esac

if [[ $# -ne 1 || -z "${1:-}" ]]; then
    echo "scripts/test_install_obelisk_layout.sh requires a clean explicit install root." >&2
    usage >&2
    exit 2
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${OBELISK_BUILD_DIR:-${REPO_DIR}/build}"
if [[ "${BUILD_DIR}" != /* ]]; then
    BUILD_DIR="${REPO_DIR}/${BUILD_DIR}"
fi
INSTALL_ROOT="$1"
WORK_DIR="$(mktemp -d /tmp/obelisk-sdk-consumer.XXXXXX)"
CXX_BIN="${CXX:-g++}"
SDK_CONSUMER_FIXTURE="${BUILD_DIR}/tests/sdk_consumer/sdk_consumer_fixture"
SERVER_ROOT="/servidor/ark"

cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

is_under_path() {
    local path="$1"
    local parent="$2"

    [[ "${path}" == "${parent}" || "${path}" == "${parent}/"* ]]
}

reject_protected_path() {
    local label="$1"
    local action="$2"
    local path="$3"
    local absolute_path
    local resolved_path

    absolute_path="$(realpath -s -m "${path}")"
    if is_under_path "${absolute_path}" "${SERVER_ROOT}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${absolute_path}" >&2
        exit 2
    fi

    resolved_path="$(realpath -m "${path}")"
    if is_under_path "${resolved_path}" "${SERVER_ROOT}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${resolved_path}" >&2
        exit 2
    fi
}

reject_symlink_path_components() {
    local label="$1"
    local path="$2"
    local lexical_path
    local resolved_path

    lexical_path="$(realpath -s -m "${path}")"
    resolved_path="$(realpath -m "${path}")"
    if [[ "${lexical_path}" != "${resolved_path}" ]]; then
        printf '%s must not resolve through symlink path components: %s -> %s\n' \
            "${label}" "${path}" "${resolved_path}" >&2
        exit 2
    fi
}

if [[ "${INSTALL_ROOT}" != /* || "${INSTALL_ROOT}" == "/" ]]; then
    echo "Install layout test root must be a non-root absolute path: ${INSTALL_ROOT}" >&2
    usage >&2
    exit 2
fi
reject_protected_path "Install layout test root" "write under" "${INSTALL_ROOT}"
reject_protected_path "OBELISK_BUILD_DIR" "read from" "${BUILD_DIR}"
if [[ -L "${INSTALL_ROOT}" ]]; then
    echo "Install layout test root must not be a symlink: ${INSTALL_ROOT}" >&2
    exit 2
fi
reject_symlink_path_components "Install layout test root" "${INSTALL_ROOT}"
if [[ -e "${INSTALL_ROOT}" && ! -d "${INSTALL_ROOT}" ]]; then
    echo "Install layout test root must be a directory or absent path: ${INSTALL_ROOT}" >&2
    exit 2
fi
if [[ -d "${INSTALL_ROOT}" ]] && find "${INSTALL_ROOT}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    echo "Install layout test root must be clean/empty before validation: ${INSTALL_ROOT}" >&2
    echo "Create a fresh root with: mktemp -d /tmp/obelisk-layout-check.XXXXXX" >&2
    exit 2
fi

require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Missing required command: ${cmd}" >&2
        exit 1
    fi
}

require_path() {
    local path="$1"
    if [[ ! -e "${path}" ]]; then
        echo "Missing expected install path: ${path}" >&2
        exit 1
    fi
}

require_not_contains() {
    local pattern="$1"
    local path="$2"
    if grep -F "${pattern}" "${path}" >/dev/null; then
        echo "Unexpected local path leak in ${path}: ${pattern}" >&2
        cat "${path}" >&2
        exit 1
    fi
}

require_installed_public_header_has_no_blocked_symbols() {
    local header_path="$1"
    local forbidden_symbols=(
        "OBELISK_API_CAPABILITY_RESOURCE_HANDLE"
        "OBELISK_API_CAPABILITY_RESOURCE_HANDLES"
        "OBELISK_API_CAPABILITY_RESOURCE_ID"
        "OBELISK_API_CAPABILITY_RESOURCE_ID_LOOKUP"
        "OBELISK_API_CAPABILITY_RESOURCE_LOOKUP"
        "OBELISK_API_CAPABILITY_RESOURCE_REF"
        "OBELISK_API_CAPABILITY_RESOURCE_TOKEN"
        "OBELISK_API_CAPABILITY_OBJECT_ID"
        "OBELISK_API_CAPABILITY_OBJECT_IDENTITY"
        "OBELISK_API_CAPABILITY_OBJECT_LOOKUP"
        "OBELISK_RESOURCE_HANDLE_ABI_VERSION"
        "ObeliskResourceHandle"
        "ObeliskResourceId"
        "ObeliskResourceID"
        "ObeliskResourceRef"
        "ObeliskResourceToken"
        "ObeliskResourceLookup"
        "ObeliskObjectId"
        "ObeliskObjectID"
        "ResourceHandle"
        "ResourceRef"
        "ResourceToken"
        "ResourceLookup"
        "GetResource"
        "ResolveResource"
        "LookupResource"
        "FindResource"
        "OpenResource"
        "RegisterResourceHandle"
        "ResolveObject"
        "LookupObject"
        "GObjects"
        "GUObjectArray"
        "GNames"
        "OBELISK_API_CAPABILITY_INVENTORY_ACTIONS"
        "OBELISK_API_CAPABILITY_INVENTORY_ACTION_OBSERVERS"
        "OBELISK_API_CAPABILITY_INVENTORY_MUTATION"
        "OBELISK_API_CAPABILITY_ITEM_MUTATION"
        "OBELISK_API_CAPABILITY_ITEM_ID_LOOKUP"
        "ObeliskInventoryAction"
        "ObeliskInventoryMutation"
        "ObeliskItemMutation"
        "ObeliskItemNetId"
        "ObeliskItemNetID"
        "RegisterInventoryAction"
        "RegisterInventoryActionObserver"
        "GiveItem"
        "RemoveItem"
        "OBELISK_API_CAPABILITY_MISSION_COPIED_BOOL"
        "MissionCopiedBool"
        "OBELISK_API_CAPABILITY_TRANSFER_BACCEPT"
        "TransferBAccept"
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL"
        "OBELISK_API_CAPABILITY_PLAYER_IDENTITY"
        "OBELISK_API_CAPABILITY_PLAYER_ID"
        "OBELISK_API_CAPABILITY_PLAYER_LOOKUP"
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LOOKUP"
        "OBELISK_API_CAPABILITY_PRINCIPAL_LOOKUP"
        "OBELISK_API_CAPABILITY_IDENTITY_LOOKUP"
        "ObeliskPlayerPrincipal"
        "ObeliskPlayerIdentity"
        "ObeliskPlayerId"
        "ObeliskPlayerID"
        "ObeliskPlayerLookup"
        "ObeliskPlayerHandle"
        "ObeliskPrincipal"
        "ObeliskPrincipalId"
        "ObeliskPrincipalID"
        "ObeliskSteamId"
        "ObeliskSteamID"
        "ObeliskTribeId"
        "ObeliskNetworkAddress"
        "RegisterPlayerPrincipal"
        "ResolvePlayerIdentity"
        "ResolvePlayerPrincipal"
        "LookupPlayerIdentity"
        "LookupPlayerPrincipal"
        "FindPlayerIdentity"
        "FindPlayerPrincipal"
        "PrincipalLookup"
        "ResolvePrincipal"
        "LookupPrincipal"
        "FindPrincipal"
        "OBELISK_API_CAPABILITY_COMMANDS"
        "OBELISK_API_CAPABILITY_CHAT_COMMANDS"
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES"
        "OBELISK_API_CAPABILITY_COMMAND_ROUTING"
        "OBELISK_API_CAPABILITY_CHAT_RESPONSES"
        "OBELISK_API_CAPABILITY_SEND_CHAT"
        "OBELISK_API_CAPABILITY_CHAT_MODERATION"
        "OBELISK_API_CAPABILITY_ADMIN_COMMANDS"
        "OBELISK_API_CAPABILITY_PLAYER_COMMANDS"
        "ObeliskCommand"
        "ObeliskCommandContext"
        "ObeliskCommandReply"
        "ObeliskCommandHandler"
        "ObeliskChatCommand"
        "ObeliskChatResponse"
        "RegisterCommand"
        "RegisterCommandHandler"
        "RegisterChatCommand"
        "ReplyToCommand"
        "SendChat"
        "SendChatMessage"
        "BroadcastChat"
        "OBELISK_API_CAPABILITY_PERMISSION"
        "OBELISK_API_CAPABILITY_PERMISSIONS"
        "OBELISK_API_CAPABILITY_PERMISSION_ADMIN"
        "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN"
        "OBELISK_API_CAPABILITY_PERMISSION_CHECKS"
        "OBELISK_API_CAPABILITY_AUTHZ_CHECKS"
        "OBELISK_API_CAPABILITY_ADMIN"
        "OBELISK_API_CAPABILITY_ADMIN_AUTHORITY"
        "ObeliskPermissionQuery"
        "ObeliskPermissionCheck"
        "ObeliskPermissionDecision"
        "ObeliskPermissionsAdmin"
        "ObeliskAuthZDecision"
        "CheckPermission"
        "HasPermission"
        "GrantPermission"
        "RevokePermission"
        "RequirePermission"
        "OBELISK_API_CAPABILITY_RESOURCE_MUTATION"
        "OBELISK_API_CAPABILITY_MUTATION"
        "OBELISK_API_CAPABILITY_RETURN_OVERRIDES"
        "ObeliskMutation"
        "ObeliskMutationContext"
        "MutateResource"
        "SetReturnOverride"
        "OverrideReturn"
        "ReturnOverride"
        "ObeliskReturnOverride"
        "OBELISK_API_CAPABILITY_RUNTIME_READY"
        "ObeliskRuntimeReady"
    )

    python3 - "${header_path}" "${REPO_DIR}/scripts" "${forbidden_symbols[@]}" <<'PY'
import re
import sys

header_path = sys.argv[1]
sys.path.insert(0, sys.argv[2])
from native_prototype_guardrails import without_native_prototype_symbols
forbidden = sys.argv[3:]

with open(header_path, "r", encoding="utf-8") as handle:
    text = handle.read()

text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
text = re.sub(r"//.*", "", text)
text = without_native_prototype_symbols(text, header_only=True)
identifiers = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))
offenders = [symbol for symbol in forbidden if symbol in identifiers]

if offenders:
    print("Installed SDK public header exposes blocked symbols:", file=sys.stderr)
    for offender in offenders:
        print(offender, file=sys.stderr)
    raise SystemExit(1)
PY
}

require_installed_cmake_package_has_no_blocked_aliases() {
    local package_dir="$1"
    local forbidden_symbols=(
        "OBELISK_API_CAPABILITY_RESOURCE_HANDLE"
        "OBELISK_API_CAPABILITY_RESOURCE_HANDLES"
        "OBELISK_API_CAPABILITY_RESOURCE_LOOKUP"
        "OBELISK_API_CAPABILITY_RESOURCE_REF"
        "OBELISK_API_CAPABILITY_RESOURCE_TOKEN"
        "ObeliskResourceHandle"
        "ObeliskResourceRef"
        "ObeliskResourceToken"
        "ObeliskResourceLookup"
        "ResourceHandle"
        "ResourceRef"
        "ResourceToken"
        "ResourceLookup"
        "GetResource"
        "ResolveResource"
        "LookupResource"
        "FindResource"
        "OpenResource"
        "RegisterResourceHandle"
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL"
        "OBELISK_API_CAPABILITY_PLAYER_IDENTITY"
        "OBELISK_API_CAPABILITY_PLAYER_LOOKUP"
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LOOKUP"
        "OBELISK_API_CAPABILITY_PRINCIPAL_LOOKUP"
        "OBELISK_API_CAPABILITY_IDENTITY_LOOKUP"
        "ObeliskPlayerPrincipal"
        "ObeliskPlayerIdentity"
        "ObeliskPlayerLookup"
        "ObeliskPlayerHandle"
        "ObeliskPrincipal"
        "ObeliskPrincipalId"
        "ObeliskPrincipalID"
        "RegisterPlayerPrincipal"
        "ResolvePlayerIdentity"
        "ResolvePlayerPrincipal"
        "LookupPlayerIdentity"
        "LookupPlayerPrincipal"
        "FindPlayerIdentity"
        "FindPlayerPrincipal"
        "PrincipalLookup"
        "ResolvePrincipal"
        "LookupPrincipal"
        "FindPrincipal"
        "OBELISK_API_CAPABILITY_COMMANDS"
        "OBELISK_API_CAPABILITY_CHAT_COMMANDS"
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES"
        "OBELISK_API_CAPABILITY_COMMAND_ROUTING"
        "OBELISK_API_CAPABILITY_ADMIN_COMMANDS"
        "OBELISK_API_CAPABILITY_PLAYER_COMMANDS"
        "ObeliskCommand"
        "ObeliskCommandContext"
        "ObeliskCommandReply"
        "ObeliskCommandHandler"
        "ObeliskChatCommand"
        "RegisterCommand"
        "RegisterCommandHandler"
        "RegisterChatCommand"
        "ReplyToCommand"
        "OBELISK_API_CAPABILITY_PERMISSION"
        "OBELISK_API_CAPABILITY_PERMISSIONS"
        "OBELISK_API_CAPABILITY_PERMISSION_ADMIN"
        "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN"
        "OBELISK_API_CAPABILITY_PERMISSION_CHECKS"
        "OBELISK_API_CAPABILITY_AUTHZ_CHECKS"
        "OBELISK_API_CAPABILITY_ADMIN"
        "OBELISK_API_CAPABILITY_ADMIN_AUTHORITY"
        "ObeliskPermissionQuery"
        "ObeliskPermissionCheck"
        "ObeliskPermissionDecision"
        "ObeliskPermissionsAdmin"
        "ObeliskAuthZDecision"
        "CheckPermission"
        "HasPermission"
        "GrantPermission"
        "RevokePermission"
        "RequirePermission"
        "OBELISK_API_CAPABILITY_RESOURCE_MUTATION"
        "OBELISK_API_CAPABILITY_MUTATION"
        "OBELISK_API_CAPABILITY_RETURN_OVERRIDES"
        "ObeliskMutation"
        "ObeliskMutationContext"
        "MutateResource"
        "SetReturnOverride"
        "OverrideReturn"
        "ReturnOverride"
        "ObeliskReturnOverride"
        "OBELISK_API_CAPABILITY_RUNTIME_READY"
        "ObeliskRuntimeReady"
    )

    python3 - "${package_dir}" "${forbidden_symbols[@]}" <<'PY'
import re
import sys
from pathlib import Path

package_dir = Path(sys.argv[1])
forbidden = set(sys.argv[2:])
allowed_readiness_identifiers = {
    "Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS",
    "Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED",
    "Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED",
    "Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED",
    "Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED",
    "Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED",
    "Obelisk_V1_COMPLETION_CLAIM_ALLOWED",
    "Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED",
    "Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED",
    "Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY",
    "Obelisk_EXACT_VERSION_REQUESTS_ALLOWED",
    "Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM",
    "Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS",
    "Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE",
    "Obelisk_SDK_BLOCKER_PROMOTION_COUNT",
    "Obelisk_SDK_BLOCKER_PROMOTION_TOTAL",
    "Obelisk_P0_DEPENDENCY_COUNT",
    "Obelisk_P0_DEPENDENCY_TOTAL",
    "Obelisk_ACTIVE_COMPLETION_BLOCKER",
}
undefined_or_false_identifiers = {
    "Obelisk_ABI_LAYOUT_READY",
    "Obelisk_ABI_LAYOUT_VALIDATED",
    "Obelisk_ACCEPTED_FOR_CONTRACT_REVIEW",
    "Obelisk_APPROVED_RUNTIME_BUNDLE_ACCEPTED",
    "Obelisk_APPROVED_RUNTIME_EVIDENCE_ACCEPTED",
    "Obelisk_C_ABI_READY",
    "Obelisk_STRUCT_SIZE_READY",
    "Obelisk_STRUCT_SIZE_VALIDATED",
    "Obelisk_CMAKE_PACKAGE_READY",
    "Obelisk_INSTALLED_HEADERS_READY",
    "Obelisk_INSTALLED_SDK_CONSUMER_TESTS_READY",
    "Obelisk_INSTALLED_SDK_PACKAGE_READY",
    "Obelisk_PACKAGE_AVAILABLE",
    "Obelisk_PACKAGE_PUBLICATION_ALLOWED",
    "Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_COMPLETION",
    "Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_PUBLIC_SDK",
    "Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_V1_COMPLETION",
    "Obelisk_PACKAGE_SHAPE_READY",
    "Obelisk_PUBLIC_ABI_AVAILABLE",
    "Obelisk_PUBLIC_CONTRACT_REVIEW_ACCEPTED",
    "Obelisk_PUBLIC_HEADER_GATE_OPEN",
    "Obelisk_PUBLIC_HEADER_GATE_PASSED",
    "Obelisk_PUBLIC_HEADER_GATE_READY",
    "Obelisk_HEADER_PROMOTION_GATE_OPEN",
    "Obelisk_HEADER_PROMOTION_GATE_PASSED",
    "Obelisk_HEADER_PROMOTION_GATE_READY",
    "Obelisk_PUBLIC_HEADER_ALLOWED",
    "Obelisk_PUBLIC_HEADER_PROMOTION_GATE_OPEN",
    "Obelisk_PUBLIC_HEADER_PROMOTION_GATE_PASSED",
    "Obelisk_PUBLIC_HEADER_PROMOTION_GATE_READY",
    "Obelisk_PUBLIC_HEADER_READY",
    "Obelisk_PUBLIC_HEADERS_READY",
    "Obelisk_PUBLIC_PACKAGE_AVAILABLE",
    "Obelisk_PUBLIC_PACKAGE_READY",
    "Obelisk_PUBLIC_SDK_READY",
    "Obelisk_SDK_CONSUMER_TESTS_READY",
    "Obelisk_STABLE_SDK_READY",
}
allowed_marker_identifiers = allowed_readiness_identifiers | undefined_or_false_identifiers
false_only_identifiers = (
    allowed_readiness_identifiers - {
        "Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS",
        "Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY",
        "Obelisk_SDK_BLOCKER_PROMOTION_COUNT",
        "Obelisk_SDK_BLOCKER_PROMOTION_TOTAL",
        "Obelisk_P0_DEPENDENCY_COUNT",
        "Obelisk_P0_DEPENDENCY_TOTAL",
        "Obelisk_ACTIVE_COMPLETION_BLOCKER",
    }
) | undefined_or_false_identifiers
claim_identifier = re.compile(
    r"(READINESS|RUNTIME_READY|ACCEPTED|APPROVED|CONTRACT_REVIEW|COMPLETE|"
    r"SDK_COMPLETE|CLAIM|PROMOTION|COUNTS_TOWARD|PACKAGE_PUBLICATION|PACKAGE_AVAILABLE|"
    r"STABLE_SDK|V1_COMPLETION|SUPPORT_TIER|PLUGIN_HUB|"
    r"PUBLIC_PACKAGE|PUBLIC_SDK|PUBLIC_HEADER|PACKAGE_SHAPE|SDK_CONSUMER|"
    r"CMAKE_PACKAGE|ABI_LAYOUT|C_ABI|STRUCT_SIZE)",
    re.I,
)

offenders = []
for path in sorted(package_dir.glob("*.cmake")):
    text = path.read_text(encoding="utf-8")
    text_no_comments = re.sub(r"#.*", "", text)
    identifiers = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text_no_comments))
    for symbol in sorted(forbidden & identifiers):
        offenders.append(f"{path.name}: blocked public SDK alias {symbol}")
    for identifier in sorted(identifiers):
        if claim_identifier.search(identifier) and identifier not in allowed_marker_identifiers:
            offenders.append(f"{path.name}: unreviewed package/readiness marker {identifier}")
    for match in re.finditer(
        r"^\s*set\(\s*(Obelisk_[A-Za-z0-9_]+)\s+([^)\s#]+)",
        text_no_comments,
        re.M,
    ):
        variable, value = match.groups()
        normalized_value = value.upper()
        if variable in false_only_identifiers and normalized_value not in {"FALSE", "0", "OFF"}:
            offenders.append(f"{path.name}: {variable} must stay false, got {value}")
        if (
            claim_identifier.search(variable)
            and variable != "Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY"
            and normalized_value in {"TRUE", "1", "ON"}
        ):
            offenders.append(f"{path.name}: {variable} must not be enabled by package shape")

if offenders:
    print("Installed SDK CMake package exposes blocked aliases or readiness markers:", file=sys.stderr)
    for offender in offenders:
        print(offender, file=sys.stderr)
    raise SystemExit(1)
PY
}

require_no_call_process_event_escape_hatch() {
    local scan_root="$1"
    local label="$2"
    local offenders

    offenders="$(
        grep -RInE \
            --include='*.c' --include='*.cpp' --include='*.h' --include='*.hpp' \
            'OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT|([.]|->)[[:space:]]*CallProcessEvent' \
            "${scan_root}" || true
    )"

    if [[ -n "${offenders}" ]]; then
        echo "${label} used the public CallProcessEvent debug escape hatch" >&2
        printf '%s\n' "${offenders}" >&2
        exit 1
    fi
}

require_dynamic_exports() {
    local path="$1"
    shift
    local expected actual symbol
    expected="$(printf '%s\n' "$@" | LC_ALL=C sort)"
    actual="$(nm -D --defined-only "${path}" | awk '{print $NF}' | LC_ALL=C sort)"
    if [[ "${actual}" != "${expected}" ]]; then
        echo "Unexpected dynamic exports in ${path}" >&2
        echo "Expected exports:" >&2
        printf '%s\n' "${expected}" >&2
        echo "Actual exports:" >&2
        printf '%s\n' "${actual}" >&2
        echo "Full nm output:" >&2
        nm -D --defined-only "${path}" >&2
        return 1
    fi
    for symbol in "$@"; do
        if ! nm -D --defined-only "${path}" | awk '{print $NF}' | grep -Fx "${symbol}" >/dev/null; then
            echo "Missing expected dynamic export ${symbol} in ${path}" >&2
            nm -D --defined-only "${path}" >&2
            return 1
        fi
    done
}

require_external_sdk_compile_commands() {
    local compile_commands_path="$1"
    local label="$2"
    local private_root

    if ! grep -F "${INSTALL_ROOT}/include" "${compile_commands_path}" >/dev/null; then
        echo "${label} did not include headers from the installed SDK layout" >&2
        cat "${compile_commands_path}" >&2
        exit 1
    fi

    for private_root in \
        "${REPO_DIR}/include" \
        "${REPO_DIR}/plugins" \
        "${REPO_DIR}/extern" \
        "${REPO_DIR}/core" \
        "${REPO_DIR}/runtime" \
        "${REPO_DIR}/ue" \
        "${REPO_DIR}/loader" \
        "${REPO_DIR}/tests"
    do
        if grep -F "${private_root}" "${compile_commands_path}" >/dev/null; then
            echo "${label} accidentally referenced repo-private paths: ${private_root}" >&2
            cat "${compile_commands_path}" >&2
            exit 1
        fi
    done
}

require_no_runtime_private_linkage() {
    local artifact_path="$1"
    local build_dir="$2"
    local label="$3"
    local dynamic_offenders
    local link_offenders

    dynamic_offenders="$(readelf -d "${artifact_path}" |
        grep -E 'Shared library: \[(libobelisk|libsubhook)[.]so|Shared library: \[lib(dl|pthread)[.]so' || true)"
    if [[ -n "${dynamic_offenders}" ]]; then
        echo "${label} linked runtime/private shared libraries directly" >&2
        printf '%s\n' "${dynamic_offenders}" >&2
        readelf -d "${artifact_path}" >&2
        exit 1
    fi

    link_offenders="$(
        grep -RInE \
            --include='link.txt' --include='*.rsp' \
            '(^|[[:space:]])-l(obelisk|subhook|dl|pthread)([[:space:]]|$)|(^|[[:space:]])-pthread([[:space:]]|$)|/(libobelisk|libsubhook)[.]so|/(core|runtime|loader|ue)/' \
            "${build_dir}" || true
    )"
    if [[ -n "${link_offenders}" ]]; then
        echo "${label} build linked runtime/private libraries or paths directly" >&2
        printf '%s\n' "${link_offenders}" >&2
        exit 1
    fi
}

require_cmake_package_shape_only() {
    local package_dir="$1"
    local offenders

    if ! grep -F 'add_library(Obelisk::obelisk_sdk INTERFACE IMPORTED)' \
        "${package_dir}/ObeliskTargets.cmake" >/dev/null; then
        echo "Installed SDK package did not export Obelisk::obelisk_sdk as an interface imported target" >&2
        cat "${package_dir}/ObeliskTargets.cmake" >&2
        exit 1
    fi

    offenders="$(
        grep -RInE \
            'IMPORTED_(IMPLIB|LINK_DEPENDENT_LIBRARIES|LOCATION|OBJECTS|SONAME)|INTERFACE_LINK_(LIBRARIES|OPTIONS)|Obelisk::obelisk([^_[:alnum:]]|$)|Obelisk::subhook([^_[:alnum:]]|$)|libobelisk[.]so|libsubhook[.]so|(^|[;"[:space:]])(-l)?(dl|pthread)([;"[:space:]]|$)|(^|[[:space:]])-pthread([[:space:]]|$)' \
            "${package_dir}" || true
    )"
    if [[ -n "${offenders}" ]]; then
        echo "Installed SDK CMake package exposed runtime/private linkage or imported binary locations" >&2
        printf '%s\n' "${offenders}" >&2
        exit 1
    fi

    local required_package_shape_markers=(
        'set(Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS "package-shape-evidence-only")'
        'set(Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED FALSE)'
        'set(Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED FALSE)'
        'set(Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED FALSE)'
        'set(Obelisk_V1_COMPLETION_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_SDK_BLOCKER_PROMOTION_COUNT 0)'
        'set(Obelisk_SDK_BLOCKER_PROMOTION_TOTAL 12)'
        'set(Obelisk_P0_DEPENDENCY_COUNT 0)'
        'set(Obelisk_P0_DEPENDENCY_TOTAL 4)'
        'set(Obelisk_ACTIVE_COMPLETION_BLOCKER "approved_runtime_evidence_missing")'
        'set(Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE)'
        'set(Obelisk_EXACT_VERSION_REQUESTS_ALLOWED FALSE)'
        'set(Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM FALSE)'
        'set(Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS FALSE)'
        'set(Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE FALSE)'
    )
    local package_shape_marker
    for package_shape_marker in "${required_package_shape_markers[@]}"; do
        if ! grep -F "${package_shape_marker}" \
            "${package_dir}/ObeliskConfig.cmake" >/dev/null; then
            echo "Installed SDK CMake package missed package-shape non-claim marker: ${package_shape_marker}" >&2
            cat "${package_dir}/ObeliskConfig.cmake" >&2
            exit 1
        fi
    done

    local readiness_claim_offenders
    readiness_claim_offenders="$(
        grep -RInEi \
            'set\([[:space:]]*Obelisk_[A-Za-z0-9_]*(READY|READINESS|ACCEPTED|APPROVED|CONTRACT_REVIEW|COMPLETE|SDK_COMPLETE|CLAIM|PROMOTION|COUNTS_TOWARD|PACKAGE_PUBLICATION|PACKAGE_AVAILABLE|STABLE_SDK|V1_COMPLETION|SUPPORT_TIER|PLUGIN_HUB|PUBLIC_PACKAGE|PUBLIC_SDK|PUBLIC_HEADER|PACKAGE_SHAPE|SDK_CONSUMER|ABI_LAYOUT|C_ABI|STRUCT_SIZE)[A-Za-z0-9_]*[[:space:]]+(TRUE|ON|1)[[:space:]]*\)' \
            "${package_dir}" |
            grep -vF 'Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE' || true
    )"
    if [[ -n "${readiness_claim_offenders}" ]]; then
        echo "Installed SDK CMake package exposed positive readiness/public-claim markers" >&2
        printf '%s\n' "${readiness_claim_offenders}" >&2
        exit 1
    fi
}

require_cmd "${CXX_BIN}"
require_cmd python3
require_cmd nm
require_cmd readelf

if env -u OBELISK_ROOT "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run \
    >"${WORK_DIR}/missing-root.out" 2>"${WORK_DIR}/missing-root.err"; then
    echo "install_obelisk.sh accepted a missing install root" >&2
    exit 1
fi
if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/missing-root.err" >/dev/null; then
    echo "missing root error was unclear" >&2
    cat "${WORK_DIR}/missing-root.err" >&2
    exit 1
fi

if OBELISK_ROOT="${WORK_DIR}/env-root" "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run \
    >"${WORK_DIR}/env-root.out" 2>"${WORK_DIR}/env-root.err"; then
    echo "install_obelisk.sh accepted OBELISK_ROOT without a positional root" >&2
    exit 1
fi
if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/env-root.err" >/dev/null; then
    echo "OBELISK_ROOT fallback rejection was unclear" >&2
    cat "${WORK_DIR}/env-root.err" >&2
    exit 1
fi

for invalid_root in "" "/" "." "relative/root"; do
    if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${invalid_root}" \
        >"${WORK_DIR}/invalid-root.out" 2>"${WORK_DIR}/invalid-root.err"; then
        echo "install_obelisk.sh accepted invalid root '${invalid_root}'" >&2
        exit 1
    fi
    if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/invalid-root.err" >/dev/null; then
        echo "invalid root error was unclear for '${invalid_root}'" >&2
        cat "${WORK_DIR}/invalid-root.err" >&2
        exit 1
    fi
done

if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run /tmp/obelisk-extra-root /tmp/obelisk-other-root \
    >"${WORK_DIR}/extra-root.out" 2>"${WORK_DIR}/extra-root.err"; then
    echo "install_obelisk.sh accepted an extra positional root" >&2
    exit 1
fi
if ! grep -F 'Unexpected extra argument' "${WORK_DIR}/extra-root.err" >/dev/null; then
    echo "extra root error was unclear" >&2
    cat "${WORK_DIR}/extra-root.err" >&2
    exit 1
fi

root_file="${WORK_DIR}/root-file"
printf 'not a directory\n' > "${root_file}"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${root_file}" \
    >"${WORK_DIR}/root-file.out" 2>"${WORK_DIR}/root-file.err"; then
    echo "install_obelisk.sh accepted a non-directory install root" >&2
    exit 1
fi
if ! grep -F 'Install root must be a directory or absent path' "${WORK_DIR}/root-file.err" >/dev/null; then
    echo "non-directory root error was unclear" >&2
    cat "${WORK_DIR}/root-file.err" >&2
    exit 1
fi

set +e
protected_root_output="$(
    "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run /servidor/ark/obelisk-install-check 2>&1
)"
status=$?
set -e
if [[ "${status}" -ne 2 ]]; then
    printf 'expected protected install root to exit 2, got %s\n%s\n' \
        "${status}" "${protected_root_output}" >&2
    exit 1
fi
if ! grep -Fq 'Install root must not write under protected server root /servidor/ark' <<<"${protected_root_output}"; then
    printf 'missing protected install root rejection\n%s\n' "${protected_root_output}" >&2
    exit 1
fi
if grep -Fq 'DRY-RUN:' <<<"${protected_root_output}"; then
    printf 'protected install root reached dry-run actions\n%s\n' "${protected_root_output}" >&2
    exit 1
fi

set +e
protected_central_root_without_ack_output="$(
    "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run /servidor/ark/obelisk 2>&1
)"
status=$?
set -e
if [[ "${status}" -ne 2 ]]; then
    printf 'expected protected central install root without env ack to exit 2, got %s\n%s\n' \
        "${status}" "${protected_central_root_without_ack_output}" >&2
    exit 1
fi
if ! grep -Fq 'Install root must not write under protected server root /servidor/ark' \
    <<<"${protected_central_root_without_ack_output}"; then
    printf 'missing protected central install root rejection without env ack\n%s\n' \
        "${protected_central_root_without_ack_output}" >&2
    exit 1
fi
if grep -Fq 'DRY-RUN:' <<<"${protected_central_root_without_ack_output}"; then
    printf 'protected central install root without env ack reached dry-run actions\n%s\n' \
        "${protected_central_root_without_ack_output}" >&2
    exit 1
fi

protected_live_link="${WORK_DIR}/protected-live-link"
ln -s /servidor/ark "${protected_live_link}"
set +e
protected_symlink_root_output="$(
    "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${protected_live_link}/obelisk-install-check" 2>&1
)"
status=$?
set -e
if [[ "${status}" -ne 2 ]]; then
    printf 'expected symlinked protected install root to exit 2, got %s\n%s\n' \
        "${status}" "${protected_symlink_root_output}" >&2
    exit 1
fi
if ! grep -Fq 'Install root must not write under protected server root /servidor/ark' <<<"${protected_symlink_root_output}"; then
    printf 'missing symlinked protected install root rejection\n%s\n' \
        "${protected_symlink_root_output}" >&2
    exit 1
fi
if grep -Fq 'DRY-RUN:' <<<"${protected_symlink_root_output}"; then
    printf 'symlinked protected install root reached dry-run actions\n%s\n' \
        "${protected_symlink_root_output}" >&2
    exit 1
fi

set +e
protected_build_dir_output="$(
    OBELISK_BUILD_DIR=/servidor/ark/obelisk/build \
        "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${WORK_DIR}/protected-build-root" 2>&1
)"
status=$?
set -e
if [[ "${status}" -ne 2 ]]; then
    printf 'expected protected installer build dir to exit 2, got %s\n%s\n' \
        "${status}" "${protected_build_dir_output}" >&2
    exit 1
fi
if ! grep -Fq 'Build dir must not read from protected server root /servidor/ark' <<<"${protected_build_dir_output}"; then
    printf 'missing protected installer build dir rejection\n%s\n' \
        "${protected_build_dir_output}" >&2
    exit 1
fi
if grep -Fq 'DRY-RUN:' <<<"${protected_build_dir_output}"; then
    printf 'protected installer build dir reached dry-run actions\n%s\n' \
        "${protected_build_dir_output}" >&2
    exit 1
fi

set +e
protected_symlink_build_dir_output="$(
    "${REPO_DIR}/scripts/install_obelisk.sh" \
        --build-dir "${protected_live_link}/obelisk/build" \
        --dry-run "${WORK_DIR}/protected-symlink-build-root" 2>&1
)"
status=$?
set -e
if [[ "${status}" -ne 2 ]]; then
    printf 'expected symlinked protected installer build dir to exit 2, got %s\n%s\n' \
        "${status}" "${protected_symlink_build_dir_output}" >&2
    exit 1
fi
if ! grep -Fq 'Build dir must not read from protected server root /servidor/ark' <<<"${protected_symlink_build_dir_output}"; then
    printf 'missing symlinked protected installer build dir rejection\n%s\n' \
        "${protected_symlink_build_dir_output}" >&2
    exit 1
fi
if grep -Fq 'DRY-RUN:' <<<"${protected_symlink_build_dir_output}"; then
    printf 'symlinked protected installer build dir reached dry-run actions\n%s\n' \
        "${protected_symlink_build_dir_output}" >&2
    exit 1
fi

symlink_target="${WORK_DIR}/root-target"
symlink_root="${WORK_DIR}/root-symlink"
mkdir -p "${symlink_target}"
ln -s "${symlink_target}" "${symlink_root}"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${symlink_root}" \
    >"${WORK_DIR}/symlink-root.out" 2>"${WORK_DIR}/symlink-root.err"; then
    echo "install_obelisk.sh accepted symlink root" >&2
    exit 1
fi
if ! grep -F 'Install root must not be a symlink' "${WORK_DIR}/symlink-root.err" >/dev/null; then
    echo "symlink root error was unclear" >&2
    cat "${WORK_DIR}/symlink-root.err" >&2
    exit 1
fi

symlink_component_target="${WORK_DIR}/root-component-target"
symlink_component_parent="${WORK_DIR}/root-component-link"
mkdir -p "${symlink_component_target}"
ln -s "${symlink_component_target}" "${symlink_component_parent}"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${symlink_component_parent}/install-root" \
    >"${WORK_DIR}/symlink-component-root.out" 2>"${WORK_DIR}/symlink-component-root.err"; then
    echo "install_obelisk.sh accepted install root through a symlink path component" >&2
    exit 1
fi
if ! grep -F 'Install root must not resolve through symlink path components' \
    "${WORK_DIR}/symlink-component-root.err" >/dev/null; then
    echo "symlink path-component root error was unclear" >&2
    cat "${WORK_DIR}/symlink-component-root.err" >&2
    exit 1
fi

symlink_subpath_root="${WORK_DIR}/symlink-subpath-root"
symlink_subpath_target="${WORK_DIR}/symlink-subpath-target"
mkdir -p "${symlink_subpath_root}" "${symlink_subpath_target}"
ln -s "${symlink_subpath_target}" "${symlink_subpath_root}/lib"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${symlink_subpath_root}" \
    >"${WORK_DIR}/symlink-subpath.out" 2>"${WORK_DIR}/symlink-subpath.err"; then
    echo "install_obelisk.sh accepted symlink managed subpath" >&2
    exit 1
fi
if ! grep -F 'Managed install path must not be a symlink' "${WORK_DIR}/symlink-subpath.err" >/dev/null; then
    echo "symlink subpath error was unclear" >&2
    cat "${WORK_DIR}/symlink-subpath.err" >&2
    exit 1
fi

for guarded_subpath in "plugins" "config" "logs" "state/instances"; do
    guarded_label="${guarded_subpath//\//-}"
    guarded_root="${WORK_DIR}/symlink-${guarded_label}-root"
    guarded_target="${WORK_DIR}/symlink-${guarded_label}-target"
    mkdir -p "${guarded_root}" "${guarded_target}"
    if [[ "${guarded_subpath}" == */* ]]; then
        mkdir -p "${guarded_root}/${guarded_subpath%/*}"
    fi
    ln -s "${guarded_target}" "${guarded_root}/${guarded_subpath}"
    if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${guarded_root}" \
        >"${WORK_DIR}/symlink-${guarded_label}.out" 2>"${WORK_DIR}/symlink-${guarded_label}.err"; then
        echo "install_obelisk.sh accepted symlink managed ${guarded_subpath} directory" >&2
        exit 1
    fi
    if ! grep -F "Managed install path must not be a symlink: ${guarded_root}/${guarded_subpath}" \
        "${WORK_DIR}/symlink-${guarded_label}.err" >/dev/null; then
        echo "symlink managed ${guarded_subpath} error was unclear" >&2
        cat "${WORK_DIR}/symlink-${guarded_label}.err" >&2
        exit 1
    fi
done

file_subpath_root="${WORK_DIR}/file-subpath-root"
mkdir -p "${file_subpath_root}"
printf 'not a directory\n' > "${file_subpath_root}/config"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${file_subpath_root}" \
    >"${WORK_DIR}/file-subpath.out" 2>"${WORK_DIR}/file-subpath.err"; then
    echo "install_obelisk.sh accepted a non-directory managed subpath" >&2
    exit 1
fi
if ! grep -F 'Managed install path must be a directory' "${WORK_DIR}/file-subpath.err" >/dev/null; then
    echo "non-directory managed subpath error was unclear" >&2
    cat "${WORK_DIR}/file-subpath.err" >&2
    exit 1
fi

for guarded_subpath in "plugins" "config" "logs"; do
    guarded_root="${WORK_DIR}/file-${guarded_subpath}-root"
    mkdir -p "${guarded_root}"
    printf 'not a directory\n' > "${guarded_root}/${guarded_subpath}"
    if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${guarded_root}" \
        >"${WORK_DIR}/file-${guarded_subpath}.out" 2>"${WORK_DIR}/file-${guarded_subpath}.err"; then
        echo "install_obelisk.sh accepted non-directory managed ${guarded_subpath} path" >&2
        exit 1
    fi
    if ! grep -F "Managed install path must be a directory: ${guarded_root}/${guarded_subpath}" \
        "${WORK_DIR}/file-${guarded_subpath}.err" >/dev/null; then
        echo "non-directory managed ${guarded_subpath} error was unclear" >&2
        cat "${WORK_DIR}/file-${guarded_subpath}.err" >&2
        exit 1
    fi
done

artifact_symlink_root="${WORK_DIR}/artifact-symlink-root"
artifact_symlink_target="${WORK_DIR}/artifact-symlink-target"
mkdir -p "${artifact_symlink_root}/lib" "${artifact_symlink_target}"
ln -s "${artifact_symlink_target}/libobelisk.so" "${artifact_symlink_root}/lib/libobelisk.so"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${artifact_symlink_root}" \
    >"${WORK_DIR}/artifact-symlink.out" 2>"${WORK_DIR}/artifact-symlink.err"; then
    echo "install_obelisk.sh accepted a symlink managed artifact path" >&2
    exit 1
fi
if ! grep -F 'Managed install artifact must not be a symlink' "${WORK_DIR}/artifact-symlink.err" >/dev/null; then
    echo "symlink managed artifact error was unclear" >&2
    cat "${WORK_DIR}/artifact-symlink.err" >&2
    exit 1
fi

artifact_directory_root="${WORK_DIR}/artifact-directory-root"
mkdir -p "${artifact_directory_root}/include/obelisk/ObeliskApi.h"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${artifact_directory_root}" \
    >"${WORK_DIR}/artifact-directory.out" 2>"${WORK_DIR}/artifact-directory.err"; then
    echo "install_obelisk.sh accepted a directory managed artifact path" >&2
    exit 1
fi
if ! grep -F 'Managed install artifact must be a regular file' "${WORK_DIR}/artifact-directory.err" >/dev/null; then
    echo "directory managed artifact error was unclear" >&2
    cat "${WORK_DIR}/artifact-directory.err" >&2
    exit 1
fi

dry_run_root="${WORK_DIR}/dry-run-root"
"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" --dry-run "${dry_run_root}" \
    >"${WORK_DIR}/dry-run.out"
if [[ -e "${dry_run_root}" ]]; then
    echo "install_obelisk.sh dry-run created the install root" >&2
    find "${dry_run_root}" -maxdepth 4 -print >&2
    exit 1
fi
if ! grep -F 'DRY-RUN: Obelisk install would publish runtime/SDK package-shape artifacts to' \
    "${WORK_DIR}/dry-run.out" >/dev/null; then
    echo "dry-run install output did not describe would-publish package-shape scope" >&2
    cat "${WORK_DIR}/dry-run.out" >&2
    exit 1
fi
if grep -F 'Obelisk installed to' "${WORK_DIR}/dry-run.out" >/dev/null; then
    echo "dry-run install output claimed a completed install" >&2
    cat "${WORK_DIR}/dry-run.out" >&2
    exit 1
fi
for dry_run_non_claim in \
    "runtime/live-ops approval" \
    "Plugin Hub readiness/publication" \
    "support-tier activation" \
    "stable SDK claim" \
    "v1 SDK completion" \
    "SDK blocker promotion 0/12" \
    "P0 dependency chain 0/4" \
    "stable_claim_allowed=false" \
    "SDK 0/12" \
    "P0 0/4" \
    "stable=false" \
    "approved_runtime_evidence_missing"; do
    if ! grep -F "${dry_run_non_claim}" "${WORK_DIR}/dry-run.out" >/dev/null; then
        echo "dry-run install output missed non-claim boundary: ${dry_run_non_claim}" >&2
        cat "${WORK_DIR}/dry-run.out" >&2
        exit 1
    fi
done

fake_bin="${WORK_DIR}/fake-bin"
failure_root="${WORK_DIR}/failure-root"
mkdir -p "${fake_bin}"
cat > "${fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *.incoming.* ]]; then
        exit 77
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${fake_bin}/mv"
if PATH="${fake_bin}:${PATH}" "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${failure_root}" \
    >"${WORK_DIR}/fail-mv.out" 2>"${WORK_DIR}/fail-mv.err"; then
    echo "install_obelisk.sh succeeded despite failing runtime rename" >&2
    exit 1
fi
if find "${failure_root}" -name '*.incoming.*' | grep -q .; then
    echo "failed runtime install left incoming temporary files" >&2
    find "${failure_root}" -print >&2
    exit 1
fi
if find "${failure_root}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "failed runtime install left staging directories" >&2
    find "${failure_root}" -maxdepth 1 -print >&2
    exit 1
fi

pair_failure_root="${WORK_DIR}/pair-failure-root"
mkdir -p "${pair_failure_root}/lib"
printf 'old-subhook\n' > "${pair_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${pair_failure_root}/lib/libobelisk.so"
cat > "${fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *.incoming.* ]]; then
        count=0
        if [[ -n "${OBELISK_FAKE_MV_COUNT:-}" && -f "${OBELISK_FAKE_MV_COUNT}" ]]; then
            count="$(cat "${OBELISK_FAKE_MV_COUNT}")"
        fi
        count=$((count + 1))
        if [[ -n "${OBELISK_FAKE_MV_COUNT:-}" ]]; then
            printf '%s\n' "${count}" > "${OBELISK_FAKE_MV_COUNT}"
        fi
        if [[ "${count}" == "2" ]]; then
            exit 77
        fi
        break
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${fake_bin}/mv"
fake_mv_count="${WORK_DIR}/fake-mv-count"
if OBELISK_FAKE_MV_COUNT="${fake_mv_count}" PATH="${fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${pair_failure_root}" \
    >"${WORK_DIR}/pair-fail-mv.out" 2>"${WORK_DIR}/pair-fail-mv.err"; then
    echo "install_obelisk.sh succeeded despite failing second runtime rename" >&2
    exit 1
fi
if [[ "$(cat "${pair_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed runtime pair install did not restore original libsubhook.so" >&2
    ls -la "${pair_failure_root}/lib" >&2
    exit 1
fi
if [[ "$(cat "${pair_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed runtime pair install changed original libobelisk.so" >&2
    ls -la "${pair_failure_root}/lib" >&2
    exit 1
fi
if find "${pair_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed runtime pair install left temporary files" >&2
    find "${pair_failure_root}" -print >&2
    exit 1
fi

sdk_failure_root="${WORK_DIR}/sdk-failure-root"
sdk_fake_bin="${WORK_DIR}/sdk-fake-bin"
mkdir -p "${sdk_failure_root}/lib" "${sdk_fake_bin}"
printf 'old-subhook\n' > "${sdk_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${sdk_failure_root}/lib/libobelisk.so"
real_cmake="$(command -v cmake)"
cat > "${sdk_fake_bin}/cmake" <<'SH'
#!/usr/bin/env bash
previous=""
for arg in "$@"; do
    if [[ "${previous}" == "--component" && "${arg}" == "SDK" ]]; then
        exit 78
    fi
    previous="${arg}"
done
exec "${OBELISK_REAL_CMAKE}" "$@"
SH
chmod +x "${sdk_fake_bin}/cmake"
if OBELISK_REAL_CMAKE="${real_cmake}" PATH="${sdk_fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${sdk_failure_root}" \
    >"${WORK_DIR}/sdk-fail.out" 2>"${WORK_DIR}/sdk-fail.err"; then
    echo "install_obelisk.sh succeeded despite failing SDK install" >&2
    exit 1
fi
if [[ "$(cat "${sdk_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed SDK install did not restore original libsubhook.so" >&2
    ls -la "${sdk_failure_root}/lib" >&2
    exit 1
fi
if [[ "$(cat "${sdk_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed SDK install did not restore original libobelisk.so" >&2
    ls -la "${sdk_failure_root}/lib" >&2
    exit 1
fi
if find "${sdk_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed SDK install left temporary files" >&2
    find "${sdk_failure_root}" -print >&2
    exit 1
fi

sdk_publish_failure_root="${WORK_DIR}/sdk-publish-failure-root"
sdk_publish_fake_bin="${WORK_DIR}/sdk-publish-fake-bin"
mkdir -p "${sdk_publish_failure_root}/lib" \
    "${sdk_publish_failure_root}/include/obelisk" \
    "${sdk_publish_failure_root}/lib/cmake/Obelisk" \
    "${sdk_publish_fake_bin}"
printf 'old-subhook\n' > "${sdk_publish_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${sdk_publish_failure_root}/lib/libobelisk.so"
printf 'old-header\n' > "${sdk_publish_failure_root}/include/obelisk/ObeliskApi.h"
printf 'old-config\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskConfig.cmake"
printf 'old-version\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskConfigVersion.cmake"
printf 'old-targets\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskTargets.cmake"
cat > "${sdk_publish_fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *ObeliskConfig.cmake.incoming.* ]]; then
        exit 79
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${sdk_publish_fake_bin}/mv"
if PATH="${sdk_publish_fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${sdk_publish_failure_root}" \
    >"${WORK_DIR}/sdk-publish-fail.out" 2>"${WORK_DIR}/sdk-publish-fail.err"; then
    echo "install_obelisk.sh succeeded despite failing SDK publish" >&2
    exit 1
fi
if [[ "$(cat "${sdk_publish_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed SDK publish did not restore original libsubhook.so" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi
if [[ "$(cat "${sdk_publish_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed SDK publish did not restore original libobelisk.so" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi
for sdk_file in \
    "include/obelisk/ObeliskApi.h:old-header" \
    "lib/cmake/Obelisk/ObeliskConfig.cmake:old-config" \
    "lib/cmake/Obelisk/ObeliskConfigVersion.cmake:old-version" \
    "lib/cmake/Obelisk/ObeliskTargets.cmake:old-targets"; do
    sdk_path="${sdk_file%%:*}"
    expected="${sdk_file#*:}"
    if [[ "$(cat "${sdk_publish_failure_root}/${sdk_path}")" != "${expected}" ]]; then
        echo "failed SDK publish did not restore ${sdk_path}" >&2
        find "${sdk_publish_failure_root}" -print >&2
        exit 1
    fi
done
if find "${sdk_publish_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-sdk.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed SDK publish left temporary files" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi

install_output="${WORK_DIR}/install.out"
"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${INSTALL_ROOT}" \
    >"${install_output}"
if ! grep -F 'Obelisk runtime/SDK package-shape artifacts installed to' \
    "${install_output}" >/dev/null; then
    echo "real install output did not describe package-shape artifact publication" >&2
    cat "${install_output}" >&2
    exit 1
fi
if grep -F 'Obelisk installed to' "${install_output}" >/dev/null; then
    echo "real install output used ambiguous install success wording" >&2
    cat "${install_output}" >&2
    exit 1
fi
for install_non_claim in \
    "runtime/live-ops approval" \
    "Plugin Hub readiness/publication" \
    "support-tier activation" \
    "stable SDK claim" \
    "v1 SDK completion" \
    "SDK blocker promotion 0/12" \
    "P0 dependency chain 0/4" \
    "stable_claim_allowed=false" \
    "SDK 0/12" \
    "P0 0/4" \
    "stable=false" \
    "approved_runtime_evidence_missing"; do
    if ! grep -F "${install_non_claim}" "${install_output}" >/dev/null; then
        echo "real install output missed non-claim boundary: ${install_non_claim}" >&2
        cat "${install_output}" >&2
        exit 1
    fi
done

require_path "${INSTALL_ROOT}/lib/libobelisk.so"
require_path "${INSTALL_ROOT}/lib/libsubhook.so"
require_path "${INSTALL_ROOT}/plugins"
require_path "${INSTALL_ROOT}/config"
require_path "${INSTALL_ROOT}/logs"
require_path "${INSTALL_ROOT}/state/instances"
require_path "${INSTALL_ROOT}/include/obelisk/ObeliskApi.h"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskConfig.cmake"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskConfigVersion.cmake"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskTargets.cmake"
require_path "${SDK_CONSUMER_FIXTURE}"

for managed_dir in \
    "lib" \
    "plugins" \
    "include" \
    "include/obelisk" \
    "lib/cmake" \
    "lib/cmake/Obelisk" \
    "config" \
    "logs" \
    "state" \
    "state/instances"; do
    managed_path="${INSTALL_ROOT}/${managed_dir}"
    if [[ -L "${managed_path}" || ! -d "${managed_path}" ]]; then
        echo "Managed install directory must be a real non-symlink directory: ${managed_path}" >&2
        ls -la "$(dirname "${managed_path}")" >&2
        exit 1
    fi
done

installed_headers="$(find "${INSTALL_ROOT}/include" -type f -printf '%P\n' | sort)"
expected_public_headers=$'obelisk/ObeliskApi.h\nobelisk/ObeliskCommandApi.h\nobelisk/ObeliskPlayerLifecycleApi.h'
if [[ "${installed_headers}" != "${expected_public_headers}" ]]; then
    echo "SDK install published unexpected public headers" >&2
    printf '%s\n' "${installed_headers}" >&2
    exit 1
fi
require_installed_public_header_has_no_blocked_symbols "${INSTALL_ROOT}/include/obelisk/ObeliskApi.h"
require_installed_public_header_has_no_blocked_symbols "${INSTALL_ROOT}/include/obelisk/ObeliskCommandApi.h"
require_installed_public_header_has_no_blocked_symbols "${INSTALL_ROOT}/include/obelisk/ObeliskPlayerLifecycleApi.h"

installed_cmake_package_files="$(find "${INSTALL_ROOT}/lib/cmake/Obelisk" -maxdepth 1 -type f -name '*.cmake' -printf '%f\n' | sort)"
expected_cmake_package_files=$'ObeliskConfig.cmake\nObeliskConfigVersion.cmake\nObeliskTargets.cmake'
if [[ "${installed_cmake_package_files}" != "${expected_cmake_package_files}" ]]; then
    echo "SDK install published unexpected CMake package files" >&2
    printf '%s\n' "${installed_cmake_package_files}" >&2
    exit 1
fi

if find "${INSTALL_ROOT}/lib" -maxdepth 1 -name '*.incoming.*' | grep -q .; then
    echo "Runtime install left incoming temporary files in ${INSTALL_ROOT}/lib" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "Runtime install left staging directories in ${INSTALL_ROOT}" >&2
    find "${INSTALL_ROOT}" -maxdepth 1 -print >&2
    exit 1
fi

for cmake_package_file in "${INSTALL_ROOT}"/lib/cmake/Obelisk/*.cmake; do
    require_not_contains "${REPO_DIR}" "${cmake_package_file}"
    require_not_contains "${REPO_DIR}/build" "${cmake_package_file}"
done
require_cmake_package_shape_only "${INSTALL_ROOT}/lib/cmake/Obelisk"
require_installed_cmake_package_has_no_blocked_aliases "${INSTALL_ROOT}/lib/cmake/Obelisk"

SDK_EXACT_STABLE_CHECK_DIR="${WORK_DIR}/sdk_exact_stable_package_check"
mkdir -p "${SDK_EXACT_STABLE_CHECK_DIR}"
cat > "${SDK_EXACT_STABLE_CHECK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkExactStablePackageCheck LANGUAGES C)

find_package(Obelisk 0.1.0 EXACT CONFIG QUIET COMPONENTS SDK)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Installed Obelisk package accepted an exact stable-looking 0.1.0 SDK request")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Exact stable-looking request leaked Obelisk::obelisk_sdk")
endif()

find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Installed Obelisk package did not define Obelisk::obelisk_sdk")
endif()
CMAKE
cmake -S "${SDK_EXACT_STABLE_CHECK_DIR}" -B "${SDK_EXACT_STABLE_CHECK_DIR}/build" \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}"

SDK_MISSING_COMPONENT_CHECK_DIR="${WORK_DIR}/sdk_missing_component_package_check"
mkdir -p "${SDK_MISSING_COMPONENT_CHECK_DIR}"
cat > "${SDK_MISSING_COMPONENT_CHECK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkMissingComponentPackageCheck LANGUAGES C)

find_package(Obelisk 0.1.0 CONFIG QUIET)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Installed Obelisk package accepted a request without COMPONENTS SDK")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Missing SDK component request leaked Obelisk::obelisk_sdk")
endif()

find_package(Obelisk 0.1.0 CONFIG QUIET COMPONENTS Runtime)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Installed Obelisk package accepted unsupported Runtime component")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Unsupported Runtime component request leaked Obelisk::obelisk_sdk")
endif()
CMAKE
cmake -S "${SDK_MISSING_COMPONENT_CHECK_DIR}" -B "${SDK_MISSING_COMPONENT_CHECK_DIR}/build" \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}"

if readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" | grep -F "${REPO_DIR}" >/dev/null; then
    echo "Installed libobelisk.so contains a source/build-tree dynamic path leak" >&2
    readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" >&2
    exit 1
fi

if ! readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" | grep -F 'Library runpath: [$ORIGIN]' >/dev/null; then
    echo "Installed libobelisk.so must resolve bundled runtime dependencies through RUNPATH=\$ORIGIN" >&2
    readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" >&2
    exit 1
fi

SDK_VERSIONLESS_CHECK_DIR="${WORK_DIR}/sdk_versionless_package_check"
mkdir -p "${SDK_VERSIONLESS_CHECK_DIR}"
cat > "${SDK_VERSIONLESS_CHECK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkVersionlessPackageCheck LANGUAGES C)

find_package(Obelisk CONFIG QUIET COMPONENTS SDK)

if(Obelisk_FOUND)
    message(FATAL_ERROR "Installed Obelisk package accepted a versionless SDK request")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Versionless SDK request leaked Obelisk::obelisk_sdk")
endif()
CMAKE
cmake -S "${SDK_VERSIONLESS_CHECK_DIR}" -B "${SDK_VERSIONLESS_CHECK_DIR}/build" \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}"

SDK_EXPLICIT_PACKAGE_CHECK_DIR="${WORK_DIR}/sdk_explicit_package_check"
mkdir -p "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}"
cat > "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkExplicitPackageCheck LANGUAGES C)

find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)

if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Installed Obelisk package did not define Obelisk::obelisk_sdk")
endif()
foreach(forbidden_target
    Obelisk::obelisk
    Obelisk::subhook
    Obelisk::runtime
    Obelisk::libobelisk
    Obelisk::libsubhook
)
    if(TARGET ${forbidden_target})
        message(FATAL_ERROR "Installed Obelisk package exposed forbidden target: ${forbidden_target}")
    endif()
endforeach()
if(NOT DEFINED OBELISK_EXPECTED_INCLUDE_DIR)
    message(FATAL_ERROR "Missing OBELISK_EXPECTED_INCLUDE_DIR for package target invariant check")
endif()
get_filename_component(expected_include_dir "${OBELISK_EXPECTED_INCLUDE_DIR}" REALPATH)
get_target_property(sdk_target_type Obelisk::obelisk_sdk TYPE)
if(NOT sdk_target_type STREQUAL "INTERFACE_LIBRARY")
    message(FATAL_ERROR "Obelisk::obelisk_sdk must be an interface SDK target, got: ${sdk_target_type}")
endif()
get_target_property(sdk_include_dirs Obelisk::obelisk_sdk INTERFACE_INCLUDE_DIRECTORIES)
if(NOT sdk_include_dirs)
    message(FATAL_ERROR "Obelisk::obelisk_sdk did not expose installed SDK include directories")
endif()
set(found_expected_include_dir FALSE)
foreach(sdk_include_dir IN LISTS sdk_include_dirs)
    get_filename_component(resolved_sdk_include_dir "${sdk_include_dir}" REALPATH)
    if(resolved_sdk_include_dir STREQUAL expected_include_dir)
        set(found_expected_include_dir TRUE)
    endif()
endforeach()
if(NOT found_expected_include_dir)
    message(FATAL_ERROR
        "Obelisk::obelisk_sdk did not expose expected installed include dir: ${expected_include_dir}; got ${sdk_include_dirs}")
endif()
get_target_property(sdk_link_libraries Obelisk::obelisk_sdk INTERFACE_LINK_LIBRARIES)
if(sdk_link_libraries AND NOT sdk_link_libraries STREQUAL "sdk_link_libraries-NOTFOUND")
    message(FATAL_ERROR "Obelisk::obelisk_sdk unexpectedly links runtime/private libraries: ${sdk_link_libraries}")
endif()
get_target_property(sdk_imported_location Obelisk::obelisk_sdk IMPORTED_LOCATION)
if(sdk_imported_location AND NOT sdk_imported_location STREQUAL "sdk_imported_location-NOTFOUND")
    message(FATAL_ERROR "Obelisk::obelisk_sdk unexpectedly exposes an imported binary location: ${sdk_imported_location}")
endif()
foreach(imported_binary_property
    IMPORTED_IMPLIB
    IMPORTED_IMPLIB_DEBUG
    IMPORTED_IMPLIB_MINSIZEREL
    IMPORTED_IMPLIB_RELEASE
    IMPORTED_IMPLIB_RELWITHDEBINFO
    IMPORTED_LINK_DEPENDENT_LIBRARIES
    IMPORTED_LINK_DEPENDENT_LIBRARIES_DEBUG
    IMPORTED_LINK_DEPENDENT_LIBRARIES_MINSIZEREL
    IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE
    IMPORTED_LINK_DEPENDENT_LIBRARIES_RELWITHDEBINFO
    IMPORTED_LOCATION_DEBUG
    IMPORTED_LOCATION_MINSIZEREL
    IMPORTED_LOCATION_RELEASE
    IMPORTED_LOCATION_RELWITHDEBINFO
    IMPORTED_OBJECTS
    IMPORTED_OBJECTS_DEBUG
    IMPORTED_OBJECTS_MINSIZEREL
    IMPORTED_OBJECTS_RELEASE
    IMPORTED_OBJECTS_RELWITHDEBINFO
    IMPORTED_SONAME
    IMPORTED_SONAME_DEBUG
    IMPORTED_SONAME_MINSIZEREL
    IMPORTED_SONAME_RELEASE
    IMPORTED_SONAME_RELWITHDEBINFO
)
    get_target_property(imported_binary_value Obelisk::obelisk_sdk ${imported_binary_property})
    if(imported_binary_value AND NOT imported_binary_value STREQUAL "imported_binary_value-NOTFOUND")
        message(FATAL_ERROR
            "Obelisk::obelisk_sdk unexpectedly exposes ${imported_binary_property}: ${imported_binary_value}")
    endif()
endforeach()
if(NOT Obelisk_SDK_FOUND)
    message(FATAL_ERROR "Installed Obelisk package did not report SDK component found")
endif()
if(NOT Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS STREQUAL "package-shape-evidence-only")
    message(FATAL_ERROR "Installed Obelisk package did not mark SDK package shape as evidence-only")
endif()
if(NOT DEFINED Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY OR
   NOT Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY)
    message(FATAL_ERROR "Installed Obelisk package did not mark find_package SDK as package-shape-only")
endif()
foreach(non_claim_var
    Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED
    Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED
    Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED
    Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED
    Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED
    Obelisk_V1_COMPLETION_CLAIM_ALLOWED
    Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED
    Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED
    Obelisk_EXACT_VERSION_REQUESTS_ALLOWED
    Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM
    Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS
    Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE
)
    if(NOT DEFINED ${non_claim_var})
        message(FATAL_ERROR "Installed Obelisk package missed non-claim marker: ${non_claim_var}")
    endif()
    if(${non_claim_var})
        message(FATAL_ERROR "Installed Obelisk package enabled forbidden non-claim marker: ${non_claim_var}")
    endif()
endforeach()
if(NOT Obelisk_VERSION STREQUAL "0.1.0")
    message(FATAL_ERROR "Unexpected Obelisk package version: ${Obelisk_VERSION}")
endif()
if(NOT Obelisk_VERSION_MAJOR EQUAL 0)
    message(FATAL_ERROR "Unexpected Obelisk package version major: ${Obelisk_VERSION_MAJOR}")
endif()
if(NOT Obelisk_VERSION_MINOR EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk package version minor: ${Obelisk_VERSION_MINOR}")
endif()
if(NOT Obelisk_VERSION_PATCH EQUAL 0)
    message(FATAL_ERROR "Unexpected Obelisk package version patch: ${Obelisk_VERSION_PATCH}")
endif()
if(NOT Obelisk_SDK_BLOCKER_PROMOTION_COUNT EQUAL 0 OR
   NOT Obelisk_SDK_BLOCKER_PROMOTION_TOTAL EQUAL 12 OR
   NOT Obelisk_P0_DEPENDENCY_COUNT EQUAL 0 OR
   NOT Obelisk_P0_DEPENDENCY_TOTAL EQUAL 4 OR
   NOT Obelisk_ACTIVE_COMPLETION_BLOCKER STREQUAL "approved_runtime_evidence_missing")
    message(FATAL_ERROR "Installed Obelisk package did not preserve blocked SDK completion markers")
endif()

add_library(versionless_sdk_check SHARED versionless_sdk_check.c)
target_link_libraries(versionless_sdk_check PRIVATE Obelisk::obelisk_sdk)
CMAKE
cat > "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}/versionless_sdk_check.c" <<'C'
#include <obelisk/ObeliskApi.h>

_Static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected Obelisk API ABI version");

unsigned obelisk_sdk_versionless_package_check(void) {
    return OBELISK_API_ABI_VERSION;
}
C
cmake -S "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}" -B "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_EXPECTED_INCLUDE_DIR="${INSTALL_ROOT}/include"
cmake --build "${SDK_EXPLICIT_PACKAGE_CHECK_DIR}/build" --parallel

default_reinstall_output="${WORK_DIR}/default-reinstall.out"
"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${INSTALL_ROOT}" \
    >"${default_reinstall_output}"
if find "${INSTALL_ROOT}/lib" -maxdepth 1 -name '*.bak' | grep -q .; then
    echo "Default reinstall created backup artifacts without --backup-existing" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi
if ! grep -F 'package-shape evidence only' "${default_reinstall_output}" >/dev/null; then
    echo "default reinstall output missed package-shape non-claim boundary" >&2
    cat "${default_reinstall_output}" >&2
    exit 1
fi

"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" --backup-existing "${INSTALL_ROOT}" >/tmp/obelisk-install-layout-reinstall.log
obelisk_backup_count="$(find "${INSTALL_ROOT}/lib" -maxdepth 1 -name 'libobelisk.so.*.bak' | wc -l)"
subhook_backup_count="$(find "${INSTALL_ROOT}/lib" -maxdepth 1 -name 'libsubhook.so.*.bak' | wc -l)"
if [[ "${obelisk_backup_count}" != "1" || "${subhook_backup_count}" != "1" ]]; then
    echo "Expected one backup each for libobelisk.so and libsubhook.so after backup reinstall" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}/lib" -maxdepth 1 -name '*.incoming.*' | grep -q .; then
    echo "Runtime reinstall left incoming temporary files in ${INSTALL_ROOT}/lib" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "Runtime reinstall left staging directories in ${INSTALL_ROOT}" >&2
    find "${INSTALL_ROOT}" -maxdepth 1 -print >&2
    exit 1
fi

CONFIG_DIR="${INSTALL_ROOT}/config/install_layout_consumer"
CONFIG_PATH="${CONFIG_DIR}/config.json"
PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_consumer.so"
C_ABI_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_c_abi_consumer.so"
NO_SHUTDOWN_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_no_shutdown_consumer.so"
DESCRIPTOR_CATALOG_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_descriptor_catalog_consumer.so"
DESCRIPTOR_TIMER_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_descriptor_timer_consumer.so"
RELEASE_BASE_EVENTS_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oBaseEvents.so"
RELEASE_TIMER_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oProcessTimer.so"
RELEASE_DESCRIPTOR_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oDescriptorCatalog.so"

mkdir -p "${CONFIG_DIR}"
cat > "${CONFIG_PATH}" <<'JSON'
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
JSON

cp -R "${REPO_DIR}/tests/sdk_installed_consumer/." "${WORK_DIR}/"

cmake -S "${WORK_DIR}" -B "${WORK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_INSTALL_ROOT="${INSTALL_ROOT}" \
    -DOBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT="${REPO_DIR}/plugins" \
    -DOBELISK_RELEASE_SCOPE_EXTERN_ROOT="${REPO_DIR}/extern" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${WORK_DIR}/build" --parallel

require_path "${PLUGIN_PATH}"
require_path "${C_ABI_PLUGIN_PATH}"
require_path "${NO_SHUTDOWN_PLUGIN_PATH}"
require_path "${DESCRIPTOR_CATALOG_PLUGIN_PATH}"
require_path "${DESCRIPTOR_TIMER_PLUGIN_PATH}"
require_path "${RELEASE_BASE_EVENTS_PLUGIN_PATH}"
require_path "${RELEASE_TIMER_PLUGIN_PATH}"
require_path "${RELEASE_DESCRIPTOR_PLUGIN_PATH}"

if ! grep -F "${INSTALL_ROOT}/include" "${WORK_DIR}/build/compile_commands.json" >/dev/null; then
    echo "SDK consumer did not include headers from the installed SDK layout" >&2
    cat "${WORK_DIR}/build/compile_commands.json" >&2
    exit 1
fi

if grep -F "${REPO_DIR}/include" "${WORK_DIR}/build/compile_commands.json" >/dev/null; then
    echo "SDK consumer accidentally included headers from the source tree" >&2
    cat "${WORK_DIR}/build/compile_commands.json" >&2
    exit 1
fi

"${WORK_DIR}/build/consumer_fixture" \
    "${PLUGIN_PATH}" \
    "install_layout_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${C_ABI_PLUGIN_PATH}" \
    "install_layout_c_abi_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${NO_SHUTDOWN_PLUGIN_PATH}" \
    "install_layout_no_shutdown_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${DESCRIPTOR_CATALOG_PLUGIN_PATH}" \
    "install_layout_descriptor_catalog_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${DESCRIPTOR_TIMER_PLUGIN_PATH}" \
    "install_layout_descriptor_timer_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

"${SDK_CONSUMER_FIXTURE}" "${RELEASE_BASE_EVENTS_PLUGIN_PATH}" oBaseEvents
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_BASE_EVENTS_PLUGIN_PATH}" oBaseEvents active-chat-command-helper
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_TIMER_PLUGIN_PATH}" oProcessTimer
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_TIMER_PLUGIN_PATH}" oProcessTimer active-timer
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_DESCRIPTOR_PLUGIN_PATH}" oDescriptorCatalog
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_DESCRIPTOR_PLUGIN_PATH}" oDescriptorCatalog active-descriptor-catalog

SDK_MINIMAL_EXAMPLE_DIR="${WORK_DIR}/sdk_minimal_plugin"
mkdir -p "${SDK_MINIMAL_EXAMPLE_DIR}"
cp -R "${REPO_DIR}/examples/sdk_minimal_plugin/." "${SDK_MINIMAL_EXAMPLE_DIR}/"
require_no_call_process_event_escape_hatch "${SDK_MINIMAL_EXAMPLE_DIR}" "Minimal SDK example"
cmake -S "${SDK_MINIMAL_EXAMPLE_DIR}" -B "${SDK_MINIMAL_EXAMPLE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${SDK_MINIMAL_EXAMPLE_DIR}/build" --parallel
SDK_MINIMAL_EXAMPLE_PLUGIN_PATH="${SDK_MINIMAL_EXAMPLE_DIR}/build/obelisk_sdk_minimal_plugin.so"
require_path "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}"
require_dynamic_exports "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}" \
    ObeliskPlugin_GetInfo \
    ObeliskPlugin_Init \
    ObeliskPlugin_Shutdown

require_no_runtime_private_linkage \
    "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}" \
    "${SDK_MINIMAL_EXAMPLE_DIR}/build" \
    "Minimal SDK example"

require_external_sdk_compile_commands \
    "${SDK_MINIMAL_EXAMPLE_DIR}/build/compile_commands.json" \
    "Minimal SDK example"

"${WORK_DIR}/build/consumer_fixture" \
    "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}" \
    "obelisk_sdk_minimal_plugin" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

SDK_DESCRIPTOR_EXAMPLE_DIR="${WORK_DIR}/sdk_descriptor_catalog"
mkdir -p "${SDK_DESCRIPTOR_EXAMPLE_DIR}"
cp -R "${REPO_DIR}/examples/sdk_descriptor_catalog/." "${SDK_DESCRIPTOR_EXAMPLE_DIR}/"
require_no_call_process_event_escape_hatch "${SDK_DESCRIPTOR_EXAMPLE_DIR}" "Descriptor catalog SDK example"
cmake -S "${SDK_DESCRIPTOR_EXAMPLE_DIR}" -B "${SDK_DESCRIPTOR_EXAMPLE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_SDK_DESCRIPTOR_CATALOG_TEST_PROBES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${SDK_DESCRIPTOR_EXAMPLE_DIR}/build" --parallel
SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH="${SDK_DESCRIPTOR_EXAMPLE_DIR}/build/obelisk_sdk_descriptor_catalog.so"
require_path "${SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH}"
require_dynamic_exports "${SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH}" \
    InstallLayoutConsumer_DescriptorCatalogValidated \
    ObeliskPlugin_GetInfo \
    ObeliskPlugin_Init \
    ObeliskPlugin_Shutdown

require_no_runtime_private_linkage \
    "${SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH}" \
    "${SDK_DESCRIPTOR_EXAMPLE_DIR}/build" \
    "Descriptor catalog SDK example"

require_external_sdk_compile_commands \
    "${SDK_DESCRIPTOR_EXAMPLE_DIR}/build/compile_commands.json" \
    "Descriptor catalog SDK example"

"${WORK_DIR}/build/consumer_fixture" \
    "${SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH}" \
    "obelisk_sdk_descriptor_catalog" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

SDK_TIMER_EXAMPLE_DIR="${WORK_DIR}/sdk_timer_plugin"
mkdir -p "${SDK_TIMER_EXAMPLE_DIR}"
cp -R "${REPO_DIR}/examples/sdk_timer_plugin/." "${SDK_TIMER_EXAMPLE_DIR}/"
require_no_call_process_event_escape_hatch "${SDK_TIMER_EXAMPLE_DIR}" "Timer SDK example"
cmake -S "${SDK_TIMER_EXAMPLE_DIR}" -B "${SDK_TIMER_EXAMPLE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_SDK_TIMER_PLUGIN_TEST_PROBES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${SDK_TIMER_EXAMPLE_DIR}/build" --parallel
SDK_TIMER_EXAMPLE_PLUGIN_PATH="${SDK_TIMER_EXAMPLE_DIR}/build/obelisk_sdk_timer_plugin.so"
require_path "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}"
require_dynamic_exports "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}" \
    InstallLayoutConsumer_ScheduledCallbackSeen \
    ObeliskPlugin_GetInfo \
    ObeliskPlugin_Init \
    ObeliskPlugin_Shutdown

require_no_runtime_private_linkage \
    "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}" \
    "${SDK_TIMER_EXAMPLE_DIR}/build" \
    "Timer SDK example"

require_external_sdk_compile_commands \
    "${SDK_TIMER_EXAMPLE_DIR}/build/compile_commands.json" \
    "Timer SDK example"

"${WORK_DIR}/build/consumer_fixture" \
    "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}" \
    "obelisk_sdk_timer_plugin" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

echo "Install layout and installed SDK package-shape consumer validation passed for ${INSTALL_ROOT}; package-shape evidence only, no runtime/stable/v1/Plugin Hub claim."
