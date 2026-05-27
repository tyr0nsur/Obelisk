add_library(oBaseEvents SHARED oBaseEvents.cpp)
target_include_directories(oBaseEvents PRIVATE ../../)
set_target_properties(oBaseEvents PROPERTIES PREFIX "")
