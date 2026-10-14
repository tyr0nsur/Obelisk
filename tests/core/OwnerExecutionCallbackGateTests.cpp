#include "core/OwnerExecutionGate.h"
#include "core/GameplayCallbackScope.h"
#include "core/ChatEventDispatcher.h"
#include "core/InventoryPolicyEventDispatcher.h"
#include "core/ItemReturnEventDispatcher.h"
#include "core/MissionCopiedBoolEventDispatcher.h"
#include "core/PlayerPrincipalEventDispatcher.h"
#include "core/StructureEventDispatcher.h"
#include "core/EventManager.h"
#include "core/TimerManager.h"

#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace
{
    using namespace Obelisk::Core;
    using namespace std::chrono_literals;
    using Gate = OwnerExecutionGate;

    void Require(bool condition, const char* message)
    {
        if (!condition) throw std::runtime_error(message);
    }

    struct Probe
    {
        Gate::Binding Binding;
        std::atomic<int> Calls{0}, Destroys{0}, ExceptionDestructors{0};
        std::atomic<bool> Leased{true};
        bool ThrowCallback = false, ThrowCleanup = false, Block = false;
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false, Release = false;
    };

    void CheckLease(Probe& probe)
    {
        if (!Gate::IsInsideExecution() || !GameplayCallbackScope::Current() ||
            Gate::Get().Inspect(probe.Binding).inFlight == 0)
            probe.Leased = false;
    }

    class CheckedException final : public std::exception
    {
    public:
        explicit CheckedException(Probe& probe) : m_Probe(probe) {}
        ~CheckedException() noexcept override
        {
            // The gameplay scope may have unwound, but owner admission must
            // protect the plugin-defined exception's destructor through catch.
            if (!Gate::IsInsideExecution() || Gate::Get().Inspect(m_Probe.Binding).inFlight == 0)
                m_Probe.Leased = false;
            ++m_Probe.ExceptionDestructors;
        }
        const char* what() const noexcept override { return "checked plugin exception"; }
    private:
        Probe& m_Probe;
    };

    template<class View> void Callback(const View&, void* data)
    {
        auto& probe = *static_cast<Probe*>(data);
        CheckLease(probe);
        ++probe.Calls;
        if (probe.Block)
        {
            std::unique_lock lock(probe.Mutex);
            probe.Entered = true;
            probe.Cv.notify_all();
            probe.Cv.wait(lock, [&] { return probe.Release; });
        }
        if (probe.ThrowCallback) throw CheckedException(probe);
    }

    void Cleanup(void* data)
    {
        auto& probe = *static_cast<Probe*>(data);
        CheckLease(probe);
        ++probe.Destroys;
        if (probe.ThrowCleanup) throw CheckedException(probe);
    }

    uint64_t NextToken()
    {
        static uint64_t token = 90000;
        return ++token;
    }

    template<class Dispatcher, class Subscription, class View>
    void VerifyCopiedFamily(const View& event)
    {
        Dispatcher dispatcher;
        int owner = 0;
        Probe probe;
        auto& gate = Gate::Get();
        probe.Binding = gate.Bind(&owner, NextToken());
        Require(bool(probe.Binding), "owner bind failed");
        const Subscription subscription{Callback<View>, &probe, Cleanup};
        Require(dispatcher.Register(&owner, subscription) != 0, "Init registration rejected");
        Require(dispatcher.Dispatch(event) == 0, "callback entered before activation");
        Require(gate.Activate(probe.Binding) == Gate::Result::Ok, "activation failed");
        Require(dispatcher.Dispatch(event) == 1 && probe.Calls == 1, "running callback missing");
        Require(gate.Pause(probe.Binding, Gate::Clock::now() + 1s) == Gate::Result::Ok, "pause failed");
        Require(dispatcher.Dispatch(event) == 0 && probe.Calls == 1, "paused callback entered");
        Require(dispatcher.Register(&owner, subscription) == 0, "paused registration committed");
        Require(gate.Resume(probe.Binding) == Gate::Result::Ok, "resume failed");
        probe.ThrowCallback = true;
        Require(dispatcher.Dispatch(event) == 0 && probe.Calls == 2, "throwing callback not caught");
        Require(probe.ExceptionDestructors > 0 && probe.Leased, "exception outlived owner lease");
        Require(gate.RetireAndDrain(probe.Binding, Gate::Clock::now() + 1s) == Gate::Result::Ok,
                "retirement failed");
        Require(dispatcher.Dispatch(event) == 0, "retired callback entered");
        probe.ThrowCleanup = true;
        bool failed = false;
        {
            // PluginManager keeps this outer cleanup lease until its catches
            // and propagated plugin-defined exception have been destroyed.
            auto lifecycleLease = Gate::EnterLifecycle(probe.Binding, Gate::LifecycleEntry::Cleanup);
            try { dispatcher.UnregisterCallbacksForOwner(&owner, Gate::Clock::now() + 1s); }
            catch (const CheckedException&) { failed = true; }
        }
        Require(failed && probe.Destroys == 1, "cleanup failure disappeared");
        Require(gate.Capture(&owner) == probe.Binding, "failure lost mapped generation");
        probe.ThrowCleanup = false;
        Require(dispatcher.UnregisterCallbacksForOwner(&owner, Gate::Clock::now() + 1s) == 1,
                "failed cleanup was not retained for retry");
        Require(probe.Destroys == 2 && probe.Leased, "retry escaped captured cleanup generation");
        Require(gate.Forget(probe.Binding) == Gate::Result::Ok, "clean generation not forgotten");
    }

    template<class Dispatcher, class Subscription, class View>
    void VerifyCleanupDeadlineAcrossOwners(const View& event, bool deferredFailure = false)
    {
        Dispatcher dispatcher;
        int firstOwner = 0, targetOwner = 0;
        Probe blocker, target;
        auto& gate = Gate::Get();
        blocker.Binding = gate.Bind(&firstOwner, NextToken());
        target.Binding = gate.Bind(&targetOwner, NextToken());
        blocker.Block = true;
        target.ThrowCleanup = deferredFailure;
        dispatcher.Register(&firstOwner, Subscription{Callback<View>, &blocker, Cleanup});
        dispatcher.Register(&targetOwner, Subscription{Callback<View>, &target, Cleanup});
        gate.Activate(blocker.Binding);
        gate.Activate(target.Binding);
        std::atomic<size_t> delivered{0};
        std::thread dispatch([&] { delivered = dispatcher.Dispatch(event); });
        bool entered;
        {
            std::unique_lock lock(blocker.Mutex);
            entered = blocker.Cv.wait_for(lock, 1s, [&] { return blocker.Entered; });
        }
        bool timedOut = false;
        const auto retired = gate.RetireAndDrain(target.Binding, Gate::Clock::now() + 100ms);
        if (entered)
        {
            try { dispatcher.UnregisterCallbacksForOwner(&targetOwner, Gate::Clock::now() + 30ms); }
            catch (const std::runtime_error&) { timedOut = true; }
        }
        const bool deferred = target.Destroys == 0;
        {
            std::lock_guard lock(blocker.Mutex);
            blocker.Release = true;
        }
        blocker.Cv.notify_all();
        dispatch.join();
        Require(entered && retired == Gate::Result::Ok && timedOut, "cross-owner cleanup did not respect deadline");
        Require(deferred && target.Destroys == 1 && target.Calls == 0 && delivered == 1,
                "timeout consumed or duplicated pending cleanup/callback");
        Require(target.Leased, "deferred deleter ran without its generation lease");
        if (deferredFailure)
        {
            target.ThrowCleanup = false;
            bool reported = false;
            {
                auto cleanupLease = Gate::EnterLifecycle(target.Binding, Gate::LifecycleEntry::Cleanup);
                try { dispatcher.UnregisterCallbacksForOwner(&targetOwner, Gate::Clock::now() + 1s); }
                catch (const CheckedException&) { reported = true; }
            }
            Require(reported && target.Destroys == 2 && target.Leased,
                    "abandoned batch lost its failure or captured cleanup generation");
        }
        dispatcher.UnregisterCallbacksForOwner(&targetOwner, Gate::Clock::now() + 1s);
        Require(gate.Forget(target.Binding) == Gate::Result::Ok, "deferred generation not clean");
        gate.RetireAndDrain(blocker.Binding, Gate::Clock::now() + 1s);
        dispatcher.UnregisterCallbacksForOwner(&firstOwner, Gate::Clock::now() + 1s);
        Require(gate.Forget(blocker.Binding) == Gate::Result::Ok, "blocker generation not clean");
    }

    template<class Dispatcher, class Subscription, class View>
    void VerifyOldGenerationCannotRebind(const View& event)
    {
        // Adversarial fixture deliberately violates manager's unregister-before-
        // Forget rule. An old registration must still never use a fresh binding.
        Dispatcher dispatcher;
        int reusedOwner = 0;
        Probe old;
        auto& gate = Gate::Get();
        old.Binding = gate.Bind(&reusedOwner, NextToken());
        dispatcher.Register(&reusedOwner, Subscription{Callback<View>, &old});
        gate.Activate(old.Binding);
        gate.RetireAndDrain(old.Binding, Gate::Clock::now() + 1s);
        gate.Forget(old.Binding);
        auto replacement = gate.Bind(&reusedOwner, NextToken());
        gate.Activate(replacement);
        Require(dispatcher.Dispatch(event) == 0 && old.Calls == 0,
                "stale registration resolved new generation at reused owner address");
        gate.RetireAndDrain(replacement, Gate::Clock::now() + 1s);
        Require(gate.Forget(replacement) == Gate::Result::Ok, "replacement generation not clean");
    }

    Probe* g_ProcessEventProbe = nullptr;
    bool ProcessEventCallback(void*, void*, void*)
    {
        CheckLease(*g_ProcessEventProbe);
        ++g_ProcessEventProbe->Calls;
        return true;
    }

    bool BlockingProcessEvent(void*, void*, void* data)
    {
        Callback<int>(0, data);
        return true;
    }

    void VerifyProcessEventCleanupDeadline()
    {
        EventManager events;
        int blockerOwner = 0, targetOwner = 0;
        Probe blocker, target;
        auto& gate = Gate::Get();
        blocker.Binding = gate.Bind(&blockerOwner, NextToken());
        target.Binding = gate.Bind(&targetOwner, NextToken());
        blocker.Block = true;
        g_ProcessEventProbe = &target;
        events.RegisterPreProcessEventOwned(&blockerOwner, BlockingProcessEvent);
        events.RegisterPreProcessEventOwned(&targetOwner, ProcessEventCallback);
        gate.Activate(blocker.Binding);
        gate.Activate(target.Binding);
        std::thread dispatch([&] { events.TriggerPreProcessEvent(nullptr, nullptr, &blocker); });
        bool entered;
        {
            std::unique_lock lock(blocker.Mutex);
            entered = blocker.Cv.wait_for(lock, 1s, [&] { return blocker.Entered; });
        }
        gate.RetireAndDrain(target.Binding, Gate::Clock::now() + 100ms);
        bool timedOut = false;
        if (entered)
        {
            try { events.UnregisterCallbacksForOwner(&targetOwner, Gate::Clock::now() + 30ms); }
            catch (const std::runtime_error&) { timedOut = true; }
        }
        {
            std::lock_guard lock(blocker.Mutex);
            blocker.Release = true;
        }
        blocker.Cv.notify_all();
        dispatch.join();
        Require(entered && timedOut && target.Calls == 0, "PE cleanup deadline/closed admission failed");
        Require(events.UnregisterCallbacksForOwner(&targetOwner, Gate::Clock::now() + 1s) == 1,
                "PE timeout lost registration instead of retaining it");
        gate.Forget(target.Binding);
        gate.RetireAndDrain(blocker.Binding, Gate::Clock::now() + 1s);
        events.UnregisterCallbacksForOwner(&blockerOwner, Gate::Clock::now() + 1s);
        gate.Forget(blocker.Binding);
        g_ProcessEventProbe = nullptr;
    }

    void VerifyProcessEventFamilies()
    {
        EventManager events;
        int owner = 0;
        Probe probe;
        g_ProcessEventProbe = &probe;
        auto& gate = Gate::Get();
        probe.Binding = gate.Bind(&owner, NextToken());
        Require(events.RegisterPreProcessEventOwned(&owner, ProcessEventCallback) != 0, "PE global-pre missing");
        Require(events.RegisterPostProcessEventOwned(&owner, ProcessEventCallback) != 0, "PE global-post missing");
        Require(events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, ProcessEventCallback) != 0, "PE filtered-pre missing");
        Require(events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, ProcessEventCallback) != 0, "PE filtered-post missing");
        events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr);
        Require(probe.Calls == 0, "PE callback before activation");
        gate.Activate(probe.Binding);
        events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr);
        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(probe.Calls == 4 && probe.Leased, "PE family did not hold captured lease");
        gate.Pause(probe.Binding, Gate::Clock::now() + 1s);
        events.TriggerPreProcessEvent(42, nullptr, nullptr, nullptr);
        events.TriggerPostProcessEvent(42, nullptr, nullptr, nullptr);
        Require(probe.Calls == 4, "paused PE callback entered");
        Require(events.RegisterPreProcessEventOwned(&owner, ProcessEventCallback) == 0, "paused PE registration committed");
        gate.Resume(probe.Binding);
        gate.RetireAndDrain(probe.Binding, Gate::Clock::now() + 1s);
        Require(events.UnregisterCallbacksForOwner(&owner, Gate::Clock::now() + 1s) == 4, "PE registry not drained");
        Require(gate.Forget(probe.Binding) == Gate::Result::Ok, "PE generation not clean");
        g_ProcessEventProbe = nullptr;
    }

    struct TimerProbe
    {
        Gate::Binding Binding;
        std::mutex Mutex;
        std::condition_variable Cv;
        int Calls = 0;
        uint64_t LastId = 0;
        bool Leased = true;
    };

    void TimerCallback(uint64_t id, void* data)
    {
        auto& probe = *static_cast<TimerProbe*>(data);
        std::lock_guard lock(probe.Mutex);
        probe.Leased = probe.Leased && Gate::IsInsideExecution() && GameplayCallbackScope::Current() &&
            Gate::Get().Inspect(probe.Binding).inFlight > 0;
        ++probe.Calls;
        probe.LastId = id;
        probe.Cv.notify_all();
    }

    void VerifyTimersPauseWithoutConsumptionOrStarvation()
    {
        auto& timers = TimerManager::Get();
        auto& gate = Gate::Get();
        int pausedOwner = 0, runningOwner = 0;
        // Keep callback storage alive even if a test assertion exits early.
        auto* paused = new TimerProbe;
        auto* running = new TimerProbe;
        auto* repeating = new TimerProbe;
        paused->Binding = gate.Bind(&pausedOwner, NextToken());
        running->Binding = gate.Bind(&runningOwner, NextToken());
        repeating->Binding = paused->Binding;
        const auto preservedId = timers.Register(&pausedOwner, 10, 0, false, TimerCallback, paused);
        Require(preservedId != 0, "one-shot registration missing");
        const auto repeatingId = timers.Register(&pausedOwner, 10, 50, true, TimerCallback, repeating);
        Require(repeatingId != 0, "repeating registration missing");
        gate.Activate(paused->Binding);
        gate.Pause(paused->Binding, Gate::Clock::now() + 1s);
        const auto otherId = timers.Register(&runningOwner, 20, 0, false, TimerCallback, running);
        Require(otherId != 0, "second-owner timer missing");
        gate.Activate(running->Binding);
        timers.NotifyOwnerResumed(&runningOwner);
        {
            std::unique_lock lock(running->Mutex);
            Require(running->Cv.wait_for(lock, 1s, [&] { return running->Calls == 1; }),
                    "paused due timer starved a runnable owner");
        }
        Require(timers.Register(&pausedOwner, 10, 0, false, TimerCallback, paused) == 0,
                "paused timer registration committed");
        {
            std::lock_guard lock(paused->Mutex);
            Require(paused->Calls == 0, "paused one-shot consumed");
        }
        {
            std::unique_lock lock(repeating->Mutex);
            Require(!repeating->Cv.wait_for(lock, 220ms, [&] { return repeating->Calls != 0; }),
                    "paused repeating timer consumed an occurrence");
        }
        gate.Resume(paused->Binding);
        timers.NotifyOwnerResumed(&pausedOwner);
        {
            std::unique_lock lock(paused->Mutex);
            Require(paused->Cv.wait_for(lock, 1s, [&] { return paused->Calls == 1; }), "resumed one-shot lost");
            Require(paused->LastId == preservedId && paused->Leased, "resume replaced handle or escaped lease");
        }
        {
            std::unique_lock lock(repeating->Mutex);
            Require(repeating->Cv.wait_for(lock, 1s, [&] { return repeating->Calls > 0; }),
                    "resumed repeating timer lost");
            Require(repeating->Calls == 1 && repeating->LastId == repeatingId && repeating->Leased,
                    "repeating timer replayed accumulated intervals or replaced handle");
        }
        gate.RetireAndDrain(paused->Binding, Gate::Clock::now() + 1s);
        gate.RetireAndDrain(running->Binding, Gate::Clock::now() + 1s);
        timers.UnregisterCallbacksForOwner(&pausedOwner, Gate::Clock::now() + 1s);
        timers.UnregisterCallbacksForOwner(&runningOwner, Gate::Clock::now() + 1s);
        Require(gate.Forget(paused->Binding) == Gate::Result::Ok &&
                gate.Forget(running->Binding) == Gate::Result::Ok && running->Leased,
                "timer generation not drained");
    }

    template<class Dispatcher, class Subscription, class View>
    void VerifyFamily(const View& event)
    {
        VerifyCopiedFamily<Dispatcher, Subscription>(event);
        VerifyCleanupDeadlineAcrossOwners<Dispatcher, Subscription>(event);
        VerifyCleanupDeadlineAcrossOwners<Dispatcher, Subscription>(event, true);
        VerifyOldGenerationCannotRebind<Dispatcher, Subscription>(event);
    }
}

