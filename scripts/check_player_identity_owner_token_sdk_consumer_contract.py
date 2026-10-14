#!/usr/bin/env python3
"""Validate the candidate-only player identity owner-token SDK consumer contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_public_abi_preflight_candidate as public_abi_preflight
from native_prototype_guardrails import without_native_prototype_symbols


SCHEMA = "obelisk.player-identity-owner-token-sdk-consumer-contract.v1"
REPORT_SCHEMA = "obelisk.player-identity-owner-token-sdk-consumer-contract-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_MANIFEST = Path(
    "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json"
)
DEFAULT_PUBLIC_ABI_PREFLIGHT = Path(
    "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json"
)
DEFAULT_PRIVATE_POD_LAYOUT = Path(
    "docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json"
)
DEFAULT_PUBLIC_HEADER = Path("include/obelisk/ObeliskApi.h")
PUBLIC_ABI_PREFLIGHT_INPUT = "abi.public_pod_contract.public_abi_preflight_candidate"
REQUIRED_ACCEPTED_INPUTS = {PUBLIC_ABI_PREFLIGHT_INPUT}
REQUIRED_SOURCE_ARTIFACTS = {
    "public_abi_preflight_candidate": str(DEFAULT_PUBLIC_ABI_PREFLIGHT),
    "private_pod_layout_candidate": str(DEFAULT_PRIVATE_POD_LAYOUT),
}
REQUIRED_COPIED_PRINCIPAL_FIELDS = {
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
}
NON_COUNTING_ARTIFACT_TOKENS = (
    "cmake_package",
    "cmake-package",
    "diagnostic",
    "find_package",
    "find-package",
    "find_package_obelisk",
    "find-package-obelisk",
    "gobjects",
    "header_only",
    "header-only",
    "identity_owner_token",
    "identity-owner-token",
    "installed_sdk",
    "installed-sdk",
    "obelisk_sdk",
    "obelisk::obelisk_sdk",
    "installed_sdk_consumer",
    "installed-sdk-consumer",
    "installed_sdk_consumer_test",
    "installed-sdk-consumer-test",
    "installed_sdk_consumer_tests",
    "installed-sdk-consumer-tests",
    "installed_sdk_package_shape",
    "installed-sdk-package-shape",
    "offline_gobjects",
    "offline-gobjects",
    "package_shape",
    "package-shape",
    "passive",
    "planning_manifest",
    "planning-manifest",
    "plugin_hub",
    "plugin-hub",
    "public_header",
    "public-header",
    "public_handle",
    "public-handle",
    "review_only",
    "review-only",
    "runtime_evidence_only",
    "runtime-evidence-only",
    "runtime_only",
    "runtime-only",
    "partial",
    "partial_runtime",
    "partial-runtime",
    "runtime_partial",
    "runtime-partial",
    "copied_runtime_partial",
    "copied-runtime-partial",
    "truncated",
    "incomplete",
    "simulation",
    "simulated",
    "side_channel",
    "side-channel",
    "side_lane",
    "side-lane",
    "synthetic",
    "mock",
    "fixture",
    "weak_helper",
    "weak-helper",
    "scoped_statement",
    "scoped-statement",
    "scoped_release_statement",
    "scoped-release-statement",
    "release_statement",
    "release-statement",
    "promotion_certificate",
    "promotion-certificate",
    "completion_certificate",
    "completion-certificate",
)
POSITIVE_CLAIM_VALUES = {
    "accepted",
    "allowed",
    "approved",
    "available",
    "claim_allowed",
    "complete",
    "completed",
    "counted",
    "counts",
    "enabled",
    "green",
    "open",
    "opened",
    "passed",
    "promoted",
    "public",
    "published",
    "ready",
    "release_grade",
    "release_ready",
    "resolved",
    "satisfied",
    "satisfies",
    "stable",
    "stable_ready",
    "stable_sdk",
    "stable_sdk_ready",
    "supported",
    "true",
    "unlocked",
    "yes",
}

REQUIRED_BEFORE_PROMOTION = {
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
    "runtime.lifecycle_evidence",
    "v1_completion",
}
REQUIRED_DOES_NOT_RESOLVE = {
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
    "runtime.lifecycle_evidence",
    "public_sdk",
    "v1_completion",
}
REQUIRED_ABI_LAYOUT_CHECKS = {
    "front-loaded abi_version and struct_size in promoted POD structs",
    "fixed-size POD only; no UE pointers, raw ProcessEvent params, FString, STL, references, or exceptions",
    "append-only after promotion; no inserting or retyping existing fields",
    "struct_size and capability checked before accessing appended fields",
    "layout tests assert size, alignment, offsets, reserved-zero, and prefix compatibility or rejection",
    "descriptor and event payload match the accepted private candidate until a replacement candidate is reviewed",
    "public header changes remain forbidden until the promotion gate opens",
}
REQUIRED_SDK_CONSUMER_CHECKS = {
    "installed SDK consumer compiles against the promoted header",
    "C and C++ consumers check abi_version, struct_size, capability bit, non-null function pointers, and nonzero plugin_owner_token before registration",
    "missing capability, short struct_size, null function pointer, or zero owner token fails closed without registration",
    "consumer treats callback payload storage as callback-local and never retains borrowed pointers",
    "consumer treats principal handles and registration handles as process-local and non-persistent",
    "consumer can unregister by owner token and registration handle",
    "consumer tests prove no dependency on private runtime headers or runtime C++ types",
}
REQUIRED_OWNER_TOKEN_SDK_SEMANTICS = {
    "C and C++ consumers check abi_version, struct_size, capability bit, non-null function pointers, and nonzero plugin_owner_token before registration",
    "missing capability, short struct_size, null function pointer, or zero owner token fails closed without registration",
    "consumer can unregister by owner token and registration handle",
}
REQUIRED_COPIED_PRINCIPAL_SDK_SEMANTICS = {
    "consumer treats callback payload storage as callback-local and never retains borrowed pointers",
    "consumer treats principal handles and registration handles as process-local and non-persistent",
}
REQUIRED_OWNER_CLEANUP_CHECKS = {
    "nonzero plugin_owner_token required",
    "opaque uint64 registration handle returned on success",
    "owner-scoped unregister requires the same plugin_owner_token",
    "plugin init failure removes registrations before dlclose",
    "plugin unload removes registrations and drains in-flight callbacks before dlclose",
    "self-unregister from the callback is safe",
    "callback exceptions do not cross the C ABI",
    "cleanup failure retains unload state for retry instead of pretending dlclose completed",
}
REQUIRED_OWNER_TOKEN_LIFECYCLE_SEMANTICS = {
    "nonzero plugin_owner_token required",
    "owner-scoped unregister requires the same plugin_owner_token",
}
REQUIRED_DOWNSTREAM_CHECKS = {
    "no downstream surface may consume player identity until obelisk.player_identity.v1 has separate promotion evidence",
    "permissions/admin and command response keep independent fail-closed gates",
    "public principal does not authorize lookup, persistence, mutation, return override, send-chat identity, or ResourceHandle identity",
    "downstream artifacts must cite promoted player identity evidence before replacing fail-closed blockers",
}
REQUIRED_BLOCKED_DOWNSTREAM = {
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "player_lookup",
    "storage_persistence",
    "mutation",
    "return_override",
    "send_chat_identity",
    "operator_ingress",
    "resource_handle_identity",
}
REQUIRED_NON_CLAIMS = {
    "candidate-only owner-token SDK consumer planning contract",
    "does not add public header symbols",
    "does not reserve final C symbol names",
    "does not add capability bits",
    "does not add callback ABI",
    "does not edit runtime C++",
    "does not promote obelisk.player_identity.v1",
    "does not resolve abi.layout, sdk.consumer, lifecycle.owner_cleanup, separation.downstream_surfaces, runtime.lifecycle_evidence, public_sdk, or v1_completion",
    "does not promote permissions/admin, command response, commands/replies, lookup, persistence, mutation, return override, ResourceHandle identity, or send-chat identity",
}
FORBIDDEN_STRUCTURED_CLAIM_KEYS = {
    "acceptedforcontractreview",
    "approvedruntimebundleaccepted",
    "approvedruntimebundleavailable",
    "approvedruntimebundlepassed",
    "approvedruntimebundleready",
    "cmakepackageavailable",
    "cmakepackageready",
    "countstowardcompletesdkclaim",
    "descriptorcommandrepliesready",
    "descriptorcommandready",
    "descriptorcommandsrepliesready",
    "descriptorcommandsready",
    "descriptoridentityready",
    "descriptorlookupready",
    "descriptormutationready",
    "descriptorpermissionsadminready",
    "descriptorrepliesready",
    "descriptorresourcehandleready",
    "descriptorreturnoverrideready",
    "descriptorsupporttieractivationready",
    "descriptorsidentityready",
    "findpackageobelisk010available",
    "findpackageobelisk010ready",
    "findpackageready",
    "headerpromotiongateopen",
    "headerpromotiongatepassed",
    "headerpromotiongateready",
    "lifecycleownercleanupready",
    "lifecycleownercleanupreadiness",
    "promotionready",
    "identitylookupready",
    "identityownertokenready",
    "ownertokenidentityready",
    "ownertokenlifecycleready",
    "ownertokenplayeridentityready",
    "ownertokenplayerprincipalready",
    "ownertokenregistrationready",
    "ownertokensdkconsumerready",
    "publicabiready",
    "publicabiavailable",
    "publiccallbackabinow",
    "publiccapabilitybitsnow",
    "publiccapabilitybitready",
    "publiccapabilitybitsready",
    "publicheaderallowed",
    "publicheadergateready",
    "publicheadersymbolsnow",
    "publicheadergateopen",
    "publicheadergatepassed",
    "publicheaderpromotiongateopen",
    "publicheaderpromotiongatepassed",
    "publicheaderpromotiongateready",
    "publicidentityavailable",
    "publicidentitypublished",
    "publicidentityready",
    "publicidentitysupported",
    "publicprincipalavailable",
    "publicprincipalpublished",
    "publicprincipalready",
    "publicprincipalsupported",
    "publicsdkavailable",
    "publicsdkcomplete",
    "publicsdkready",
    "publicsdkv1completionclaim",
    "completesdkaccepted",
    "completesdkavailable",
    "completesdkclaimallowed",
    "completesdkcomplete",
    "completesdkpathaccepted",
    "completesdkpathavailable",
    "completesdkpathcounts",
    "completesdkpathready",
    "completesdkready",
    "sdkcompleteclaimallowed",
    "sdkcompletepathaccepted",
    "sdkcompletepathready",
    "sdkcompletionpathaccepted",
    "sdkcompletionpathcounts",
    "sdkcompletionpathready",
    "commandsrepliesavailable",
    "commandsrepliespublic",
    "commandsrepliespublished",
    "commandsrepliesready",
    "commandsrepliessupported",
    "gobjectspublichandleready",
    "identityownertokenpublichandleready",
    "identityownertokenresourcehandleready",
    "playeridentityownertokenready",
    "playeridentityownertokensdkconsumerready",
    "playerprincipallifecycleready",
    "playerprincipallifecyclepublicabiready",
    "playerprincipallifecyclepublicsdkready",
    "playerprincipalownertokenready",
    "playerprincipalownertokensdkconsumerready",
    "principalownertokenready",
    "offlinegobjectspublichandleready",
    "planningmanifestpublichandleready",
    "publichandleready",
    "resourcehandleavailable",
    "resourcehandleidentityready",
    "resourcehandlepublic",
    "resourcehandlepublished",
    "resourcehandleready",
    "resourcehandlesupported",
    "releasesupportallowed",
    "releasesupportavailable",
    "releasesupportready",
    "releasesupportsupported",
    "releasegradesupportallowed",
    "releasegradesupportavailable",
    "releasegradesupportready",
    "releasegradesupportsupported",
    "routeacceptedaspublicabi",
    "sidechannelpublichandleready",
    "sidelanepublichandleready",
    "sdkconsumerready",
    "sdkconsumerreadiness",
    "callbackabiexposed",
    "callbackabiready",
    "capabilitybitready",
    "capabilitybitsready",
    "crossprocessregistration",
    "crossprocessregistrations",
    "crossprocessregistry",
    "persistentregistration",
    "persistentregistrationhandle",
    "persistentregistrationhandles",
    "persistentregistry",
    "registrationhandlepersistent",
    "registrationhandlespersistent",
    "registrationhandlesrestartstable",
    "registrationhandlesurviverestart",
    "registrationhandlessurviverestart",
    "registrationhandlevalidafterunload",
    "registrationhandlesvalidafterunload",
    "handlepostunloadvalidity",
    "handlespostunloadvalidity",
    "postunloadhandlevalidity",
    "postunloadhandlesvalidity",
    "postunloadvalidity",
    "postunloadvalidityready",
    "registrationspersistent",
    "runtimeenabled",
    "runtimeprincipalready",
    "runtimeready",
    "stableclaimallowed",
    "stablesdkclaimallowed",
    "stablesdkready",
    "productionstablesdkclaimallowed",
    "supporttieractivated",
    "supporttieractivationallowed",
    "supporttierready",
    "pluginhubpublicationallowed",
    "pluginhubpublicationready",
    "pluginhubreadinessclaimallowed",
    "pluginhubready",
    "publicationallowed",
    "publicationavailable",
    "publicationpublished",
    "publicationready",
    "packagepublicationallowed",
    "packagepublicationavailable",
    "packagepublicationpublished",
    "packagepublicationready",
    "pluginpublicationallowed",
    "pluginpublicationavailable",
    "pluginpublicationpublished",
    "pluginpublicationready",
    "installedsdkcompletionclaim",
    "installedsdkcompletionready",
    "installedsdkv1completionclaim",
    "installedsdkpackageshapeavailable",
    "installedsdkpackageshapeready",
    "obeliskconfigcmakeavailable",
    "obeliskconfigcmakeready",
    "obelisktargetscmakeavailable",
    "obelisktargetscmakeready",
    "packageshapeavailable",
    "packageshapeready",
    "packageshapepublichandleready",
    "bareunregisterbyid",
    "bareunregisterbyidavailable",
    "bareunregisterbyidready",
    "bareunregisterbyhandle",
    "bareunregisterbyhandleavailable",
    "bareunregisterbyhandleready",
    "ownerlessunregister",
    "ownerlessunregisterallowed",
    "ownerlessunregisterready",
    "unregisterbyidavailable",
    "unregisterbyidready",
    "unregisterbyhandleavailable",
    "unregisterbyhandleready",
    "v1completionevidence",
    "v1completionready",
    "weakhelperpublichandleready",
    "weakhelperresourcehandleready",
}
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"excludes?|without|until|missing|blocked|blocker|unavailable|required[_ -]?before|"
    r"must[_ -]?not|no_)\b",
    re.IGNORECASE,
)
PUBLIC_TEXT_OVERCLAIM_PATTERNS = {
    "public_header_ready": re.compile(
        r"\bpublic[-_ ]+header(?:[-_ ]+symbols?)?\s+(?:is\s+|are\s+)?"
        r"(?:allowed|available|ready|exposed|promoted|enabled|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_capability_available": re.compile(
        r"\b(?:public[-_ ]+)?(?:identity[-_ ]+)?capability(?:[-_ ]+bits?)?\s+(?:is\s+|are\s+)?"
        r"(?:available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_callback_abi": re.compile(
        r"\b(?:public[-_ ]+)?callback[-_ ]+abi\s+(?:is\s+)?"
        r"(?:available|ready|exposed|promoted|enabled|supported)",
        re.IGNORECASE,
    ),
    "public_sdk_ready": re.compile(
        r"\b(?:player[-_ ]+identity[-_ ]+)?public[-_ ]+sdk(?:[-_ ]+consumer)?\s+(?:is\s+)?"
        r"(?:ready|available|promoted|enabled|complete|supported)",
        re.IGNORECASE,
    ),
    "owner_token_sdk_consumer_ready": re.compile(
        r"\b(?:owner[-_ ]+token[-_ ]+)?(?:sdk[-_ ]+consumer|consumer[-_ ]+contract)"
        r"(?:[-_ ]+readiness)?\s+(?:is\s+)?"
        r"(?:ready|available|accepted|approved|complete|satisfied|resolved|promoted|counts?)",
        re.IGNORECASE,
    ),
    "lifecycle_owner_cleanup_ready": re.compile(
        r"\b(?:lifecycle[-_ ]+owner[-_ ]+cleanup|owner[-_ ]+cleanup|owner[-_ ]+token[-_ ]+lifecycle)"
        r"(?:[-_ ]+readiness)?\s+(?:is\s+)?"
        r"(?:ready|available|accepted|approved|complete|satisfied|resolved|promoted)",
        re.IGNORECASE,
    ),
    "runtime_ready": re.compile(
        r"\bruntime\s+(?:is\s+)?(?:ready|enabled|authorized|available|promoted|supported)",
        re.IGNORECASE,
    ),
    "promotion_ready": re.compile(
        r"\bpromotion\s+(?:is\s+)?(?:ready|authorized|complete|available)",
        re.IGNORECASE,
    ),
    "v1_completion_ready": re.compile(
        r"\bv1(?:[-_ ]+sdk)?[-_ ]+completion\s+(?:is\s+)?(?:ready|complete|available|promoted)",
        re.IGNORECASE,
    ),
    "stable_sdk_ready": re.compile(
        r"\b(?:production[-_ ]+)?stable[-_ ]+(?:sdk|claim|wording)\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|promoted|supported)",
        re.IGNORECASE,
    ),
    "support_tier_ready": re.compile(
        r"\bsupport[-_ ]+tier(?:[-_ ]+activation)?\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|activated|promoted|supported)",
        re.IGNORECASE,
    ),
    "plugin_hub_ready": re.compile(
        r"\b(?:plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:readiness|publication|package|support))?"
        r"\s+(?:is\s+)?(?:allowed|available|ready|enabled|published|promoted|released|supported)",
        re.IGNORECASE,
    ),
    "publication_ready": re.compile(
        r"\b(?:plugin[-_ ]+hub[-_ ]+|package[-_ ]+|public[-_ ]+package[-_ ]+)?"
        r"publication(?:[-_ ]+readiness)?\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|approved|published|promoted|released|supported)",
        re.IGNORECASE,
    ),
    "release_support_available": re.compile(
        r"\b(?:release[-_ ]+support|release[-_ ]+grade[-_ ]+support|production[-_ ]+support)"
        r"\s+(?:is\s+)?(?:allowed|available|ready|enabled|authorized|active|supported)",
        re.IGNORECASE,
    ),
    "public_module_sdk_coverage": re.compile(
        r"\b(?:public[-_ ]+)?module[-_ ]+sdk[-_ ]+(?:coverage|support)\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|active|promoted|supported)",
        re.IGNORECASE,
    ),
    "installed_sdk_completion_claim": re.compile(
        r"\b(?:installed[-_ ]+sdk|installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape|cmake[-_ ]+(?:package|config)|Obelisk::obelisk_sdk)\b"
        r"[^\.;]{0,100}\b(?:complete[-_ ]+sdk|sdk[-_ ]+completion|v1(?:[-_ ]+sdk)?[-_ ]+completion|completion)"
        r"\b[^\.;]{0,80}\b(?:ready|available|complete|promoted|supported|counts?|claim(?:ed)?)\b|"
        r"\b(?:complete[-_ ]+sdk|sdk[-_ ]+completion|v1(?:[-_ ]+sdk)?[-_ ]+completion)\b"
        r"[^\.;]{0,100}\b(?:installed[-_ ]+sdk|package[-_ ]+shape|cmake[-_ ]+(?:package|config)|"
        r"Obelisk::obelisk_sdk)\b[^\.;]{0,80}\b"
        r"(?:ready|available|complete|promoted|supported|counts?|claim(?:ed)?)\b",
        re.IGNORECASE,
    ),
    "complete_sdk_path_ready": re.compile(
        r"\b(?:complete[-_ ]+sdk|sdk[-_ ]+completion)"
        r"(?:[-_ ]+(?:path|route|track|lane|gate|flow))?\b[^\.;]{0,100}\b"
        r"(?:accepted|approved|available|claims?|complete|counts?|enabled|promoted|ready|"
        r"satisf(?:y|ies|ied)|supported|unlocks?)\b|"
        r"\b(?:accepted|approved|available|claims?|complete|counts?|enabled|promoted|ready|"
        r"satisf(?:y|ies|ied)|supported|unlocks?)\b[^\.;]{0,100}\b"
        r"(?:complete[-_ ]+sdk|sdk[-_ ]+completion)"
        r"(?:[-_ ]+(?:path|route|track|lane|gate|flow))?\b",
        re.IGNORECASE,
    ),
    "public_identity_available": re.compile(
        r"\b(?:public[-_ ]+)?(?:player[-_ ]+)?identity(?:[-_ ]+(?:SDK|surface|callback|ABI))?"
        r"\s+(?:is\s+|are\s+)?(?:public|available|ready|enabled|promoted|published|supported)",
        re.IGNORECASE,
    ),
    "public_principal_available": re.compile(
        r"\b(?:public[-_ ]+)?(?:player[-_ ]+)?principal"
        r"(?:[-_ ]+(?:lifecycle|SDK|surface|callback|ABI))?"
        r"\s+(?:is\s+|are\s+)?(?:public|available|ready|enabled|promoted|published|supported)",
        re.IGNORECASE,
    ),
    "commands_replies_available": re.compile(
        r"\b(?:commands?\s*/\s*repl(?:y|ies)|commands?[-_ ]+repl(?:y|ies)|"
        r"command[-_ ]+repl(?:y|ies))\b\s+(?:is\s+|are\s+)?"
        r"(?:public|available|ready|enabled|promoted|published|supported)",
        re.IGNORECASE,
    ),
    "resource_handle_available": re.compile(
        r"\b(?:public[-_ ]+)?(?:ResourceHandle|resource[-_ ]+handle)"
        r"(?:[-_ ]+(?:SDK|API|surface|identity))?\s+(?:is\s+|are\s+)?"
        r"(?:public|available|ready|enabled|promoted|published|supported)",
        re.IGNORECASE,
    ),
    "artifact_side_lane_handle_readiness": re.compile(
        r"\b(?:(?:offline[-_ ]+)?gobjects|weak[-_ ]+helper|package[-_ ]+shape|side[-_ ]+(?:lane|channel)|"
        r"planning[-_ ]+manifest|identity[-_ ]+owner[-_ ]+token|owner[-_ ]+token[-_ ]+identity)\b"
        r"[^\.;]{0,120}\b(?:accepted|approved|claims?|completes?|counts?|enables?|grants?|"
        r"impl(?:y|ies|ied)|promotes?|provides?|proves?|resolves?|routes?|satisf(?:y|ies|ied)|"
        r"supports?|unlocks?|validates?)\b[^\.;]{0,120}\b"
        r"(?:public[-_ ]+handle|ResourceHandle|resource[-_ ]+handle|object[-_ ]+identity|"
        r"lookup|public[-_ ]+sdk|complete[-_ ]+sdk|v1(?:[-_ ]+sdk)?[-_ ]+completion)",
        re.IGNORECASE,
    ),
    "post_unload_validity": re.compile(
        r"\b(?:post[-_ ]+unload[-_ ]+validity|validity[-_ ]+after[-_ ]+(?:plugin[-_ ]+)?unload|"
        r"valid[-_ ]+after[-_ ]+(?:plugin[-_ ]+)?unload)\b",
        re.IGNORECASE,
    ),
    "public_contract_ready": re.compile(
        r"\bpublic[-_ ]+contract\s+(?:is\s+)?(?:allowed|ready|available|promoted|enabled|complete)",
        re.IGNORECASE,
    ),
    "sdk_ready_without_runtime_evidence_or_public_review": re.compile(
        r"\b(?:without|missing|pending|before)\b[^\.;]{0,100}\b"
        r"(?:runtime[-_ ]+(?:lifecycle[-_ ]+)?evidence|approved[-_ ]+runtime[-_ ]+evidence|"
        r"public[-_ ]+(?:contract[-_ ]+)?review|contract[-_ ]+review)\b[^\.;]{0,100}\b"
        r"(?:(?:player[-_ ]+identity|player[-_ ]+principal|identity|principal)[-_ ]+)?"
        r"public[-_ ]+sdk(?:[-_ ]+consumer)?\s+(?:is\s+)?"
        r"(?:ready|available|promoted|enabled|complete|supported)",
        re.IGNORECASE,
    ),
    "package_shape_readiness_claim": re.compile(
        r"(?:\b(?:installed[-_ ]+sdk|obelisk::obelisk_sdk|cmake[-_ ]+(?:package|config)|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|package[-_ ]+shape)\b|"
        r"\bfind[-_ ]+package\s*\(?\s*Obelisk\s+0\.1\.0\b[^\.;\)]*\)?)"
        r"[^\.;]{0,120}\b"
        r"(?:activat(?:e|es|ed|ion)|authori[sz](?:e|es|ed)|claims?|completes?|counts?|"
        r"enables?|grants?|promotes?|proves?|satisf(?:y|ies|ied)|supports?|unlocks?)\b"
        r"[^\.;]{0,120}\b"
        r"(?:public[-_ ]+sdk|runtime[-_ ]+readiness|stable[-_ ]+sdk|complete[-_ ]+sdk|"
        r"v1(?:[-_ ]+sdk)?[-_ ]+completion|support[-_ ]+tier(?:[-_ ]+activation)?|"
        r"plugin[-_ ]+hub)",
        re.IGNORECASE,
    ),
    "descriptor_downstream_or_authority_claim": re.compile(
        r"\b(?:descriptors?|descriptor[-_ ]+apis?|DescribeResourceKind|"
        r"DescribeGameplayPolicyEventKind|ObeliskResourceKindDescriptor|"
        r"ObeliskGameplayPolicyEventDescriptor)\b[^\.;]{0,120}\b"
        r"(?:activat(?:e|es|ed|ion)|authori[sz](?:e|es|ed)|claims?|completes?|enables?|"
        r"grants?|impl(?:y|ies|ied)|promotes?|provides?|proves?|resolves?|routes?|"
        r"satisf(?:y|ies|ied)|supports?|unlocks?)\b[^\.;]{0,120}\b"
        r"(?:identity|permissions?[/_-]?admin|admin|command[-_ ]+repl(?:y|ies)|"
        r"commands?[/_-]?repl(?:y|ies)|command[-_ ]+routing|commands?|repl(?:y|ies)|"
        r"ResourceHandle|resource[-_ ]+handle|lookup|mutation|mutat(?:e|ion)|"
        r"return[-_ ]+override|support[-_ ]+tier(?:[-_ ]+activation)?|activation)",
        re.IGNORECASE,
    ),
    "player_identity_promoted": re.compile(r"\b(?:promotes?|promoted)\s+obelisk\.player_identity\.v1\b", re.IGNORECASE),
    "public_capability_symbol": re.compile(
        r"\bOBELISK_API_CAPABILITY_[A-Z0-9_]*(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET)[A-Z0-9_]*\b"
    ),
    "public_player_header_symbol": re.compile(
        r"\b(?:"
        r"Obelisk[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*|"
        r"Register[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*|"
        r"OBELISK_[A-Z0-9_]*(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET)[A-Z0-9_]*"
        r")\b"
    ),
    "persistent_registration_state": re.compile(
        r"\b(?:persistent|persisted|durable|cross[-_ ]+process|cross[-_ ]+server|"
        r"cluster[-_ ]+shared|global)\b[^\.;]{0,80}\b"
        r"(?:identity[-_ ]+|player[-_ ]+identity[-_ ]+|registration[-_ ]+|callback[-_ ]+|principal[-_ ]+)?"
        r"(?:registr(?:y|ies|ations?)|handles?|ids?)\b",
        re.IGNORECASE,
    ),
    "persisted_registration_handles": re.compile(
        r"\b(?:persisted|persists?|persisting|reused?|shared)\b[^\.;]{0,80}\b"
        r"(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b"
        r"(?:[^\.;]{0,80}\b(?:across|cross[-_ ]+process|processes|servers?|instances?))?",
        re.IGNORECASE,
    ),
    "cross_process_registration_handles": re.compile(
        r"\b(?:registration|principal|callback|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?:cross[-_ ]+process|cross[-_ ]+server|shared\s+across\s+(?:processes|servers?|instances?)|"
        r"shared\s+across\s+ARK\s+server\s+processes|reused?\s+across\s+(?:processes|servers?|instances?)|"
        r"reused?\s+across\s+ARK\s+server\s+processes)\b",
        re.IGNORECASE,
    ),
    "registration_handles_persistent": re.compile(
        r"\b(?:registration|principal|callback|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?<!non-)(?<!non_)(?<!non )(?:persistent|persisted|durable|global)\b",
        re.IGNORECASE,
    ),
    "registration_handles_survive_restart_or_unload": re.compile(
        r"\b(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?:survives?|remain(?:s)?\s+valid|valid\s+after|restart[-_ ]+stable)\b[^\.;]{0,80}\b"
        r"(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart)\b|"
        r"\b(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart)\b[^\.;]{0,80}\b"
        r"(?:preserves?|keeps?|retains?|reuses?)\b[^\.;]{0,80}\b"
        r"(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b",
        re.IGNORECASE,
    ),
    "owner_token_persistent_state": re.compile(
        r"\b(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b[^\.;]{0,100}\b"
        r"(?:persistent|persisted|durable|global|cluster[-_ ]+shared|shared[-_ ]+cluster)\b|"
        r"\b(?:persistent|persisted|durable|global|cluster[-_ ]+shared|shared[-_ ]+cluster)\b"
        r"[^\.;]{0,100}\b(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b|"
        r"\b(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b[^\.;]{0,100}\b"
        r"(?:write|writes|written|store|stores|stored|save|saves|saved)\b[^\.;]{0,80}\b"
        r"(?:config|configuration|shared[-_ ]+storage|storage|database|file)\b",
        re.IGNORECASE,
    ),
    "owner_token_cross_process": re.compile(
        r"\b(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b[^\.;]{0,100}\b"
        r"(?:cross[-_ ]+process|cross[-_ ]+server|cross[-_ ]+instance|cluster[-_ ]+(?:wide|node|shared)|"
        r"shared\s+across|reused?\s+across|stable\s+across)\b[^\.;]{0,80}\b"
        r"(?:processes|servers?|instances?|ARK\s+server\s+processes|cluster\s+nodes)?\b|"
        r"\b(?:cross[-_ ]+process|cross[-_ ]+server|cross[-_ ]+instance|cluster[-_ ]+(?:wide|node|shared)|"
        r"shared\s+across|reused?\s+across|stable\s+across)\b[^\.;]{0,100}\b"
        r"(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b",
        re.IGNORECASE,
    ),
    "owner_token_survives_restart_or_unload": re.compile(
        r"\b(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b[^\.;]{0,100}\b"
        r"(?:survives?|remain(?:s)?\s+valid|valid\s+after|restart[-_ ]+stable|reload[-_ ]+stable|"
        r"reused?\s+after|reused?\s+following)\b[^\.;]{0,80}\b"
        r"(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart|plugin[-_ ]+unload)\b|"
        r"\b(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart|plugin[-_ ]+unload)\b"
        r"[^\.;]{0,80}\b(?:preserves?|keeps?|retains?|reuses?)\b[^\.;]{0,80}\b"
        r"(?:plugin[-_ ]+owner[-_ ]+tokens?|owner[-_ ]+tokens?)\b",
        re.IGNORECASE,
    ),
    "ownerless_unregister": re.compile(
        r"\b(?:ownerless|owner[-_ ]+less)\b[^\.;]{0,80}\bunregister\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b|"
        r"\bunregister\b[^\.;]{0,80}\bwithout\b[^\.;]{0,40}\bowner[-_ ]+token\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b",
        re.IGNORECASE,
    ),
    "bare_unregister_by_id": re.compile(
        r"\b(?:bare[-_ ]+)?unregister[-_ ]+by[-_ ]+(?:id|handle)\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b",
        re.IGNORECASE,
    ),
    "source_artifact_ready_alias": re.compile(
        r"\b(?:public[-_ ]+sdk|public[-_ ]+header|public[-_ ]+abi|callback[-_ ]+abi|"
        r"capability[-_ ]+bits?|runtime|promotion|support[-_ ]+tier|stable[-_ ]+sdk|"
        r"plugin[-_ ]+hub|v1[-_ ]+completion)[-_ ]+"
        r"(?:ready|allowed|available|enabled|promoted|complete|exposed)\b",
        re.IGNORECASE,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--public-abi-preflight-candidate", type=Path, default=DEFAULT_PUBLIC_ABI_PREFLIGHT)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def normalized_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def normalize_contract_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def truthy_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalize_contract_key(value) in POSITIVE_CLAIM_VALUES
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return any(truthy_claim_value(item) for item in value.values())
    return False


PUBLIC_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:public|identity|player_identity|principal|abi|sdk|header|headers|capability|callback|"
    r"lookup|public_handle|resource_handle|owner_token|identity_owner_token|owner_token_identity|"
    r"gobjects|offline_gobjects|weak_helper|side_lane|side_channel|planning_manifest|"
    r"contract_review|review_artifact|runtime_evidence|"
    r"approved_runtime_evidence|runtime_bundle|approved_runtime_bundle|public_header_gate|"
    r"header_promotion_gate|public_header_promotion_gate|cmake|package_shape|installed_sdk|"
    r"installed_sdk_package_shape|obelisk_config_cmake|obelisk_targets_cmake|find_package|"
    r"descriptor)"
    r".*(?:ready|readiness|allowed|available|enabled|promot(?:e|es|ed|ion)|unlock(?:s|ed)?|"
    r"open(?:s|ed)?|pass(?:es|ed)?|accept(?:ed|ance)?|approv(?:ed|al)?|counts?|counting|"
    r"complete|completion|resolv(?:e|es|ed)|satisf(?:y|ies|ied)|claim)",
    re.IGNORECASE,
)
STRUCT_SIZE_OR_LAYOUT_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:struct_?size|pod_?layout|abi_?layout|layout_?abi|fixed_?size|prefix_?compat)"
    r".*(?:ready|readiness|allowed|available|complete|completion|claim|counts?|"
    r"accepted|approved|passed|promot(?:e|es|ed|ion)|resolved?|satisf(?:y|ies|ied)|"
    r"unlock(?:s|ed)?|validat(?:e|es|ed|ion)|verif(?:y|ies|ied))",
    re.IGNORECASE,
)
OWNER_TOKEN_LIFETIME_CLAIM_KEY_RE = re.compile(
    r"(?:plugin_?owner_?tokens?|owner_?tokens?).*"
    r"(?:persist|durable|global|cross_?process|cross_?server|cross_?instance|cluster|"
    r"restart|reload|unload|dlclose|reuse|shar(?:e|ed|ing))|"
    r"(?:persist|durable|global|cross_?process|cross_?server|cross_?instance|cluster|"
    r"restart|reload|unload|dlclose|reuse|shar(?:e|ed|ing)).*"
    r"(?:plugin_?owner_?tokens?|owner_?tokens?)",
    re.IGNORECASE,
)
HANDLE_LIFETIME_CLAIM_KEY_RE = re.compile(
    r"(?:registration|callback|timer|principal)?_?(?:handles?|ids?).*"
    r"(?:persist|durable|global|cross_?process|cross_?server|cross_?instance|cluster|"
    r"restart|reload|unload|dlclose|reuse|shar(?:e|ed|ing)|stable|valid_?after|surviv(?:e|es))|"
    r"(?:persist|durable|global|cross_?process|cross_?server|cross_?instance|cluster|"
    r"restart|reload|unload|dlclose|reuse|shar(?:e|ed|ing)|stable|valid_?after|surviv(?:e|es)).*"
    r"(?:registration|callback|timer|principal)?_?(?:handles?|ids?)",
    re.IGNORECASE,
)
PLUGIN_HUB_OR_SUPPORT_TIER_CLAIM_KEY_RE = re.compile(
    r"(?:plugin_?hub|pluginhub).*"
    r"(?:publish(?:ed|es|ing)?|publication|ready|readiness|available|support(?:ed)?|"
    r"activ(?:e|ated|ation)|release(?:d)?|public|claim|allowed)|"
    r"(?:publish(?:ed|es|ing)?|publication|ready|readiness|available|support(?:ed)?|"
    r"activ(?:e|ated|ation)|release(?:d)?|public|claim|allowed).*"
    r"(?:plugin_?hub|pluginhub)|"
    r"support_?tier.*"
    r"(?:activ(?:e|ated|ation)|ready|readiness|available|support(?:ed)?|public|claim|allowed)|"
    r"(?:activ(?:e|ated|ation)|ready|readiness|available|support(?:ed)?|public|claim|allowed).*"
    r"support_?tier",
    re.IGNORECASE,
)
PUBLICATION_CLAIM_KEY_RE = re.compile(
    r"(?:publication|publish(?:ed|es|ing)?).*"
    r"(?:ready|readiness|allowed|available|enabled|published|public|claim)|"
    r"(?:ready|readiness|allowed|available|enabled|published|public|claim).*"
    r"(?:publication|publish(?:ed|es|ing)?)",
    re.IGNORECASE,
)
RELEASE_SUPPORT_CLAIM_KEY_RE = re.compile(
    r"(?:release_?support|release_?grade_?support|production_?support).*"
    r"(?:ready|readiness|allowed|available|enabled|active|supported|claim)|"
    r"(?:ready|readiness|allowed|available|enabled|active|supported|claim).*"
    r"(?:release_?support|release_?grade_?support|production_?support)",
    re.IGNORECASE,
)
PUBLIC_MODULE_OR_RUNTIME_SUPPORT_CLAIM_KEY_RE = re.compile(
    r"(?:public_?)?module_?sdk_?(?:coverage|support|ready|available|active|activated|public|claim|allowed)|"
    r"(?:public_?)?module_?coverage.*(?:ready|available|active|activated|claim|allowed|support(?:ed)?)|"
    r"runtime_?(?:support|supported|authorized|authorization|available|active|activated)",
    re.IGNORECASE,
)
BLOCKED_PUBLIC_SURFACE_CLAIM_KEY_RE = re.compile(
    r"(?:public_?identity|public_?principal|player_?identity_?public|player_?principal_?public|"
    r"player_?principal_?lifecycle|principal_?lifecycle|identity_?lifecycle|"
    r"commands?_?replies?|command_?repl(?:y|ies)|"
    r"resource_?handle|public_?handle|gobjects|offline_?gobjects|weak_?helper|"
    r"side_?(?:lane|channel)|planning_?manifest|identity_?owner_?token|owner_?token_?identity).*"
    r"(?:ready|readiness|allowed|available|enabled|public|published|promot(?:e|es|ed|ion)|"
    r"support(?:ed)?|claim)|"
    r"(?:ready|readiness|allowed|available|enabled|public|published|promot(?:e|es|ed|ion)|"
    r"support(?:ed)?|claim).*"
    r"(?:public_?identity|public_?principal|player_?identity_?public|player_?principal_?public|"
    r"player_?principal_?lifecycle|principal_?lifecycle|identity_?lifecycle|"
    r"commands?_?replies?|command_?repl(?:y|ies)|"
    r"resource_?handle|public_?handle|gobjects|offline_?gobjects|weak_?helper|"
    r"side_?(?:lane|channel)|planning_?manifest|identity_?owner_?token|owner_?token_?identity)",
    re.IGNORECASE,
)
INSTALLED_SDK_COMPLETION_CLAIM_KEY_RE = re.compile(
    r"(?:installed_?sdk|installed_?sdk_?package_?shape|package_?shape|cmake_?package|"
    r"obelisk_?sdk).*"
    r"(?:complete_?sdk|sdk_?completion|v1_?completion|completion).*"
    r"(?:ready|readiness|allowed|available|complete|claim|counts?|counting|promot(?:e|es|ed|ion)|"
    r"support(?:ed)?)|"
    r"(?:complete_?sdk|sdk_?completion|v1_?completion|completion).*"
    r"(?:installed_?sdk|installed_?sdk_?package_?shape|package_?shape|cmake_?package|"
    r"obelisk_?sdk).*"
    r"(?:ready|readiness|allowed|available|complete|claim|counts?|counting|promot(?:e|es|ed|ion)|"
    r"support(?:ed)?)",
    re.IGNORECASE,
)
POST_UNLOAD_VALIDITY_CLAIM_KEY_RE = re.compile(
    r"(?:post_?unload|after_?unload|valid_?after_?unload|validity_?after_?unload).*"
    r"(?:valid|validity|ready|readiness|allowed|available|enabled|support(?:ed)?|"
    r"handles?|ids?|tokens?)|"
    r"(?:valid|validity|ready|readiness|allowed|available|enabled|support(?:ed)?|"
    r"handles?|ids?|tokens?).*"
    r"(?:post_?unload|after_?unload|valid_?after_?unload|validity_?after_?unload)",
    re.IGNORECASE,
)
ROUTE_ACCEPTED_PUBLIC_ALIAS_KEY_RE = re.compile(
    r"(?:route|post_evidence|post_runtime_evidence|runtime_evidence|approved_runtime_evidence)"
    r".*(?:accept(?:ed|ance)?|counts?|counting|as)"
    r".*(?:public|identity|principal|abi|sdk|header|lookup|owner_token|complete|completion|claim)",
    re.IGNORECASE,
)
COMPLETE_SDK_PATH_CLAIM_KEY_RE = re.compile(
    r"(?:complete_?sdk|sdk_?complete|sdk_?completion|v1_?sdk_?complete|"
    r"complete_?sdk_?(?:path|route|track|lane|gate|flow)|"
    r"sdk_?completion_?(?:path|route|track|lane|gate|flow))"
    r".*(?:accept(?:ed|ance)?|approv(?:ed|al)?|allow(?:ed)?|available|claim(?:ed)?|"
    r"complete|counts?|counting|enable(?:d)?|pass(?:ed)?|promot(?:e|es|ed|ion)|"
    r"ready|readiness|resolv(?:e|es|ed)|satisf(?:y|ies|ied)|support(?:ed)?|unlock(?:s|ed)?)|"
    r"(?:accept(?:ed|ance)?|approv(?:ed|al)?|allow(?:ed)?|available|claim(?:ed)?|"
    r"complete|counts?|counting|enable(?:d)?|pass(?:ed)?|promot(?:e|es|ed|ion)|"
    r"ready|readiness|resolv(?:e|es|ed)|satisf(?:y|ies|ied)|support(?:ed)?|unlock(?:s|ed)?)"
    r".*(?:complete_?sdk|sdk_?complete|sdk_?completion|v1_?sdk_?complete|"
    r"complete_?sdk_?(?:path|route|track|lane|gate|flow)|"
    r"sdk_?completion_?(?:path|route|track|lane|gate|flow))",
    re.IGNORECASE,
)
MISSING_GATE_CONTEXT_KEY_RE = re.compile(
    r"(?:runtime(?:_?lifecycle)?_?evidence|approved_?runtime_?evidence|"
    r"runtime_?proof|runtime_?validation|runtime_?bundle|approved_?runtime_?bundle|"
    r"public_?header_?gate|public_?header_?promotion_?gate|header_?promotion_?gate|"
    r"public_?(?:contract_?)?review|contract_?review|accepted_?for_?contract_?review)",
    re.IGNORECASE,
)
MISSING_GATE_ACCEPTANCE_KEY_RE = re.compile(
    r"(?:accept(?:ed|ance)?|approv(?:ed|al)?|ready|readiness|available|present|provided|"
    r"review(?:ed)?|validat(?:ed|ion)|complete|completion|satisf(?:y|ies|ied)|pass(?:es|ed)?|"
    r"open(?:s|ed)?|counts?|counting|claim(?:ed)?)",
    re.IGNORECASE,
)
MISSING_GATE_TEXT_OVERCLAIM_PATTERNS = {
    "runtime_evidence_satisfied": re.compile(
        r"\b(?:runtime[-_ ]+(?:lifecycle[-_ ]+)?evidence|approved[-_ ]+runtime[-_ ]+evidence)\b"
        r"[^\.;]{0,100}\b(?:accepted|approved|ready|available|present|provided|reviewed|validated|"
        r"complete|satisf(?:ied|ies)|passes?|counts?)\b",
        re.IGNORECASE,
    ),
    "public_review_satisfied": re.compile(
        r"\b(?:public[-_ ]+(?:contract[-_ ]+)?review|contract[-_ ]+review)\b[^\.;]{0,100}\b"
        r"(?:accepted|approved|ready|available|present|provided|reviewed|validated|complete|"
        r"satisf(?:ied|ies)|passes?|counts?)\b",
        re.IGNORECASE,
    ),
    "approved_runtime_bundle_satisfied": re.compile(
        r"\b(?:approved[-_ ]+runtime[-_ ]+bundle|runtime[-_ ]+bundle)\b[^\.;]{0,100}\b"
        r"(?:accepted|approved|ready|available|present|provided|reviewed|validated|complete|"
        r"satisf(?:ied|ies)|passes?|passed|counts?)\b",
        re.IGNORECASE,
    ),
    "public_header_promotion_gate_satisfied": re.compile(
        r"\b(?:public[-_ ]+header[-_ ]+(?:promotion[-_ ]+)?gate|header[-_ ]+promotion[-_ ]+gate)"
        r"\b[^\.;]{0,100}\b(?:accepted|approved|ready|available|open(?:ed)?|passed|passes?|"
        r"reviewed|validated|complete|satisf(?:ied|ies)|counts?)\b",
        re.IGNORECASE,
    ),
}
GUARDED_DOWNSTREAM_SURFACE_ALIASES = {
    "permissions_admin": (
        "permissions_admin",
        "permission_admin",
        "permissions",
        "permission",
        "admin_permission",
        "admin_permissions",
        "authz",
        "authorization",
    ),
    "command_chat_response": (
        "command_chat_response",
        "command_response",
        "chat_command_response",
        "chat_response",
    ),
    "commands_replies": (
        "commands_replies",
        "command_replies",
        "commands",
        "command",
        "replies",
        "reply",
    ),
    "player_lookup": (
        "player_lookup",
        "principal_lookup",
        "identity_lookup",
        "lookup",
        "lookups",
        "resolve_player",
        "player_resolution",
        "principal_resolution",
        "identity_resolution",
    ),
    "storage_persistence": (
        "storage_persistence",
        "persistent_storage",
        "persistence",
        "persist",
        "persisted",
        "storage",
        "database",
        "durable_storage",
    ),
    "mutation": (
        "mutation",
        "mutations",
        "mutate",
        "mutates",
        "mutating",
        "write_api",
        "state_write",
    ),
    "return_override": (
        "return_override",
        "return_overrides",
        "return_value_override",
        "override_return",
        "return override",
        "return value override",
    ),
    "send_chat_identity": (
        "send_chat_identity",
        "send_chat",
        "send chat",
        "chat_reply",
        "chat reply",
        "chat replies",
        "sender_identity",
        "sender identity",
    ),
    "operator_ingress": (
        "operator_ingress",
        "operator ingress",
        "rcon",
        "discord",
        "webhook",
    ),
    "resource_handle_identity": (
        "resource_handle_identity",
        "resource handle identity",
        "resource_handle",
        "resource handle",
        "ResourceHandle",
        "object_identity",
        "object identity",
    ),
}
DOWNSTREAM_SURFACE_ACTIVATION_KEY_RE = re.compile(
    r"(?:ready|readiness|allow(?:ed|s)?|available|enable(?:d|s)?|support(?:ed|s)?|"
    r"consume(?:s|d)?|consumption|use(?:s|d|r)?|route(?:d|s)?|bind(?:s|ing|ed)?|"
    r"authori[sz](?:e|ed|es|ation)|resolve(?:d|s)?|lookup|persist(?:s|ed|ent|ence|ing)?|"
    r"stor(?:e|ed|age)|sav(?:e|ed|es)|durable|database|sdk)",
    re.IGNORECASE,
)
DOWNSTREAM_SURFACE_TEXT_RE = {
    surface: re.compile(
        "|".join(rf"\b{re.escape(alias).replace('_', r'[-_ /]+')}\b" for alias in aliases),
        re.IGNORECASE,
    )
    for surface, aliases in GUARDED_DOWNSTREAM_SURFACE_ALIASES.items()
}
DOWNSTREAM_SURFACE_TEXT_ACTIVATION_RE = re.compile(
    r"\b(?:ready|allowed|available|enabled|supported|consume(?:s|d)?|use(?:s|d)?|"
    r"route(?:s|d)?|bind(?:s|ing|ed)?|authori[sz](?:e|ed|es)|resolve(?:s|d)?|"
    r"persist(?:s|ed|ing)?|stor(?:e|ed)|sav(?:e|ed|es))\b",
    re.IGNORECASE,
)
DOWNSTREAM_PRINCIPAL_TEXT_RE = re.compile(
    r"\b(?:player[-_ ]+identity|identity|principal|opaque[-_ ]+principal|owner[-_ ]+token|"
    r"principal[-_ ]+handle|identity[-_ ]+handle)\b",
    re.IGNORECASE,
)
NON_COUNTING_SDK_CONSUMER_SOURCE_PATTERNS = {
    "cmake_package_material": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|obeliskconfig\.cmake|"
        r"obelisktargets\.cmake|obelisk::obelisk_sdk|obelisk[-_ ]+sdk|"
        r"components?[-_ ]+sdk|find[-_ ]+package(?:\s*\(\s*Obelisk\s+0\.1\.0\b)?)\b",
        re.IGNORECASE,
    ),
    "diagnostic_material": re.compile(r"\bdiagnostic(?:[-_ ]+only)?\b", re.IGNORECASE),
    "installed_sdk_consumer_test_material": re.compile(
        r"\b(?:installed[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+tests?)?|"
        r"sdk[-_ ]+consumer[-_ ]+tests?|tests/sdk_installed_consumer|tests/sdk_consumer)\b",
        re.IGNORECASE,
    ),
    "installed_sdk_package_shape_material": re.compile(
        r"\b(?:installed[-_ ]+sdk(?:[-_ ]+package[-_ ]+shape)?|"
        r"sdk[-_ ]+package[-_ ]+shape|package[-_ ]+shape)\b",
        re.IGNORECASE,
    ),
    "offline_gobjects_material": re.compile(r"\b(?:offline[-_ ]+)?gobjects\b", re.IGNORECASE),
    "weak_helper_material": re.compile(r"\bweak[-_ ]+helper\b", re.IGNORECASE),
    "side_lane_material": re.compile(r"\bside[-_ ]+(?:lane|channel)\b", re.IGNORECASE),
    "planning_manifest_material": re.compile(r"\bplanning[-_ ]+manifest\b", re.IGNORECASE),
    "passive_material": re.compile(r"\bpassive(?:[-_ ]+(?:monitor|snapshot|material|artifact|evidence))?\b", re.IGNORECASE),
    "plugin_hub_material": re.compile(
        r"\b(?:plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:wording|seed|package|support|publication))?\b",
        re.IGNORECASE,
    ),
    "public_header_material": re.compile(
        r"\b(?:public[-_ ]+headers?|installed[-_ ]+headers?|"
        r"obelisk[-_ ]*api(?:\.h|[-_ ]+h)?|include/obelisk/obeliskapi\.h)\b",
        re.IGNORECASE,
    ),
    "review_only_material": re.compile(
        r"\b(?:review[-_ ]+only|contract[-_ ]+review[-_ ]+only|review[-_ ]+artifact)\b",
        re.IGNORECASE,
    ),
    "runtime_evidence_only_material": re.compile(
        r"\b(?:runtime[-_ ]+(?:lifecycle[-_ ]+)?evidence(?:[-_ ]+only)?|"
        r"approved[-_ ]+runtime[-_ ]+evidence(?:[-_ ]+only)?|runtime[-_ ]+only)\b",
        re.IGNORECASE,
    ),
    "approved_runtime_bundle_only_material": re.compile(
        r"\b(?:approved[-_ ]+runtime[-_ ]+bundle(?:[-_ ]+only)?|"
        r"runtime[-_ ]+bundle(?:[-_ ]+only)?)\b",
        re.IGNORECASE,
    ),
    "simulation_mock_fixture_material": re.compile(
        r"\b(?:simulation|simulated|synthetic|mock|fixture)\b",
        re.IGNORECASE,
    ),
    "partial_copied_runtime_material": re.compile(
        r"\b(?:copied[-_ ]+runtime(?:[-_ ]+evidence|[-_ ]+observer[-_ ]+log)?|"
        r"runtime[-_ ]+(?:observer[-_ ]+log|lifecycle[-_ ]+evidence|evidence))\b"
        r"[^\.;]{0,80}\b(?:partial|truncated|incomplete)\b|"
        r"\b(?:partial|truncated|incomplete)\b[^\.;]{0,80}\b"
        r"(?:copied[-_ ]+runtime|runtime[-_ ]+(?:observer[-_ ]+log|lifecycle[-_ ]+evidence|evidence))\b",
        re.IGNORECASE,
    ),
}
SDK_CONSUMER_READINESS_KEY_RE = re.compile(
    r"(?:sdk_?consumer|owner_?token_?sdk_?consumer|consumer_?contract|"
    r"lifecycle_?owner_?cleanup|owner_?cleanup|owner_?token_?lifecycle|"
    r"player_?identity_?owner_?token|player_?principal_?owner_?token|"
    r"player_?principal_?lifecycle|principal_?owner_?token|"
    r"cmake_?package|obelisk_?config_?cmake|obelisk_?targets_?cmake|"
    r"find_?package(?:_?obelisk(?:_?0_?1_?0)?)?|installed_?sdk_?package_?shape|"
    r"package_?shape|gobjects|offline_?gobjects|weak_?helper|side_?(?:lane|channel)|"
    r"planning_?manifest|public_?handle|identity_?owner_?token|owner_?token_?identity)"
    r".*(?:ready|readiness|available|accepted|approved|complete|completion|"
    r"resolve|resolved|satisfy|satisfied|claim|counts?|counting)",
    re.IGNORECASE,
)
SDK_CONSUMER_READINESS_TEXT_RE = re.compile(
    r"\b(?:owner[-_ ]+token[-_ ]+)?(?:sdk[-_ ]+consumer|consumer[-_ ]+contract)"
    r"(?:[-_ ]+readiness)?\b[^\.;]{0,100}\b"
    r"(?:ready|available|accepted|approved|complete|satisf(?:y|ies|ied)|resolved?|counts?|counting|claim(?:ed)?)\b|"
    r"\b(?:ready|available|accepted|approved|complete|satisf(?:y|ies|ied)|resolved?|counts?|counting|claim(?:ed)?)"
    r"\b[^\.;]{0,100}\b(?:owner[-_ ]+token[-_ ]+)?(?:sdk[-_ ]+consumer|consumer[-_ ]+contract)"
    r"(?:[-_ ]+readiness)?\b|"
    r"\b(?:lifecycle[-_ ]+owner[-_ ]+cleanup|owner[-_ ]+cleanup|owner[-_ ]+token[-_ ]+lifecycle)"
    r"(?:[-_ ]+readiness)?\b[^\.;]{0,100}\b"
    r"(?:ready|available|accepted|approved|complete|satisf(?:y|ies|ied)|resolved?|counts?|counting|claim(?:ed)?)\b|"
    r"\b(?:runtime[-_ ]+readiness|public[-_ ]+sdk|public[-_ ]+abi|public[-_ ]+header|"
    r"support[-_ ]+tier|stable[-_ ]+sdk|v1(?:[-_ ]+sdk)?[-_ ]+completion|complete[-_ ]+sdk|"
    r"plugin[-_ ]+hub(?:[-_ ]+(?:readiness|publication|support))?)\b[^\.;]{0,100}\b"
    r"(?:ready|allowed|available|accepted|approved|complete|enabled|promoted|published|released|"
    r"proves?|validates?|unlock(?:s|ed)?|satisf(?:y|ies|ied)|supported|counts?|counting|claim(?:ed)?)\b|"
    r"\b(?:ready|allowed|available|accepted|approved|complete|enabled|promoted|published|released|"
    r"proves?|validates?|unlock(?:s|ed)?|satisf(?:y|ies|ied)|supported|counts?|counting|claim(?:ed)?)\b[^\.;]{0,100}\b"
    r"(?:runtime[-_ ]+readiness|public[-_ ]+sdk|public[-_ ]+abi|public[-_ ]+header|"
    r"support[-_ ]+tier|stable[-_ ]+sdk|v1(?:[-_ ]+sdk)?[-_ ]+completion|complete[-_ ]+sdk|"
    r"plugin[-_ ]+hub(?:[-_ ]+(?:readiness|publication|support))?)\b",
    re.IGNORECASE,
)
PUBLIC_HEADER_CONTRACT_TOKEN_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net|"
    r"owner_?token[A-Za-z0-9_]*(?:identity|principal|player)|"
    r"player_?(?:handle|data|id|session|lifecycle|login|logout|connect|disconnect|join|leave|"
    r"event|callback|identity|principal)|"
    r"register_?[A-Za-z0-9_]*(?:player|identity|principal|steam|eos|unique_?net)|"
    r"obelisk_api_capability_[A-Za-z0-9_]*(?:player|identity|principal|steam|eos|unique_?net)|"
    r"resource_?handle|"
    r"[A-Za-z0-9_]*(?:lookup|resolve)[A-Za-z0-9_]*",
    re.IGNORECASE,
)
PUBLIC_HEADER_CONTRACT_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
}
PUBLIC_HEADER_OWNER_TOKEN_REGISTRATION_RE = re.compile(
    r"\bRegister[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)"
    r"[A-Za-z0-9_]*(?:WithOwnerToken|OwnerToken)[A-Za-z0-9_]*(?:Handle)?\b"
)
PUBLIC_HEADER_BORROWED_RUNTIME_POINTER_RE = re.compile(
    r"\b(?:UObject|UFunction|FString|FName|UClass|UStruct|AActor|APawn|AController|"
    r"APlayerController|AShooterPlayerController|APrimalCharacter|UPrimalInventoryComponent)"
    r"\s*\*|"
    r"\b(?:const\s+)?void\s*\*\s*(?:caller|function|parms|params|raw[A-Za-z0-9_]*|"
    r"runtime[A-Za-z0-9_]*|player|controller|pawn|character|inventory|object|uobject)\b|"
    r"\b(?:ProcessEvent|RawParams|raw_?params|parms)\b|"
    r"\b(?:uintptr_t|intptr_t|uint64_t|int64_t)\s+"
    r"(?:uobject|object_?ptr|object_?address|object_?addr|player_?ptr|player_?address|"
    r"player_?addr|controller_?ptr|controller_?address|pawn_?ptr|character_?ptr|"
    r"raw_?pointer|pointer|address|addr)\b",
    re.IGNORECASE,
)
PUBLIC_HEADER_IDENTITY_STRUCT_START_RE = re.compile(
    r"\b(?:typedef\s+)?struct\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)?"
)
PUBLIC_HEADER_STRUCT_END_RE = re.compile(r"}\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)?\s*;")


def is_forbidden_structured_claim_key(key: object) -> bool:
    compact_key = normalized_key(str(key))
    if compact_key in FORBIDDEN_STRUCTURED_CLAIM_KEYS:
        return True
    normalized = normalize_contract_key(key)
    return bool(
        PUBLIC_READINESS_ALIAS_KEY_RE.search(normalized)
        or ROUTE_ACCEPTED_PUBLIC_ALIAS_KEY_RE.search(normalized)
        or STRUCT_SIZE_OR_LAYOUT_READINESS_ALIAS_KEY_RE.search(normalized)
        or OWNER_TOKEN_LIFETIME_CLAIM_KEY_RE.search(normalized)
        or HANDLE_LIFETIME_CLAIM_KEY_RE.search(normalized)
        or PLUGIN_HUB_OR_SUPPORT_TIER_CLAIM_KEY_RE.search(normalized)
        or PUBLICATION_CLAIM_KEY_RE.search(normalized)
        or RELEASE_SUPPORT_CLAIM_KEY_RE.search(normalized)
        or PUBLIC_MODULE_OR_RUNTIME_SUPPORT_CLAIM_KEY_RE.search(normalized)
        or BLOCKED_PUBLIC_SURFACE_CLAIM_KEY_RE.search(normalized)
        or INSTALLED_SDK_COMPLETION_CLAIM_KEY_RE.search(normalized)
        or POST_UNLOAD_VALIDITY_CLAIM_KEY_RE.search(normalized)
        or COMPLETE_SDK_PATH_CLAIM_KEY_RE.search(normalized)
    )


def collect_structured_overclaims(value: Any, path: str = "$") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if is_forbidden_structured_claim_key(key) and truthy_claim_value(item):
                claims.append({"path": item_path, "key": key, "value": item})
            claims.extend(collect_structured_overclaims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_structured_overclaims(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        claims.extend(collect_text_overclaims(value, path))
    return claims


def has_negative_context(value: str, match_start: int) -> bool:
    normalized = value.replace("_", " ")
    clause_start = max(normalized.rfind(";", 0, match_start), normalized.rfind(".", 0, match_start))
    clause_end_candidates = [
        index
        for index in (
            normalized.find(";", match_start),
            normalized.find(".", match_start),
        )
        if index != -1
    ]
    clause_end = min(clause_end_candidates) if clause_end_candidates else len(normalized)
    prefix = normalized[clause_start + 1 : match_start]
    suffix = normalized[match_start:clause_end]
    if re.search(r"(?:^|\b)non[-_ ]*$", prefix, re.IGNORECASE):
        return True
    if NEGATIVE_CONTEXT_RE.search(prefix):
        return True
    return bool(
        re.search(
            r"\b(?:forbidden|unavailable|blocked|redacted|cannot|can't|false)\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def collect_text_overclaims(value: str, path: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
        for match in pattern.finditer(value):
            if has_negative_context(value, match.start()):
                continue
            claims.append({"path": path, "term": term, "value": value})
            break
    return claims


def collect_public_source_key_overclaims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if not is_forbidden_structured_claim_key(key):
                claims.extend(collect_text_overclaims(str(key), item_path))
            claims.extend(collect_public_source_key_overclaims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_public_source_key_overclaims(item, f"{path}[{index}]"))
    return claims


def is_public_header_contract_token(token: str) -> bool:
    return token not in PUBLIC_HEADER_CONTRACT_ALLOWLIST and bool(PUBLIC_HEADER_CONTRACT_TOKEN_RE.search(token))


def scan_public_header_contract(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        text = public_abi_preflight.strip_c_comments_and_strings(
            without_native_prototype_symbols(path.read_text(encoding="utf-8"), header_only=True)
        )
    except OSError as exc:
        add(blockers, "public_header_contract_unreadable", "--public-header", path=str(path), error=str(exc))
        return {
            "path": str(path),
            "readable": False,
            "detected_identity_owner_token_symbols": [],
            "owner_token_registration_symbols": [],
            "borrowed_runtime_pointer_exposures": [],
        }

    detected: list[dict[str, Any]] = []
    owner_token_registrations: list[dict[str, Any]] = []
    borrowed_runtime_pointers: list[dict[str, Any]] = []
    seen_tokens: set[str] = set()
    active_identity_struct: str | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line)
        contract_tokens = [token for token in tokens if is_public_header_contract_token(token)]
        for token in contract_tokens:
            if token not in seen_tokens:
                seen_tokens.add(token)
                detected.append({"token": token, "line": line_number})

        for token in tokens:
            if PUBLIC_HEADER_OWNER_TOKEN_REGISTRATION_RE.fullmatch(token):
                owner_token_registrations.append({"token": token, "line": line_number})

        struct_start = PUBLIC_HEADER_IDENTITY_STRUCT_START_RE.search(line)
        if struct_start and contract_tokens:
            active_identity_struct = struct_start.group("name") or contract_tokens[0]

        block_context = active_identity_struct or (contract_tokens[0] if contract_tokens else None)
        if block_context and PUBLIC_HEADER_BORROWED_RUNTIME_POINTER_RE.search(line):
            borrowed_runtime_pointers.append(
                {
                    "line": line_number,
                    "context": block_context,
                    "source": line.strip(),
                }
            )

        struct_end = PUBLIC_HEADER_STRUCT_END_RE.search(line)
        if struct_end:
            end_name = struct_end.group("name")
            if end_name and is_public_header_contract_token(end_name) and active_identity_struct is None:
                active_identity_struct = end_name
            if active_identity_struct:
                active_identity_struct = None

    if detected:
        add(
            blockers,
            "public_header_identity_owner_token_symbols_detected",
            "--public-header",
            detected=detected,
        )
    if owner_token_registrations:
        add(
            blockers,
            "public_header_identity_owner_token_registration_symbols_detected",
            "--public-header",
            detected=owner_token_registrations,
        )
    if borrowed_runtime_pointers:
        add(
            blockers,
            "public_header_borrowed_runtime_pointer_exposure_detected",
            "--public-header",
            exposures=borrowed_runtime_pointers,
        )

    return {
        "path": str(path),
        "readable": True,
        "detected_identity_owner_token_symbols": detected,
        "owner_token_registration_symbols": owner_token_registrations,
        "borrowed_runtime_pointer_exposures": borrowed_runtime_pointers,
    }


def gate_contexts_for_key(key: object) -> set[str]:
    normalized = normalize_contract_key(key)
    if not MISSING_GATE_CONTEXT_KEY_RE.search(normalized):
        return set()
    contexts: set[str] = set()
    if "runtime_bundle" in normalized or "approved_runtime_bundle" in normalized:
        contexts.add("approved_runtime_bundle")
    elif "runtime" in normalized:
        contexts.add("runtime_evidence")
    if "header_gate" in normalized or "header_promotion_gate" in normalized:
        contexts.add("public_header_promotion_gate")
    if "review" in normalized or "accepted_for_contract_review" in normalized:
        contexts.add("public_review")
    return contexts


def is_gate_acceptance_key(key: object) -> bool:
    return bool(MISSING_GATE_ACCEPTANCE_KEY_RE.search(normalize_contract_key(key)))


def collect_missing_gate_overclaims(
    value: Any,
    path: str = "$",
    gate_contexts: set[str] | None = None,
) -> list[dict[str, Any]]:
    active_contexts = set(gate_contexts or set())
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            item_contexts = active_contexts | gate_contexts_for_key(key)
            if item_contexts and truthy_claim_value(item) and (
                is_gate_acceptance_key(key) or not isinstance(item, (dict, list))
            ):
                claims.append(
                    {
                        "path": item_path,
                        "key": key,
                        "contexts": sorted(item_contexts),
                        "value": item,
                    }
                )
            claims.extend(collect_missing_gate_overclaims(item, item_path, item_contexts))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_missing_gate_overclaims(item, f"{path}[{index}]", active_contexts))
    elif isinstance(value, str):
        for term, pattern in MISSING_GATE_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                claims.append({"path": path, "term": term, "value": value})
                break
    return claims


def downstream_surfaces_for_key(key: object) -> set[str]:
    normalized = normalize_contract_key(key)
    compact = normalized_key(str(key))
    surfaces: set[str] = set()
    for surface, aliases in GUARDED_DOWNSTREAM_SURFACE_ALIASES.items():
        for alias in aliases:
            alias_normalized = normalize_contract_key(alias)
            alias_compact = normalized_key(alias)
            if (
                normalized == alias_normalized
                or compact == alias_compact
                or alias_normalized in normalized
                or alias_compact in compact
            ):
                surfaces.add(surface)
                break
    return surfaces


def is_downstream_surface_activation_key(key: object) -> bool:
    return bool(DOWNSTREAM_SURFACE_ACTIVATION_KEY_RE.search(normalize_contract_key(key)))


def collect_downstream_surface_activation_claims(
    value: Any,
    path: str = "$",
    surface_contexts: set[str] | None = None,
) -> list[dict[str, Any]]:
    if ".must_remain_blocked" in path:
        return []
    active_surfaces = set(surface_contexts or set())
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            item_surfaces = active_surfaces | downstream_surfaces_for_key(key)
            if (
                item_surfaces
                and is_downstream_surface_activation_key(key)
                and truthy_claim_value(item)
            ):
                claims.append(
                    {
                        "path": item_path,
                        "key": key,
                        "surfaces": sorted(item_surfaces),
                        "value": item,
                    }
                )
            claims.extend(collect_downstream_surface_activation_claims(item, item_path, item_surfaces))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_downstream_surface_activation_claims(item, f"{path}[{index}]", active_surfaces))
    elif isinstance(value, str):
        matching_surfaces = [
            surface
            for surface, pattern in DOWNSTREAM_SURFACE_TEXT_RE.items()
            if pattern.search(value)
        ]
        if matching_surfaces and (
            DOWNSTREAM_PRINCIPAL_TEXT_RE.search(value)
            or {"permissions_admin", "player_lookup", "storage_persistence"} & set(matching_surfaces)
            or {
                "mutation",
                "return_override",
                "send_chat_identity",
                "operator_ingress",
                "resource_handle_identity",
            }
            & set(matching_surfaces)
        ):
            for match in DOWNSTREAM_SURFACE_TEXT_ACTIVATION_RE.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                claims.append(
                    {
                        "path": path,
                        "term": "downstream_surface_activation",
                        "surfaces": sorted(matching_surfaces),
                        "value": value,
                    }
                )
                break
    return claims


def non_counting_sdk_consumer_source_kinds(value: object) -> set[str]:
    raw = str(value).replace("_", " ")
    normalized = normalize_contract_key(value).replace("_", " ")
    text = f"{raw} {normalized}"
    return {
        kind
        for kind, pattern in NON_COUNTING_SDK_CONSUMER_SOURCE_PATTERNS.items()
        if pattern.search(text)
    }


def is_sdk_consumer_readiness_key(key: object) -> bool:
    normalized = normalize_contract_key(key)
    compact = normalized_key(str(key))
    return bool(SDK_CONSUMER_READINESS_KEY_RE.search(normalized)) or compact in {
        "sdkconsumerready",
        "sdkconsumerreadiness",
        "ownertokensdkconsumerready",
        "ownertokenlifecycleready",
        "lifecycleownercleanupready",
        "lifecycleownercleanupreadiness",
        "publicsdkready",
        "publicabiready",
        "publicheaderready",
        "runtimeready",
        "supporttierready",
        "supporttieractivationallowed",
        "stablesdkready",
        "stablesdkclaimallowed",
        "v1completionready",
        "pluginhubready",
        "pluginhubpublicationready",
    }


def collect_non_counting_sdk_consumer_source_claims(
    value: Any,
    path: str = "$",
    source_contexts: set[str] | None = None,
) -> list[dict[str, Any]]:
    active_sources = set(source_contexts or set())
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            item_sources = active_sources | non_counting_sdk_consumer_source_kinds(key)
            if item_sources and is_sdk_consumer_readiness_key(key) and truthy_claim_value(item):
                claims.append(
                    {
                        "path": item_path,
                        "key": key,
                        "sources": sorted(item_sources),
                        "value": item,
                    }
                )
            claims.extend(collect_non_counting_sdk_consumer_source_claims(item, item_path, item_sources))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(
                collect_non_counting_sdk_consumer_source_claims(item, f"{path}[{index}]", active_sources)
            )
    elif isinstance(value, str):
        value_sources = active_sources | non_counting_sdk_consumer_source_kinds(value)
        if value_sources:
            for match in SDK_CONSUMER_READINESS_TEXT_RE.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                claims.append(
                    {
                        "path": path,
                        "term": "non_counting_sdk_consumer_readiness_source",
                        "sources": sorted(value_sources),
                        "value": value,
                    }
                )
                break
    return claims


def string_set(payload: dict[str, Any], key: str) -> set[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def require_strings(
    payload: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
) -> None:
    missing = sorted(required - string_set(payload, key))
    if missing:
        add(blockers, f"{key}_missing_required", f"$.{key}", missing=missing)


def require_semantic_strings(
    payload: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    label: str,
) -> None:
    missing = sorted(required - string_set(payload, key))
    if missing:
        add(blockers, reason, label, missing=missing)


def contains_non_counting_artifact_token(*values: Any) -> bool:
    text = " ".join(str(value).lower() for value in values)
    return any(token in text for token in NON_COUNTING_ARTIFACT_TOKENS)


def validate_accepted_inputs(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    accepted_inputs = payload.get("accepted_inputs")
    if not isinstance(accepted_inputs, dict):
        add(blockers, "accepted_inputs_missing", "$.accepted_inputs")
        return
    if accepted_inputs.get(PUBLIC_ABI_PREFLIGHT_INPUT) is not True:
        add(blockers, "public_abi_preflight_input_not_true", f"$.accepted_inputs.{PUBLIC_ABI_PREFLIGHT_INPUT}")
    unexpected_inputs = sorted(str(key) for key in set(accepted_inputs) - REQUIRED_ACCEPTED_INPUTS)
    if unexpected_inputs:
        add(
            blockers,
            "accepted_inputs_unexpected_non_counting_inputs",
            "$.accepted_inputs",
            unexpected=unexpected_inputs,
        )
    non_counting_inputs = sorted(
        str(key)
        for key, value in accepted_inputs.items()
        if contains_non_counting_artifact_token(key, value)
    )
    if non_counting_inputs:
        add(
            blockers,
            "accepted_inputs_non_counting_artifacts_claimed",
            "$.accepted_inputs",
            artifacts=non_counting_inputs,
        )


def validate_source_artifacts(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    sources = payload.get("source_artifacts")
    if not isinstance(sources, dict):
        add(blockers, "source_artifacts_missing", "$.source_artifacts")
        return
    unexpected_sources = sorted(str(key) for key in set(sources) - set(REQUIRED_SOURCE_ARTIFACTS))
    if unexpected_sources:
        add(
            blockers,
            "source_artifacts_unexpected_non_counting_artifacts",
            "$.source_artifacts",
            unexpected=unexpected_sources,
        )
    for key, expected in REQUIRED_SOURCE_ARTIFACTS.items():
        if sources.get(key) != expected:
            add(blockers, f"source_{key}_mismatch", f"$.source_artifacts.{key}", value=sources.get(key))
    non_counting_sources = sorted(
        str(key)
        for key, value in sources.items()
        if contains_non_counting_artifact_token(key, value)
    )
    if non_counting_sources:
        add(
            blockers,
            "source_artifacts_non_counting_artifacts_claimed",
            "$.source_artifacts",
            artifacts=non_counting_sources,
        )


def section(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        add(blockers, f"{key}_missing", f"$.{key}")
        return {}
    return value


def validate_preflight(
    path: Path,
    public_header: Path,
    blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        preflight_payload = public_abi_preflight.load_json(path)
        private_payload = public_abi_preflight.private_layout.load_json(public_abi_preflight.DEFAULT_PRIVATE_LAYOUT)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(blockers, "public_abi_preflight_candidate_unreadable", "--public-abi-preflight-candidate", error=str(exc))
        return {}, {"accepted_for_candidate_review": False, "blockers": ["public_abi_preflight_candidate_unreadable"]}

    preflight_blockers: list[dict[str, Any]] = []
    header_scan = public_abi_preflight.scan_public_header(public_header, preflight_blockers)
    public_abi_preflight.validate_manifest(preflight_payload, private_payload, preflight_blockers)
    if preflight_blockers:
        add(
            blockers,
            "public_abi_preflight_candidate_not_accepted",
            "--public-abi-preflight-candidate",
            input_blockers=[blocker["reason"] for blocker in preflight_blockers],
        )
    return preflight_payload, {
        "accepted_for_candidate_review": not preflight_blockers,
        "blockers": [blocker["reason"] for blocker in preflight_blockers],
        "blocker_details": preflight_blockers,
        "public_header_scan": header_scan,
    }


def field_names(summary: dict[str, Any]) -> list[str]:
    fields = summary.get("fields")
    if not isinstance(fields, list):
        return []
    return [item for item in fields if isinstance(item, str)]


def validate_layout_summary(
    payload: dict[str, Any],
    preflight_payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    abi_layout = section(payload, "abi_layout", blockers)
    if not abi_layout:
        return
    if abi_layout.get("status") != "required_before_promotion":
        add(blockers, "abi_layout_status_mismatch", "$.abi_layout.status", value=abi_layout.get("status"))
    if abi_layout.get("public_symbols_allowed") is not False:
        add(
            blockers,
            "abi_layout_public_symbols_allowed_not_false",
            "$.abi_layout.public_symbols_allowed",
            value=abi_layout.get("public_symbols_allowed"),
        )
    require_strings(abi_layout, "required_checks", REQUIRED_ABI_LAYOUT_CHECKS, blockers)

    event = abi_layout.get("event_payload_summary")
    descriptor = abi_layout.get("descriptor_summary")
    if not isinstance(event, dict):
        add(blockers, "abi_layout_event_payload_summary_missing", "$.abi_layout.event_payload_summary")
        event = {}
    if not isinstance(descriptor, dict):
        add(blockers, "abi_layout_descriptor_summary_missing", "$.abi_layout.descriptor_summary")
        descriptor = {}
    copied_principal_missing = sorted(REQUIRED_COPIED_PRINCIPAL_FIELDS - set(field_names(event)))
    if copied_principal_missing:
        add(
            blockers,
            "copied_principal_payload_fields_missing_required",
            "$.abi_layout.event_payload_summary.fields",
            missing=copied_principal_missing,
        )
    expected_event = preflight_payload.get("event_payload") if isinstance(preflight_payload, dict) else {}
    expected_descriptor = preflight_payload.get("descriptor") if isinstance(preflight_payload, dict) else {}
    if (
        event.get("struct_size") != expected_event.get("struct_size")
        or event.get("alignment") != expected_event.get("alignment")
        or field_names(event) != field_names(expected_event)
    ):
        add(blockers, "abi_layout_event_payload_preflight_drift", "$.abi_layout.event_payload_summary")
    if (
        descriptor.get("struct_size") != expected_descriptor.get("struct_size")
        or descriptor.get("alignment") != expected_descriptor.get("alignment")
        or field_names(descriptor) != field_names(expected_descriptor)
    ):
        add(blockers, "abi_layout_descriptor_preflight_drift", "$.abi_layout.descriptor_summary")


def validate_manifest(payload: dict[str, Any], preflight_payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", value=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", value=payload.get("surface"))
    for key, expected in (
        ("artifact_status", "candidate_only"),
        ("visibility", "planning_contract"),
        ("status", "blocked"),
    ):
        if payload.get(key) != expected:
            add(blockers, f"{key}_mismatch", f"$.{key}", value=payload.get(key))
    for key in ("candidate_only", "accepted_for_candidate_review"):
        if payload.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.{key}", value=payload.get(key))
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
        "public_sdk_v1_completion_claim",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", value=payload.get(key))
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", value=payload.get(key))

    validate_accepted_inputs(payload, blockers)
    validate_source_artifacts(payload, blockers)

    require_strings(payload, "required_before_promotion", REQUIRED_BEFORE_PROMOTION, blockers)
    require_strings(payload, "does_not_resolve", REQUIRED_DOES_NOT_RESOLVE, blockers)
    require_strings(payload, "non_claims", REQUIRED_NON_CLAIMS, blockers)
    validate_layout_summary(payload, preflight_payload, blockers)

    sdk = section(payload, "sdk_consumer", blockers)
    if sdk:
        if sdk.get("status") != "required_before_promotion":
            add(blockers, "sdk_consumer_status_mismatch", "$.sdk_consumer.status", value=sdk.get("status"))
        if sdk.get("public_sdk_ready") is not False:
            add(blockers, "sdk_consumer_public_sdk_ready_not_false", "$.sdk_consumer.public_sdk_ready")
        require_strings(sdk, "required_checks", REQUIRED_SDK_CONSUMER_CHECKS, blockers)
        require_semantic_strings(
            sdk,
            "required_checks",
            REQUIRED_OWNER_TOKEN_SDK_SEMANTICS,
            blockers,
            reason="owner_token_sdk_consumer_semantics_missing_required",
            label="$.sdk_consumer.required_checks",
        )
        require_semantic_strings(
            sdk,
            "required_checks",
            REQUIRED_COPIED_PRINCIPAL_SDK_SEMANTICS,
            blockers,
            reason="copied_principal_sdk_consumer_semantics_missing_required",
            label="$.sdk_consumer.required_checks",
        )

    cleanup = section(payload, "lifecycle_owner_cleanup", blockers)
    if cleanup:
        if cleanup.get("status") != "required_before_promotion":
            add(
                blockers,
                "lifecycle_owner_cleanup_status_mismatch",
                "$.lifecycle_owner_cleanup.status",
                value=cleanup.get("status"),
            )
        if cleanup.get("registration_model") != "owner_token_handle":
            add(
                blockers,
                "lifecycle_owner_cleanup_registration_model_mismatch",
                "$.lifecycle_owner_cleanup.registration_model",
                value=cleanup.get("registration_model"),
            )
        require_strings(cleanup, "required_checks", REQUIRED_OWNER_CLEANUP_CHECKS, blockers)
        require_semantic_strings(
            cleanup,
            "required_checks",
            REQUIRED_OWNER_TOKEN_LIFECYCLE_SEMANTICS,
            blockers,
            reason="owner_token_lifecycle_semantics_missing_required",
            label="$.lifecycle_owner_cleanup.required_checks",
        )

    downstream = section(payload, "downstream_separation", blockers)
    if downstream:
        if downstream.get("status") != "blocked_until_player_identity_promoted":
            add(
                blockers,
                "downstream_separation_status_mismatch",
                "$.downstream_separation.status",
                value=downstream.get("status"),
            )
        if downstream.get("consumption_allowed_now") is not False:
            add(
                blockers,
                "downstream_separation_consumption_allowed_now_not_false",
                "$.downstream_separation.consumption_allowed_now",
                value=downstream.get("consumption_allowed_now"),
            )
        require_strings(downstream, "must_remain_blocked", REQUIRED_BLOCKED_DOWNSTREAM, blockers)
        require_strings(downstream, "required_checks", REQUIRED_DOWNSTREAM_CHECKS, blockers)

    nested_claims = collect_structured_overclaims(payload)
    nested_claims.extend(collect_public_source_key_overclaims(payload))
    if nested_claims:
        add(
            blockers,
            "nested_public_runtime_or_completion_claims",
            "$",
            claims=nested_claims,
        )

    missing_gate_claims = collect_missing_gate_overclaims(payload)
    if missing_gate_claims:
        add(
            blockers,
            "missing_runtime_evidence_or_public_review_claims",
            "$",
            claims=missing_gate_claims,
        )

    non_counting_sdk_source_claims = collect_non_counting_sdk_consumer_source_claims(payload)
    if non_counting_sdk_source_claims:
        add(
            blockers,
            "non_counting_sdk_consumer_readiness_source_claims",
            "$",
            claims=non_counting_sdk_source_claims,
        )

    downstream_surface_claims = collect_downstream_surface_activation_claims(payload)
    if downstream_surface_claims:
        add(
            blockers,
            "blocked_downstream_surface_activation_claims",
            "$",
            claims=downstream_surface_claims,
        )


def build_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    preflight_report: dict[str, Any],
    public_header_contract_scan: dict[str, Any],
) -> dict[str, Any]:
    check_passed = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "check_passed": check_passed,
        "contract_check_passed": check_passed,
        "package_shape_evidence_only": True,
        "ready": False,
        "ready_scope": "checker_pass_only_non_promotional_package_shape_evidence",
        "valid": check_passed,
        "status": payload.get("status"),
        "candidate_only": payload.get("candidate_only") is True,
        "accepted_for_candidate_review": payload.get("accepted_for_candidate_review") is True and check_passed,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_claim": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "required_before_promotion": payload.get("required_before_promotion", []),
        "does_not_resolve": payload.get("does_not_resolve", []),
        "abi_layout": payload.get("abi_layout", {}),
        "sdk_consumer": payload.get("sdk_consumer", {}),
        "lifecycle_owner_cleanup": payload.get("lifecycle_owner_cleanup", {}),
        "downstream_separation": payload.get("downstream_separation", {}),
        "public_abi_preflight_candidate": preflight_report,
        "public_header_contract_scan": public_header_contract_scan,
        "public_or_runtime_claims": [
            claim
            for detail in blockers
            if detail.get("reason") == "nested_public_runtime_or_completion_claims"
            for claim in detail.get("claims", [])
        ],
        "runtime_or_public_review_claims": [
            claim
            for detail in blockers
            if detail.get("reason") == "missing_runtime_evidence_or_public_review_claims"
            for claim in detail.get("claims", [])
        ],
        "non_counting_sdk_consumer_source_claims": [
            claim
            for detail in blockers
            if detail.get("reason") == "non_counting_sdk_consumer_readiness_source_claims"
            for claim in detail.get("claims", [])
        ],
        "blocked_downstream_surface_claims": [
            claim
            for detail in blockers
            if detail.get("reason") == "blocked_downstream_surface_activation_claims"
            for claim in detail.get("claims", [])
        ],
        "public_header_borrowed_runtime_pointer_exposures": [
            exposure
            for detail in blockers
            if detail.get("reason") == "public_header_borrowed_runtime_pointer_exposure_detected"
            for exposure in detail.get("exposures", [])
        ],
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": payload.get("non_claims", []),
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    try:
        payload = load_json(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"--manifest invalid: {exc}") from exc
    preflight_payload, preflight_report = validate_preflight(args.public_abi_preflight_candidate, args.public_header, blockers)
    public_header_contract_scan = scan_public_header_contract(args.public_header, blockers)
    validate_manifest(payload, preflight_payload, blockers)
    report = build_report(
        payload,
        blockers,
        preflight_report=preflight_report,
        public_header_contract_scan=public_header_contract_scan,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "player identity owner-token SDK consumer contract: "
            + ("ok" if report["check_passed"] else "blocked")
        )
    return 0 if report["check_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
