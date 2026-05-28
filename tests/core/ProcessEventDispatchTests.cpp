#include "hooks/ProcessEventCallGuard.h"
#include "hooks/ProcessEventDispatch.h"
#include "core/EventManager.h"
#include "runtime/Logger.h"

#include <iostream>
#include <stdexcept>

namespace
{
    int g_OriginalCallCount = 0;
    int g_PreCallbackCount = 0;
    int g_PostCallbackCount = 0;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void ResetCounters()
    {
        g_OriginalCallCount = 0;
        g_PreCallbackCount = 0;
        g_PostCallbackCount = 0;
    }

    void FakeOriginal(void*, void*, void*)
    {
        ++g_OriginalCallCount;
    }

    bool PreCallbackCallsOriginal(void*, void*, void*)
    {
        ++g_PreCallbackCount;
        Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
        FakeOriginal(nullptr, nullptr, nullptr);
        return true;
    }

    bool PreCallbackAllowsAutomaticOriginal(void*, void*, void*)
    {
        ++g_PreCallbackCount;
        return true;
    }

    bool PreCallbackBlocksOriginal(void*, void*, void*)
    {
        ++g_PreCallbackCount;
        return false;
    }

    bool PostCallback(void*, void*, void*)
    {
        ++g_PostCallbackCount;
        return true;
    }

    void TestPreCallbackManualOriginalSkipsAutomaticOriginal()
    {
        ResetCounters();
        int owner = 0;
        auto& eventManager = Obelisk::Core::EventManager::Get();
        eventManager.RegisterPreProcessEventForNameIndexOwned(&owner, 42, PreCallbackCallsOriginal);

        const bool originalWasCalled = Obelisk::Hooks::DispatchProcessEventCallbacks(
            42,
            reinterpret_cast<void*>(0x1),
            reinterpret_cast<void*>(0x2),
            reinterpret_cast<void*>(0x3),
            true,
            false,
            FakeOriginal);

        Require(g_PreCallbackCount == 1, "manual-original pre-callback was not called");
        Require(g_OriginalCallCount == 1, "manual original call was followed by automatic original");
        Require(originalWasCalled, "manual original call was not reported");

        eventManager.UnregisterCallbacksForOwner(&owner);
    }

    void TestPreCallbackWithoutManualOriginalCallsAutomaticOriginal()
    {
        ResetCounters();
        int owner = 0;
        auto& eventManager = Obelisk::Core::EventManager::Get();
        eventManager.RegisterPreProcessEventForNameIndexOwned(&owner, 42, PreCallbackAllowsAutomaticOriginal);

        const bool originalWasCalled = Obelisk::Hooks::DispatchProcessEventCallbacks(
            42,
            reinterpret_cast<void*>(0x1),
            reinterpret_cast<void*>(0x2),
            reinterpret_cast<void*>(0x3),
            true,
            false,
            FakeOriginal);

        Require(g_PreCallbackCount == 1, "normal pre-callback was not called");
        Require(g_OriginalCallCount == 1, "automatic original was not called exactly once");
        Require(originalWasCalled, "automatic original call was not reported");

        eventManager.UnregisterCallbacksForOwner(&owner);
    }

    void TestPreCallbackCanBlockOriginal()
    {
        ResetCounters();
        int owner = 0;
        auto& eventManager = Obelisk::Core::EventManager::Get();
        eventManager.RegisterPreProcessEventForNameIndexOwned(&owner, 42, PreCallbackBlocksOriginal);

        const bool originalWasCalled = Obelisk::Hooks::DispatchProcessEventCallbacks(
            42,
            reinterpret_cast<void*>(0x1),
            reinterpret_cast<void*>(0x2),
            reinterpret_cast<void*>(0x3),
            true,
            true,
            FakeOriginal);

        Require(g_PreCallbackCount == 1, "blocking pre-callback was not called");
        Require(g_OriginalCallCount == 0, "blocked original was called");
        Require(g_PostCallbackCount == 0, "post-callback ran after blocked original");
        Require(!originalWasCalled, "blocked original was reported as called");

        eventManager.UnregisterCallbacksForOwner(&owner);
    }

    void TestPostCallbackRunsAfterOriginal()
    {
        ResetCounters();
        int owner = 0;
        auto& eventManager = Obelisk::Core::EventManager::Get();
        eventManager.RegisterPostProcessEventForNameIndexOwned(&owner, 42, PostCallback);

        const bool originalWasCalled = Obelisk::Hooks::DispatchProcessEventCallbacks(
            42,
            reinterpret_cast<void*>(0x1),
            reinterpret_cast<void*>(0x2),
            reinterpret_cast<void*>(0x3),
            false,
            true,
            FakeOriginal);

        Require(g_OriginalCallCount == 1, "original was not called before post dispatch");
        Require(g_PostCallbackCount == 1, "post-callback was not called");
        Require(originalWasCalled, "post path did not report original call");

        eventManager.UnregisterCallbacksForOwner(&owner);
    }
}

int main()
{
    Obelisk::Logger::Init();

    TestPreCallbackManualOriginalSkipsAutomaticOriginal();
    TestPreCallbackWithoutManualOriginalCallsAutomaticOriginal();
    TestPreCallbackCanBlockOriginal();
    TestPostCallbackRunsAfterOriginal();

    Obelisk::Logger::Shutdown();

    std::cout << "ProcessEventDispatchTests passed\n";
    return 0;
}
