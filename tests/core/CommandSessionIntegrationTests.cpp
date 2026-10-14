#include "core/ChatSessionRegistry.h"
#include "core/CommandDispatcher.h"
#include "core/GameplayCallbackScope.h"
#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace
{
    using namespace Obelisk::Core;
    void Require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
    struct Delivery { void* Controller; std::string Text; };
    enum class Mode { Ordinary, RolloverReturnNew, RolloverReturnOld, SendInvalidatesOrigin };
    struct State
    {
        ChatSessionRegistry Sessions;
        CommandDispatcher Commands;
        int Owner{}, OtherOwner{}, First{}, Second{}, FirstConnection{}, SecondConnection{}, FirstPlayerState{}, SecondPlayerState{};
        ChatSessionRegistry::Endpoint Origin, Destination;
        uint64_t OriginToken = 0, DestinationToken = 0, OuterInvocation = 0, LastInvocation = 0;
        Mode CurrentMode = Mode::Ordinary;
        std::vector<Delivery> Delivered;
        unsigned WorldCalls = 0, TeleportCalls = 0;
        bool ValidOrigin = true, ValidDestination = true, Nested = false, CallbackPassed = false;
    };
    bool Validate(const ChatSessionRegistry::Endpoint& endpoint, void* data) noexcept
    {
        const auto& state = *static_cast<State*>(data);
        const auto equal = [&](const auto& other) {
            return endpoint.Controller == other.Controller && endpoint.Connection == other.Connection && endpoint.PlayerState == other.PlayerState;
        };
        return (state.ValidOrigin && equal(state.Origin)) || (state.ValidDestination && equal(state.Destination));
    }
    bool Send(const ChatSessionRegistry::Endpoint& endpoint, std::string_view text, void* data) noexcept
    {
        try
        {
            auto& state = *static_cast<State*>(data); state.Delivered.push_back({endpoint.Controller, std::string(text)});
            if (state.CurrentMode == Mode::SendInvalidatesOrigin)
            {
                state.Sessions.InvalidateController(state.Origin.Controller);
                state.OriginToken = state.Sessions.Observe(state.Origin, "Origin reconnected");
            }
            return true;
        }
        catch (...) { return false; }
    }
    bool CaptureWorld(void* controller, ObeliskCommandWorldInfo* out, void* data) noexcept
    {
        try
        {
            auto& state = *static_cast<State*>(data); ++state.WorldCalls;
            if (controller != state.Origin.Controller || !out || out->struct_size < sizeof(*out)) return false;
            const auto old = state.OriginToken;
            if (state.CurrentMode == Mode::RolloverReturnNew || state.CurrentMode == Mode::RolloverReturnOld)
            {
                state.Sessions.InvalidateController(state.Origin.Controller);
                state.OriginToken = state.Sessions.Observe(state.Origin, "Origin reconnected");
            }
            *out = {}; out->abi_version = OBELISK_COMMAND_WORLD_INFO_ABI_VERSION; out->struct_size = sizeof(*out);
            out->flags = OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE; out->x = 100; out->y = 200; out->z = 300;
            out->process_epoch = 700; out->session_token = state.CurrentMode == Mode::RolloverReturnOld ? old : state.OriginToken;
            return true;
        }
        catch (...) { return false; }
    }
    bool Teleport(void* controller, const ObeliskCommandWorldInfo* destination, void* data) noexcept
    {
        auto& state = *static_cast<State*>(data); ++state.TeleportCalls;
        return controller == state.Origin.Controller && destination && std::isfinite(destination->x) &&
            std::isfinite(destination->y) && std::isfinite(destination->z);
    }
    bool Reply(void* controller, std::string_view text, void* data) noexcept
    {
        try { static_cast<State*>(data)->Delivered.push_back({controller, std::string(text)}); return true; }
        catch (...) { return false; }
    }
    ObeliskChatSession SessionBuffer()
    { ObeliskChatSession value{}; value.abi_version = OBELISK_CHAT_SESSION_ABI_VERSION; value.struct_size = sizeof(value); return value; }
    ObeliskCommandWorldInfo WorldBuffer()
    { ObeliskCommandWorldInfo value{}; value.abi_version = OBELISK_COMMAND_WORLD_INFO_ABI_VERSION; value.struct_size = sizeof(value); return value; }
    void Nested(const ObeliskCommandInvocation* invocation, void* data)
    {
        auto& state = *static_cast<State*>(data); auto current = SessionBuffer();
        state.Nested = !state.Commands.GetChatSession(&state.Owner, state.OuterInvocation, &current) &&
            !state.Commands.SendChatToSession(&state.Owner, state.OuterInvocation, state.DestinationToken, 700, "outer") &&
            state.Commands.GetChatSession(&state.Owner, invocation->invocation_token, &current);
    }
    void Invoke(const ObeliskCommandInvocation* invocation, void* data)
    {
        auto& state = *static_cast<State*>(data); state.LastInvocation = invocation->invocation_token;
        const auto token = invocation->invocation_token; auto current = SessionBuffer(); auto world = WorldBuffer();
        bool passed = state.Commands.GetChatSession(&state.Owner, token, &current) && current.session_token == state.OriginToken && current.process_epoch == 700;
        if (state.CurrentMode == Mode::RolloverReturnNew || state.CurrentMode == Mode::RolloverReturnOld)
        {
            const auto oldToken = current.session_token;
            passed &= !state.Commands.GetWorldInfo(&state.Owner, token, &world) &&
                oldToken != state.OriginToken && !state.Commands.GetChatSession(&state.Owner, token, &current) &&
                !state.Commands.Reply(&state.Owner, token, "stale reply") &&
                !state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "stale origin");
            state.CallbackPassed = passed; return;
        }
        if (state.CurrentMode == Mode::SendInvalidatesOrigin)
        {
            passed &= state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "first") &&
                !state.Commands.Reply(&state.Owner, token, "reply after relogin") &&
                !state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "after relogin");
            state.CallbackPassed = passed; return;
        }
        std::array<ObeliskChatSession, 2> list{SessionBuffer(), SessionBuffer()}; size_t written = 0, total = 0;
        passed &= state.Commands.ListChatSessions(&state.Owner, token, list.data(), list.size(), &written, &total) && written == 2 && total == 2;
        passed &= state.Commands.GetWorldInfo(&state.Owner, token, &world) && world.session_token == state.OriginToken && world.x == 100;
        passed &= !state.Commands.GetChatSession(&state.OtherOwner, token, &current) &&
            !state.Commands.GetChatSession(&state.Owner, token + 1, &current) &&
            !state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 701, "wrong epoch") &&
            !state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken + 100, 700, "unknown destination");
        bool workerAccepted = false;
        std::thread worker([&] {
            auto session = SessionBuffer(); auto pose = WorldBuffer();
            workerAccepted = state.Commands.GetChatSession(&state.Owner, token, &session) ||
                state.Commands.ListChatSessions(&state.Owner, token, list.data(), list.size(), &written, &total) ||
                state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "worker") ||
                state.Commands.GetWorldInfo(&state.Owner, token, &pose) || state.Commands.TeleportOrigin(&state.Owner, token, &world);
        }); worker.join(); passed &= !workerAccepted;
        {
            GameplayCallbackScope otherScope(GameplayCallbackFamily::Timer, GameplayCallbackScope::TrackingMode::CurrentOnly);
            passed &= !state.Commands.GetChatSession(&state.Owner, token, &current) &&
                !state.Commands.GetWorldInfo(&state.Owner, token, &world) &&
                !state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "other scope") &&
                !state.Commands.TeleportOrigin(&state.Owner, token, &world);
        }
        state.OuterInvocation = token;
        const CommandRuntimeContext context{state.OriginToken, CaptureWorld, &state, Teleport};
        passed &= state.Commands.Dispatch(state.Origin.Controller, "/nested-session", 0, Reply, &state, nullptr, &context) == 1 && state.Nested;
        passed &= state.Commands.GetChatSession(&state.Owner, token, &current) &&
            state.Commands.SendChatToSession(&state.Owner, token, state.DestinationToken, 700, "correct destination") &&
            state.Delivered.back().Controller == state.Destination.Controller;
        world.session_token = state.OriginToken; world.process_epoch = 701;
        passed &= !state.Commands.TeleportOrigin(&state.Owner, token, &world); world.process_epoch = 700;
        world.session_token = state.DestinationToken; passed &= !state.Commands.TeleportOrigin(&state.Owner, token, &world);
        world.session_token = state.OriginToken; passed &= state.Commands.TeleportOrigin(&state.Owner, token, &world);
        state.CallbackPassed = passed;
    }
}

