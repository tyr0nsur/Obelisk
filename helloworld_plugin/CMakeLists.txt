add_library(HelloWorldPlugin SHARED HelloWorldPlugin.cpp)
target_include_directories(HelloWorldPlugin PRIVATE ../)
set_target_properties(HelloWorldPlugin PROPERTIES PREFIX "")
