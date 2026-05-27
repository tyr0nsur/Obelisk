add_library(oBaseEvents SHARED oBaseEvents.cpp)
target_include_directories(oBaseEvents PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oBaseEvents PRIVATE obelisk_sdk)
set_target_properties(oBaseEvents PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
