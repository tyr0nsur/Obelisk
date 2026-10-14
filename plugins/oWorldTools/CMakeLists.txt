add_library(oWorldTools SHARED oWorldTools.cpp)
target_include_directories(oWorldTools PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oWorldTools PRIVATE obelisk_sdk)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(oWorldTools PRIVATE -fno-gnu-unique)
endif()
set_target_properties(oWorldTools PROPERTIES PREFIX ""
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN 1)
