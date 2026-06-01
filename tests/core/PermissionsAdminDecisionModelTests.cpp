#include <cstdint>
#include <iostream>
#include <stdexcept>

namespace
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

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool IsSupportedScope(PrincipalScope scope)
    {
        return scope == PrincipalScope::CallbackLocal || scope == PrincipalScope::ProcessLocal;
    }

    bool IsRecognizedAuthority(PolicyAuthority authority)
    {
        return authority == PolicyAuthority::RuntimeOwned || authority == PolicyAuthority::OperatorConfig;
    }

    bool IsAllowCapableAuthority(PolicyAuthority authority)
    {
        return authority == PolicyAuthority::RuntimeOwned;
    }

    Decision EvaluatePermissionQuery(const PermissionQuery& query)
    {
        const Principal& principal = query.PrincipalValue;
        const OwnerContext& owner = query.Owner;
        const PolicyProvenance& provenance = query.Provenance;
        const AbuseControls& abuse = query.Abuse;

        if (!owner.HasOwnerToken || !owner.HasCapability)
            return Decision::Deny;

        if (!principal.Copied || principal.Handle == 0)
            return Decision::Deny;

        if (!principal.HasGeneration || principal.Generation != principal.CurrentGeneration)
            return Decision::Unknown;

        if (!IsSupportedScope(principal.Scope) || !principal.SameProcess)
            return Decision::Unknown;

        if (!provenance.HasSourceId || !provenance.HasSourceGeneration ||
            !provenance.HasAuthorityGeneration || !provenance.HasPolicyEpoch)
        {
            return Decision::Unknown;
        }

        if (provenance.SuppliedByPlugin || provenance.Authority == PolicyAuthority::PluginSupplied)
            return Decision::Deny;

        if (!IsRecognizedAuthority(provenance.Authority) || !IsAllowCapableAuthority(provenance.Authority))
            return Decision::Unknown;

        if (!provenance.SourceGenerationMatches || !provenance.AuthorityGenerationMatches)
            return Decision::Unknown;

        if (!abuse.RateLimitOk)
            return Decision::Deny;

        if (!abuse.AuditOk)
            return Decision::Unknown;

        return Decision::Allow;
    }

    PermissionQuery CompleteRuntimeOwnedQuery()
    {
        return {};
    }

    void RequireDecision(Decision actual, Decision expected, const char* message)
    {
        Require(actual == expected, message);
    }

    void TestAllowsOnlyCompleteRuntimeOwnedCopiedPrincipal()
    {
        RequireDecision(EvaluatePermissionQuery(CompleteRuntimeOwnedQuery()),
                        Decision::Allow,
                        "complete runtime-owned query was not allowed");

        PermissionQuery operatorConfig = CompleteRuntimeOwnedQuery();
        operatorConfig.Provenance.Authority = PolicyAuthority::OperatorConfig;
        RequireDecision(EvaluatePermissionQuery(operatorConfig),
                        Decision::Unknown,
                        "operator-config provenance returned allow before allow-capable promotion");

        PermissionQuery unknownAuthority = CompleteRuntimeOwnedQuery();
        unknownAuthority.Provenance.Authority = PolicyAuthority::Unknown;
        RequireDecision(EvaluatePermissionQuery(unknownAuthority),
                        Decision::Unknown,
                        "unknown provenance authority returned allow");

        PermissionQuery remoteAuthority = CompleteRuntimeOwnedQuery();
        remoteAuthority.Provenance.Authority = PolicyAuthority::RemoteService;
        RequireDecision(EvaluatePermissionQuery(remoteAuthority),
                        Decision::Unknown,
                        "remote-service authority returned allow");
    }

    void TestPrincipalGenerationFailsClosed()
    {
        PermissionQuery notCopied = CompleteRuntimeOwnedQuery();
        notCopied.PrincipalValue.Copied = false;
        RequireDecision(EvaluatePermissionQuery(notCopied),
                        Decision::Deny,
                        "borrowed principal returned allow");

        PermissionQuery missingHandle = CompleteRuntimeOwnedQuery();
        missingHandle.PrincipalValue.Handle = 0;
        RequireDecision(EvaluatePermissionQuery(missingHandle),
                        Decision::Deny,
                        "missing principal handle returned allow");

        PermissionQuery missingGeneration = CompleteRuntimeOwnedQuery();
        missingGeneration.PrincipalValue.HasGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingGeneration),
                        Decision::Unknown,
                        "missing principal generation returned allow");

        PermissionQuery staleGeneration = CompleteRuntimeOwnedQuery();
        staleGeneration.PrincipalValue.CurrentGeneration = staleGeneration.PrincipalValue.Generation + 1;
        RequireDecision(EvaluatePermissionQuery(staleGeneration),
                        Decision::Unknown,
                        "stale principal generation returned allow");
    }

    void TestUnsupportedScopeFailsClosed()
    {
        PermissionQuery clusterStable = CompleteRuntimeOwnedQuery();
        clusterStable.PrincipalValue.Scope = PrincipalScope::ClusterStable;
        RequireDecision(EvaluatePermissionQuery(clusterStable),
                        Decision::Unknown,
                        "cluster-stable principal scope returned allow");

        PermissionQuery crossMap = CompleteRuntimeOwnedQuery();
        crossMap.PrincipalValue.Scope = PrincipalScope::CrossMapShared;
        RequireDecision(EvaluatePermissionQuery(crossMap),
                        Decision::Unknown,
                        "cross-map principal scope returned allow");

        PermissionQuery persistent = CompleteRuntimeOwnedQuery();
        persistent.PrincipalValue.Scope = PrincipalScope::Persistent;
        RequireDecision(EvaluatePermissionQuery(persistent),
                        Decision::Unknown,
                        "persistent principal scope returned allow");

        PermissionQuery processMismatch = CompleteRuntimeOwnedQuery();
        processMismatch.PrincipalValue.SameProcess = false;
        RequireDecision(EvaluatePermissionQuery(processMismatch),
                        Decision::Unknown,
                        "process-mismatched principal returned allow");
    }

    void TestOwnerAndCapabilityFailClosed()
    {
        PermissionQuery missingOwner = CompleteRuntimeOwnedQuery();
        missingOwner.Owner.HasOwnerToken = false;
        RequireDecision(EvaluatePermissionQuery(missingOwner),
                        Decision::Deny,
                        "missing owner token returned allow");

        PermissionQuery missingCapability = CompleteRuntimeOwnedQuery();
        missingCapability.Owner.HasCapability = false;
        RequireDecision(EvaluatePermissionQuery(missingCapability),
                        Decision::Deny,
                        "missing capability returned allow");
    }

    void TestPolicyProvenanceFailsClosed()
    {
        PermissionQuery missingSource = CompleteRuntimeOwnedQuery();
        missingSource.Provenance.HasSourceId = false;
        RequireDecision(EvaluatePermissionQuery(missingSource),
                        Decision::Unknown,
                        "missing policy source returned allow");

        PermissionQuery missingSourceGeneration = CompleteRuntimeOwnedQuery();
        missingSourceGeneration.Provenance.HasSourceGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingSourceGeneration),
                        Decision::Unknown,
                        "missing policy source generation returned allow");

        PermissionQuery missingEpoch = CompleteRuntimeOwnedQuery();
        missingEpoch.Provenance.HasPolicyEpoch = false;
        RequireDecision(EvaluatePermissionQuery(missingEpoch),
                        Decision::Unknown,
                        "missing policy epoch returned allow");

        PermissionQuery missingAuthorityGeneration = CompleteRuntimeOwnedQuery();
        missingAuthorityGeneration.Provenance.HasAuthorityGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingAuthorityGeneration),
                        Decision::Unknown,
                        "missing authority generation returned allow");

        PermissionQuery sourceMismatch = CompleteRuntimeOwnedQuery();
        sourceMismatch.Provenance.SourceGenerationMatches = false;
        RequireDecision(EvaluatePermissionQuery(sourceMismatch),
                        Decision::Unknown,
                        "policy source generation mismatch returned allow");

        PermissionQuery authorityMismatch = CompleteRuntimeOwnedQuery();
        authorityMismatch.Provenance.AuthorityGenerationMatches = false;
        RequireDecision(EvaluatePermissionQuery(authorityMismatch),
                        Decision::Unknown,
                        "authority generation mismatch returned allow");
    }

    void TestPluginSuppliedProvenanceFailsClosed()
    {
        PermissionQuery pluginAuthority = CompleteRuntimeOwnedQuery();
        pluginAuthority.Provenance.Authority = PolicyAuthority::PluginSupplied;
        RequireDecision(EvaluatePermissionQuery(pluginAuthority),
                        Decision::Deny,
                        "plugin-supplied authority returned allow");

        PermissionQuery selfAttested = CompleteRuntimeOwnedQuery();
        selfAttested.Provenance.SuppliedByPlugin = true;
        RequireDecision(EvaluatePermissionQuery(selfAttested),
                        Decision::Deny,
                        "plugin-self-attested provenance returned allow");
    }

    void TestRateLimitAndAuditFailuresFailClosed()
    {
        PermissionQuery rateLimited = CompleteRuntimeOwnedQuery();
        rateLimited.Abuse.RateLimitOk = false;
        RequireDecision(EvaluatePermissionQuery(rateLimited),
                        Decision::Deny,
                        "rate-limit failure returned allow");

        PermissionQuery auditFailed = CompleteRuntimeOwnedQuery();
        auditFailed.Abuse.AuditOk = false;
        RequireDecision(EvaluatePermissionQuery(auditFailed),
                        Decision::Unknown,
                        "audit failure returned allow");
    }
}

int main()
{
    TestAllowsOnlyCompleteRuntimeOwnedCopiedPrincipal();
    TestPrincipalGenerationFailsClosed();
    TestUnsupportedScopeFailsClosed();
    TestOwnerAndCapabilityFailClosed();
    TestPolicyProvenanceFailsClosed();
    TestPluginSuppliedProvenanceFailsClosed();
    TestRateLimitAndAuditFailuresFailClosed();

    std::cout << "PermissionsAdminDecisionModelTests passed\n";
    return 0;
}
