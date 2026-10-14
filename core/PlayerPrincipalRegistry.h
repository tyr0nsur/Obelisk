#pragma once

#include <cstddef>
#include <cstdint>
#include <mutex>
#include <unordered_map>

namespace Obelisk::Core
{
    using PlayerPrincipalInvalidationFlags = uint64_t;

    enum class PlayerPrincipalInvalidationReason : uint64_t
    {
        None = 0,
        Logout = 1ull << 0,
        Reconnect = 1ull << 1,
        RuntimeReset = 1ull << 2,
        Superseded = 1ull << 3,
    };

    constexpr PlayerPrincipalInvalidationFlags PlayerPrincipalInvalidationFlag(
        PlayerPrincipalInvalidationReason reason)
    {
        return static_cast<PlayerPrincipalInvalidationFlags>(reason);
    }

    struct PlayerPrincipalToken
    {
        uint64_t Handle = 0;
        uint64_t Generation = 0;
        uint64_t RegistryId = 0;

        bool HasValidShape() const
        {
            return Handle != 0 && Generation != 0 && RegistryId != 0;
        }
    };

    enum class PlayerPrincipalLookupStatus : uint32_t
    {
        Valid,
        ZeroHandle,
        ZeroGeneration,
        ZeroRegistryId,
        RegistryMismatch,
        UnknownHandle,
        StaleGeneration,
        Invalidated,
    };

    struct PlayerPrincipalLookup
    {
        PlayerPrincipalLookupStatus Status = PlayerPrincipalLookupStatus::UnknownHandle;
        uint64_t Handle = 0;
        uint64_t RequestedGeneration = 0;
        uint64_t CurrentGeneration = 0;
        uint64_t RequestedRegistryId = 0;
        uint64_t CurrentRegistryId = 0;
        PlayerPrincipalInvalidationFlags InvalidationReasons = 0;
        bool Live = false;

        bool IsValid() const
        {
            return Status == PlayerPrincipalLookupStatus::Valid;
        }
    };

    // Internal runtime registry only. Handles are opaque, process-local counters; do not
    // persist them or derive them from UE/player identity data.
    class PlayerPrincipalRegistry
    {
    public:
        PlayerPrincipalRegistry();
        PlayerPrincipalRegistry(const PlayerPrincipalRegistry&) = delete;
        PlayerPrincipalRegistry& operator=(const PlayerPrincipalRegistry&) = delete;

        static PlayerPrincipalRegistry& Get();

        PlayerPrincipalToken AllocatePrincipal();
        // Reactivation requires the exact invalidated token and an explicit reconnect
        // invalidation, not plain logout or terminal reset/supersede states.
        PlayerPrincipalToken ReactivatePrincipal(const PlayerPrincipalToken& token);
        bool InvalidatePrincipal(const PlayerPrincipalToken& token,
                                 PlayerPrincipalInvalidationFlags reasons);
        bool LogoutPrincipal(const PlayerPrincipalToken& token);
        PlayerPrincipalLookup Lookup(const PlayerPrincipalToken& token) const;
        bool Validate(const PlayerPrincipalToken& token) const;
        size_t LiveCount() const;
        size_t RetainedInvalidatedCount() const;

#ifdef OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS
        void SetNextHandleForTesting(uint64_t nextHandle);
        void SetNextRetiredSequenceForTesting(uint64_t nextSequence);
        void SetMaxRetainedInvalidatedPrincipalsForTesting(size_t maxRetained);
        bool SetGenerationForTesting(uint64_t handle, uint64_t generation);
#endif

    private:
        struct PrincipalEntry
        {
            uint64_t Generation = 1;
            PlayerPrincipalInvalidationFlags InvalidationReasons = 0;
            uint64_t RetiredSequence = 0;
            bool Live = true;
        };

        uint64_t AllocateHandleLocked();
        uint64_t AllocateRetiredSequenceLocked();
        void PruneRetainedInvalidatedPrincipalsLocked();

        mutable std::mutex m_Mutex;
        uint64_t m_NextHandle = 1;
        uint64_t m_HighWaterHandle = 0;
        uint64_t m_NextRetiredSequence = 1;
        size_t m_LiveCount = 0;
        size_t m_RetainedInvalidatedCount = 0;
        size_t m_MaxRetainedInvalidatedPrincipals = 4096;
        std::unordered_map<uint64_t, PrincipalEntry> m_Principals;
        uint64_t m_RegistryId = 0;
    };
}
