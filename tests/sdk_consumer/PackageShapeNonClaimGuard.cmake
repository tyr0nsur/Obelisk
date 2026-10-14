cmake_minimum_required(VERSION 3.22)

foreach(required_var IN ITEMS
    OBELISK_BUILD_CMAKE_PACKAGE_DIR
    OBELISK_PACKAGE_SHAPE_GUARD_WORK_DIR
)
    if(NOT DEFINED ${required_var} OR "${${required_var}}" STREQUAL "")
        message(FATAL_ERROR "Missing required ${required_var}")
    endif()
endforeach()

set(obelisk_config "${OBELISK_BUILD_CMAKE_PACKAGE_DIR}/ObeliskConfig.cmake")
set(obelisk_config_version "${OBELISK_BUILD_CMAKE_PACKAGE_DIR}/ObeliskConfigVersion.cmake")
if(NOT EXISTS "${obelisk_config}")
    message(FATAL_ERROR "Missing generated ObeliskConfig.cmake: ${obelisk_config}")
endif()
if(NOT EXISTS "${obelisk_config_version}")
    message(FATAL_ERROR
        "Missing generated ObeliskConfigVersion.cmake: ${obelisk_config_version}")
endif()

set(work_dir "${OBELISK_PACKAGE_SHAPE_GUARD_WORK_DIR}")
file(REMOVE_RECURSE "${work_dir}")
file(MAKE_DIRECTORY "${work_dir}")

set(package_root "${work_dir}/package")
set(package_cmake_dir "${package_root}/lib/cmake/Obelisk")
execute_process(
    COMMAND
        "${CMAKE_COMMAND}"
        --install "${OBELISK_BUILD_CMAKE_PACKAGE_DIR}"
        --component SDK
        --prefix "${package_root}"
    RESULT_VARIABLE install_result
    OUTPUT_VARIABLE install_stdout
    ERROR_VARIABLE install_stderr
)
if(NOT install_result EQUAL 0)
    message(FATAL_ERROR
        "SDK component temp install failed with ${install_result}\n"
        "stdout:\n${install_stdout}\n"
        "stderr:\n${install_stderr}")
endif()

foreach(required_installed_file IN ITEMS
    include/obelisk/ObeliskApi.h
    lib/cmake/Obelisk/ObeliskConfig.cmake
    lib/cmake/Obelisk/ObeliskConfigVersion.cmake
    lib/cmake/Obelisk/ObeliskTargets.cmake
)
    if(NOT EXISTS "${package_root}/${required_installed_file}")
        message(FATAL_ERROR
            "SDK component temp install missed required package-shape file: "
            "${required_installed_file}")
    endif()
endforeach()

foreach(forbidden_installed_file IN ITEMS
    lib/libobelisk.so
    plugins/oBaseEvents.so
    plugins/oProcessTimer.so
    plugins/oDescriptorCatalog.so
)
    if(EXISTS "${package_root}/${forbidden_installed_file}")
        message(FATAL_ERROR
            "SDK component temp install leaked runtime/plugin artifact: "
            "${forbidden_installed_file}")
    endif()
endforeach()

function(obelisk_configure_package_case case_name cmake_content)
    set(source_dir "${work_dir}/${case_name}/source")
    set(binary_dir "${work_dir}/${case_name}/build")
    file(MAKE_DIRECTORY "${source_dir}")
    file(WRITE "${source_dir}/CMakeLists.txt" "${cmake_content}")

    execute_process(
        COMMAND
            "${CMAKE_COMMAND}"
            -S "${source_dir}"
            -B "${binary_dir}"
            "-DObelisk_DIR=${package_cmake_dir}"
            "-DCMAKE_PREFIX_PATH=${package_root}"
            "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=FALSE"
            "-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=FALSE"
        RESULT_VARIABLE configure_result
        OUTPUT_VARIABLE configure_stdout
        ERROR_VARIABLE configure_stderr
    )
    if(NOT configure_result EQUAL 0)
        message(FATAL_ERROR
            "Package-shape guard case ${case_name} failed with ${configure_result}\n"
            "stdout:\n${configure_stdout}\n"
            "stderr:\n${configure_stderr}")
    endif()
endfunction()

