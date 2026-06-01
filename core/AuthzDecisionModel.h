#pragma once

#include <cstdint>

namespace obelisk::permissions_admin
{
    enum class Decision
    {
        Allow,
        Deny,
        Unknown
    };

    enum class PrincipalScope
    {
        CallbackLocal,
        ProcessLocal,
        ClusterStable,
        Persistent,
        CrossMapShared
    };

    enum class PolicyAuthority
    {
        RuntimeOwned,
        OperatorConfig,
        PluginSupplied,
        RemoteService,
        Unknown
    };

    struct Principal
    {
        bool Copied = false;
        uint64_t Handle = 0;
        bool HasGeneration = false;
        uint64_t Generation = 0;
        uint64_t CurrentGeneration = 0;
        PrincipalScope Scope = PrincipalScope::CallbackLocal;
        bool SameProcess = false;
    };

    struct OwnerContext
    {
        bool HasOwnerToken = false;
        bool HasCapability = false;
    };

    struct PolicyProvenance
    {
        bool HasSourceId = false;
        bool HasSourceGeneration = false;
        bool SourceGenerationMatches = false;
        bool HasAuthorityGeneration = false;
        bool AuthorityGenerationMatches = false;
        bool HasPolicyEpoch = false;
        PolicyAuthority Authority = PolicyAuthority::Unknown;
        bool SuppliedByPlugin = false;
    };

    struct AbuseControls
    {
        bool RateLimitOk = true;
        bool AuditOk = true;
    };

    struct PermissionQuery
    {
        Principal PrincipalValue;
        OwnerContext Owner;
        PolicyProvenance Provenance;
        AbuseControls Abuse;
    };

    bool IsSupportedScope(PrincipalScope scope);
    bool IsRecognizedAuthority(PolicyAuthority authority);
    bool IsAllowCapableAuthority(PolicyAuthority authority);
    Decision EvaluatePermissionQuery(const PermissionQuery& query);
    PermissionQuery CompleteRuntimeOwnedQuery();
}
