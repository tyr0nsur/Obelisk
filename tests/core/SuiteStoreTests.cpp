#include "services/SuiteStore.h"
#include <sqlite3.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>

namespace
{
    using namespace Obelisk::Services;
    using Status = SuiteStoreStatus;
    using Effect = SuitePermissionEffect;
    namespace fs = std::filesystem;
    using namespace std::chrono_literals;

    void Require(bool condition, const char* message)
    {
        if (!condition) throw std::runtime_error(message);
    }

    struct Directory
    {
        fs::path Root;
        Directory()
        {
            char path[] = "/tmp/obelisk-suite-store-tests.XXXXXX";
            const char* value = ::mkdtemp(path);
            Require(value != nullptr, "temporary directory creation failed");
            Root = value;
        }
        ~Directory() { std::error_code error; fs::remove_all(Root, error); }
        fs::path Database(std::string_view instance = "test") const
        { return Root / std::string(instance) / "suite.sqlite3"; }
    };

    struct RawDatabase
    {
        sqlite3* Db = nullptr;
        explicit RawDatabase(const fs::path& path)
        {
            Require(sqlite3_open_v2(path.c_str(), &Db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, nullptr) == SQLITE_OK,
                    "fixture connection failed");
            sqlite3_busy_timeout(Db, 2000);
        }
        ~RawDatabase() { sqlite3_close(Db); }
        void Exec(const char* sql)
        { Require(sqlite3_exec(Db, sql, nullptr, nullptr, nullptr) == SQLITE_OK, "fixture SQL failed"); }
        int64_t Scalar(const char* sql)
        {
            sqlite3_stmt* statement = nullptr;
            Require(sqlite3_prepare_v2(Db, sql, -1, &statement, nullptr) == SQLITE_OK, "fixture query preparation failed");
            const int result = sqlite3_step(statement);
            const int64_t value = result == SQLITE_ROW ? sqlite3_column_int64(statement, 0) : 0;
            sqlite3_finalize(statement);
            Require(result == SQLITE_ROW, "fixture query returned no row");
            return value;
        }
    };

    std::unique_ptr<SuiteStore> Open(const Directory& directory, std::string_view instance = "test")
    {
        Status status;
        auto store = SuiteStore::Open(directory.Root, instance, status);
        Require(store && status == Status::Ok, "suite open/migration failed");
        return store;
    }

    int64_t Balance(SuiteStore& store, const SuiteSubject& subject)
    {
        const auto result = store.Balance(subject);
        Require(result.Status == Status::Ok && result.Balance >= 0, "balance query failed");
        return result.Balance;
    }

