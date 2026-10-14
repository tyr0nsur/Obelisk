#include "CommandDispatcher.h"
#include "GameplayCallbackScope.h"

#include <algorithm>
#include <limits>
#include <cmath>
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
            const CommandRuntimeContext* Runtime;
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

        unsigned char FoldAscii(unsigned char ch) noexcept
        {
            return ch >= 'A' && ch <= 'Z' ? static_cast<unsigned char>(ch + ('a' - 'A')) : ch;
        }

        bool EqualCommandName(std::string_view left, std::string_view right, bool insensitive) noexcept
        {
            if (left.size() != right.size())
                return false;
            for (size_t i = 0; i < left.size(); ++i)
            {
                const auto lhs = static_cast<unsigned char>(left[i]);
                const auto rhs = static_cast<unsigned char>(right[i]);
                if ((insensitive ? FoldAscii(lhs) : lhs) != (insensitive ? FoldAscii(rhs) : rhs))
                    return false;
            }
            return true;
        }

        bool MatchesCommand(std::string_view name, uint64_t flags, std::string_view message) noexcept
        {
            if (message.size() < name.size() ||
                !EqualCommandName(name, message.substr(0, name.size()),
                                  flags & OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE))
                return false;
            if (message.size() == name.size())
                return true;
            return (flags & OBELISK_COMMAND_MATCH_FLAG_VERB) &&
                   (message[name.size()] == ' ' || message[name.size()] == '\t');
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
        return RegisterWithOptions(owner, command, 0, callback, userData);
    }

    uint64_t CommandDispatcher::RegisterWithOptions(void* owner, std::string_view command, uint64_t matchFlags,
                                                    ObeliskCommandCallback callback, void* userData)
    {
        constexpr uint64_t supported = OBELISK_COMMAND_MATCH_FLAG_VERB |
                                       OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE;
        if (!IsAvailable() || !owner || !callback || !ValidCommand(command) || (matchFlags & ~supported))
            return 0;
        auto execution = OwnerExecutionGate::Get().Capture(owner);
        auto registrationLease = OwnerExecutionGate::EnterRegistration(execution);
        if (!registrationLease)
            return 0;
        auto registration = std::make_shared<Registration>();
        registration->Execution = std::move(execution);
        registration->Owner = owner;
        registration->Command = command;
        registration->MatchFlags = matchFlags;
        registration->Callback = callback;
        registration->UserData = userData;
        std::lock_guard lock(m_Mutex);
        if (!IsAvailable() || m_NextRegistrationId == std::numeric_limits<uint64_t>::max())
            return 0;
        for (const auto& existing : m_Registrations)
            if (existing->Active && (matchFlags || existing->MatchFlags) &&
                EqualCommandName(command, existing->Command,
                    (matchFlags | existing->MatchFlags) & OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE))
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

    size_t CommandDispatcher::UnregisterCallbacksForOwner(void* owner, std::chrono::steady_clock::time_point deadline)
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
        if (!m_Quiescence.wait_until(lock, deadline, [&] { return !HasOwnerInvocationsLocked(owner); }))
            throw std::runtime_error("command owner cleanup deadline expired; keep plugin mapped");
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
                                        ReplyBackend backend, void* backendData, const CommandPlayerSnapshot* player, const CommandRuntimeContext* runtimeContext)
    {
        if (!IsAvailable() || !controller || !backend || sendMode > 3 ||
            message.empty() || message.size() > 4096 || !ValidUtf8(message))
            return 0;
        std::vector<std::shared_ptr<Registration>> callbacks;
        {
            std::lock_guard lock(m_Mutex);
            for (const auto& registration : m_Registrations)
                if (registration->Active && MatchesCommand(registration->Command, registration->MatchFlags, message))
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
            auto ownerLease = OwnerExecutionGate::EnterCallback(registration->Execution);
            if (!ownerLease)
                continue;
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
                                       backendData, std::this_thread::get_id(), hasSnapshot ? &copiedPlayer : nullptr, runtimeContext,
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
        if(invocation->Runtime){ObeliskChatSession origin{};origin.struct_size=sizeof(origin);
            if(!GetChatSession(owner,invocationToken,&origin))return false;}
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
    void CommandDispatcher::SetChatSessionRegistry(ChatSessionRegistry* value) noexcept { m_ChatSessions.store(value); }
    bool CommandDispatcher::IsChatSessionsAvailable() const noexcept {
        const auto* value=m_ChatSessions.load(); return IsAvailable() && value && value->Available();
    }
    void CommandDispatcher::SetWorldInfoAvailable(bool value) noexcept { m_WorldInfoAvailable.store(value); }
    bool CommandDispatcher::IsWorldInfoAvailable() const noexcept { return IsAvailable() && m_WorldInfoAvailable.load(); }
    namespace {
        const InvocationScope* CurrentFor(CommandDispatcher* dispatcher,void* owner,uint64_t token) noexcept {
            const auto* value=g_CurrentInvocation;
            return value && owner && token && value->Dispatcher==dispatcher && value->Owner==owner &&
                value->Token==token && value->Thread==std::this_thread::get_id() && value->CallbackScope &&
                GameplayCallbackScope::Current()==value->CallbackScope ? value : nullptr;
        }
    }
    bool CommandDispatcher::GetChatSession(void* owner,uint64_t token,ObeliskChatSession* out) noexcept {
        const auto* value=CurrentFor(this,owner,token); auto* sessions=m_ChatSessions.load();
        return IsChatSessionsAvailable() && value && value->Runtime && sessions->Snapshot(value->Runtime->ChatSessionToken,out);
    }
    bool CommandDispatcher::ListChatSessions(void* owner,uint64_t token,ObeliskChatSession* records,size_t capacity,size_t* written,size_t* total) noexcept {
        ObeliskChatSession origin{}; origin.struct_size=sizeof(origin);
        return GetChatSession(owner,token,&origin) && m_ChatSessions.load()->List(records,capacity,written,total);
    }
    bool CommandDispatcher::SendChatToSession(void* owner,uint64_t token,uint64_t destination,uint64_t epoch,std::string_view text) noexcept {
        ObeliskChatSession origin{}; origin.struct_size=sizeof(origin);
        return GetChatSession(owner,token,&origin) && m_ChatSessions.load()->Deliver(destination,epoch,text);
    }
    bool CommandDispatcher::GetWorldInfo(void* owner,uint64_t token,ObeliskCommandWorldInfo* out) noexcept {
        const auto* value=CurrentFor(this,owner,token);ObeliskChatSession origin{};origin.struct_size=sizeof(origin);
        if(!IsWorldInfoAvailable()||!value||!value->Runtime||!value->Runtime->WorldInfo||!out||out->struct_size<sizeof(*out)||!GetChatSession(owner,token,&origin))return false;
        ObeliskCommandWorldInfo copied{};copied.struct_size=sizeof(copied);
        if(!value->Runtime->WorldInfo(value->Controller,&copied,value->Runtime->Data)||
            copied.session_token!=origin.session_token||copied.process_epoch!=origin.process_epoch||
            copied.abi_version!=OBELISK_COMMAND_WORLD_INFO_ABI_VERSION||copied.struct_size<sizeof(copied)||(copied.flags&~31ull))return false;
        if((copied.flags&OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE)&&(!std::isfinite(copied.x)||!std::isfinite(copied.y)||!std::isfinite(copied.z)||std::abs(copied.x)>1e8||std::abs(copied.y)>1e8||std::abs(copied.z)>1e8))return false;
        if((copied.flags&OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE)&&(!std::isfinite(copied.pitch)||!std::isfinite(copied.yaw)||!std::isfinite(copied.roll)))return false;
        ObeliskChatSession after{};after.struct_size=sizeof(after);
        if(!GetChatSession(owner,token,&after)||after.session_token!=origin.session_token||after.process_epoch!=origin.process_epoch)return false;
        *out=copied;return true;
    }

    void CommandDispatcher::SetSelfTeleportAvailable(bool value) noexcept {m_SelfTeleportAvailable.store(value);}
    bool CommandDispatcher::IsSelfTeleportAvailable()const noexcept{return IsWorldInfoAvailable()&&m_SelfTeleportAvailable.load();}
    bool CommandDispatcher::TeleportOrigin(void* owner,uint64_t token,const ObeliskCommandWorldInfo* destination) noexcept {
        const auto* value=CurrentFor(this,owner,token);ObeliskChatSession origin{};origin.struct_size=sizeof(origin);
        return IsSelfTeleportAvailable()&&value&&value->Runtime&&value->Runtime->Teleport&&destination&&
            destination->abi_version==OBELISK_COMMAND_WORLD_INFO_ABI_VERSION&&destination->struct_size>=sizeof(*destination)&&
            (destination->flags&OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE)&&!(destination->flags&~31ull)&&
            std::isfinite(destination->x)&&std::isfinite(destination->y)&&std::isfinite(destination->z)&&
            std::abs(destination->x)<=1e8&&std::abs(destination->y)<=1e8&&std::abs(destination->z)<=1e8&&GetChatSession(owner,token,&origin)&&
            origin.session_token==destination->session_token&&origin.process_epoch==destination->process_epoch&&
            value->Runtime->Teleport(value->Controller,destination,value->Runtime->Data);
    }

}
