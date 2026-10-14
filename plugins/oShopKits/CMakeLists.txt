add_library(oShopKits SHARED oShopKits.cpp)
target_include_directories(oShopKits PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oShopKits PRIVATE obelisk_sdk)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(oShopKits PRIVATE -fno-gnu-unique)
endif()
set_target_properties(oShopKits PROPERTIES PREFIX ""
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN 1)
