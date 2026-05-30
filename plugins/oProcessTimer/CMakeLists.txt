add_library(oProcessTimer SHARED oProcessTimer.cpp)
target_include_directories(oProcessTimer PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oProcessTimer PRIVATE obelisk_sdk)
set_target_properties(oProcessTimer PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