function(obelisk_build_package_case case_name cmake_content)
    set(source_dir "${work_dir}/${case_name}/source")
    set(binary_dir "${work_dir}/${case_name}/build")
    file(MAKE_DIRECTORY "${source_dir}")
    file(COPY "${CMAKE_CURRENT_LIST_DIR}/AbiLayoutGuard.c" DESTINATION "${source_dir}")
    file(WRITE "${source_dir}/CMakeLists.txt" "${cmake_content}")

    execute_process(
        COMMAND
            "${CMAKE_COMMAND}"
            -S "${source_dir}"
            -B "${binary_dir}"
            "-DObelisk_DIR=${package_cmake_dir}"
            "-DCMAKE_PREFIX_PATH=${package_root}"
            "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=FALSE"
            "-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=FALSE"
        RESULT_VARIABLE configure_result
        OUTPUT_VARIABLE configure_stdout
        ERROR_VARIABLE configure_stderr
    )
    if(NOT configure_result EQUAL 0)
        message(FATAL_ERROR
            "Package-shape build case ${case_name} configure failed with ${configure_result}\n"
            "stdout:\n${configure_stdout}\n"
            "stderr:\n${configure_stderr}")
    endif()

    execute_process(
        COMMAND
            "${CMAKE_COMMAND}"
            --build "${binary_dir}"
            --target package_abi_layout_guard
        RESULT_VARIABLE build_result
        OUTPUT_VARIABLE build_stdout
        ERROR_VARIABLE build_stderr
    )
    if(NOT build_result EQUAL 0)
        message(FATAL_ERROR
            "Package-shape build case ${case_name} build failed with ${build_result}\n"
            "stdout:\n${build_stdout}\n"
            "stderr:\n${build_stderr}")
    endif()

    execute_process(
        COMMAND
            "${CMAKE_CTEST_COMMAND}"
            --test-dir "${binary_dir}"
            --output-on-failure
            -R "^PackageAbiLayoutGuard$"
        RESULT_VARIABLE test_result
        OUTPUT_VARIABLE test_stdout
        ERROR_VARIABLE test_stderr
    )
    if(NOT test_result EQUAL 0)
        message(FATAL_ERROR
            "Package-shape build case ${case_name} test failed with ${test_result}\n"
            "stdout:\n${test_stdout}\n"
            "stderr:\n${test_stderr}")
    endif()
endfunction()

obelisk_configure_package_case("exact_stable_rejected" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkExactStableRejected LANGUAGES NONE)

find_package(Obelisk 0.1.0 EXACT CONFIG QUIET COMPONENTS SDK)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Obelisk package accepted an EXACT stable-looking SDK request")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Rejected EXACT SDK request leaked Obelisk::obelisk_sdk")
endif()
]=])

obelisk_configure_package_case("versionless_rejected" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkVersionlessRejected LANGUAGES NONE)

find_package(Obelisk CONFIG QUIET COMPONENTS SDK)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Obelisk package accepted a versionless SDK request")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Rejected versionless SDK request leaked Obelisk::obelisk_sdk")
endif()
]=])

obelisk_configure_package_case("missing_sdk_component_rejected" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkMissingComponentRejected LANGUAGES NONE)

find_package(Obelisk 0.1.0 CONFIG QUIET)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Obelisk package accepted a request without COMPONENTS SDK")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Rejected missing-component request leaked Obelisk::obelisk_sdk")
endif()
]=])

obelisk_configure_package_case("unsupported_component_rejected" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkUnsupportedComponentRejected LANGUAGES NONE)

find_package(Obelisk 0.1.0 CONFIG QUIET COMPONENTS Runtime)
if(Obelisk_FOUND)
    message(FATAL_ERROR "Obelisk package accepted unsupported Runtime component")
endif()
if(TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Rejected unsupported-component request leaked Obelisk::obelisk_sdk")
endif()
]=])

obelisk_configure_package_case("sdk_package_shape_non_claim" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkPackageShapeNonClaim LANGUAGES NONE)

find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Obelisk package did not define Obelisk::obelisk_sdk")
endif()
get_target_property(sdk_target_type Obelisk::obelisk_sdk TYPE)
if(NOT sdk_target_type STREQUAL "INTERFACE_LIBRARY")
    message(FATAL_ERROR
        "Installed Obelisk::obelisk_sdk must stay interface-only, got: ${sdk_target_type}")
