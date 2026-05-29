add_library(oChatLogger SHARED oChatLogger.c)
target_include_directories(oChatLogger PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oChatLogger PRIVATE obelisk_sdk)
set_target_properties(oChatLogger PROPERTIES
    PREFIX ""
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
    C_VISIBILITY_PRESET hidden
)
