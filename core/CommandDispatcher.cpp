#include "CommandDispatcher.h"
#include "GameplayCallbackScope.h"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <thread>

namespace Obelisk::Core
{
    namespace
    {
        struct InvocationScope
        {
            CommandDispatcher* Dispatcher;
            void* Owner;
            uint64_t Token;
            void* Controller;
            CommandDispatcher::ReplyBackend Backend;
            void* BackendData;
            std::thread::id Thread;
            const ObeliskCommandPlayer* Player;
            const GameplayCallbackScope* CallbackScope = nullptr;
            InvocationScope* Previous;
        };

        thread_local InvocationScope* g_CurrentInvocation = nullptr;
        std::atomic<uint64_t> g_NextInvocationToken{1};

        uint64_t AllocateInvocationToken() noexcept
        {
            uint64_t next = g_NextInvocationToken.load(std::memory_order_relaxed);
            while (next != std::numeric_limits<uint64_t>::max())
            {
                if (g_NextInvocationToken.compare_exchange_weak(next, next + 1, std::memory_order_relaxed))
                    return next;
            }
            // Never reuse an expired token, even on counter exhaustion.
            return 0;
        }

        bool IsInsideDispatcherCallback(CommandDispatcher* dispatcher)
        {
            for (auto* invocation = g_CurrentInvocation; invocation; invocation = invocation->Previous)
                if (invocation->Dispatcher == dispatcher)
                    return true;
            return false;
        }