endif()
get_target_property(sdk_include_dirs Obelisk::obelisk_sdk INTERFACE_INCLUDE_DIRECTORIES)
if(NOT sdk_include_dirs OR sdk_include_dirs STREQUAL "sdk_include_dirs-NOTFOUND")
    message(FATAL_ERROR "Installed Obelisk::obelisk_sdk did not expose include directories")
endif()
foreach(sdk_include_dir IN LISTS sdk_include_dirs)
    if(NOT EXISTS "${sdk_include_dir}/obelisk/ObeliskApi.h")
        message(FATAL_ERROR
            "Installed Obelisk::obelisk_sdk include dir does not contain ObeliskApi.h: "
            "${sdk_include_dir}")
    endif()
endforeach()
foreach(forbidden_property IN ITEMS
    IMPORTED_IMPLIB
    IMPORTED_LINK_DEPENDENT_LIBRARIES
    IMPORTED_LOCATION
    IMPORTED_OBJECTS
    IMPORTED_SONAME
    INTERFACE_COMPILE_DEFINITIONS
    INTERFACE_COMPILE_OPTIONS
    INTERFACE_LINK_LIBRARIES
    INTERFACE_LINK_OPTIONS
    INTERFACE_SOURCES
    INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
)
    get_target_property(forbidden_value Obelisk::obelisk_sdk ${forbidden_property})
    if(forbidden_value AND NOT forbidden_value STREQUAL "forbidden_value-NOTFOUND")
        message(FATAL_ERROR
            "Installed Obelisk::obelisk_sdk must not expose ${forbidden_property}: "
            "${forbidden_value}")
    endif()
endforeach()
if(NOT Obelisk_SDK_FOUND)
    message(FATAL_ERROR "Obelisk package did not mark SDK component found")
endif()
if(NOT Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS STREQUAL "package-shape-evidence-only")
    message(FATAL_ERROR
        "Obelisk package status must remain package-shape-evidence-only, got "
        "${Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS}")
endif()
if(NOT Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY)
    message(FATAL_ERROR "Obelisk package did not mark find_package SDK as package-shape-only")
endif()
if(NOT Obelisk_SDK_BLOCKER_PROMOTION_COUNT EQUAL 0 OR
   NOT Obelisk_SDK_BLOCKER_PROMOTION_TOTAL EQUAL 12)
    message(FATAL_ERROR
        "Obelisk SDK blocker counters must remain 0/12 for package-shape success, got "
        "${Obelisk_SDK_BLOCKER_PROMOTION_COUNT}/${Obelisk_SDK_BLOCKER_PROMOTION_TOTAL}")
endif()
if(NOT Obelisk_P0_DEPENDENCY_COUNT EQUAL 0 OR
   NOT Obelisk_P0_DEPENDENCY_TOTAL EQUAL 4)
    message(FATAL_ERROR
        "Obelisk P0 dependency counters must remain 0/4 for package-shape success, got "
        "${Obelisk_P0_DEPENDENCY_COUNT}/${Obelisk_P0_DEPENDENCY_TOTAL}")
endif()
if(NOT Obelisk_ACTIVE_COMPLETION_BLOCKER STREQUAL "approved_runtime_evidence_missing")
    message(FATAL_ERROR
        "Obelisk package-shape success must keep the active completion blocker, got "
        "${Obelisk_ACTIVE_COMPLETION_BLOCKER}")
endif()

