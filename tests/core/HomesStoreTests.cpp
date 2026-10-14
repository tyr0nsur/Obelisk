#include "services/HomesStore.h"
#include <sqlite3.h>
#include <atomic>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>

namespace
{
    using namespace Obelisk::Services;
    using Status = HomesStatus;
    namespace fs = std::filesystem;
    void Require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
    struct Directory
    {
        fs::path Root;
        Directory() { char name[] = "/tmp/obelisk-homes.XXXXXX"; auto* path = mkdtemp(name); Require(path, "mkdtemp failed"); Root = path; }
        ~Directory() { std::error_code error; fs::remove_all(Root, error); }
    };
    auto Open(const Directory& directory, std::string_view instance = "test")
    {
        Status status; auto result = HomesStore::Open(directory.Root, instance, status);
        Require(result && status == Status::Ok, "homes open failed"); return result;
    }
    const HomesSubject kOwner{"authority-A", "玩家'🙂"};
    const HomePosition kPosition{100, 200, 300, 90};
    void PersistenceQuotaAndWorld()
    {
        Directory directory;
        {
            auto store = Open(directory);
            Require(store->Put(kOwner, "base", "TheIsland:save-A", kPosition, 100, 2) == Status::Ok &&
                store->Put(kOwner, "cave", "TheIsland:save-A", kPosition, 100, 2, 110) == Status::Ok &&
                store->Put(kOwner, "extra", "TheIsland:save-B", kPosition, 100, 2) == Status::QuotaExceeded,
                "quota failed across saves");
            Require(store->Get(kOwner, "base", "TheIsland:save-B", 100).Status == Status::WorldMismatch &&
                store->Get({"authority-B", kOwner.OpaqueId}, "base", "TheIsland:save-A", 100).Status == Status::NotFound,
                "save fingerprint or subject namespace collapsed");
            Require(store->Put(kOwner, "base", "TheIsland:save-A", {200, 300, 400, -90}, 101, 2) == Status::Ok,
                "quota blocked existing-home update");
            Require(store->Get(kOwner, "cave", "TheIsland:save-A", 110).Status == Status::Expired &&
                store->Put(kOwner, "extra", "TheIsland:save-B", kPosition, 110, 2) == Status::Ok,
                "expiry boundary did not release quota");
        }
        auto reopened = Open(directory); const auto home = reopened->Get(kOwner, "base", "TheIsland:save-A", 110);
        Require(home.Status == Status::Ok && home.Home.Position.X == 200 && home.Home.Revision == 2 &&
            reopened->List(kOwner, 110).Homes.size() == 2, "reopen lost copied location/revision/active list");
        Require(reopened->Remove(kOwner, "base") == Status::Ok && reopened->Remove(kOwner, "base") == Status::NotFound,
            "home deletion failed");
        struct stat info{}; Require(stat((directory.Root / "test/homes.sqlite3").c_str(), &info) == 0 &&
            (info.st_mode & 0777) == 0600, "private database mode wrong");
    }
    void TravelReservationAndCooldown()
    {
        Directory directory; auto store = Open(directory);
        Require(store->Put(kOwner, "base", "world", kPosition, 100, 2) == Status::Ok, "home failed");
        const auto first = store->ReserveTravel(kOwner, "base", "world", 100, 30, 10, "travel-1");
        Require(first.Status == Status::Ok && first.LeaseUntilUtcSeconds == 110 &&
            store->ReserveTravel(kOwner, "base", "world", 101, 30, 10, "travel-1").Replayed &&
            store->ReserveTravel(kOwner, "base", "world", 101, 31, 10, "travel-1").Status == Status::PayloadConflict &&
            store->ReserveTravel(kOwner, "base", "world", 101, 30, 10, "travel-2").Status == Status::ReservationPending,
            "reservation idempotency or single-pending gate failed");
        Require(store->FinishTravel(kOwner, "travel-1", false, 101).Status == Status::Ok &&
            store->FinishTravel(kOwner, "travel-1", false, 102).Replayed &&
            store->FinishTravel(kOwner, "travel-1", true, 102).Status == Status::PayloadConflict,
            "failed travel outcome rewrite or cooldown spent");
        Require(store->ReserveTravel(kOwner, "base", "world", 102, 30, 10, "travel-2").Status == Status::Ok &&
            store->FinishTravel(kOwner, "travel-2", true, 105).NextAllowedUtcSeconds == 135 &&
            store->ReserveTravel(kOwner, "base", "world", 134, 30, 10, "travel-3").Status == Status::Cooldown &&
            store->ReserveTravel(kOwner, "base", "world", 135, 30, 10, "travel-3").Status == Status::Ok,
            "cooldown did not start after success or boundary wrong");
        Require(store->FinishTravel(kOwner, "travel-3", true, 145).Status == Status::ReservationExpired &&
            store->ReserveTravel(kOwner, "base", "world", 145, 30, 10, "travel-3").Status == Status::ReservationExpired &&
            store->ReserveTravel(kOwner, "base", "world", 145, 30, 10, "travel-4").Status == Status::Ok,
            "lease retry extended expired operation or dead reservation blocked forever");
        store.reset(); auto reopened = Open(directory);
        Require(reopened->ReserveTravel(kOwner, "base", "world", 146, 30, 10, "travel-4").Replayed &&
            reopened->FinishTravel(kOwner, "travel-4", true, 149).Status == Status::Ok,
            "reopen lost operation/reservation");
    }
    void ConcurrentQuotaAndReservation()
    {
        Directory directory; auto first = Open(directory), second = Open(directory);
        std::atomic<int> created{0};
        std::thread a([&] { if (first->Put(kOwner, "one", "world", kPosition, 0, 1) == Status::Ok) ++created; });
        std::thread b([&] { if (second->Put(kOwner, "two", "world", kPosition, 0, 1) == Status::Ok) ++created; });
        a.join(); b.join(); Require(created == 1 && first->List(kOwner, 0).Homes.size() == 1, "cross-connection quota race");
        const auto name = first->List(kOwner, 0).Homes.front().Name;
        std::atomic<int> reserved{0};
        std::thread c([&] { if (first->ReserveTravel(kOwner, name, "world", 1, 10, 10, "one").Status == Status::Ok) ++reserved; });
        std::thread d([&] { if (second->ReserveTravel(kOwner, name, "world", 1, 10, 10, "two").Status == Status::Ok) ++reserved; });
        c.join(); d.join(); Require(reserved == 1, "cross-connection double reservation");
    }
    void ValidationAndPaths()
    {
        Directory directory; auto store = Open(directory);
        auto bad = kPosition; bad.X = std::numeric_limits<double>::quiet_NaN();
        Require(store->Put(kOwner, "base", "world", bad, 0, 1) == Status::InvalidArgument &&
            store->Put(kOwner, "../bad", "world", kPosition, 0, 1) == Status::InvalidArgument &&
            store->Put(kOwner, "base", "world", kPosition, 0, 1, 0) == Status::InvalidArgument &&
            store->Put(kOwner, "base", std::string("x\0y", 3), kPosition, 0, 1) == Status::InvalidArgument,
            "invalid destination accepted");
        Require(store->Put(kOwner, "base", "world", kPosition, 0, 1) == Status::Ok &&
            store->ReserveTravel(kOwner, "base", "world", std::numeric_limits<int64_t>::max(), 10, 10, "overflow").Status == Status::InvalidArgument,
            "lease arithmetic overflow accepted");
        Status status; Require(!HomesStore::Open(directory.Root, "../bad", status) && status == Status::InvalidPath, "instance traversal accepted");
        fs::create_directory_symlink(directory.Root / "test", directory.Root / "linked");
        Require(!HomesStore::Open(directory.Root, "linked", status) && status == Status::InvalidPath, "instance symlink accepted");
        fs::create_directory(directory.Root / "other"); chmod((directory.Root / "other").c_str(), 0700);
        fs::create_symlink(directory.Root / "test/homes.sqlite3", directory.Root / "other/homes.sqlite3");
        Require(!HomesStore::Open(directory.Root, "other", status) && status == Status::InvalidPath, "database symlink accepted");
    }
    void RevisionRollbackAndFutureSchema()
    {
        Directory directory; auto store = Open(directory);
        Require(store->Put(kOwner, "base", "world", kPosition, 100, 2) == Status::Ok &&
            store->ReserveTravel(kOwner, "base", "world", 100, 20, 10, "revision").Status == Status::Ok &&
            store->ResolveTravel(kOwner, "revision", "world", 101).Status == Status::Ok &&
            store->Put(kOwner, "base", "world", {200, 200, 300, 90}, 101, 2) == Status::Ok &&
            store->ResolveTravel(kOwner, "revision", "world", 102).Status == Status::PayloadConflict &&
            store->ReserveTravel(kOwner, "base", "world", 102, 20, 10, "revision").Status == Status::PayloadConflict &&
            store->FinishTravel(kOwner, "revision", false, 102).Status == Status::Ok,
            "reserved destination ignored edited home revision or could not cancel");
        sqlite3* db = nullptr;
        Require(sqlite3_open((directory.Root / "test/homes.sqlite3").c_str(), &db) == SQLITE_OK, "raw fixture open failed");
        auto exec = [&](const char* sql) { Require(sqlite3_exec(db, sql, nullptr, nullptr, nullptr) == SQLITE_OK, "fixture SQL failed"); };
        exec("CREATE TRIGGER fail_reservation BEFORE INSERT ON travel_state BEGIN SELECT RAISE(ABORT,'fixture'); END;");
        Require(store->ReserveTravel(kOwner, "base", "world", 103, 20, 10, "rolled-back").Status == Status::StorageError,
            "reservation write failure hidden");
        exec("DROP TRIGGER fail_reservation;");
        Require(store->ReserveTravel(kOwner, "base", "world", 103, 20, 10, "rolled-back").Status == Status::Ok,
            "failed transaction consumed operation ID or retained pending state");
        sqlite3_close(db); store.reset();
        Require(sqlite3_open((directory.Root / "test/homes.sqlite3").c_str(), &db) == SQLITE_OK, "future fixture open failed");
        exec("PRAGMA user_version=2;"); sqlite3_close(db);
        Status status; Require(!HomesStore::Open(directory.Root, "test", status) && status == Status::UnsupportedSchema,
            "future schema silently downgraded");
    }
}
int main()
{
    try { PersistenceQuotaAndWorld(); TravelReservationAndCooldown(); ConcurrentQuotaAndReservation(); ValidationAndPaths(); RevisionRollbackAndFutureSchema(); }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
    return 0;
}
