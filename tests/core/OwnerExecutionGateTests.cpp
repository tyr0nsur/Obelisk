#include "core/OwnerExecutionGate.h"
#include "core/GameplayCallbackScope.h"

#include <atomic>
#include <condition_variable>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <type_traits>

namespace
{
    using Gate = Obelisk::Core::OwnerExecutionGate;
    using namespace std::chrono_literals;
    static_assert(!std::is_copy_constructible_v<Gate::Lease>);
    static_assert(!std::is_move_constructible_v<Gate::Lease>);

    void Require(bool condition, const char* message)
    {
        if (!condition) throw std::runtime_error(message);
    }

    template <typename Predicate>
    void WaitUntil(Predicate predicate)
    {
        const auto deadline = Gate::Clock::now() + 2s;
        while (!predicate())
        {
            Require(Gate::Clock::now() < deadline, "concurrent operation did not reach its expected barrier");
            std::this_thread::yield();
        }
    }

    struct Barrier
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Released = false;
        void EnterAndWait()
        {
            std::unique_lock lock(Mutex);
            Entered = true;
            Cv.notify_all();
            Cv.wait(lock, [&] { return Released; });
        }
        void WaitForEntry()
        {
            std::unique_lock lock(Mutex);
            Require(Cv.wait_for(lock, 2s, [&] { return Entered; }), "worker did not enter");
        }
        void Release()
        {
            std::lock_guard lock(Mutex);
            Released = true;
            Cv.notify_all();
        }
    };

    void TestInitializingPauseAndGenerationRetirement()
    {
        Gate gate;
        int owner, otherOwner;
        auto first = gate.Bind(&owner, 42);
        Require(first && gate.Capture(&owner) == first, "initial owner did not bind");
        Require(!gate.Bind(&owner, 43) && !gate.Bind(&otherOwner, 42), "live owner/token was aliased");
        Require(!Gate::EnterCallback(first), "callback entered before Init succeeded");
        {
            auto init = Gate::EnterLifecycle(first, Gate::LifecycleEntry::Init);
            Require(static_cast<bool>(init), "Init lifecycle entry rejected");
            auto registration = Gate::EnterRegistration(first);
            Require(static_cast<bool>(registration), "Init could not register future callbacks");
            Require(gate.Activate(first) == Gate::Result::InsideCallback, "control reentered Init");
        }
        Require(gate.Activate(first) == Gate::Result::Ok, "successful Init did not activate");
        int pluginState = 7;
        { auto callback = Gate::EnterCallback(first); Require(static_cast<bool>(callback), "running callback rejected"); ++pluginState; }
        Require(gate.Pause(first, Gate::Clock::now()) == Gate::Result::Ok, "idle pause failed");
        Require(!Gate::EnterCallback(first) && !Gate::EnterRegistration(first), "pause admitted work");
        Require(pluginState == 8 && gate.Resume(first) == Gate::Result::Ok, "pause discarded retained plugin state");
        { auto callback = Gate::EnterCallback(first); Require(static_cast<bool>(callback), "resume did not restore delivery"); ++pluginState; }
        Require(pluginState == 9, "resumed generation did not retain state");
        const auto generation = gate.Inspect(first).generation;
        Require(gate.RetireAndDrain(first, Gate::Clock::now()) == Gate::Result::Ok, "retirement failed");
        Require(gate.Resume(first) == Gate::Result::WrongState && gate.Activate(first) == Gate::Result::WrongState,
                "retired generation was revived");
        Require(!gate.Bind(&owner, 44), "retained mapping was rebound before cleanup/forget");
        Require(gate.Forget(first) == Gate::Result::Ok, "retired idle owner could not be forgotten");
        auto replacement = gate.Bind(&owner, 44);
        Require(replacement && gate.Inspect(replacement).generation != generation, "base-address reuse revived a generation");
        Require(gate.Activate(replacement) == Gate::Result::Ok, "replacement could not activate");
        Require(!Gate::EnterCallback(first) && !Gate::EnterLifecycle(first, Gate::LifecycleEntry::Cleanup),
                "old snapshot admitted code after owner address was reused");
        Require(gate.Capture(&owner) == replacement && gate.Forget(first) == Gate::Result::InvalidBinding,
                "old binding removed its replacement");
        Gate foreign;
        Require(foreign.Pause(replacement, Gate::Clock::now()) == Gate::Result::InvalidBinding,
                "another registry controlled a foreign binding");
    }

    void TestTimeoutIsolationAndRetirementWinsPause()
    {
        Gate gate;
        int owner, otherOwner;
        auto binding = gate.Bind(&owner, 1);
        auto other = gate.Bind(&otherOwner, 2);
        Require(gate.Activate(binding) == Gate::Result::Ok && gate.Activate(other) == Gate::Result::Ok,
                "owners could not activate");
        Barrier active;
        std::thread callback([&] { auto lease = Gate::EnterCallback(binding); if (lease) active.EnterAndWait(); });
        active.WaitForEntry();
        const auto isolation = gate.Pause(other, Gate::Clock::now());
        const auto timeout = gate.Pause(binding, Gate::Clock::now());
        const auto closed = !Gate::EnterCallback(binding);
        auto pause = std::async(std::launch::async, [&] { return gate.Pause(binding, Gate::Clock::now() + 2s); });
        const auto retire = gate.RetireAndDrain(binding, Gate::Clock::now());
        const auto pauseResult = pause.get();
        active.Release();
        callback.join();
        Require(isolation == Gate::Result::Ok, "unrelated owner blocked another owner's pause");
        Require(timeout == Gate::Result::TimedOut && closed && retire == Gate::Result::TimedOut,
                "active callback was freed or readmitted on timeout");
        Require(pauseResult == Gate::Result::WrongState, "pause overwrote concurrent irreversible retirement");
        Require(gate.RetireAndDrain(binding, Gate::Clock::now() + 2s) == Gate::Result::Ok &&
                gate.Inspect(binding).phase == Gate::Phase::Retired, "drained callback could not complete retirement");
        Require(!Gate::EnterCallback(binding), "retirement resumed callbacks");
    }

    void TestReentrantControlAndCurrentOnlyFamilies()
    {
        Gate gate;
        int owner, otherOwner;
        auto binding = gate.Bind(&owner, 1);
        auto other = gate.Bind(&otherOwner, 2);
        Require(gate.Activate(binding) == Gate::Result::Ok && gate.Activate(other) == Gate::Result::Ok,
                "owners could not activate");
        {
            auto outer = Gate::EnterCallback(binding);
            auto inner = Gate::EnterCallback(other);
            Require(outer && inner && gate.Inspect(binding).inFlight == 1 && gate.Inspect(other).inFlight == 1,
                    "nested owners were not counted separately");
            Require(gate.Pause(other, Gate::Clock::now()) == Gate::Result::InsideCallback &&
                    gate.RetireAndDrain(binding, Gate::Clock::now()) == Gate::Result::InsideCallback,
                    "callback could control an owner and deadlock its own drain");
        }
        using Scope = Obelisk::Core::GameplayCallbackScope;
        for (auto family : {Obelisk::Core::GameplayCallbackFamily::Timer, Obelisk::Core::GameplayCallbackFamily::ProcessEvent})
        {
            Scope callback(family, Scope::TrackingMode::CurrentOnly);
            Require(!Scope::IsInsideAnyCallback(), "test did not exercise tracking-only legacy callback");
            Require(gate.Pause(binding, Gate::Clock::now()) == Gate::Result::InsideCallback,
                    "tracking-only callback bypassed control rejection");
        }
        Require(!Gate::IsInsideExecution() && gate.Inspect(binding).phase == Gate::Phase::Running,
                "reentrant control leaked TLS or changed admission");
    }

    struct PluginException final : std::exception
    {
        Barrier* Destruction;
        explicit PluginException(Barrier& barrier) : Destruction(&barrier) {}
        ~PluginException() noexcept override { Destruction->EnterAndWait(); }
    };

    void TestExceptionDestructorAndPrivilegedCleanupRetainMapping()
    {
        Gate gate;
        int owner;
        auto binding = gate.Bind(&owner, 5);
        Require(gate.Activate(binding) == Gate::Result::Ok, "exception owner could not activate");
        Barrier destruction;
        std::thread callback([&] {
            auto lease = Gate::EnterCallback(binding); // Outside try, also protects exception destruction.
            try { throw PluginException(destruction); }
            catch (const PluginException&) {}
        });
        destruction.WaitForEntry();
        const auto beforeExceptionDestruction = gate.RetireAndDrain(binding, Gate::Clock::now());
        destruction.Release();
        callback.join();
        Require(beforeExceptionDestruction == Gate::Result::TimedOut, "exception destructor outlived plugin mapping protection");
        Require(gate.RetireAndDrain(binding, Gate::Clock::now()) == Gate::Result::Ok, "completed exception did not release gate");
        Barrier cleanup;
        std::thread deleter([&] { auto lease = Gate::EnterLifecycle(binding, Gate::LifecycleEntry::Cleanup); if (lease) cleanup.EnterAndWait(); });
        cleanup.WaitForEntry();
        const auto forgetDuringCleanup = gate.Forget(binding);
        const auto prematureShutdown = static_cast<bool>(Gate::EnterLifecycle(binding, Gate::LifecycleEntry::Shutdown));
        cleanup.Release();
        deleter.join();
        Require(forgetDuringCleanup == Gate::Result::Busy && !prematureShutdown, "cleanup state was freed while deleter was active");
        {
            auto shutdown = Gate::EnterLifecycle(binding, Gate::LifecycleEntry::Shutdown);
            Require(static_cast<bool>(shutdown), "drained shutdown could not enter");
            Require(gate.Forget(binding) == Gate::Result::InsideCallback, "shutdown closed its own library stack");
        }
        Require(gate.Forget(binding) == Gate::Result::Ok, "completed shutdown could not release binding");
    }
}

int main()
{
    try
    {
        TestInitializingPauseAndGenerationRetirement();
        TestTimeoutIsolationAndRetirementWinsPause();
        TestReentrantControlAndCurrentOnlyFamilies();
        TestExceptionDestructorAndPrivilegedCleanupRetainMapping();
        std::cout << "OwnerExecutionGateTests passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "OwnerExecutionGateTests failed: " << error.what() << '\n';
        return 1;
    }
}
