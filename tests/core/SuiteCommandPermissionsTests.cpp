#include "services/SuiteCommandPermissions.h"

#include <sqlite3.h>

#include <filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <unistd.h>

namespace
{
    using namespace Obelisk::Services;
    using Status = SuiteCommandPermissionStatus;
    using StoreStatus = SuiteStoreStatus;
    using Effect = SuitePermissionEffect;

    void Require(bool condition, const char* message)
    { if (!condition) throw std::runtime_error(message); }

    struct Directory
    {
        std::filesystem::path Root;
        Directory()
        {
            char pattern[] = "/tmp/obelisk-command-permissions.XXXXXX";
            const auto* value = ::mkdtemp(pattern);
            Require(value, "mkdtemp failed");
            Root = value;
        }
        ~Directory() { std::error_code error; std::filesystem::remove_all(Root, error); }
    };

    // Test-only explicit authority. There is no server/storefront resolver in
    // production; this fixture supplies authentication facts deliberately.
    struct Authority final : SuiteCommandPrincipalAuthority
    {
        uint64_t CurrentRevision = 1;
        size_t ResolveCalls = 0;
        std::optional<SuiteAuthorizedCommandPrincipal> Principal;
        std::function<void(size_t)> OnResolve;
        uint64_t Revision() noexcept override { return CurrentRevision; }
        std::optional<SuiteAuthorizedCommandPrincipal> Resolve(
            const SuitePermissionCommandScope&, int64_t) noexcept override
        {
            ++ResolveCalls;
            if (OnResolve) OnResolve(ResolveCalls);
            return Principal;
        }
    };

    struct Fixture
    {
        Directory Temp;
        std::unique_ptr<SuiteStore> Store;
        Authority Issuer;
        int64_t Now = 100;
        SuitePermissionCommandScope Scope{"test", 42, 7, 13, 99};
        SuiteSubject Subject{"trusted:accounts", "opaque-玩家'"};
        SuiteCommandPermissionPolicy Policy{"test", {{"operator-auth", "trusted:accounts"}},
            {{"oHomes", "/home", "homes.travel"}, {"oAdvancedChat", "/tell", "chat.whisper"}}};
        std::unique_ptr<SuiteCommandPermissions> Service;
        Fixture()
        {
            StoreStatus status;
            Store = SuiteStore::Open(Temp.Root, "test", status);
            Require(Store && status == StoreStatus::Ok, "open failed");
            Require(Store->CreateRole("traveler") == StoreStatus::Ok &&
                    Store->PutPermission("traveler", "homes.*", Effect::Allow) == StoreStatus::Ok &&
                    Store->PutMembership(Subject, "traveler") == StoreStatus::Ok, "ACL setup failed");
            Issuer.Principal = SuiteAuthorizedCommandPrincipal{Scope, Subject, "operator-auth", 1, 11, 0, 1000};
            Service = std::make_unique<SuiteCommandPermissions>(*Store, Issuer, [this] { return Now; });
            Require(Service->Configure(Policy) == Status::Configured, "configuration failed");
        }
        SuiteCommandPermissionDecision Check()
        { return Service->Evaluate(Scope, "oHomes", "/home"); }
        std::unique_ptr<SuiteStore> SecondConnection()
        {
            StoreStatus status;
            auto connection = SuiteStore::Open(Temp.Root, "test", status);
            Require(connection && status == StoreStatus::Ok, "second connection failed");
            return connection;
        }
    };

