#pragma once

#include <cstdint>
#include <cstddef>

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
        bool OwnerTokenNonZero = false;
        bool OwnerKnown = false;
        bool OwnerUnloading = false;
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

    struct QueryText
    {
        const char* Action = nullptr;
        size_t ActionSize = 0;
        const char* ResourceScope = nullptr;
        size_t ResourceScopeSize = 0;
    };

    struct PermissionQuery
    {
        Principal PrincipalValue;
        OwnerContext Owner;
        PolicyProvenance Provenance;
        AbuseControls Abuse;
        QueryText Text;
    };

    bool HasWellFormedCopiedQueryText(const QueryText& text);
    bool IsSupportedScope(PrincipalScope scope);
    bool IsRecognizedAuthority(PolicyAuthority authority);
    bool IsAllowCapableAuthority(PolicyAuthority authority);
    Decision EvaluatePermissionQuery(const PermissionQuery& query);
    PermissionQuery CompleteRuntimeOwnedQuery();
}
