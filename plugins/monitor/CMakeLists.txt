add_library(MonitorPlugin SHARED MonitorPlugin.cpp)
target_include_directories(MonitorPlugin PRIVATE ../../)
target_link_libraries(MonitorPlugin PRIVATE pthread)
set_target_properties(MonitorPlugin PROPERTIES PREFIX "")
