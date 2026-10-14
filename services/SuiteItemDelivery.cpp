#include "SuiteItemDelivery.h"
#include <limits>
#include <map>
#include <string_view>

namespace Obelisk::Services
{
    namespace
    {
        bool VariantValid(std::string_view value)
        {
            if (value.empty() || value.size() > 512) return false;
            for (const unsigned char byte : value)
                if (byte < 32 || byte > 126) return false;
            return true;
        }

        using Items = std::map<uint64_t, const SuiteInventoryItem*>;
        bool ReadSnapshot(const SuiteInventorySnapshot& snapshot, Items& items)
        {
            if (snapshot.Items.size() > 4096) return false;
            for (const auto& item : snapshot.Items)
            {
                if (!item.ItemToken || !VariantValid(item.Variant) || item.Quantity <= 0 ||
                    item.Quantity > std::numeric_limits<int32_t>::max() ||
                    !items.emplace(item.ItemToken, &item).second) return false;
            }
            return true;
        }

        SuiteItemDeliveryVerification Unknown(SuiteItemDeliveryReason reason)
        { return {SuiteDeliveryOutcome::Uncertain, reason, false, 0}; }
    }

    SuiteItemDeliveryVerification VerifySuiteItemDelivery(
        const SuiteItemDeliveryExpected& expected, const SuiteItemDeliveryEvidence& evidence) noexcept
    {
        try
        {
            if (!VariantValid(expected.Variant) || expected.Quantity <= 0 || expected.Quantity > 1000000)
                return Unknown(SuiteItemDeliveryReason::InvalidSpecification);
            if (!evidence.NativeCallReturned) return Unknown(SuiteItemDeliveryReason::CallIncomplete);
            if (!evidence.ExclusiveAttribution) return Unknown(SuiteItemDeliveryReason::AttributionUnknown);
            const auto& context = evidence.Before.Context;
            if (!context.ProcessEpoch || !context.SessionToken || !context.InventoryToken ||
                context != evidence.After.Context) return Unknown(SuiteItemDeliveryReason::ContextChanged);
            if (!evidence.Before.Complete || !evidence.After.Complete)
                return Unknown(SuiteItemDeliveryReason::SnapshotIncomplete);
            Items before, after;
            if (!ReadSnapshot(evidence.Before, before) || !ReadSnapshot(evidence.After, after))
                return Unknown(SuiteItemDeliveryReason::SnapshotInvalid);
            int64_t delta = 0;
            for (const auto& [token, item] : before)
            {
                const auto found = after.find(token);
                if (found == after.end() || item->Variant != found->second->Variant)
                    return Unknown(SuiteItemDeliveryReason::UnexpectedInventoryChange);
                const auto increase = found->second->Quantity - item->Quantity;
                if (increase < 0 || (increase && item->Variant != expected.Variant))
                    return Unknown(SuiteItemDeliveryReason::UnexpectedInventoryChange);
                delta += increase;
            }
            for (const auto& [token, item] : after)
            {
                if (before.contains(token)) continue;
                if (item->Variant != expected.Variant)
                    return Unknown(SuiteItemDeliveryReason::UnexpectedInventoryChange);
                delta += item->Quantity;
            }
            // Bounds above give <=4096*INT32_MAX, comfortably inside int64_t.
            if (!delta)
                return {SuiteDeliveryOutcome::VerifiedNoDelivery,
                    SuiteItemDeliveryReason::UnchangedInventory, true, 0};
            if (delta == expected.Quantity)
                return {SuiteDeliveryOutcome::Delivered, SuiteItemDeliveryReason::ExactQuantity, true, delta};
            return {SuiteDeliveryOutcome::Uncertain,
                SuiteItemDeliveryReason::PartialOrExcessQuantity, true, delta};
        }
        catch (...) { return Unknown(SuiteItemDeliveryReason::SnapshotInvalid); }
    }
}
