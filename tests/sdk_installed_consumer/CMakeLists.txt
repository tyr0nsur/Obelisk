cmake_minimum_required(VERSION 3.22)
project(ObeliskInstallLayoutConsumer LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)

if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Installed Obelisk package did not define Obelisk::obelisk_sdk")
endif()
if(NOT Obelisk_SDK_FOUND)
    message(FATAL_ERROR "Installed Obelisk package did not report SDK component found")
endif()
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
if(NOT Obelisk_DEVELOPMENT_LINE STREQUAL "0.1.0-dev")
    message(FATAL_ERROR "Unexpected Obelisk development line: ${Obelisk_DEVELOPMENT_LINE}")
endif()
if(NOT Obelisk_RELEASE_CHANNEL STREQUAL "dev")
    message(FATAL_ERROR "Unexpected Obelisk release channel: ${Obelisk_RELEASE_CHANNEL}")
endif()
if(NOT Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS STREQUAL "package-shape-evidence-only")
    message(FATAL_ERROR
        "Unexpected Obelisk installed SDK package-shape status: "
        "${Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS}")
endif()

function(obelisk_require_package_marker variable expected_value)
    if(NOT DEFINED ${variable})
        message(FATAL_ERROR
            "Installed Obelisk SDK package did not define required package-shape marker: "
            "${variable}")
    endif()
    if(NOT "${${variable}}" STREQUAL "${expected_value}")
        message(FATAL_ERROR
            "Installed Obelisk SDK package marker ${variable} must be "
            "${expected_value}, got ${${variable}}")
    endif()
endfunction()

function(obelisk_reject_defined_positive_alias variable)
    if(NOT DEFINED ${variable})
        return()
    endif()

    string(TOUPPER "${${variable}}" alias_value)
    if(alias_value STREQUAL "" OR
       alias_value STREQUAL "0" OR
       alias_value STREQUAL "FALSE" OR
       alias_value STREQUAL "OFF" OR
       alias_value STREQUAL "NO")
        return()
    endif()

    message(FATAL_ERROR
        "Installed Obelisk SDK package exposed forbidden positive readiness alias "
        "${variable}=${${variable}}")
endfunction()

obelisk_require_package_marker(Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE)
obelisk_require_package_marker(Obelisk_SDK_BLOCKER_PROMOTION_COUNT 0)
obelisk_require_package_marker(Obelisk_SDK_BLOCKER_PROMOTION_TOTAL 12)
obelisk_require_package_marker(Obelisk_P0_DEPENDENCY_COUNT 0)
obelisk_require_package_marker(Obelisk_P0_DEPENDENCY_TOTAL 4)
obelisk_require_package_marker(
    Obelisk_ACTIVE_COMPLETION_BLOCKER
    approved_runtime_evidence_missing
)

