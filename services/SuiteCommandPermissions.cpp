#include "SuiteCommandPermissions.h"

#include <algorithm>
#include <limits>
#include <utility>

namespace Obelisk::Services
{
    namespace
    {
        using Status = SuiteCommandPermissionStatus;
        bool Token(std::string_view text, bool dotted = false) noexcept
        {
            if (text.empty() || text.size() > 64) return false;
            for (const unsigned char ch : text)
                if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                    (ch >= '0' && ch <= '9') || ch == '_' || ch == '-' ||
                    (dotted && (ch == '.' || ch == ':')))) return false;
            return true;
        }
        bool Command(std::string_view text) noexcept
        {
            if (text.size() < 2 || text.size() > 64 || text.front() != '/') return false;
            text.remove_prefix(1);
            for (const unsigned char ch : text)
                if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') ||
                    ch == '_' || ch == '-')) return false;
            return true;
        }
        bool Action(std::string_view text) noexcept
        {
            if (text.empty() || text.size() > 128) return false;
            size_t start = 0, segments = 0;
            for (size_t i = 0; i <= text.size(); ++i)
                if (i == text.size() || text[i] == '.')
                {
                    if (++segments > 8 || !Token(text.substr(start, i - start))) return false;
                    start = i + 1;
                }
            return true;
        }
        bool Valid(const SuiteCommandPermissionPolicy& policy) noexcept
        {
            if (!Token(policy.InstanceId) || policy.TrustedAuthorities.empty() ||
                policy.TrustedAuthorities.size() > 32 || policy.Routes.empty() ||
                policy.Routes.size() > 128) return false;
            for (size_t i = 0; i < policy.TrustedAuthorities.size(); ++i)
            {
                const auto& authority = policy.TrustedAuthorities[i];
                if (!Token(authority.AuthorityId) || !Token(authority.SubjectNamespace, true)) return false;
                for (size_t j = 0; j < i; ++j)
                    if (policy.TrustedAuthorities[j].AuthorityId == authority.AuthorityId &&
                        policy.TrustedAuthorities[j].SubjectNamespace == authority.SubjectNamespace) return false;
            }
            for (size_t i = 0; i < policy.Routes.size(); ++i)
            {
                const auto& route = policy.Routes[i];
                if (!Token(route.PluginId) || !Command(route.Command) || !Action(route.Action)) return false;
                for (size_t j = 0; j < i; ++j)
                    if (policy.Routes[j].PluginId == route.PluginId &&
                        policy.Routes[j].Command == route.Command) return false;
            }
            return true;
        }
        bool SamePrincipal(const SuiteAuthorizedCommandPrincipal& first,
                           const SuiteAuthorizedCommandPrincipal& second) noexcept
        {
            return first.Scope == second.Scope && first.Subject.Namespace == second.Subject.Namespace &&
                first.Subject.OpaqueId == second.Subject.OpaqueId && first.AuthorityId == second.AuthorityId &&
                first.AuthorityRevision == second.AuthorityRevision &&
                first.PrincipalGeneration == second.PrincipalGeneration &&
                first.IssuedUtcSeconds == second.IssuedUtcSeconds &&
                first.ExpiresUtcSeconds == second.ExpiresUtcSeconds;
        }
        bool Current(const SuiteAuthorizedCommandPrincipal& principal, int64_t now) noexcept
        {
            return principal.IssuedUtcSeconds >= 0 && principal.IssuedUtcSeconds <= now &&
                principal.ExpiresUtcSeconds > now;
        }
    }

    struct SuiteCommandPermissions::Policy
    {
        SuiteCommandPermissionPolicy Configuration;
        uint64_t Generation = 0;
    };

    SuiteCommandPermissions::SuiteCommandPermissions(SuiteStore& store,
        SuiteCommandPrincipalAuthority& authority, Clock clock)
        : m_Store(store), m_Authority(authority), m_Clock(std::move(clock)) {}

    SuiteCommandPermissionStatus SuiteCommandPermissions::Configure(
        const SuiteCommandPermissionPolicy& configuration) noexcept
    {
        std::shared_ptr<Policy> next;
        try
        {
            if (Valid(configuration))
            {
                next = std::make_shared<Policy>();
                next->Configuration = configuration;
            }
        }
        catch (...) { next.reset(); }
        std::lock_guard lock(m_Mutex);
        m_Policy.reset();
        if (m_Generation == std::numeric_limits<uint64_t>::max())
            return Status::InvalidConfiguration;
        ++m_Generation;
        if (!next) return Status::InvalidConfiguration;
        next->Generation = m_Generation;
        m_Policy = std::move(next);
        return Status::Configured;
    }

    void SuiteCommandPermissions::Clear() noexcept
    {
        std::lock_guard lock(m_Mutex);
        m_Policy.reset();
        if (m_Generation != std::numeric_limits<uint64_t>::max()) ++m_Generation;
    }

    std::optional<int64_t> SuiteCommandPermissions::Time() noexcept
    {
        try
        {
            if (!m_Clock) return std::nullopt;
            const auto now = m_Clock(); // external callbacks never hold our mutex
            std::lock_guard lock(m_Mutex);
            if (now < 0 || now < m_LatestUtcSeconds) return std::nullopt;
            m_LatestUtcSeconds = now;
            return now;
        }
        catch (...) { return std::nullopt; }
    }

    SuiteCommandPermissionDecision SuiteCommandPermissions::Evaluate(
        const SuitePermissionCommandScope& scope, std::string_view pluginId,
        std::string_view command) noexcept
    {
        SuiteCommandPermissionDecision decision;
        const auto reject = [&decision](Status status)
        { decision.Status = status; decision.Allowed = false; return decision; };
        try
        {
            if (!Token(scope.InstanceId) || !Token(pluginId) || !Command(command))
                return reject(Status::InvalidArgument);
            if (!scope.ProcessEpoch || !scope.SessionToken || !scope.OwnerGeneration || !scope.InvocationToken)
                return reject(Status::InvalidScope);
            std::shared_ptr<const Policy> policy;
            {
                std::lock_guard lock(m_Mutex);
                policy = m_Policy;
                decision.PolicyGeneration = m_Generation;
            }
            if (!policy) return reject(Status::Unconfigured);
            if (scope.InstanceId != policy->Configuration.InstanceId) return reject(Status::InvalidScope);
            const auto& routes = policy->Configuration.Routes;
            const auto route = std::find_if(routes.begin(), routes.end(), [&](const auto& entry)
            { return entry.PluginId == pluginId && entry.Command == command; });
            if (route == routes.end()) return reject(Status::NoRoute);
            const auto now = Time();
            if (!now) return reject(Status::ClockError);
            const uint64_t revision = m_Authority.Revision();
            if (!revision) return reject(Status::AuthorityUnavailable);
            const auto principal = m_Authority.Resolve(scope, *now);
            if (!principal) return reject(Status::AuthorityUnavailable);
            if (!(principal->Scope == scope)) return reject(Status::InvalidScope);
            if (!principal->PrincipalGeneration || principal->AuthorityRevision != revision)
                return reject(Status::StaleAuthority);
            const auto& trusted = policy->Configuration.TrustedAuthorities;
            if (std::none_of(trusted.begin(), trusted.end(), [&](const auto& entry)
                { return entry.AuthorityId == principal->AuthorityId &&
                    entry.SubjectNamespace == principal->Subject.Namespace; }))
                return reject(Status::UntrustedAuthority);
            const auto queryTime = Time();
            if (!queryTime) return reject(Status::ClockError);
            if (!Current(*principal, *queryTime)) return reject(Status::ExpiredPrincipal);
            if (m_Authority.Revision() != revision) return reject(Status::StaleAuthority);
            // No ACL decision cache: every command sees a fresh SQLite SELECT.
            const auto result = m_Store.CheckPermission(principal->Subject, route->Action, *queryTime);
            decision.StorageStatus = result.Status;
            if (result.Status != SuiteStoreStatus::Ok) return reject(Status::StorageFailure);
            const auto completionTime = Time();
            if (!completionTime) return reject(Status::ClockError);
            if (!Current(*principal, *completionTime)) return reject(Status::ExpiredPrincipal);
            if (result.NextMembershipExpiryUtcSeconds &&
                *result.NextMembershipExpiryUtcSeconds <= *completionTime)
                return reject(Status::ExpiredPermission);
            if (m_Authority.Revision() != revision) return reject(Status::StaleAuthority);
            const auto currentPrincipal = m_Authority.Resolve(scope, *completionTime);
            if (!currentPrincipal || !SamePrincipal(*principal, *currentPrincipal) ||
                m_Authority.Revision() != revision) return reject(Status::StaleAuthority);
            // The resolver itself may take time. Its unchanged lease/revision
            // cannot extend a principal or ACL membership past its deadline.
            const auto finalTime = Time();
            if (!finalTime) return reject(Status::ClockError);
            if (!Current(*principal, *finalTime)) return reject(Status::ExpiredPrincipal);
            if (result.NextMembershipExpiryUtcSeconds &&
                *result.NextMembershipExpiryUtcSeconds <= *finalTime)
                return reject(Status::ExpiredPermission);
            {
                std::lock_guard lock(m_Mutex);
                if (!m_Policy || m_Generation != policy->Generation)
                    return reject(Status::ConfigurationChanged);
            }
            decision.ExplicitDeny = result.ExplicitDeny;
            decision.Allowed = result.Allowed;
            decision.Status = result.Allowed ? Status::Allowed : Status::Denied;
            return decision;
        }
        catch (...) { return reject(Status::AuthorityUnavailable); }
    }
}
