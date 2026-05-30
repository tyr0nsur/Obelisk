add_library(oChatAudit SHARED oChatAudit.cpp)
target_include_directories(oChatAudit PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oChatAudit PRIVATE obelisk_sdk)
set_target_properties(oChatAudit PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
