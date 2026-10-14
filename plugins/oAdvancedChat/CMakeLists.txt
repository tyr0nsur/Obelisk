add_library(oAdvancedChat SHARED oAdvancedChat.cpp ../../core/AdvancedChatRouter.cpp)
target_include_directories(oAdvancedChat PRIVATE ${PROJECT_SOURCE_DIR} ${PROJECT_SOURCE_DIR}/extern)
target_link_libraries(oAdvancedChat PRIVATE obelisk_sdk pthread)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(oAdvancedChat PRIVATE -fno-gnu-unique)
endif()
set_target_properties(oAdvancedChat PROPERTIES PREFIX ""
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN 1)