int main()
{
    try
    {
        using namespace Obelisk::Core;
        const std::array inventory{InventoryPolicyScalarValue{InventoryPolicyScalarField::BIgnoreCooldown, false},
                                   InventoryPolicyScalarValue{InventoryPolicyScalarField::ReturnValue, true}};
        const std::array item{ItemReturnScalarValue{ItemReturnScalarField::ReturnValue, true}};
        const std::array mission{MissionCopiedBoolValue{MissionCopiedBoolField::ReturnValue, true}};
        const std::array structure{StructureScalarValue{StructureScalarField::ReturnValue, StructureScalarType::Bool, true}};
        VerifyFamily<ChatEventDispatcher, ChatMessageSubscription>(ChatMessageView{.Message = "copied", .SenderName = "player"});
        VerifyFamily<InventoryPolicyEventDispatcher, InventoryPolicyEventSubscription>(InventoryPolicyEventView{InventoryPolicyEventKind::CanUse, inventory});
        VerifyFamily<ItemReturnEventDispatcher, ItemReturnEventSubscription>(ItemReturnEventView{ItemReturnEventKind::CanRepair, item});
        VerifyFamily<MissionCopiedBoolEventDispatcher, MissionCopiedBoolEventSubscription>(MissionCopiedBoolEventView{MissionCopiedBoolEventKind::BPAllowPlayerToLeaveMission, mission});
        VerifyFamily<PlayerPrincipalEventDispatcher, PlayerPrincipalEventSubscription>(PlayerPrincipalEventView{.Kind = PlayerPrincipalEventKind::SessionEnd, .Action = PlayerPrincipalAction::CandidateInvalidated, .EventSequence = 1, .ServerProcessEpoch = 1});
        VerifyFamily<StructureEventDispatcher, StructureEventSubscription>(StructureEventView{.Kind = StructureEventKind::VerifyPinCode, .Scalars = structure});
        VerifyProcessEventFamilies();
        VerifyProcessEventCleanupDeadline();
        VerifyTimersPauseWithoutConsumptionOrStarvation();
        std::cout << "Owner execution callback gate integration passed\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
