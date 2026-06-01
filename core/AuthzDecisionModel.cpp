#include "core/AuthzDecisionModel.h"

namespace obelisk::permissions_admin
{
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
        PermissionQuery query;
        query.PrincipalValue.Copied = true;
        query.PrincipalValue.Handle = 17;
        query.PrincipalValue.HasGeneration = true;
        query.PrincipalValue.Generation = 42;
        query.PrincipalValue.CurrentGeneration = 42;
        query.PrincipalValue.Scope = PrincipalScope::CallbackLocal;
        query.PrincipalValue.SameProcess = true;

        query.Owner.HasOwnerToken = true;
        query.Owner.HasCapability = true;

        query.Provenance.HasSourceId = true;
        query.Provenance.HasSourceGeneration = true;
        query.Provenance.SourceGenerationMatches = true;
        query.Provenance.HasAuthorityGeneration = true;
        query.Provenance.AuthorityGenerationMatches = true;
        query.Provenance.HasPolicyEpoch = true;
        query.Provenance.Authority = PolicyAuthority::RuntimeOwned;
        query.Provenance.SuppliedByPlugin = false;

        query.Abuse.RateLimitOk = true;
        query.Abuse.AuditOk = true;
        return query;
    }
}
