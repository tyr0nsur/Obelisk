add_library(WhitelistPlugin SHARED WhitelistPlugin.cpp)
target_include_directories(WhitelistPlugin PRIVATE ../../)
set_target_properties(WhitelistPlugin PROPERTIES PREFIX "")
