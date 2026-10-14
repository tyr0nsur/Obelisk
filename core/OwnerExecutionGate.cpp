#include "OwnerExecutionGate.h"
#include "GameplayCallbackScope.h"

#include <condition_variable>
#include <limits>
#include <utility>

namespace Obelisk::Core
{
    namespace
    {
        thread_local size_t g_OwnerExecutionDepth = 0;
    }

    struct OwnerExecutionGate::RegistryIdentity {};

    struct OwnerExecutionGate::State
    {
        State(std::shared_ptr<RegistryIdentity> registry, void* owner, uint64_t token, uint64_t generation)
            : Registry(std::move(registry)), Owner(owner), OwnerToken(token), Generation(generation) {}
        const std::shared_ptr<RegistryIdentity> Registry;
        void* const Owner;
        const uint64_t OwnerToken;
        const uint64_t Generation;
        std::mutex Mutex;
        std::condition_variable Quiescence;
        Phase CurrentPhase = Phase::Initializing;
        size_t InFlight = 0;
        bool Faulted = false;
        bool Forgotten = false;
    };

    OwnerExecutionGate::OwnerExecutionGate() : m_Identity(std::make_shared<RegistryIdentity>()) {}

    OwnerExecutionGate& OwnerExecutionGate::Get()
    {
        static auto* gate = new OwnerExecutionGate;
        return *gate;
    }

    OwnerExecutionGate::Binding OwnerExecutionGate::Bind(void* owner, uint64_t ownerToken)
    {
        if (!owner || !ownerToken || ControlForbidden())
            return {};
        std::lock_guard lock(m_RegistryMutex);
        if (!m_NextGeneration || m_Owners.contains(owner))
            return {};
        for (const auto& [key, state] : m_Owners)
        {
            (void)key;
            if (state->OwnerToken == ownerToken)
                return {};
        }
        auto state = std::make_shared<State>(m_Identity, owner, ownerToken, m_NextGeneration);
        m_Owners.emplace(owner, state);
        ++m_NextGeneration; // Saturates to zero, rather than reusing a generation.
        return state;
    }

    OwnerExecutionGate::Binding OwnerExecutionGate::Capture(void* owner) const
    {
        std::lock_guard lock(m_RegistryMutex);
        const auto found = m_Owners.find(owner);
        return found == m_Owners.end() ? Binding{} : found->second;
    }

    bool OwnerExecutionGate::Owns(const Binding& state) const noexcept
    {
        return state && state->Registry == m_Identity;
    }

    OwnerExecutionGate::Snapshot OwnerExecutionGate::Inspect(const Binding& state) const noexcept
    {
        if (!Owns(state))
            return {};
        try
        {
            std::lock_guard lock(state->Mutex);
            return {state->CurrentPhase, state->Owner, state->OwnerToken, state->Generation,
                    state->InFlight, state->Faulted};
        }
        catch (...)
        {
            return {Phase::Missing, state->Owner, state->OwnerToken, state->Generation, 0, true};
        }
    }

    bool OwnerExecutionGate::AllowsRegistration(const Binding& state) const noexcept
    {
        const auto snapshot = Inspect(state);
        return !snapshot.faulted && (snapshot.phase == Phase::Initializing || snapshot.phase == Phase::Running);
    }

    OwnerExecutionGate::Lease::Lease(const Binding& state, bool lifecycle, LifecycleEntry kind, bool registration) noexcept
        : m_State(state), m_Thread(std::this_thread::get_id())
    {
        if (g_OwnerExecutionDepth == std::numeric_limits<size_t>::max())
            return;
        try
        {
            if (state)
            {
                std::lock_guard lock(state->Mutex);
                bool allowed = state->CurrentPhase == Phase::Running;
                if (registration)
                    allowed = state->CurrentPhase == Phase::Initializing || state->CurrentPhase == Phase::Running;
                if (lifecycle)
                {
                    switch (kind)
                    {
                    case LifecycleEntry::Init:
                        allowed = state->CurrentPhase == Phase::Initializing && state->InFlight == 0;
                        break;
                    case LifecycleEntry::Cleanup:
                        // Trusted core cleanup, not normal delivery. Its caller
                        // must keep pending cleanup/code mapped until it drains.
                        allowed = true;
                        break;
                    case LifecycleEntry::Shutdown:
                        allowed = state->CurrentPhase == Phase::Retired && state->InFlight == 0;
                        break;
                    }
                }
                if (!allowed || state->Forgotten || state->Faulted || state->InFlight == std::numeric_limits<size_t>::max())
                    return;
                ++state->InFlight;
            }
            ++g_OwnerExecutionDepth;
            m_Entered = true;
        }
        catch (...)
        {
            // Admission failure must never invoke plugin code or escape to UE.
        }
    }

    OwnerExecutionGate::Lease::~Lease() noexcept
    {
        if (!m_Entered)
            return;
        const bool wrongThread = m_Thread != std::this_thread::get_id();
        if (!wrongThread && g_OwnerExecutionDepth != 0)
            --g_OwnerExecutionDepth;
        if (!m_State)
            return;
        try
        {
            {
                std::lock_guard lock(m_State->Mutex);
                if (wrongThread || m_State->InFlight == 0)
                    m_State->Faulted = true; // Retain code if accounting was violated.
                else
                    --m_State->InFlight;
            }
            m_State->Quiescence.notify_all();
        }
        catch (...)
        {
            // A stranded count fails the drain deadline; never force dlclose.
        }
    }

