add_library(oEssentials SHARED oEssentials.cpp)
target_include_directories(oEssentials PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oEssentials PRIVATE obelisk_sdk)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(oEssentials PRIVATE -fno-gnu-unique)
endif()
set_target_properties(oEssentials PROPERTIES PREFIX ""
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN 1)
