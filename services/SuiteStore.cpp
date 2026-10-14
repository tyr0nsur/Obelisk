#include "SuiteStore.h"

#include <sqlite3.h>

#include <array>
#include <cerrno>
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
        using Status = SuiteStoreStatus;
        constexpr int kApplicationId = 0x4f424e53; // Private ObeliskNative suite store.
        constexpr int kBusyTimeoutMs = 2000;

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

        bool ValidSubject(const SuiteSubject& subject) noexcept
        {
            return ValidToken(subject.Namespace, 64, true) && ValidUtf8(subject.OpaqueId, SuiteStore::OpaqueIdMaxBytes);
        }

        bool ValidAction(std::string_view value, bool pattern) noexcept
        {
            if (value.empty() || value.size() > 128) return false;
            const bool wildcard = pattern && value.size() > 2 && value.ends_with(".*");
            if (wildcard) value.remove_suffix(2);
            size_t segments = wildcard ? 1 : 0, start = 0;
            for (size_t i = 0; i <= value.size(); ++i)
                if (i == value.size() || value[i] == '.')
                {
                    if (++segments > 8 || !ValidToken(value.substr(start, i - start), 64, false)) return false;
                    start = i + 1;
                }
            return true;
        }

        bool PatternMatches(std::string_view pattern, std::string_view action) noexcept
        {
            if (pattern.ends_with(".*"))
            {
                pattern.remove_suffix(1); // Keep dot: "chat.*" cannot match "chatty.read" or "chat".
                return action.size() > pattern.size() && action.starts_with(pattern);
            }
            return pattern == action;
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
            constexpr std::array filenames{"suite.sqlite3", "suite.sqlite3-wal", "suite.sqlite3-shm", "suite.sqlite3-journal"};
            for (const auto* filename : filenames)
            {
                struct stat info{};
                if (::fstatat(instanceDirectory.Value, filename, &info, AT_SYMLINK_NOFOLLOW) == 0)
                {
                    if (!PrivateFile(info)) return false;
                }
                else if (errno != ENOENT) return false;
            }
            FileDescriptor database(::openat(instanceDirectory.Value, "suite.sqlite3",
                O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600));
            struct stat info{};
            if (database.Value < 0 || ::fstat(database.Value, &info) != 0 || !PrivateFile(info)) return false;
            identity.Database = info;
            path = (root / instanceName / "suite.sqlite3").string();
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
            return ::fstatat(instanceDirectory.Value, "suite.sqlite3", &info, AT_SYMLINK_NOFOLLOW) == 0 &&
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

        Status ReadPragma(sqlite3* db, const char* sql, int& out) noexcept
        {
            Statement query(db, sql);
            const int result = query.Step();
            if (result != SQLITE_ROW) return SqlStatus(result) == Status::Ok ? Status::StorageError : SqlStatus(result);
            out = sqlite3_column_int(query.Value, 0);
            return Status::Ok;
        }

        Status Initialize(sqlite3* db) noexcept
        {
            int version = -1, application = 0;
            auto status = ReadPragma(db, "PRAGMA user_version", version);
            if (status != Status::Ok) return status;
            if (version < 0 || version > SuiteStore::SchemaVersion) return Status::UnsupportedSchema;
            status = ReadPragma(db, "PRAGMA application_id", application);
            if (status != Status::Ok) return status;
            if ((version == 1 && application != kApplicationId) || (version == 0 && application != 0))
                return Status::UnsupportedSchema;
            if (sqlite3_exec(db, "PRAGMA foreign_keys=ON", nullptr, nullptr, nullptr) != SQLITE_OK) return Status::StorageError;
            if (version == 0)
            {
                Transaction transaction(db);
                if (transaction.Result != SQLITE_OK) return SqlStatus(transaction.Result);
                // Two connections can both observe zero before the first migration.
                status = ReadPragma(db, "PRAGMA user_version", version);
                if (status != Status::Ok) return status;
                if (version == 0)
                {
                    {
                        Statement existing(db, "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'");
                        const int result = existing.Step();
                        if (result != SQLITE_ROW) return SqlStatus(result) == Status::Ok ? Status::StorageError : SqlStatus(result);
                        if (sqlite3_column_int64(existing.Value, 0) != 0) return Status::UnsupportedSchema;
                    }
                    constexpr const char* schema = R"sql(
CREATE TABLE roles(role TEXT COLLATE BINARY NOT NULL PRIMARY KEY);
CREATE TABLE role_permissions(
 role TEXT COLLATE BINARY NOT NULL REFERENCES roles(role) ON DELETE CASCADE,
 pattern TEXT COLLATE BINARY NOT NULL,
 effect INTEGER NOT NULL CHECK(typeof(effect)='integer' AND effect IN(0,1)),
 PRIMARY KEY(role,pattern));
CREATE TABLE memberships(
 subject_namespace TEXT COLLATE BINARY NOT NULL, opaque_id TEXT COLLATE BINARY NOT NULL,
 role TEXT COLLATE BINARY NOT NULL REFERENCES roles(role) ON DELETE CASCADE,
 expires_utc INTEGER CHECK(expires_utc IS NULL OR (typeof(expires_utc)='integer' AND expires_utc>=0)),
 PRIMARY KEY(subject_namespace,opaque_id,role));
CREATE TABLE wallets(
 subject_namespace TEXT COLLATE BINARY NOT NULL, opaque_id TEXT COLLATE BINARY NOT NULL,
 balance INTEGER NOT NULL CHECK(typeof(balance)='integer' AND balance>=0),
 PRIMARY KEY(subject_namespace,opaque_id));
CREATE TABLE wallet_operations(
 operation_id TEXT COLLATE BINARY NOT NULL PRIMARY KEY,
 kind INTEGER NOT NULL CHECK(kind IN(1,2,3)),
 source_namespace TEXT COLLATE BINARY NOT NULL, source_id TEXT COLLATE BINARY NOT NULL,
 destination_namespace TEXT COLLATE BINARY, destination_id TEXT COLLATE BINARY,
 amount INTEGER NOT NULL CHECK(typeof(amount)='integer' AND amount>0),
 balance INTEGER NOT NULL CHECK(typeof(balance)='integer' AND balance>=0),
 destination_balance INTEGER CHECK(destination_balance IS NULL OR (typeof(destination_balance)='integer' AND destination_balance>=0)),
 CHECK((kind=3 AND destination_namespace IS NOT NULL AND destination_id IS NOT NULL AND destination_balance IS NOT NULL)
    OR (kind IN(1,2) AND destination_namespace IS NULL AND destination_id IS NULL AND destination_balance IS NULL)));
PRAGMA application_id=0x4f424e53;
PRAGMA user_version=1;
)sql";
                    const int result = sqlite3_exec(db, schema, nullptr, nullptr, nullptr);
                    if (result != SQLITE_OK) return SqlStatus(result);
                }
                else
                {
                    status = ReadPragma(db, "PRAGMA application_id", application);
                    if (status != Status::Ok) return status;
                    if (version != SuiteStore::SchemaVersion || application != kApplicationId) return Status::UnsupportedSchema;
                }
                status = transaction.Commit();
                if (status != Status::Ok) return status;
            }
            // Validate expected tables/columns even when version metadata is present.
            constexpr std::array checks{
                "SELECT role FROM roles LIMIT 0",
                "SELECT role,pattern,effect FROM role_permissions LIMIT 0",
                "SELECT subject_namespace,opaque_id,role,expires_utc FROM memberships LIMIT 0",
                "SELECT subject_namespace,opaque_id,balance FROM wallets LIMIT 0",
                "SELECT operation_id,kind,source_namespace,source_id,destination_namespace,destination_id,amount,balance,destination_balance FROM wallet_operations LIMIT 0"};
            for (const auto* sql : checks)
            {
                Statement query(db, sql);
                if (query.Step() != SQLITE_DONE) return Status::UnsupportedSchema;
            }
            {
                Statement journal(db, "PRAGMA journal_mode=WAL");
                const int journalResult = journal.Step();
                if (journalResult != SQLITE_ROW) return SqlStatus(journalResult) == Status::Ok ? Status::StorageError : SqlStatus(journalResult);
                if (journal.ColumnText(0) != "wal") return Status::StorageError;
            }
            return SqlStatus(sqlite3_exec(db, "PRAGMA synchronous=FULL", nullptr, nullptr, nullptr));
        }

        Status ReadBalance(sqlite3* db, const SuiteSubject& subject, int64_t& balance, bool& exists) noexcept
        {
            Statement query(db, "SELECT balance FROM wallets WHERE subject_namespace=?1 AND opaque_id=?2");
            query.Text(1, subject.Namespace); query.Text(2, subject.OpaqueId);
            const int result = query.Step();
            if (result == SQLITE_DONE) { balance = 0; exists = false; return Status::Ok; }
            if (result != SQLITE_ROW) return SqlStatus(result);
            if (sqlite3_column_type(query.Value, 0) != SQLITE_INTEGER) return Status::StorageError;
            balance = sqlite3_column_int64(query.Value, 0);
            exists = true;
            return balance >= 0 ? Status::Ok : Status::StorageError;
        }

        Status WriteBalance(sqlite3* db, const SuiteSubject& subject, int64_t balance) noexcept
        {
            Statement update(db, "INSERT INTO wallets(subject_namespace,opaque_id,balance) VALUES(?1,?2,?3) "
                "ON CONFLICT(subject_namespace,opaque_id) DO UPDATE SET balance=excluded.balance");
            update.Text(1, subject.Namespace); update.Text(2, subject.OpaqueId); update.Integer(3, balance);
            return SqlStatus(update.Step());
        }
    }

    struct SuiteStore::Impl
    {
        sqlite3* Db = nullptr;
        std::mutex Mutex;
        ~Impl() { if (Db) sqlite3_close_v2(Db); }
    };

    SuiteStore::SuiteStore(std::unique_ptr<Impl> impl) noexcept : m_Impl(std::move(impl)) {}
    SuiteStore::~SuiteStore() noexcept = default;

    std::unique_ptr<SuiteStore> SuiteStore::Open(const std::filesystem::path& root, std::string_view instance, Status& status) noexcept
    {
        status = Status::StorageError;
        try
        {
            std::string path;
            PathIdentity identity;
            if (!PreparePath(root, instance, path, identity)) { status = Status::InvalidPath; return {}; }
            auto impl = std::make_unique<Impl>();
            const int result = sqlite3_open_v2(path.c_str(), &impl->Db,
                SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX | SQLITE_OPEN_PRIVATECACHE | SQLITE_OPEN_NOFOLLOW, nullptr);
            if (result != SQLITE_OK) { status = SqlStatus(result); return {}; }
            if (!VerifyPathIdentity(root, instance, identity)) { status = Status::InvalidPath; return {}; }
            if (sqlite3_db_readonly(impl->Db, "main") != 0) return {};
            if (sqlite3_busy_timeout(impl->Db, kBusyTimeoutMs) != SQLITE_OK) return {};
            status = Initialize(impl->Db);
            if (status != Status::Ok) return {};
            auto store = std::unique_ptr<SuiteStore>(new SuiteStore(std::move(impl)));
            return store;
        }
        catch (...) { status = Status::StorageError; return {}; }
    }

    Status SuiteStore::CreateRole(std::string_view role) noexcept
    {
        if (!ValidToken(role, 64, true)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement insert(m_Impl->Db, "INSERT INTO roles(role) VALUES(?1) ON CONFLICT(role) DO NOTHING");
            insert.Text(1, role);
            return SqlStatus(insert.Step());
        }
        catch (...) { return Status::StorageError; }
    }

    Status SuiteStore::PutPermission(std::string_view role, std::string_view pattern, SuitePermissionEffect effect) noexcept
    {
        if (!ValidToken(role, 64, true) || !ValidAction(pattern, true) ||
            (effect != SuitePermissionEffect::Allow && effect != SuitePermissionEffect::Deny)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement insert(m_Impl->Db, "INSERT INTO role_permissions(role,pattern,effect) "
                "SELECT ?1,?2,?3 WHERE EXISTS(SELECT 1 FROM roles WHERE role=?1) "
                "ON CONFLICT(role,pattern) DO UPDATE SET effect=excluded.effect");
            insert.Text(1, role); insert.Text(2, pattern); insert.Integer(3, static_cast<int>(effect));
            const auto status = SqlStatus(insert.Step());
            return status == Status::Ok && sqlite3_changes(m_Impl->Db) == 0 ? Status::NotFound : status;
        }
        catch (...) { return Status::StorageError; }
    }

    Status SuiteStore::RemovePermission(std::string_view role, std::string_view pattern) noexcept
    {
        if (!ValidToken(role, 64, true) || !ValidAction(pattern, true)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement remove(m_Impl->Db, "DELETE FROM role_permissions WHERE role=?1 AND pattern=?2");
            remove.Text(1, role); remove.Text(2, pattern);
            const auto status = SqlStatus(remove.Step());
            return status == Status::Ok && sqlite3_changes(m_Impl->Db) == 0 ? Status::NotFound : status;
        }
        catch (...) { return Status::StorageError; }
    }

    Status SuiteStore::PutMembership(const SuiteSubject& subject, std::string_view role, std::optional<int64_t> expires) noexcept
    {
        if (!ValidSubject(subject) || !ValidToken(role, 64, true) || (expires && *expires < 0)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement insert(m_Impl->Db, "INSERT INTO memberships(subject_namespace,opaque_id,role,expires_utc) "
                "SELECT ?1,?2,?3,?4 WHERE EXISTS(SELECT 1 FROM roles WHERE role=?3) "
                "ON CONFLICT(subject_namespace,opaque_id,role) DO UPDATE SET expires_utc=excluded.expires_utc");
            insert.Text(1, subject.Namespace); insert.Text(2, subject.OpaqueId); insert.Text(3, role);
            if (expires) insert.Integer(4, *expires); else insert.Null(4);
            const auto status = SqlStatus(insert.Step());
            return status == Status::Ok && sqlite3_changes(m_Impl->Db) == 0 ? Status::NotFound : status;
        }
        catch (...) { return Status::StorageError; }
    }

    Status SuiteStore::RemoveMembership(const SuiteSubject& subject, std::string_view role) noexcept
    {
        if (!ValidSubject(subject) || !ValidToken(role, 64, true)) return Status::InvalidArgument;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement remove(m_Impl->Db, "DELETE FROM memberships WHERE subject_namespace=?1 AND opaque_id=?2 AND role=?3");
            remove.Text(1, subject.Namespace); remove.Text(2, subject.OpaqueId); remove.Text(3, role);
            const auto status = SqlStatus(remove.Step());
            return status == Status::Ok && sqlite3_changes(m_Impl->Db) == 0 ? Status::NotFound : status;
        }
        catch (...) { return Status::StorageError; }
    }

    SuitePermissionResult SuiteStore::CheckPermission(const SuiteSubject& subject, std::string_view action, int64_t now) noexcept
    {
        if (!ValidSubject(subject) || !ValidAction(action, false) || now < 0) return {Status::InvalidArgument};
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Statement query(m_Impl->Db, "SELECT p.pattern,p.effect FROM memberships m JOIN role_permissions p ON p.role=m.role "
                "WHERE m.subject_namespace=?1 AND m.opaque_id=?2 AND (m.expires_utc IS NULL OR m.expires_utc>?3)");
            query.Text(1, subject.Namespace); query.Text(2, subject.OpaqueId); query.Integer(3, now);
            bool allowed = false, denied = false;
            for (;;)
            {
                const int result = query.Step();
                if (result == SQLITE_DONE) return {Status::Ok, allowed && !denied, denied};
                if (result != SQLITE_ROW) return {SqlStatus(result)};
                const auto pattern = query.ColumnText(0);
                const int effect = sqlite3_column_int(query.Value, 1);
                if (!ValidAction(pattern, true) || sqlite3_column_type(query.Value, 1) != SQLITE_INTEGER || (effect != 0 && effect != 1))
                    return {Status::StorageError};
                if (PatternMatches(pattern, action))
                {
                    if (effect == 1) denied = true;
                    else allowed = true;
                }
            }
        }
        catch (...) { return {Status::StorageError}; }
    }

    SuiteBalanceResult SuiteStore::Balance(const SuiteSubject& subject) noexcept
    {
        if (!ValidSubject(subject)) return {Status::InvalidArgument};
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            SuiteBalanceResult result;
            result.Status = ReadBalance(m_Impl->Db, subject, result.Balance, result.Exists);
            return result;
        }
        catch (...) { return {Status::StorageError}; }
    }

    SuiteOperationResult SuiteStore::Credit(const SuiteSubject& subject, int64_t amount, std::string_view id) noexcept
    { return Apply(1, subject, nullptr, amount, id); }
    SuiteOperationResult SuiteStore::Debit(const SuiteSubject& subject, int64_t amount, std::string_view id) noexcept
    { return Apply(2, subject, nullptr, amount, id); }
    SuiteOperationResult SuiteStore::Transfer(const SuiteSubject& source, const SuiteSubject& destination, int64_t amount, std::string_view id) noexcept
    { return Apply(3, source, &destination, amount, id); }

    SuiteOperationResult SuiteStore::Apply(int kind, const SuiteSubject& source, const SuiteSubject* destination,
                                         int64_t amount, std::string_view id) noexcept
    {
        if (!ValidSubject(source) || (destination && !ValidSubject(*destination)) || amount <= 0 || !ValidUtf8(id, 128) ||
            (destination && source.Namespace == destination->Namespace && source.OpaqueId == destination->OpaqueId))
            return {Status::InvalidArgument};
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            Transaction transaction(m_Impl->Db);
            if (transaction.Result != SQLITE_OK) return {SqlStatus(transaction.Result)};
            {
                Statement previous(m_Impl->Db, "SELECT kind,source_namespace,source_id,destination_namespace,destination_id,amount,balance,destination_balance "
                    "FROM wallet_operations WHERE operation_id=?1");
                previous.Text(1, id);
                const int result = previous.Step();
                if (result == SQLITE_ROW)
                {
                    const bool sameDestination = destination
                        ? previous.ColumnText(3) == destination->Namespace && previous.ColumnText(4) == destination->OpaqueId
                        : sqlite3_column_type(previous.Value, 3) == SQLITE_NULL && sqlite3_column_type(previous.Value, 4) == SQLITE_NULL;
                    if (sqlite3_column_int(previous.Value, 0) != kind || previous.ColumnText(1) != source.Namespace ||
                        previous.ColumnText(2) != source.OpaqueId || !sameDestination || sqlite3_column_int64(previous.Value, 5) != amount)
                        return {Status::PayloadConflict};
                    if (sqlite3_column_type(previous.Value, 6) != SQLITE_INTEGER ||
                        (destination && sqlite3_column_type(previous.Value, 7) != SQLITE_INTEGER)) return {Status::StorageError};
                    const int64_t balance = sqlite3_column_int64(previous.Value, 6);
                    const int64_t target = destination ? sqlite3_column_int64(previous.Value, 7) : 0;
                    if (balance < 0 || target < 0) return {Status::StorageError};
                    return {Status::Ok, true, balance, target}; // Read-only transaction rolls back on scope exit.
                }
                if (result != SQLITE_DONE) return {SqlStatus(result)};
            }
            int64_t balance = 0, target = 0;
            bool exists = false;
            auto status = ReadBalance(m_Impl->Db, source, balance, exists);
            if (status != Status::Ok) return {status};
            if (kind == 1)
            {
                if (amount > std::numeric_limits<int64_t>::max() - balance) return {Status::Overflow};
                balance += amount;
            }
            else
            {
                if (amount > balance) return {Status::InsufficientFunds};
                balance -= amount;
            }
            if (destination)
            {
                status = ReadBalance(m_Impl->Db, *destination, target, exists);
                if (status != Status::Ok) return {status};
                if (amount > std::numeric_limits<int64_t>::max() - target) return {Status::Overflow};
                target += amount;
            }
            status = WriteBalance(m_Impl->Db, source, balance);
            if (status != Status::Ok) return {status};
            if (destination)
            {
                status = WriteBalance(m_Impl->Db, *destination, target);
                if (status != Status::Ok) return {status};
            }
            Statement record(m_Impl->Db, "INSERT INTO wallet_operations(operation_id,kind,source_namespace,source_id,destination_namespace,destination_id,amount,balance,destination_balance) "
                "VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)");
            record.Text(1, id); record.Integer(2, kind); record.Text(3, source.Namespace); record.Text(4, source.OpaqueId);
            if (destination) { record.Text(5, destination->Namespace); record.Text(6, destination->OpaqueId); record.Integer(9, target); }
            else { record.Null(5); record.Null(6); record.Null(9); }
            record.Integer(7, amount); record.Integer(8, balance);
            status = SqlStatus(record.Step());
            if (status != Status::Ok) return {status};
            status = transaction.Commit();
            return status == Status::Ok ? SuiteOperationResult{status, false, balance, target} : SuiteOperationResult{status};
        }
        catch (...) { return {Status::StorageError}; }
    }
}
