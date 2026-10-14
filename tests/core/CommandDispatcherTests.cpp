#include "core/CommandDispatcher.h"
#include "core/GameplayCallbackScope.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

namespace
{
    using Obelisk::Core::CommandDispatcher;
    using namespace std::chrono_literals;

    void Require(bool value, const char* message)
    {
        if (!value)
            throw std::runtime_error(message);
    }

    struct Delivery
    {
        void* Controller;
        std::string Text;
    };

    bool Capture(void* controller, std::string_view reply, void* data) noexcept
    {
        try
        {
            static_cast<std::vector<Delivery>*>(data)->push_back({controller, std::string(reply)});
            return true;
        }
        catch (...)
        {
            return false;
        }
    }

    struct State
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        uint64_t Token = 0;
        bool Replied = false;
        bool WrongOwner = true;
        bool WrongThread = true;
        bool PreviousTokenRejected = false;
        int Count = 0;
    };

    void Ping(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<State*>(data);
        ++state.Count;
        const auto previousToken = state.Token;
        state.Token = event->invocation_token;
        state.PreviousTokenRejected = !state.Dispatcher->Reply(state.Owner, previousToken, "stale");
        state.WrongOwner = state.Dispatcher->Reply(&state, state.Token, "wrong");
        std::thread worker([&] { state.WrongThread = state.Dispatcher->Reply(state.Owner, state.Token, "thread"); });
        worker.join();
        state.Replied = state.Dispatcher->Reply(state.Owner, state.Token, "pong");
    }

    void TestTargetingAndExpiry()
    {
        CommandDispatcher dispatcher;
        int owner = 0, firstController = 0, secondController = 0;
        State state{&dispatcher, &owner};
        Require(!dispatcher.Register(&owner, "/ping", Ping, &state), "unverified backend must deny registrations");
        dispatcher.SetAvailable(true);
        const auto id = dispatcher.Register(&owner, "/ping", Ping, &state);
        Require(id != 0, "registration failed");
        std::vector<Delivery> deliveries;
        Require(dispatcher.Dispatch(&firstController, "/pingx", 0, Capture, &deliveries) == 0,
                "prefix collision must not route");
        Require(dispatcher.Dispatch(&firstController, "/ping args", 0, Capture, &deliveries) == 0,
                "arguments must not accidentally match exact command");
        Require(dispatcher.Dispatch(&firstController, "/ping", 0, Capture, &deliveries) == 1, "first callback missing");
        const auto expired = state.Token;
        Require(state.Replied && !state.WrongOwner && !state.WrongThread, "reply ownership or thread boundary broken");
        Require(!dispatcher.Reply(&owner, expired, "late"), "retained invocation token must expire");
        Require(dispatcher.Dispatch(&secondController, "/ping", 3, Capture, &deliveries) == 1, "second callback missing");
        Require(state.Token != expired, "invocations must receive different tokens");
        Require(state.PreviousTokenRejected, "fresh callback accepted the previous player's invocation token");
        Require(deliveries.size() == 2 && deliveries[0].Controller == &firstController &&
                deliveries[1].Controller == &secondController && deliveries[0].Text == "pong" &&
                deliveries[1].Text == "pong", "reply delivered to wrong controller");
        Require(!dispatcher.Unregister(&state, id), "other owner must not unregister");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1, "owner cleanup failed");
        Require(dispatcher.Dispatch(&firstController, "/ping", 0, Capture, &deliveries) == 0,
                "cleanup must remove delivery");
        // Reusing the same private address (e.g. after reconnect) cannot revive a token.
        Require(dispatcher.Register(&owner, "/ping", Ping, &state), "re-registration failed");
        Require(!dispatcher.Reply(&owner, expired, "reconnect"), "address reuse revived expired invocation");
    }

    struct NestedState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        void* OuterController;
        void* InnerController;
        std::vector<Delivery>* Deliveries;
        uint64_t OuterToken = 0;
        bool RejectedOuter = false;
        bool RepliedInner = false;
        bool ResumedOuter = false;
    };

    void Inner(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<NestedState*>(data);
        state.RejectedOuter = !state.Dispatcher->Reply(state.Owner, state.OuterToken, "misrouted");
        state.RepliedInner = state.Dispatcher->Reply(state.Owner, event->invocation_token, "inner");
    }

    void Outer(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<NestedState*>(data);
        state.OuterToken = event->invocation_token;
        state.Dispatcher->Dispatch(state.InnerController, "/inner", 0, Capture, state.Deliveries);
        state.ResumedOuter = state.Dispatcher->Reply(state.Owner, state.OuterToken, "outer");
    }

    void TestNestedInvocations()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner, outer, inner;
        std::vector<Delivery> deliveries;
        NestedState state{&dispatcher, &owner, &outer, &inner, &deliveries};
        Require(dispatcher.Register(&owner, "/outer", Outer, &state) != 0, "outer registration failed");
        Require(dispatcher.Register(&owner, "/inner", Inner, &state) != 0, "inner registration failed");
        Require(dispatcher.Dispatch(&outer, "/outer", 0, Capture, &deliveries) == 1, "outer delivery failed");
        Require(state.RejectedOuter && state.RepliedInner && state.ResumedOuter, "nested invocation context leaked");
        Require(deliveries.size() == 2 && deliveries[0].Controller == &inner && deliveries[0].Text == "inner" &&
                deliveries[1].Controller == &outer && deliveries[1].Text == "outer", "nested replies misrouted");
        Require(!dispatcher.Reply(&owner, state.OuterToken, "expired"), "outer token survived callback return");
    }

    struct BlockingState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Release = false;
    };

    void Block(const ObeliskCommandInvocation*, void* data)
    {
        auto& state = *static_cast<BlockingState*>(data);
        std::unique_lock lock(state.Mutex);
        state.Entered = true;
        state.Cv.notify_all();
        state.Cv.wait(lock, [&] { return state.Release; });
    }

    void TestCleanupQuiescence()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner, controller;
        BlockingState state;
        Require(dispatcher.Register(&owner, "/wait", Block, &state), "blocking registration failed");
        std::vector<Delivery> deliveries;
        std::thread dispatch([&] { dispatcher.Dispatch(&controller, "/wait", 0, Capture, &deliveries); });
        {
            std::unique_lock lock(state.Mutex);
            Require(state.Cv.wait_for(lock, 2s, [&] { return state.Entered; }), "callback did not enter");
        }
        std::promise<void> started;
        auto cleanup = std::async(std::launch::async, [&] {
            started.set_value();
            return dispatcher.UnregisterCallbacksForOwner(&owner);
        });
        started.get_future().wait();
        const bool waited = cleanup.wait_for(60ms) == std::future_status::timeout;
        {
            std::lock_guard lock(state.Mutex);
            state.Release = true;
        }
        state.Cv.notify_all();
        dispatch.join();
        Require(waited && cleanup.get() == 1, "owner cleanup must wait before plugin code can unmap");
        Require(dispatcher.SubscriptionCount() == 0, "owner subscriptions survived cleanup");
    }

    struct SelfState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        uint64_t Id = 0;
        bool Removed = false;
        bool OwnerCleanupDenied = false;
    };

    void SelfRemove(const ObeliskCommandInvocation*, void* data)
    {
        auto& state = *static_cast<SelfState*>(data);
        state.Removed = state.Dispatcher->Unregister(state.Owner, state.Id);
        try
        {
            state.Dispatcher->UnregisterCallbacksForOwner(state.Owner);
        }
        catch (const std::logic_error&)
        {
            state.OwnerCleanupDenied = true;
        }
    }

    void Throw(const ObeliskCommandInvocation*, void*) { throw std::runtime_error("plugin failure"); }

    void TestSelfRemovalAndException()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner, controller;
        SelfState state{&dispatcher, &owner};
        state.Id = dispatcher.Register(&owner, "/self", SelfRemove, &state);
        std::vector<Delivery> deliveries;
        Require(dispatcher.Dispatch(&controller, "/self", 0, Capture, &deliveries) == 1, "self callback failed");
        Require(state.Removed && state.OwnerCleanupDenied, "self-unload must not permit dlclose on callback stack");
        Require(dispatcher.Dispatch(&controller, "/self", 0, Capture, &deliveries) == 0, "self removal failed");
        Require(dispatcher.Register(&owner, "/throw", Throw, nullptr), "throw registration failed");
        Require(dispatcher.Dispatch(&controller, "/throw", 0, Capture, &deliveries) == 0, "exception must be contained");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1, "exception stranded in-flight cleanup");
    }

    void ValidateReplies(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<State*>(data);
        const auto reply = [&](std::string_view text) { return state.Dispatcher->Reply(state.Owner, event->invocation_token, text); };
        state.Replied = !reply("") && !reply(std::string(1025, 'x')) && !reply(std::string("a\0b", 3)) &&
                        !reply(std::string("\xc0\x80", 2)) && !reply(std::string("\xed\xa0\x80", 3)) &&
                        reply("pong \xf0\x9f\x8e\xae");
        state.Dispatcher->SetAvailable(false);
        state.WrongOwner = reply("revoked");
    }

    void TestPayloadAndBackendRevocation()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        int owner, controller;
        State state{&dispatcher, &owner};
        Require(!dispatcher.Register(&owner, "/", Ping, &state), "empty command name accepted");
        Require(!dispatcher.Register(&owner, "/ping evil", Ping, &state), "whitespace command name accepted");
        Require(dispatcher.Register(&owner, "/utf", ValidateReplies, &state), "validation registration failed");
        std::vector<Delivery> deliveries;
        Require(dispatcher.Dispatch(nullptr, "/utf", 0, Capture, &deliveries) == 0, "null origin accepted");
        Require(dispatcher.Dispatch(&controller, "/utf", 4, Capture, &deliveries) == 0, "invalid chat mode accepted");
        Require(dispatcher.Dispatch(&controller, "/utf", 0, Capture, &deliveries) == 1, "validation callback failed");
        Require(state.Replied && !state.WrongOwner && deliveries.size() == 1, "invalid UTF-8 or revoked backend accepted");
        Require(dispatcher.Dispatch(&controller, "/utf", 0, Capture, &deliveries) == 0, "revocation did not stop dispatch");
    }

    struct PlayerState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        uint64_t Token = 0;
        std::string Name;
        std::string Id;
        std::string* AdapterName = nullptr;
        std::string* AdapterId = nullptr;
        bool Valid = false;
        bool WrongOwnerRejected = false;
        bool WrongThreadRejected = false;
        bool PreviousTokenRejected = false;
    };

    void InspectPlayer(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<PlayerState*>(data);
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.PreviousTokenRejected = !state.Dispatcher->GetPlayer(state.Owner, state.Token, &player);
        state.Token = event->invocation_token;
        state.WrongOwnerRejected = !state.Dispatcher->GetPlayer(&state, state.Token, &player);
        std::thread worker([&] {
            ObeliskCommandPlayer other{};
            other.struct_size = sizeof(other);
            state.WrongThreadRejected = !state.Dispatcher->GetPlayer(state.Owner, state.Token, &other);
        });
        worker.join();
        // Model private adapter buffer mutation/reuse while plugin code runs.
        if (state.AdapterName)
            state.AdapterName->assign("changed");
        if (state.AdapterId)
            state.AdapterId->assign("changed");
        state.Valid = state.Dispatcher->GetPlayer(state.Owner, state.Token, &player);
        if (state.Valid)
        {
            Require(player.abi_version == OBELISK_COMMAND_PLAYER_ABI_VERSION &&
                    player.struct_size == sizeof(player), "player snapshot ABI invalid");
            state.Name.assign(player.player_name.data, player.player_name.size);
            state.Id.assign(player.platform_id.data, player.platform_id.size);
        }
    }

    void TestPlayerSnapshotsAndCopyLifetime()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetPlayerSnapshotsAvailable(true);
        Require(!dispatcher.IsPlayerSnapshotsAvailable(), "identity must require command backend availability");
        dispatcher.SetAvailable(true);
        int owner, firstController, secondController;
        PlayerState state{&dispatcher, &owner};
        Require(dispatcher.Register(&owner, "/identity", InspectPlayer, &state), "identity registration failed");
        constexpr uint64_t flags = OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE |
                                   OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE;
        std::string name = "\xc3\x81gata \xf0\x9f\x8e\xae";
        std::string id = "native:opaque-one";
        const std::string expectedName = name;
        state.AdapterName = &name;
        state.AdapterId = &id;
        const Obelisk::Core::CommandPlayerSnapshot first{flags, name, id};
        std::vector<Delivery> deliveries;
        Require(dispatcher.Dispatch(&firstController, "/identity", 0, Capture, &deliveries, &first) == 1,
                "first identity invocation failed");
        Require(state.Valid && state.Name == expectedName && state.Id == "native:opaque-one" &&
                state.WrongOwnerRejected && state.WrongThreadRejected, "snapshot copied data or access boundary broken");
        const auto expired = state.Token;
        ObeliskCommandPlayer out{OBELISK_COMMAND_PLAYER_ABI_VERSION, sizeof(out), 0x1234, {"sentinel", 8}, {nullptr, 0}};
        Require(!dispatcher.GetPlayer(&owner, expired, &out) && out.flags == 0x1234 && out.player_name.size == 8,
                "expired getter must reject and preserve output");
        state.AdapterName = nullptr;
        state.AdapterId = nullptr;
        const Obelisk::Core::CommandPlayerSnapshot second{flags, "Bruno", "native:opaque-two"};
        Require(dispatcher.Dispatch(&secondController, "/identity", 0, Capture, &deliveries, &second) == 1 &&
                state.Valid && state.Name == "Bruno" && state.Id == "native:opaque-two" && state.PreviousTokenRejected,
                "second player accepted stale identity or inherited another player's snapshot");
        dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(!dispatcher.GetPlayer(&owner, state.Token, &out), "owner cleanup retained access to identity");
    }

    struct NestedPlayerState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        void* InnerController;
        std::vector<Delivery>* Deliveries;
        uint64_t OuterToken = 0;
        bool InnerCorrect = false;
        bool OuterDeniedInInner = false;
        bool OuterRestored = false;
    };

    void InnerPlayer(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<NestedPlayerState*>(data);
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.OuterDeniedInInner = !state.Dispatcher->GetPlayer(state.Owner, state.OuterToken, &player);
        state.InnerCorrect = state.Dispatcher->GetPlayer(state.Owner, event->invocation_token, &player) &&
                             std::string_view(player.player_name.data, player.player_name.size) == "Inner";
    }

    void OuterPlayer(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<NestedPlayerState*>(data);
        state.OuterToken = event->invocation_token;
        const Obelisk::Core::CommandPlayerSnapshot inner{OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE, "Inner", {}};
        state.Dispatcher->Dispatch(state.InnerController, "/inner-player", 0, Capture, state.Deliveries, &inner);
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.OuterRestored = state.Dispatcher->GetPlayer(state.Owner, state.OuterToken, &player) &&
                             std::string_view(player.player_name.data, player.player_name.size) == "Outer";
    }

    void TestNestedPlayerScope()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        dispatcher.SetPlayerSnapshotsAvailable(true);
        int owner, outer, inner;
        std::vector<Delivery> deliveries;
        NestedPlayerState state{&dispatcher, &owner, &inner, &deliveries};
        Require(dispatcher.Register(&owner, "/outer-player", OuterPlayer, &state), "outer player registration failed");
        Require(dispatcher.Register(&owner, "/inner-player", InnerPlayer, &state), "inner player registration failed");
        const Obelisk::Core::CommandPlayerSnapshot player{OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE, "Outer", {}};
        Require(dispatcher.Dispatch(&outer, "/outer-player", 0, Capture, &deliveries, &player) == 1,
                "nested player invocation failed");
        Require(state.InnerCorrect && state.OuterDeniedInInner && state.OuterRestored,
                "nested identity scope leaked or was not restored");
    }

    struct PlayerFlagsState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        bool Present = false;
        uint64_t Flags = 0;
        uint64_t Token = 0;
        uint64_t Id = 0;
        bool RemoveSelf = false;
        bool ShortOutputDenied = false;
        std::string Name;
    };

    void InspectPlayerFlags(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<PlayerFlagsState*>(data);
        state.Token = event->invocation_token;
        ObeliskCommandPlayer shortOut{};
        shortOut.struct_size = sizeof(shortOut) - 1;
        shortOut.flags = 0x5678;
        state.ShortOutputDenied = !state.Dispatcher->GetPlayer(state.Owner, state.Token, &shortOut) &&
                                  shortOut.flags == 0x5678;
        if (state.RemoveSelf)
            Require(state.Dispatcher->Unregister(state.Owner, state.Id), "identity self-unregister failed");
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.Present = state.Dispatcher->GetPlayer(state.Owner, state.Token, &player);
        if (state.Present)
        {
            state.Flags = player.flags;
            if (player.flags & OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE)
                state.Name.assign(player.player_name.data, player.player_name.size);
            else
                Require(!player.player_name.data && !player.player_name.size, "missing name must have empty view");
            if (!(player.flags & OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE))
                Require(!player.platform_id.data && !player.platform_id.size, "missing ID must have empty view");
        }
    }

    void TestPlayerPayloadLimitsAndCleanup()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        dispatcher.SetPlayerSnapshotsAvailable(true);
        int owner, controller;
        PlayerFlagsState state{&dispatcher, &owner};
        state.Id = dispatcher.Register(&owner, "/fields", InspectPlayerFlags, &state);
        Require(state.Id, "field registration failed");
        std::vector<Delivery> deliveries;
        constexpr auto both = OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE | OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE;
        const auto dispatch = [&](const Obelisk::Core::CommandPlayerSnapshot* player) {
            Require(dispatcher.Dispatch(&controller, "/fields", 0, Capture, &deliveries, player) == 1,
                    "invalid identity must not suppress command delivery");
        };
        dispatch(nullptr);
        Require(!state.Present && state.ShortOutputDenied, "absent snapshot or short output accepted");
        Obelisk::Core::CommandPlayerSnapshot player{both, std::string_view("a\0b", 3), std::string_view("\xed\xa0\x80", 3)};
        dispatch(&player);
        Require(state.Present && state.Flags == 0, "invalid UTF-8 or NUL identity field remained available");
        player = {both, std::string_view(nullptr, 1), std::string_view(nullptr, 1)};
        dispatch(&player);
        Require(state.Present && state.Flags == 0, "null identity data must lose availability without suppressing commands");
        const std::string boundaryName(256, 'n');
        const std::string excessiveId(257, 'i');
        player = {both, boundaryName, excessiveId};
        dispatch(&player);
        Require(state.Present && state.Flags == OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE && state.Name == boundaryName,
                "identity byte boundaries handled incorrectly");
        const std::string excessiveName(257, 'n');
        const std::string boundaryId(256, 'i');
        player = {both, excessiveName, boundaryId};
        dispatch(&player);
        Require(state.Present && state.Flags == OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE,
                "name/ID boundary validation must be independent");
        player = {uint64_t{1} << 63, "untrusted", "untrusted"};
        dispatch(&player);
        Require(!state.Present, "reserved identity flags accepted");
        dispatcher.SetPlayerSnapshotsAvailable(false);
        player = {both, "name", "id"};
        dispatch(&player);
        Require(!state.Present, "unavailable identity backend accepted snapshot");
        dispatcher.SetPlayerSnapshotsAvailable(true);
        state.RemoveSelf = true;
        dispatch(&player);
        Require(state.Present && state.Flags == both && dispatcher.SubscriptionCount() == 0,
                "self-unregister invalidated live copied data or failed cleanup");
        ObeliskCommandPlayer out{};
        out.struct_size = sizeof(out);
        Require(!dispatcher.GetPlayer(&owner, state.Token, &out), "self-unregistered callback retained getter after return");
    }

    struct FamilyState
    {
        CommandDispatcher* Dispatcher;
        void* Owner;
        bool RejectedNested = false;
        bool Restored = false;
    };

    void InspectNestedFamilies(const ObeliskCommandInvocation* event, void* data)
    {
        using Obelisk::Core::GameplayCallbackFamily;
        using Obelisk::Core::GameplayCallbackScope;
        auto& state = *static_cast<FamilyState*>(data);
        const auto* originalScope = GameplayCallbackScope::Current();
        Require(originalScope && GameplayCallbackScope::IsInsideCallback(GameplayCallbackFamily::Command),
                "command callback scope was not entered");
        state.RejectedNested = true;
        state.Restored = true;
        for (const auto family : {GameplayCallbackFamily::PlayerLifecycle, GameplayCallbackFamily::Chat,
                                  GameplayCallbackFamily::Command})
        {
            ObeliskCommandPlayer out{};
            out.struct_size = sizeof(out);
            {
                GameplayCallbackScope nested(family);
                state.RejectedNested = state.RejectedNested && GameplayCallbackScope::Current() != originalScope &&
                    !state.Dispatcher->GetPlayer(state.Owner, event->invocation_token, &out) &&
                    !state.Dispatcher->Reply(state.Owner, event->invocation_token, "wrong-family");
            }
            state.Restored = state.Restored && GameplayCallbackScope::Current() == originalScope &&
                state.Dispatcher->GetPlayer(state.Owner, event->invocation_token, &out);
        }
        state.Restored = state.Restored && state.Dispatcher->Reply(state.Owner, event->invocation_token, "restored");
    }

    void TestExactGameplayCallbackScope()
    {
        CommandDispatcher dispatcher;
        dispatcher.SetAvailable(true);
        dispatcher.SetPlayerSnapshotsAvailable(true);
        int owner, controller;
        FamilyState state{&dispatcher, &owner};
        Require(dispatcher.Register(&owner, "/scope", InspectNestedFamilies, &state), "scope registration failed");
        std::vector<Delivery> deliveries;
        const Obelisk::Core::CommandPlayerSnapshot player{OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE, "Origin", {}};
        Require(dispatcher.Dispatch(&controller, "/scope", 0, Capture, &deliveries, &player) == 1 &&
                state.RejectedNested && state.Restored && deliveries.size() == 1 && deliveries.front().Text == "restored",
                "nested callback family borrowed command authorization or outer scope was not restored");
        Require(!Obelisk::Core::GameplayCallbackScope::Current() &&
                !Obelisk::Core::GameplayCallbackScope::IsInsideAnyCallback(), "gameplay scope leaked after callback");
    }
}

int main()
{
    TestTargetingAndExpiry();
    TestNestedInvocations();
    TestCleanupQuiescence();
    TestSelfRemovalAndException();
    TestPayloadAndBackendRevocation();
    TestPlayerSnapshotsAndCopyLifetime();
    TestNestedPlayerScope();
    TestPlayerPayloadLimitsAndCleanup();
    TestExactGameplayCallbackScope();
    std::cout << "CommandDispatcherTests passed\n";
}
