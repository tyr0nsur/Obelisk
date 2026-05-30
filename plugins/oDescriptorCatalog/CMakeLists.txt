add_library(oDescriptorCatalog SHARED oDescriptorCatalog.cpp)
target_include_directories(oDescriptorCatalog PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oDescriptorCatalog PRIVATE obelisk_sdk)
set_target_properties(oDescriptorCatalog PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
