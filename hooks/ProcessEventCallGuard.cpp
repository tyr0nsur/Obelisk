#include "ProcessEventCallGuard.h"

#include <array>
#include <cstddef>

namespace Obelisk::Hooks::ProcessEventCallGuard
{
    namespace
    {
        constexpr std::size_t kMaxNestedPreCallbackScopes = 64;

        struct PreCallbackStack
        {
            std::array<bool, kMaxNestedPreCallbackScopes> originalCalled{};
            std::size_t depth = 0;
        };

        thread_local PreCallbackStack s_PreCallbackStack;
    }

    PreCallbackScope::PreCallbackScope()
        : m_Depth(s_PreCallbackStack.depth)
    {
        if (m_Depth < s_PreCallbackStack.originalCalled.size())
        {
            s_PreCallbackStack.originalCalled[m_Depth] = false;
            ++s_PreCallbackStack.depth;
            m_Active = true;
        }
    }

    PreCallbackScope::~PreCallbackScope()
    {
        if (m_Active && s_PreCallbackStack.depth > m_Depth)
            s_PreCallbackStack.depth = m_Depth;
    }

    bool PreCallbackScope::OriginalCalled() const
    {
        return m_Active &&
            s_PreCallbackStack.depth > m_Depth &&
            s_PreCallbackStack.originalCalled[m_Depth];
    }

    void MarkOriginalCalledFromPublicApi()
    {
        if (s_PreCallbackStack.depth > 0 &&
            s_PreCallbackStack.depth <= s_PreCallbackStack.originalCalled.size())
        {
            s_PreCallbackStack.originalCalled[s_PreCallbackStack.depth - 1] = true;
        }
    }

    bool IsInsidePreCallback()
    {
        return s_PreCallbackStack.depth > 0;
    }
}
