#include "api/ObeliskApi.h"

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    if (api) {
        api->LogInfo("[Plugin] HelloWorldPlugin started successfully!");
    }
    return true;
}
