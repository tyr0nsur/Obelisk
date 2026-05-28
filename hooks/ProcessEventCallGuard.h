#pragma once

#include <cstddef>

namespace Obelisk::Hooks::ProcessEventCallGuard
{
    class PreCallbackScope
    {
    public:
        PreCallbackScope();
        ~PreCallbackScope();

        PreCallbackScope(const PreCallbackScope&) = delete;
        PreCallbackScope& operator=(const PreCallbackScope&) = delete;

        bool OriginalCalled() const;

    private:
        std::size_t m_Depth = 0;
        bool m_Active = false;
    };

    void MarkOriginalCalledFromPublicApi();
    bool IsInsidePreCallback();
}
