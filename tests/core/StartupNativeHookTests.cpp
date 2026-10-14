#include "hooks/StartupNativeHook.h"

#include <array>
#include <atomic>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <sys/mman.h>
#include <thread>
#include <unistd.h>

namespace
{
    using NativeFunction = int (*)(int);
    NativeFunction g_Original = nullptr;
    int g_DetourCalls = 0;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    int Detour(int value)
    {
        ++g_DetourCalls;
        return g_Original(value) + 100;
    }

    constexpr std::array<uint8_t, 20> kPrologue{
        0x89, 0xf8,                   // mov eax, edi
        0x83, 0xc0, 0x01,             // add eax, 1
        0x90, 0x90, 0x90, 0x90, 0x90,
        0x90, 0x90, 0x90, 0x90, 0x90,
        0x90, 0x90, 0x90, 0x90, 0x90
    };
    constexpr std::array<uint8_t, 4> kSuffix{0x83, 0xc0, 0x07, 0xc3}; // add eax, 7; ret

    void* MakeCodePage()
    {
        const long pageSize = sysconf(_SC_PAGESIZE);
        Require(pageSize > 0, "page size unavailable");
        void* page = mmap(nullptr, static_cast<size_t>(pageSize), PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        Require(page != MAP_FAILED, "code mmap failed");
        std::memcpy(page, kPrologue.data(), kPrologue.size());
        std::memcpy(static_cast<uint8_t*>(page) + kPrologue.size(), kSuffix.data(), kSuffix.size());
        Require(mprotect(page, static_cast<size_t>(pageSize), PROT_READ | PROT_EXEC) == 0,
                "code page mprotect failed");
        return page;
    }

    void TestRejectsUnsafeInstallations(void* target)
    {
        Obelisk::Hooks::StartupNativeHook hook;
        auto wrong = kPrologue;
        wrong[0] ^= 1;
        Require(!hook.Install(target, reinterpret_cast<void*>(&Detour), wrong), "wrong profile accepted");
        Require(!hook.IsInstalled() && !hook.Trampoline(), "failed install retained hook state");
        Require(std::memcmp(target, kPrologue.data(), kPrologue.size()) == 0,
                "rejected profile changed target");
        Require(!hook.Install(target, reinterpret_cast<void*>(&Detour),
                              std::span<const uint8_t>(kPrologue.data(), 13)),
                "short overwrite accepted");
        Require(!hook.Install(nullptr, reinterpret_cast<void*>(&Detour), kPrologue), "null target accepted");
        Require(!hook.Install(target, nullptr, kPrologue), "null detour accepted");
        Require(!hook.Install(target, target, kPrologue), "self detour accepted");
        Require(!hook.Install(reinterpret_cast<void*>(uintptr_t{1}),
                              reinterpret_cast<void*>(&Detour), kPrologue), "invalid target accepted");

        std::array<uint8_t, 20> writableBuffer = kPrologue;
        Require(!hook.Install(writableBuffer.data(), reinterpret_cast<void*>(&Detour), kPrologue),
                "non-executable target accepted");

        std::atomic<bool> started{false};
        std::atomic<bool> stop{false};
        std::thread worker([&] {
            started.store(true, std::memory_order_release);
            while (!stop.load(std::memory_order_acquire))
                std::this_thread::yield();
        });
        while (!started.load(std::memory_order_acquire))
            std::this_thread::yield();
        const bool installed = hook.Install(target, reinterpret_cast<void*>(&Detour), kPrologue);
        stop.store(true, std::memory_order_release);
        worker.join();
        Require(!installed, "hook installed while another thread was active");
        Require(std::memcmp(target, kPrologue.data(), kPrologue.size()) == 0,
                "thread guard changed target");
    }

    void TestRoutingTrampolineAndLifetime(void* target)
    {
        auto native = reinterpret_cast<NativeFunction>(target);
        Require(native(5) == 13, "synthetic original returned wrong value");
        {
            Obelisk::Hooks::StartupNativeHook hook;
            Require(hook.Install(target, reinterpret_cast<void*>(&Detour), kPrologue),
                    "verified startup hook installation failed");
            Require(hook.IsInstalled() && hook.Trampoline(), "installed hook state absent");
            g_Original = reinterpret_cast<NativeFunction>(hook.Trampoline());
            // RAX is already live at the jump-back point. A mov rax/jmp rax
            // trampoline would corrupt this computed return value.
            Require(g_Original(5) == 13, "trampoline clobbered RAX or omitted original instructions");
            Require(native(5) == 113 && g_DetourCalls == 1, "target did not route through detour");
            Require(native(-10) == 98 && g_DetourCalls == 2, "hook failed to preserve argument registers");
            Require(!hook.Install(target, reinterpret_cast<void*>(&Detour), kPrologue),
                    "second installation accepted");
            Require(hook.IsInstalled() && hook.Trampoline() == reinterpret_cast<void*>(g_Original),
                    "second installation damaged existing trampoline");
        }
        Require(g_Original(10) == 18, "destruction unmapped installed trampoline");
        Require(native(10) == 118 && g_DetourCalls == 3, "destruction removed installed patch");
        // Installed code remains mapped until this test process exits.
    }
}

int main()
{
    void* target = MakeCodePage();
    TestRejectsUnsafeInstallations(target);
    TestRoutingTrampolineAndLifetime(target);
    std::cout << "StartupNativeHookTests passed\n";
    return 0;
}
