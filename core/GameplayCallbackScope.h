#pragma once

#include <cstddef>

namespace Obelisk::Core
{
    enum class GameplayCallbackFamily
    {
        Chat,
        Structure,
        Inventory,
        Mission,
    };

    class GameplayCallbackScope
    {
    public:
        explicit GameplayCallbackScope(GameplayCallbackFamily family)
            : m_Family(family)
        {
            ++Depth(m_Family);
        }

        GameplayCallbackScope(const GameplayCallbackScope&) = delete;
        GameplayCallbackScope& operator=(const GameplayCallbackScope&) = delete;

        ~GameplayCallbackScope()
        {
            --Depth(m_Family);
        }

        static bool IsInsideCallback(GameplayCallbackFamily family)
        {
            return Depth(family) != 0;
        }

        static bool IsInsideAnyCallback()
        {
            return Depth(GameplayCallbackFamily::Chat) != 0 ||
                Depth(GameplayCallbackFamily::Structure) != 0 ||
                Depth(GameplayCallbackFamily::Inventory) != 0 ||
                Depth(GameplayCallbackFamily::Mission) != 0;
        }

    private:
        static size_t& Depth(GameplayCallbackFamily family)
        {
            static thread_local size_t chatDepth = 0;
            static thread_local size_t structureDepth = 0;
            static thread_local size_t inventoryDepth = 0;
            static thread_local size_t missionDepth = 0;
            switch (family)
            {
            case GameplayCallbackFamily::Chat:
                return chatDepth;
            case GameplayCallbackFamily::Structure:
                return structureDepth;
            case GameplayCallbackFamily::Inventory:
                return inventoryDepth;
            case GameplayCallbackFamily::Mission:
                return missionDepth;
            }
            return chatDepth;
        }

        GameplayCallbackFamily m_Family;
    };
}
