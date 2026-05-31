cmake_minimum_required(VERSION 3.22)
project(ObeliskInstallLayoutConsumer LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Obelisk 0.1.0 CONFIG REQUIRED)

if(NOT Obelisk_DEVELOPMENT_LINE STREQUAL "0.1.0-dev")
    message(FATAL_ERROR "Unexpected Obelisk development line: ${Obelisk_DEVELOPMENT_LINE}")
endif()
if(NOT Obelisk_RELEASE_CHANNEL STREQUAL "dev")
    message(FATAL_ERROR "Unexpected Obelisk release channel: ${Obelisk_RELEASE_CHANNEL}")
endif()
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