foreach(required_false_non_claim_var IN ITEMS
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
    obelisk_require_package_marker(${required_false_non_claim_var} FALSE)
endforeach()

foreach(forbidden_positive_alias IN ITEMS
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
    Obelisk_SDK_CONSUMER_TESTS_READY
    Obelisk_STABLE_SDK_READY
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
)
    obelisk_reject_defined_positive_alias(${forbidden_positive_alias})
endforeach()
if(NOT Obelisk_API_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk API ABI version: ${Obelisk_API_ABI_VERSION}")
endif()
if(NOT Obelisk_PLUGIN_METADATA_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk plugin metadata ABI version: ${Obelisk_PLUGIN_METADATA_ABI_VERSION}")
endif()
if(NOT Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk plugin init context ABI version: ${Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION}")
endif()
if(NOT Obelisk_GAMEPLAY_POLICY_EVENT_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk gameplay policy event ABI version: ${Obelisk_GAMEPLAY_POLICY_EVENT_ABI_VERSION}")
endif()
if(NOT Obelisk_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk resource kind descriptor ABI version: ${Obelisk_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION}")
endif()
if(NOT Obelisk_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk gameplay policy event descriptor ABI version: ${Obelisk_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION}")
endif()
if(NOT Obelisk_CHAT_MESSAGE_EVENT_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk chat message event ABI version: ${Obelisk_CHAT_MESSAGE_EVENT_ABI_VERSION}")
endif()

get_filename_component(OBELISK_INSTALLED_PACKAGE_ROOT "${Obelisk_DIR}/../../.." ABSOLUTE)
set(OBELISK_EXPECTED_SDK_INCLUDE_DIR "${OBELISK_INSTALLED_PACKAGE_ROOT}/include")
get_target_property(
    OBELISK_SDK_INTERFACE_INCLUDE_DIRECTORIES
    Obelisk::obelisk_sdk
    INTERFACE_INCLUDE_DIRECTORIES
)
if(NOT OBELISK_SDK_INTERFACE_INCLUDE_DIRECTORIES STREQUAL OBELISK_EXPECTED_SDK_INCLUDE_DIR)
    message(FATAL_ERROR
        "Installed Obelisk SDK target must expose only the installed public include root; "
        "expected ${OBELISK_EXPECTED_SDK_INCLUDE_DIR}, got "
        "${OBELISK_SDK_INTERFACE_INCLUDE_DIRECTORIES}")
endif()

foreach(interface_property IN ITEMS
    INTERFACE_COMPILE_DEFINITIONS
    INTERFACE_COMPILE_OPTIONS
    INTERFACE_LINK_LIBRARIES
    INTERFACE_SOURCES
    INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
)
    get_target_property(
        OBELISK_SDK_INTERFACE_PROPERTY_VALUE
        Obelisk::obelisk_sdk
        ${interface_property}
    )
    if(OBELISK_SDK_INTERFACE_PROPERTY_VALUE)
        message(FATAL_ERROR
            "Installed Obelisk SDK target must not export ${interface_property}: "
            "${OBELISK_SDK_INTERFACE_PROPERTY_VALUE}")
    endif()
endforeach()

set(OBELISK_INSTALLED_PACKAGE_ABI_DEFINITIONS
    OBELISK_CMAKE_API_ABI_VERSION=${Obelisk_API_ABI_VERSION}
    OBELISK_CMAKE_PLUGIN_METADATA_ABI_VERSION=${Obelisk_PLUGIN_METADATA_ABI_VERSION}
    OBELISK_CMAKE_PLUGIN_INIT_CONTEXT_ABI_VERSION=${Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION}
    OBELISK_CMAKE_GAMEPLAY_POLICY_EVENT_ABI_VERSION=${Obelisk_GAMEPLAY_POLICY_EVENT_ABI_VERSION}
    OBELISK_CMAKE_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION=${Obelisk_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION}
    OBELISK_CMAKE_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION=${Obelisk_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION}
    OBELISK_CMAKE_CHAT_MESSAGE_EVENT_ABI_VERSION=${Obelisk_CHAT_MESSAGE_EVENT_ABI_VERSION}
)

add_library(install_layout_consumer SHARED consumer_plugin.cpp)
target_link_libraries(install_layout_consumer PRIVATE Obelisk::obelisk_sdk)
target_compile_definitions(install_layout_consumer PRIVATE ${OBELISK_INSTALLED_PACKAGE_ABI_DEFINITIONS})
set_target_properties(install_layout_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_library(install_layout_c_abi_consumer SHARED c_abi_plugin.c)
target_link_libraries(install_layout_c_abi_consumer PRIVATE Obelisk::obelisk_sdk)
target_compile_definitions(install_layout_c_abi_consumer PRIVATE ${OBELISK_INSTALLED_PACKAGE_ABI_DEFINITIONS})
set_target_properties(install_layout_c_abi_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_c_abi_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    C_VISIBILITY_PRESET hidden
)

add_library(install_layout_no_shutdown_consumer SHARED no_shutdown_plugin.cpp)
target_link_libraries(install_layout_no_shutdown_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_no_shutdown_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_no_shutdown_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_library(install_layout_descriptor_catalog_consumer SHARED descriptor_catalog_plugin.cpp)
target_link_libraries(install_layout_descriptor_catalog_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_descriptor_catalog_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_descriptor_catalog_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_library(install_layout_descriptor_timer_consumer SHARED descriptor_timer_plugin.cpp)
target_link_libraries(install_layout_descriptor_timer_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_descriptor_timer_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_descriptor_timer_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_executable(consumer_fixture consumer_fixture.cpp)
target_link_libraries(consumer_fixture PRIVATE Obelisk::obelisk_sdk dl)

set(OBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT "" CACHE PATH
    "Optional repo plugins/ root used by the install layout test to compile release-scope examples against the installed SDK")
set(OBELISK_RELEASE_SCOPE_EXTERN_ROOT "" CACHE PATH
    "Optional repo extern/ root used by release-scope examples that own third-party header-only dependencies")

function(add_obelisk_release_scope_example target_name source_relative_path)
    set(source_path "${OBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT}/${source_relative_path}")
    if(NOT EXISTS "${source_path}")
        message(FATAL_ERROR "Missing release-scope example source: ${source_path}")
    endif()

    add_library(${target_name} SHARED "${source_path}")
    target_include_directories(${target_name} PRIVATE "${OBELISK_RELEASE_SCOPE_EXTERN_ROOT}")
    target_link_libraries(${target_name} PRIVATE Obelisk::obelisk_sdk)
    set_target_properties(${target_name} PROPERTIES
        PREFIX ""
        LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN 1
    )
endfunction()

if(OBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT)
    if(NOT OBELISK_RELEASE_SCOPE_EXTERN_ROOT OR NOT EXISTS "${OBELISK_RELEASE_SCOPE_EXTERN_ROOT}/nlohmann/json.hpp")
        message(FATAL_ERROR
            "OBELISK_RELEASE_SCOPE_EXTERN_ROOT must point at the repo extern/ directory")
    endif()

    add_obelisk_release_scope_example(
        release_scope_oBaseEvents
        oBaseEvents/oBaseEvents.cpp
    )
    set_target_properties(release_scope_oBaseEvents PROPERTIES OUTPUT_NAME "oBaseEvents")

    add_obelisk_release_scope_example(
        release_scope_oProcessTimer
        oProcessTimer/oProcessTimer.cpp
    )
    set_target_properties(release_scope_oProcessTimer PROPERTIES OUTPUT_NAME "oProcessTimer")

    add_obelisk_release_scope_example(
        release_scope_oDescriptorCatalog
        oDescriptorCatalog/oDescriptorCatalog.cpp
    )
    set_target_properties(release_scope_oDescriptorCatalog PROPERTIES OUTPUT_NAME "oDescriptorCatalog")
endif()