foreach(false_var IN ITEMS
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
    if(NOT DEFINED ${false_var})
        message(FATAL_ERROR "Obelisk package did not define non-claim marker ${false_var}")
    endif()
    if(${${false_var}})
        message(FATAL_ERROR "Obelisk package enabled forbidden non-claim marker ${false_var}")
    endif()
endforeach()

foreach(undefined_or_false_var IN ITEMS
    Obelisk_ABI_LAYOUT_READY
    Obelisk_ABI_LAYOUT_VALIDATED
    Obelisk_ACCEPTED_FOR_CONTRACT_REVIEW
    Obelisk_APPROVED_RUNTIME_BUNDLE_ACCEPTED
    Obelisk_APPROVED_RUNTIME_EVIDENCE_ACCEPTED
    Obelisk_C_ABI_READY
    Obelisk_STRUCT_SIZE_READY
    Obelisk_STRUCT_SIZE_VALIDATED
    Obelisk_CMAKE_PACKAGE_READY
    Obelisk_INSTALLED_HEADERS_READY
    Obelisk_INSTALLED_SDK_CONSUMER_TESTS_READY
    Obelisk_INSTALLED_SDK_PACKAGE_READY
    Obelisk_OWNER_TOKEN_LIFECYCLE_READY
    Obelisk_OWNER_TOKEN_SDK_CONSUMER_READY
    Obelisk_PACKAGE_AVAILABLE
    Obelisk_PACKAGE_PUBLICATION_ALLOWED
    Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_COMPLETION
    Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_PUBLIC_SDK
    Obelisk_PACKAGE_SHAPE_COUNTS_TOWARD_V1_COMPLETION
    Obelisk_PACKAGE_SHAPE_READY
    Obelisk_PUBLIC_ABI_AVAILABLE
    Obelisk_PUBLIC_CONTRACT_REVIEW_ACCEPTED
    Obelisk_PUBLIC_HEADER_GATE_OPEN
    Obelisk_PUBLIC_HEADER_GATE_PASSED
    Obelisk_PUBLIC_HEADER_GATE_READY
    Obelisk_HEADER_PROMOTION_GATE_OPEN
    Obelisk_HEADER_PROMOTION_GATE_PASSED
    Obelisk_HEADER_PROMOTION_GATE_READY
    Obelisk_PUBLIC_HEADER_ALLOWED
    Obelisk_PUBLIC_HEADER_PROMOTION_GATE_OPEN
    Obelisk_PUBLIC_HEADER_PROMOTION_GATE_PASSED
    Obelisk_PUBLIC_HEADER_PROMOTION_GATE_READY
    Obelisk_PUBLIC_HEADER_READY
    Obelisk_PUBLIC_HEADERS_READY
    Obelisk_PUBLIC_PACKAGE_AVAILABLE
    Obelisk_PUBLIC_PACKAGE_READY
    Obelisk_PUBLIC_SDK_READY
    Obelisk_COMPLETE_SDK_READY
    Obelisk_COMPLETE_SDK_V1_READY
    Obelisk_SDK_COMPLETE
    Obelisk_SDK_V1_COMPLETE
    Obelisk_V1_SDK_COMPLETE
    Obelisk_IDENTITY_P0_DEPENDENCY_READY
    Obelisk_PLAYER_IDENTITY_P0_DEPENDENCY_READY
    Obelisk_PERMISSIONS_P0_DEPENDENCY_READY
    Obelisk_COMMANDS_P0_DEPENDENCY_READY
    Obelisk_IDENTITY_DEPENDENCY_READY
    Obelisk_PLAYER_IDENTITY_DEPENDENCY_READY
    Obelisk_PERMISSIONS_DEPENDENCY_READY
    Obelisk_COMMANDS_DEPENDENCY_READY
    Obelisk_IDENTITY_PERMISSION_COMMANDS_DEPENDENCIES_READY
    Obelisk_PLAYER_IDENTITY_CONTRACT_REVIEW_ACCEPTED
    Obelisk_PLAYER_IDENTITY_OWNER_TOKEN_SDK_CONSUMER_READY
    Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_READY
    Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_PLAYER_IDENTITY_PUBLIC_ABI_READY
    Obelisk_PLAYER_IDENTITY_PUBLIC_HEADER_ALLOWED
    Obelisk_PLAYER_IDENTITY_RUNTIME_EVIDENCE_ACCEPTED
    Obelisk_PLAYER_PRINCIPAL_CONTRACT_REVIEW_ACCEPTED
    Obelisk_PLAYER_PRINCIPAL_LIFECYCLE_READY
    Obelisk_PLAYER_PRINCIPAL_OWNER_TOKEN_SDK_CONSUMER_READY
    Obelisk_PLAYER_PRINCIPAL_PUBLIC_ABI_READY
    Obelisk_PLAYER_PRINCIPAL_PUBLIC_HEADER_ALLOWED
    Obelisk_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE_ACCEPTED
    Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_READY
    Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_READY
    Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_READY
    Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_POST_IDENTITY_BRIDGE_READY
    Obelisk_POST_IDENTITY_BRIDGE_PROMOTION_READY
    Obelisk_POST_IDENTITY_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_POST_IDENTITY_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_READY
    Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_PROMOTION_READY
    Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_READY
    Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_PROMOTION_READY
    Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_COMMANDS_REPLIES_FINAL_GATE_READY
    Obelisk_COMMANDS_REPLIES_FINAL_GATE_PROMOTION_READY
    Obelisk_COMMANDS_REPLIES_FINAL_GATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_COMMANDS_REPLIES_FINAL_GATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_BRIDGE_REPORT_READY
    Obelisk_BUILDER_REPORT_READY
    Obelisk_PROMOTION_CERTIFICATE_BUILDER_REPORT_READY
    Obelisk_P0_OFFLINE_ROADMAP_READY
    Obelisk_P0_OFFLINE_ROADMAP_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_P0_OFFLINE_ROADMAP_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_SDK_STATUS_REPORT_READY
    Obelisk_SDK_STATUS_REPORT_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_SDK_STATUS_REPORT_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_STATUS_REPORT_READY
    Obelisk_STATUS_REPORT_COUNTS_TOWARD_COMPLETE_SDK_CLAIM
    Obelisk_STATUS_REPORT_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN
    Obelisk_RESOURCE_HANDLE_IDENTITY_READY
    Obelisk_RESOURCE_MUTATION_READY
    Obelisk_MUTATION_READY
    Obelisk_RESOURCE_MUTABLE_READY
    Obelisk_MUTABLE_RESOURCE_READY
    Obelisk_RESOURCE_WRITE_READY
    Obelisk_RETURN_OVERRIDE_READY
    Obelisk_RETURN_OVERRIDES_READY
    Obelisk_CALL_PROCESS_EVENT_ABI_VERSION
    Obelisk_PUBLIC_CALL_PROCESS_EVENT_ABI_VERSION
    Obelisk_STABLE_CALL_PROCESS_EVENT_ABI_VERSION
    Obelisk_PROCESS_EVENT_PUBLIC_ABI_VERSION
    Obelisk_PROCESS_EVENT_STABLE_ABI_VERSION
    Obelisk_RAW_PROCESS_EVENT_ABI_VERSION
    Obelisk_RAW_PROCESS_EVENT_PUBLIC_ABI_VERSION
    Obelisk_PUBLIC_CALL_PROCESS_EVENT_READY
    Obelisk_STABLE_CALL_PROCESS_EVENT_READY
    Obelisk_CALL_PROCESS_EVENT_PUBLIC_READY
    Obelisk_CALL_PROCESS_EVENT_STABLE_READY
    Obelisk_RAW_PROCESS_EVENT_READY
    Obelisk_RAW_PROCESS_EVENT_PUBLIC_READY
    Obelisk_PUBLIC_PROCESS_EVENT_READY
    Obelisk_PROCESS_EVENT_PUBLIC_READY
    Obelisk_PROCESS_EVENT_PUBLIC_SDK_READY
    Obelisk_PROCESS_EVENT_PUBLIC_CONTRACT_READY
    Obelisk_RAW_PROCESS_EVENT_PUBLIC_CONTRACT_READY
    Obelisk_PROCESS_EVENT_STABLE_SDK_READY
    Obelisk_PROCESS_EVENT_CALLBACKS_PUBLIC_READY
    Obelisk_RAW_PROCESS_EVENT_CALLBACKS_READY
    Obelisk_SDK_CONSUMER_TESTS_READY
    Obelisk_STABLE_SDK_READY
)
    if(DEFINED ${undefined_or_false_var} AND "${${undefined_or_false_var}}")
        message(FATAL_ERROR
            "Obelisk package exposed forbidden positive readiness alias "
            "${undefined_or_false_var}=${${undefined_or_false_var}}")
    endif()
endforeach()
]=])

