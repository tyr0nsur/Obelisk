#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace Obelisk::Hooks
{
    // A deliberately limited x86-64 hook for startup, before threads execute
    // gameplay code. expectedPrologue must contain complete instructions and
    // no relative branches, RIP-relative operands, or other relocations.
    // The caller establishes these properties from the exact binary profile.
    // The task-count guard cannot serialize a concurrent thread creation.
    // An installed hook, detour code and trampoline must stay loaded until
    // process exit. Destruction does not remove the patch or unmap its code.
    class StartupNativeHook
    {
    public:
        StartupNativeHook() = default;
        ~StartupNativeHook() = default;
        StartupNativeHook(const StartupNativeHook&) = delete;
        StartupNativeHook& operator=(const StartupNativeHook&) = delete;
        StartupNativeHook(StartupNativeHook&&) = delete;
        StartupNativeHook& operator=(StartupNativeHook&&) = delete;

        bool Install(void* target, void* detour,
                     std::span<const uint8_t> expectedPrologue) noexcept;
        void* Trampoline() const noexcept { return m_Trampoline; }
        bool IsInstalled() const noexcept { return m_Installed; }
        std::string_view LastError() const noexcept { return m_LastError; }

    private:
        void* m_Trampoline = nullptr;
        bool m_Installed = false;
        std::string_view m_LastError;
    };
}
