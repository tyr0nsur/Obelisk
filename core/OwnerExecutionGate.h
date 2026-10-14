#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>
#include <unordered_map>

namespace Obelisk::Core
{
    // Private lifetime/admission control. This is not a plugin C ABI or an OS
    // thread-stopping facility. Registered plugin code must hold a Binding from
    // its own load generation; resolving a base address at invocation time can
    // mistake an old snapshot for a newly loaded library at the same address.
    class OwnerExecutionGate
    {
        struct State;
        struct RegistryIdentity;

    public:
        using Clock = std::chrono::steady_clock;
        using Binding = std::shared_ptr<State>;
        enum class Phase { Missing, Initializing, Running, Pausing, Paused, Retiring, Retired };
        enum class Result { Ok, TimedOut, InvalidBinding, InsideCallback, WrongState, Busy, Failed };
        enum class LifecycleEntry { Init, Cleanup, Shutdown };

        struct Snapshot
        {
            Phase phase = Phase::Missing;
            void* owner = nullptr;
            uint64_t ownerToken = 0;
            uint64_t generation = 0;
            size_t inFlight = 0;
            bool faulted = false;
        };

        class Lease
        {
        public:
            Lease(const Lease&) = delete;
            Lease& operator=(const Lease&) = delete;
            Lease(Lease&&) = delete;
            Lease& operator=(Lease&&) = delete;
            ~Lease() noexcept;
            explicit operator bool() const noexcept { return m_Entered; }

        private:
            friend class OwnerExecutionGate;
            Lease(const Binding&, bool lifecycle, LifecycleEntry, bool registration = false) noexcept;
            Binding m_State;
            std::thread::id m_Thread;
            bool m_Entered = false;
        };

        OwnerExecutionGate();
        OwnerExecutionGate(const OwnerExecutionGate&) = delete;
        OwnerExecutionGate& operator=(const OwnerExecutionGate&) = delete;
        static OwnerExecutionGate& Get();

        // Bind before Init. A mapped generation must be retired, cleaned and
        // forgotten before another generation can bind the same owner address.
        Binding Bind(void* owner, uint64_t ownerToken);
        Binding Capture(void* owner) const;
        Snapshot Inspect(const Binding&) const noexcept;
        bool AllowsRegistration(const Binding&) const noexcept;

        // Empty bindings explicitly preserve internal/test subscriptions outside
        // PluginManager. Plugin registration wrappers must require a bound owner.
        // Even these unmanaged entries mark TLS to forbid reentrant control.
        // Keep leases outside the callback try/catch, until exception objects and
        // plugin-defined destructors have finished, on the constructing thread.
        static Lease EnterCallback(const Binding&) noexcept;
        static Lease EnterRegistration(const Binding&) noexcept;
        static Lease EnterLifecycle(const Binding&, LifecycleEntry) noexcept;
        static bool IsInsideExecution() noexcept;

        Result Activate(const Binding&) noexcept;
        Result Pause(const Binding&, Clock::time_point deadline) noexcept;
        Result Resume(const Binding&) noexcept;
        Result RetireAndDrain(const Binding&, Clock::time_point deadline) noexcept;
        Result Forget(const Binding&) noexcept;

        // Pausing/retirement closes delivery before waiting. A timeout leaves
        // admission closed and code/state mapped; retirement is irreversible.
        // This barrier only accounts for instrumented executions. Registrations,
        // deferred cleanup, exception_ptrs and cooperative background threads
        // still require their own cleanup barriers before Shutdown/dlclose.
    private:
        bool Owns(const Binding&) const noexcept;
        static bool ControlForbidden() noexcept;
        std::shared_ptr<RegistryIdentity> m_Identity;
        mutable std::mutex m_RegistryMutex;
        std::unordered_map<void*, Binding> m_Owners;
        uint64_t m_NextGeneration = 1;
    };
}
