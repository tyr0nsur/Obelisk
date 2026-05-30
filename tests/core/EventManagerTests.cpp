#include "core/EventManager.h"
#include "runtime/Logger.h"

#include <cstdlib>
#include <cstdint>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <thread>

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

    struct ReentrantUnregisterState {
        Obelisk::Core::EventManager* events = nullptr;
        void* owner = nullptr;
        uint64_t other_id = 0;
        int first_calls = 0;
        int second_calls = 0;
    };

    ReentrantUnregisterState* g_ReentrantUnregisterState = nullptr;

    struct BlockingCallbackState {
        std::mutex mutex;
        std::condition_variable cv;
        bool entered = false;
        bool release = false;
        bool exiting = false;
    };

    BlockingCallbackState* g_BlockingPreState = nullptr;
    BlockingCallbackState* g_BlockingPostState = nullptr;

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

    bool BlockingPre(void*, void*, void*)
    {
        Require(g_BlockingPreState != nullptr, "blocking pre callback has no state");
        std::unique_lock<std::mutex> lock(g_BlockingPreState->mutex);
        g_BlockingPreState->entered = true;
        g_BlockingPreState->cv.notify_all();
        g_BlockingPreState->cv.wait(lock, [] {
            return g_BlockingPreState->release;
        });
        g_BlockingPreState->exiting = true;
        g_BlockingPreState->cv.notify_all();
        return true;
    }

    bool BlockingPost(void*, void*, void*)
    {
        Require(g_BlockingPostState != nullptr, "blocking post callback has no state");
        std::unique_lock<std::mutex> lock(g_BlockingPostState->mutex);
        g_BlockingPostState->entered = true;
        g_BlockingPostState->cv.notify_all();
        g_BlockingPostState->cv.wait(lock, [] {
            return g_BlockingPostState->release;
        });
        g_BlockingPostState->exiting = true;
        g_BlockingPostState->cv.notify_all();
        return false;
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

    bool ReentrantUnregisterFirst(void*, void*, void*)
    {
        Require(g_ReentrantUnregisterState != nullptr, "reentrant unregister callback has no state");
        Require(g_ReentrantUnregisterState->events != nullptr, "reentrant unregister callback has no event manager");
        ++g_ReentrantUnregisterState->first_calls;
        Require(g_ReentrantUnregisterState->events->UnregisterCallbackForOwner(
                    g_ReentrantUnregisterState->owner,
                    g_ReentrantUnregisterState->other_id),
                "reentrant unregister of second callback failed");
        return true;
    }

    bool ReentrantUnregisterSecond(void*, void*, void*)
    {
        Require(g_ReentrantUnregisterState != nullptr, "reentrant unregister second callback has no state");
        ++g_ReentrantUnregisterState->second_calls;
        return true;
    }

    void EnableProcessEventBlockingGate(const fs::path& root)
    {
        setenv("OBELISK_ROOT", root.string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
        setenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-process-event-blocking");
        Require(marker.is_open(), "failed to create ProcessEvent blocking marker");
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(true);
    }

    void DisableProcessEventBlockingGate()
    {
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(false);
        unsetenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING");
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
        DisableProcessEventBlockingGate();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        g_Counters.block_global_pre = true;
        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "global pre callback blocked without explicit ProcessEvent blocking gate");
        Require(g_Counters.global_pre == 1, "global pre blocker did not run");
        Require(g_Counters.filtered_pre == 1, "filtered pre callback did not continue after ungated global block");

        ResetCounters();
        g_Counters.block_filtered_pre = true;
        Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "filtered pre callback blocked without explicit ProcessEvent blocking gate");
        Require(g_Counters.global_pre == 1, "global pre callback did not run before ungated filtered block");
        Require(g_Counters.filtered_pre == 1, "filtered pre blocker did not run");
    }

    void TestPreCallbackBlockingWithGate()
    {
        const fs::path root = MakeTempRoot();
        EnableProcessEventBlockingGate(root);

        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPreProcessEventOwned(&owner, GlobalPre);
        events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, FilteredPre);

        g_Counters.block_global_pre = true;
        Require(!events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "global pre callback block was ignored with explicit gate");
        Require(g_Counters.global_pre == 1, "gated global pre blocker did not run");
        Require(g_Counters.filtered_pre == 0, "filtered pre callback ran after gated global block");

        ResetCounters();
        g_Counters.block_filtered_pre = true;
        Require(!events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                "filtered pre callback block was ignored with explicit gate");
        Require(g_Counters.global_pre == 1, "global pre callback did not run before filtered block");
        Require(g_Counters.filtered_pre == 1, "filtered pre blocker did not run");

        DisableProcessEventBlockingGate();
        fs::remove_all(root);
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

    void TestPostCallbackReturnValueDoesNotAffectDispatch()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;

        events.RegisterPostProcessEventOwned(&owner, [](void*, void*, void*) -> bool {
            ++g_Counters.global_post;
            return false;
        });
        events.RegisterPostProcessEventOwned(&owner, GlobalPost);

        events.TriggerPostProcessEvent(nullptr, nullptr, nullptr);
        Require(g_Counters.global_post == 2, "post callback false return stopped later callbacks");
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

    void TestReentrantUnregisterSkipsLaterRawCallbackSnapshots()
    {
        auto run = [](auto register_first, auto register_second, auto trigger, const char* scope) {
            Obelisk::Core::EventManager events;
            int owner = 0;
            ReentrantUnregisterState state;
            state.events = &events;
            state.owner = &owner;
            g_ReentrantUnregisterState = &state;

            const uint64_t firstId = register_first(events, &owner);
            state.other_id = register_second(events, &owner);
            Require(firstId != 0 && state.other_id != 0, scope);

            trigger(events);
            Require(state.first_calls == 1, "first reentrant raw callback did not run");
            Require(state.second_calls == 0, "unregistered raw callback ran from stale snapshot");

            Require(events.UnregisterCallbackForOwner(&owner, firstId),
                    "first reentrant raw callback could not unregister");
            g_ReentrantUnregisterState = nullptr;
        };

        run(
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPreProcessEventOwned(owner, ReentrantUnregisterFirst);
            },
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPreProcessEventOwned(owner, ReentrantUnregisterSecond);
            },
            [](Obelisk::Core::EventManager& events) {
                Require(events.TriggerPreProcessEvent(nullptr, nullptr, nullptr),
                        "global pre reentrant unregister blocked dispatch");
            },
            "global pre reentrant unregister registrations failed");

        run(
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPreProcessEventForNameIndexOwned(owner, 42, ReentrantUnregisterFirst);
            },
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPreProcessEventForNameIndexOwned(owner, 42, ReentrantUnregisterSecond);
            },
            [](Obelisk::Core::EventManager& events) {
                Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                        "filtered pre reentrant unregister blocked dispatch");
            },
            "filtered pre reentrant unregister registrations failed");

        run(
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPostProcessEventOwned(owner, ReentrantUnregisterFirst);
            },
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPostProcessEventOwned(owner, ReentrantUnregisterSecond);
            },
            [](Obelisk::Core::EventManager& events) {
                events.TriggerPostProcessEvent(nullptr, nullptr, nullptr);
            },
            "global post reentrant unregister registrations failed");

        run(
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPostProcessEventForNameIndexOwned(owner, 42, ReentrantUnregisterFirst);
            },
            [](Obelisk::Core::EventManager& events, void* owner) {
                return events.RegisterPostProcessEventForNameIndexOwned(owner, 42, ReentrantUnregisterSecond);
            },
            [](Obelisk::Core::EventManager& events) {
                events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
            },
            "filtered post reentrant unregister registrations failed");
    }

    void TestOwnerCleanupWaitsForInFlightFilteredPreCallback()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;
        BlockingCallbackState state;
        g_BlockingPreState = &state;

        const uint64_t id = events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, BlockingPre);
        Require(id != 0, "blocking filtered pre registration id was zero");

        std::thread dispatchThread([&events] {
            Require(events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr),
                    "blocking filtered pre callback blocked dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state] {
                        return state.entered;
                    }),
                    "blocking filtered pre callback did not enter");
        }

        std::atomic_bool cleanupReturned = false;
        size_t removed = 0;
        std::thread cleanupThread([&] {
            removed = events.UnregisterCallbacksForOwner(&owner);
            cleanupReturned.store(true);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupReturned.load(), "owner cleanup returned while filtered pre callback was in flight");

        {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.release = true;
        }
        state.cv.notify_all();

        cleanupThread.join();
        dispatchThread.join();

        Require(cleanupReturned.load(), "owner cleanup did not return after filtered pre callback exit");
        Require(removed == 1, "owner cleanup removed wrong count after filtered pre dispatch");
        Require(!events.HasPreProcessEventCallbacks(), "filtered pre callback survived owner cleanup");
        g_BlockingPreState = nullptr;
    }

    void TestOwnerCleanupWaitsForInFlightPostCallback()
    {
        ResetCounters();
        Obelisk::Core::EventManager events;
        int owner = 0;
        BlockingCallbackState state;
        g_BlockingPostState = &state;

        const uint64_t id = events.RegisterPostProcessEventOwned(&owner, BlockingPost);
        Require(id != 0, "blocking post registration id was zero");

        std::thread dispatchThread([&events] {
            events.TriggerPostProcessEvent(nullptr, nullptr, nullptr);
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state] {
                        return state.entered;
                    }),
                    "blocking post callback did not enter");
        }

        std::atomic_bool cleanupReturned = false;
        size_t removed = 0;
        std::thread cleanupThread([&] {
            removed = events.UnregisterCallbacksForOwner(&owner);
            cleanupReturned.store(true);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupReturned.load(), "owner cleanup returned while post callback was in flight");

        {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.release = true;
        }
        state.cv.notify_all();

        cleanupThread.join();
        dispatchThread.join();

        Require(cleanupReturned.load(), "owner cleanup did not return after callback exit");
        Require(removed == 1, "owner cleanup removed wrong count after post dispatch");
        Require(!events.HasPostProcessEventCallbacks(), "post callback survived owner cleanup");
        g_BlockingPostState = nullptr;
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
    TestPreCallbackBlockingWithGate();
    TestFilteredPostCallbacks();
    TestPostCallbackReturnValueDoesNotAffectDispatch();
    TestPreCallbackExceptionsDoNotBlockOrStopLaterCallbacks();
    TestPostCallbackExceptionsDoNotStopLaterCallbacks();
    TestOwnerCleanup();
    TestSingleRegistrationUnregister();
    TestNullCallbacksAreIgnored();
    TestCallbackCanUnregisterItself();
    TestReentrantUnregisterSkipsLaterRawCallbackSnapshots();
    TestOwnerCleanupWaitsForInFlightFilteredPreCallback();
    TestOwnerCleanupWaitsForInFlightPostCallback();
    TestRegistrationIdsSkipZeroAfterWrap();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "EventManagerTests passed\n";
    return 0;
}