    OwnerExecutionGate::Lease OwnerExecutionGate::EnterCallback(const Binding& binding) noexcept
    {
        return Lease(binding, false, LifecycleEntry::Cleanup);
    }

    OwnerExecutionGate::Lease OwnerExecutionGate::EnterRegistration(const Binding& binding) noexcept
    {
        return Lease(binding, false, LifecycleEntry::Cleanup, true);
    }

    OwnerExecutionGate::Lease OwnerExecutionGate::EnterLifecycle(const Binding& binding, LifecycleEntry kind) noexcept
    {
        return Lease(binding, true, kind);
    }

    bool OwnerExecutionGate::IsInsideExecution() noexcept
    {
        return g_OwnerExecutionDepth != 0;
    }

    bool OwnerExecutionGate::ControlForbidden() noexcept
    {
        return IsInsideExecution() || GameplayCallbackScope::Current() != nullptr;
    }

    OwnerExecutionGate::Result OwnerExecutionGate::Activate(const Binding& state) noexcept
    {
        if (ControlForbidden()) return Result::InsideCallback;
        if (!Owns(state)) return Result::InvalidBinding;
        try
        {
            std::lock_guard lock(state->Mutex);
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase != Phase::Initializing) return Result::WrongState;
            if (state->InFlight != 0) return Result::Busy;
            state->CurrentPhase = Phase::Running;
            return Result::Ok;
        }
        catch (...) { return Result::Failed; }
    }

    OwnerExecutionGate::Result OwnerExecutionGate::Pause(const Binding& state, Clock::time_point deadline) noexcept
    {
        if (ControlForbidden()) return Result::InsideCallback;
        if (!Owns(state)) return Result::InvalidBinding;
        try
        {
            std::unique_lock lock(state->Mutex);
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase == Phase::Paused && state->InFlight == 0) return Result::Ok;
            if (state->CurrentPhase != Phase::Running && state->CurrentPhase != Phase::Pausing &&
                state->CurrentPhase != Phase::Paused)
                return Result::WrongState;
            state->CurrentPhase = Phase::Pausing;
            if (!state->Quiescence.wait_until(lock, deadline, [&] {
                    return state->InFlight == 0 || state->Faulted || state->CurrentPhase != Phase::Pausing;
                }))
                return Result::TimedOut;
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase == Phase::Paused) return Result::Ok;
            if (state->CurrentPhase != Phase::Pausing) return Result::WrongState;
            state->CurrentPhase = Phase::Paused;
            state->Quiescence.notify_all();
            return Result::Ok;
        }
        catch (...) { return Result::Failed; }
    }

    OwnerExecutionGate::Result OwnerExecutionGate::Resume(const Binding& state) noexcept
    {
        if (ControlForbidden()) return Result::InsideCallback;
        if (!Owns(state)) return Result::InvalidBinding;
        try
        {
            std::lock_guard lock(state->Mutex);
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase != Phase::Paused) return Result::WrongState;
            if (state->InFlight != 0) return Result::Busy;
            state->CurrentPhase = Phase::Running;
            return Result::Ok;
        }
        catch (...) { return Result::Failed; }
    }

    OwnerExecutionGate::Result OwnerExecutionGate::RetireAndDrain(const Binding& state, Clock::time_point deadline) noexcept
    {
        if (ControlForbidden()) return Result::InsideCallback;
        if (!Owns(state)) return Result::InvalidBinding;
        try
        {
            std::unique_lock lock(state->Mutex);
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase != Phase::Retired)
                state->CurrentPhase = Phase::Retiring;
            state->Quiescence.notify_all();
            if (!state->Quiescence.wait_until(lock, deadline, [&] {
                    return state->InFlight == 0 || state->Faulted;
                }))
                return Result::TimedOut;
            if (state->Faulted) return Result::Failed;
            state->CurrentPhase = Phase::Retired;
            return Result::Ok;
        }
        catch (...) { return Result::Failed; }
    }

    OwnerExecutionGate::Result OwnerExecutionGate::Forget(const Binding& state) noexcept
    {
        if (ControlForbidden()) return Result::InsideCallback;
        if (!Owns(state)) return Result::InvalidBinding;
        try
        {
            // Registry -> state is the only combined lock order. State operations
            // never call registries, callbacks or PluginManager while locked.
            std::lock_guard registryLock(m_RegistryMutex);
            std::lock_guard stateLock(state->Mutex);
            if (state->Faulted) return Result::Failed;
            if (state->CurrentPhase != Phase::Retired) return Result::WrongState;
            if (state->InFlight != 0) return Result::Busy;
            const auto found = m_Owners.find(state->Owner);
            if (found == m_Owners.end() || found->second != state) return Result::InvalidBinding;
            state->Forgotten = true;
            m_Owners.erase(found);
            return Result::Ok;
        }
        catch (...) { return Result::Failed; }
    }
}
