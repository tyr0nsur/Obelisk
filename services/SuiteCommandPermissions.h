#pragma once

#include "SuiteStore.h"

#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace Obelisk::Services
{
    // Private copied context, supplied by a trusted command adapter. The fields
    // are scope checks, never credentials or a replacement for runtime gates.
    struct SuitePermissionCommandScope
    {
        std::string InstanceId;
        uint64_t ProcessEpoch = 0;
        uint64_t SessionToken = 0;
        uint64_t OwnerGeneration = 0;
        uint64_t InvocationToken = 0;
        bool operator==(const SuitePermissionCommandScope&) const = default;
    };

    struct SuiteAuthorizedCommandPrincipal
    {
        SuitePermissionCommandScope Scope;
        SuiteSubject Subject;
        std::string AuthorityId;
        uint64_t AuthorityRevision = 0;
        uint64_t PrincipalGeneration = 0;
        int64_t IssuedUtcSeconds = 0;
        int64_t ExpiresUtcSeconds = 0;
    };

    // Implemented/installed by the trusted operator or authenticated private
    // adapter, never by a gameplay plugin. A resolver must validate the CURRENT
    // command scope and online principal. All revocations/rebindings advance
    // Revision; unchanged revisions must yield the same still-valid principal.
    // No implementation infers identity from a name or observed native ID.
    class SuiteCommandPrincipalAuthority
    {
    public:
        virtual ~SuiteCommandPrincipalAuthority() = default;
        virtual uint64_t Revision() noexcept = 0;
        virtual std::optional<SuiteAuthorizedCommandPrincipal> Resolve(
            const SuitePermissionCommandScope&, int64_t nowUtcSeconds) noexcept = 0;
    };

    struct SuiteTrustedAuthorityNamespace
    {
        std::string AuthorityId;
        std::string SubjectNamespace;
    };

    struct SuiteCommandPermissionRoute
    {
        std::string PluginId;
        std::string Command; // canonical exact "/verb", without arguments
        std::string Action;  // exact bounded SuiteStore action, no wildcard
    };

    struct SuiteCommandPermissionPolicy
    {
        std::string InstanceId;
        std::vector<SuiteTrustedAuthorityNamespace> TrustedAuthorities;
        std::vector<SuiteCommandPermissionRoute> Routes;
    };

    enum class SuiteCommandPermissionStatus
    {
        Configured,
        Allowed,
        Denied,
        InvalidArgument,
        InvalidConfiguration,
        Unconfigured,
        NoRoute,
        InvalidScope,
        AuthorityUnavailable,
        UntrustedAuthority,
        StaleAuthority,
        ExpiredPrincipal,
        ExpiredPermission,
        ClockError,
        ConfigurationChanged,
        StorageFailure,
    };

    struct SuiteCommandPermissionDecision
    {
        SuiteCommandPermissionStatus Status = SuiteCommandPermissionStatus::Denied;
        bool Allowed = false;
        bool ExplicitDeny = false;
        uint64_t PolicyGeneration = 0;
        SuiteStoreStatus StorageStatus = SuiteStoreStatus::Ok;
    };

    // Private, offline integration foundation. NOT linked to libobelisk or the
    // SDK; the actual server does not yet have an authenticated resolver.
    // Dependencies must outlive this object; drain calls before destruction.
    class SuiteCommandPermissions
    {
    public:
        using Clock = std::function<int64_t()>;
        SuiteCommandPermissions(SuiteStore&, SuiteCommandPrincipalAuthority&, Clock);
        SuiteCommandPermissions(const SuiteCommandPermissions&) = delete;
        SuiteCommandPermissions& operator=(const SuiteCommandPermissions&) = delete;

        // Every attempt advances the generation. Invalid configuration closes
        // admission rather than retaining a possibly revoked older policy.
        SuiteCommandPermissionStatus Configure(const SuiteCommandPermissionPolicy&) noexcept;
        void Clear() noexcept;
        SuiteCommandPermissionDecision Evaluate(const SuitePermissionCommandScope&,
            std::string_view pluginId, std::string_view command) noexcept;

    private:
        struct Policy;
        std::optional<int64_t> Time() noexcept;
        SuiteStore& m_Store;
        SuiteCommandPrincipalAuthority& m_Authority;
        Clock m_Clock;
        std::mutex m_Mutex;
        std::shared_ptr<const Policy> m_Policy;
        uint64_t m_Generation = 0;
        int64_t m_LatestUtcSeconds = -1;
    };
}
