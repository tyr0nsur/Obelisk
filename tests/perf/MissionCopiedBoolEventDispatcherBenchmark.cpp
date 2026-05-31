#include "core/MissionCopiedBoolEventDispatcher.h"

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    thread_local bool g_CountAllocations = false;
    thread_local uint64_t g_AllocationCount = 0;
}

void* operator new(std::size_t size)
{
    if (void* ptr = std::malloc(size == 0 ? 1 : size))
    {
        if (g_CountAllocations)
            ++g_AllocationCount;
        return ptr;
    }
    throw std::bad_alloc();
}

void* operator new[](std::size_t size)
{
    return operator new(size);
}

void operator delete(void* ptr) noexcept
{
    std::free(ptr);
}

void operator delete[](void* ptr) noexcept
{
    std::free(ptr);
}

void operator delete(void* ptr, std::size_t) noexcept
{
    std::free(ptr);
}

void operator delete[](void* ptr, std::size_t) noexcept
{
    std::free(ptr);
}

namespace
{
    struct CallbackState
    {
        uint64_t Calls = 0;
    };

    void CountingCallback(const Obelisk::Core::MissionCopiedBoolEventView&, void* userData)
    {
        auto* state = static_cast<CallbackState*>(userData);
        ++state->Calls;
    }

    std::array<Obelisk::Core::MissionCopiedBoolValue, 2> MakeBoolStorage()
    {
        std::array<Obelisk::Core::MissionCopiedBoolValue, 2> bools{};
        bools[0].Field = Obelisk::Core::MissionCopiedBoolField::BForceAdd;
        bools[0].Value = true;
        bools[1].Field = Obelisk::Core::MissionCopiedBoolField::ReturnValue;
        bools[1].Value = false;
        return bools;
    }

    Obelisk::Core::MissionCopiedBoolEventView MakeEvent(
        const std::array<Obelisk::Core::MissionCopiedBoolValue, 2>& bools)
    {
        return {
            .Kind = Obelisk::Core::MissionCopiedBoolEventKind::AddPlayerToMission,
            .Bools = std::span<const Obelisk::Core::MissionCopiedBoolValue>(bools.data(), bools.size()),
        };
    }

    Obelisk::Core::MissionCopiedBoolEventView MakeInvalidEvent(
        const std::array<Obelisk::Core::MissionCopiedBoolValue, 2>& bools)
    {
        return {
            .Kind = static_cast<Obelisk::Core::MissionCopiedBoolEventKind>(99),
            .Bools = std::span<const Obelisk::Core::MissionCopiedBoolValue>(bools.data(), bools.size()),
        };
    }

    struct BenchmarkResult
    {
        std::string Name;
        uint64_t Iterations = 0;
        uint64_t NsAverage = 0;
        uint64_t Allocations = 0;
        uint64_t AllocationsPerIter = 0;
        uint64_t Dispatched = 0;
    };

    template <typename Fn>
    BenchmarkResult RunCase(const std::string& name, uint64_t iterations, Fn&& fn)
    {
        fn();
        g_AllocationCount = 0;
        g_CountAllocations = true;
        const auto start = std::chrono::steady_clock::now();
        uint64_t dispatched = 0;
        for (uint64_t i = 0; i < iterations; ++i)
            dispatched += static_cast<uint64_t>(fn());
        const auto end = std::chrono::steady_clock::now();
        g_CountAllocations = false;

        const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        return {
            .Name = name,
            .Iterations = iterations,
            .NsAverage = iterations == 0 ? 0 : static_cast<uint64_t>(ns / static_cast<int64_t>(iterations)),
            .Allocations = g_AllocationCount,
            .AllocationsPerIter = iterations == 0 ? 0 : g_AllocationCount / iterations,
            .Dispatched = dispatched,
        };
    }

    void PrintResult(const BenchmarkResult& result)
    {
        std::cout << result.Name
                  << " iterations=" << result.Iterations
                  << " ns_avg=" << result.NsAverage
                  << " allocations=" << result.Allocations
                  << " allocations_per_iter=" << result.AllocationsPerIter
                  << " dispatched=" << result.Dispatched
                  << "\n";
    }
}

int main()
{
    constexpr uint64_t kIterations = 10000;
    const auto bools = MakeBoolStorage();
    const auto event = MakeEvent(bools);
    const auto invalidEvent = MakeInvalidEvent(bools);

    PrintResult(RunCase("invalid_event", kIterations, [&]() {
        Obelisk::Core::MissionCopiedBoolEventDispatcher dispatcher;
        return dispatcher.Dispatch(invalidEvent);
    }));

    {
        Obelisk::Core::MissionCopiedBoolEventDispatcher dispatcher;
        PrintResult(RunCase("no_subscribers", kIterations, [&]() {
            return dispatcher.Dispatch(event);
        }));
    }

    {
        Obelisk::Core::MissionCopiedBoolEventDispatcher dispatcher;
        int owners[4]{};
        CallbackState states[4]{};
        for (size_t i = 0; i < 4; ++i)
        {
            if (dispatcher.Register(&owners[i], {CountingCallback, &states[i]}) == 0)
                throw std::runtime_error("mission copied-bool benchmark registration failed");
        }
        PrintResult(RunCase("four_subscribers_stack_snapshot", kIterations, [&]() {
            return dispatcher.Dispatch(event);
        }));
    }

    {
        Obelisk::Core::MissionCopiedBoolEventDispatcher dispatcher;
        int owners[5]{};
        CallbackState states[5]{};
        for (size_t i = 0; i < 5; ++i)
        {
            if (dispatcher.Register(&owners[i], {CountingCallback, &states[i]}) == 0)
                throw std::runtime_error("mission copied-bool benchmark registration failed");
        }
        PrintResult(RunCase("five_subscribers_heap_snapshot", kIterations, [&]() {
            return dispatcher.Dispatch(event);
        }));
    }

    return 0;
}