        bool ValidCommand(std::string_view command)
        {
            if (command.size() < 2 || command.size() > 64 || command.front() != '/')
                return false;
            for (const unsigned char ch : command.substr(1))
                if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                      (ch >= '0' && ch <= '9') || ch == '_' || ch == '-'))
                    return false;
            return true;
        }

        bool ValidUtf8(std::string_view text)
        {
            if (!text.data())
                return false;
            for (size_t i = 0; i < text.size();)
            {
                const auto first = static_cast<unsigned char>(text[i++]);
                if (first == 0)
                    return false;
                if (first < 0x80)
                    continue;
                size_t continuation = 0;
                uint32_t scalar = 0;
                uint32_t minimum = 0;
                if (first >= 0xc2 && first <= 0xdf)
                    continuation = 1, scalar = first & 0x1f, minimum = 0x80;
                else if (first >= 0xe0 && first <= 0xef)
                    continuation = 2, scalar = first & 0x0f, minimum = 0x800;
                else if (first >= 0xf0 && first <= 0xf4)
                    continuation = 3, scalar = first & 0x07, minimum = 0x10000;
                else
                    return false;
                if (text.size() - i < continuation)
                    return false;
                while (continuation--)
                {
                    const auto next = static_cast<unsigned char>(text[i++]);
                    if ((next & 0xc0) != 0x80)
                        return false;
                    scalar = (scalar << 6) | (next & 0x3f);
                }
                if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff))
                    return false;
            }
            return true;
        }
    }

    CommandDispatcher& CommandDispatcher::Get()
    {
        static auto* dispatcher = new CommandDispatcher;
        return *dispatcher;
    }

    void CommandDispatcher::SetAvailable(bool available) noexcept
    {
        m_Available.store(available, std::memory_order_release);
    }

    bool CommandDispatcher::IsAvailable() const noexcept
    {
        return m_Available.load(std::memory_order_acquire);
    }

    void CommandDispatcher::SetPlayerSnapshotsAvailable(bool available) noexcept
    {
        m_PlayerSnapshotsAvailable.store(available, std::memory_order_release);
    }

    bool CommandDispatcher::IsPlayerSnapshotsAvailable() const noexcept
    {
        return IsAvailable() && m_PlayerSnapshotsAvailable.load(std::memory_order_acquire);
    }

    uint64_t CommandDispatcher::Register(void* owner, std::string_view command,
                                         ObeliskCommandCallback callback, void* userData)
    {
        if (!IsAvailable() || !owner || !callback || !ValidCommand(command))
            return 0;
        auto registration = std::make_shared<Registration>();
        registration->Owner = owner;
        registration->Command = command;
        registration->Callback = callback;
        registration->UserData = userData;
        std::lock_guard lock(m_Mutex);
        if (!IsAvailable() || m_NextRegistrationId == std::numeric_limits<uint64_t>::max())
            return 0;
        registration->Id = m_NextRegistrationId++;
        m_Registrations.push_back(registration);
        return registration->Id;
    }

    void CommandDispatcher::PruneInactiveLocked()
    {
        std::erase_if(m_Registrations, [](const auto& entry) { return !entry->Active && entry->InFlight == 0; });
    }

    bool CommandDispatcher::Unregister(void* owner, uint64_t registrationId)
    {
        if (!owner || !registrationId)
            return false;
        std::unique_lock lock(m_Mutex);
        const auto found = std::find_if(m_Registrations.begin(), m_Registrations.end(), [&](const auto& entry) {
            return entry->Owner == owner && entry->Id == registrationId;
        });
        if (found == m_Registrations.end() || !(*found)->Active)
            return false;
        auto registration = *found;
        registration->Active = false;
        if (!IsInsideDispatcherCallback(this))
            m_Quiescence.wait(lock, [&] { return registration->InFlight == 0; });
        PruneInactiveLocked();
        return true;
    }

    bool CommandDispatcher::HasOwnerInvocationsLocked(void* owner) const
    {
        return std::any_of(m_Registrations.begin(), m_Registrations.end(), [owner](const auto& entry) {
            return entry->Owner == owner && entry->InFlight != 0;
        });
    }

    size_t CommandDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;
        std::unique_lock lock(m_Mutex);
        size_t removed = 0;
        for (const auto& registration : m_Registrations)
        {
            if (registration->Owner == owner && registration->Active)
            {
                registration->Active = false;
                ++removed;
            }
        }
        // PluginManager must retain the mapping if unload was attempted inside a
        // callback: returning successfully would allow dlclose on its own stack.
        if (IsInsideDispatcherCallback(this) && HasOwnerInvocationsLocked(owner))
            throw std::logic_error("command owner cleanup requires returning from the callback before unload");
        m_Quiescence.wait(lock, [&] { return !HasOwnerInvocationsLocked(owner); });
        PruneInactiveLocked();
        return removed;
    }

    size_t CommandDispatcher::SubscriptionCount() const
    {
        std::lock_guard lock(m_Mutex);
        return std::count_if(m_Registrations.begin(), m_Registrations.end(), [](const auto& entry) { return entry->Active; });
    }

    void CommandDispatcher::FinishInvocation(const std::shared_ptr<Registration>& registration) noexcept
    {
        {
            std::lock_guard lock(m_Mutex);
            --registration->InFlight;
            PruneInactiveLocked();
        }
        m_Quiescence.notify_all();
    }

    size_t CommandDispatcher::Dispatch(void* controller, std::string_view message, uint32_t sendMode,
                                        ReplyBackend backend, void* backendData, const CommandPlayerSnapshot* player)
    {
        if (!IsAvailable() || !controller || !backend || sendMode > 3 ||
            message.empty() || message.size() > 4096 || !ValidUtf8(message))
            return 0;
        std::vector<std::shared_ptr<Registration>> callbacks;
        {
            std::lock_guard lock(m_Mutex);
            for (const auto& registration : m_Registrations)
                if (registration->Active && registration->Command == message)
                    callbacks.push_back(registration);
        }
        if (callbacks.empty())
            return 0;
        const std::string copiedMessage(message);
        // Copy before entering any plugin callback. Plugin reentrancy and adapter
        // buffer reuse cannot change this invocation's name or native ID.
        constexpr auto knownFlags = OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE |
                                    OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE;
        const bool hasSnapshot = IsPlayerSnapshotsAvailable() && player && !(player->Flags & ~knownFlags);
        std::string copiedName;
        std::string copiedId;
        uint64_t playerFlags = 0;
        if (hasSnapshot)
        {
            const auto copyField = [&](uint64_t flag, std::string_view input, size_t maximum, std::string& copy) {
                if ((player->Flags & flag) && !input.empty() && input.size() <= maximum && ValidUtf8(input))
                {
                    copy.assign(input);
                    playerFlags |= flag;
                }
            };
            copyField(OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE, player->PlayerName,
                      OBELISK_COMMAND_PLAYER_NAME_MAX_BYTES, copiedName);
            copyField(OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE, player->PlatformId,
                      OBELISK_COMMAND_PLAYER_PLATFORM_ID_MAX_BYTES, copiedId);
        }
        const ObeliskCommandPlayer copiedPlayer{
            OBELISK_COMMAND_PLAYER_ABI_VERSION, sizeof(ObeliskCommandPlayer), playerFlags,
            {(playerFlags & OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE) ? copiedName.data() : nullptr, copiedName.size()},
            {(playerFlags & OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE) ? copiedId.data() : nullptr, copiedId.size()}};
        size_t dispatched = 0;
        for (const auto& registration : callbacks)
        {
            const uint64_t token = AllocateInvocationToken();
            if (!token)
                break;
            {
                std::lock_guard lock(m_Mutex);
                if (!registration->Active || !IsAvailable())
                    continue;
                ++registration->InFlight;
            }
            InvocationScope invocation{this, registration->Owner, token, controller, backend,
                                       backendData, std::this_thread::get_id(), hasSnapshot ? &copiedPlayer : nullptr,
                                       nullptr, g_CurrentInvocation};
            g_CurrentInvocation = &invocation;
            const ObeliskCommandInvocation event{
                OBELISK_COMMAND_INVOCATION_ABI_VERSION, sizeof(ObeliskCommandInvocation), sendMode,
                0, token, {copiedMessage.data(), copiedMessage.size()}};
            try
            {
                GameplayCallbackScope callbackScope(GameplayCallbackFamily::Command);
                invocation.CallbackScope = &callbackScope;
                registration->Callback(&event, registration->UserData);
                ++dispatched;
            }
            catch (...)
            {
                // A failing plugin cannot strand an invocation token or cleanup.
            }
            g_CurrentInvocation = invocation.Previous;
            FinishInvocation(registration);
        }
        return dispatched;
    }

    bool CommandDispatcher::Reply(void* owner, uint64_t invocationToken, std::string_view reply) noexcept
    {
        auto* invocation = g_CurrentInvocation;
        if (!IsAvailable() || !owner || !invocationToken || !invocation ||
            invocation->Dispatcher != this || invocation->Owner != owner ||
            invocation->Token != invocationToken || invocation->Thread != std::this_thread::get_id() ||
            !invocation->CallbackScope || GameplayCallbackScope::Current() != invocation->CallbackScope ||
            reply.empty() || reply.size() > 1024 || !ValidUtf8(reply))
            return false;
        return invocation->Backend(invocation->Controller, reply, invocation->BackendData);
    }

    bool CommandDispatcher::GetPlayer(void* owner, uint64_t invocationToken, ObeliskCommandPlayer* out) noexcept
    {
        const auto* invocation = g_CurrentInvocation;
        if (!IsPlayerSnapshotsAvailable() || !owner || !invocationToken || !out ||
            out->struct_size < sizeof(ObeliskCommandPlayer) || !invocation || invocation->Dispatcher != this ||
            invocation->Owner != owner || invocation->Token != invocationToken ||
            invocation->Thread != std::this_thread::get_id() || !invocation->Player)
            return false;
        if (!invocation->CallbackScope || GameplayCallbackScope::Current() != invocation->CallbackScope)
            return false;
        *out = *invocation->Player;
        return true;
    }
}
