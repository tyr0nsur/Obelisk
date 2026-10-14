#pragma once

#include <cstdint>
#include <cstddef>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace Obelisk::Core
{
    enum class AdvancedChatChannel { Global, Local, Tribe, Whisper };
    enum class AdvancedChatStatus
    {
        Ok, InvalidArgument, UnknownSession, StaleSession, MissingContext,
        Muted, RateLimited, RecipientUnavailable, ClockRegression, CapacityReached
    };
    // Private copied session handles supplied by a verified native adapter.
    // Account IDs and display names are deliberately absent from the handle.
    struct AdvancedChatSession { uint64_t Id = 0, Generation = 0; };
    struct AdvancedChatPosition { double X = 0, Y = 0, Z = 0; };
    struct AdvancedChatPresence
    {
        AdvancedChatSession Session;
        std::string DisplayName;
        std::string WorldFingerprint;
        std::optional<uint64_t> Tribe;
        std::optional<AdvancedChatPosition> Position;
    };
    struct AdvancedChatPlan
    {
        AdvancedChatStatus Status = AdvancedChatStatus::InvalidArgument;
        AdvancedChatSession Sender;
        AdvancedChatChannel Channel = AdvancedChatChannel::Global;
        std::string Text;
        std::string WorldFingerprint;
        std::optional<uint64_t> Tribe;
        std::vector<AdvancedChatSession> Recipients;
    };
    class AdvancedChatRouter
    {
    public:
        struct Settings
        {
            double LocalRadius = 10000;
            uint32_t BurstMessages = 5;
            int64_t RateWindowMilliseconds = 3000;
            // Bounds tracked identifiers INCLUDING disconnected tombstones.
            // A reconnect must increase generation; a retired handle never revives.
            size_t MaxSessions = 1024;
        };
        AdvancedChatRouter();
        explicit AdvancedChatRouter(Settings settings);
        // Caller serializes native lifecycle observations. A greater generation
        // replaces presence, mute and rate state; an old generation never does.
        AdvancedChatStatus Upsert(const AdvancedChatPresence& presence);
        bool Disconnect(AdvancedChatSession session);
        AdvancedChatStatus Mute(AdvancedChatSession session, std::optional<int64_t> untilMilliseconds);
        // Monotonic caller clock; a rejected clock must never reset rate state.
        // Plans copy all destinations. They are not delivery or authorization.
        AdvancedChatPlan Plan(AdvancedChatSession sender, AdvancedChatChannel channel,
            std::string_view message, int64_t nowMilliseconds,
            std::optional<AdvancedChatSession> whisperTarget = std::nullopt);
        // Must be called immediately before EACH native send, with the sender
        // and destination. Disconnect/reconnect invalidates outstanding plans.
        bool IsDeliverable(const AdvancedChatPlan& plan, AdvancedChatSession destination) const;
    private:
        struct State
        {
            AdvancedChatPresence Presence;
            bool Connected = true;
            std::optional<int64_t> MutedUntil;
            int64_t LastClock = -1;
            std::vector<int64_t> SentAt;
        };
        Settings m_Settings;
        mutable std::mutex m_Mutex;
        std::unordered_map<uint64_t, State> m_Sessions;
    };
}
