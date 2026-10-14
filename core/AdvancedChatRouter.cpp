#include "AdvancedChatRouter.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace Obelisk::Core
{
    namespace
    {
        bool Same(AdvancedChatSession a, AdvancedChatSession b) noexcept
        { return a.Id == b.Id && a.Generation == b.Generation; }
        bool Valid(AdvancedChatSession session) noexcept { return session.Id && session.Generation; }
        bool Text(std::string_view value, size_t maximum) noexcept
        {
            if (value.empty() || value.size() > maximum) return false;
            for (size_t i = 0; i < value.size();)
            {
                const auto head = static_cast<unsigned char>(value[i++]);
                if (!head || head == '\r' || head == '\n') return false;
                if (head < 0x80) continue;
                uint32_t scalar = 0, minimum = 0; size_t count = 0;
                if (head >= 0xc2 && head <= 0xdf) scalar = head & 31, minimum = 0x80, count = 1;
                else if (head >= 0xe0 && head <= 0xef) scalar = head & 15, minimum = 0x800, count = 2;
                else if (head >= 0xf0 && head <= 0xf4) scalar = head & 7, minimum = 0x10000, count = 3;
                else return false;
                if (count > value.size() - i) return false;
                while (count--)
                {
                    const auto tail = static_cast<unsigned char>(value[i++]);
                    if ((tail & 0xc0) != 0x80) return false;
                    scalar = (scalar << 6) | (tail & 63);
                }
                if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff)) return false;
            }
            return true;
        }
        bool Position(const AdvancedChatPosition& value) noexcept
        {
            return std::isfinite(value.X) && std::isfinite(value.Y) && std::isfinite(value.Z) &&
                std::abs(value.X) <= 100000000 && std::abs(value.Y) <= 100000000 && std::abs(value.Z) <= 100000000;
        }
    }
    AdvancedChatRouter::AdvancedChatRouter() : AdvancedChatRouter(Settings{}) {}
    AdvancedChatRouter::AdvancedChatRouter(Settings settings) : m_Settings(settings)
    {
        if (!std::isfinite(settings.LocalRadius) || settings.LocalRadius <= 0 || settings.LocalRadius > 100000000 ||
            !settings.BurstMessages || settings.BurstMessages > 1000 || settings.RateWindowMilliseconds <= 0 ||
            settings.RateWindowMilliseconds > 86400000 || !settings.MaxSessions || settings.MaxSessions > 100000)
            throw std::invalid_argument("Invalid advanced chat settings");
    }
    AdvancedChatStatus AdvancedChatRouter::Upsert(const AdvancedChatPresence& presence)
    {
        if (!Valid(presence.Session) || !Text(presence.DisplayName, 256) ||
            !Text(presence.WorldFingerprint, 256) || (presence.Tribe && !*presence.Tribe) ||
            (presence.Position && !Position(*presence.Position))) return AdvancedChatStatus::InvalidArgument;
        std::lock_guard lock(m_Mutex);
        auto found = m_Sessions.find(presence.Session.Id);
        if (found == m_Sessions.end())
        {
            if (m_Sessions.size() >= m_Settings.MaxSessions) return AdvancedChatStatus::CapacityReached;
            m_Sessions.emplace(presence.Session.Id, State{presence});
        }
        else
        {
            if (presence.Session.Generation < found->second.Presence.Session.Generation) return AdvancedChatStatus::StaleSession;
            if (presence.Session.Generation == found->second.Presence.Session.Generation)
            {
                if (!found->second.Connected) return AdvancedChatStatus::StaleSession;
                found->second.Presence = presence;
            }
            else found->second = State{presence};
        }
        return AdvancedChatStatus::Ok;
    }
    bool AdvancedChatRouter::Disconnect(AdvancedChatSession session)
    {
        std::lock_guard lock(m_Mutex);
        const auto found = m_Sessions.find(session.Id);
        if (found == m_Sessions.end() || !found->second.Connected || !Same(found->second.Presence.Session, session)) return false;
        found->second.Connected = false; found->second.SentAt.clear(); return true;
    }
    AdvancedChatStatus AdvancedChatRouter::Mute(AdvancedChatSession session, std::optional<int64_t> until)
    {
        if (!Valid(session) || (until && *until < 0)) return AdvancedChatStatus::InvalidArgument;
        std::lock_guard lock(m_Mutex);
        const auto found = m_Sessions.find(session.Id);
        if (found == m_Sessions.end() || !found->second.Connected) return AdvancedChatStatus::UnknownSession;
        if (!Same(found->second.Presence.Session, session)) return AdvancedChatStatus::StaleSession;
        found->second.MutedUntil = until; return AdvancedChatStatus::Ok;
    }
    AdvancedChatPlan AdvancedChatRouter::Plan(AdvancedChatSession sender, AdvancedChatChannel channel,
        std::string_view message, int64_t now, std::optional<AdvancedChatSession> target)
    {
        AdvancedChatPlan plan; plan.Sender = sender; plan.Channel = channel;
        if (!Valid(sender) || !Text(message, 1024) || now < 0 ||
            (channel != AdvancedChatChannel::Global && channel != AdvancedChatChannel::Local &&
             channel != AdvancedChatChannel::Tribe && channel != AdvancedChatChannel::Whisper) ||
            (channel == AdvancedChatChannel::Whisper ? !target || !Valid(*target) : target.has_value())) return plan;
        std::lock_guard lock(m_Mutex);
        const auto found = m_Sessions.find(sender.Id);
        if (found == m_Sessions.end() || !found->second.Connected) { plan.Status = AdvancedChatStatus::UnknownSession; return plan; }
        auto& state = found->second;
        if (!Same(state.Presence.Session, sender)) { plan.Status = AdvancedChatStatus::StaleSession; return plan; }
        if (now < state.LastClock) { plan.Status = AdvancedChatStatus::ClockRegression; return plan; }
        state.LastClock = now;
        if (state.MutedUntil && now < *state.MutedUntil) { plan.Status = AdvancedChatStatus::Muted; return plan; }
        if (state.MutedUntil) state.MutedUntil.reset();
        if ((channel == AdvancedChatChannel::Local && !state.Presence.Position) ||
            (channel == AdvancedChatChannel::Tribe && !state.Presence.Tribe))
        { plan.Status = AdvancedChatStatus::MissingContext; return plan; }
        if (channel == AdvancedChatChannel::Whisper)
        {
            const auto destination = m_Sessions.find(target->Id);
            if (destination == m_Sessions.end() || !destination->second.Connected || !Same(destination->second.Presence.Session, *target))
            { plan.Status = AdvancedChatStatus::RecipientUnavailable; return plan; }
        }
        // Subtraction cannot overflow because nonnegative times are ordered.
        std::erase_if(state.SentAt, [&](int64_t at) { return now - at >= m_Settings.RateWindowMilliseconds; });
        if (state.SentAt.size() >= m_Settings.BurstMessages) { plan.Status = AdvancedChatStatus::RateLimited; return plan; }
        for (const auto& [id, recipient] : m_Sessions)
        {
            const auto& presence = recipient.Presence;
            if (!recipient.Connected) continue;
            bool include = false;
            switch (channel)
            {
                case AdvancedChatChannel::Global:
                    include = presence.WorldFingerprint == state.Presence.WorldFingerprint; break;
                case AdvancedChatChannel::Local:
                    if (presence.Position && presence.WorldFingerprint == state.Presence.WorldFingerprint)
                    {
                        const auto& a = *state.Presence.Position; const auto& b = *presence.Position;
                        include = std::hypot(a.X - b.X, a.Y - b.Y, a.Z - b.Z) <= m_Settings.LocalRadius;
                    }
                    break;
                case AdvancedChatChannel::Tribe:
                    include = presence.WorldFingerprint == state.Presence.WorldFingerprint &&
                        presence.Tribe && presence.Tribe == state.Presence.Tribe; break;
                case AdvancedChatChannel::Whisper:
                    include = Same(presence.Session, sender) || Same(presence.Session, *target); break;
            }
            if (include) plan.Recipients.push_back(presence.Session);
        }
        std::sort(plan.Recipients.begin(), plan.Recipients.end(), [](auto a, auto b) { return a.Id < b.Id; });
        plan.Text = message; plan.WorldFingerprint = state.Presence.WorldFingerprint;
        plan.Tribe = state.Presence.Tribe; plan.Status = AdvancedChatStatus::Ok;
        state.SentAt.push_back(now); return plan;
    }
    bool AdvancedChatRouter::IsDeliverable(const AdvancedChatPlan& plan, AdvancedChatSession destination) const
    {
        if (plan.Status != AdvancedChatStatus::Ok || !Valid(plan.Sender) || !Valid(destination) ||
            std::none_of(plan.Recipients.begin(), plan.Recipients.end(), [&](auto value) { return Same(value, destination); })) return false;
        std::lock_guard lock(m_Mutex);
        const auto sender = m_Sessions.find(plan.Sender.Id), recipient = m_Sessions.find(destination.Id);
        if (sender == m_Sessions.end() || recipient == m_Sessions.end() || !sender->second.Connected ||
            !recipient->second.Connected || !Same(sender->second.Presence.Session, plan.Sender) ||
            !Same(recipient->second.Presence.Session, destination) || sender->second.MutedUntil) return false;
        const auto& a = sender->second.Presence; const auto& b = recipient->second.Presence;
        if (plan.Channel == AdvancedChatChannel::Whisper) return true;
        if (a.WorldFingerprint != plan.WorldFingerprint || b.WorldFingerprint != plan.WorldFingerprint) return false;
        if (plan.Channel == AdvancedChatChannel::Global) return true;
        if (plan.Channel == AdvancedChatChannel::Tribe)
            return plan.Tribe && a.Tribe == plan.Tribe && b.Tribe == plan.Tribe;
        return a.Position && b.Position &&
            std::hypot(a.Position->X - b.Position->X, a.Position->Y - b.Position->Y, a.Position->Z - b.Position->Z) <= m_Settings.LocalRadius;
    }
}