void TestCommandSessionIntegration()
{
    State state; state.Origin = {&state.First, &state.FirstConnection, &state.FirstPlayerState};
    state.Destination = {&state.Second, &state.SecondConnection, &state.SecondPlayerState};
    Require(state.Sessions.Configure(700, Validate, Send, &state), "session configure failed");
    state.Commands.SetAvailable(true); state.Commands.SetChatSessionRegistry(&state.Sessions);
    state.Commands.SetWorldInfoAvailable(true); state.Commands.SetSelfTeleportAvailable(true);
    state.OriginToken = state.Sessions.Observe(state.Origin, "Origin 玩家"); state.DestinationToken = state.Sessions.Observe(state.Destination, "Destination");
    Require(state.OriginToken && state.DestinationToken &&
        state.Commands.Register(&state.Owner, "/session-test", Invoke, &state) &&
        state.Commands.Register(&state.Owner, "/nested-session", Nested, &state), "session fixtures did not register");
    auto run = [&](Mode mode) {
        state.CurrentMode = mode; state.CallbackPassed = false;
        const CommandRuntimeContext context{state.OriginToken, CaptureWorld, &state, Teleport};
        Require(state.Commands.Dispatch(state.Origin.Controller, "/session-test", 0, Reply, &state, nullptr, &context) == 1 && state.CallbackPassed,
            "command session scope, destination or stale-origin contract failed");
    };
    run(Mode::Ordinary);
    auto session = SessionBuffer(); auto world = WorldBuffer();
    Require(!state.Commands.GetChatSession(&state.Owner, state.LastInvocation, &session) &&
        !state.Commands.Reply(&state.Owner, state.LastInvocation, "expired reply") &&
        !state.Commands.SendChatToSession(&state.Owner, state.LastInvocation, state.DestinationToken, 700, "expired") &&
        !state.Commands.GetWorldInfo(&state.Owner, state.LastInvocation, &world) &&
        !state.Commands.TeleportOrigin(&state.Owner, state.LastInvocation, &world), "retained command scope remained active");
    const auto oldDestination = state.DestinationToken;
    state.Sessions.InvalidateController(state.Destination.Controller);
    state.DestinationToken = state.Sessions.Observe(state.Destination, "Destination reconnected");
    Require(oldDestination != state.DestinationToken && !state.Sessions.Deliver(oldDestination, 700, "old destination"),
        "address reuse revived destination token");
    run(Mode::RolloverReturnNew); run(Mode::RolloverReturnOld); run(Mode::SendInvalidatesOrigin); run(Mode::Ordinary);
    Require(state.Commands.UnregisterCallbacksForOwner(&state.Owner) == 2, "session test cleanup failed");
}
