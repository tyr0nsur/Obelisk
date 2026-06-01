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

    using ReasonFlags = uint64_t;

    enum class ReasonFlag : uint64_t
    {
        None = 0,
        MissingOwnerToken = 1ull << 0,
        ZeroOwnerToken = 1ull << 1,
        UnknownOwner = 1ull << 2,
        OwnerUnloading = 1ull << 3,
        MissingCapability = 1ull << 4,
        MalformedQueryText = 1ull << 5,
        PrincipalNotCopied = 1ull << 6,
        MissingPrincipalHandle = 1ull << 7,
        MissingPrincipalGeneration = 1ull << 8,
        StalePrincipalGeneration = 1ull << 9,
        UnsupportedPrincipalScope = 1ull << 10,
        CrossProcessPrincipal = 1ull << 11,
        MissingPolicySourceId = 1ull << 12,
        MissingPolicySourceGeneration = 1ull << 13,
        MissingAuthorityGeneration = 1ull << 14,
        MissingPolicyEpoch = 1ull << 15,
        PluginSuppliedProvenance = 1ull << 16,
        UnrecognizedAuthority = 1ull << 17,
        AuthorityNotAllowCapable = 1ull << 18,
        PolicySourceGenerationMismatch = 1ull << 19,
        AuthorityGenerationMismatch = 1ull << 20,
        RateLimited = 1ull << 21,
        AuditUnavailable = 1ull << 22,
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

    struct PermissionEvaluation
    {
        Decision DecisionValue = Decision::Deny;
        ReasonFlags ReasonFlagsValue = 0;
    };

    bool HasWellFormedCopiedQueryText(const QueryText& text);
    bool IsSupportedScope(PrincipalScope scope);
    bool IsRecognizedAuthority(PolicyAuthority authority);
    bool IsAllowCapableAuthority(PolicyAuthority authority);
    PermissionEvaluation EvaluatePermissionQueryDetailed(const PermissionQuery& query);
    Decision EvaluatePermissionQuery(const PermissionQuery& query);
    PermissionQuery CompleteRuntimeOwnedQuery();
}
