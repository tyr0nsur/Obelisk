#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <string_view>

namespace Obelisk::Services
{
    // Private offline storage. Subjects come from an explicit external authority;
    // their bytes and namespaces establish no authentication or ARK permissions.
    struct SuiteSubject
    {
        std::string Namespace;
        std::string OpaqueId;
    };

    enum class SuiteStoreStatus
    {
        Ok,
        InvalidArgument,
        InvalidPath,
        NotFound,
        InsufficientFunds,
        Overflow,
        PayloadConflict,
        Busy,
        UnsupportedSchema,
        StorageError,
        InvalidState,
        LimitReached,
        CooldownActive,
    };

    enum class SuitePermissionEffect { Allow = 0, Deny = 1 };

    struct SuitePermissionResult
    {
        SuiteStoreStatus Status = SuiteStoreStatus::StorageError;
        bool Allowed = false;
        bool ExplicitDeny = false;
    };

    struct SuiteBalanceResult
    {
        SuiteStoreStatus Status = SuiteStoreStatus::StorageError;
        int64_t Balance = 0;
        bool Exists = false;
    };

    struct SuiteOperationResult
    {
        SuiteStoreStatus Status = SuiteStoreStatus::StorageError;
        bool Replayed = false;
        // Original committed results on replay, not today's wallet balances.
        // Balance is the subject's result for Credit/Debit, source for Transfer.
        int64_t Balance = 0;
        int64_t DestinationBalance = 0;
    };

    enum class SuiteReceiptKind { Purchase = 1, Kit = 2 };
    enum class SuiteReceiptState { Reserved = 1, Attempting = 2, Delivered = 3, NoDelivery = 4, Uncertain = 5 };
    enum class SuiteDeliveryOutcome { Delivered = 1, VerifiedNoDelivery = 2, Uncertain = 3 };

    // Server-authoritative immutable request, not player-provided prices or
    // proof of identity. Payload identifies the complete delivery specification.
    struct SuiteReceiptRequest
    {
        SuiteSubject Subject;
        std::string ProductId;
        std::string CatalogRevision;
        std::string FulfillmentPayload;
        int64_t Quantity = 1;
        int64_t UnitPrice = 0;
        int64_t RequestedUtcSeconds = 0;
        int64_t KitMaxClaims = 0; // zero: unlimited
        int64_t KitCooldownSeconds = 0;
    };

    struct SuiteReceiptResult
    {
        SuiteStoreStatus Status = SuiteStoreStatus::StorageError;
        bool Replayed = false;
        SuiteReceiptState State = SuiteReceiptState::Reserved;
        int64_t ReservedBalance = 0; // original balance after reservation debit
        std::optional<int64_t> RefundedBalance; // original balance after refund
    };

    struct SuiteReceiptSnapshot
    {
        SuiteReceiptResult Result;
        SuiteReceiptKind Kind = SuiteReceiptKind::Purchase;
        SuiteReceiptRequest Request;
        std::string AttemptId;
    };

    class SuiteStore
    {
    public:
        static constexpr int SchemaVersion = 2;
        static constexpr size_t OpaqueIdMaxBytes = 256;

        // Existing absolute privateRoot and its instance child must be real
        // directories owned by the current UID/root with mode 0700. No symlink
        // components are accepted. Ancestors must be current UID/root owned and
        // not writable by group/others, except trusted-owner sticky directories.
        // Creates instance/suite.sqlite3 with mode 0600; paths must remain stable.
        static std::unique_ptr<SuiteStore> Open(
            const std::filesystem::path& privateRoot, std::string_view instanceId,
            SuiteStoreStatus& status) noexcept;
        ~SuiteStore() noexcept;
        SuiteStore(const SuiteStore&) = delete;
        SuiteStore& operator=(const SuiteStore&) = delete;

        SuiteStoreStatus CreateRole(std::string_view role) noexcept;
        SuiteStoreStatus PutPermission(std::string_view role, std::string_view pattern,
                                       SuitePermissionEffect effect) noexcept;
        SuiteStoreStatus RemovePermission(std::string_view role, std::string_view pattern) noexcept;
        SuiteStoreStatus PutMembership(const SuiteSubject& subject, std::string_view role,
                                       std::optional<int64_t> expiresUtcSeconds = std::nullopt) noexcept;
        SuiteStoreStatus RemoveMembership(const SuiteSubject& subject, std::string_view role) noexcept;
        // Exact ASCII dot-separated actions or terminal subtree pattern "a.b.*".
        // An active matching deny beats every allow. No rule means deny.
        // Expiry <= now is inactive. Neither this query nor its subject proves
        // authentication, an online session, native player identity or ARK admin.
        SuitePermissionResult CheckPermission(const SuiteSubject& subject, std::string_view action,
                                              int64_t nowUtcSeconds) noexcept;

        SuiteBalanceResult Balance(const SuiteSubject& subject) noexcept;
        // Positive integral units only; no floats, overdraft, or signed overflow.
        // A successful transaction consumes operationId store-wide. An identical
        // payload returns its original results; changed payload conflicts.
        // Failed transactions do not consume the ID and may be retried.
        SuiteOperationResult Credit(const SuiteSubject& subject, int64_t amount,
                                    std::string_view operationId) noexcept;
        SuiteOperationResult Debit(const SuiteSubject& subject, int64_t amount,
                                   std::string_view operationId) noexcept;
        SuiteOperationResult Transfer(const SuiteSubject& source, const SuiteSubject& destination,
                                      int64_t amount, std::string_view operationId) noexcept;

        // Transactionally create receipt and debit. IDs share the wallet
        // operation namespace; exact immutable replay does not debit again.
        SuiteReceiptResult ReservePurchase(const SuiteReceiptRequest&, std::string_view receiptId) noexcept;
        // Kits are free, quantity one. Active reservations/uncertain attempts
        // count toward max claims and cooldown; confirmed no-delivery does not.
        SuiteReceiptResult ReserveKit(const SuiteReceiptRequest&, std::string_view receiptId) noexcept;
        SuiteReceiptSnapshot Receipt(std::string_view receiptId) noexcept;
        // A successful begin is persisted BEFORE invoking any game action.
        // Replayed begin must NOT invoke again; it reports the existing attempt.
        SuiteReceiptResult BeginDelivery(std::string_view receiptId, std::string_view attemptId) noexcept;
        // Only an authoritative adapter may assert delivered or verified no
        // delivery. Attempting/Uncertain never auto-refund/retry after a crash.
        // Uncertain is terminal pending an explicit future reconciliation tool.
        SuiteReceiptResult CompleteDelivery(std::string_view receiptId, std::string_view attemptId,
                                           SuiteDeliveryOutcome outcome) noexcept;

    private:
        SuiteReceiptResult Reserve(SuiteReceiptKind, const SuiteReceiptRequest&, std::string_view) noexcept;
        struct Impl;
        explicit SuiteStore(std::unique_ptr<Impl>) noexcept;
        SuiteOperationResult Apply(int kind, const SuiteSubject& source,
                                   const SuiteSubject* destination, int64_t amount,
                                   std::string_view operationId) noexcept;
        std::unique_ptr<Impl> m_Impl;
    };
}
