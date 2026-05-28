#include "core/EventManager.h"
#include "runtime/Logger.h"

#include <cstdlib>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace fs = std::filesystem;

namespace
{
    struct Counters {
        int global_pre = 0;
        int filtered_pre = 0;
        int global_post = 0;
        int filtered_post = 0;
        bool block_global_pre = false;
        bool block_filtered_pre = false;
    };

    Counters g_Counters;
    Obelisk::Core::EventManager* g_SelfUnregisterEvents = nullptr;
    uint64_t g_SelfUnregisterId = 0;

    void ResetCounters()
    {
        g_Counters = {};
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    fs::path MakeTempRoot()
    {
        char templatePath[] = "/tmp/obelisk_event_manager_tests.XXXXXX";
        char* directory = mkdtemp(templatePath);
        Require(directory != nullptr, "mkdtemp failed");
        return fs::path(directory);
    }

    bool GlobalPre(void*, void*, void*)
    {
        ++g_Counters.global_pre;
        return !g_Counters.block_global_pre;
    }

    bool FilteredPre(void*, void*, void*)
    {
        ++g_Counters.filtered_pre;
        return !g_Counters.block_filtered_pre;
    }

    bool GlobalPost(void*, void*, void*)
    {
        ++g_Counters.global_post;
        return true;
    }

    bool FilteredPost(void*, void*, void*)
    {
        ++g_Counters.filtered_post;
        return true;
    }

    bool ThrowingGlobalPre(void*, void*, void*)
    {
        ++g_Counters.global_pre;
        throw std::runtime_error("global pre failed");
    }

    bool ThrowingFilteredPre(void*, void*, void*)
    {
        ++g_Counters.filtered_pre;
        throw std::runtime_error("filtered pre failed");
    }

    bool ThrowingGlobalPost(void*, void*, void*)
    {
        ++g_Counters.global_post;
        throw std::runtime_error("global post failed");
    }

    bool ThrowingFilteredPost(void*, void*, void*)
    {
        ++g_Counters.filtered_post;
        throw std::runtime_error("filtered post failed");
    }

    bool NullSafeCallback(void*, void*, void*)
    {
        return true;
    }

    bool SelfUnregisteringPre(void*, void*, void*)
    {
        ++g_Counters.global_pre;
        Require(g_SelfUnregisterEvents != nullptr, "self-unregister callback has no event manager");
        Require(g_SelfUnregisterEvents->UnregisterCallback(g_SelfUnregisterId),
                "self-unregister callback could not unregister itself");
        return true;
    }

    void TestFilteredPreCallbacks()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        Require(events.HasPreProcessEventCallbacks(), "pre callbacks were not reported");
        Require(events.TriggerPreProcessEvent(7, nullptr, nullptr, nullptr), "unmatched event was blocked");
        Require(g_Counters.global_pre == 1, "global pre callback did not run for unmatched event");
        Require(g_Counters.filtered_pre == 0, "filtered pre callback ran for wrong name index");

        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr), "matched event was blocked");
        Require(g_Counters.global_pre == 2, "global pre callback did not run for matched event");
        Require(g_Counters.filtered_pre == 1, "filtered pre callback did not run for matched name index");
    }

    void TestPreCallbackBlocking()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        g_Counters.block_global_pre = true;
        Require(!events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "global pre callback block was ignored");
        Require(g_Counters.global_pre == 1, "global pre blocker did not run");
        Require(g_Counters.filtered_pre == 0, "filtered pre callback ran after global block");

        ResetCounters();
        g_Counters.block_filtered_pre = true;
        Require(!events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "filtered pre callback block was ignored");
        Require(g_Counters.global_pre == 1, "global pre callback did not run before filtered block");
        Require(g_Counters.filtered_pre == 1, "filtered pre blocker did not run");
    }

    void TestFilteredPostCallbacks()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPostProcessEventOwned(&owner, GlobalPost);
        events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, FilteredPost);

        Require(events.HasPostProcessEventCallbacks(), "post callbacks were not reported");
        events.TriggerPostProcessEvent(7, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 1, "global post callback did not run for unmatched event");
        Require(g_Counters.filtered_post == 0, "filtered post callback ran for wrong name index");

        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 2, "global post callback did not run for matched event");
        Require(g_Counters.filtered_post == 1, "filtered post callback did not run for matched name index");
    }

    void TestPreCallbackExceptionsDoNotBlockOrStopLaterCallbacks()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, ThrowingGlobalPre);
        events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, ThrowingFilteredPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "throwing pre callback blocked event dispatch");
        Require(g_Counters.global_pre == 2, "global pre dispatch stopped after exception");
        Require(g_Counters.filtered_pre == 2, "filtered pre dispatch stopped after exception");
    }

    void TestPostCallbackExceptionsDoNotStopLaterCallbacks()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPostProcessEventOwned(&owner, ThrowingGlobalPost);
        events.RegisterPostProcessEventOwned(&owner, GlobalPost);
        events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, ThrowingFilteredPost);
        events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, FilteredPost);

        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 2, "global post dispatch stopped after exception");
        Require(g_Counters.filtered_post == 2, "filtered post dispatch stopped after exception");
    }

    void TestOwnerCleanup()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner_a = 0;
        int owner_b = 0;

        events.RegisterPreProcessEventOwned(&owner_a, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner_a, 42, FilteredPre);
        events.RegisterPostProcessEventOwned(&owner_b, GlobalPost);
        events.RegisterPostProcessEventForNameIndexOwned(&owner_b, 42, FilteredPost);

        Require(events.UnregisterCallbacksForOwner(&owner_a) == 2, "owner A cleanup removed wrong count");
        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "pre event blocked after owner cleanup");
        Require(g_Counters.global_pre == 0, "owner A global pre callback survived cleanup");
        Require(g_Counters.filtered_pre == 0, "owner A filtered pre callback survived cleanup");

        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 1, "owner B global post callback was removed incorrectly");
        Require(g_Counters.filtered_post == 1, "owner B filtered post callback was removed incorrectly");

        Require(events.UnregisterCallbacksForOwner(&owner_b) == 2, "owner B cleanup removed wrong count");
        ResetCounters();
        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 0, "owner B global post callback survived cleanup");
        Require(g_Counters.filtered_post == 0, "owner B filtered post callback survived cleanup");
    }

    void TestSingleRegistrationUnregister()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;
        int otherOwner = 0;

        const uint64_t globalPreId = events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        const uint64_t filteredPreId = events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);
        const uint64_t globalPostId = events.RegisterPostProcessEventOwned(&owner, GlobalPost);
        const uint64_t filteredPostId = events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, FilteredPost);

        Require(globalPreId != 0, "global pre registration id was zero");
        Require(filteredPreId != 0, "filtered pre registration id was zero");
        Require(globalPostId != 0, "global post registration id was zero");
        Require(filteredPostId != 0, "filtered post registration id was zero");
        Require(globalPreId != filteredPreId, "registration ids were not unique");

        Require(!events.UnregisterCallbackForOwner(&otherOwner, filteredPreId),
                "wrong owner unregistered filtered pre callback");
        Require(events.UnregisterCallbackForOwner(&owner, filteredPreId),
                "filtered pre unregister by owner and id failed");
        Require(!events.UnregisterCallbackForOwner(&owner, filteredPreId),
                "filtered pre unregister by owner and id succeeded twice");
        Require(!events.UnregisterCallbackForOwner(nullptr, globalPreId),
                "null owner unregistered a callback");
        Require(!events.UnregisterCallback(0), "zero registration id unregistered a callback");

        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "pre event blocked after unregistering one callback");
        Require(g_Counters.global_pre == 1, "global pre callback was removed by filtered id");
        Require(g_Counters.filtered_pre == 0, "filtered pre callback survived id unregister");

        Require(events.UnregisterCallbackForOwner(&owner, globalPostId),
                "global post unregister by owner and id failed");
        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 0, "global post callback survived id unregister");
        Require(g_Counters.filtered_post == 1, "filtered post callback was removed by global id");

        Require(events.UnregisterCallbacksForOwner(&owner) == 2, "owner cleanup did not remove remaining callbacks");
    }

    void TestNullCallbacksAreIgnored()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, nullptr);
        events.RegisterPostProcessEventOwned(&owner, nullptr);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, nullptr);
        events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, nullptr);
        events.RegisterPreProcessEventOwned(&owner, NullSafeCallback);

        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "null pre callback blocked event");
        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(events.UnregisterCallbacksForOwner(&owner) == 5, "null callbacks were not tracked for cleanup");
    }

    void TestCallbackCanUnregisterItself()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        g_SelfUnregisterEvents = &events;
        g_SelfUnregisterId = events.RegisterPreProcessEventOwned(&owner, SelfUnregisteringPre);
        Require(g_SelfUnregisterId != 0, "self-unregister registration id was zero");

        Require(events.TriggerPreProcessEvent(nullptr, nullptr, nullptr),
                "self-unregistering callback blocked the event");
        Require(g_Counters.global_pre == 1, "self-unregistering callback did not run once");
        Require(!events.HasPreProcessEventCallbacks(), "self-unregistering callback survived dispatch");

        Require(events.TriggerPreProcessEvent(nullptr, nullptr, nullptr),
                "empty callback list blocked an event");
        Require(g_Counters.global_pre == 1, "self-unregistered callback ran again");

        g_SelfUnregisterEvents = nullptr;
        g_SelfUnregisterId = 0;
    }

    void TestRegistrationIdsSkipZeroAfterWrap()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        const uint64_t firstId = events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        Require(firstId == 1, "first registration id was not one");

        events.SetNextRegistrationIdForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t lastId = events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        const uint64_t wrappedId = events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        Require(lastId == std::numeric_limits<uint64_t>::max(), "last registration id was not preserved");
        Require(wrappedId == 2, "wrapped registration id did not skip zero or live ids");
        Require(wrappedId != firstId, "wrapped registration reused a live registration id");
        Require(!events.UnregisterCallback(0), "zero registration id unregistered a callback after wrap");
        Require(events.UnregisterCallbackForOwner(&owner, firstId), "first registration id could not unregister");
        Require(events.UnregisterCallbackForOwner(&owner, lastId), "last registration id could not unregister");
        Require(events.UnregisterCallbackForOwner(&owner, wrappedId), "wrapped registration id could not unregister");
        Require(!events.HasPreProcessEventCallbacks(), "wrapped registration callbacks survived unregister");
    }
}

int main()
{
    const fs::path logRoot = MakeTempRoot();
    setenv("OBELISK_LOG_DIR", logRoot.string().c_str(), 1);
    Obelisk::Logger::Init();

    TestFilteredPreCallbacks();
    TestPreCallbackBlocking();
    TestFilteredPostCallbacks();
    TestPreCallbackExceptionsDoNotBlockOrStopLaterCallbacks();
    TestPostCallbackExceptionsDoNotStopLaterCallbacks();
    TestOwnerCleanup();
    TestSingleRegistrationUnregister();
    TestNullCallbacksAreIgnored();
    TestCallbackCanUnregisterItself();
    TestRegistrationIdsSkipZeroAfterWrap();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "EventManagerTests passed\n";
    return 0;
}
