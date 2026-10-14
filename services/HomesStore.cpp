#include "HomesStore.h"
#include <sqlite3.h>
#include <array>
#include <cerrno>
#include <cmath>
#include <limits>
#include <mutex>
#include <utility>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace Obelisk::Services
{
    namespace
    {
        using Status = HomesStatus;
        constexpr int kApplicationId = 0x4f424e48;
        Status SqlStatus(int result) noexcept
        {
            if (result == SQLITE_OK || result == SQLITE_DONE || result == SQLITE_ROW) return Status::Ok;
            if ((result & 0xff) == SQLITE_BUSY || (result & 0xff) == SQLITE_LOCKED) return Status::Busy;
            return Status::StorageError;
        }

        bool ValidUtf8(std::string_view text, size_t maximum) noexcept
        {
            if (text.empty() || text.size() > maximum || !text.data()) return false;
            for (size_t i = 0; i < text.size();)
            {
                const auto first = static_cast<unsigned char>(text[i++]);
                if (first == 0) return false;
                if (first < 0x80) continue;
                uint32_t scalar = 0, minimum = 0;
                size_t remaining = 0;
                if (first >= 0xc2 && first <= 0xdf) { scalar = first & 0x1f; remaining = 1; minimum = 0x80; }
                else if (first >= 0xe0 && first <= 0xef) { scalar = first & 0x0f; remaining = 2; minimum = 0x800; }
                else if (first >= 0xf0 && first <= 0xf4) { scalar = first & 7; remaining = 3; minimum = 0x10000; }
                else return false;
                if (remaining > text.size() - i) return false;
                while (remaining--)
                {
                    const auto next = static_cast<unsigned char>(text[i++]);
                    if ((next & 0xc0) != 0x80) return false;
                    scalar = (scalar << 6) | (next & 0x3f);
                }
                if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff)) return false;
            }
            return true;
        }

        bool ValidToken(std::string_view token, size_t maximum, bool dotted) noexcept
        {
            if (token.empty() || token.size() > maximum) return false;
            for (unsigned char ch : token)
                if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                      (ch >= '0' && ch <= '9') || ch == '_' || ch == '-' || (dotted && (ch == '.' || ch == ':'))))
                    return false;
            return true;
        }

        bool ValidSubject(const HomesSubject& subject) noexcept
        {
            return ValidToken(subject.Namespace, 64, true) && ValidUtf8(subject.OpaqueId, 256);
        }

        class FileDescriptor
        {
        public:
            explicit FileDescriptor(int value = -1) noexcept : Value(value) {}
            ~FileDescriptor() { if (Value >= 0) ::close(Value); }
            FileDescriptor(const FileDescriptor&) = delete;
            FileDescriptor& operator=(const FileDescriptor&) = delete;
            void Reset(int value) noexcept { if (Value >= 0) ::close(Value); Value = value; }
            int Value;
        };

        bool TrustedAncestor(int fd) noexcept
        {
            struct stat info{};
            if (fd < 0 || ::fstat(fd, &info) != 0 || !S_ISDIR(info.st_mode) ||
                (info.st_uid != ::geteuid() && info.st_uid != 0)) return false;
            // Sticky /tmp permits creation while protecting another UID's
            // entries. A writable non-sticky ancestor permits root replacement.
            return (info.st_mode & 0022) == 0 || (info.st_mode & S_ISVTX) != 0;
        }

        struct PathIdentity
        {
            struct stat Root{}, Instance{}, Database{};
        };

        bool SameInode(const struct stat& first, const struct stat& second) noexcept
        { return first.st_dev == second.st_dev && first.st_ino == second.st_ino; }

        bool PrivateDirectory(int fd) noexcept
        {
            struct stat info{};
            return fd >= 0 && ::fstat(fd, &info) == 0 && S_ISDIR(info.st_mode) &&
                (info.st_uid == ::geteuid() || info.st_uid == 0) && (info.st_mode & 0777) == 0700;
        }

        bool PrivateFile(const struct stat& info) noexcept
        {
            return S_ISREG(info.st_mode) && (info.st_uid == ::geteuid() || info.st_uid == 0) &&
                (info.st_mode & 0777) == 0600 && info.st_nlink == 1;
        }

        bool PreparePath(const std::filesystem::path& root, std::string_view instance, std::string& path, PathIdentity& identity)
        {
            if (!root.is_absolute() || root.native().size() > 4000 ||
                root.native().find('\0') != std::string::npos || !ValidToken(instance, 64, false)) return false;
            FileDescriptor directory(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
            if (!TrustedAncestor(directory.Value)) return false;
            for (const auto& part : root.relative_path())
            {
                const auto component = part.native();
                if (component == "." || component == "..") return false;
                if (component.empty()) continue;
                const int next = ::openat(directory.Value, component.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
                if (next < 0) return false;
                directory.Reset(next);
                if (!TrustedAncestor(directory.Value)) return false;
            }
            if (!PrivateDirectory(directory.Value) || ::fstat(directory.Value, &identity.Root) != 0) return false;
            const std::string instanceName(instance);
            if (::mkdirat(directory.Value, instanceName.c_str(), 0700) != 0 && errno != EEXIST) return false;
            FileDescriptor instanceDirectory(::openat(directory.Value, instanceName.c_str(),
                O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
            if (!PrivateDirectory(instanceDirectory.Value) || ::fstat(instanceDirectory.Value, &identity.Instance) != 0) return false;
            constexpr std::array filenames{"homes.sqlite3", "homes.sqlite3-wal", "homes.sqlite3-shm", "homes.sqlite3-journal"};
            for (const auto* filename : filenames)
            {
                struct stat info{};
                if (::fstatat(instanceDirectory.Value, filename, &info, AT_SYMLINK_NOFOLLOW) == 0)
                {
                    if (!PrivateFile(info)) return false;
                }
                else if (errno != ENOENT) return false;
            }
            FileDescriptor database(::openat(instanceDirectory.Value, "homes.sqlite3",
                O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600));
            struct stat info{};
            if (database.Value < 0 || ::fstat(database.Value, &info) != 0 || !PrivateFile(info)) return false;
            identity.Database = info;
            path = (root / instanceName / "homes.sqlite3").string();
            return true;
        }

        bool VerifyPathIdentity(const std::filesystem::path& root, std::string_view instance, const PathIdentity& identity)
        {
            FileDescriptor directory(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
            if (!TrustedAncestor(directory.Value)) return false;
            for (const auto& part : root.relative_path())
            {
                const auto component = part.native();
                if (component.empty()) continue;
                const int next = ::openat(directory.Value, component.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
                if (next < 0) return false;
                directory.Reset(next);
                if (!TrustedAncestor(directory.Value)) return false;
            }
            struct stat info{};
            if (!PrivateDirectory(directory.Value) || ::fstat(directory.Value, &info) != 0 || !SameInode(info, identity.Root)) return false;
            const std::string instanceName(instance);
            FileDescriptor instanceDirectory(::openat(directory.Value, instanceName.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
            if (!PrivateDirectory(instanceDirectory.Value) || ::fstat(instanceDirectory.Value, &info) != 0 || !SameInode(info, identity.Instance)) return false;
            return ::fstatat(instanceDirectory.Value, "homes.sqlite3", &info, AT_SYMLINK_NOFOLLOW) == 0 &&
                PrivateFile(info) && SameInode(info, identity.Database);
        }

        class Statement
        {
        public:
            Statement(sqlite3* db, const char* sql) noexcept
                : Result(sqlite3_prepare_v2(db, sql, -1, &Value, nullptr)) {}
            ~Statement() { if (Value) sqlite3_finalize(Value); }
            Statement(const Statement&) = delete;
            Statement& operator=(const Statement&) = delete;
            bool Text(int index, std::string_view text) noexcept
            {
                if (Result == SQLITE_OK) Result = sqlite3_bind_text(Value, index, text.data(), static_cast<int>(text.size()), SQLITE_TRANSIENT);
                return Result == SQLITE_OK;
            }
            bool Integer(int index, int64_t value) noexcept
            {
                if (Result == SQLITE_OK) Result = sqlite3_bind_int64(Value, index, value);
                return Result == SQLITE_OK;
            }
            bool Floating(int index, double value) noexcept
            {
                if (Result == SQLITE_OK) Result = sqlite3_bind_double(Value, index, value);
                return Result == SQLITE_OK;
            }
            bool Null(int index) noexcept
            {
                if (Result == SQLITE_OK) Result = sqlite3_bind_null(Value, index);
                return Result == SQLITE_OK;
            }
            int Step() noexcept { return Result == SQLITE_OK ? sqlite3_step(Value) : Result; }
            std::string_view ColumnText(int index) const noexcept
            {
                const auto* value = sqlite3_column_text(Value, index);
                return value ? std::string_view(reinterpret_cast<const char*>(value), sqlite3_column_bytes(Value, index)) : std::string_view{};
            }
            sqlite3_stmt* Value = nullptr;
            int Result;
        };

        class Transaction
        {
        public:
            explicit Transaction(sqlite3* db) noexcept : Db(db), Result(sqlite3_exec(db, "BEGIN IMMEDIATE", nullptr, nullptr, nullptr)) {}
            ~Transaction() { if (Result == SQLITE_OK && !Finished) sqlite3_exec(Db, "ROLLBACK", nullptr, nullptr, nullptr); }
            Status Commit() noexcept
            {
                const int result = sqlite3_exec(Db, "COMMIT", nullptr, nullptr, nullptr);
                if (result == SQLITE_OK) Finished = true;
                return SqlStatus(result);
            }
            sqlite3* Db;
            int Result;
            bool Finished = false;
        };

        bool Name(std::string_view name) noexcept
        {
            if (name.empty() || name.size() > 32) return false;
            for (unsigned char ch : name)
                if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-')) return false;
            return true;
        }
        bool Position(const HomePosition& value) noexcept
        {
            return std::isfinite(value.X) && std::isfinite(value.Y) && std::isfinite(value.Z) && std::isfinite(value.Yaw) &&
                std::abs(value.X) <= HomesStore::MaximumCoordinateMagnitude &&
                std::abs(value.Y) <= HomesStore::MaximumCoordinateMagnitude &&
                std::abs(value.Z) <= HomesStore::MaximumCoordinateMagnitude && value.Yaw >= -180 && value.Yaw <= 180;
        }
        bool Clock(int64_t now) noexcept { return now >= 0; }
        bool AddTime(int64_t now, int64_t delta) noexcept
        { return Clock(now) && delta >= 0 && delta <= std::numeric_limits<int64_t>::max() - now; }
        Status Pragmas(sqlite3* db) noexcept
        {
            Transaction transaction(db);
            if (transaction.Result != SQLITE_OK) return SqlStatus(transaction.Result);
            Statement version(db, "PRAGMA user_version"), application(db, "PRAGMA application_id");
            if (version.Step() != SQLITE_ROW || application.Step() != SQLITE_ROW) return Status::StorageError;
            const auto number = sqlite3_column_int(version.Value, 0), app = sqlite3_column_int(application.Value, 0);
            if (number < 0 || number > HomesStore::SchemaVersion ||
                (number == 0 ? app != 0 : app != kApplicationId)) return Status::UnsupportedSchema;
            if (number == 0)
            {
                Statement objects(db, "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'");
                if (objects.Step() != SQLITE_ROW || sqlite3_column_int64(objects.Value, 0)) return Status::UnsupportedSchema;
                const char* schema = R"sql(
CREATE TABLE homes(
 subject_namespace TEXT NOT NULL COLLATE BINARY, opaque_id TEXT NOT NULL COLLATE BINARY,
 name TEXT NOT NULL COLLATE BINARY, world TEXT NOT NULL COLLATE BINARY,
 x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL, yaw REAL NOT NULL,
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>0),
 updated INTEGER NOT NULL CHECK(typeof(updated)='integer' AND updated>=0),
 expires INTEGER CHECK(expires IS NULL OR (typeof(expires)='integer' AND expires>=0)),
 PRIMARY KEY(subject_namespace,opaque_id,name));
CREATE TABLE travel_state(
 subject_namespace TEXT NOT NULL COLLATE BINARY, opaque_id TEXT NOT NULL COLLATE BINARY,
 next_allowed INTEGER NOT NULL CHECK(typeof(next_allowed)='integer' AND next_allowed>=0),
 pending TEXT COLLATE BINARY, pending_until INTEGER,
 PRIMARY KEY(subject_namespace,opaque_id),
 CHECK((pending IS NULL AND pending_until IS NULL) OR
       (pending IS NOT NULL AND typeof(pending_until)='integer' AND pending_until>=0)));
CREATE TABLE travel_operations(
 operation TEXT NOT NULL COLLATE BINARY PRIMARY KEY,
 subject_namespace TEXT NOT NULL COLLATE BINARY, opaque_id TEXT NOT NULL COLLATE BINARY,
 name TEXT NOT NULL COLLATE BINARY, world TEXT NOT NULL COLLATE BINARY,
 x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL, yaw REAL NOT NULL,
 revision INTEGER NOT NULL, updated INTEGER NOT NULL, expires INTEGER,
 cooldown INTEGER NOT NULL CHECK(typeof(cooldown)='integer' AND cooldown>=0),
 lease_seconds INTEGER NOT NULL CHECK(typeof(lease_seconds)='integer' AND lease_seconds>0),
 reserved INTEGER NOT NULL CHECK(typeof(reserved)='integer' AND reserved>=0),
 lease_until INTEGER NOT NULL CHECK(typeof(lease_until)='integer' AND lease_until>=reserved),
 outcome INTEGER CHECK(outcome IS NULL OR outcome IN(0,1)), finished INTEGER, next_allowed INTEGER);
PRAGMA application_id=0x4f424e48;
PRAGMA user_version=1;
)sql";
                const int result = sqlite3_exec(db, schema, nullptr, nullptr, nullptr);
                if (result != SQLITE_OK) return SqlStatus(result);
            }
            constexpr std::array checks{
                "SELECT subject_namespace,opaque_id,name,world,x,y,z,yaw,revision,updated,expires FROM homes LIMIT 0",
                "SELECT subject_namespace,opaque_id,next_allowed,pending,pending_until FROM travel_state LIMIT 0",
                "SELECT operation,subject_namespace,opaque_id,name,world,x,y,z,yaw,revision,updated,expires,cooldown,lease_seconds,reserved,lease_until,outcome,finished,next_allowed FROM travel_operations LIMIT 0"};
            for (const auto* sql : checks) { Statement check(db, sql); if (check.Step() != SQLITE_DONE) return Status::UnsupportedSchema; }
            return transaction.Commit();
        }
        HomeRecord ReadHome(Statement& query, int column)
        {
            HomeRecord value;
            value.Name = query.ColumnText(column++); value.WorldFingerprint = query.ColumnText(column++);
            value.Position.X = sqlite3_column_double(query.Value, column++);
            value.Position.Y = sqlite3_column_double(query.Value, column++);
            value.Position.Z = sqlite3_column_double(query.Value, column++);
            value.Position.Yaw = sqlite3_column_double(query.Value, column++);
            value.Revision = sqlite3_column_int64(query.Value, column++);
            value.UpdatedUtcSeconds = sqlite3_column_int64(query.Value, column++);
            if (sqlite3_column_type(query.Value, column) != SQLITE_NULL) value.ExpiresUtcSeconds = sqlite3_column_int64(query.Value, column);
            return value;
        }
        bool ValidHome(const HomeRecord& home) noexcept
        {
            return Name(home.Name) && ValidUtf8(home.WorldFingerprint, 256) && Position(home.Position) &&
                home.Revision > 0 && Clock(home.UpdatedUtcSeconds) &&
                (!home.ExpiresUtcSeconds || *home.ExpiresUtcSeconds >= home.UpdatedUtcSeconds);
        }
        Status ReadHome(sqlite3* db, const HomesSubject& subject, std::string_view name, HomeRecord& home)
        {
            Statement query(db, "SELECT name,world,x,y,z,yaw,revision,updated,expires FROM homes WHERE subject_namespace=?1 AND opaque_id=?2 AND name=?3");
            query.Text(1, subject.Namespace); query.Text(2, subject.OpaqueId); query.Text(3, name);
            const int result = query.Step();
            if (result == SQLITE_DONE) return Status::NotFound;
            if (result != SQLITE_ROW) return SqlStatus(result);
            home = ReadHome(query, 0); return ValidHome(home) ? Status::Ok : Status::StorageError;
        }
        struct Travel
        {
            HomesSubject Subject;
            HomeRecord Home;
            int64_t Cooldown = 0, LeaseSeconds = 0, Reserved = 0, LeaseUntil = 0, NextAllowed = 0;
            std::optional<bool> Outcome;
        };
        Status ReadTravel(sqlite3* db, std::string_view operation, Travel& travel)
        {
            Statement query(db, "SELECT subject_namespace,opaque_id,name,world,x,y,z,yaw,revision,updated,expires,cooldown,lease_seconds,reserved,lease_until,outcome,next_allowed FROM travel_operations WHERE operation=?1");
            query.Text(1, operation); const int result = query.Step();
            if (result == SQLITE_DONE) return Status::NotFound;
            if (result != SQLITE_ROW) return SqlStatus(result);
            travel.Subject = {std::string(query.ColumnText(0)), std::string(query.ColumnText(1))};
            travel.Home = ReadHome(query, 2); travel.Cooldown = sqlite3_column_int64(query.Value, 11);
            travel.LeaseSeconds = sqlite3_column_int64(query.Value, 12); travel.Reserved = sqlite3_column_int64(query.Value, 13);
            travel.LeaseUntil = sqlite3_column_int64(query.Value, 14);
            if (sqlite3_column_type(query.Value, 15) != SQLITE_NULL) travel.Outcome = sqlite3_column_int(query.Value, 15) != 0;
            travel.NextAllowed = sqlite3_column_type(query.Value, 16) == SQLITE_NULL ? 0 : sqlite3_column_int64(query.Value, 16);
            return ValidSubject(travel.Subject) && ValidHome(travel.Home) && travel.Cooldown >= 0 &&
                travel.LeaseSeconds > 0 && travel.Reserved >= 0 && travel.LeaseUntil >= travel.Reserved ? Status::Ok : Status::StorageError;
        }
        HomeTravelResult Result(const Travel& travel, Status status, bool replayed = false)
        {
            HomeTravelResult result; result.Status = status; result.Home = travel.Home;
            result.Replayed = replayed; result.LeaseUntilUtcSeconds = travel.LeaseUntil; result.NextAllowedUtcSeconds = travel.NextAllowed;
            return result;
        }
        Status ValidateReservedHome(sqlite3* db, const Travel& travel, int64_t now)
        {
            HomeRecord current; const auto status = ReadHome(db, travel.Subject, travel.Home.Name, current);
            if (status != Status::Ok) return status;
            if (current.WorldFingerprint != travel.Home.WorldFingerprint) return Status::WorldMismatch;
            if (current.Revision != travel.Home.Revision) return Status::PayloadConflict;
            if (current.ExpiresUtcSeconds && *current.ExpiresUtcSeconds <= now) return Status::Expired;
            return now < current.UpdatedUtcSeconds ? Status::InvalidArgument : Status::Ok;
        }
    }
    struct HomesStore::Impl
    {
        sqlite3* Db = nullptr;
        std::mutex Mutex;
        ~Impl() { if (Db) sqlite3_close_v2(Db); }
    };
    HomesStore::HomesStore(std::unique_ptr<Impl> impl) noexcept : m_Impl(std::move(impl)) {}
    HomesStore::~HomesStore() noexcept = default;
    std::unique_ptr<HomesStore> HomesStore::Open(const std::filesystem::path& root, std::string_view instance, Status& status) noexcept
    {
        status = Status::StorageError;
        try
        {
            std::string path; PathIdentity identity;
            if (!PreparePath(root, instance, path, identity)) { status = Status::InvalidPath; return {}; }
            auto impl = std::make_unique<Impl>();
            const int opened = sqlite3_open_v2(path.c_str(), &impl->Db,
                SQLITE_OPEN_READWRITE | SQLITE_OPEN_FULLMUTEX | SQLITE_OPEN_PRIVATECACHE | SQLITE_OPEN_NOFOLLOW, nullptr);
            if (opened != SQLITE_OK) { status = SqlStatus(opened); return {}; }
            if (!VerifyPathIdentity(root, instance, identity)) { status = Status::InvalidPath; return {}; }
            if (sqlite3_busy_timeout(impl->Db, 2000) != SQLITE_OK) return {};
            status = Pragmas(impl->Db); if (status != Status::Ok) return {};
            if (sqlite3_exec(impl->Db, "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL", nullptr, nullptr, nullptr) != SQLITE_OK)
            { status = Status::StorageError; return {}; }
            return std::unique_ptr<HomesStore>(new HomesStore(std::move(impl)));
        }
        catch (...) { status = Status::StorageError; return {}; }
    }
    HomesStatus HomesStore::Put(const HomesSubject& subject, std::string_view name, std::string_view world,
        HomePosition position, int64_t now, uint32_t quota, std::optional<int64_t> expires) noexcept
    {
        if (!ValidSubject(subject) || !Name(name) || !ValidUtf8(world, 256) || !Position(position) || !Clock(now) ||
            !quota || quota > 1000 || (expires && *expires <= now)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex); auto* db = m_Impl->Db;
            Transaction transaction(db); if (transaction.Result != SQLITE_OK) return SqlStatus(transaction.Result);
            HomeRecord existing; const auto read = ReadHome(db, subject, name, existing);
            if (read != Status::Ok && read != Status::NotFound) return read;
            if (read == Status::Ok && existing.Revision == std::numeric_limits<int64_t>::max()) return Status::StorageError;
            if (read == Status::Ok && now < existing.UpdatedUtcSeconds) return Status::InvalidArgument;
            if (read == Status::NotFound || (existing.ExpiresUtcSeconds && *existing.ExpiresUtcSeconds <= now))
            {
                Statement count(db, "SELECT count(*) FROM homes WHERE subject_namespace=?1 AND opaque_id=?2 AND (expires IS NULL OR expires>?3)");
                count.Text(1, subject.Namespace); count.Text(2, subject.OpaqueId); count.Integer(3, now);
                const int counted = count.Step();
                if (counted != SQLITE_ROW) return SqlStatus(counted) == Status::Ok ? Status::StorageError : SqlStatus(counted);
                if (sqlite3_column_int64(count.Value, 0) >= quota) return Status::QuotaExceeded;
            }
            Statement insert(db, "INSERT INTO homes(subject_namespace,opaque_id,name,world,x,y,z,yaw,revision,updated,expires) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11) ON CONFLICT(subject_namespace,opaque_id,name) DO UPDATE SET world=excluded.world,x=excluded.x,y=excluded.y,z=excluded.z,yaw=excluded.yaw,revision=excluded.revision,updated=excluded.updated,expires=excluded.expires");
            insert.Text(1, subject.Namespace); insert.Text(2, subject.OpaqueId); insert.Text(3, name); insert.Text(4, world);
            insert.Floating(5, position.X); insert.Floating(6, position.Y);
            insert.Floating(7, position.Z); insert.Floating(8, position.Yaw);
            insert.Integer(9, read == Status::Ok ? existing.Revision + 1 : 1); insert.Integer(10, now);
            if (expires) insert.Integer(11, *expires); else insert.Null(11);
            const auto status = SqlStatus(insert.Step()); if (status != Status::Ok) return status;
            return transaction.Commit();
        }
        catch (...) { return Status::StorageError; }
    }
    HomeResult HomesStore::Get(const HomesSubject& subject, std::string_view name, std::string_view world, int64_t now) noexcept
    {
        HomeResult result;
        if (!ValidSubject(subject) || !Name(name) || !ValidUtf8(world, 256) || !Clock(now))
        { result.Status = Status::InvalidArgument; return result; }
        try
        {
            std::lock_guard lock(m_Impl->Mutex); result.Status = ReadHome(m_Impl->Db, subject, name, result.Home);
            if (result.Status == Status::Ok && result.Home.ExpiresUtcSeconds && *result.Home.ExpiresUtcSeconds <= now) result.Status = Status::Expired;
            if (result.Status == Status::Ok && result.Home.WorldFingerprint != world) result.Status = Status::WorldMismatch;
        }
        catch (...) { result.Status = Status::StorageError; }
        return result;
    }
    HomesListResult HomesStore::List(const HomesSubject& subject, int64_t now) noexcept
    {
        HomesListResult result;
        if (!ValidSubject(subject) || !Clock(now)) { result.Status = Status::InvalidArgument; return result; }
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement query(m_Impl->Db, "SELECT name,world,x,y,z,yaw,revision,updated,expires FROM homes WHERE subject_namespace=?1 AND opaque_id=?2 AND (expires IS NULL OR expires>?3) ORDER BY name COLLATE BINARY");
            query.Text(1, subject.Namespace); query.Text(2, subject.OpaqueId); query.Integer(3, now);
            int step;
            while ((step = query.Step()) == SQLITE_ROW)
            {
                auto home = ReadHome(query, 0); if (!ValidHome(home)) { result.Status = Status::StorageError; result.Homes.clear(); return result; }
                result.Homes.push_back(std::move(home));
            }
            result.Status = SqlStatus(step); if (result.Status != Status::Ok) result.Homes.clear();
        }
        catch (...) { result.Status = Status::StorageError; result.Homes.clear(); }
        return result;
    }
    HomesStatus HomesStore::Remove(const HomesSubject& subject, std::string_view name) noexcept
    {
        if (!ValidSubject(subject) || !Name(name)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement remove(m_Impl->Db, "DELETE FROM homes WHERE subject_namespace=?1 AND opaque_id=?2 AND name=?3");
            remove.Text(1, subject.Namespace); remove.Text(2, subject.OpaqueId); remove.Text(3, name);
            const auto status = SqlStatus(remove.Step());
            return status == Status::Ok && !sqlite3_changes(m_Impl->Db) ? Status::NotFound : status;
        }
        catch (...) { return Status::StorageError; }
    }
    HomeTravelResult HomesStore::ReserveTravel(const HomesSubject& subject, std::string_view name,
        std::string_view world, int64_t now, int64_t cooldown, int64_t lease, std::string_view operation) noexcept
    {
        HomeTravelResult result;
        if (!ValidSubject(subject) || !Name(name) || !ValidUtf8(world, 256) || !Clock(now) ||
            cooldown < 0 || cooldown > 86400 || lease < 1 || lease > 300 || !AddTime(now, lease) ||
            !ValidToken(operation, 128, true)) { result.Status = Status::InvalidArgument; return result; }
        try
        {
            std::lock_guard lock(m_Impl->Mutex); auto* db = m_Impl->Db;
            Transaction transaction(db); if (transaction.Result != SQLITE_OK) { result.Status = SqlStatus(transaction.Result); return result; }
            Travel previous; const auto previousStatus = ReadTravel(db, operation, previous);
            if (previousStatus == Status::Ok)
            {
                if (previous.Subject.Namespace != subject.Namespace || previous.Subject.OpaqueId != subject.OpaqueId ||
                    previous.Home.Name != name || previous.Home.WorldFingerprint != world ||
                    previous.Cooldown != cooldown || previous.LeaseSeconds != lease) return Result(previous, Status::PayloadConflict);
                if (now < previous.Reserved) return Result(previous, Status::InvalidArgument);
                if (previous.Outcome) return Result(previous, Status::AlreadyCompleted, true);
                return Result(previous, now >= previous.LeaseUntil ? Status::ReservationExpired : ValidateReservedHome(db, previous, now), true);
            }
            if (previousStatus != Status::NotFound) { result.Status = previousStatus; return result; }
            Travel travel; travel.Subject = subject;
            result.Status = ReadHome(db, subject, name, travel.Home); if (result.Status != Status::Ok) return result;
            if (travel.Home.ExpiresUtcSeconds && *travel.Home.ExpiresUtcSeconds <= now) return Result(travel, Status::Expired);
            if (travel.Home.WorldFingerprint != world) return Result(travel, Status::WorldMismatch);
            if (now < travel.Home.UpdatedUtcSeconds) return Result(travel, Status::InvalidArgument);
            Statement state(db, "SELECT next_allowed,pending,pending_until FROM travel_state WHERE subject_namespace=?1 AND opaque_id=?2");
            state.Text(1, subject.Namespace); state.Text(2, subject.OpaqueId); const int stateResult = state.Step();
            if (stateResult == SQLITE_ROW)
            {
                travel.NextAllowed = sqlite3_column_int64(state.Value, 0);
                if (travel.NextAllowed < 0) return Result(travel, Status::StorageError);
                if (travel.NextAllowed > now) return Result(travel, Status::Cooldown);
                if (sqlite3_column_type(state.Value, 1) != SQLITE_NULL && sqlite3_column_int64(state.Value, 2) > now)
                    return Result(travel, Status::ReservationPending);
            }
            else if (stateResult != SQLITE_DONE) return Result(travel, SqlStatus(stateResult));
            travel.Cooldown = cooldown; travel.LeaseSeconds = lease; travel.Reserved = now; travel.LeaseUntil = now + lease;
            Statement insert(db, "INSERT INTO travel_operations(operation,subject_namespace,opaque_id,name,world,x,y,z,yaw,revision,updated,expires,cooldown,lease_seconds,reserved,lease_until) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16)");
            insert.Text(1, operation); insert.Text(2, subject.Namespace); insert.Text(3, subject.OpaqueId);
            insert.Text(4, travel.Home.Name); insert.Text(5, world);
            insert.Floating(6, travel.Home.Position.X); insert.Floating(7, travel.Home.Position.Y);
            insert.Floating(8, travel.Home.Position.Z); insert.Floating(9, travel.Home.Position.Yaw);
            insert.Integer(10, travel.Home.Revision); insert.Integer(11, travel.Home.UpdatedUtcSeconds);
            if (travel.Home.ExpiresUtcSeconds) insert.Integer(12, *travel.Home.ExpiresUtcSeconds); else insert.Null(12);
            insert.Integer(13, cooldown); insert.Integer(14, lease); insert.Integer(15, now); insert.Integer(16, travel.LeaseUntil);
            const auto inserted = SqlStatus(insert.Step()); if (inserted != Status::Ok) return Result(travel, inserted);
            Statement reserve(db, "INSERT INTO travel_state(subject_namespace,opaque_id,next_allowed,pending,pending_until) VALUES(?1,?2,0,?3,?4) ON CONFLICT(subject_namespace,opaque_id) DO UPDATE SET pending=excluded.pending,pending_until=excluded.pending_until");
            reserve.Text(1, subject.Namespace); reserve.Text(2, subject.OpaqueId); reserve.Text(3, operation); reserve.Integer(4, travel.LeaseUntil);
            const auto reserved = SqlStatus(reserve.Step()); if (reserved != Status::Ok) return Result(travel, reserved);
            return Result(travel, transaction.Commit());
        }
        catch (...) { result.Status = Status::StorageError; return result; }
    }
    HomeTravelResult HomesStore::ResolveTravel(const HomesSubject& subject, std::string_view operation,
        std::string_view world, int64_t now) noexcept
    {
        HomeTravelResult result;
        if (!ValidSubject(subject) || !ValidToken(operation, 128, true) || !ValidUtf8(world, 256) || !Clock(now))
        { result.Status = Status::InvalidArgument; return result; }
        try
        {
            std::lock_guard lock(m_Impl->Mutex); auto* db = m_Impl->Db;
            Transaction transaction(db); if (transaction.Result != SQLITE_OK) { result.Status = SqlStatus(transaction.Result); return result; }
            Travel travel; result.Status = ReadTravel(db, operation, travel); if (result.Status != Status::Ok) return result;
            if (travel.Subject.Namespace != subject.Namespace || travel.Subject.OpaqueId != subject.OpaqueId) return Result(travel, Status::PayloadConflict);
            if (travel.Home.WorldFingerprint != world) return Result(travel, Status::WorldMismatch);
            if (travel.Outcome) return Result(travel, Status::AlreadyCompleted);
            if (now < travel.Reserved) return Result(travel, Status::InvalidArgument);
            if (now >= travel.LeaseUntil) return Result(travel, Status::ReservationExpired);
            Statement state(db, "SELECT pending FROM travel_state WHERE subject_namespace=?1 AND opaque_id=?2");
            state.Text(1, subject.Namespace); state.Text(2, subject.OpaqueId);
            if (state.Step() != SQLITE_ROW || state.ColumnText(0) != operation) return Result(travel, Status::ReservationExpired);
            return Result(travel, ValidateReservedHome(db, travel, now));
        }
        catch (...) { result.Status = Status::StorageError; return result; }
    }
    HomeTravelResult HomesStore::FinishTravel(const HomesSubject& subject, std::string_view operation,
        bool succeeded, int64_t now) noexcept
    {
        HomeTravelResult result;
        if (!ValidSubject(subject) || !ValidToken(operation, 128, true) || !Clock(now))
        { result.Status = Status::InvalidArgument; return result; }
        try
        {
            std::lock_guard lock(m_Impl->Mutex); auto* db = m_Impl->Db;
            Transaction transaction(db); if (transaction.Result != SQLITE_OK) { result.Status = SqlStatus(transaction.Result); return result; }
            Travel travel; result.Status = ReadTravel(db, operation, travel); if (result.Status != Status::Ok) return result;
            if (travel.Subject.Namespace != subject.Namespace || travel.Subject.OpaqueId != subject.OpaqueId) return Result(travel, Status::PayloadConflict);
            if (travel.Outcome) return Result(travel, *travel.Outcome == succeeded ? Status::Ok : Status::PayloadConflict, true);
            if (now < travel.Reserved) return Result(travel, Status::InvalidArgument);
            if (now >= travel.LeaseUntil) return Result(travel, Status::ReservationExpired);
            if (succeeded && !AddTime(now, travel.Cooldown)) return Result(travel, Status::InvalidArgument);
            Statement state(db, "SELECT next_allowed,pending FROM travel_state WHERE subject_namespace=?1 AND opaque_id=?2");
            state.Text(1, subject.Namespace); state.Text(2, subject.OpaqueId);
            if (state.Step() != SQLITE_ROW || state.ColumnText(1) != operation) return Result(travel, Status::ReservationExpired);
            const auto oldNext = sqlite3_column_int64(state.Value, 0);
            if (oldNext < 0) return Result(travel, Status::StorageError);
            travel.NextAllowed = succeeded ? now + travel.Cooldown : oldNext;
            Statement complete(db, "UPDATE travel_operations SET outcome=?1,finished=?2,next_allowed=?3 WHERE operation=?4 AND outcome IS NULL");
            complete.Integer(1, succeeded ? 1 : 0); complete.Integer(2, now); complete.Integer(3, travel.NextAllowed); complete.Text(4, operation);
            const auto completed = SqlStatus(complete.Step()); if (completed != Status::Ok) return Result(travel, completed);
            Statement release(db, "UPDATE travel_state SET next_allowed=?1,pending=NULL,pending_until=NULL WHERE subject_namespace=?2 AND opaque_id=?3 AND pending=?4");
            release.Integer(1, travel.NextAllowed); release.Text(2, subject.Namespace); release.Text(3, subject.OpaqueId); release.Text(4, operation);
            const auto released = SqlStatus(release.Step()); if (released != Status::Ok) return Result(travel, released);
            return Result(travel, transaction.Commit());
        }
        catch (...) { result.Status = Status::StorageError; return result; }
    }
}
