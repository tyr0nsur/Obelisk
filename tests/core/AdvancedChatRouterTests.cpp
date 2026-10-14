#include "core/AdvancedChatRouter.h"
#include <iostream>
#include <limits>
#include <stdexcept>

namespace
{
    using namespace Obelisk::Core;
    using Status = AdvancedChatStatus;
    void Require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
    AdvancedChatPresence Presence(uint64_t id, uint64_t generation, uint64_t tribe, double x,
        std::string world = "TheIsland:save-A")
    { return {{id, generation}, "Player", std::move(world), tribe, AdvancedChatPosition{x, 0, 0}}; }
    void RoutingAndContext()
    {
        AdvancedChatRouter router({100, 20, 1000, 20});
        Require(router.Upsert(Presence(1, 1, 3, 0)) == Status::Ok &&
            router.Upsert(Presence(2, 1, 3, 100)) == Status::Ok &&
            router.Upsert(Presence(3, 1, 4, 101)) == Status::Ok &&
            router.Upsert(Presence(4, 1, 3, 0, "TheIsland:save-B")) == Status::Ok, "presence failed");
        const auto global = router.Plan({1, 1}, AdvancedChatChannel::Global, "hola", 10);
        const auto local = router.Plan({1, 1}, AdvancedChatChannel::Local, "cerca", 10);
        const auto tribe = router.Plan({1, 1}, AdvancedChatChannel::Tribe, "tribu", 10);
        const auto whisper = router.Plan({1, 1}, AdvancedChatChannel::Whisper, "privado", 10, {{4, 1}});
        Require(global.Status == Status::Ok && global.Recipients.size() == 3 && local.Recipients.size() == 2 &&
            tribe.Recipients.size() == 2 && whisper.Recipients.size() == 2, "channel recipients crossed boundaries");
        Require(router.IsDeliverable(tribe, {2, 1}) && !router.IsDeliverable(tribe, {3, 1}), "recipient membership lost");
        Require(router.Upsert(Presence(2, 1, 4, 200)) == Status::Ok && !router.IsDeliverable(tribe, {2, 1}) &&
            !router.IsDeliverable(local, {2, 1}), "queued messages ignored changed tribe/position");
        Require(router.Plan({1, 1}, AdvancedChatChannel::Whisper, "old", 10, {{4, 2}}).Status == Status::RecipientUnavailable,
            "unknown target generation accepted");
        Require(router.Upsert({{5, 1}, "No contexto", "TheIsland:save-A", {}, {}}) == Status::Ok &&
            router.Plan({5, 1}, AdvancedChatChannel::Tribe, "no", 10).Status == Status::MissingContext &&
            router.Plan({5, 1}, AdvancedChatChannel::Local, "no", 10).Status == Status::MissingContext,
            "missing native context invented");
    }
    void SessionsMuteAndRate()
    {
        AdvancedChatRouter router({100, 2, 1000, 3});
        Require(router.Upsert(Presence(1, 10, 3, 0)) == Status::Ok && router.Upsert(Presence(2, 10, 3, 0)) == Status::Ok, "presence failed");
        const auto old = router.Plan({1, 10}, AdvancedChatChannel::Global, "uno", 100);
        Require(router.Plan({1, 10}, AdvancedChatChannel::Global, "dos", 100).Status == Status::Ok &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "tres", 100).Status == Status::RateLimited &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "clock", 99).Status == Status::ClockRegression &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "cuatro", 1099).Status == Status::RateLimited &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "cinco", 1100).Status == Status::Ok,
            "rate window or regression boundary failed");
        Require(router.Mute({1, 10}, 2000) == Status::Ok &&
            !router.IsDeliverable(old, {2, 10}) &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "muted", 1999).Status == Status::Muted &&
            router.Plan({1, 10}, AdvancedChatChannel::Global, "end", 2000).Status == Status::Ok, "mute expiry wrong");
        Require(router.Disconnect({2, 10}) && !router.IsDeliverable(old, {2, 10}) &&
            router.Upsert(Presence(2, 10, 3, 0)) == Status::StaleSession &&
            router.Upsert(Presence(2, 11, 3, 0)) == Status::Ok && !router.IsDeliverable(old, {2, 11}) &&
            !router.Disconnect({2, 10}), "disconnect/reconnect revived stale destination");
        Require(router.Upsert(Presence(1, 9, 3, 0)) == Status::StaleSession &&
            router.Mute({1, 9}, 10000) == Status::StaleSession, "old generation mutated current session");
        Require(router.Disconnect({1, 10}) && !router.IsDeliverable(old, {1, 10}), "disconnected sender remained deliverable");
        Require(router.Upsert(Presence(1, 11, 3, 0)) == Status::Ok &&
            router.Plan({1, 11}, AdvancedChatChannel::Global, "new", 0).Status == Status::Ok, "new generation kept previous rate/mute");
    }
    void InputAndCapacity()
    {
        AdvancedChatRouter router({100, 1, 1000, 1});
        Require(router.Upsert(Presence(1, 1, 3, 0)) == Status::Ok &&
            router.Upsert(Presence(2, 1, 3, 0)) == Status::CapacityReached, "unbounded session storage");
        auto invalid = Presence(1, 1, 3, 0); invalid.Position->X = std::numeric_limits<double>::quiet_NaN();
        Require(router.Upsert(invalid) == Status::InvalidArgument &&
            router.Plan({1, 1}, AdvancedChatChannel::Global, std::string("x\0y", 3), 0).Status == Status::InvalidArgument &&
            router.Plan({1, 1}, AdvancedChatChannel::Global, "a\nb", 0).Status == Status::InvalidArgument &&
            router.Plan({1, 1}, AdvancedChatChannel::Global, std::string("\xed\xa0\x80", 3), 0).Status == Status::InvalidArgument,
            "invalid coordinates/control/UTF-8 accepted");
        const auto utf8 = router.Plan({1, 1}, AdvancedChatChannel::Global, "Hola 玩家 🙂", 0);
        Require(utf8.Status == Status::Ok && utf8.Text == "Hola 玩家 🙂", "UTF-8 copy failed");
    }
}
int main()
{
    try { RoutingAndContext(); SessionsMuteAndRate(); InputAndCapacity(); }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
    return 0;
}
