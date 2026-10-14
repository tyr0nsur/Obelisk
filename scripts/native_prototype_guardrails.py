"""Exact names of the native prototype; these never promote historical SDK modules.

The complete-SDK decision manifests predate the callback-scoped prototype. Their
generic command/player matchers must still reject other APIs and authority claims.
Only the explicit extension is exempt, and header exemptions require its complete
shape rather than an isolated capability or a renamed blocked API.
"""

from pathlib import Path
import re


NATIVE_PROTOTYPE_CAPABILITIES = (
    "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
    "OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT",
    "OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS",
)
NATIVE_PROTOTYPE_API_FIELDS = (
    "RegisterCommandWithOwnerTokenHandle",
    "UnregisterCommandWithOwnerToken",
    "ReplyToCommandWithOwnerToken",
    "GetCommandPlayerWithOwnerToken",
    "RegisterPlayerLifecycleWithOwnerTokenHandle",
    "UnregisterPlayerLifecycleWithOwnerToken",
)
NATIVE_PROTOTYPE_HEADER_NAMES = ("ObeliskCommandApi.h", "ObeliskPlayerLifecycleApi.h")
NATIVE_PROTOTYPE_TYPES = (
    "ObeliskCommandApi", "ObeliskPlayerLifecycleApi",
    "ObeliskCommandStringView", "ObeliskCommandInvocation", "ObeliskCommandPlayer",
    "ObeliskCommandCallback", "ObeliskPlayerLifecycleStringView",
    "ObeliskPlayerLifecycleEvent", "ObeliskPlayerLifecycleCallback",
)
NATIVE_PROTOTYPE_MACROS = (
    "OBELISK_COMMAND_INVOCATION_ABI_VERSION", "OBELISK_COMMAND_PLAYER_ABI_VERSION",
    "OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE",
    "OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE",
    "OBELISK_COMMAND_PLAYER_NAME_MAX_BYTES", "OBELISK_COMMAND_PLAYER_PLATFORM_ID_MAX_BYTES",
    "OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION",
    "OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED",
    "OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED",
    "OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE",
    "OBELISK_PLAYER_LIFECYCLE_FLAGS_SUPPORTED_MASK",
    "OBELISK_PLAYER_LIFECYCLE_NAME_MAX_BYTES", "OBELISK_PLAYER_LIFECYCLE_PLATFORM_ID_MAX_BYTES",
)
NATIVE_PROTOTYPE_SYMBOLS = frozenset(
    (*NATIVE_PROTOTYPE_CAPABILITIES, *NATIVE_PROTOTYPE_API_FIELDS,
     *NATIVE_PROTOTYPE_TYPES, *NATIVE_PROTOTYPE_MACROS)
)
_NATIVE_API_SIGNATURES = (
    "uint64_t(*RegisterCommandWithOwnerTokenHandle)(uint64_townerToken,constchar*commandName,ObeliskCommandCallbackcallback,void*userData);",
    "bool(*UnregisterCommandWithOwnerToken)(uint64_townerToken,uint64_tregistrationId);",
    "bool(*ReplyToCommandWithOwnerToken)(uint64_townerToken,uint64_tinvocationToken,ObeliskCommandStringViewreply);",
    "bool(*GetCommandPlayerWithOwnerToken)(uint64_townerToken,uint64_tinvocationToken,ObeliskCommandPlayer*out);",
    "uint64_t(*RegisterPlayerLifecycleWithOwnerTokenHandle)(uint64_townerToken,ObeliskPlayerLifecycleCallbackcallback,void*userData);",
    "bool(*UnregisterPlayerLifecycleWithOwnerToken)(uint64_townerToken,uint64_tregistrationId);",
)


def native_prototype_header_symbols(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return set()
    return native_prototype_symbols_for_header(text)


def native_prototype_symbols_for_header(text: str) -> set[str]:
    stripped = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
    if not all(len(re.findall(r'#\s*include\s*[<"](?:obelisk/)?' + re.escape(name) + r'[>"]', stripped)) == 1
               for name in NATIVE_PROTOTYPE_HEADER_NAMES):
        return set()
    for bit, cap in enumerate(NATIVE_PROTOTYPE_CAPABILITIES, start=12):
        values = re.findall(r"#\s*define\s+" + re.escape(cap) + r"\b([^\n]*)", stripped)
        if len(values) != 1 or re.sub(r"\s+", "", values[0]) != f"(1ull<<{bit})":
            return set()
    compact = re.sub(r"\s+", "", stripped)
    for field, signature in zip(NATIVE_PROTOTYPE_API_FIELDS, _NATIVE_API_SIGNATURES):
        if len(re.findall(r"\b" + re.escape(field) + r"\b", stripped)) != 1 or signature not in compact:
            return set()
    tables = re.findall(r"typedef\s+struct\s+ObeliskApi\s*\{([^}]+)\}\s*ObeliskApi\s*;", stripped, flags=re.DOTALL)
    if len(tables) != 1 or not re.sub(r"\s+", "", tables[0]).endswith("".join(_NATIVE_API_SIGNATURES)):
        return set()
    return set(NATIVE_PROTOTYPE_SYMBOLS)


def without_native_prototype_symbols(text: str, *, header_only: bool = False) -> str:
    allowed = native_prototype_symbols_for_header(text) if header_only else NATIVE_PROTOTYPE_SYMBOLS
    if not allowed:
        return text
    if header_only:
        # Historical identity scans also forbid this parameter name. Exempt only
        # the verified command-registration declaration, never another field.
        text = re.sub(
            r"\(\s*\*\s*RegisterCommandWithOwnerTokenHandle\s*\)[^;]*;",
            lambda match: re.sub(r"\bcommandName\b", "prototype_input", match.group(0)),
            text,
        )
    pattern = r"\b(?:" + "|".join(re.escape(name) for name in sorted(allowed)) + r")\b"
    return re.sub(pattern, "NativePrototype", text)


def native_prototype_scan_text(text: str) -> str:
    # The copied display-name member is legal only alongside these exact types;
    # their fields are separately frozen by the public-header layout checks.
    copied_player = re.search(r"\b(?:ObeliskCommandPlayer|ObeliskPlayerLifecycleEvent)\b", text)
    text = without_native_prototype_symbols(text)
    if copied_player:
        text = re.sub(r"\bplayer_name\b", "copied_display_name", text)
    return text
