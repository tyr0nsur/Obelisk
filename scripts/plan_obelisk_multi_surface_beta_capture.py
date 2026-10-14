#!/usr/bin/env python3
"""Plan an offline multi-surface beta capture window.

This helper does not touch ARK servers, logs, Discord, markers, or files outside stdout.
It gives the lead a candidate-only checklist so one beta session can exercise every
safe gated Obelisk surface that is already represented by local checkers.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


SCHEMA = "obelisk.multi-surface-beta-capture-plan.v1"
EXACT_CAPTURE_OBJECTIVES_SCHEMA = "obelisk.multi-surface-beta-capture-exact-objectives.v1"
STRICT_PLAYER_PRINCIPAL_TRIPLET = "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout"
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE = "approved_runtime_principal_lifecycle_evidence_bundle"
CANDIDATE_ARTIFACT_ROOT = "candidate-artifacts"
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
SAFE_MAP_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
COMMON_REDACTION_NOTE = "do not retain raw player text, secrets, webhook URLs, or private player data"
ARTIFACT_TEMPLATE_ROOT = CANDIDATE_ARTIFACT_ROOT + "/"
TARGET_BINDING_SOURCE = "operator_cli_plan_target"
APPROVED_RUNTIME_WINDOW_SCOPE = "separately_approved_player_principal_lifecycle_window"
APPROVED_RUNTIME_WINDOW_ID_TEMPLATE = "<approved-player-principal-lifecycle-window-id>"
BROAD_BETA_CAPTURE_PACK_PATH_ID = "admin_commands_dino_tribe_buff_candidate_path"
BROAD_BETA_CAPTURE_WORKSHEET_ID = "admin_commands_dino_tribe_buff_candidate_worksheet"
BROAD_BETA_CAPTURE_WORKSHEET_FILE = "admin-commands-dino-tribe-buff-candidate-worksheet.json"
BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA = (
    "obelisk.multi-surface-beta-capture-broad-candidate-worksheet.v1"
)
SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID = (
    "admin_commands_dino_tribe_buff_inventory_transfer_mission_candidate_worksheet"
)
SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE = "simultaneous-side-lane-candidate-worksheet.json"
SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA = (
    "obelisk.multi-surface-beta-capture-simultaneous-candidate-worksheet.v1"
)
BROAD_BETA_CAPTURE_SURFACE_IDS = (
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "dino_scalar",
    "tribe_scalar",
    "buff_status",
)
BROAD_BETA_CAPTURE_ACTION_GROUP_IDS = (
    "admin_and_command_routes",
    "world_state_scalar_candidates",
)
PARALLEL_BETA_CAPTURE_MATRIX_ID = (
    "admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates"
)
PARALLEL_BETA_CAPTURE_SURFACE_IDS = (
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "dino_scalar",
    "tribe_scalar",
    "buff_status",
    "inventory_item_copied_signals",
    "inventory_custom_filter_array_boundary",
    "inventory_action_compact_intake",
    "item_return_only",
    "transfer_baccept",
    "transfer_scriptstruct",
    "mission_copied_bool",
)
PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS = (
    "admin_and_command_routes",
    "world_state_scalar_candidates",
    "inventory_item_candidates",
    "transfer_candidates",
    "mission_candidates",
)
SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS = PARALLEL_BETA_CAPTURE_SURFACE_IDS
SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS = PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS
SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID = "single_player_parallel_side_lane_capture_sequence"
SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID = (
    "single_player_player_principal_and_side_lane_candidate_worksheet"
)
SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE = (
    "single-player-full-sequence-candidate-worksheet.json"
)
SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA = (
    "obelisk.multi-surface-beta-capture-single-player-sequence-worksheet.v1"
)
SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS = (
    "primary_player_principal_gate",
    *PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS,
)
SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS = (
    "player_principal_lifecycle",
    *PARALLEL_BETA_CAPTURE_SURFACE_IDS,
)
SINGLE_PLAYER_PARALLEL_CAPTURE_DOMAIN_IDS = (
    "player_principal",
    "admin",
    "commands",
    "dino",
    "tribe",
    "buff",
    "inventory",
    "item",
    "transfer",
    "mission",
)
SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS: tuple[str, ...] = ()
SINGLE_PLAYER_PHASE_DOMAIN_IDS_BY_ACTION_GROUP = {
    "primary_player_principal_gate": ("player_principal",),
    "admin_and_command_routes": ("admin", "commands"),
    "world_state_scalar_candidates": ("dino", "tribe", "buff"),
    "inventory_item_candidates": ("inventory", "item"),
    "transfer_candidates": ("transfer",),
    "mission_candidates": ("mission",),
}
TARGET_BOUND_CHECKER_COMMAND_MATRIX_ID = "target_bound_offline_checker_command_matrix"
TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS = "offline_command_templates_candidate_only"
SIDE_LANE_CAPTURE_QUEUE_ID = "player_principal_bound_side_lane_capture_queue"
SIDE_LANE_CAPTURE_QUEUE_STATUS = "queued_candidate_observations_non_counting"
PATH_ARGUMENT_ARTIFACT_KINDS = {"directory", "json"}
SCALAR_ARGUMENT_ARTIFACT_KINDS = {"sha256", "text"}
PARALLEL_BETA_CAPTURE_DOMAINS = (
    ("admin", ("permissions_admin",)),
    ("commands", ("command_chat_response", "commands_replies")),
    ("dino", ("dino_scalar",)),
    ("tribe", ("tribe_scalar",)),
    ("buff", ("buff_status",)),
    (
        "inventory",
        (
            "inventory_item_copied_signals",
            "inventory_custom_filter_array_boundary",
            "inventory_action_compact_intake",
        ),
    ),
    ("item", ("item_return_only",)),
    ("transfer", ("transfer_baccept", "transfer_scriptstruct")),
    ("mission", ("mission_copied_bool",)),
)
BROAD_BETA_CAPTURE_NON_CLAIM = (
    "admin/commands/dino/tribe/buff beta capture path is status-only candidate "
    "planning; it does not authorize runtime capture, replace the required "
    "player-principal triplet, clear approved runtime evidence, contribute SDK/P0 "
    "progress, or imply public/stable readiness"
)
PARALLEL_BETA_CAPTURE_NON_CLAIM = (
    "admin/commands/dino/tribe/buff/inventory/item/transfer/mission beta capture matrix is "
    "status-only candidate planning; it can only coordinate copied offline artifacts "
    "inside a separately approved player-principal lifecycle window and never replaces "
    "the required player-principal triplet, clears approved runtime evidence, "
    "contributes SDK/P0 progress, or implies public/stable readiness"
)
SINGLE_PLAYER_ROUTE_SUMMARY = (
    "one tester may run the primary player-principal lifecycle phase and then optional "
    "admin/commands/dino/tribe/buff/inventory/item/transfer/mission side-lane candidate phases "
    "inside the same separately approved window"
)
SINGLE_PLAYER_ROUTE_NON_CLAIM = (
    "single-player parallel beta capture sequence is a no-restart, no-Discord, "
    "redacted-metadata route for candidate-only offline planning; it does not authorize "
    "runtime capture, live log reads, marker/env changes, Discord sends, SDK/P0 "
    "progress, readiness, or approved runtime evidence, and cannot clear "
    "approved_runtime_evidence_missing"
)
NO_RESTART_ACTION_BOUNDARY = (
    "beta tester actions do not require or authorize starts, stops, restarts, marker "
    "changes, env changes, live log reads, or Discord sends"
)
NO_RAW_PLAYER_TEXT_BOUNDARY = (
    "retain only redacted metadata; raw player text, secrets, webhook URLs, and "
    "private player data are prohibited"
)
LIFECYCLE_CORRELATION_SCHEMA = (
    "obelisk.multi-surface-beta-capture-lifecycle-correlation-metadata.v1"
)
SOURCE_METADATA_SCHEMA = "obelisk.multi-surface-beta-capture-source-metadata.v1"
SOURCE_METADATA_STATUS = "blank_template_for_redacted_copied_offline_source_metadata"
BETA_CAPTURE_INTERACTION_BOUNDARY_SCHEMA = (
    "obelisk.multi-surface-beta-capture-interaction-boundary.v1"
)
SOURCE_METADATA_FIELD_IDS = (
    "source_kind",
    "copied_offline_artifact_path",
    "source_sha256",
    "redaction_review_id",
    "approved_window_id",
    "target_binding_id",
    "side_lane_correlation_id",
    "operator_sequence_index",
)
SOURCE_METADATA_INSTRUCTIONS = (
    "Fill source metadata only after copying redacted material into the offline workspace.",
    "Do not point source metadata at live server paths, Discord, RCON, or webhook URLs.",
    "Keep source metadata to provenance fields only; no raw player text, secrets, or private player data.",
    "Source metadata is required for checker intake but never counts as runtime evidence, SDK progress, P0 progress, or readiness.",
)
LIFECYCLE_CORRELATION_STATUS = "blank_template_for_redacted_metadata_only"
LIFECYCLE_CORRELATION_FIELD_IDS = (
    "approved_window_id",
    "side_lane_correlation_id",
    "primary_lifecycle_phase_anchor",
    "primary_lifecycle_event_reference",
    "relative_lifecycle_offset_seconds",
    "operator_sequence_index",
)
LIFECYCLE_PHASE_ANCHOR_VALUES = (
    "before_handle_new_player",
    "handle_new_player_to_checkjoin",
    "checkjoin_to_onlogout",
    "after_matched_onlogout",
    "not_recorded",
)
PRIMARY_LIFECYCLE_EVENT_REFERENCE_VALUES = (
    "HandleNewPlayer(1,1)",
    "CheckJoinInProgress(1,0)",
    "matched OnLogout",
    "not_recorded",
)
LIFECYCLE_CORRELATION_INSTRUCTIONS = (
    "Use one redacted side_lane_correlation_id for all side-lane rows that belong to the same beta tester/window.",
    "Record the primary_lifecycle_phase_anchor relative to the strict player-principal lifecycle triplet.",
    "Keep primary_lifecycle_event_reference to the event label only; do not copy raw log lines or player identity.",
    "Use relative_lifecycle_offset_seconds only as a small integer offset or omit it when unknown.",
    "These fields are correlation metadata only and never count as runtime evidence, SDK progress, P0 progress, or readiness.",
)
NO_FLOOD_CAPTURE_POLICY_ID = "single_window_no_flood_candidate_capture_policy"
NO_FLOOD_CAPTURE_POLICY_STATUS = "no_flood_candidate_only_non_evidence"
NO_FLOOD_DEDUPE_KEY_FIELDS = (
    "approved_window_id",
    "target_binding_id",
    "surface_id",
    "side_lane_correlation_id",
)

NON_CLAIM_FLAGS: dict[str, bool] = {
    "candidate_only": True,
    "candidate_only_non_evidence": True,
    "non_evidence": True,
    "touches_live_servers": False,
    "authorizes_beta_session": False,
    "authorizes_evidence_window": False,
    "authorizes_live_log_reads": False,
    "authorizes_live_operations": False,
    "authorizes_live_server_access": False,
    "authorizes_runtime_capture": False,
    "authorizes_runtime_observer": False,
    "authorizes_server_restart": False,
    "authorizes_server_start": False,
    "authorizes_server_stop": False,
    "authorizes_marker_or_env_changes": False,
    "authorizes_player_backed_window": False,
    "authorizes_discord_send": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_progress": False,
    "counts_as_p0_progress": False,
    "clears_approved_runtime_evidence_missing": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "stable_sdk_ready": False,
    "v1_completion_ready": False,
    "plugin_hub_ready": False,
    "publication_ready": False,
    "readiness_claim_allowed": False,
    "downstream_unlock_allowed": False,
    "passive_capture_counts_as_evidence": False,
    "stale_artifact_counts_as_evidence": False,
    "stale_or_passive_alias_substitution_allowed": False,
    "replaces_player_principal_evidence": False,
    "replaces_player_principal_triplet": False,
    "substitutes_for_player_principal_lifecycle_evidence": False,
    "substitutes_for_player_principal_lifecycle_triplet": False,
    "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
    "player_principal_lifecycle_evidence_substitution_allowed": False,
    "approved_runtime_evidence_substitution_allowed": False,
    "primary_evidence_substitution_allowed": False,
    "side_lane_counts_toward_sdk": False,
    "side_lane_counts_toward_p0": False,
    "pack_authorizes_player_backed_window": False,
    "pack_authorizes_runtime_observer": False,
    "pack_authorizes_marker_or_env_change": False,
    "pack_authorizes_restart": False,
    "pack_authorizes_discord": False,
    "side_lane_collection_can_replace_player_principal_evidence": False,
    "side_lane_collection_counts_before_checker_acceptance": False,
    "source_present": False,
    "source_material_present": False,
    "source_material_counts_as_evidence": False,
    "flood_capture_allowed": False,
    "unbounded_tester_requests_allowed": False,
    "discord_request_fanout_allowed": False,
}

BETA_CAPTURE_INTERACTION_BOUNDARY_FLAGS: dict[str, bool] = {
    "beta_notices_count_as_approved_runtime_evidence": False,
    "beta_notices_count_as_runtime_evidence": False,
    "beta_notices_count_as_sdk_progress": False,
    "beta_notices_count_as_p0_progress": False,
    "button_clicks_count_as_approved_runtime_evidence": False,
    "button_clicks_count_as_runtime_evidence": False,
    "button_clicks_count_as_sdk_progress": False,
    "button_clicks_count_as_p0_progress": False,
    "public_reachability_counts_as_runtime_evidence": False,
    "public_reachability_counts_as_sdk_progress": False,
    "multi_surface_plan_counts_as_approved_runtime_evidence": False,
    "multi_surface_plan_counts_as_sdk_progress": False,
    "discord_or_beta_interactions_grant_public_sdk_readiness": False,
    "discord_or_beta_interactions_grant_stable_readiness": False,
    "discord_or_beta_interactions_authorize_live_actions": False,
    "discord_or_beta_interactions_approve_live_actions": False,
    "discord_or_beta_interactions_authorize_discord_send": False,
    "discord_or_beta_interactions_clear_runtime_evidence_blockers": False,
}

ARTIFACT_INTAKE_CONSTRAINTS: dict[str, bool] = {
    "path_template_only": True,
    "path_template_must_be_relative": True,
    "path_template_must_start_with_candidate_artifacts": True,
    "path_template_must_not_contain_parent_traversal": True,
    "path_template_must_not_name_live_server_paths": True,
    "source_material_must_be_copied_to_offline_workspace": True,
    "source_material_must_not_be_read_from_live_server_path_by_pack": True,
    "redaction_required_before_checker_intake": True,
    "raw_player_text_private_data_secrets_and_webhooks_prohibited": True,
    "target_binding_must_match_pack_target": True,
    "candidate_artifact_presence_never_implies_checker_acceptance": True,
    "candidate_artifact_intake_cannot_replace_primary_runtime_evidence": True,
    "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence": True,
    "lifecycle_correlation_metadata_required_for_side_lanes": True,
    "lifecycle_correlation_metadata_is_non_evidence": True,
}

PARALLEL_CAPTURE_BOUNDARY: dict[str, bool] = {
    "parallel_with_player_principal_lifecycle_window_planned": True,
    "side_surfaces_grouped_as_optional_parallel_candidate_observations": True,
    "side_surfaces_non_evidence_until_own_checker_acceptance": True,
    "separate_player_backed_window_approval_required": True,
    "candidate_surface_claims_require_checker_acceptance": True,
    "target_binding_required_for_all_artifacts": True,
    "pack_authorizes_player_backed_window": False,
    "pack_authorizes_runtime_observer": False,
    "pack_authorizes_marker_or_env_change": False,
    "pack_authorizes_restart": False,
    "pack_authorizes_discord": False,
    "side_lane_collection_can_replace_player_principal_evidence": False,
    "side_lane_collection_counts_before_checker_acceptance": False,
}

PLAYER_PRINCIPAL_WINDOW_COMPOSITION: dict[str, Any] = {
    "composes_with_window": "player_principal_lifecycle",
    "primary_surface_id": "player_principal_lifecycle",
    "primary_strict_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
    "side_surface_role": "optional_parallel_candidate_observations",
    "side_surfaces_optional": True,
    "side_surfaces_parallel_candidate_only": True,
    "side_surfaces_non_evidence_until_own_checker_acceptance": True,
    "side_surfaces_require_own_checker_acceptance": True,
    "all_artifacts_require_exact_target_binding": True,
    "primary_player_principal_evidence_remains_required": True,
    "counts_as_sdk_progress": False,
    "counts_as_p0_progress": False,
    "substitution_allowed": False,
}

NON_SUBSTITUTION_FLAGS: dict[str, bool] = {
    "replaces_player_principal_evidence": False,
    "replaces_player_principal_triplet": False,
    "substitutes_for_player_principal_lifecycle_evidence": False,
    "substitutes_for_player_principal_lifecycle_triplet": False,
    "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
    "player_principal_lifecycle_evidence_substitution_allowed": False,
    "approved_runtime_evidence_substitution_allowed": False,
    "primary_evidence_substitution_allowed": False,
    "side_lane_collection_can_replace_player_principal_evidence": False,
    "side_lane_collection_counts_before_checker_acceptance": False,
}

REDACTION_POLICY: dict[str, Any] = {
    "required": True,
    "must_redact": [
        "raw_player_text",
        "secrets",
        "webhook_urls",
        "private_player_data",
    ],
    "retain_only_redacted_offline_copies": True,
    "checker_inputs_must_be_redacted": True,
}

COMMON_BETA_CAPTURE_WORKSHEET_FIELDS: tuple[dict[str, Any], ...] = (
    {
        "field_id": "approved_window_id",
        "required": True,
        "value_template": APPROVED_RUNTIME_WINDOW_ID_TEMPLATE,
        "retention_rule": "approved window id only; no raw log lines",
    },
    {
        "field_id": "side_lane_correlation_id",
        "required": True,
        "value_template": "<redacted-side-lane-correlation-id>",
        "retention_rule": (
            "opaque beta-session id only; no player name, platform id, chat text, IP, "
            "secret, or webhook"
        ),
    },
    {
        "field_id": "primary_lifecycle_phase_anchor",
        "required": True,
        "allowed_values": list(LIFECYCLE_PHASE_ANCHOR_VALUES),
        "retention_rule": "phase label only; no raw lifecycle log line",
    },
    {
        "field_id": "primary_lifecycle_event_reference",
        "required": True,
        "allowed_values": list(PRIMARY_LIFECYCLE_EVENT_REFERENCE_VALUES),
        "retention_rule": "event label only; no player identity or raw log text",
    },
    {
        "field_id": "relative_lifecycle_offset_seconds",
        "required": False,
        "value_template": "<integer-seconds-or-omitted>",
        "retention_rule": "integer offset only; no absolute live log excerpt",
    },
    {
        "field_id": "operator_sequence_index",
        "required": True,
        "value_template": "<1-based-observation-order-within-window>",
        "retention_rule": "small integer order only",
    },
    {
        "field_id": "observed_at_utc",
        "required": True,
        "value_template": "<YYYY-MM-DDTHH:MM:SSZ>",
        "retention_rule": "timestamp only",
    },
    {
        "field_id": "candidate_artifact_path",
        "required": True,
        "value_source": "surface capture_artifacts path_template",
        "retention_rule": "relative candidate-artifacts path only",
    },
    {
        "field_id": "redaction_summary",
        "required": True,
        "value_template": "<redacted-metadata-summary>",
        "retention_rule": "summarize metadata shape; omit raw player text and private data",
    },
)

BETA_CAPTURE_WORKSHEET_FIELDS_BY_SURFACE: dict[str, tuple[dict[str, Any], ...]] = {
    "player_principal_lifecycle": (
        {
            "field_id": "player_principal_join_cycle_step",
            "required": True,
            "allowed_values": [
                "join_attempt",
                "same_target_entry_or_transfer_attempt",
                "clean_logout",
                "not_recorded",
            ],
            "retention_rule": "cycle step label only; no player identity or raw log line",
        },
        {
            "field_id": "session_start_observer_role",
            "required": True,
            "allowed_values": ["session_start", "session_start_created", "not_observed"],
            "retention_rule": "observer role/status label only",
        },
        {
            "field_id": "checkjoin_rejected_start_shape",
            "required": True,
            "allowed_values": ["CheckJoinInProgress(1,0)", "not_observed"],
            "retention_rule": "exact function/parameter shape label only",
        },
        {
            "field_id": "session_end_correlation_shape",
            "required": True,
            "allowed_values": [
                "matched OnLogout",
                "session_end_invalidated_matched",
                "not_observed",
            ],
            "retention_rule": "correlation label only; no raw logout line",
        },
        {
            "field_id": "presence_without_lifecycle_start_after_observer_gate",
            "required": False,
            "allowed_values": ["true", "false", "not_recorded"],
            "retention_rule": (
                "diagnostic boolean label only; it is not approved runtime evidence"
            ),
        },
        {
            "field_id": "approved_evidence_manifest_path",
            "required": True,
            "value_template": (
                "candidate-artifacts/player_principal_lifecycle/"
                "approved-runtime-principal-lifecycle-evidence-manifest.json"
            ),
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "permissions_admin": (
        {
            "field_id": "admin_command_family",
            "required": True,
            "allowed_values": ["admin", "list_player", "kick_path"],
            "retention_rule": "route label only",
        },
        {
            "field_id": "invocation_channel",
            "required": False,
            "allowed_values": ["server_console", "in_game_admin", "copied_offline_note"],
            "retention_rule": "channel label only",
        },
        {
            "field_id": "redacted_response_shape",
            "required": True,
            "allowed_values": [
                "no_response",
                "single_line_shape",
                "multi_line_shape",
                "denied_shape",
                "error_shape",
            ],
            "retention_rule": "shape label only; no response body",
        },
        {
            "field_id": "target_actor_reference",
            "required": False,
            "value_template": "<redacted-or-omitted>",
            "retention_rule": "do not retain private player data",
        },
    ),
    "command_chat_response": (
        {
            "field_id": "command_family",
            "required": True,
            "allowed_values": [
                "non_private_beta_command",
                "help_or_status_command",
                "negative_path_command",
            ],
            "retention_rule": "command family only; no raw command text",
        },
        {
            "field_id": "response_channel",
            "required": True,
            "allowed_values": ["chat_response", "server_notice", "no_response"],
            "retention_rule": "channel label only",
        },
        {
            "field_id": "response_shape",
            "required": True,
            "allowed_values": ["none", "one_message", "multi_message", "denied", "error"],
            "retention_rule": "shape label only; no response text",
        },
        {
            "field_id": "correlation_marker",
            "required": False,
            "value_template": "<opaque-test-marker-no-player-text>",
            "retention_rule": "opaque marker only",
        },
    ),
    "commands_replies": (
        {
            "field_id": "reply_route_family",
            "required": True,
            "allowed_values": ["direct_reply", "broadcast_reply", "no_reply", "denied_reply"],
            "retention_rule": "route label only",
        },
        {
            "field_id": "reply_delivery_shape",
            "required": True,
            "allowed_values": ["none", "single_delivery", "multi_delivery", "error_delivery"],
            "retention_rule": "delivery shape only; no reply payload",
        },
        {
            "field_id": "command_response_path_report_path",
            "required": True,
            "value_template": (
                "candidate-artifacts/commands_replies/"
                "offline-command-response-path-report.json"
            ),
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "dino_scalar": (
        {
            "field_id": "dino_context_shape",
            "required": True,
            "allowed_values": ["nearby_tame", "nearby_wild", "mounted", "no_dino_context"],
            "retention_rule": "context label only",
        },
        {
            "field_id": "scalar_names_observed",
            "required": True,
            "value_template": ["<redacted-scalar-name-or-category>"],
            "retention_rule": "field names or categories only; no object identity",
        },
        {
            "field_id": "scalar_value_shape",
            "required": True,
            "allowed_values": ["boolean", "integer", "float", "enum_label", "presence_only"],
            "retention_rule": "value shape only unless checker fixture explicitly allows value",
        },
    ),
    "tribe_scalar": (
        {
            "field_id": "tribe_context_shape",
            "required": True,
            "allowed_values": ["own_tribe_view", "ally_view", "neutral_view", "no_tribe_context"],
            "retention_rule": "context label only; no private identity",
        },
        {
            "field_id": "boundary_fields_observed",
            "required": True,
            "value_template": ["<redacted-boundary-field-or-category>"],
            "retention_rule": "field names or categories only",
        },
        {
            "field_id": "visibility_result_shape",
            "required": True,
            "allowed_values": ["visible", "hidden", "partial", "not_observed"],
            "retention_rule": "visibility shape only",
        },
    ),
    "buff_status": (
        {
            "field_id": "buff_context_shape",
            "required": True,
            "allowed_values": ["natural_buff", "applied_safe_buff", "removed_safe_buff", "no_buff"],
            "retention_rule": "context label only",
        },
        {
            "field_id": "status_transition_shape",
            "required": True,
            "allowed_values": ["present", "absent", "applied", "removed", "changed"],
            "retention_rule": "transition shape only",
        },
        {
            "field_id": "status_fields_observed",
            "required": True,
            "value_template": ["<redacted-status-field-or-category>"],
            "retention_rule": "field names or categories only",
        },
    ),
    "inventory_item_copied_signals": (
        {
            "field_id": "inventory_context_shape",
            "required": True,
            "allowed_values": [
                "open_inventory",
                "move_harmless_item",
                "remote_inventory_view",
                "not_observed",
            ],
            "retention_rule": "context label only; no item identity or player identity",
        },
        {
            "field_id": "copied_signal_shape",
            "required": True,
            "allowed_values": ["presence_only", "boolean", "integer", "category_label", "not_observed"],
            "retention_rule": "shape/category only unless an offline checker fixture explicitly permits the value",
        },
        {
            "field_id": "inventory_artifact_family",
            "required": True,
            "allowed_values": ["copied_signal_notes"],
            "retention_rule": "artifact family label only",
        },
    ),
    "inventory_custom_filter_array_boundary": (
        {
            "field_id": "filter_context_shape",
            "required": True,
            "allowed_values": [
                "inventory_filter_view",
                "remote_filter_view",
                "filter_metadata_only",
                "not_observed",
            ],
            "retention_rule": "context label only; no raw array payload",
        },
        {
            "field_id": "array_boundary_shape",
            "required": True,
            "allowed_values": ["array_property_seen", "byte_boundary_seen", "metadata_only", "not_observed"],
            "retention_rule": "boundary shape only; no object identity",
        },
        {
            "field_id": "array_metadata_path",
            "required": True,
            "value_template": (
                "candidate-artifacts/inventory_custom_filter_array_boundary/"
                "offline-inventory-custom-filter-array-boundary-snapshot.json"
            ),
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "inventory_action_compact_intake": (
        {
            "field_id": "inventory_action_family",
            "required": True,
            "allowed_values": [
                "inventory_use_check",
                "allow_equip_item_check",
                "can_repair_check",
                "use_item_onto_item_check",
                "not_recorded",
            ],
            "retention_rule": "action family label only; no raw params",
        },
        {
            "field_id": "dispatch_budget",
            "required": True,
            "value_template": "0",
            "retention_rule": "dispatch budget scalar only; must stay zero",
        },
        {
            "field_id": "observer_metadata_shape",
            "required": True,
            "allowed_values": ["redacted_compact_intake", "fname_index_only", "budget_scalar_only"],
            "retention_rule": "metadata shape only; no raw player text or private data",
        },
    ),
    "item_return_only": (
        {
            "field_id": "item_check_family",
            "required": True,
            "allowed_values": [
                "remote_add_check",
                "inventory_use_check",
                "equip_or_repair_check",
                "not_observed",
            ],
            "retention_rule": "check family label only",
        },
        {
            "field_id": "return_policy_shape",
            "required": True,
            "allowed_values": ["allow_shape", "deny_shape", "return_only_shape", "not_observed"],
            "retention_rule": "return policy shape only; no item identity",
        },
        {
            "field_id": "policy_slice_path",
            "required": True,
            "value_template": "candidate-artifacts/item_return_only/offline-item-return-only-policy-slice.json",
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "transfer_baccept": (
        {
            "field_id": "transfer_context_shape",
            "required": True,
            "allowed_values": [
                "same_target_entry",
                "cluster_transfer_prompt",
                "transfer_confirmation",
                "not_observed",
            ],
            "retention_rule": "context label only; no destination private data",
        },
        {
            "field_id": "baccept_shape",
            "required": True,
            "allowed_values": ["true_shape", "false_shape", "presence_only", "not_observed"],
            "retention_rule": "boolean shape only unless checker fixture explicitly allows value",
        },
        {
            "field_id": "transfer_policy_slice_path",
            "required": True,
            "value_template": "candidate-artifacts/transfer_baccept/offline-transfer-baccept-policy-slice.json",
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "transfer_scriptstruct": (
        {
            "field_id": "transfer_struct_context",
            "required": True,
            "allowed_values": ["cluster_transfer", "same_target_entry", "snapshot_metadata_only", "not_observed"],
            "retention_rule": "context label only",
        },
        {
            "field_id": "scriptstruct_field_categories",
            "required": True,
            "value_template": ["<redacted-scriptstruct-field-category>"],
            "retention_rule": "field categories only; no raw payload",
        },
        {
            "field_id": "scriptstruct_snapshot_root",
            "required": True,
            "value_template": "candidate-artifacts/transfer_scriptstruct/offline-scriptstruct-snapshot-root",
            "retention_rule": "relative candidate-artifacts path only",
        },
    ),
    "mission_copied_bool": (
        {
            "field_id": "mission_context_shape",
            "required": True,
            "allowed_values": [
                "mission_join_attempt",
                "mission_leave_attempt",
                "mission_removed_event",
                "usable_items_query_seen",
                "not_observed",
            ],
            "retention_rule": "mission context label only; no player/controller/character refs",
        },
        {
            "field_id": "mission_bool_family",
            "required": True,
            "allowed_values": [
                "AddPlayerToMission",
                "BPAllowPlayerToLeaveMission",
                "BPOnPlayerRemovedFromMission",
                "GetPlayerUsableItems_recognition_only",
            ],
            "retention_rule": "function family label only; GetPlayerUsableItems remains recognition-only",
        },
        {
            "field_id": "mission_bool_value_shape",
            "required": True,
            "allowed_values": ["boolean", "presence_only", "not_observed"],
            "retention_rule": "value shape only unless checker fixture explicitly allows value",
        },
        {
            "field_id": "mission_redaction_boundary",
            "required": True,
            "value_template": "no-player-controller-character-refs-or-item-id-arrays",
            "retention_rule": "redaction boundary label only",
        },
    ),
}


def target_binding_id(target: dict[str, str]) -> str:
    return f"instance={target['instance']}|map={target['map']}"


def target_binding(target: dict[str, str], *, source: str = TARGET_BINDING_SOURCE) -> dict[str, Any]:
    return {
        "source": source,
        "binding_id": target_binding_id(target),
        "instance": target["instance"],
        "map": target["map"],
        "all_artifacts_must_match": True,
        "mismatched_target_rejects_pack": True,
    }


def approved_runtime_window_binding(
    target: dict[str, str],
    *,
    source: str = TARGET_BINDING_SOURCE,
) -> dict[str, Any]:
    binding = target_binding(target, source=source)
    return {
        "window_scope": APPROVED_RUNTIME_WINDOW_SCOPE,
        "window_id_template": APPROVED_RUNTIME_WINDOW_ID_TEMPLATE,
        "target_binding": binding,
        "target_binding_id": binding["binding_id"],
        "instance": target["instance"],
        "map": target["map"],
        "same_window_as_player_principal_lifecycle": True,
        "side_surfaces_must_share_primary_window": True,
        "candidate_artifacts_must_match_window": True,
        "separate_operator_approval_required": True,
        "pack_authorizes_window": False,
        "window_substitution_allowed": False,
        "side_lane_window_substitution_allowed": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
    }


def lifecycle_correlation_field_ids() -> list[str]:
    return list(LIFECYCLE_CORRELATION_FIELD_IDS)


def lifecycle_correlation_metadata(target: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": LIFECYCLE_CORRELATION_SCHEMA,
        "status": LIFECYCLE_CORRELATION_STATUS,
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "same_approved_runtime_window_required": True,
        "exact_target_binding_required": True,
        "primary_surface_id": "player_principal_lifecycle",
        "required_primary_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
        "field_ids": lifecycle_correlation_field_ids(),
        "lifecycle_phase_anchor_allowed_values": list(LIFECYCLE_PHASE_ANCHOR_VALUES),
        "primary_lifecycle_event_reference_allowed_values": list(
            PRIMARY_LIFECYCLE_EVENT_REFERENCE_VALUES
        ),
        "instructions": list(LIFECYCLE_CORRELATION_INSTRUCTIONS),
        "blank_by_default": True,
        "redacted_metadata_only": True,
        "candidate_only": True,
        "non_evidence": True,
        "metadata_only": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
    }


def source_metadata_template(
    target: dict[str, str],
    *,
    surface_id: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": SOURCE_METADATA_SCHEMA,
        "status": SOURCE_METADATA_STATUS,
        "required": True,
        "field_ids": list(SOURCE_METADATA_FIELD_IDS),
        "instructions": list(SOURCE_METADATA_INSTRUCTIONS),
        "target": dict(target),
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "surface_id": surface_id,
        "artifact_id": artifact_id,
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "source_accepted": False,
        "source_ready": False,
        "source_required_for_checker_intake": True,
        "source_metadata_required": True,
        "copy_to_offline_workspace_required": True,
        "redaction_required": True,
        "live_server_path_allowed": False,
        "discord_or_rcon_source_allowed": False,
        "raw_player_text_retention_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
    }


def attach_source_metadata(value: Any, target: dict[str, str]) -> Any:
    if isinstance(value, dict):
        updated = {
            key: child
            if key
            in {
                "artifact_intake_constraints",
                "candidate_only_metadata",
                "no_flood_capture_policy",
                "non_claim_flags",
                "non_substitution_flags",
                "parallel_capture_boundary",
                "player_principal_window_composition",
                "redaction_policy",
                "single_player_route_constraints",
                "source_metadata",
                "text_privacy_boundary",
            }
            else attach_source_metadata(child, target)
            for key, child in value.items()
        }
        if (
            "source_metadata" not in updated
            and (
                "source_present" in updated
                or "source_material_present" in updated
                or updated.get("source_metadata_required") is True
            )
        ):
            surface_id = updated.get("surface_id") or updated.get("id")
            artifact_id = updated.get("artifact_id")
            if artifact_id is None and updated.get("artifact_kind") in {"candidate_artifact", "capture_artifact"}:
                artifact_id = updated.get("id")
            updated["source_metadata_required"] = True
            updated["source_metadata"] = source_metadata_template(
                target,
                surface_id=surface_id if isinstance(surface_id, str) else None,
                artifact_id=artifact_id if isinstance(artifact_id, str) else None,
            )
        return updated
    if isinstance(value, list):
        return [attach_source_metadata(child, target) for child in value]
    return value


def artifact_intake_constraints() -> dict[str, bool]:
    return dict(ARTIFACT_INTAKE_CONSTRAINTS)


def redaction_policy() -> dict[str, Any]:
    return {
        **REDACTION_POLICY,
        "must_redact": list(REDACTION_POLICY["must_redact"]),
    }


def clone_worksheet_field(field: dict[str, Any]) -> dict[str, Any]:
    clone = dict(field)
    if isinstance(clone.get("allowed_values"), list):
        clone["allowed_values"] = list(clone["allowed_values"])
    if isinstance(clone.get("value_template"), list):
        clone["value_template"] = list(clone["value_template"])
    return clone


def beta_capture_worksheet_fields_for(surface_id: str) -> list[dict[str, Any]]:
    fields = BETA_CAPTURE_WORKSHEET_FIELDS_BY_SURFACE.get(surface_id)
    if fields is None:
        raise SystemExit(f"internal beta capture worksheet fields missing for {surface_id}")
    return [
        *[clone_worksheet_field(field) for field in COMMON_BETA_CAPTURE_WORKSHEET_FIELDS],
        *[clone_worksheet_field(field) for field in fields],
    ]


def beta_capture_worksheet_surface_rows(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
    *,
    surface_ids: tuple[str, ...] = BROAD_BETA_CAPTURE_SURFACE_IDS,
) -> list[dict[str, Any]]:
    by_id = {surface["id"]: surface for surface in surfaces}
    missing = [
        surface_id
        for surface_id in surface_ids
        if surface_id not in by_id
        or surface_id not in BETA_CAPTURE_WORKSHEET_FIELDS_BY_SURFACE
    ]
    if missing:
        raise SystemExit(f"internal beta capture worksheet surface set missing: {missing}")
    rows = []
    for order, surface_id in enumerate(surface_ids, start=1):
        surface = by_id[surface_id]
        template = action_group_template_for_surface(surface_id)
        rows.append(
            {
                "order": order,
                "surface_id": surface_id,
                "action_group_id": template["id"],
                "target_binding": target_binding(target),
                "target_binding_id": target_binding_id(target),
                "approved_runtime_window_binding": approved_runtime_window_binding(target),
                "objective": surface["objective"],
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "tester_brief": template["tester_brief"],
                "checker": surface["checker"],
                "resolved_checker_command_template": surface[
                    "resolved_checker_command_template"
                ],
                "candidate_artifact_paths": [
                    artifact["path_template"] for artifact in surface["capture_artifacts"]
                ],
                "worksheet_fields": beta_capture_worksheet_fields_for(surface_id),
                "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
                "correlation_field_ids": lifecycle_correlation_field_ids(),
                "correlation_metadata_required": True,
                "correlation_metadata_blank_by_default": True,
                "correlation_metadata_non_evidence": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "source_present": False,
                "source_material_present": False,
                "observation_rows": [],
                "observation_rows_status": "blank_template_for_tester_metadata",
                "same_approved_runtime_window_required": True,
                "exact_target_binding_required": True,
                "copy_to_offline_workspace_before_checker": True,
                "redaction_required_before_checker_intake": True,
                "candidate_only": True,
                "non_evidence": True,
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "blocked_by_player_principal_evidence": True,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
            }
        )
    return rows


def text_privacy_boundary() -> dict[str, Any]:
    return {
        "boundary": NO_RAW_PLAYER_TEXT_BOUNDARY,
        "redacted_metadata_only": True,
        "redaction_required_before_checker_intake": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "must_redact": list(REDACTION_POLICY["must_redact"]),
    }


def parallel_capture_boundary() -> dict[str, bool]:
    return dict(PARALLEL_CAPTURE_BOUNDARY)


def beta_capture_interaction_boundary() -> dict[str, Any]:
    return {
        "schema": BETA_CAPTURE_INTERACTION_BOUNDARY_SCHEMA,
        "scope": "multi_surface_beta_capture_coordination",
        "interaction_surface": "beta_notice_buttons_public_reachability_and_pack_plans",
        "single_operational_message_style": "single_updated_embed_buttons_operational_message",
        "accepted_copied_sibling_set_required_before_runtime_claims": True,
        "accepted_copied_sibling_sets_required_for_runtime_evidence": True,
        "beta_notice_is_coordination_only": True,
        "button_clicks_are_coordination_only": True,
        "public_reachability_is_non_evidence": True,
        "multi_surface_capture_plan_is_candidate_only": True,
        "non_claim_flags": dict(BETA_CAPTURE_INTERACTION_BOUNDARY_FLAGS),
        **BETA_CAPTURE_INTERACTION_BOUNDARY_FLAGS,
    }


def player_principal_window_composition() -> dict[str, Any]:
    return dict(PLAYER_PRINCIPAL_WINDOW_COMPOSITION)


def non_substitution_flags() -> dict[str, bool]:
    return dict(NON_SUBSTITUTION_FLAGS)


def no_restart_action_boundary() -> dict[str, bool]:
    return {
        "no_restart_required": True,
        "operator_actions_do_not_require_restart": True,
        "tester_actions_do_not_require_restart": True,
        "no_marker_or_env_change_required": True,
        "pack_authorizes_restart": False,
        "restart_required": False,
        "server_restart_required": False,
        "operator_action_requires_restart": False,
        "tester_action_requires_restart": False,
        "marker_or_env_change_required": False,
    }


def no_flood_capture_policy() -> dict[str, Any]:
    return {
        "id": NO_FLOOD_CAPTURE_POLICY_ID,
        "status": NO_FLOOD_CAPTURE_POLICY_STATUS,
        "dedupe_key_fields": list(NO_FLOOD_DEDUPE_KEY_FIELDS),
        "request_budget_unit": "surface_per_approved_window",
        "max_request_rows_per_surface_per_window": 1,
        "max_primary_lifecycle_request_rows_per_window": 1,
        "operator_requests_are_templates": True,
        "operator_must_batch_side_lane_requests": True,
        "tester_prompts_must_be_batched_by_action_group": True,
        "dedupe_by_target_window_surface_and_correlation": True,
        "repeated_requests_require_new_operator_approval": True,
        "one_request_row_per_surface_per_approved_window": True,
        "candidate_only": True,
        "non_evidence": True,
        "metadata_only": True,
        "no_flood": True,
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "live_polling_allowed": False,
        "rcon_request_allowed": False,
        "discord_send_allowed": False,
        "discord_request_fanout_allowed": False,
        "server_restart_allowed": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "publication_ready": False,
    }


def single_player_route_constraints() -> dict[str, bool]:
    return {
        "single_player_route_only": True,
        "primary_player_principal_phase_required": True,
        "primary_player_principal_phase_runs_first": True,
        "primary_player_principal_route_must_be_active_before_side_lanes": True,
        "side_lane_collection_requires_active_player_principal_route": True,
        "parallel_side_lane_phases_optional_after_primary": True,
        "same_approved_runtime_window_required": True,
        "exact_target_binding_required": True,
        "redacted_metadata_only": True,
        "copy_to_offline_workspace_before_checker": True,
        "checker_acceptance_required_before_any_surface_claim": True,
        "approved_runtime_evidence_missing_remains_blocking": True,
        "lifecycle_correlation_metadata_required": True,
        "side_lane_correlation_id_required": True,
        "primary_lifecycle_phase_anchor_required": True,
        "offline_command_templates_only": True,
        "no_discord_required": True,
        "discord_send_required": False,
        "live_log_read_required": False,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "side_lane_collection_before_primary_route_active_allowed": False,
        "authorizes_discord_send": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_server_restart": False,
        "authorizes_server_start": False,
        "authorizes_server_stop": False,
        "authorizes_marker_or_env_changes": False,
        "pack_authorizes_discord": False,
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "side_lane_collection_can_replace_player_principal_evidence": False,
        "side_lane_collection_counts_before_checker_acceptance": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "lifecycle_correlation_metadata_counts_as_evidence": False,
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "dedupe_by_target_window_surface_and_correlation": True,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "source_present": False,
        "source_material_present": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        **no_restart_action_boundary(),
    }


def candidate_only_metadata() -> dict[str, Any]:
    return {
        "classification": "candidate_only_non_evidence",
        "candidate_only": True,
        "non_evidence": True,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "readiness_claim_allowed": False,
        "downstream_unlock_allowed": False,
        "passive_capture_counts_as_evidence": False,
        "stale_artifact_counts_as_evidence": False,
        "stale_or_passive_alias_substitution_allowed": False,
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "no_flood": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "side_lane_collection_can_replace_player_principal_evidence": False,
        "side_lane_collection_counts_before_checker_acceptance": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "non_substitution_flags": non_substitution_flags(),
    }


def capture_artifact(
    artifact_id: str,
    kind: str,
    path_template: str,
    *,
    checker_input: str | None,
    collection_note: str,
    artifact_group: str | None = None,
    required_for_checker: bool = True,
    sibling_artifacts: tuple[str, ...] = (),
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "id": artifact_id,
        "kind": kind,
        "path_template": path_template,
        "checker_input": checker_input,
        "required_for_checker": required_for_checker,
        "candidate_artifact_only": True,
        "copy_to_offline_workspace": True,
        "must_not_be_live_server_path": True,
        "redaction_required": True,
        "redaction_note": COMMON_REDACTION_NOTE,
        "collection_note": collection_note,
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "source_present": False,
        "source_material_present": False,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "non_substitution_flags": non_substitution_flags(),
    }
    if artifact_group is not None:
        artifact["artifact_group"] = artifact_group
    if sibling_artifacts:
        artifact["sibling_artifacts"] = list(sibling_artifacts)
    return artifact


SURFACES: tuple[dict[str, Any], ...] = (
    {
        "id": "player_principal_lifecycle",
        "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "objective": STRICT_PLAYER_PRINCIPAL_TRIPLET,
        "operator_action": "join, attempt same-target entry/transfer, then clean logout without cluster switching",
        "tester_action": "join the target, attempt same-target entry or transfer, then cleanly logout",
        "checker_args": ["<approved-runtime-principal-lifecycle-evidence-manifest.json>", "--json"],
    },
    {
        "id": "permissions_admin",
        "checker": "scripts/check_permissions_admin_public_readiness.py",
        "objective": "list-player/kick-path candidate observations only",
        "operator_action": "exercise admin/list-player path only under explicit gate and redaction rules",
        "tester_action": "run approved list-player or admin path with redacted output only",
        "checker_args": ["--beta-capture-artifact", "<offline-permissions-admin-beta-capture.json>", "--json"],
    },
    {
        "id": "command_chat_response",
        "checker": "scripts/check_command_chat_response_public_readiness.py",
        "objective": "command/chat response path candidate observations only",
        "operator_action": "send approved beta test commands that avoid private text retention",
        "tester_action": "send approved non-private beta commands and retain only redacted response metadata",
        "checker_args": [
            "--root",
            "<offline-command-chat-response-root>",
            "--readiness",
            "<offline-command-chat-response-readiness.json>",
            "--json",
        ],
    },
    {
        "id": "commands_replies",
        "checker": "scripts/check_commands_replies_public_readiness.py",
        "objective": "command reply routing candidate observations only",
        "operator_action": "exercise command reply flow after chat-response path is gated",
        "tester_action": "exercise approved reply commands without retaining raw chat text",
        "checker_args": ["--response-path-report", "<offline-command-response-path-report.json>", "--json"],
    },
    {
        "id": "dino_scalar",
        "checker": "scripts/check_dino_scalar_readiness.py",
        "objective": "dino scalar candidate observations only",
        "operator_action": "interact with nearby tame/wild dino state without mutation claims",
        "tester_action": "stand near benign tame or wild dino state and capture scalar metadata only",
        "checker_args": ["--snapshot-root", "<offline-ufunction-snapshot-root>", "--json"],
    },
    {
        "id": "tribe_scalar",
        "checker": "scripts/check_tribe_scalar_boundary_readiness.py",
        "objective": "tribe scalar boundary candidate observations only",
        "operator_action": "exercise tribe-related visibility without private identity capture",
        "tester_action": "trigger tribe-visible state while avoiding private identity capture",
        "checker_args": ["--snapshot-root", "<offline-ufunction-snapshot-root>", "--json"],
    },
    {
        "id": "buff_status",
        "checker": "scripts/check_buff_status_readiness.py",
        "objective": "buff/status candidate observations only",
        "operator_action": "apply/remove safe visible buffs or observe natural buff state",
        "tester_action": "apply or observe safe visible buff state and retain status metadata only",
        "checker_args": ["--snapshot-root", "<offline-ufunction-snapshot-root>", "--json"],
    },
    {
        "id": "inventory_item_copied_signals",
        "checker": "scripts/check_inventory_item_copied_signals_stability.py",
        "objective": "inventory/item copied-signal candidates only",
        "operator_action": "open inventory and move benign test items without mutation API claims",
        "tester_action": "open inventory and move harmless test items while capturing copied-signal notes only",
        "checker_args": ["--json"],
    },
    {
        "id": "inventory_custom_filter_array_boundary",
        "checker": "scripts/check_inventory_custom_filter_array_boundary.py",
        "objective": "inventory custom-filter array boundary candidates only",
        "operator_action": "capture only redacted InventoryCustomFilter UFunction array-boundary metadata",
        "tester_action": "exercise inventory filter view and retain redacted array-boundary metadata only",
        "checker_args": [
            "--snapshot",
            "<offline-inventory-custom-filter-array-boundary-snapshot.json>",
            "--json",
        ],
    },
    {
        "id": "inventory_action_compact_intake",
        "checker": "scripts/check_inventory_action_redacted_observer_gate.py",
        "objective": "inventory-action compact-intake redacted observer gate candidates only",
        "operator_action": (
            "model the gated inventory-action observer from copied offline metadata; any matching "
            "inventory-use exercise remains dispatch-budget-0, redacted, and separately approved"
        ),
        "tester_action": (
            "perform benign inventory action only under separate approval with dispatch-budget 0 "
            "and redacted outputs"
        ),
        "checker_args": [
            "--snapshot-root",
            "<offline-inventory-action-compact-snapshot-root>",
            "--public-sdk-surfaces",
            "<offline-inventory-action-public-sdk-surfaces.json>",
            "--public-gameplay-events",
            "<offline-inventory-action-public-gameplay-events.json>",
            "--decision-manifest",
            "<offline-inventory-action-decisions.json>",
            "--gate-enabled",
            "--observer-profile",
            "observer-debug",
            "--marker",
            "allow-observer-debug-window",
            "--marker",
            "allow-experimental-observers",
            "--marker",
            "enable-inventory-action-redacted-observer",
            "--marker",
            "enable-process-event-hook",
            "--marker",
            "disable-plugins",
            "--ark-binary-sha256",
            "<supported-ark-binary-sha256>",
            "--fname-index",
            "<inventory-action-target-fname-index>",
            "--dispatch-budget",
            "0",
            "--observation-budget",
            "<bounded-observation-budget-1-to-10>",
            "--json",
        ],
    },
    {
        "id": "item_return_only",
        "checker": "scripts/check_item_return_only_readiness.py",
        "objective": "item return-only policy-slice candidates only",
        "operator_action": (
            "exercise benign inventory item checks only after redacted item-return policy-slice "
            "inputs are copied offline"
        ),
        "tester_action": "exercise harmless item checks with copied policy-slice metadata only",
        "checker_args": [
            "--root",
            "<offline-item-return-only-pack-root>",
            "--manifest",
            "<offline-item-return-only-policy-slice.json>",
            "--expected-manifest-sha256",
            "<offline-item-return-only-policy-slice-sha256>",
            "--json",
        ],
    },
    {
        "id": "transfer_baccept",
        "checker": "scripts/check_transfer_baccept_readiness.py",
        "objective": "transfer bAccept copied-bool candidate observations only",
        "operator_action": "attempt normal transfer confirmation only if the lead keeps a transfer server available",
        "tester_action": "attempt normal transfer confirmation only when the lead confirms timing and target",
        "checker_args": [
            "--root",
            "<offline-transfer-baccept-pack-root>",
            "--manifest",
            "<offline-transfer-baccept-policy-slice.json>",
            "--expected-manifest-sha256",
            "<offline-transfer-baccept-policy-slice-sha256>",
            "--json",
        ],
    },
    {
        "id": "transfer_scriptstruct",
        "checker": "scripts/check_transfer_scriptstruct_readiness.py",
        "objective": "transfer ScriptStruct candidate observations only",
        "operator_action": "attempt normal cluster transfer only if the lead keeps a transfer server available",
        "tester_action": "attempt normal cluster transfer only when the lead confirms timing and target",
        "checker_args": ["--snapshot-root", "<offline-scriptstruct-snapshot-root>", "--json"],
    },
    {
        "id": "mission_copied_bool",
        "checker": "scripts/check_mission_copied_bool_readiness.py",
        "objective": "mission copied-bool candidate observations only",
        "operator_action": (
            "exercise safe mission join/leave/removal observations only after redacted "
            "mission policy-slice inputs are copied offline"
        ),
        "tester_action": (
            "trigger or observe safe mission state only when the lead confirms timing; "
            "retain copied bool metadata only"
        ),
        "checker_args": [
            "--root",
            "<offline-mission-copied-bool-pack-root>",
            "--manifest",
            "<offline-mission-copied-bool-policy-slice.json>",
            "--expected-manifest-sha256",
            "<offline-mission-copied-bool-policy-slice-sha256>",
            "--json",
        ],
    },
)


CAPTURE_ARTIFACTS_BY_SURFACE: dict[str, tuple[dict[str, Any], ...]] = {
    "player_principal_lifecycle": (
        capture_artifact(
            "approved_runtime_principal_lifecycle_manifest_candidate",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/player_principal_lifecycle/"
            "approved-runtime-principal-lifecycle-evidence-manifest.json",
            checker_input="<approved-runtime-principal-lifecycle-evidence-manifest.json>",
            collection_note=(
                "candidate bundle manifest only; acceptance still requires the strict approved "
                "runtime principal lifecycle checker"
            ),
            sibling_artifacts=(
                "window-request.json",
                "observer-window.env",
                "operator-approval-request.md",
                "operator-approval-receipt.json",
                "preflight-pre.json",
                "preflight-post.json",
                "window-manifest.env",
                "copied-obelisk-log",
            ),
        ),
    ),
    "permissions_admin": (
        capture_artifact(
            "permissions_admin_beta_capture",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/permissions_admin/offline-permissions-admin-beta-capture.json",
            checker_input="<offline-permissions-admin-beta-capture.json>",
            collection_note="candidate permissions/admin observation artifact for offline checker intake",
        ),
    ),
    "command_chat_response": (
        capture_artifact(
            "command_chat_response_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/command_chat_response/offline-command-chat-response-root",
            checker_input="<offline-command-chat-response-root>",
            collection_note="candidate command/chat response root copied into the offline workspace",
            artifact_group="commands",
        ),
        capture_artifact(
            "command_chat_response_readiness",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/command_chat_response/offline-command-chat-response-readiness.json",
            checker_input="<offline-command-chat-response-readiness.json>",
            collection_note="candidate command/chat readiness summary paired with the response root",
            artifact_group="commands",
        ),
    ),
    "commands_replies": (
        capture_artifact(
            "command_response_path_report",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/commands_replies/offline-command-response-path-report.json",
            checker_input="<offline-command-response-path-report.json>",
            collection_note="candidate command reply routing report for offline checker intake",
            artifact_group="commands",
        ),
    ),
    "dino_scalar": (
        capture_artifact(
            "ufunction_snapshot_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/shared/offline-ufunction-snapshot-root",
            checker_input="<offline-ufunction-snapshot-root>",
            collection_note="shared candidate UFunction snapshot root for dino, tribe, and buff scalar checks",
            artifact_group="ufunction_snapshot_root",
        ),
    ),
    "tribe_scalar": (
        capture_artifact(
            "ufunction_snapshot_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/shared/offline-ufunction-snapshot-root",
            checker_input="<offline-ufunction-snapshot-root>",
            collection_note="shared candidate UFunction snapshot root for dino, tribe, and buff scalar checks",
            artifact_group="ufunction_snapshot_root",
        ),
    ),
    "buff_status": (
        capture_artifact(
            "ufunction_snapshot_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/shared/offline-ufunction-snapshot-root",
            checker_input="<offline-ufunction-snapshot-root>",
            collection_note="shared candidate UFunction snapshot root for dino, tribe, and buff scalar checks",
            artifact_group="ufunction_snapshot_root",
        ),
    ),
    "inventory_item_copied_signals": (
        capture_artifact(
            "inventory_item_copied_signals_candidate",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_item_copied_signals/"
            "offline-inventory-item-copied-signals-candidate.json",
            checker_input=None,
            required_for_checker=False,
            collection_note=(
                "candidate inventory copied-signal notes; current checker has no beta artifact "
                "path flag, so keep this parked for future fixture promotion"
            ),
        ),
    ),
    "inventory_custom_filter_array_boundary": (
        capture_artifact(
            "inventory_custom_filter_array_boundary_snapshot",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_custom_filter_array_boundary/"
            "offline-inventory-custom-filter-array-boundary-snapshot.json",
            checker_input="<offline-inventory-custom-filter-array-boundary-snapshot.json>",
            collection_note=(
                "candidate InventoryCustomFilter UFunction snapshot; retain only redacted "
                "ArrayProperty byte-boundary metadata, not raw array payloads or object identity"
            ),
            artifact_group="inventory",
        ),
    ),
    "inventory_action_compact_intake": (
        capture_artifact(
            "inventory_action_compact_snapshot_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "offline-inventory-action-compact-snapshot-root",
            checker_input="<offline-inventory-action-compact-snapshot-root>",
            collection_note=(
                "candidate inventory-action compact-intake snapshot root; copied offline only "
                "and still metadata/redaction gated"
            ),
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_public_sdk_surfaces",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "offline-inventory-action-public-sdk-surfaces.json",
            checker_input="<offline-inventory-action-public-sdk-surfaces.json>",
            collection_note="offline copied public surface manifest used only to prove no action-param leak",
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_public_gameplay_events",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "offline-inventory-action-public-gameplay-events.json",
            checker_input="<offline-inventory-action-public-gameplay-events.json>",
            collection_note="offline copied gameplay events manifest used only for non-claim boundary checks",
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_decisions",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "offline-inventory-action-decisions.json",
            checker_input="<offline-inventory-action-decisions.json>",
            collection_note="offline copied inventory/item decisions manifest for blocked-promotion checks",
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_supported_ark_binary_sha256",
            "sha256",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "supported-ark-binary.sha256",
            checker_input="<supported-ark-binary-sha256>",
            collection_note="supported ARK binary SHA value for the modeled exact gate, not a live read",
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_target_fname_index",
            "text",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "inventory-action-target-fname-index.txt",
            checker_input="<inventory-action-target-fname-index>",
            collection_note="modeled exact target FName index from copied snapshot metadata only",
            artifact_group="inventory",
        ),
        capture_artifact(
            "inventory_action_observation_budget",
            "text",
            f"{CANDIDATE_ARTIFACT_ROOT}/inventory_action_compact_intake/"
            "bounded-observation-budget-1-to-10.txt",
            checker_input="<bounded-observation-budget-1-to-10>",
            collection_note="bounded candidate observation budget scalar; dispatch budget remains exactly 0",
            artifact_group="inventory",
        ),
    ),
    "item_return_only": (
        capture_artifact(
            "item_return_only_pack_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/item_return_only/offline-item-return-only-pack-root",
            checker_input="<offline-item-return-only-pack-root>",
            collection_note="candidate item return-only pack root copied into the offline workspace",
            artifact_group="inventory",
        ),
        capture_artifact(
            "item_return_only_policy_slice",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/item_return_only/offline-item-return-only-policy-slice.json",
            checker_input="<offline-item-return-only-policy-slice.json>",
            collection_note="candidate item return-only policy slice paired with the pack root",
            artifact_group="inventory",
        ),
        capture_artifact(
            "item_return_only_policy_slice_sha256",
            "sha256",
            f"{CANDIDATE_ARTIFACT_ROOT}/item_return_only/offline-item-return-only-policy-slice.sha256",
            checker_input="<offline-item-return-only-policy-slice-sha256>",
            collection_note="expected sha256 for the candidate item return-only policy slice",
            artifact_group="inventory",
        ),
    ),
    "transfer_baccept": (
        capture_artifact(
            "transfer_baccept_pack_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/transfer_baccept/offline-transfer-baccept-pack-root",
            checker_input="<offline-transfer-baccept-pack-root>",
            collection_note="candidate transfer bAccept pack root copied into the offline workspace",
            artifact_group="transfer",
        ),
        capture_artifact(
            "transfer_baccept_policy_slice",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/transfer_baccept/offline-transfer-baccept-policy-slice.json",
            checker_input="<offline-transfer-baccept-policy-slice.json>",
            collection_note="candidate transfer bAccept policy slice paired with the pack root",
            artifact_group="transfer",
        ),
        capture_artifact(
            "transfer_baccept_policy_slice_sha256",
            "sha256",
            f"{CANDIDATE_ARTIFACT_ROOT}/transfer_baccept/offline-transfer-baccept-policy-slice.sha256",
            checker_input="<offline-transfer-baccept-policy-slice-sha256>",
            collection_note="expected sha256 for the candidate transfer bAccept policy slice",
            artifact_group="transfer",
        ),
    ),
    "transfer_scriptstruct": (
        capture_artifact(
            "transfer_scriptstruct_snapshot_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/transfer_scriptstruct/offline-scriptstruct-snapshot-root",
            checker_input="<offline-scriptstruct-snapshot-root>",
            collection_note="candidate transfer ScriptStruct snapshot root copied into the offline workspace",
            artifact_group="transfer",
        ),
    ),
    "mission_copied_bool": (
        capture_artifact(
            "mission_copied_bool_pack_root",
            "directory",
            f"{CANDIDATE_ARTIFACT_ROOT}/mission_copied_bool/offline-mission-copied-bool-pack-root",
            checker_input="<offline-mission-copied-bool-pack-root>",
            collection_note="candidate mission copied-bool pack root copied into the offline workspace",
            artifact_group="mission",
        ),
        capture_artifact(
            "mission_copied_bool_policy_slice",
            "json",
            f"{CANDIDATE_ARTIFACT_ROOT}/mission_copied_bool/offline-mission-copied-bool-policy-slice.json",
            checker_input="<offline-mission-copied-bool-policy-slice.json>",
            collection_note=(
                "candidate mission copied-bool policy slice; player/controller/character refs "
                "and item id arrays remain redacted"
            ),
            artifact_group="mission",
        ),
        capture_artifact(
            "mission_copied_bool_policy_slice_sha256",
            "sha256",
            f"{CANDIDATE_ARTIFACT_ROOT}/mission_copied_bool/offline-mission-copied-bool-policy-slice.sha256",
            checker_input="<offline-mission-copied-bool-policy-slice-sha256>",
            collection_note="expected sha256 for the candidate mission copied-bool policy slice",
            artifact_group="mission",
        ),
    ),
}


BETA_TESTER_ACTION_GROUP_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "primary_player_principal_gate",
        "title": "Primary player-principal evidence gate",
        "surface_ids": ("player_principal_lifecycle",),
        "lead_next_action": (
            "assign one tester to produce the strict HandleNewPlayer/CheckJoinInProgress/OnLogout "
            "runtime triplet under the separately approved evidence window"
        ),
        "tester_brief": "join the target, attempt same-target entry or transfer, then cleanly logout",
    },
    {
        "id": "admin_and_command_routes",
        "title": "Admin and command route candidates",
        "surface_ids": ("permissions_admin", "command_chat_response", "commands_replies"),
        "lead_next_action": "assign one admin tester to run the approved redacted admin and command script",
        "tester_brief": "exercise list-player, chat command response, and reply routing without retaining raw text",
    },
    {
        "id": "world_state_scalar_candidates",
        "title": "Dino, tribe, and buff scalar candidates",
        "surface_ids": ("dino_scalar", "tribe_scalar", "buff_status"),
        "lead_next_action": "assign one tester near known tame/tribe/buff conditions to create compact observations",
        "tester_brief": "observe benign dino, tribe, and visible buff state without mutation or identity claims",
    },
    {
        "id": "inventory_item_candidates",
        "title": "Inventory and item candidates",
        "surface_ids": (
            "inventory_item_copied_signals",
            "inventory_custom_filter_array_boundary",
            "inventory_action_compact_intake",
            "item_return_only",
        ),
        "lead_next_action": (
            "assign one tester to open inventory and exercise benign item checks with redacted outputs "
            "only inside a separately approved player-principal lifecycle window"
        ),
        "tester_brief": (
            "move harmless test items and capture only copied scalar, redacted observer-gate, "
            "or redacted array-boundary metadata"
        ),
    },
    {
        "id": "transfer_candidates",
        "title": "Transfer candidates",
        "surface_ids": ("transfer_baccept", "transfer_scriptstruct"),
        "lead_next_action": "assign one tester only if a transfer server remains available and the lead approves timing",
        "tester_brief": "attempt normal transfer confirmation and cluster transfer with copied offline artifacts only",
    },
    {
        "id": "mission_candidates",
        "title": "Mission candidates",
        "surface_ids": ("mission_copied_bool",),
        "lead_next_action": (
            "assign one tester to trigger or observe safe mission state only when timing "
            "and redacted copied artifact handling are approved"
        ),
        "tester_brief": (
            "exercise safe mission join, leave, or removal observations with copied bool "
            "metadata only"
        ),
    },
)


def validate_beta_tester_action_group_templates(surface_ids: list[str]) -> None:
    grouped_ids = [
        surface_id
        for group in BETA_TESTER_ACTION_GROUP_TEMPLATES
        for surface_id in group["surface_ids"]
    ]
    duplicates = sorted({surface_id for surface_id in grouped_ids if grouped_ids.count(surface_id) > 1})
    if duplicates:
        raise SystemExit(f"internal beta tester action group duplicates: {duplicates}")
    if set(grouped_ids) != set(surface_ids):
        raise SystemExit("internal beta tester action group surface set mismatch")


def action_group_template_for_surface(surface_id: str) -> dict[str, Any]:
    matches = [
        template
        for template in BETA_TESTER_ACTION_GROUP_TEMPLATES
        if surface_id in template["surface_ids"]
    ]
    if len(matches) != 1:
        raise SystemExit(f"internal beta tester action group binding invalid for {surface_id}")
    return matches[0]


def operator_tester_action_metadata(
    surface: dict[str, Any],
    target: dict[str, str],
    *,
    side_lane: bool,
) -> dict[str, Any]:
    template = action_group_template_for_surface(surface["id"])
    return {
        "surface_id": surface["id"],
        "action_group_id": template["id"],
        "action_group_title": template["title"],
        "operator_action": surface["operator_action"],
        "tester_action": surface["tester_action"],
        "operator_next_action": template["lead_next_action"],
        "lead_next_action": template["lead_next_action"],
        "tester_brief": template["tester_brief"],
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "same_approved_runtime_window_required": True,
        "exact_approved_runtime_window_required": True,
        "same_instance_and_map_required": True,
        "separate_operator_approval_required_before_collection": True,
        "operator_must_record_approval_receipt": True,
        "tester_must_stay_on_bound_target": True,
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "candidate_observation_only": True,
        "optional_parallel_candidate_observation": side_lane,
        "side_lane": side_lane,
        "non_evidence_until_checker_acceptance": True,
        "substitution_allowed": False,
        "source_present": False,
        "source_material_present": False,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def beta_tester_next_action_groups(surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    surface_ids = [surface["id"] for surface in surfaces]
    validate_beta_tester_action_group_templates(surface_ids)
    by_id = {surface["id"]: surface for surface in surfaces}
    groups = []
    for order, template in enumerate(BETA_TESTER_ACTION_GROUP_TEMPLATES, start=1):
        group_surfaces = [by_id[surface_id] for surface_id in template["surface_ids"]]
        approved_window_binding = group_surfaces[0]["approved_runtime_window_binding"]
        group_target = {
            "instance": approved_window_binding["instance"],
            "map": approved_window_binding["map"],
        }
        optional_group = template["id"] != "primary_player_principal_gate"
        groups.append(
            {
                "id": template["id"],
                "title": template["title"],
                "order": order,
                "surface_ids": list(template["surface_ids"]),
                "surfaces": [
                    {
                        "id": surface["id"],
                        "priority": surface["priority"],
                        "checker": surface["checker"],
                        "candidate_artifact_count": surface["candidate_artifact_count"],
                    }
                    for surface in group_surfaces
                ],
                "checker_commands": [
                    {
                        "surface_id": surface["id"],
                        "command": surface["post_capture_checker_command"],
                        "checker_command_bindings": surface["checker_command_bindings"],
                        "resolved_checker_command_template": surface[
                            "resolved_checker_command_template"
                        ],
                        "target_bound_checker_command": surface[
                            "target_bound_checker_command"
                        ],
                    }
                    for surface in group_surfaces
                ],
                "candidate_artifact_count": sum(
                    surface["candidate_artifact_count"] for surface in group_surfaces
                ),
                "lead_next_action": template["lead_next_action"],
                "tester_brief": template["tester_brief"],
                "approved_runtime_window_binding": approved_window_binding,
                "operator_tester_action_metadata": {
                    "action_group_id": template["id"],
                    "surface_ids": list(template["surface_ids"]),
                    "operator_next_action": template["lead_next_action"],
                    "lead_next_action": template["lead_next_action"],
                    "tester_brief": template["tester_brief"],
                    "approved_runtime_window_binding": approved_window_binding,
                    "same_approved_runtime_window_required": True,
                    "exact_approved_runtime_window_required": True,
                    "same_instance_and_map_required": True,
                    "separate_operator_approval_required_before_collection": True,
                    "tester_actions_required": True,
                    "lifecycle_correlation_metadata": lifecycle_correlation_metadata(
                        group_target
                    ),
                    "correlation_field_ids": lifecycle_correlation_field_ids(),
                    "correlation_metadata_required": True,
                    "correlation_metadata_non_evidence": True,
                    "no_flood_capture_policy": no_flood_capture_policy(),
                    "no_flood": True,
                    "one_request_row_per_surface_per_approved_window": True,
                    "candidate_observation_only": True,
                    "optional_parallel_candidate_observations": optional_group,
                    "non_evidence_until_checker_acceptance": True,
                    "substitution_allowed": False,
                    "source_present": False,
                    "source_material_present": False,
                    "raw_player_text_retention_allowed": False,
                    "raw_player_text_capture_allowed": False,
                    "raw_chat_payload_capture_allowed": False,
                    "private_player_data_retention_allowed": False,
                    "secrets_or_webhook_retention_allowed": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_progress": False,
                    "counts_as_p0_progress": False,
                    "source_material_counts_as_evidence": False,
                    "flood_capture_allowed": False,
                    "unbounded_tester_requests_allowed": False,
                    "discord_request_fanout_allowed": False,
                    "action_boundary": NO_RESTART_ACTION_BOUNDARY,
                    **no_restart_action_boundary(),
                },
                "beta_session_objective": (
                    "collect redacted candidate artifacts for the listed surfaces in one beta "
                    "session only when a separate player-principal lifecycle window is approved"
                ),
                "player_principal_window_composition": player_principal_window_composition(),
                "composition_role": (
                    "primary_player_principal_lifecycle_window"
                    if not optional_group
                    else "optional_parallel_candidate_observations"
                ),
                "optional_parallel_candidate_observations": optional_group,
                "candidate_only": True,
                "non_evidence": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "source_present": False,
                "source_material_present": False,
                "parallel_capture_boundary": parallel_capture_boundary(),
                "non_substitution_flags": non_substitution_flags(),
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "current_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "readiness_claim_allowed": False,
                "downstream_unlock_allowed": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "operator_next_action": template["lead_next_action"],
                "action_boundary": NO_RESTART_ACTION_BOUNDARY,
                **no_restart_action_boundary(),
            }
        )
    return groups


def broad_beta_capture_pack_path(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    by_id = {surface["id"]: surface for surface in surfaces}
    missing = [surface_id for surface_id in BROAD_BETA_CAPTURE_SURFACE_IDS if surface_id not in by_id]
    if missing:
        raise SystemExit(f"internal broad beta capture surface set missing: {missing}")
    path_surfaces = [by_id[surface_id] for surface_id in BROAD_BETA_CAPTURE_SURFACE_IDS]
    shared_artifact_groups = [
        {
            "artifact_group": "commands",
            "surface_ids": ["command_chat_response", "commands_replies"],
            "status": "status_only_candidate_only",
            "candidate_only": True,
            "non_evidence": True,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
        },
        {
            "artifact_group": "ufunction_snapshot_root",
            "surface_ids": ["dino_scalar", "tribe_scalar", "buff_status"],
            "path_template": f"{CANDIDATE_ARTIFACT_ROOT}/shared/offline-ufunction-snapshot-root",
            "status": "status_only_candidate_only",
            "candidate_only": True,
            "non_evidence": True,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
        },
    ]
    worksheet_rows = beta_capture_worksheet_surface_rows(path_surfaces, target)
    return {
        "id": BROAD_BETA_CAPTURE_PACK_PATH_ID,
        "title": "Admin, commands, dino, tribe, and buff candidate path",
        "status": "status_only_candidate_capture_path",
        "path_status": "status_only_candidate_non_evidence",
        "worksheet": {
            "id": BROAD_BETA_CAPTURE_WORKSHEET_ID,
            "schema": BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
            "file": BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            "status": "candidate_worksheet_template",
            "surface_ids": list(BROAD_BETA_CAPTURE_SURFACE_IDS),
            "row_count": len(worksheet_rows),
            "target_binding_id": target_binding_id(target),
            "same_approved_runtime_window_required": True,
            "redacted_metadata_only": True,
            "no_flood": True,
            "one_request_row_per_surface_per_approved_window": True,
            "candidate_only": True,
            "non_evidence": True,
            "source_present": False,
            "source_material_present": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "clears_approved_runtime_evidence_missing": False,
            "source_material_counts_as_evidence": False,
            "flood_capture_allowed": False,
            "unbounded_tester_requests_allowed": False,
            "discord_request_fanout_allowed": False,
        },
        "surface_ids": list(BROAD_BETA_CAPTURE_SURFACE_IDS),
        "action_group_ids": list(BROAD_BETA_CAPTURE_ACTION_GROUP_IDS),
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "candidate_surface_count": len(path_surfaces),
        "candidate_artifact_count": sum(surface["candidate_artifact_count"] for surface in path_surfaces),
        "surfaces": [
            {
                "id": surface["id"],
                "priority": surface["priority"],
                "checker": surface["checker"],
                "command": surface["post_capture_checker_command"],
                "candidate_artifact_count": surface["candidate_artifact_count"],
                "candidate_artifacts": [
                    {
                        "id": artifact["id"],
                        "path_template": artifact["path_template"],
                        "checker_input": artifact["checker_input"],
                        "required_for_checker": artifact["required_for_checker"],
                    }
                    for artifact in surface["capture_artifacts"]
                ],
                "target_binding_id": surface["target_binding_id"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": True,
                "correlation_metadata_non_evidence": True,
                "same_approved_runtime_window_required": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "candidate_only": True,
                "non_evidence": True,
                "source_present": False,
                "source_material_present": False,
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
            }
            for surface in path_surfaces
        ],
        "worksheet_rows": worksheet_rows,
        "shared_artifact_groups": shared_artifact_groups,
        "candidate_only": True,
        "candidate_capture_only": True,
        "status_only": True,
        "non_evidence": True,
        "debug_only": True,
        "side_lane_non_counting": True,
        "same_approved_runtime_window_required": True,
        "artifact_templates_only": True,
        "copy_to_offline_workspace_before_analysis": True,
        "redaction_required_before_checker_intake": True,
        "do_not_read_live_server_paths_from_pack": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "source_present": False,
        "source_material_present": False,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "non_claim": BROAD_BETA_CAPTURE_NON_CLAIM,
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "non_substitution_flags": non_substitution_flags(),
        "non_claim_flags": non_claim_flags(),
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "approved_runtime_evidence_substitution_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "readiness_claim_allowed": False,
        "downstream_unlock_allowed": False,
    }


def parallel_beta_capture_side_lane_matrix(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    by_id = {surface["id"]: surface for surface in surfaces}
    missing = [surface_id for surface_id in PARALLEL_BETA_CAPTURE_SURFACE_IDS if surface_id not in by_id]
    if missing:
        raise SystemExit(f"internal parallel beta capture surface set missing: {missing}")
    matrix_surfaces = [by_id[surface_id] for surface_id in PARALLEL_BETA_CAPTURE_SURFACE_IDS]
    target_binding_row = target_binding(target)
    approved_window_binding = approved_runtime_window_binding(target)
    domain_rows = [
        {
            "domain": domain,
            "surface_ids": list(surface_ids),
            "status": "status_only_candidate_non_evidence",
            "target_binding": target_binding_row,
            "target_binding_id": target_binding_id(target),
            "approved_runtime_window_binding": approved_window_binding,
            "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
            "correlation_field_ids": lifecycle_correlation_field_ids(),
            "correlation_metadata_required": True,
            "correlation_metadata_non_evidence": True,
            "operator_next_action": action_group_template_for_surface(surface_ids[0])[
                "lead_next_action"
            ],
            "lead_next_action": action_group_template_for_surface(surface_ids[0])[
                "lead_next_action"
            ],
            "tester_brief": action_group_template_for_surface(surface_ids[0])["tester_brief"],
            "operator_actions": [by_id[surface_id]["operator_action"] for surface_id in surface_ids],
            "tester_actions": [by_id[surface_id]["tester_action"] for surface_id in surface_ids],
            "no_flood_capture_policy": no_flood_capture_policy(),
            "no_flood": True,
            "one_request_row_per_surface_per_approved_window": True,
            "candidate_only": True,
            "non_evidence": True,
            "source_present": False,
            "source_material_present": False,
            "same_approved_runtime_window_required": True,
            "exact_approved_runtime_window_required": True,
            "exact_target_binding_required": True,
            "requires_checker_acceptance": True,
            "requires_player_principal_triplet": True,
            "side_lane_non_counting": True,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "substitutes_for_player_principal_lifecycle_evidence": False,
            "primary_evidence_substitution_allowed": False,
            "source_material_counts_as_evidence": False,
            "flood_capture_allowed": False,
            "unbounded_tester_requests_allowed": False,
            "discord_request_fanout_allowed": False,
            "action_boundary": NO_RESTART_ACTION_BOUNDARY,
            **no_restart_action_boundary(),
        }
        for domain, surface_ids in PARALLEL_BETA_CAPTURE_DOMAINS
    ]
    action_group_rows = [
        {
            "action_group_id": group_id,
            "surface_ids": list(action_group_template["surface_ids"]),
            "status": "status_only_candidate_non_evidence",
            "target_binding": target_binding_row,
            "target_binding_id": target_binding_id(target),
            "approved_runtime_window_binding": approved_window_binding,
            "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
            "correlation_field_ids": lifecycle_correlation_field_ids(),
            "correlation_metadata_required": True,
            "correlation_metadata_non_evidence": True,
            "operator_next_action": action_group_template["lead_next_action"],
            "lead_next_action": action_group_template["lead_next_action"],
            "tester_brief": action_group_template["tester_brief"],
            "operator_actions": [
                by_id[surface_id]["operator_action"]
                for surface_id in action_group_template["surface_ids"]
            ],
            "tester_actions": [
                by_id[surface_id]["tester_action"]
                for surface_id in action_group_template["surface_ids"]
            ],
            "no_flood_capture_policy": no_flood_capture_policy(),
            "no_flood": True,
            "one_request_row_per_surface_per_approved_window": True,
            "candidate_only": True,
            "non_evidence": True,
            "source_present": False,
            "source_material_present": False,
            "same_approved_runtime_window_required": True,
            "exact_approved_runtime_window_required": True,
            "exact_target_binding_required": True,
            "requires_checker_acceptance": True,
            "requires_player_principal_triplet": True,
            "side_lane_non_counting": True,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "substitution_allowed": False,
            "primary_evidence_substitution_allowed": False,
            "source_material_counts_as_evidence": False,
            "flood_capture_allowed": False,
            "unbounded_tester_requests_allowed": False,
            "discord_request_fanout_allowed": False,
            "action_boundary": NO_RESTART_ACTION_BOUNDARY,
            **no_restart_action_boundary(),
        }
        for group_id in PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS
        for action_group_template in BETA_TESTER_ACTION_GROUP_TEMPLATES
        if action_group_template["id"] == group_id
    ]
    return {
        "id": PARALLEL_BETA_CAPTURE_MATRIX_ID,
        "title": (
            "Admin, commands, dino, tribe, buff, inventory, item, transfer, and mission "
            "parallel candidates"
        ),
        "status": "status_only_parallel_candidate_capture_matrix",
        "matrix_status": "status_only_candidate_non_evidence",
        "surface_ids": list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
        "action_group_ids": list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS),
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "candidate_surface_count": len(matrix_surfaces),
        "candidate_artifact_count": sum(surface["candidate_artifact_count"] for surface in matrix_surfaces),
        "domain_rows": domain_rows,
        "action_group_rows": action_group_rows,
        "surface_rows": [
            {
                "id": surface["id"],
                "priority": surface["priority"],
                "action_group_id": action_group_template_for_surface(surface["id"])["id"],
                "checker": surface["checker"],
                "command": surface["post_capture_checker_command"],
                "candidate_artifact_count": surface["candidate_artifact_count"],
                "candidate_artifact_ids": [
                    artifact["id"] for artifact in surface["capture_artifacts"]
                ],
                "required_checker_inputs": [
                    row["checker_input"] for row in surface["required_checker_artifacts"]
                ],
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": True,
                "correlation_metadata_non_evidence": True,
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "operator_next_action": action_group_template_for_surface(surface["id"])[
                    "lead_next_action"
                ],
                "lead_next_action": action_group_template_for_surface(surface["id"])[
                    "lead_next_action"
                ],
                "tester_brief": action_group_template_for_surface(surface["id"])[
                    "tester_brief"
                ],
                "operator_tester_action_metadata": surface.get(
                    "operator_tester_action_metadata",
                    operator_tester_action_metadata(surface, target, side_lane=True),
                ),
                "checker_command_bindings": surface["checker_command_bindings"],
                "resolved_checker_command_template": surface[
                    "resolved_checker_command_template"
                ],
                "target_bound_checker_command": surface["target_bound_checker_command"],
                "same_approved_runtime_window_required": True,
                "exact_approved_runtime_window_required": True,
                "same_instance_and_map_required": True,
                "exact_target_binding_required": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "candidate_only": True,
                "status_only": True,
                "non_evidence": True,
                "source_present": False,
                "source_material_present": False,
                "optional_parallel_candidate_observation": True,
                "parallel_with_player_principal_lifecycle_window": True,
                "side_lane": True,
                "side_lane_non_counting": True,
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "blocked_by_player_principal_evidence": True,
                "current_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "replaces_player_principal_evidence": False,
                "replaces_player_principal_triplet": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_triplet": False,
                "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
                "player_principal_lifecycle_evidence_substitution_allowed": False,
                "approved_runtime_evidence_substitution_allowed": False,
                "primary_evidence_substitution_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "v1_completion_ready": False,
                "action_boundary": NO_RESTART_ACTION_BOUNDARY,
                **no_restart_action_boundary(),
            }
            for surface in matrix_surfaces
        ],
        "candidate_only": True,
        "candidate_capture_only": True,
        "status_only": True,
        "non_evidence": True,
        "debug_only": True,
        "optional_parallel_candidate_observations": True,
        "parallel_with_player_principal_lifecycle_window_planned": True,
        "same_approved_runtime_window_required": True,
        "exact_approved_runtime_window_required": True,
        "same_instance_and_map_required": True,
        "exact_target_binding_required": True,
        "side_lane_non_counting": True,
        "artifact_templates_only": True,
        "copy_to_offline_workspace_before_analysis": True,
        "redaction_required_before_checker_intake": True,
        "do_not_read_live_server_paths_from_pack": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "source_present": False,
        "source_material_present": False,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "non_claim": PARALLEL_BETA_CAPTURE_NON_CLAIM,
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "non_substitution_flags": non_substitution_flags(),
        "non_claim_flags": non_claim_flags(),
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "approved_runtime_evidence_substitution_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "readiness_claim_allowed": False,
        "downstream_unlock_allowed": False,
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def single_player_parallel_capture_sequence(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    by_id = {surface["id"]: surface for surface in surfaces}
    templates = {template["id"]: template for template in BETA_TESTER_ACTION_GROUP_TEMPLATES}
    missing_groups = [
        group_id
        for group_id in SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS
        if group_id not in templates
    ]
    if missing_groups:
        raise SystemExit(f"internal single-player capture group missing: {missing_groups}")
    side_lane_surface_ids = [
        surface_id
        for group_id in PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS
        for surface_id in templates[group_id]["surface_ids"]
    ]
    if side_lane_surface_ids != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        raise SystemExit("internal single-player side-lane surface order mismatch")
    missing_surfaces = [
        surface_id
        for surface_id in SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS
        if surface_id not in by_id
    ]
    if missing_surfaces:
        raise SystemExit(f"internal single-player capture surface missing: {missing_surfaces}")
    unexpected_exclusions = [
        surface_id
        for surface_id in by_id
        if surface_id not in SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS
        and surface_id not in SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS
    ]
    if unexpected_exclusions:
        raise SystemExit(
            "internal single-player capture route exclusion set missing: "
            f"{unexpected_exclusions}"
        )

    target_binding_row = target_binding(target)
    approved_window_binding = approved_runtime_window_binding(target)
    privacy = text_privacy_boundary()
    route_constraints = single_player_route_constraints()
    phases = []
    for order, group_id in enumerate(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS, start=1):
        template = templates[group_id]
        group_surfaces = [by_id[surface_id] for surface_id in template["surface_ids"]]
        optional_group = group_id != "primary_player_principal_gate"
        phase_domain_ids = SINGLE_PLAYER_PHASE_DOMAIN_IDS_BY_ACTION_GROUP[group_id]
        phases.append(
            {
                "order": order,
                "phase_id": group_id,
                "phase_role": (
                    "optional_parallel_candidate_observations"
                    if optional_group
                    else "primary_player_principal_lifecycle"
                ),
                "phase_domain_ids": list(phase_domain_ids),
                "surface_ids": list(template["surface_ids"]),
                "status": "status_only_candidate_non_evidence",
                "target_binding": target_binding_row,
                "target_binding_id": target_binding_id(target),
                "approved_runtime_window_binding": approved_window_binding,
                "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
                "correlation_field_ids": lifecycle_correlation_field_ids(),
                "correlation_metadata_required": True,
                "correlation_metadata_non_evidence": True,
                "operator_next_action": template["lead_next_action"],
                "lead_next_action": template["lead_next_action"],
                "tester_brief": template["tester_brief"],
                "operator_actions": [
                    surface["operator_action"] for surface in group_surfaces
                ],
                "tester_actions": [
                    surface["tester_action"] for surface in group_surfaces
                ],
                "checker_commands": [
                    {
                        "surface_id": surface["id"],
                        "command": surface["post_capture_checker_command"],
                        "checker_command_bindings": surface["checker_command_bindings"],
                        "resolved_checker_command_template": surface[
                            "resolved_checker_command_template"
                        ],
                        "target_bound_checker_command": surface[
                            "target_bound_checker_command"
                        ],
                    }
                    for surface in group_surfaces
                ],
                "candidate_artifact_ids": [
                    artifact["id"]
                    for surface in group_surfaces
                    for artifact in surface["capture_artifacts"]
                ],
                "readiness_checker_support": [
                    {
                        "surface_id": surface["id"],
                        "checker": surface["checker"],
                        "supported_by_existing_readiness_script": True,
                        "checker_mode": "offline_status_only",
                    }
                    for surface in group_surfaces
                ],
                "single_player_route": True,
                "single_player_route_constraints": dict(route_constraints),
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "candidate_only": True,
                "status_only": True,
                "non_evidence": True,
                "source_present": False,
                "source_material_present": False,
                "optional_parallel_candidate_observations": optional_group,
                "same_approved_runtime_window_required": True,
                "exact_approved_runtime_window_required": True,
                "same_instance_and_map_required": True,
                "exact_target_binding_required": True,
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "blocked_by_player_principal_evidence": True,
                "operator_action_metadata_explicit": True,
                "raw_player_text_retention_allowed": False,
                "raw_player_text_capture_allowed": False,
                "raw_chat_payload_capture_allowed": False,
                "private_player_data_retention_allowed": False,
                "secrets_or_webhook_retention_allowed": False,
                "text_privacy_boundary": privacy,
                "pack_authorizes_discord": False,
                "discord_send_required": False,
                "authorizes_discord_send": False,
                "authorizes_live_log_reads": False,
                "authorizes_runtime_capture": False,
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "substitution_allowed": False,
                "primary_evidence_substitution_allowed": False,
                "side_lane_collection_can_replace_player_principal_evidence": False,
                "side_lane_collection_counts_before_checker_acceptance": False,
                "side_lane_counts_toward_sdk": False,
                "side_lane_counts_toward_p0": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "action_boundary": NO_RESTART_ACTION_BOUNDARY,
                **no_restart_action_boundary(),
            }
        )

    return {
        "id": SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID,
        "title": "Single-player parallel beta capture sequence",
        "status": "status_only_parallel_candidate_sequence",
        "sequence_status": "status_only_candidate_non_evidence",
        "route_summary": SINGLE_PLAYER_ROUTE_SUMMARY,
        "non_claim": SINGLE_PLAYER_ROUTE_NON_CLAIM,
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "surface_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
        "single_player_route_surface_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
        "side_lane_surface_ids": list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
        "candidate_domain_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_DOMAIN_IDS),
        "excluded_surface_ids": list(SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS),
        "action_group_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS),
        "phase_count": len(phases),
        "phases": phases,
        "single_player_route": True,
        "single_player_route_constraints": route_constraints,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "text_privacy_boundary": privacy,
        "candidate_only": True,
        "status_only": True,
        "non_evidence": True,
        "source_present": False,
        "source_material_present": False,
        "parallel_with_player_principal_lifecycle_window_planned": True,
        "same_approved_runtime_window_required": True,
        "exact_approved_runtime_window_required": True,
        "same_instance_and_map_required": True,
        "exact_target_binding_required": True,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "operator_action_metadata_explicit": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "pack_authorizes_discord": False,
        "discord_send_required": False,
        "authorizes_discord_send": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_server_restart": False,
        "authorizes_server_start": False,
        "authorizes_server_stop": False,
        "authorizes_marker_or_env_changes": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "substitution_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "side_lane_collection_can_replace_player_principal_evidence": False,
        "side_lane_collection_counts_before_checker_acceptance": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "non_claim_flags": non_claim_flags(),
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def clone_capture_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    clone = dict(artifact)
    if isinstance(clone.get("sibling_artifacts"), list):
        clone["sibling_artifacts"] = list(clone["sibling_artifacts"])
    if isinstance(clone.get("non_claim_flags"), dict):
        clone["non_claim_flags"] = dict(clone["non_claim_flags"])
    if isinstance(clone.get("non_substitution_flags"), dict):
        clone["non_substitution_flags"] = dict(clone["non_substitution_flags"])
    if isinstance(clone.get("candidate_only_metadata"), dict):
        clone["candidate_only_metadata"] = dict(clone["candidate_only_metadata"])
        if isinstance(clone["candidate_only_metadata"].get("non_substitution_flags"), dict):
            clone["candidate_only_metadata"]["non_substitution_flags"] = dict(
                clone["candidate_only_metadata"]["non_substitution_flags"]
            )
    if isinstance(clone.get("parallel_capture_boundary"), dict):
        clone["parallel_capture_boundary"] = dict(clone["parallel_capture_boundary"])
    if isinstance(clone.get("no_flood_capture_policy"), dict):
        clone["no_flood_capture_policy"] = dict(clone["no_flood_capture_policy"])
        if isinstance(clone["no_flood_capture_policy"].get("dedupe_key_fields"), list):
            clone["no_flood_capture_policy"]["dedupe_key_fields"] = list(
                clone["no_flood_capture_policy"]["dedupe_key_fields"]
            )
    if isinstance(clone.get("approved_runtime_window_binding"), dict):
        clone["approved_runtime_window_binding"] = dict(clone["approved_runtime_window_binding"])
        if isinstance(clone["approved_runtime_window_binding"].get("target_binding"), dict):
            clone["approved_runtime_window_binding"]["target_binding"] = dict(
                clone["approved_runtime_window_binding"]["target_binding"]
            )
    return clone


def bind_capture_artifact(artifact: dict[str, Any], target: dict[str, str]) -> dict[str, Any]:
    clone = clone_capture_artifact(artifact)
    clone["target_binding"] = target_binding(target)
    clone["approved_runtime_window_binding"] = approved_runtime_window_binding(target)
    clone["lifecycle_correlation_metadata"] = lifecycle_correlation_metadata(target)
    clone["correlation_field_ids"] = lifecycle_correlation_field_ids()
    clone["correlation_metadata_required"] = True
    clone["correlation_metadata_non_evidence"] = True
    clone["artifact_intake_constraints"] = artifact_intake_constraints()
    clone["redaction_policy"] = redaction_policy()
    return clone


def capture_artifacts_for(surface_id: str, target: dict[str, str] | None = None) -> list[dict[str, Any]]:
    artifacts = CAPTURE_ARTIFACTS_BY_SURFACE.get(surface_id)
    if artifacts is None:
        raise SystemExit(f"internal capture artifacts missing for {surface_id}")
    if target is None:
        return [clone_capture_artifact(artifact) for artifact in artifacts]
    return [bind_capture_artifact(artifact, target) for artifact in artifacts]


def validate_surface_artifact_placeholders(surface: dict[str, Any], artifacts: list[dict[str, Any]]) -> None:
    checker_args = surface.get("checker_args", ["--json"])
    if not isinstance(checker_args, list) or not all(isinstance(arg, str) for arg in checker_args):
        raise SystemExit(f"internal checker args invalid for {surface.get('id')}")
    placeholders = {arg for arg in checker_args if arg.startswith("<") and arg.endswith(">")}
    artifact_inputs = {
        artifact["checker_input"]
        for artifact in artifacts
        if isinstance(artifact.get("checker_input"), str)
    }
    missing = sorted(placeholders - artifact_inputs)
    if missing:
        raise SystemExit(f"internal capture artifact input missing for {surface.get('id')}: {missing}")


def validate_token(value: str, label: str, pattern: re.Pattern[str] = SAFE_TOKEN_RE) -> str:
    if not pattern.fullmatch(value):
        raise SystemExit(f"{label} contains unsafe characters: {value}")
    return value


def non_claim_flags() -> dict[str, bool]:
    return dict(NON_CLAIM_FLAGS)


def checker_command(surface: dict[str, Any]) -> list[str]:
    args = surface.get("checker_args", ["--json"])
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise SystemExit(f"internal checker args invalid for {surface.get('id')}")
    checker = surface.get("checker")
    if not isinstance(checker, str):
        raise SystemExit(f"internal checker path invalid for {surface.get('id')}")
    return ["python3", checker, *args]


def checker_command_bindings(
    command: list[str],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_by_input = {
        artifact["checker_input"]: artifact
        for artifact in artifacts
        if isinstance(artifact.get("checker_input"), str)
    }
    bindings = []
    for order, part in enumerate(
        [item for item in command if item.startswith("<") and item.endswith(">")],
        start=1,
    ):
        artifact = artifact_by_input.get(part)
        if artifact is None:
            raise SystemExit(f"internal command placeholder has no artifact binding: {part}")
        kind = artifact["kind"]
        if kind in PATH_ARGUMENT_ARTIFACT_KINDS:
            resolution = "path_template"
            resolved = artifact["path_template"]
        elif kind in SCALAR_ARGUMENT_ARTIFACT_KINDS:
            resolution = "read_scalar_text_from_path_template"
            resolved = f"<read-text:{artifact['path_template']}>"
        else:
            raise SystemExit(
                f"internal command placeholder artifact kind is not supported: {kind}"
            )
        bindings.append(
            {
                "order": order,
                "checker_input": part,
                "artifact_id": artifact["id"],
                "artifact_kind": kind,
                "path_template": artifact["path_template"],
                "argument_resolution": resolution,
                "resolved_argument_template": resolved,
                "target_binding": artifact["target_binding"],
                "target_binding_id": artifact["target_binding"]["binding_id"],
                "approved_runtime_window_binding": artifact[
                    "approved_runtime_window_binding"
                ],
                "same_approved_runtime_window_required": True,
                "target_binding_required": True,
                "redaction_required": True,
                "must_not_be_live_server_path": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "candidate_only": True,
                "non_evidence": True,
                "source_present": False,
                "source_material_present": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
            }
        )
    return bindings


def resolved_checker_command_template(
    command: list[str],
    bindings: list[dict[str, Any]],
) -> list[str]:
    replacements = {
        binding["checker_input"]: binding["resolved_argument_template"]
        for binding in bindings
    }
    return [replacements.get(part, part) for part in command]


def target_bound_checker_command_row(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface_id": surface["id"],
        "priority": surface["priority"],
        "action_group_id": action_group_template_for_surface(surface["id"])["id"],
        "status": TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS,
        "target_binding": surface["target_binding"],
        "target_binding_id": surface["target_binding_id"],
        "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
        "lifecycle_correlation_metadata": surface["lifecycle_correlation_metadata"],
        "correlation_field_ids": surface["correlation_field_ids"],
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "command": surface["post_capture_checker_command"],
        "checker_command_bindings": surface["checker_command_bindings"],
        "resolved_checker_command_template": surface[
            "resolved_checker_command_template"
        ],
        "candidate_artifact_paths": [
            artifact["path_template"] for artifact in surface["capture_artifacts"]
        ],
        "operator_action": surface["operator_action"],
        "tester_action": surface["tester_action"],
        "tester_brief": action_group_template_for_surface(surface["id"])[
            "tester_brief"
        ],
        "offline_template_only": True,
        "usable_after_redacted_artifact_copy": True,
        "same_approved_runtime_window_required": True,
        "exact_target_binding_required": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "candidate_only": True,
        "non_evidence": True,
        "source_present": False,
        "source_material_present": False,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def required_checker_artifacts(surface: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    placeholders = {
        arg
        for arg in surface.get("checker_args", ["--json"])
        if isinstance(arg, str) and arg.startswith("<") and arg.endswith(">")
    }
    rows = []
    for artifact in artifacts:
        checker_input = artifact.get("checker_input")
        if artifact.get("required_for_checker") is True and isinstance(checker_input, str):
            rows.append(
                {
                    "artifact_id": artifact["id"],
                    "checker_input": checker_input,
                    "path_template": artifact["path_template"],
                    "satisfies_checker_placeholder": checker_input in placeholders,
                    "target_binding_required": True,
                    "target_binding_id": artifact["target_binding"]["binding_id"],
                    "target_binding": artifact["target_binding"],
                    "same_approved_runtime_window_required": True,
                    "approved_runtime_window_binding": artifact["approved_runtime_window_binding"],
                    "redaction_required": True,
                    "must_not_be_live_server_path": True,
                }
            )
    return rows


def optional_candidate_artifacts(artifacts: list[dict[str, Any]]) -> list[str]:
    return [
        artifact["id"]
        for artifact in artifacts
        if artifact.get("required_for_checker") is False
    ]


def surface_entry(surface: dict[str, Any], priority: int, target: dict[str, str]) -> dict[str, Any]:
    side_lane = surface["id"] != "player_principal_lifecycle"
    capture_artifacts = capture_artifacts_for(surface["id"], target)
    validate_surface_artifact_placeholders(surface, capture_artifacts)
    post_capture_checker_command = checker_command(surface)
    command_bindings = checker_command_bindings(
        post_capture_checker_command,
        capture_artifacts,
    )
    command_template = resolved_checker_command_template(
        post_capture_checker_command,
        command_bindings,
    )
    entry = {
        **surface,
        "priority": priority,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "capture_artifacts": capture_artifacts,
        "candidate_artifact_count": len(capture_artifacts),
        "required_checker_artifacts": required_checker_artifacts(surface, capture_artifacts),
        "optional_candidate_artifacts": optional_candidate_artifacts(capture_artifacts),
        "checker_inputs_satisfied_by_artifacts": True,
        "candidate_classification": "candidate_only_non_counting",
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "source_present": False,
        "source_material_present": False,
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "operator_tester_action_metadata": operator_tester_action_metadata(
            surface,
            target,
            side_lane=side_lane,
        ),
        "composition_role": (
            "optional_parallel_candidate_observation"
            if side_lane
            else "primary_player_principal_lifecycle_window"
        ),
        "optional_parallel_candidate_observation": side_lane,
        "parallel_with_player_principal_lifecycle_window": side_lane,
        "non_substitution_flags": non_substitution_flags(),
        "candidate_capture_only": True,
        "side_lane": side_lane,
        "side_lane_non_counting": side_lane,
        "blocked_by_player_principal_evidence": True,
        "requires_player_principal_triplet": True,
        "requires_checker_acceptance": True,
        "post_capture_checker_command": post_capture_checker_command,
        "checker_command_bindings": command_bindings,
        "resolved_checker_command_template": command_template,
        "resolved_checker_command_status": TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS,
        "post_capture_boundary": (
            "copy material to an approved offline workspace and run this checker; "
            "presence in the beta pack never promotes the surface"
        ),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_present": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "approved_runtime_evidence_substitution_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "non_claim_flags": non_claim_flags(),
    }
    entry["target_bound_checker_command"] = target_bound_checker_command_row(entry)
    return entry


def target_bound_checker_command_matrix(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    rows = [target_bound_checker_command_row(surface) for surface in surfaces]
    return {
        "id": TARGET_BOUND_CHECKER_COMMAND_MATRIX_ID,
        "status": TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS,
        "matrix_status": "candidate_only_non_evidence",
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "row_count": len(rows),
        "rows": rows,
        "all_rows_target_bound": True,
        "all_rows_offline_templates_only": True,
        "all_rows_require_redacted_artifact_copy": True,
        "scalar_arguments_use_read_text_templates": True,
        "path_arguments_use_candidate_artifact_templates": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "candidate_only": True,
        "non_evidence": True,
        "source_present": False,
        "source_material_present": False,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "same_approved_runtime_window_required": True,
        "exact_target_binding_required": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "non_claim_flags": non_claim_flags(),
        "text_privacy_boundary": text_privacy_boundary(),
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def side_lane_capture_queue(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    by_id = {surface["id"]: surface for surface in surfaces}
    missing = [surface_id for surface_id in PARALLEL_BETA_CAPTURE_SURFACE_IDS if surface_id not in by_id]
    if missing:
        raise SystemExit(f"internal side-lane capture queue surface set missing: {missing}")

    target_binding_row = target_binding(target)
    approved_window_binding = approved_runtime_window_binding(target)
    queue_rows = []
    for order, surface_id in enumerate(PARALLEL_BETA_CAPTURE_SURFACE_IDS, start=1):
        surface = by_id[surface_id]
        template = action_group_template_for_surface(surface_id)
        queue_rows.append(
            {
                "queue_order": order,
                "surface_id": surface_id,
                "action_group_id": template["id"],
                "status": SIDE_LANE_CAPTURE_QUEUE_STATUS,
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": True,
                "correlation_metadata_non_evidence": True,
                "operator_next_action": template["lead_next_action"],
                "lead_next_action": template["lead_next_action"],
                "tester_brief": template["tester_brief"],
                "tester_action": surface["tester_action"],
                "checker": surface["checker"],
                "resolved_checker_command_template": surface[
                    "resolved_checker_command_template"
                ],
                "candidate_artifact_ids": [
                    artifact["id"] for artifact in surface["capture_artifacts"]
                ],
                "candidate_artifact_paths": [
                    artifact["path_template"] for artifact in surface["capture_artifacts"]
                ],
                "primary_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_primary_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "required_primary_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
                "same_approved_runtime_window_required": True,
                "exact_target_binding_required": True,
                "copy_to_offline_workspace_before_checker": True,
                "redaction_required_before_checker_intake": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "candidate_only": True,
                "non_evidence": True,
                "source_present": False,
                "source_material_present": False,
                "side_lane": True,
                "side_lane_non_counting": True,
                "may_queue_with_primary_window": True,
                "primary_route_acceptance_required_before_counting": True,
                "own_checker_required_before_surface_claim": True,
                "blocked_by_player_principal_evidence": True,
                "requires_player_principal_triplet": True,
                "requires_checker_acceptance": True,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "replaces_player_principal_evidence": False,
                "replaces_player_principal_triplet": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "primary_evidence_substitution_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "action_boundary": NO_RESTART_ACTION_BOUNDARY,
                **no_restart_action_boundary(),
            }
        )

    return {
        "id": SIDE_LANE_CAPTURE_QUEUE_ID,
        "status": SIDE_LANE_CAPTURE_QUEUE_STATUS,
        "queue_status": "candidate_only_non_evidence",
        "target": target,
        "target_binding": target_binding_row,
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_window_binding,
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "correlation_field_ids": lifecycle_correlation_field_ids(),
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "primary_surface_id": "player_principal_lifecycle",
        "primary_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_primary_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "required_primary_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
        "surface_ids": list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
        "action_group_ids": list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS),
        "row_count": len(queue_rows),
        "rows": queue_rows,
        "queue_summary": (
            "queue optional side-lane candidate artifacts during the separately approved "
            "player-principal lifecycle window, but keep every row non-counting until "
            "the primary route accepts and the row's own checker accepts copied offline input"
        ),
        "same_approved_runtime_window_required": True,
        "exact_target_binding_required": True,
        "copy_to_offline_workspace_before_checker": True,
        "redaction_required_before_checker_intake": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "candidate_only": True,
        "non_evidence": True,
        "source_present": False,
        "source_material_present": False,
        "side_lane_non_counting": True,
        "primary_route_acceptance_required_before_counting": True,
        "own_checker_required_before_surface_claim": True,
        "blocked_by_player_principal_evidence": True,
        "requires_player_principal_triplet": True,
        "requires_checker_acceptance": True,
        "pack_authorizes_player_backed_window": False,
        "pack_authorizes_runtime_observer": False,
        "pack_authorizes_marker_or_env_change": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "primary_evidence_substitution_allowed": False,
        "side_lane_collection_can_replace_player_principal_evidence": False,
        "side_lane_collection_counts_before_checker_acceptance": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "non_claim_flags": non_claim_flags(),
        "non_substitution_flags": non_substitution_flags(),
        "action_boundary": NO_RESTART_ACTION_BOUNDARY,
        **no_restart_action_boundary(),
    }


def beta_capture_domain_for_surface(surface_id: str) -> str:
    if surface_id == "player_principal_lifecycle":
        return "player_principal"
    for domain, surface_ids in PARALLEL_BETA_CAPTURE_DOMAINS:
        if surface_id in surface_ids:
            return domain
    raise SystemExit(f"internal beta capture domain missing for {surface_id}")


def exact_capture_objectives(
    surfaces: list[dict[str, Any]],
    target: dict[str, str],
) -> dict[str, Any]:
    rows = []
    for surface in surfaces:
        surface_id = surface["id"]
        side_lane = surface_id != "player_principal_lifecycle"
        rows.append(
            {
                "order": surface["priority"],
                "surface_id": surface_id,
                "domain_id": beta_capture_domain_for_surface(surface_id),
                "action_group_id": action_group_template_for_surface(surface_id)["id"],
                "objective": surface["objective"],
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "tester_brief": action_group_template_for_surface(surface_id)["tester_brief"],
                "checker": surface["checker"],
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface[
                    "approved_runtime_window_binding"
                ],
                "candidate_artifact_count": surface["candidate_artifact_count"],
                "candidate_artifact_ids": [
                    artifact["id"] for artifact in surface["capture_artifacts"]
                ],
                "same_approved_runtime_window_required": True,
                "exact_target_binding_required": True,
                "no_flood_capture_policy": no_flood_capture_policy(),
                "no_flood": True,
                "one_request_row_per_surface_per_approved_window": True,
                "candidate_only": True,
                "non_evidence": True,
                "status_only": True,
                "source_present": False,
                "source_material_present": False,
                "side_lane": side_lane,
                "optional_parallel_candidate_observation": side_lane,
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "blocked_by_player_principal_evidence": True,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "authorizes_discord_send": False,
                "authorizes_runtime_capture": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
            }
        )
    return {
        "schema": EXACT_CAPTURE_OBJECTIVES_SCHEMA,
        "status": "exact_objectives_candidate_only_non_evidence",
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "surface_ids": [surface["id"] for surface in surfaces],
        "objective_count": len(rows),
        "objective_rows": rows,
        "primary_surface_id": "player_principal_lifecycle",
        "primary_strict_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "candidate_only": True,
        "non_evidence": True,
        "status_only": True,
        "source_present": False,
        "source_material_present": False,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "authorizes_discord_send": False,
        "authorizes_runtime_capture": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "non_claim_flags": non_claim_flags(),
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    surface_ids = [surface["id"] for surface in SURFACES]
    if len(surface_ids) != len(set(surface_ids)):
        raise SystemExit("internal duplicate capture surface id")
    if set(surface_ids) != set(CAPTURE_ARTIFACTS_BY_SURFACE):
        raise SystemExit("internal capture artifact surface set mismatch")
    validate_beta_tester_action_group_templates(surface_ids)
    target = {"instance": args.instance, "map": args.map}
    surfaces = [surface_entry(surface, index + 1, target) for index, surface in enumerate(SURFACES)]
    action_groups = beta_tester_next_action_groups(surfaces)
    broad_path = broad_beta_capture_pack_path(surfaces, target)
    parallel_matrix = parallel_beta_capture_side_lane_matrix(surfaces, target)
    single_player_sequence = single_player_parallel_capture_sequence(surfaces, target)
    checker_commands = target_bound_checker_command_matrix(surfaces, target)
    queue = side_lane_capture_queue(surfaces, target)
    exact_objectives = exact_capture_objectives(surfaces, target)
    plan = {
        "schema": SCHEMA,
        "status": "candidate_capture_plan",
        "target": target,
        "target_binding": target_binding(target),
        "target_binding_id": target_binding_id(target),
        "approved_runtime_window_binding": approved_runtime_window_binding(target),
        "server_policy": {
            "keep_servers_running_when_practical": True,
            "max_ark_servers_running": 2,
            "no_restart_from_pack": True,
            "pack_authorizes_restart": False,
            "pack_authorizes_live_log_reads": False,
            "maintenance_restarts_out_of_scope": True,
            "keep_transfer_server_when_practical": True,
        },
        "required_primary_evidence": {
            "surface": "player_principal_lifecycle",
            "strict_triplet": STRICT_PLAYER_PRINCIPAL_TRIPLET,
            "must_be_checker_accepted": True,
            "required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        },
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "capture_surfaces": surfaces,
        "broad_beta_capture_pack_path": broad_path,
        "parallel_beta_capture_side_lane_matrix": parallel_matrix,
        "single_player_parallel_capture_sequence": single_player_sequence,
        "target_bound_checker_command_matrix": checker_commands,
        "side_lane_capture_queue": queue,
        "exact_capture_objectives": exact_objectives,
        "single_beta_session_intent": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "no_flood": True,
        "beta_capture_interaction_boundary": beta_capture_interaction_boundary(),
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "text_privacy_boundary": text_privacy_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(target),
        "practical_beta_session_objectives": {
            "primary_first": STRICT_PLAYER_PRINCIPAL_TRIPLET,
            "side_lane_collection": (
                "collect redacted admin, command, dino, tribe, buff, inventory, item, "
                "transfer, and mission candidates only where their checkers already gate intake"
            ),
            "player_principal_window_composition": (
                "side surfaces are optional parallel candidate observations inside the "
                "separately approved player-principal lifecycle window; they remain "
                "non-evidence until their own checkers accept copied offline artifacts"
            ),
            "same_approved_runtime_window": (
                "every side-lane artifact must bind to the same approved runtime window, "
                "instance, and map as the primary player-principal lifecycle evidence"
            ),
            "lifecycle_correlation_metadata": (
                "record the same redacted side-lane correlation id, lifecycle phase anchor, "
                "event label, and optional integer offset on side-lane worksheets so admin, "
                "commands, dino, tribe, buff, inventory, transfer, and mission observations can be matched back to the "
                "approved player-principal window without retaining raw player text or "
                "claiming evidence"
            ),
            "operator_focus": [
                "one tester for the primary player-principal lifecycle triplet",
                "one admin tester for redacted admin and command routes",
                "one world-state tester for dino, tribe, and buff scalar observations",
                "one inventory tester for benign item and inventory metadata",
                "one transfer tester only when a transfer server is available",
                "one mission tester for safe mission copied-bool observations",
            ],
            "claim_boundary": (
                "side-lane artifacts remain non-evidence until their own checker accepts "
                "and never replace approved player-principal lifecycle evidence"
            ),
            "broad_status_only_path": (
                "admin/commands/dino/tribe/buff candidate capture is prepared as one "
                "status-only path for a single beta session; it remains non-evidence "
                "and non-readiness until copied offline artifacts pass their own checkers"
            ),
            "parallel_side_lane_matrix": (
                "admin/commands/dino/tribe/buff/inventory/item/transfer/mission candidates are bound "
                "as one status-only side-lane matrix for parallel beta collection; every "
                "row requires the same approved player-principal lifecycle window and exact "
                "target binding"
            ),
            "single_player_parallel_capture_sequence": (
                "one tester can run the primary player-principal sequence and then collect "
                "admin/commands/dino/tribe/buff/inventory/item/transfer/mission side-lane candidates "
                "in ordered phases, with redacted metadata only, no restart authority, no "
                "Discord sends, and no approved_runtime_evidence_missing clearance"
            ),
            "target_bound_checker_command_matrix": (
                "checker command placeholders are resolved to candidate-artifact templates "
                "bound to the same instance, map, and approved player-principal lifecycle "
                "window; scalar inputs remain read-text templates for copied offline files"
            ),
            "side_lane_capture_queue": (
                "testers get target-bound queue rows for each side lane, but every row "
                "remains blocked by approved_runtime_evidence_missing and non-counting "
                "until the primary route and the row's own checker accept"
            ),
            "exact_capture_objectives": (
                "one exact objective row is emitted for each surface, bound to the target "
                "and approved runtime window template, with source_present=false and "
                "candidate-only non-evidence flags"
            ),
            "no_flood": (
                "tester requests are batched by action group and deduped by approved "
                "window, target binding, surface, and side_lane_correlation_id"
            ),
        },
        "artifact_intake_constraints": artifact_intake_constraints(),
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups": action_groups,
        "non_claim_flags": non_claim_flags(),
        "next_action": "prepare_gated_observers_and_beta_script_for_all_candidate_surfaces",
    }
    return attach_source_metadata(plan, target)


def emit_text(plan: dict[str, Any]) -> str:
    candidate_artifact_count = sum(surface["candidate_artifact_count"] for surface in plan["capture_surfaces"])
    excluded_surfaces = (
        ",".join(plan["single_player_parallel_capture_sequence"]["excluded_surface_ids"])
        or "none"
    )
    lines = [
        "multi_surface_beta_capture_plan=candidate_only",
        f"target={plan['target']['instance']}/{plan['target']['map']}",
        f"required_primary_evidence={STRICT_PLAYER_PRINCIPAL_TRIPLET}",
        f"current_route_blocker={CURRENT_ROUTE_BLOCKER}",
        f"next_required_artifact={REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE}",
        f"candidate_artifact_templates={candidate_artifact_count}",
        f"broad_beta_capture_pack_path={plan['broad_beta_capture_pack_path']['id']}",
        (
            "broad_beta_capture_surfaces="
            f"{','.join(plan['broad_beta_capture_pack_path']['surface_ids'])}"
        ),
        "broad_beta_capture_status=status_only_candidate_non_evidence",
        f"parallel_beta_capture_matrix={plan['parallel_beta_capture_side_lane_matrix']['id']}",
        (
            "parallel_beta_capture_surfaces="
            f"{','.join(plan['parallel_beta_capture_side_lane_matrix']['surface_ids'])}"
        ),
        "parallel_beta_capture_status=status_only_candidate_non_evidence",
        f"single_player_parallel_capture_sequence={plan['single_player_parallel_capture_sequence']['id']}",
        "single_player_parallel_capture_status=status_only_candidate_non_evidence",
        (
            "single_player_parallel_capture_surfaces="
            f"{','.join(plan['single_player_parallel_capture_sequence']['surface_ids'])}"
        ),
        (
            "single_player_parallel_capture_domains="
            f"{','.join(plan['single_player_parallel_capture_sequence']['candidate_domain_ids'])}"
        ),
        (
            "single_player_route_excluded_surfaces="
            f"{excluded_surfaces}"
        ),
        f"target_bound_checker_command_matrix={plan['target_bound_checker_command_matrix']['id']}",
        "target_bound_checker_command_matrix_status=offline_command_templates_candidate_only",
        f"side_lane_capture_queue={plan['side_lane_capture_queue']['id']}",
        "side_lane_capture_queue_status=queued_candidate_observations_non_counting",
        f"exact_capture_objectives={plan['exact_capture_objectives']['objective_count']}",
        "no_flood_capture_policy=single_window_no_flood_candidate_capture_policy",
        "no_flood=true",
        "source_present=false",
        "server_policy=max_2 keep_running_when_practical no_restart_from_pack",
        "raw_player_text_retention_allowed=false",
        "secrets_or_webhook_retention_allowed=false",
        "single_player_route_redacted_metadata_only=true",
        "single_player_route_no_restart=true",
        "single_player_route_no_discord=true",
        "single_player_route_clears_approved_runtime_evidence_missing=false",
        "beta_interactions_approve_live_actions=false",
        "beta_interactions_count_as_sdk_progress=false",
        "beta_interactions_grant_public_sdk_readiness=false",
        "beta_interactions_grant_stable_readiness=false",
        "parallel_with_player_principal_lifecycle_window_planned=true",
        "side_surfaces_grouped_as_optional_parallel_candidate_observations=true",
        "side_surfaces_non_evidence_until_own_checker_acceptance=true",
        "same_approved_runtime_window_required=true",
        f"lifecycle_correlation_metadata={plan['lifecycle_correlation_metadata']['status']}",
        "lifecycle_correlation_fields=approved_window_id,side_lane_correlation_id,primary_lifecycle_phase_anchor,primary_lifecycle_event_reference,relative_lifecycle_offset_seconds,operator_sequence_index",
        "lifecycle_correlation_metadata_counts_as_runtime_evidence=false",
        "separate_player_backed_window_approval_required=true",
        "pack_authorizes_player_backed_window=false",
        "side_lane_collection_can_replace_player_principal_evidence=false",
        "counts_as_approved_runtime_evidence=false",
        "counts_as_sdk_progress=false",
        "runtime_ready=false",
        "public_sdk_ready=false",
        "next_action_groups:",
    ]
    for group in plan["next_action_groups"]:
        lines.append(
            f"- {group['id']}: surfaces={','.join(group['surface_ids'])} "
            f"lead_next_action={group['lead_next_action']} tester_brief={group['tester_brief']}"
        )
    lines.extend(
        [
            "capture_surfaces:",
        ]
    )
    for surface in plan["capture_surfaces"]:
        lines.append(
            f"- {surface['id']}: checker={surface['checker']} "
            f"candidate_artifacts={surface['candidate_artifact_count']} objective={surface['objective']} "
            f"tester_action={surface['tester_action']}"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.instance = validate_token(args.instance, "--instance")
    args.map = validate_token(args.map, "--map", SAFE_MAP_RE)
    return args


def main() -> int:
    args = parse_args()
    plan = build_plan(args)
    if plan.get("schema") != SCHEMA:
        raise SystemExit("internal schema mismatch")
    surface_ids = [surface["id"] for surface in plan["capture_surfaces"]]
    if len(surface_ids) != len(set(surface_ids)):
        raise SystemExit("internal duplicate capture surface id")
    priorities = [surface["priority"] for surface in plan["capture_surfaces"]]
    if priorities != list(range(1, len(plan["capture_surfaces"]) + 1)):
        raise SystemExit("internal capture surface priority mismatch")
    if any(surface["non_claim_flags"] != NON_CLAIM_FLAGS for surface in plan["capture_surfaces"]):
        raise SystemExit("internal non-claim flag mismatch")
    if plan.get("parallel_capture_boundary") != PARALLEL_CAPTURE_BOUNDARY:
        raise SystemExit("internal parallel capture boundary mismatch")
    if any(group.get("parallel_capture_boundary") != PARALLEL_CAPTURE_BOUNDARY for group in plan["next_action_groups"]):
        raise SystemExit("internal next-action group parallel capture boundary mismatch")
    if plan.get("broad_beta_capture_pack_path") != attach_source_metadata(
        broad_beta_capture_pack_path(plan["capture_surfaces"], plan["target"]),
        plan["target"],
    ):
        raise SystemExit("internal broad beta capture pack path mismatch")
    if plan.get("parallel_beta_capture_side_lane_matrix") != attach_source_metadata(
        parallel_beta_capture_side_lane_matrix(plan["capture_surfaces"], plan["target"]),
        plan["target"],
    ):
        raise SystemExit("internal parallel beta capture side-lane matrix mismatch")
    if plan.get("single_player_parallel_capture_sequence") != attach_source_metadata(
        single_player_parallel_capture_sequence(plan["capture_surfaces"], plan["target"]),
        plan["target"],
    ):
        raise SystemExit("internal single-player parallel capture sequence mismatch")
    if plan.get("target_bound_checker_command_matrix") != attach_source_metadata(
        target_bound_checker_command_matrix(plan["capture_surfaces"], plan["target"]),
        plan["target"],
    ):
        raise SystemExit("internal target-bound checker command matrix mismatch")
    if plan.get("side_lane_capture_queue") != attach_source_metadata(
        side_lane_capture_queue(plan["capture_surfaces"], plan["target"]),
        plan["target"],
    ):
        raise SystemExit("internal side-lane capture queue mismatch")
    if plan.get("text_privacy_boundary") != text_privacy_boundary():
        raise SystemExit("internal text privacy boundary mismatch")
    if plan["broad_beta_capture_pack_path"].get("surface_ids") != list(BROAD_BETA_CAPTURE_SURFACE_IDS):
        raise SystemExit("internal broad beta capture surface path mismatch")
    if plan["parallel_beta_capture_side_lane_matrix"].get("surface_ids") != list(
        PARALLEL_BETA_CAPTURE_SURFACE_IDS
    ):
        raise SystemExit("internal parallel beta capture surface matrix mismatch")
    if any(
        group.get("approved_runtime_window_binding") != plan["approved_runtime_window_binding"]
        for group in plan["next_action_groups"]
    ):
        raise SystemExit("internal next-action group approved runtime window binding mismatch")
    if any(
        surface.get("parallel_capture_boundary") != PARALLEL_CAPTURE_BOUNDARY
        for surface in plan["capture_surfaces"]
    ):
        raise SystemExit("internal surface parallel capture boundary mismatch")
    if any(
        surface.get("approved_runtime_window_binding") != plan["approved_runtime_window_binding"]
        for surface in plan["capture_surfaces"]
    ):
        raise SystemExit("internal surface approved runtime window binding mismatch")
    if any(
        artifact["non_claim_flags"] != NON_CLAIM_FLAGS
        for surface in plan["capture_surfaces"]
        for artifact in surface["capture_artifacts"]
    ):
        raise SystemExit("internal capture artifact non-claim flag mismatch")
    if any(
        artifact.get("parallel_capture_boundary") != PARALLEL_CAPTURE_BOUNDARY
        for surface in plan["capture_surfaces"]
        for artifact in surface["capture_artifacts"]
    ):
        raise SystemExit("internal capture artifact parallel capture boundary mismatch")
    if any(
        artifact.get("approved_runtime_window_binding") != plan["approved_runtime_window_binding"]
        for surface in plan["capture_surfaces"]
        for artifact in surface["capture_artifacts"]
    ):
        raise SystemExit("internal capture artifact approved runtime window binding mismatch")
    if any(
        surface.get("target_bound_checker_command") != attach_source_metadata(
            target_bound_checker_command_row(surface),
            plan["target"],
        )
        for surface in plan["capture_surfaces"]
    ):
        raise SystemExit("internal surface target-bound checker command mismatch")
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(emit_text(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
