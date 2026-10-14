add_library(oPing SHARED oPing.cpp)
target_include_directories(oPing PRIVATE ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oPing PRIVATE obelisk_sdk)
# GNU-unique C++ objects otherwise make dlclose retain the mapping implicitly.
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(oPing PRIVATE -fno-gnu-unique)
endif()
set_target_properties(oPing PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
