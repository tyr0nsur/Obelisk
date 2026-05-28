#include "ProcessEventDispatch.h"

#include "ProcessEventCallGuard.h"
#include "core/EventManager.h"
#include "runtime/Logger.h"

namespace Obelisk::Hooks
{
    bool DispatchProcessEventCallbacks(
        int32_t nameIndex,
        void* object,
        void* function,
        void* params,
        bool hasPreCallbacks,
        bool hasPostCallbacks,
        ProcessEventOriginalInvoker original)
    {
        auto& eventManager = Core::EventManager::Get();
        bool skipAutomaticOriginal = false;
        if (hasPreCallbacks)
        {
            ProcessEventCallGuard::PreCallbackScope preCallbackScope;
            const bool preCallbacksAllowedOriginal =
                eventManager.TriggerPreProcessEvent(nameIndex, object, function, params);

            if (preCallbackScope.OriginalCalled())
            {
                skipAutomaticOriginal = true;
                OBELISK_WARN("ProcessEvent original was called from a pre-callback; skipping the automatic original call to avoid double execution.");
            }
            if (!preCallbacksAllowedOriginal)
                return skipAutomaticOriginal;
        }

        if (!skipAutomaticOriginal && original)
        {
            original(object, function, params);
            skipAutomaticOriginal = true;
        }

        if (hasPostCallbacks)
            eventManager.TriggerPostProcessEvent(nameIndex, object, function, params);

        return skipAutomaticOriginal;
    }
}