    void TestPermissionsDenyExpiryAndNamespaces()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject first{"realm-A", "opaque-玩家🙂'"};
        const SuiteSubject second{"realm-B", first.OpaqueId};
        Require(store->CreateRole("readers") == Status::Ok && store->CreateRole("readers") == Status::Ok,
                "role creation not idempotent");
        Require(store->CreateRole("blocked") == Status::Ok, "deny role creation failed");
        Require(store->PutPermission("missing", "chat.read", Effect::Allow) == Status::NotFound, "missing role accepted");
        Require(store->PutPermission("readers", "chat.*", Effect::Allow) == Status::Ok, "wildcard allow failed");
        Require(store->PutPermission("blocked", "chat.read", Effect::Deny) == Status::Ok, "explicit deny failed");
        Require(store->PutMembership(first, "readers") == Status::Ok, "membership failed");
        Require(store->PutMembership(first, "blocked", 100) == Status::Ok, "expiring membership failed");
        const auto denied = store->CheckPermission(first, "chat.read", 99);
        Require(denied.Status == Status::Ok && !denied.Allowed && denied.ExplicitDeny, "deny did not beat allow");
        const auto expired = store->CheckPermission(first, "chat.read", 100);
        Require(expired.Status == Status::Ok && expired.Allowed && !expired.ExplicitDeny, "expiry boundary wrong");
        Require(store->CheckPermission(first, "chat.read.history", 100).Allowed, "subtree wildcard failed");
        Require(!store->CheckPermission(first, "chat", 100).Allowed &&
                !store->CheckPermission(first, "chatty.read", 100).Allowed &&
                !store->CheckPermission(first, "Chat.read", 100).Allowed, "wildcard broadened across boundaries");
        Require(!store->CheckPermission(second, "chat.read", 100).Allowed, "namespace collapsed or inferred identity");
        Require(store->PutMembership(first, "blocked", 200) == Status::Ok &&
                store->CheckPermission(first, "chat.read", 199).ExplicitDeny, "expiry renewal failed");
        Require(store->RemoveMembership(first, "blocked") == Status::Ok &&
                store->RemoveMembership(first, "blocked") == Status::NotFound, "membership removal wrong");
        Require(store->RemovePermission("readers", "chat.*") == Status::Ok &&
                !store->CheckPermission(first, "chat.read", 100).Allowed, "default deny missing after removal");
        Require(store->PutMembership(first, "missing") == Status::NotFound, "unknown membership role accepted");
        for (const char* pattern : {"*", "chat*", "chat.*.read", "chat..read", "a.b.c.d.e.f.g.h.*"})
            Require(store->PutPermission("readers", pattern, Effect::Allow) == Status::InvalidArgument,
                    "unbounded wildcard or malformed action accepted");
        Require(store->CheckPermission(first, "chat.*", 100).Status == Status::InvalidArgument &&
                store->CheckPermission(first, "chat.read", -1).Status == Status::InvalidArgument &&
                store->PutMembership(first, "readers", -1) == Status::InvalidArgument,
                "invalid action/time accepted");
    }

    void TestPreparedTextAndValidation()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject quoted{"local", "x' OR 1=1 --/../../literal"};
        const SuiteSubject unrelated{"local", "other"};
        Require(store->CreateRole("reader") == Status::Ok &&
                store->PutPermission("reader", "status.read", Effect::Allow) == Status::Ok &&
                store->PutMembership(quoted, "reader") == Status::Ok, "quoted text fixture failed");
        Require(store->CheckPermission(quoted, "status.read", 0).Allowed &&
                !store->CheckPermission(unrelated, "status.read", 0).Allowed, "text escaped its prepared parameter");
        Require(store->Credit(quoted, 7, "op' Unicode🙂").Status == Status::Ok &&
                Balance(*store, quoted) == 7 && Balance(*store, unrelated) == 0, "opaque text wallet key corrupted");
        const SuiteSubject numeric{"local", "18446744073709551615"};
        Require(store->Credit(numeric, 3, "numeric-text").Status == Status::Ok, "large numeric opaque ID was narrowed");
        for (const auto& invalid : {SuiteSubject{"", "id"}, SuiteSubject{"local", ""},
                                   SuiteSubject{"local", std::string("a\0b", 3)},
                                   SuiteSubject{"local", std::string("\xc0\xaf", 2)},
                                   SuiteSubject{"local", std::string("\xed\xa0\x80", 3)},
                                   SuiteSubject{"local", std::string(257, 'x')}})
        {
            Require(store->Balance(invalid).Status == Status::InvalidArgument &&
                    store->PutMembership(invalid, "reader") == Status::InvalidArgument,
                    "invalid UTF-8/subject accepted");
        }
        Require(store->Credit(quoted, 0, "zero").Status == Status::InvalidArgument &&
                store->Debit(quoted, -1, "negative").Status == Status::InvalidArgument &&
                store->Credit(quoted, 1, std::string("x\0y", 3)).Status == Status::InvalidArgument &&
                store->Transfer(quoted, quoted, 1, "self").Status == Status::InvalidArgument,
                "invalid wallet input accepted");
    }

    void TestWalletAtomicityIdempotenceAndConflicts()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject source{"offline", "source"}, target{"offline", "target"}, empty{"offline", "empty"};
        const auto absent = store->Balance(source);
        Require(absent.Status == Status::Ok && absent.Balance == 0 && !absent.Exists, "missing wallet shape wrong");
        const auto credit = store->Credit(source, 10, "credit");
        Require(credit.Status == Status::Ok && !credit.Replayed && credit.Balance == 10, "credit failed");
        Require(store->Debit(source, 3, "debit").Balance == 7, "debit failed");
        const auto replay = store->Credit(source, 10, "credit");
        Require(replay.Status == Status::Ok && replay.Replayed && replay.Balance == 10 && Balance(*store, source) == 7,
                "replay repeated mutation or lost original result");
        const auto transfer = store->Transfer(source, target, 5, "transfer");
        Require(transfer.Status == Status::Ok && transfer.Balance == 2 && transfer.DestinationBalance == 5,
                "transfer did not atomically debit/credit");
        Require(store->Credit(target, 7, "target-credit").Status == Status::Ok, "target credit failed");
        const auto repeated = store->Transfer(source, target, 5, "transfer");
        Require(repeated.Status == Status::Ok && repeated.Replayed && repeated.Balance == 2 &&
                repeated.DestinationBalance == 5 && Balance(*store, target) == 12, "transfer replay not stable");
        Require(store->Transfer(source, target, 4, "transfer").Status == Status::PayloadConflict &&
                store->Transfer(source, empty, 5, "transfer").Status == Status::PayloadConflict &&
                store->Credit(source, 5, "transfer").Status == Status::PayloadConflict &&
                store->Credit(target, 10, "credit").Status == Status::PayloadConflict,
                "changed payload reused committed operation ID");
        Require(Balance(*store, source) == 2 && Balance(*store, target) == 12, "conflict changed wallets");
        Require(store->Transfer(source, empty, 5, "retry").Status == Status::InsufficientFunds &&
                !store->Balance(empty).Exists && Balance(*store, source) == 2, "overdraft left partial state");
        Require(store->Credit(source, 10, "replenish").Status == Status::Ok &&
                store->Transfer(source, empty, 5, "retry").Status == Status::Ok, "failed operation consumed its ID");
        RawDatabase raw(directory.Database());
        Require(raw.Scalar("SELECT count(*) FROM wallet_operations") == 6, "operation journal duplicated/lost commits");
    }

    void TestOverflowAndMaximumIntegralUnits()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject source{"offline", "source"}, full{"offline", "full"};
        constexpr auto maximum = std::numeric_limits<int64_t>::max();
        Require(store->Credit(source, 20, "source-credit").Status == Status::Ok &&
                store->Credit(full, maximum, "maximum").Status == Status::Ok, "maximum integral credit failed");
        Require(store->Credit(full, 1, "overflow-credit").Status == Status::Overflow &&
                store->Transfer(source, full, 1, "overflow-transfer").Status == Status::Overflow &&
                Balance(*store, source) == 20 && Balance(*store, full) == maximum, "overflow mutated a wallet");
        Require(store->Debit(full, 1, "make-room").Status == Status::Ok &&
                store->Transfer(source, full, 1, "overflow-transfer").Status == Status::Ok,
                "rolled-back overflow ID could not retry");
        Require(store->Debit(full, maximum, "maximum-debit").Status == Status::Ok && Balance(*store, full) == 0 &&
                store->Debit(full, 1, "overdraft").Status == Status::InsufficientFunds,
                "maximum debit or nonnegative invariant failed");
    }

    void TestRollbackAfterPartialDatabaseWrites()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject source{"offline", "source"}, target{"offline", "blocked"};
        store->Credit(source, 30, "source-credit");
        store->Credit(target, 3, "target-credit");
        RawDatabase raw(directory.Database());
        raw.Exec("CREATE TRIGGER reject_target BEFORE UPDATE OF balance ON wallets "
                 "WHEN NEW.opaque_id='blocked' BEGIN SELECT RAISE(ABORT,'fixture rejection'); END;");
        Require(store->Transfer(source, target, 10, "late-failure").Status == Status::StorageError,
                "fixture did not interrupt second wallet write");
        Require(Balance(*store, source) == 30 && Balance(*store, target) == 3 &&
                raw.Scalar("SELECT count(*) FROM wallet_operations") == 2, "second-write failure did not roll back first write");
        raw.Exec("DROP TRIGGER reject_target;");
        Require(store->Transfer(source, target, 10, "late-failure").Status == Status::Ok,
                "rollback consumed the operation ID");
        raw.Exec("CREATE TRIGGER reject_record BEFORE INSERT ON wallet_operations "
                 "WHEN NEW.operation_id='record-failure' BEGIN SELECT RAISE(ABORT,'fixture rejection'); END;");
        Require(store->Transfer(source, target, 1, "record-failure").Status == Status::StorageError &&
                Balance(*store, source) == 20 && Balance(*store, target) == 13,
                "journal failure left committed wallet changes");
        raw.Exec("DROP TRIGGER reject_record;");
        Require(store->Transfer(source, target, 1, "record-failure").Status == Status::Ok,
                "journal rollback could not retry");
    }

    void TestReopenPersistenceAndMigrationGuard()
    {
        Directory directory;
        const SuiteSubject subject{"custom.realm", "持久🙂"};
        {
            auto store = Open(directory);
            Require(store->Credit(subject, 8, "persisted").Status == Status::Ok &&
                    store->CreateRole("reader") == Status::Ok &&
                    store->PutPermission("reader", "history.read", Effect::Allow) == Status::Ok &&
                    store->PutMembership(subject, "reader", 1000) == Status::Ok, "persistence setup failed");
        }
        {
            auto store = Open(directory);
            Require(Balance(*store, subject) == 8 && store->CheckPermission(subject, "history.read", 999).Allowed &&
                    !store->CheckPermission(subject, "history.read", 1000).Allowed,
                    "wallet/ACL/expiry did not survive reopen");
            const auto replay = store->Credit(subject, 8, "persisted");
            Require(replay.Status == Status::Ok && replay.Replayed && Balance(*store, subject) == 8,
                    "operation journal did not survive reopen");
        }
        {
            RawDatabase raw(directory.Database());
            Require(raw.Scalar("PRAGMA user_version") == SuiteStore::SchemaVersion, "schema migration not committed");
            raw.Exec("PRAGMA user_version=3;");
        }
        Status status;
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::UnsupportedSchema,
                "future schema accepted/downgraded");
        RawDatabase raw(directory.Database());
        Require(raw.Scalar("PRAGMA user_version") == 3 && raw.Scalar("SELECT balance FROM wallets") == 8,
                "future-version rejection changed stored state");
    }

    void TestForeignSchemaIsNotOverwritten()
    {
        Directory directory;
        fs::create_directory(directory.Root / "test");
        ::chmod((directory.Root / "test").c_str(), 0700);
        {
            RawDatabase raw(directory.Database());
            raw.Exec("CREATE TABLE unrelated(value TEXT); INSERT INTO unrelated VALUES('preserve');");
        }
        ::chmod(directory.Database().c_str(), 0600);
        Status status;
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::UnsupportedSchema,
                "foreign unversioned schema adopted");
        RawDatabase raw(directory.Database());
        Require(raw.Scalar("SELECT count(*) FROM unrelated") == 1 && raw.Scalar("PRAGMA user_version") == 0,
                "foreign schema changed during rejection");
    }

    template<class Fn> SuiteOperationResult RetryBusy(Fn&& operation)
    {
        const auto deadline = std::chrono::steady_clock::now() + 8s;
        for (;;)
        {
            const auto result = operation();
            if (result.Status != Status::Busy || std::chrono::steady_clock::now() >= deadline) return result;
            std::this_thread::sleep_for(1ms);
        }
    }

    void TestTwoConnectionsSerializeWritersAndDuplicateIds()
    {
        Directory directory;
        auto first = Open(directory);
        auto second = Open(directory);
        const SuiteSubject shared{"offline", "shared"}, left{"offline", "left"}, right{"offline", "right"};
        std::atomic<bool> failed{false};
        auto credits = [&](SuiteStore& store, const char* prefix) {
            for (int i = 0; i < 40; ++i)
            {
                const std::string id = std::string(prefix) + std::to_string(i);
                if (RetryBusy([&] { return store.Credit(shared, 1, id); }).Status != Status::Ok) failed = true;
            }
        };
        std::thread one([&] { credits(*first, "one-"); });
        std::thread two([&] { credits(*second, "two-"); });
        one.join(); two.join();
        Require(!failed && Balance(*first, shared) == 80 && Balance(*second, shared) == 80,
                "concurrent connections lost/duplicated credits");
        std::atomic<int> applied{0}, replayed{0};
        const auto duplicate = [&](SuiteStore& store) {
            const auto result = RetryBusy([&] { return store.Credit(shared, 5, "same-operation"); });
            if (result.Status != Status::Ok) failed = true;
            else if (result.Replayed) ++replayed;
            else ++applied;
        };
        std::thread duplicateOne([&] { duplicate(*first); });
        std::thread duplicateTwo([&] { duplicate(*second); });
        duplicateOne.join(); duplicateTwo.join();
        Require(!failed && applied == 1 && replayed == 1 && Balance(*first, shared) == 85,
                "concurrent idempotent request committed twice");
        std::atomic<int> conflictingSuccess{0}, conflictingRejected{0};
        std::atomic<int64_t> winningAmount{0};
        const auto conflicting = [&](SuiteStore& store, int64_t amount) {
            const auto result = RetryBusy([&] { return store.Credit(shared, amount, "different-payload"); });
            if (result.Status == Status::Ok) { ++conflictingSuccess; winningAmount = amount; }
            else if (result.Status == Status::PayloadConflict) ++conflictingRejected;
            else failed = true;
        };
        std::thread conflictingOne([&] { conflicting(*first, 7); });
        std::thread conflictingTwo([&] { conflicting(*second, 9); });
        conflictingOne.join(); conflictingTwo.join();
        Require(!failed && conflictingSuccess == 1 && conflictingRejected == 1 &&
                Balance(*first, shared) == 85 + winningAmount,
                "concurrent changed payload committed instead of conflicting");
        first->Credit(left, 100, "left-seed");
        first->Credit(right, 100, "right-seed");
        auto transfers = [&](SuiteStore& store, const SuiteSubject& source, const SuiteSubject& destination, const char* prefix) {
            for (int i = 0; i < 30; ++i)
            {
                const std::string id = std::string(prefix) + std::to_string(i);
                if (RetryBusy([&] { return store.Transfer(source, destination, 1, id); }).Status != Status::Ok) failed = true;
            }
        };
        std::thread forward([&] { transfers(*first, left, right, "forward-"); });
        std::thread backward([&] { transfers(*second, right, left, "backward-"); });
        forward.join(); backward.join();
        Require(!failed && Balance(*first, left) == 100 && Balance(*first, right) == 100,
                "concurrent transfers lost conservation or updates");
    }

    void TestBusyFailureRollsBackAndCanRetry()
    {
        Directory directory;
        auto store = Open(directory);
        const SuiteSubject subject{"offline", "wallet"};
        RawDatabase raw(directory.Database());
        raw.Exec("BEGIN IMMEDIATE;");
        const auto result = store->Credit(subject, 5, "busy-operation");
        raw.Exec("ROLLBACK;");
        Require(result.Status == Status::Busy && !store->Balance(subject).Exists,
                "busy write was applied or misclassified");
        Require(store->Credit(subject, 5, "busy-operation").Status == Status::Ok && Balance(*store, subject) == 5,
                "busy failure consumed operation ID");
    }

    SuiteReceiptRequest Purchase(const SuiteSubject& subject, int64_t price = 10)
    {
        return {subject, "starter", "catalog-v1", "{\"item\":\"starter\",\"amount\":1}", 1, price, 100, 0, 0};
    }

    void TestReceiptReservationDeliveryAndUncertainty()
    {
        Directory directory;
        const SuiteSubject subject{"external-authority", "opaque-player"};
        auto store = Open(directory);
        Require(store->Credit(subject, 100, "seed").Status == Status::Ok, "commerce seed failed");
        const auto request = Purchase(subject, 12);
        auto reserved = store->ReservePurchase(request, "purchase");
        Require(reserved.Status == Status::Ok && !reserved.Replayed && reserved.ReservedBalance == 88 &&
                reserved.State == SuiteReceiptState::Reserved && Balance(*store, subject) == 88,
                "purchase did not reserve/debit atomically");
        store->Credit(subject, 5, "later-credit");
        const auto replay = store->ReservePurchase(request, "purchase");
        Require(replay.Status == Status::Ok && replay.Replayed && replay.ReservedBalance == 88 && Balance(*store, subject) == 93,
                "reservation replay repeated debit or lost original result");
        auto changed = request; changed.FulfillmentPayload += " ";
        Require(store->ReservePurchase(changed, "purchase").Status == Status::PayloadConflict &&
                store->Credit(subject, 1, "purchase").Status == Status::PayloadConflict &&
                store->ReservePurchase(request, "seed").Status == Status::PayloadConflict,
                "receipt payload/operation ID collision accepted");
        Require(store->BeginDelivery("purchase", "attempt-one").Status == Status::Ok, "begin failed");
        const auto beginReplay = store->BeginDelivery("purchase", "attempt-one");
        Require(beginReplay.Status == Status::Ok && beginReplay.Replayed &&
                store->BeginDelivery("purchase", "attempt-two").Status == Status::InvalidState,
                "delivery admission replay was unsafe");
        store.reset(); store = Open(directory);
        auto saved = store->Receipt("purchase");
        Require(saved.Result.Status == Status::Ok && saved.Result.State == SuiteReceiptState::Attempting &&
                saved.AttemptId == "attempt-one" && saved.Request.FulfillmentPayload == request.FulfillmentPayload &&
                Balance(*store, subject) == 93, "crash/reopen lost pending delivery/debit");
        Require(store->CompleteDelivery("purchase", "wrong-attempt", SuiteDeliveryOutcome::Delivered).Status == Status::PayloadConflict,
                "wrong attempt completed receipt");
        Require(store->CompleteDelivery("purchase", "attempt-one", SuiteDeliveryOutcome::Uncertain).Status == Status::Ok &&
                store->BeginDelivery("purchase", "new-attempt").Status == Status::InvalidState &&
                store->CompleteDelivery("purchase", "attempt-one", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::InvalidState &&
                Balance(*store, subject) == 93, "uncertain attempt was retried/refunded");
        Require(store->CompleteDelivery("purchase", "attempt-one", SuiteDeliveryOutcome::Uncertain).Replayed,
                "uncertain outcome was not idempotent");
        store.reset(); store = Open(directory);
        Require(store->Receipt("purchase").Result.State == SuiteReceiptState::Uncertain && Balance(*store, subject) == 93,
                "uncertainty did not persist");
        Require(store->ReservePurchase(request, "delivered").Status == Status::Ok &&
                store->BeginDelivery("delivered", "delivery-confirmed").Status == Status::Ok &&
                store->CompleteDelivery("delivered", "delivery-confirmed", SuiteDeliveryOutcome::Delivered).Status == Status::Ok &&
                store->CompleteDelivery("delivered", "delivery-confirmed", SuiteDeliveryOutcome::Delivered).Replayed &&
                store->CompleteDelivery("delivered", "delivery-confirmed", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::InvalidState &&
                Balance(*store, subject) == 81, "delivered purchase mutated or refunded on replay");
        Require(store->ReservePurchase(request, "failed").Status == Status::Ok &&
                store->BeginDelivery("failed", "verified-failure").Status == Status::Ok, "failure setup failed");
        const auto refund = store->CompleteDelivery("failed", "verified-failure", SuiteDeliveryOutcome::VerifiedNoDelivery);
        Require(refund.Status == Status::Ok && refund.State == SuiteReceiptState::NoDelivery &&
                refund.RefundedBalance == 81 && Balance(*store, subject) == 81, "verified no-delivery did not refund");
        store->Credit(subject, 2, "post-refund");
        const auto refundReplay = store->CompleteDelivery("failed", "verified-failure", SuiteDeliveryOutcome::VerifiedNoDelivery);
        Require(refundReplay.Status == Status::Ok && refundReplay.Replayed && refundReplay.RefundedBalance == 81 &&
                Balance(*store, subject) == 83, "refund replay lost result/doubled credit");
    }

    void TestReceiptRollbackOverflowAndAttemptIdCollision()
    {
        Directory directory; auto store = Open(directory);
        const SuiteSubject subject{"offline", "source"};
        store->Credit(subject, 100, "seed");
        RawDatabase raw(directory.Database());
        raw.Exec("CREATE TRIGGER reject_receipt BEFORE INSERT ON fulfillment_receipts "
                 "WHEN NEW.receipt_id='failure' BEGIN SELECT RAISE(ABORT,'reject receipt'); END;");
        auto request = Purchase(subject, 25);
        Require(store->ReservePurchase(request, "failure").Status == Status::StorageError && Balance(*store, subject) == 100 &&
                store->Receipt("failure").Result.Status == Status::NotFound, "receipt insert failure did not roll back debit");
        raw.Exec("DROP TRIGGER reject_receipt;");
        Require(store->ReservePurchase(request, "failure").Status == Status::Ok &&
                store->BeginDelivery("failure", "unique-attempt").Status == Status::Ok, "reservation retry failed");
        Require(store->ReservePurchase(request, "another").Status == Status::Ok &&
                store->BeginDelivery("another", "unique-attempt").Status == Status::PayloadConflict &&
                store->Receipt("another").Result.State == SuiteReceiptState::Reserved,
                "attempt ID collision advanced receipt");
        raw.Exec("CREATE TRIGGER reject_finalize BEFORE UPDATE OF state ON fulfillment_receipts "
                 "WHEN NEW.receipt_id='failure' AND NEW.state=4 BEGIN SELECT RAISE(ABORT,'reject finalize'); END;");
        Require(store->CompleteDelivery("failure", "unique-attempt", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::StorageError &&
                Balance(*store, subject) == 50 && store->Receipt("failure").Result.State == SuiteReceiptState::Attempting,
                "receipt finalization failure committed wallet refund");
        raw.Exec("DROP TRIGGER reject_finalize;");
        Require(store->CompleteDelivery("failure", "unique-attempt", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::Ok &&
                Balance(*store, subject) == 75, "refund retry failed");
        request.Quantity = 2; request.UnitPrice = std::numeric_limits<int64_t>::max();
        Require(store->ReservePurchase(request, "overflow").Status == Status::Overflow &&
                store->Receipt("overflow").Result.Status == Status::NotFound, "price multiplication overflow accepted");
        request = Purchase(subject, 1);
        store->ReservePurchase(request, "refund-overflow"); store->BeginDelivery("refund-overflow", "overflow-attempt");
        store->Credit(subject, std::numeric_limits<int64_t>::max() - 74, "fill");
        Require(store->CompleteDelivery("refund-overflow", "overflow-attempt", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::Overflow &&
                store->Receipt("refund-overflow").Result.State == SuiteReceiptState::Attempting,
                "overflow refund changed terminal state");
        store->Debit(subject, 1, "make-room-refund");
        Require(store->CompleteDelivery("refund-overflow", "overflow-attempt", SuiteDeliveryOutcome::VerifiedNoDelivery).Status == Status::Ok,
                "overflow refund could not retry after room");
    }

    void TestKitsDurableLimitsCooldownsAndConcurrentReservations()
    {
        Directory directory; auto first = Open(directory); auto second = Open(directory);
        const SuiteSubject subject{"realm-A", "player"};
        auto kit = Purchase(subject, 0); kit.KitMaxClaims = 2; kit.KitCooldownSeconds = 10;
        Require(first->ReserveKit(kit, "kit-one").Status == Status::Ok &&
                first->ReserveKit(kit, "kit-too-soon").Status == Status::CooldownActive, "kit cooldown not enforced");
        kit.RequestedUtcSeconds = 110;
        Require(first->ReserveKit(kit, "kit-two").Status == Status::Ok, "kit cooldown boundary wrong");
        first->BeginDelivery("kit-two", "kit-attempt");
        first->CompleteDelivery("kit-two", "kit-attempt", SuiteDeliveryOutcome::Uncertain);
        kit.RequestedUtcSeconds = 120;
        Require(first->ReserveKit(kit, "kit-over-limit").Status == Status::LimitReached, "uncertain kit did not consume quota");
        first->BeginDelivery("kit-one", "kit-failure");
        first->CompleteDelivery("kit-one", "kit-failure", SuiteDeliveryOutcome::VerifiedNoDelivery);
        Require(first->ReserveKit(kit, "kit-retry").Status == Status::Ok, "verified failed kit kept quota");
        first.reset(); first = Open(directory);
        Require(first->ReserveKit(kit, "kit-again").Status == Status::LimitReached, "kit quota lost on reopen");
        kit.Subject.Namespace = "realm-B"; kit.ProductId = "one-claim"; kit.KitMaxClaims = 1; kit.KitCooldownSeconds = 0;
        std::atomic<int> committed{0}, denied{0};
        const auto reserve = [&](SuiteStore& store, const char* id) {
            const auto result = store.ReserveKit(kit, id);
            if (result.Status == Status::Ok) ++committed;
            if (result.Status == Status::LimitReached) ++denied;
        };
        std::thread one([&] { reserve(*first, "race-one"); });
        std::thread two([&] { reserve(*second, "race-two"); }); one.join(); two.join();
        Require(committed == 1 && denied == 1, "concurrent connections exceeded one-claim kit quota");
        kit.Subject.Namespace = "realm-C";
        Require(first->ReserveKit(kit, "isolated-kit").Status == Status::Ok, "kit namespaces collapsed");
        kit.UnitPrice = 1;
        Require(first->ReserveKit(kit, "paid-kit").Status == Status::InvalidArgument, "free kit admitted paid payload");
    }

    void TestConcurrentPurchaseReplayAdmitsOneDelivery()
    {
        Directory directory; auto first = Open(directory); auto second = Open(directory);
        const SuiteSubject subject{"offline", "same-purchase"};
        first->Credit(subject, 100, "seed");
        auto request = Purchase(subject, 30);
        std::atomic<int> reserved{0}, replayed{0}, admitted{0}, rejected{0};
        const auto reserve = [&](SuiteStore& store) {
            const auto result = store.ReservePurchase(request, "single-receipt");
            if (result.Status != Status::Ok) ++rejected;
            else if (result.Replayed) ++replayed; else ++reserved;
        };
        std::thread one([&] { reserve(*first); }); std::thread two([&] { reserve(*second); }); one.join(); two.join();
        Require(reserved == 1 && replayed == 1 && rejected == 0 && Balance(*first, subject) == 70,
                "concurrent receipt replay charged twice");
        replayed = 0;
        const auto begin = [&](SuiteStore& store) {
            const auto result = store.BeginDelivery("single-receipt", "single-attempt");
            if (result.Status != Status::Ok) ++rejected;
            else if (result.Replayed) ++replayed; else ++admitted;
        };
        std::thread beginOne([&] { begin(*first); }); std::thread beginTwo([&] { begin(*second); }); beginOne.join(); beginTwo.join();
        Require(admitted == 1 && replayed == 1 && rejected == 0,
                "concurrent begin admitted more than one delivery action");
    }

    void TestSchemaOneUpgradePreservesDataAndRollsBackFailure()
    {
        Directory directory;
        const SuiteSubject subject{"offline", "old-player"};
        { auto store = Open(directory); store->Credit(subject, 42, "old-credit");
          store->CreateRole("old-role"); store->PutPermission("old-role", "shop.read", Effect::Allow);
          store->PutMembership(subject, "old-role"); }
        { RawDatabase raw(directory.Database()); raw.Exec("DROP TABLE fulfillment_receipts; PRAGMA user_version=1;"); }
        { auto store = Open(directory); Require(Balance(*store, subject) == 42 &&
                store->CheckPermission(subject, "shop.read", 0).Allowed && store->Credit(subject, 42, "old-credit").Replayed,
                "schema one upgrade lost balances/ACL/idempotent journal"); }
        { RawDatabase raw(directory.Database()); Require(raw.Scalar("PRAGMA user_version") == 2,
                "schema two version not committed"); raw.Exec("DROP TABLE fulfillment_receipts; PRAGMA user_version=1; "
                "CREATE TABLE fulfillment_receipts(preserve INTEGER); INSERT INTO fulfillment_receipts VALUES(7);"); }
        Status status;
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::StorageError,
                "conflicting schema migration succeeded");
        RawDatabase raw(directory.Database());
        Require(raw.Scalar("PRAGMA user_version") == 1 && raw.Scalar("SELECT preserve FROM fulfillment_receipts") == 7 &&
                raw.Scalar("SELECT balance FROM wallets") == 42, "failed additive migration changed old data/version");
    }

    void TestPrivatePathsAndSymlinkRejection()
    {
        Directory directory;
        Status status;
        for (const char* instance : {"", "..", "../escape", "a/b", "."})
            Require(!SuiteStore::Open(directory.Root, instance, status) && status == Status::InvalidPath,
                    "unsafe instance path accepted");
        Require(!SuiteStore::Open("relative", "test", status) && status == Status::InvalidPath,
                "relative private root accepted");
        ::chmod(directory.Root.c_str(), 0755);
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::InvalidPath,
                "public root accepted");
        ::chmod(directory.Root.c_str(), 0700);
        fs::create_directory(directory.Root / "writable-parent");
        fs::create_directory(directory.Root / "writable-parent" / "private");
        ::chmod((directory.Root / "writable-parent").c_str(), 0777);
        ::chmod((directory.Root / "writable-parent" / "private").c_str(), 0700);
        Require(!SuiteStore::Open(directory.Root / "writable-parent" / "private", "test", status) &&
                status == Status::InvalidPath, "replaceable private root under writable ancestor accepted");
        fs::create_directory(directory.Root / "real");
        ::chmod((directory.Root / "real").c_str(), 0700);
        fs::create_directory_symlink(directory.Root / "real", directory.Root / "root-link");
        Require(!SuiteStore::Open(directory.Root / "root-link", "test", status) && status == Status::InvalidPath,
                "symlink root component accepted");
        fs::create_directory_symlink(directory.Root / "real", directory.Root / "instance-link");
        Require(!SuiteStore::Open(directory.Root, "instance-link", status) && status == Status::InvalidPath,
                "symlink instance accepted");
        fs::create_directory(directory.Root / "test");
        ::chmod((directory.Root / "test").c_str(), 0700);
        const auto protectedFile = directory.Root / "protected-file";
        { std::ofstream stream(protectedFile); stream << "unchanged"; }
        ::chmod(protectedFile.c_str(), 0600);
        fs::create_symlink(protectedFile, directory.Database());
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::InvalidPath,
                "symlink database accepted");
        fs::remove(directory.Database());
        fs::create_symlink(protectedFile, directory.Root / "test" / "suite.sqlite3-wal");
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::InvalidPath,
                "symlink sidecar accepted");
        fs::remove(directory.Root / "test" / "suite.sqlite3-wal");
        fs::create_hard_link(protectedFile, directory.Database());
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::InvalidPath,
                "hard-linked database accepted");
        fs::remove(directory.Database());
        { std::ifstream stream(protectedFile); std::string value; stream >> value; Require(value == "unchanged", "path rejection altered external file"); }
        auto store = Open(directory);
        struct stat info{};
        Require(::stat(directory.Database().c_str(), &info) == 0 && (info.st_mode & 0777) == 0600 &&
                ::stat((directory.Root / "test").c_str(), &info) == 0 && (info.st_mode & 0777) == 0700,
                "created data paths are not private");
        Require(store->Credit({"offline", "one"}, 1, "one").Status == Status::Ok, "private-path store unusable");
        store.reset();
        ::chmod(directory.Database().c_str(), 0644);
        Require(!SuiteStore::Open(directory.Root, "test", status) && status == Status::InvalidPath,
                "public database file accepted");
        ::chmod(directory.Database().c_str(), 0600);
        store = Open(directory);
        auto isolated = Open(directory, "second-instance");
        Require(Balance(*isolated, {"offline", "one"}) == 0, "instances shared mutable wallets");
    }
}

int main()
{
    try
    {
        TestPermissionsDenyExpiryAndNamespaces();
        TestPreparedTextAndValidation();
        TestWalletAtomicityIdempotenceAndConflicts();
        TestOverflowAndMaximumIntegralUnits();
        TestRollbackAfterPartialDatabaseWrites();
        TestReopenPersistenceAndMigrationGuard();
        TestForeignSchemaIsNotOverwritten();
        TestTwoConnectionsSerializeWritersAndDuplicateIds();
        TestBusyFailureRollsBackAndCanRetry();
        TestPrivatePathsAndSymlinkRejection();
        TestReceiptReservationDeliveryAndUncertainty();
        TestReceiptRollbackOverflowAndAttemptIdCollision();
        TestKitsDurableLimitsCooldownsAndConcurrentReservations();
        TestSchemaOneUpgradePreservesDataAndRollsBackFailure();
        TestConcurrentPurchaseReplayAdmitsOneDelivery();
        std::cout << "SuiteStore tests passed\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
