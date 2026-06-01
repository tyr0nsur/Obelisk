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
        bool Copied = true;
        uint64_t Handle = 17;
        bool HasGeneration = true;
        uint64_t Generation = 42;
        uint64_t CurrentGeneration = 42;
        PrincipalScope Scope = PrincipalScope::CallbackLocal;
        bool SameProcess = true;
    };

    struct OwnerContext
    {
        bool HasOwnerToken = true;
        bool HasCapability = true;
    };

    struct PolicyProvenance
    {
        bool HasSourceId = true;
        bool HasSourceGeneration = true;
        bool SourceGenerationMatches = true;
        bool HasAuthorityGeneration = true;
        bool AuthorityGenerationMatches = true;
        bool HasPolicyEpoch = true;
        PolicyAuthority Authority = PolicyAuthority::RuntimeOwned;
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
