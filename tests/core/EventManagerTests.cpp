#include "core/EventManager.h"

#include <cstdint>
#include <iostream>
#include <stdexcept>

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

    void ResetCounters()
    {
        g_Counters = {};
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
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

    bool NullSafeCallback(void*, void*, void*)
    {
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

        const uint64_t globalPreId = events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        const uint64_t filteredPreId = events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);
        const uint64_t globalPostId = events.RegisterPostProcessEventOwned(&owner, GlobalPost);
        const uint64_t filteredPostId = events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, FilteredPost);

        Require(globalPreId != 0, "global pre registration id was zero");
        Require(filteredPreId != 0, "filtered pre registration id was zero");
        Require(globalPostId != 0, "global post registration id was zero");
        Require(filteredPostId != 0, "filtered post registration id was zero");
        Require(globalPreId != filteredPreId, "registration ids were not unique");

        Require(events.UnregisterCallback(filteredPreId), "filtered pre unregister by id failed");
        Require(!events.UnregisterCallback(filteredPreId), "filtered pre unregister by id was not idempotent");
        Require(!events.UnregisterCallback(0), "zero registration id unregistered a callback");

        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "pre event blocked after unregistering one callback");
        Require(g_Counters.global_pre == 1, "global pre callback was removed by filtered id");
        Require(g_Counters.filtered_pre == 0, "filtered pre callback survived id unregister");

        Require(events.UnregisterCallback(globalPostId), "global post unregister by id failed");
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
}

int main()
{
    TestFilteredPreCallbacks();
    TestPreCallbackBlocking();
    TestFilteredPostCallbacks();
    TestOwnerCleanup();
    TestSingleRegistrationUnregister();
    TestNullCallbacksAreIgnored();

    std::cout << "EventManagerTests passed\n";
    return 0;
}