    void TestTrustedPrincipalAndExactCommandRoute()
    {
        Fixture f;
        const auto allowed = f.Check();
        Require(allowed.Allowed && allowed.Status == Status::Allowed && allowed.PolicyGeneration == 1,
                "explicit trusted principal was denied");
        Require(!f.Service->Evaluate(f.Scope, "oHomes", "/home-other").Allowed &&
                f.Service->Evaluate(f.Scope, "oHomes", "/home-other").Status == Status::NoRoute,
                "command prefix gained authorization");
        Require(f.Service->Evaluate(f.Scope, "otherPlugin", "/home").Status == Status::NoRoute,
                "other plugin inherited route");
        Require(f.Service->Evaluate(f.Scope, "oHomes", "/HOME").Status == Status::InvalidArgument &&
                f.Service->Evaluate(f.Scope, "oHomes", "/home target").Status == Status::InvalidArgument,
                "service parsed noncanonical command instead of exact trusted route");
        auto scope = f.Scope;
        scope.InvocationToken = 0;
        Require(f.Service->Evaluate(scope, "oHomes", "/home").Status == Status::InvalidScope,
                "unscoped invocation accepted");
        scope = f.Scope;
        scope.InstanceId = "other-instance";
        Require(f.Service->Evaluate(scope, "oHomes", "/home").Status == Status::InvalidScope,
                "cross-instance command accepted");
        for (const int field : {0, 1, 2, 3})
        {
            scope = f.Scope;
            if (field == 0) ++scope.ProcessEpoch;
            if (field == 1) ++scope.SessionToken;
            if (field == 2) ++scope.OwnerGeneration;
            if (field == 3) ++scope.InvocationToken;
            Require(f.Service->Evaluate(scope, "oHomes", "/home").Status == Status::InvalidScope,
                    "principal escaped its exact returned command scope");
        }
        Require(!f.Service->Evaluate(f.Scope, "oAdvancedChat", "/tell").Allowed,
                "homes permission implied unrelated chat permission");
    }

    void TestObservedIdAndAuthorityCannotGrantImplicitly()
    {
        Fixture f;
        f.Issuer.Principal.reset();
        Require(f.Check().Status == Status::AuthorityUnavailable, "missing authority granted from stored role");
        f.Issuer.Principal = SuiteAuthorizedCommandPrincipal{f.Scope, f.Subject, "untrusted", 1, 11, 0, 1000};
        Require(f.Check().Status == Status::UntrustedAuthority, "unknown issuer accepted");
        const SuiteSubject observed{"observed-native", f.Subject.OpaqueId};
        Require(f.Store->PutMembership(observed, "traveler") == StoreStatus::Ok, "observation fixture failed");
        f.Issuer.Principal->AuthorityId = "operator-auth";
        f.Issuer.Principal->Subject = observed;
        Require(f.Check().Status == Status::UntrustedAuthority,
                "same native-looking identifier promoted unconfigured observation namespace");
        f.Issuer.Principal->Subject = f.Subject;
        f.Issuer.Principal->Subject.OpaqueId.clear();
        const auto invalidSubject = f.Check();
        Require(!invalidSubject.Allowed && invalidSubject.Status == Status::StorageFailure &&
                invalidSubject.StorageStatus == StoreStatus::InvalidArgument, "malformed principal granted");
        f.Issuer.CurrentRevision = 0;
        Require(f.Check().Status == Status::AuthorityUnavailable, "uninitialized authority revision accepted");
    }

    void TestFreshAclRevocationDenyAndExpiryAcrossConnections()
    {
        Fixture f;
        auto writer = f.SecondConnection();
        Require(f.Check().Allowed, "initial grant missing");
        Require(writer->RemoveMembership(f.Subject, "traveler") == StoreStatus::Ok, "revoke failed");
        Require(f.Check().Status == Status::Denied, "revoked grant remained cached");
        Require(writer->PutMembership(f.Subject, "traveler", 150) == StoreStatus::Ok, "timed grant failed");
        f.Now = 149;
        Require(f.Check().Allowed, "active timed grant missing");
        f.Now = 150;
        Require(!f.Check().Allowed, "expired membership stayed cached");
        Require(writer->PutMembership(f.Subject, "traveler") == StoreStatus::Ok &&
                writer->CreateRole("blocked") == StoreStatus::Ok &&
                writer->PutPermission("blocked", "homes.travel", Effect::Deny) == StoreStatus::Ok &&
                writer->PutMembership(f.Subject, "blocked", 200) == StoreStatus::Ok, "deny fixture failed");
        const auto denied = f.Check();
        Require(denied.Status == Status::Denied && denied.ExplicitDeny, "deny did not beat broad allow");
        f.Now = 200;
        Require(f.Check().Allowed, "expired deny was retained");
        Require(writer->RemovePermission("traveler", "homes.*") == StoreStatus::Ok,
                "permission removal failed");
        Require(!f.Check().Allowed, "revoked role permission stayed cached");
    }

