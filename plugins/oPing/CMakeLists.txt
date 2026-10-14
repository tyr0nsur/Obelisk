add_library(oPing SHARED oPing.cpp)
target_include_directories(oPing PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oPing PRIVATE obelisk_sdk)
set_target_properties(oPing PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
