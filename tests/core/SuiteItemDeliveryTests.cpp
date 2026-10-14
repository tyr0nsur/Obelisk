#include "services/SuiteItemDelivery.h"
#include <chrono>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <sys/stat.h>

using namespace Obelisk::Services;
namespace fs = std::filesystem;

namespace
{
    void Require(bool value, const char* message)
    { if (!value) throw std::runtime_error(message); }

    SuiteItemDeliveryEvidence Evidence()
    {
        const SuiteInventorySnapshot before{{41, 52, 63}, true,
            {{101, "stone|blueprint=0|quality=0", 100}, {102, "wood|blueprint=0|quality=0", 30}}};
        return {before, before, true, true};
    }

    const SuiteItemDeliveryExpected Expected{"stone|blueprint=0|quality=0", 10};

    void TestReceipts()
    {
        auto evidence = Evidence();
        auto result = VerifySuiteItemDelivery(Expected, evidence);
        Require(result.Outcome == SuiteDeliveryOutcome::VerifiedNoDelivery && result.DeltaKnown,
            "Complete unchanged isolated inventory did not prove no delivery");
        evidence.After.Items[0].Quantity += 10;
        result = VerifySuiteItemDelivery(Expected, evidence);
        Require(result.Outcome == SuiteDeliveryOutcome::Delivered && result.ObservedQuantity == 10,
            "Existing stack increase was confused with entire stack quantity");
        evidence = Evidence(); evidence.After.Items.push_back({103, Expected.Variant, 4});
        evidence.After.Items.push_back({104, Expected.Variant, 6});
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Delivered,
            "Split new stacks did not establish exact quantity");
        evidence = Evidence(); evidence.After.Items[0].Quantity += 4;
        evidence.After.Items.push_back({103, Expected.Variant, 6});
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Delivered,
            "Mixed existing/new stacks did not establish exact quantity");
        for (const auto delta : {1, 9, 11, 100})
        {
            evidence = Evidence(); evidence.After.Items[0].Quantity += delta;
            result = VerifySuiteItemDelivery(Expected, evidence);
            Require(result.Outcome == SuiteDeliveryOutcome::Uncertain && result.ObservedQuantity == delta,
                "Partial/excess grant was treated as full delivery or no delivery");
        }
        evidence = Evidence(); evidence.Before.Complete = false;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Truncated before snapshot admitted a refund");
        evidence = Evidence(); evidence.After.Complete = false;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Truncated after snapshot admitted a refund");
        evidence = Evidence(); evidence.ExclusiveAttribution = false;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Read-only snapshots were promoted to mutation attribution");
        evidence = Evidence(); evidence.NativeCallReturned = false;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Interrupted native call admitted a refund");
        for (int field = 0; field < 3; ++field)
        {
            evidence = Evidence();
            if (field == 0) ++evidence.After.Context.ProcessEpoch;
            if (field == 1) ++evidence.After.Context.SessionToken;
            if (field == 2) ++evidence.After.Context.InventoryToken;
            Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
                "Successor process/session/inventory reused previous evidence");
        }
        evidence = Evidence(); evidence.After.Items[0].Variant = "stone|blueprint=1|quality=0";
        evidence.After.Items[0].Quantity += 10;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Changed item identity/blueprint was accepted");
        evidence = Evidence(); evidence.After.Items[1].Quantity += 1;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Unrelated inventory changes admitted no-delivery refund");
        evidence = Evidence(); evidence.After.Items[0].Quantity -= 1;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Quantity reduction was accepted as unchanged inventory");
        evidence = Evidence(); evidence.After.Items.pop_back();
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Removed item was accepted as unchanged inventory");
        evidence = Evidence(); evidence.After.Items.push_back(evidence.After.Items[0]);
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Duplicate item token was double counted");
        evidence = Evidence(); evidence.After.Items[0].ItemToken = 0;
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Unknown item lifetime was accepted");
        evidence = Evidence(); evidence.After.Items[0].Quantity = std::numeric_limits<int64_t>::max();
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Native quantity bound was ignored");
        evidence = Evidence(); evidence.After.Items.assign(4097, evidence.After.Items[0]);
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Unbounded inventory was accepted");
        evidence = Evidence(); evidence.After.Items[0].Variant = std::string("stone\0forged", 12);
        Require(VerifySuiteItemDelivery(Expected, evidence).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Embedded NUL variant was accepted");
        Require(VerifySuiteItemDelivery({Expected.Variant, 0}, Evidence()).Outcome == SuiteDeliveryOutcome::Uncertain,
            "Empty specification was accepted");
    }

    void TestDurableFinalization()
    {
        const auto root = fs::temp_directory_path() / ("ObeliskDelivery_" +
            std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        fs::create_directory(root); chmod(root.c_str(), 0700);
        struct Cleanup
        {
            fs::path Path;
            ~Cleanup() { std::error_code error; fs::remove_all(Path, error); }
        } cleanup{root};
        fs::create_directory(root / "receipts"); chmod((root / "receipts").c_str(), 0700);
        SuiteStoreStatus status;
        auto store = SuiteStore::Open(root, "receipts", status);
        Require(store && status == SuiteStoreStatus::Ok, "Receipt integration database did not open");
        const SuiteSubject subject{"operator-fixture", "account-a"};
        Require(store->Credit(subject, 100, "initial-credit").Status == SuiteStoreStatus::Ok, "Credit failed");
        const SuiteReceiptRequest request{subject, "stone", "own-catalog-v1", Expected.Variant, 10, 2, 1000};
        Require(store->ReservePurchase(request, "purchase-partial").Status == SuiteStoreStatus::Ok, "Reserve failed");
        const auto admitted = store->BeginDelivery("purchase-partial", "attempt-partial");
        Require(admitted.Status == SuiteStoreStatus::Ok && !admitted.Replayed, "Initial attempt not admitted");
        auto partial = Evidence(); partial.After.Items[0].Quantity += 3;
        const auto outcome = VerifySuiteItemDelivery(Expected, partial).Outcome;
        Require(outcome == SuiteDeliveryOutcome::Uncertain, "Partial receipt was not uncertain");
        Require(store->CompleteDelivery("purchase-partial", "attempt-partial", outcome).State == SuiteReceiptState::Uncertain,
            "Partial result was not durably blocked");
        Require(store->Balance(subject).Balance == 80 && store->BeginDelivery("purchase-partial", "attempt-partial").Status == SuiteStoreStatus::InvalidState,
            "Partial attempt refunded or admitted an automatic second grant");
        Require(store->CompleteDelivery("purchase-partial", "attempt-partial", SuiteDeliveryOutcome::VerifiedNoDelivery).Status != SuiteStoreStatus::Ok,
            "An uncertain receipt was overwritten by a refund");
        Require(store->ReservePurchase(request, "purchase-none").Status == SuiteStoreStatus::Ok, "Second reserve failed");
        Require(store->BeginDelivery("purchase-none", "attempt-none").Status == SuiteStoreStatus::Ok, "Second attempt failed");
        Require(store->CompleteDelivery("purchase-none", "attempt-none", VerifySuiteItemDelivery(Expected, Evidence()).Outcome).State == SuiteReceiptState::NoDelivery,
            "Verified unchanged inventory did not finalize no delivery");
        Require(store->Balance(subject).Balance == 80, "Verified no delivery did not refund exactly once");
        store.reset(); store = SuiteStore::Open(root, "receipts", status);
        Require(store && store->Receipt("purchase-partial").Result.State == SuiteReceiptState::Uncertain &&
            store->Balance(subject).Balance == 80, "Reopening lost blocked partial receipt or balance");
        store.reset(); fs::remove_all(root);
    }
}

int main()
{
    try { TestReceipts(); TestDurableFinalization(); std::cout << "Suite item delivery verification passed\n"; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
