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
        PlayerPrincipal,
        Command,
        PlayerLifecycle,
        ProcessEvent,
        Timer,
    };

    class GameplayCallbackScope
    {
    public:
        enum class TrackingMode { Gameplay, CurrentOnly };

        // CurrentOnly marks a runtime callback without changing the gameplay
        // depths used by existing cross-family cleanup/unload policies.
        explicit GameplayCallbackScope(GameplayCallbackFamily family, TrackingMode mode = TrackingMode::Gameplay)
            : m_Family(family)
            , m_CountsDepth(mode == TrackingMode::Gameplay)
            , m_Previous(CurrentStorage())
        {
            if (m_CountsDepth)
                ++Depth(m_Family);
            CurrentStorage() = this;
        }

        GameplayCallbackScope(const GameplayCallbackScope&) = delete;
        GameplayCallbackScope& operator=(const GameplayCallbackScope&) = delete;

        ~GameplayCallbackScope()
        {
            CurrentStorage() = m_Previous;
            if (m_CountsDepth)
                --Depth(m_Family);
        }

        static const GameplayCallbackScope* Current()
        {
            return CurrentStorage();
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
                Depth(GameplayCallbackFamily::Mission) != 0 ||
                Depth(GameplayCallbackFamily::PlayerPrincipal) != 0 ||
                Depth(GameplayCallbackFamily::Command) != 0 ||
                Depth(GameplayCallbackFamily::PlayerLifecycle) != 0 ||
                Depth(GameplayCallbackFamily::ProcessEvent) != 0 ||
                Depth(GameplayCallbackFamily::Timer) != 0;
        }

    private:
        static const GameplayCallbackScope*& CurrentStorage()
        {
            static thread_local const GameplayCallbackScope* current = nullptr;
            return current;
        }

        static size_t& Depth(GameplayCallbackFamily family)
        {
            static thread_local size_t chatDepth = 0;
            static thread_local size_t structureDepth = 0;
            static thread_local size_t inventoryDepth = 0;
            static thread_local size_t missionDepth = 0;
            static thread_local size_t playerPrincipalDepth = 0;
            static thread_local size_t commandDepth = 0;
            static thread_local size_t playerLifecycleDepth = 0;
            static thread_local size_t processEventDepth = 0;
            static thread_local size_t timerDepth = 0;
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
            case GameplayCallbackFamily::PlayerPrincipal:
                return playerPrincipalDepth;
            case GameplayCallbackFamily::Command:
                return commandDepth;
            case GameplayCallbackFamily::PlayerLifecycle:
                return playerLifecycleDepth;
            case GameplayCallbackFamily::ProcessEvent:
                return processEventDepth;
            case GameplayCallbackFamily::Timer:
                return timerDepth;
            }
            return chatDepth;
        }

        GameplayCallbackFamily m_Family;
        bool m_CountsDepth;
        const GameplayCallbackScope* m_Previous;
    };
}