    void TestAuthorityRevokedOrReboundDuringDecision()
    {
        Fixture f;
        f.Issuer.OnResolve = [&](size_t call) { if (call == 1) ++f.Issuer.CurrentRevision; };
        Require(f.Check().Status == Status::StaleAuthority, "revision race allowed old principal");
        f.Issuer.OnResolve = {};
        f.Issuer.CurrentRevision = 1;
        f.Issuer.ResolveCalls = 0;
        f.Issuer.OnResolve = [&](size_t call) { if (call == 2) f.Issuer.Principal.reset(); };
        Require(f.Check().Status == Status::StaleAuthority, "disconnect during ACL query preserved allow");
        f.Issuer.Principal = SuiteAuthorizedCommandPrincipal{f.Scope, f.Subject, "operator-auth", 1, 11, 0, 1000};
        f.Issuer.ResolveCalls = 0;
        f.Issuer.OnResolve = [&](size_t call) { if (call == 2) ++f.Issuer.Principal->PrincipalGeneration; };
        Require(f.Check().Status == Status::StaleAuthority, "unannounced principal generation rollover accepted");
    }

    void TestReloadAndClearInvalidateInflightDecision()
    {
        Fixture f;
        f.Issuer.OnResolve = [&](size_t call)
        {
            if (call == 2)
            {
                auto changed = f.Policy;
                changed.Routes[0].Action = "admin.teleport";
                Require(f.Service->Configure(changed) == Status::Configured, "reload failed");
            }
        };
        Require(f.Check().Status == Status::ConfigurationChanged, "inflight old policy grant escaped reload");
        f.Issuer.OnResolve = {};
        Require(!f.Check().Allowed, "new restricted route inherited old route grant");
        Require(f.Service->Configure(f.Policy) == Status::Configured && f.Check().Allowed,
                "valid policy restore failed");
        f.Service->Clear();
        Require(f.Check().Status == Status::Unconfigured, "clear retained authorization");
    }

    void TestMalformedReloadClosesAdmission()
    {
        Fixture f;
        Require(f.Check().Allowed, "initial grant missing");
        const auto initial = f.Policy;
        for (int kind = 0; kind < 8; ++kind)
        {
            auto malformed = initial;
            if (kind == 0) malformed.InstanceId = "../test";
            if (kind == 1) malformed.TrustedAuthorities.clear();
            if (kind == 2) malformed.TrustedAuthorities.push_back(malformed.TrustedAuthorities.front());
            if (kind == 3) malformed.Routes.push_back(malformed.Routes.front());
            if (kind == 4) malformed.Routes.front().Action = "homes.*";
            if (kind == 5) malformed.Routes.front().Command = "/home args";
            if (kind == 6) malformed.Routes.front().PluginId = "../oHomes";
            if (kind == 7) malformed.Routes.resize(129, malformed.Routes.front());
            Require(f.Service->Configure(malformed) == Status::InvalidConfiguration &&
                    f.Check().Status == Status::Unconfigured, "invalid reload retained previous allow policy");
            Require(f.Service->Configure(initial) == Status::Configured, "restore failed");
        }
    }

