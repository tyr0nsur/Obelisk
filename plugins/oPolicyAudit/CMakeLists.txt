add_library(oPolicyAudit SHARED oPolicyAudit.cpp)
target_include_directories(oPolicyAudit PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oPolicyAudit PRIVATE obelisk_sdk)
set_target_properties(oPolicyAudit PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
