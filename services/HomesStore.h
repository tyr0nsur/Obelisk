#pragma once

#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace Obelisk::Services
{
    struct HomesSubject { std::string Namespace, OpaqueId; };
    struct HomePosition { double X = 0, Y = 0, Z = 0, Yaw = 0; };
    struct HomeRecord
    {
        std::string Name, WorldFingerprint;
        HomePosition Position;
        int64_t Revision = 0, UpdatedUtcSeconds = 0;
        std::optional<int64_t> ExpiresUtcSeconds;
    };
    enum class HomesStatus
    {
        Ok, InvalidArgument, InvalidPath, NotFound, Expired, WorldMismatch,
        QuotaExceeded, Cooldown, ReservationPending, ReservationExpired,
        PayloadConflict, AlreadyCompleted, Busy, UnsupportedSchema, StorageError
    };
    struct HomesListResult { HomesStatus Status = HomesStatus::StorageError; std::vector<HomeRecord> Homes; };
    struct HomeResult { HomesStatus Status = HomesStatus::StorageError; HomeRecord Home; };
    struct HomeTravelResult
    {
        HomesStatus Status = HomesStatus::StorageError;
        HomeRecord Home;
        bool Replayed = false;
        int64_t LeaseUntilUtcSeconds = 0, NextAllowedUtcSeconds = 0;
    };
    // Private durable policy storage. Caller supplies an established external
    // subject and an explicit save/world fingerprint. Neither identifies an
    // authenticated native player, grants permission, or executes teleport.
    class HomesStore
    {
    public:
        static constexpr int SchemaVersion = 1;
        static constexpr double MaximumCoordinateMagnitude = 100000000;
        static std::unique_ptr<HomesStore> Open(const std::filesystem::path& privateRoot,
            std::string_view instanceId, HomesStatus& status) noexcept;
        ~HomesStore() noexcept;
        HomesStore(const HomesStore&) = delete;
        HomesStore& operator=(const HomesStore&) = delete;

        // ASCII home names (a-z/0-9/_/-), 1..32 bytes. Names are case sensitive.
        // Quota counts all active homes of this subject, including other worlds.
        HomesStatus Put(const HomesSubject& subject, std::string_view name,
            std::string_view worldFingerprint, HomePosition position, int64_t nowUtcSeconds,
            uint32_t quota, std::optional<int64_t> expiresUtcSeconds = std::nullopt) noexcept;
        HomeResult Get(const HomesSubject& subject, std::string_view name,
            std::string_view currentWorldFingerprint, int64_t nowUtcSeconds) noexcept;
        HomesListResult List(const HomesSubject& subject, int64_t nowUtcSeconds) noexcept;
        HomesStatus Remove(const HomesSubject& subject, std::string_view name) noexcept;

        // Reserves one copied destination per subject; cross-connection atomic.
        // Identical operation IDs replay the original reservation. Changed
        // subject/name/world/cooldown/lease payload conflicts. Retrying does not
        // extend the lease, bypass the quota, or renew an expired operation.
        HomeTravelResult ReserveTravel(const HomesSubject& subject, std::string_view name,
            std::string_view currentWorldFingerprint, int64_t nowUtcSeconds,
            int64_t cooldownSeconds, int64_t leaseSeconds, std::string_view operationId) noexcept;
        // Revalidate immediately before acting: same subject, world, home
        // revision and unexpired reservation. This remains a storage decision;
        // the adapter must also validate live character/gameplay restrictions.
        HomeTravelResult ResolveTravel(const HomesSubject& subject, std::string_view operationId,
            std::string_view currentWorldFingerprint, int64_t nowUtcSeconds) noexcept;
        // Call only after the adapter reports the outcome. Failure releases the
        // reservation without spending cooldown; success starts cooldown NOW.
        // Completion is idempotent; conflicting outcomes cannot rewrite history.
        HomeTravelResult FinishTravel(const HomesSubject& subject, std::string_view operationId,
            bool succeeded, int64_t nowUtcSeconds) noexcept;
    private:
        struct Impl;
        explicit HomesStore(std::unique_ptr<Impl>) noexcept;
        std::unique_ptr<Impl> m_Impl;
    };
}
