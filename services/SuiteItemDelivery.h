#pragma once

#include "SuiteStore.h"
#include <cstdint>
#include <string>
#include <vector>

namespace Obelisk::Services
{
    // Private copied evidence, supplied only by a future verified native adapter.
    // Tokens are non-reusable process-local inventory/item lifetimes, not account
    // IDs. Variant includes every requested attribute (class, blueprint, quality,
    // etc.); matching only a display name or class is insufficient.
    struct SuiteInventoryContext
    {
        uint64_t ProcessEpoch = 0;
        uint64_t SessionToken = 0;
        uint64_t InventoryToken = 0;
        bool operator==(const SuiteInventoryContext&) const = default;
    };

    struct SuiteInventoryItem
    {
        uint64_t ItemToken = 0;
        std::string Variant;
        int64_t Quantity = 0;
    };

    struct SuiteInventorySnapshot
    {
        SuiteInventoryContext Context;
        bool Complete = false;
        std::vector<SuiteInventoryItem> Items;
    };

    struct SuiteItemDeliveryExpected
    {
        std::string Variant;
        int64_t Quantity = 0;
    };

    struct SuiteItemDeliveryEvidence
    {
        SuiteInventorySnapshot Before;
        SuiteInventorySnapshot After;
        bool NativeCallReturned = false;
        // Adapter must establish exclusive attribution and no unobserved
        // destinations or side effects. Ordinary inventory reads do not do so.
        bool ExclusiveAttribution = false;
    };

    enum class SuiteItemDeliveryReason
    {
        ExactQuantity,
        UnchangedInventory,
        InvalidSpecification,
        CallIncomplete,
        AttributionUnknown,
        ContextChanged,
        SnapshotIncomplete,
        SnapshotInvalid,
        UnexpectedInventoryChange,
        PartialOrExcessQuantity,
    };

    struct SuiteItemDeliveryVerification
    {
        SuiteDeliveryOutcome Outcome = SuiteDeliveryOutcome::Uncertain;
        SuiteItemDeliveryReason Reason = SuiteItemDeliveryReason::SnapshotInvalid;
        bool DeltaKnown = false;
        int64_t ObservedQuantity = 0;
    };

    // Never calls ARK, authenticates a player, grants an item, refunds a wallet,
    // or authorizes replay. A native success boolean is deliberately not an
    // input: it can mean partial delivery. CompleteDelivery consumes this result
    // only after a durable BeginDelivery admitted exactly one native attempt.
    SuiteItemDeliveryVerification VerifySuiteItemDelivery(
        const SuiteItemDeliveryExpected&, const SuiteItemDeliveryEvidence&) noexcept;
}
