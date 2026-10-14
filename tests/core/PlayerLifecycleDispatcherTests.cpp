#include "core/PlayerLifecycleDispatcher.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

namespace
{
    using Obelisk::Core::PlayerLifecycleDispatcher;
    using Obelisk::Core::PlayerLifecycleSnapshot;
    using namespace std::chrono_literals;

    static_assert(std::is_standard_layout_v<ObeliskPlayerLifecycleEvent>);
    static_assert(std::is_trivially_copyable_v<ObeliskPlayerLifecycleEvent>);
    static_assert(sizeof(ObeliskPlayerLifecycleEvent) == 72);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, flags) == 16);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, sequence) == 24);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, process_epoch) == 32);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, player_name) == 40);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, platform_id) == 56);

    constexpr uint64_t kQuality = OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED |
        OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED |
        OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD;
    constexpr uint64_t kTextFlags = OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE |
        OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    template <typename Predicate>
    void WaitUntil(Predicate predicate)
    {
        const auto deadline = std::chrono::steady_clock::now() + 2s;
        while (!predicate())
        {
            Require(std::chrono::steady_clock::now() < deadline, "condition did not become true");
            std::this_thread::yield();
        }
    }

    PlayerLifecycleSnapshot Login(std::string_view name = "Alice", std::string_view id = "native-id-a")
    {
        return {OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED,
                kQuality | kTextFlags | OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED |
                    OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE,
                1, 42, name, id};
    }

    PlayerLifecycleSnapshot Logout(std::string_view name = "Alice", std::string_view id = "native-id-a")
    {
        return {OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED, kQuality | kTextFlags, 2, 42, name, id};
    }

    struct Record
    {
        uint32_t Kind = 0;
        uint64_t Flags = 0;
        uint64_t Sequence = 0;
        uint64_t ProcessEpoch = 0;
        std::string Name;
        std::string Id;
        bool NameNull = false;
        bool IdNull = false;
    };

    struct Capture
    {
        bool ValidAbi = true;
        bool CopiedStorage = true;
        const char* BorrowedName = nullptr;
        const char* BorrowedId = nullptr;
        std::vector<Record> Records;
    };

    void CaptureCallback(const ObeliskPlayerLifecycleEvent* event, void* data)
    {
        auto& capture = *static_cast<Capture*>(data);
        capture.ValidAbi = capture.ValidAbi && event &&
            event->abi_version == OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION &&
            event->struct_size == sizeof(ObeliskPlayerLifecycleEvent) && event->reserved0 == 0;
        if (!event)
            return;
        if (event->player_name.data && capture.BorrowedName)
            capture.CopiedStorage = capture.CopiedStorage && event->player_name.data != capture.BorrowedName;
        if (event->platform_id.data && capture.BorrowedId)
            capture.CopiedStorage = capture.CopiedStorage && event->platform_id.data != capture.BorrowedId;
        Record record{event->kind, event->flags, event->sequence, event->process_epoch};
        record.NameNull = event->player_name.data == nullptr;
        record.IdNull = event->platform_id.data == nullptr;
        if (event->player_name.data)
            record.Name.assign(event->player_name.data, event->player_name.size);
        if (event->platform_id.data)
            record.Id.assign(event->platform_id.data, event->platform_id.size);
        capture.Records.push_back(std::move(record));
    }

    void TestAvailabilityAndTwoCopiedIdentities()
    {
        PlayerLifecycleDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        Require(!dispatcher.IsAvailable(), "lifecycle was available before adapter verification");
        Require(dispatcher.Register(&owner, CaptureCallback, &capture) == 0,
                "callback registered before adapter verification");
        Require(dispatcher.Dispatch(Login()) == 0, "disabled lifecycle dispatched");
        dispatcher.SetAvailable(true);
        Require(dispatcher.Register(nullptr, CaptureCallback, &capture) == 0, "null owner registered");
        Require(dispatcher.Register(&owner, nullptr, &capture) == 0, "null callback registered");
        Require(dispatcher.Dispatch(Login()) == 0, "empty dispatcher delivered an event");
        Require(dispatcher.Register(&owner, CaptureCallback, &capture) != 0, "callback registration failed");

        std::string name = "Alice \xf0\x9f\x8c\x8d";
        std::string id = "native-id-a";
        capture.BorrowedName = name.data();
        capture.BorrowedId = id.data();
        Require(dispatcher.Dispatch(Login(name, id)) == 1, "first identity did not dispatch");
        name.assign("Bob");
        id.assign("native-id-b");
        capture.BorrowedName = name.data();
        capture.BorrowedId = id.data();
        auto bob = Login(name, id);
        bob.Sequence = 3;
        Require(dispatcher.Dispatch(bob) == 1, "second identity did not dispatch");
        name.assign("adapter-buffer-reused");
        id.clear();
        Require(capture.ValidAbi && capture.CopiedStorage, "callback received incorrect ABI or adapter storage");
        Require(capture.Records.size() == 2 && capture.Records[0].Name == "Alice \xf0\x9f\x8c\x8d" &&
                    capture.Records[0].Id == "native-id-a" && capture.Records[1].Name == "Bob" &&
                    capture.Records[1].Id == "native-id-b",
                "plugin-owned retained text changed after callback or identities were mixed");
        Require(capture.Records[0].Sequence == 1 && capture.Records[1].Sequence == 3 &&
                    capture.Records[0].ProcessEpoch == 42,
                "source observation ordering context was lost");
        dispatcher.SetAvailable(false);
        Require(dispatcher.Dispatch(bob) == 0, "deactivated adapter dispatched");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1, "disabled adapter prevented owner cleanup");
    }

    void TestRejectsBadObservationQualityAndAllowsLogoutWithoutConnection()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, CaptureCallback, &capture);
        std::vector<PlayerLifecycleSnapshot> invalid;
        for (const uint64_t required : {OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED,
                                       OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED,
                                       OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD,
                                       OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED})
        {
            auto event = Login();
            event.Flags &= ~required;
            invalid.push_back(event);
        }
        auto reserved = Login();
        reserved.Flags |= 1ull << 63;
        invalid.push_back(reserved);
        auto wrongKind = Login();
        wrongKind.Kind = 999;
        invalid.push_back(wrongKind);
        auto zeroSequence = Login();
        zeroSequence.Sequence = 0;
        invalid.push_back(zeroSequence);
        auto zeroEpoch = Login();
        zeroEpoch.ProcessEpoch = 0;
        invalid.push_back(zeroEpoch);
        auto returnedLogout = Logout();
        returnedLogout.Flags |= OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED;
        invalid.push_back(returnedLogout);
        for (const auto& event : invalid)
            Require(dispatcher.Dispatch(event) == 0, "malformed observation reached a plugin");
        Require(capture.Records.empty(), "invalid observation invoked a callback");
        Require(dispatcher.Dispatch(Logout()) == 1, "logout required a live connection or original return");
        Require(capture.Records.back().Kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED &&
                    !(capture.Records.back().Flags & (OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED |
                                                      OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE)),
                "logout falsely claimed original return or connection availability");
    }

    void TestOptionalFieldsValidateUtf8AndBounds()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, CaptureCallback, &capture);
        const std::vector<std::string> invalid{
            "", std::string(257, 'a'), std::string("a\0b", 3), std::string("\xc0\xaf", 2),
            std::string("\xed\xa0\x80", 3), std::string("\xf4\x90\x80\x80", 4), std::string("\xe2\x82", 2)};
        for (const auto& text : invalid)
        {
            Require(dispatcher.Dispatch(Login(text, text)) == 1, "optional bad text suppressed lifecycle event");
            const auto& record = capture.Records.back();
            Require(!(record.Flags & kTextFlags) && record.NameNull && record.IdNull &&
                        record.Name.empty() && record.Id.empty(),
                    "malformed optional text retained an availability claim or borrowed view");
        }
        std::string maximum(256, 'x');
        Require(dispatcher.Dispatch(Login(maximum, maximum)) == 1, "256-byte fields were rejected");
        Require((capture.Records.back().Flags & kTextFlags) == kTextFlags &&
                    capture.Records.back().Name.size() == 256 && capture.Records.back().Id.size() == 256,
                "maximum valid fields lost availability");
        auto absent = Login("ignored", "ignored");
        absent.Flags &= ~kTextFlags;
        Require(dispatcher.Dispatch(absent) == 1, "unavailable optional fields suppressed lifecycle event");
        Require(capture.Records.back().NameNull && capture.Records.back().IdNull,
                "unavailable fields leaked non-null views");
        Require(dispatcher.Dispatch(Login(std::string_view{}, "valid-id")) == 1,
                "null optional view suppressed event");
        Require(capture.Records.back().NameNull && capture.Records.back().Id == "valid-id",
                "invalid name prevented independent native-ID observation");
    }

    struct MutateSource
    {
        std::string* Name;
        std::string* Id;
        Capture First;
    };

    void MutatingCallback(const ObeliskPlayerLifecycleEvent* event, void* data)
    {
        auto& mutation = *static_cast<MutateSource*>(data);
        CaptureCallback(event, &mutation.First);
        mutation.Name->assign("changed-name");
        mutation.Id->assign("changed-id");
    }

    void TestCopiesBeforeFirstCallback()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        std::string name = "entry-name";
        std::string id = "entry-id";
        MutateSource mutation{&name, &id};
        Capture second;
        dispatcher.Register(&owner, MutatingCallback, &mutation);
        dispatcher.Register(&owner, CaptureCallback, &second);
        Require(dispatcher.Dispatch(Login(name, id)) == 2, "copy-isolation callbacks did not dispatch");
        Require(second.Records[0].Name == "entry-name" && second.Records[0].Id == "entry-id" &&
                    mutation.First.Records[0].Name == second.Records[0].Name,
                "callback buffer reuse changed another subscriber's observation");
    }

    void TestOwnerIsolationAndHandleRetirement()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int ownerA = 0;
        int ownerB = 0;
        Capture a;
        Capture b;
        const auto aId = dispatcher.Register(&ownerA, CaptureCallback, &a);
        const auto bId = dispatcher.Register(&ownerB, CaptureCallback, &b);
        Require(!dispatcher.Unregister(&ownerB, aId), "wrong owner removed another plugin's callback");
        Require(!dispatcher.Unregister(nullptr, aId) && !dispatcher.Unregister(&ownerA, 0),
                "invalid owner/handle unregistered a callback");
        Require(dispatcher.UnregisterCallbacksForOwner(&ownerA) == 1, "owner cleanup removed wrong count");
        Require(dispatcher.Dispatch(Login()) == 1 && a.Records.empty() && b.Records.size() == 1,
                "owner cleanup affected an unrelated plugin");
        const auto newAId = dispatcher.Register(&ownerA, CaptureCallback, &a);
        Require(newAId > bId && !dispatcher.Unregister(&ownerA, aId), "retired handle was reused");
        Require(dispatcher.Unregister(&ownerA, newAId) && !dispatcher.Unregister(&ownerA, newAId),
                "registration cancellation was not idempotent");
        Require(dispatcher.Unregister(&ownerB, bId), "remaining owner could not unregister");
        Require(dispatcher.SubscriptionCount() == 0, "cancelled subscriptions remained active");
    }

    struct SelfState
    {
        PlayerLifecycleDispatcher* Dispatcher;
        void* Owner;
        uint64_t Id = 0;
        int Calls = 0;
        bool Cancelled = false;
        bool CleanupRefused = false;
    };

    void SelfUnregisterCallback(const ObeliskPlayerLifecycleEvent*, void* data)
    {
        auto& self = *static_cast<SelfState*>(data);
        ++self.Calls;
        self.Cancelled = self.Dispatcher->Unregister(self.Owner, self.Id);
    }

    void SelfCleanupCallback(const ObeliskPlayerLifecycleEvent*, void* data)
    {
        auto& self = *static_cast<SelfState*>(data);
        ++self.Calls;
        try
        {
            self.Dispatcher->UnregisterCallbacksForOwner(self.Owner);
        }
        catch (const std::logic_error&)
        {
            self.CleanupRefused = true;
        }
    }

    void TestSelfUnregisterAndSelfUnloadRefusal()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        SelfState self{&dispatcher, &owner};
        self.Id = dispatcher.Register(&owner, SelfUnregisterCallback, &self);
        Require(dispatcher.Dispatch(Login()) == 1 && self.Cancelled, "callback could not cancel itself");
        Require(dispatcher.Dispatch(Login()) == 0 && self.Calls == 1, "self-cancelled callback ran again");
        self.Id = dispatcher.Register(&owner, SelfCleanupCallback, &self);
        Require(dispatcher.Dispatch(Login()) == 1 && self.CleanupRefused,
                "owner cleanup allowed unloading its current callback frame");
        Require(dispatcher.Dispatch(Login()) == 0, "refused self-unload failed to cancel future delivery");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "owner retry could not finish after callback returned");
    }

    struct BlockingState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Released = false;
        bool Finished = false;
        int Calls = 0;
    };

    void BlockingCallback(const ObeliskPlayerLifecycleEvent*, void* data)
    {
        auto& state = *static_cast<BlockingState*>(data);
        std::unique_lock lock(state.Mutex);
        ++state.Calls;
        state.Entered = true;
        state.Cv.notify_all();
        state.Cv.wait(lock, [&] { return state.Released; });
        state.Finished = true;
    }

    void WaitForEntry(BlockingState& state)
    {
        std::unique_lock lock(state.Mutex);
        Require(state.Cv.wait_for(lock, 2s, [&] { return state.Entered; }), "blocking callback did not enter");
    }

    void Release(BlockingState& state)
    {
        std::lock_guard lock(state.Mutex);
        state.Released = true;
        state.Cv.notify_all();
    }

    void TestOwnerCleanupDrainsInFlightCallbacks()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        BlockingState state;
        dispatcher.Register(&owner, BlockingCallback, &state);
        auto delivery = std::async(std::launch::async, [&] { return dispatcher.Dispatch(Login()); });
        WaitForEntry(state);
        auto cleanup = std::async(std::launch::async, [&] { return dispatcher.UnregisterCallbacksForOwner(&owner); });
        try
        {
            WaitUntil([&] { return dispatcher.SubscriptionCount() == 0; });
            Require(cleanup.wait_for(0ms) == std::future_status::timeout,
                    "owner cleanup returned while its plugin callback was in flight");
            Require(dispatcher.Dispatch(Login()) == 0, "cleanup allowed a new callback to enter");
        }
        catch (...)
        {
            Release(state);
            delivery.wait();
            cleanup.wait();
            throw;
        }
        Release(state);
        Require(delivery.get() == 1 && cleanup.get() == 1 && state.Finished && state.Calls == 1,
                "owner cleanup did not finish after its callback returned");
    }

    void TestOwnerCleanupDeadlineCancelsAndRetainsActiveCallback()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        BlockingState state;
        Require(dispatcher.Register(&owner, BlockingCallback, &state), "deadline callback registration failed");
        auto delivery = std::async(std::launch::async, [&] { return dispatcher.Dispatch(Login()); });
        try { WaitForEntry(state); }
        catch (...) { Release(state); delivery.wait(); throw; }
        auto cleanup = std::async(std::launch::async, [&] {
            try
            {
                dispatcher.UnregisterCallbacksForOwner(&owner, std::chrono::steady_clock::now() + 30ms);
                return false;
            }
            catch (const std::runtime_error& error)
            {
                return std::string_view(error.what()).find("deadline expired") != std::string_view::npos;
            }
        });
        const bool bounded = cleanup.wait_for(2s) == std::future_status::ready;
        const bool cancelled = dispatcher.SubscriptionCount() == 0 && dispatcher.Dispatch(Login()) == 0;
        Release(state);
        const auto delivered = delivery.get();
        const bool timedOut = cleanup.get();
        Require(bounded && timedOut && cancelled && delivered == 1 && state.Finished && state.Calls == 1,
                "owner cleanup deadline did not preserve the active callback and reject new deliveries");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner, std::chrono::steady_clock::now()) == 0,
                "deadline owner cleanup could not finish after callback return");
    }

    void TestGranularUnregisterDrainsInFlightCallback()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        BlockingState state;
        const auto id = dispatcher.Register(&owner, BlockingCallback, &state);
        auto delivery = std::async(std::launch::async, [&] { return dispatcher.Dispatch(Login()); });
        WaitForEntry(state);
        auto unregister = std::async(std::launch::async, [&] { return dispatcher.Unregister(&owner, id); });
        try
        {
            WaitUntil([&] { return dispatcher.SubscriptionCount() == 0; });
            Require(unregister.wait_for(0ms) == std::future_status::timeout,
                    "unregister returned while its callback could still use user_data");
        }
        catch (...)
        {
            Release(state);
            delivery.wait();
            unregister.wait();
            throw;
        }
        Release(state);
        Require(delivery.get() == 1 && unregister.get() && state.Finished,
                "unregister did not drain callback before completing");
    }

    struct NestedState
    {
        PlayerLifecycleDispatcher* Dispatcher;
        Capture Observations;
        bool Entered = false;
    };

    void NestedCallback(const ObeliskPlayerLifecycleEvent* event, void* data)
    {
        auto& state = *static_cast<NestedState*>(data);
        CaptureCallback(event, &state.Observations);
        if (!state.Entered)
        {
            state.Entered = true;
            state.Dispatcher->Dispatch(Logout("nested-player", "nested-id"));
            CaptureCallback(event, &state.Observations);
        }
    }

    void ThrowingCallback(const ObeliskPlayerLifecycleEvent*, void*)
    {
        throw std::runtime_error("plugin failure");
    }

    void TestNestedSnapshotsAndCallbackFailure()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner = 0;
        NestedState nested{&dispatcher};
        Capture surviving;
        dispatcher.Register(&owner, ThrowingCallback, nullptr);
        dispatcher.Register(&owner, NestedCallback, &nested);
        dispatcher.Register(&owner, CaptureCallback, &surviving);
        Require(dispatcher.Dispatch(Login("outer-player", "outer-id")) == 2,
                "plugin exception suppressed remaining callbacks");
        Require(nested.Observations.Records.size() == 3 &&
                    nested.Observations.Records[0].Name == "outer-player" &&
                    nested.Observations.Records[1].Name == "nested-player" &&
                    nested.Observations.Records[2].Name == "outer-player",
                "nested delivery replaced outer callback's borrowed snapshot");
        Require(surviving.Records.size() == 2 && surviving.Records[0].Id == "nested-id" &&
                    surviving.Records[1].Id == "outer-id",
                "nested identities crossed callback scopes");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 3,
                "callback failure stranded in-flight owner cleanup");
    }

    struct NestedOwnerCleanup
    {
        PlayerLifecycleDispatcher* Dispatcher;
        void* OuterOwner;
        bool Nested = false;
        bool Refused = false;
    };

    void OuterOwnerCallback(const ObeliskPlayerLifecycleEvent*, void* data)
    {
        auto& state = *static_cast<NestedOwnerCleanup*>(data);
        if (!state.Nested)
        {
            state.Nested = true;
            state.Dispatcher->Dispatch(Logout());
        }
    }

    void InnerOwnerCallback(const ObeliskPlayerLifecycleEvent*, void* data)
    {
        auto& state = *static_cast<NestedOwnerCleanup*>(data);
        if (!state.Refused)
        {
            try
            {
                state.Dispatcher->UnregisterCallbacksForOwner(state.OuterOwner);
            }
            catch (const std::logic_error&)
            {
                state.Refused = true;
            }
        }
    }

    void TestNestedCallbackCannotUnloadOuterOwner()
    {
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int outerOwner = 0;
        int innerOwner = 0;
        NestedOwnerCleanup state{&dispatcher, &outerOwner};
        dispatcher.Register(&outerOwner, OuterOwnerCallback, &state);
        dispatcher.Register(&innerOwner, InnerOwnerCallback, &state);
        Require(dispatcher.Dispatch(Login()) == 2 && state.Refused,
                "nested callback allowed unloading a plugin still on its outer stack");
        Require(dispatcher.UnregisterCallbacksForOwner(&outerOwner) == 0 &&
                    dispatcher.UnregisterCallbacksForOwner(&innerOwner) == 1,
                "owner cleanup could not complete after nested callbacks returned");
    }

    void TestManagedPauseOwnerIsolationAndStaleGeneration()
    {
        using Gate = Obelisk::Core::OwnerExecutionGate;
        auto& gate = Gate::Get();
        PlayerLifecycleDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner, otherOwner;
        auto binding = gate.Bind(&owner, 9401);
        auto other = gate.Bind(&otherOwner, 9402);
        Require(binding && other && gate.Activate(binding) == Gate::Result::Ok && gate.Activate(other) == Gate::Result::Ok,
                "lifecycle owners did not bind/activate");
        Capture capture, otherCapture, replacementCapture;
        const auto oldHandle = dispatcher.Register(&owner, CaptureCallback, &capture);
        const auto otherHandle = dispatcher.Register(&otherOwner, CaptureCallback, &otherCapture);
        Require(oldHandle && otherHandle && gate.Pause(binding, Gate::Clock::now()) == Gate::Result::Ok,
                "lifecycle pause setup failed");
        Require(dispatcher.Register(&owner, CaptureCallback, &capture) == 0, "paused lifecycle owner registered new work");
        Require(dispatcher.Dispatch(Login()) == 1 && capture.Records.empty() && otherCapture.Records.size() == 1,
                "pause delivered an observation or suppressed an unrelated owner");
        Require(dispatcher.SubscriptionCount() == 2 && gate.Resume(binding) == Gate::Result::Ok,
                "pause discarded lifecycle subscriptions");
        Require(dispatcher.Dispatch(Logout()) == 2 && capture.Records.size() == 1 &&
                capture.Records.front().Kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED,
                "resume replayed a missed login or did not restore the original callback");
        Require(gate.RetireAndDrain(binding, Gate::Clock::now()) == Gate::Result::Ok && gate.Forget(binding) == Gate::Result::Ok,
                "lifecycle generation did not retire");
        auto replacement = gate.Bind(&owner, 9403);
        Require(replacement && gate.Activate(replacement) == Gate::Result::Ok, "replacement lifecycle owner did not activate");
        Require(dispatcher.Register(&owner, CaptureCallback, &replacementCapture) != 0, "replacement registration failed");
        Require(dispatcher.Dispatch(Login("New observation", "new-native-id")) == 2 &&
                capture.Records.size() == 1 && replacementCapture.Records.size() == 1 &&
                replacementCapture.Records.front().Name == "New observation",
                "old callback at a reused owner address borrowed a new generation's admission");
        Require(gate.RetireAndDrain(replacement, Gate::Clock::now()) == Gate::Result::Ok &&
                gate.RetireAndDrain(other, Gate::Clock::now()) == Gate::Result::Ok, "lifecycle owners did not drain");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 2 && dispatcher.UnregisterCallbacksForOwner(&otherOwner) == 1,
                "old/new lifecycle handle cleanup was incomplete");
        Require(gate.Forget(replacement) == Gate::Result::Ok && gate.Forget(other) == Gate::Result::Ok,
                "lifecycle gates could not be released after cleanup");
    }
}

int main()
{
    try
    {
        TestAvailabilityAndTwoCopiedIdentities();
        TestRejectsBadObservationQualityAndAllowsLogoutWithoutConnection();
        TestOptionalFieldsValidateUtf8AndBounds();
        TestCopiesBeforeFirstCallback();
        TestOwnerIsolationAndHandleRetirement();
        TestSelfUnregisterAndSelfUnloadRefusal();
        TestOwnerCleanupDrainsInFlightCallbacks();
        TestOwnerCleanupDeadlineCancelsAndRetainsActiveCallback();
        TestGranularUnregisterDrainsInFlightCallback();
        TestNestedSnapshotsAndCallbackFailure();
        TestNestedCallbackCannotUnloadOuterOwner();
        TestManagedPauseOwnerIsolationAndStaleGeneration();
        std::cout << "PlayerLifecycleDispatcherTests passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "PlayerLifecycleDispatcherTests failed: " << error.what() << '\n';
        return 1;
    }
}