obelisk_build_package_case("installed_package_abi_layout_guard" [=[
cmake_minimum_required(VERSION 3.22)
project(ObeliskInstalledPackageAbiLayoutGuard LANGUAGES C)

find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Obelisk package did not define Obelisk::obelisk_sdk")
endif()
if(NOT Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY)
    message(FATAL_ERROR "Installed package ABI guard must remain package-shape-only")
endif()
if(Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED OR
   Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED OR
   Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED OR
   Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED OR
   Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED OR
   Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS OR
   Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE OR
   Obelisk_ACCEPTED_FOR_CONTRACT_REVIEW OR
   Obelisk_APPROVED_RUNTIME_BUNDLE_ACCEPTED OR
   Obelisk_APPROVED_RUNTIME_EVIDENCE_ACCEPTED OR
   Obelisk_PUBLIC_CONTRACT_REVIEW_ACCEPTED OR
   Obelisk_PUBLIC_HEADER_GATE_OPEN OR
   Obelisk_PUBLIC_HEADER_GATE_PASSED OR
   Obelisk_PUBLIC_HEADER_GATE_READY OR
   Obelisk_HEADER_PROMOTION_GATE_OPEN OR
   Obelisk_HEADER_PROMOTION_GATE_PASSED OR
   Obelisk_HEADER_PROMOTION_GATE_READY OR
   Obelisk_PUBLIC_HEADER_PROMOTION_GATE_OPEN OR
   Obelisk_PUBLIC_HEADER_PROMOTION_GATE_PASSED OR
   Obelisk_PUBLIC_HEADER_PROMOTION_GATE_READY OR
   Obelisk_OWNER_TOKEN_LIFECYCLE_READY OR
   Obelisk_OWNER_TOKEN_SDK_CONSUMER_READY OR
   Obelisk_PLAYER_IDENTITY_OWNER_TOKEN_SDK_CONSUMER_READY OR
   Obelisk_PLAYER_IDENTITY_PUBLIC_ABI_READY OR
   Obelisk_PLAYER_IDENTITY_PUBLIC_HEADER_ALLOWED OR
   Obelisk_PLAYER_IDENTITY_RUNTIME_EVIDENCE_ACCEPTED OR
   Obelisk_PLAYER_IDENTITY_CONTRACT_REVIEW_ACCEPTED OR
   Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_READY OR
   Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_PLAYER_PRINCIPAL_OWNER_TOKEN_SDK_CONSUMER_READY OR
   Obelisk_PLAYER_PRINCIPAL_LIFECYCLE_READY OR
   Obelisk_PLAYER_PRINCIPAL_PUBLIC_ABI_READY OR
   Obelisk_PLAYER_PRINCIPAL_PUBLIC_HEADER_ALLOWED OR
   Obelisk_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE_ACCEPTED OR
   Obelisk_PLAYER_PRINCIPAL_CONTRACT_REVIEW_ACCEPTED OR
   Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_READY OR
   Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_READY OR
   Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_READY OR
   Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_COMMANDS_REPLIES_PROMOTION_CERTIFICATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_POST_IDENTITY_BRIDGE_READY OR
   Obelisk_POST_IDENTITY_BRIDGE_PROMOTION_READY OR
   Obelisk_POST_IDENTITY_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_POST_IDENTITY_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_READY OR
   Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_PROMOTION_READY OR
   Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_POST_PERMISSIONS_ADMIN_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_READY OR
   Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_PROMOTION_READY OR
   Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_POST_COMMAND_CHAT_RESPONSE_BRIDGE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_COMMANDS_REPLIES_FINAL_GATE_READY OR
   Obelisk_COMMANDS_REPLIES_FINAL_GATE_PROMOTION_READY OR
   Obelisk_COMMANDS_REPLIES_FINAL_GATE_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_COMMANDS_REPLIES_FINAL_GATE_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_BRIDGE_REPORT_READY OR
   Obelisk_BUILDER_REPORT_READY OR
   Obelisk_PROMOTION_CERTIFICATE_BUILDER_REPORT_READY OR
   Obelisk_P0_OFFLINE_ROADMAP_READY OR
   Obelisk_P0_OFFLINE_ROADMAP_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_P0_OFFLINE_ROADMAP_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_SDK_STATUS_REPORT_READY OR
   Obelisk_SDK_STATUS_REPORT_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_SDK_STATUS_REPORT_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_STATUS_REPORT_READY OR
   Obelisk_STATUS_REPORT_COUNTS_TOWARD_COMPLETE_SDK_CLAIM OR
   Obelisk_STATUS_REPORT_COUNTS_TOWARD_P0_DEPENDENCY_CHAIN OR
   Obelisk_RESOURCE_HANDLE_IDENTITY_READY OR
   Obelisk_RESOURCE_MUTATION_READY OR
   Obelisk_MUTATION_READY OR
   Obelisk_RESOURCE_MUTABLE_READY OR
   Obelisk_MUTABLE_RESOURCE_READY OR
   Obelisk_RESOURCE_WRITE_READY OR
   Obelisk_RETURN_OVERRIDE_READY OR
   Obelisk_RETURN_OVERRIDES_READY OR
   Obelisk_CALL_PROCESS_EVENT_ABI_VERSION OR
   Obelisk_PUBLIC_CALL_PROCESS_EVENT_ABI_VERSION OR
   Obelisk_STABLE_CALL_PROCESS_EVENT_ABI_VERSION OR
   Obelisk_PROCESS_EVENT_PUBLIC_ABI_VERSION OR
   Obelisk_PROCESS_EVENT_STABLE_ABI_VERSION OR
   Obelisk_RAW_PROCESS_EVENT_ABI_VERSION OR
   Obelisk_RAW_PROCESS_EVENT_PUBLIC_ABI_VERSION OR
   Obelisk_PUBLIC_CALL_PROCESS_EVENT_READY OR
   Obelisk_STABLE_CALL_PROCESS_EVENT_READY OR
   Obelisk_CALL_PROCESS_EVENT_PUBLIC_READY OR
   Obelisk_CALL_PROCESS_EVENT_STABLE_READY OR
   Obelisk_RAW_PROCESS_EVENT_READY OR
   Obelisk_RAW_PROCESS_EVENT_PUBLIC_READY OR
   Obelisk_PUBLIC_PROCESS_EVENT_READY OR
   Obelisk_PROCESS_EVENT_PUBLIC_READY OR
   Obelisk_PROCESS_EVENT_PUBLIC_SDK_READY OR
   Obelisk_PROCESS_EVENT_PUBLIC_CONTRACT_READY OR
   Obelisk_RAW_PROCESS_EVENT_PUBLIC_CONTRACT_READY OR
   Obelisk_PROCESS_EVENT_STABLE_SDK_READY OR
   Obelisk_PROCESS_EVENT_CALLBACKS_PUBLIC_READY OR
   Obelisk_RAW_PROCESS_EVENT_CALLBACKS_READY OR
   Obelisk_COMPLETE_SDK_READY OR
   Obelisk_COMPLETE_SDK_V1_READY OR
   Obelisk_SDK_COMPLETE OR
   Obelisk_SDK_V1_COMPLETE OR
   Obelisk_V1_SDK_COMPLETE OR
   Obelisk_IDENTITY_P0_DEPENDENCY_READY OR
   Obelisk_PLAYER_IDENTITY_P0_DEPENDENCY_READY OR
   Obelisk_PERMISSIONS_P0_DEPENDENCY_READY OR
   Obelisk_COMMANDS_P0_DEPENDENCY_READY OR
   Obelisk_IDENTITY_DEPENDENCY_READY OR
   Obelisk_PLAYER_IDENTITY_DEPENDENCY_READY OR
   Obelisk_PERMISSIONS_DEPENDENCY_READY OR
   Obelisk_COMMANDS_DEPENDENCY_READY OR
   Obelisk_IDENTITY_PERMISSION_COMMANDS_DEPENDENCIES_READY OR
   Obelisk_V1_COMPLETION_CLAIM_ALLOWED OR
   Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED OR
   Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED)
    message(FATAL_ERROR
        "Installed package ABI guard exposed public readiness or completion claim metadata")
endif()

get_target_property(sdk_target_type Obelisk::obelisk_sdk TYPE)
if(NOT sdk_target_type STREQUAL "INTERFACE_LIBRARY")
    message(FATAL_ERROR
        "Installed Obelisk::obelisk_sdk must stay interface-only, got: ${sdk_target_type}")
endif()
foreach(forbidden_property IN ITEMS
    IMPORTED_IMPLIB
    IMPORTED_LINK_DEPENDENT_LIBRARIES
    IMPORTED_LOCATION
    IMPORTED_OBJECTS
    IMPORTED_SONAME
    INTERFACE_COMPILE_DEFINITIONS
    INTERFACE_COMPILE_OPTIONS
    INTERFACE_LINK_LIBRARIES
    INTERFACE_LINK_OPTIONS
    INTERFACE_SOURCES
    INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
)
    get_target_property(forbidden_value Obelisk::obelisk_sdk ${forbidden_property})
    if(forbidden_value AND NOT forbidden_value STREQUAL "forbidden_value-NOTFOUND")
        message(FATAL_ERROR
            "Installed Obelisk::obelisk_sdk must not expose ${forbidden_property}: "
            "${forbidden_value}")
    endif()
endforeach()

add_executable(package_abi_layout_guard AbiLayoutGuard.c)
target_link_libraries(package_abi_layout_guard PRIVATE Obelisk::obelisk_sdk)
set_target_properties(package_abi_layout_guard PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME PackageAbiLayoutGuard COMMAND package_abi_layout_guard)
]=])
