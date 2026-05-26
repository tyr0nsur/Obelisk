add_library(TestPlugin SHARED TestPlugin.cpp)
target_include_directories(TestPlugin PRIVATE ../)
set_target_properties(TestPlugin PROPERTIES PREFIX "")
