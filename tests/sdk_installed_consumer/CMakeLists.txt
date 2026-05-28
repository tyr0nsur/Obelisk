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

add_library(install_layout_consumer SHARED consumer_plugin.cpp)
target_link_libraries(install_layout_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_library(install_layout_c_abi_consumer SHARED c_abi_plugin.c)
target_link_libraries(install_layout_c_abi_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_c_abi_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_c_abi_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    C_VISIBILITY_PRESET hidden
)

add_executable(consumer_fixture consumer_fixture.cpp)
target_link_libraries(consumer_fixture PRIVATE Obelisk::obelisk_sdk dl)
