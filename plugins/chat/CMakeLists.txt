add_library(ChatPlugin SHARED ChatPlugin.cpp)
target_include_directories(ChatPlugin PRIVATE ../../)
set_target_properties(ChatPlugin PROPERTIES PREFIX "")
