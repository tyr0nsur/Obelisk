#include "api/ObeliskApi.h"
#include <stdio.h>

bool OnMyProcessEvent(void* caller, void* function, void* parms) {
    // Just returning true allows the event to pass through
    // Returning false would block the original ProcessEvent execution
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    api->LogInfo("TestPlugin says HELLO FROM THE OTHER SIDE!");
    api->RegisterPreProcessEvent(OnMyProcessEvent);
    return true;
}
