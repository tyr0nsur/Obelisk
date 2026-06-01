#include "core/AuthzDecisionModel.h"

namespace obelisk::permissions_admin
{
    namespace
    {
        constexpr size_t kMaxActionBytes = 128;
        constexpr size_t kMaxResourceScopeBytes = 256;

        constexpr ReasonFlags Flag(ReasonFlag reason)
        {
            return static_cast<ReasonFlags>(reason);
        }

        bool HasValidCopiedByteSpan(const char* data, size_t size, size_t max_size, bool allow_empty)
        {
            if (size > max_size)
                return false;
            if (size == 0)
                return allow_empty && data == nullptr;
            return data != nullptr;
        }
    }

    bool HasWellFormedCopiedQueryText(const QueryText& text)
    {
        return HasValidCopiedByteSpan(text.Action, text.ActionSize, kMaxActionBytes, false) &&
               HasValidCopiedByteSpan(text.ResourceScope, text.ResourceScopeSize, kMaxResourceScopeBytes, true);
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

    PermissionEvaluation EvaluatePermissionQueryDetailed(const PermissionQuery& query)
    {
        const Principal& principal = query.PrincipalValue;
        const OwnerContext& owner = query.Owner;
        const PolicyProvenance& provenance = query.Provenance;
        const AbuseControls& abuse = query.Abuse;

        if (!owner.HasOwnerToken || !owner.OwnerTokenNonZero || !owner.OwnerKnown ||
            owner.OwnerUnloading || !owner.HasCapability)
        {
            ReasonFlags reasons = 0;
            if (!owner.HasOwnerToken)
                reasons |= Flag(ReasonFlag::MissingOwnerToken);
            if (!owner.OwnerTokenNonZero)
                reasons |= Flag(ReasonFlag::ZeroOwnerToken);
            if (!owner.OwnerKnown)
                reasons |= Flag(ReasonFlag::UnknownOwner);
            if (owner.OwnerUnloading)
                reasons |= Flag(ReasonFlag::OwnerUnloading);
            if (!owner.HasCapability)
                reasons |= Flag(ReasonFlag::MissingCapability);
            return {Decision::Deny, reasons};
        }

        if (!HasWellFormedCopiedQueryText(query.Text))
            return {Decision::Deny, Flag(ReasonFlag::MalformedQueryText)};

        if (!principal.Copied || principal.Handle == 0)
        {
            ReasonFlags reasons = 0;
            if (!principal.Copied)
                reasons |= Flag(ReasonFlag::PrincipalNotCopied);
            if (principal.Handle == 0)
                reasons |= Flag(ReasonFlag::MissingPrincipalHandle);
            return {Decision::Deny, reasons};
        }

        if (!principal.HasGeneration || principal.Generation != principal.CurrentGeneration)
        {
            ReasonFlags reasons = 0;
            if (!principal.HasGeneration)
                reasons |= Flag(ReasonFlag::MissingPrincipalGeneration);
            if (principal.HasGeneration && principal.Generation != principal.CurrentGeneration)
                reasons |= Flag(ReasonFlag::StalePrincipalGeneration);
            return {Decision::Unknown, reasons};
        }

        if (!IsSupportedScope(principal.Scope) || !principal.SameProcess)
        {
            ReasonFlags reasons = 0;
            if (!IsSupportedScope(principal.Scope))
                reasons |= Flag(ReasonFlag::UnsupportedPrincipalScope);
            if (!principal.SameProcess)
                reasons |= Flag(ReasonFlag::CrossProcessPrincipal);
            return {Decision::Unknown, reasons};
        }

        if (!provenance.HasSourceId || !provenance.HasSourceGeneration ||
            !provenance.HasAuthorityGeneration || !provenance.HasPolicyEpoch)
        {
            ReasonFlags reasons = 0;
            if (!provenance.HasSourceId)
                reasons |= Flag(ReasonFlag::MissingPolicySourceId);
            if (!provenance.HasSourceGeneration)
                reasons |= Flag(ReasonFlag::MissingPolicySourceGeneration);
            if (!provenance.HasAuthorityGeneration)
                reasons |= Flag(ReasonFlag::MissingAuthorityGeneration);
            if (!provenance.HasPolicyEpoch)
                reasons |= Flag(ReasonFlag::MissingPolicyEpoch);
            return {Decision::Unknown, reasons};
        }

        if (provenance.SuppliedByPlugin || provenance.Authority == PolicyAuthority::PluginSupplied)
            return {Decision::Deny, Flag(ReasonFlag::PluginSuppliedProvenance)};

        if (!IsRecognizedAuthority(provenance.Authority) || !IsAllowCapableAuthority(provenance.Authority))
        {
            ReasonFlags reasons = 0;
            if (!IsRecognizedAuthority(provenance.Authority))
                reasons |= Flag(ReasonFlag::UnrecognizedAuthority);
            if (IsRecognizedAuthority(provenance.Authority) && !IsAllowCapableAuthority(provenance.Authority))
                reasons |= Flag(ReasonFlag::AuthorityNotAllowCapable);
            return {Decision::Unknown, reasons};
        }

        if (!provenance.SourceGenerationMatches || !provenance.AuthorityGenerationMatches)
        {
            ReasonFlags reasons = 0;
            if (!provenance.SourceGenerationMatches)
                reasons |= Flag(ReasonFlag::PolicySourceGenerationMismatch);
            if (!provenance.AuthorityGenerationMatches)
                reasons |= Flag(ReasonFlag::AuthorityGenerationMismatch);
            return {Decision::Unknown, reasons};
        }

        if (!abuse.RateLimitOk)
            return {Decision::Deny, Flag(ReasonFlag::RateLimited)};

        if (!abuse.AuditOk)
            return {Decision::Unknown, Flag(ReasonFlag::AuditUnavailable)};

        return {Decision::Allow, 0};
    }

    Decision EvaluatePermissionQuery(const PermissionQuery& query)
    {
        return EvaluatePermissionQueryDetailed(query).DecisionValue;
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
        query.Owner.OwnerTokenNonZero = true;
        query.Owner.OwnerKnown = true;
        query.Owner.OwnerUnloading = false;
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

        query.Text.Action = "obelisk.permission.sample";
        query.Text.ActionSize = 25;
        query.Text.ResourceScope = nullptr;
        query.Text.ResourceScopeSize = 0;
        return query;
    }
}