    void TestExpiryWhileDecisionFinishesAndClockRollback()
    {
        Fixture f;
        Require(f.Store->PutMembership(f.Subject, "traveler", 101) == StoreStatus::Ok, "expiry fixture failed");
        size_t tick = 0;
        SuiteCommandPermissions membershipService(*f.Store, f.Issuer, [&] { return ++tick < 3 ? 100 : 101; });
        Require(membershipService.Configure(f.Policy) == Status::Configured, "clock service configure failed");
        const auto membershipExpiry = membershipService.Evaluate(f.Scope, "oHomes", "/home");
        Require(!membershipExpiry.Allowed && membershipExpiry.Status == Status::ExpiredPermission,
                "membership expiry during decision was ignored");
        Require(!membershipService.Evaluate(f.Scope, "oHomes", "/home").Allowed,
                "expired membership gained on following decision");
        Require(f.Store->PutMembership(f.Subject, "traveler") == StoreStatus::Ok, "restore membership failed");
        f.Issuer.Principal->ExpiresUtcSeconds = 101;
        tick = 0;
        SuiteCommandPermissions principalService(*f.Store, f.Issuer, [&] { return ++tick < 3 ? 100 : 101; });
        principalService.Configure(f.Policy);
        Require(principalService.Evaluate(f.Scope, "oHomes", "/home").Status == Status::ExpiredPrincipal,
                "principal expired during decision was accepted");
        f.Issuer.Principal->ExpiresUtcSeconds = 1000;
        Require(f.Check().Allowed, "clock fixture initial grant missing");
        f.Now = 99;
        Require(f.Check().Status == Status::ClockError, "clock rollback resurrected permissions");
        f.Now = 101;
        Require(f.Check().Allowed, "clock catchup failed");
        SuiteCommandPermissions badClock(*f.Store, f.Issuer, []() -> int64_t { throw std::runtime_error("clock"); });
        badClock.Configure(f.Policy);
        Require(badClock.Evaluate(f.Scope, "oHomes", "/home").Status == Status::ClockError,
                "failed clock was converted to grant");
        {
            Fixture slow;
            Require(slow.Store->PutMembership(slow.Subject, "traveler", 101) == StoreStatus::Ok,
                    "slow resolver ACL fixture failed");
            slow.Issuer.OnResolve = [&](size_t call) { if (call == 2) slow.Now = 101; };
            Require(slow.Check().Status == Status::ExpiredPermission,
                    "slow second resolver outlived the ACL membership deadline");
        }
        {
            Fixture slow;
            slow.Issuer.Principal->ExpiresUtcSeconds = 101;
            slow.Issuer.OnResolve = [&](size_t call) { if (call == 2) slow.Now = 101; };
            Require(slow.Check().Status == Status::ExpiredPrincipal,
                    "slow second resolver outlived the principal deadline");
        }
    }

    void TestStorageFaultNeverProducesGrant()
    {
        Fixture f;
        sqlite3* database = nullptr;
        Require(sqlite3_open((f.Temp.Root / "test" / "suite.sqlite3").c_str(), &database) == SQLITE_OK,
                "raw DB open failed");
        Require(sqlite3_exec(database, "DROP TABLE role_permissions", nullptr, nullptr, nullptr) == SQLITE_OK,
                "storage failure fixture failed");
        sqlite3_close(database);
        const auto result = f.Check();
        Require(!result.Allowed && result.Status == Status::StorageFailure &&
                result.StorageStatus == StoreStatus::StorageError, "failed ACL SELECT produced grant");
    }
}

int main()
{
    try
    {
        TestTrustedPrincipalAndExactCommandRoute();
        TestObservedIdAndAuthorityCannotGrantImplicitly();
        TestFreshAclRevocationDenyAndExpiryAcrossConnections();
        TestAuthorityRevokedOrReboundDuringDecision();
        TestReloadAndClearInvalidateInflightDecision();
        TestMalformedReloadClosesAdmission();
        TestExpiryWhileDecisionFinishesAndClockRollback();
        TestStorageFaultNeverProducesGrant();
        std::cout << "Suite command permissions: 8 scenarios passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Suite command permissions failure: " << error.what() << '\n';
        return 1;
    }
}
