#include "core/AuthzDecisionModel.h"

#include <iostream>
#include <stdexcept>

namespace
{
    using obelisk::permissions_admin::CompleteRuntimeOwnedQuery;
    using obelisk::permissions_admin::Decision;
    using obelisk::permissions_admin::EvaluatePermissionQuery;
    using obelisk::permissions_admin::EvaluatePermissionQueryDetailed;
    using obelisk::permissions_admin::HasWellFormedCopiedQueryText;
    using obelisk::permissions_admin::PermissionQuery;
    using obelisk::permissions_admin::PolicyAuthority;
    using obelisk::permissions_admin::PrincipalScope;
    using obelisk::permissions_admin::ReasonFlag;
    using obelisk::permissions_admin::ReasonFlags;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void RequireDecision(Decision actual, Decision expected, const char* message)
    {
        Require(actual == expected, message);
    }

    constexpr ReasonFlags Flag(ReasonFlag reason)
    {
        return static_cast<ReasonFlags>(reason);
    }

    void RequireEvaluation(const PermissionQuery& query,
                           Decision expectedDecision,
                           ReasonFlags expectedReasons,
                           const char* message)
    {
        const auto evaluation = EvaluatePermissionQueryDetailed(query);
        Require(evaluation.DecisionValue == expectedDecision, message);
        Require(EvaluatePermissionQuery(query) == evaluation.DecisionValue,
                "detailed permissions/admin evaluation drifted from wrapper decision");
        Require(evaluation.ReasonFlagsValue == expectedReasons,
                "permissions/admin reason flags did not match expected diagnostic bits");
    }

    void TestDetailedEvaluationPreservesWrapperDecision()
    {
        for (PermissionQuery query : {
                 PermissionQuery{},
                 CompleteRuntimeOwnedQuery(),
             })
        {
            Require(EvaluatePermissionQuery(query) == EvaluatePermissionQueryDetailed(query).DecisionValue,
                    "detailed permissions/admin evaluation changed wrapper decision");
        }

        PermissionQuery operatorConfig = CompleteRuntimeOwnedQuery();
        operatorConfig.Provenance.Authority = PolicyAuthority::OperatorConfig;
        Require(EvaluatePermissionQuery(operatorConfig) ==
                    EvaluatePermissionQueryDetailed(operatorConfig).DecisionValue,
                "operator-config detailed evaluation changed wrapper decision");

        PermissionQuery pluginSupplied = CompleteRuntimeOwnedQuery();
        pluginSupplied.Provenance.SuppliedByPlugin = true;
        Require(EvaluatePermissionQuery(pluginSupplied) ==
                    EvaluatePermissionQueryDetailed(pluginSupplied).DecisionValue,
                "plugin-supplied detailed evaluation changed wrapper decision");

        PermissionQuery rateLimited = CompleteRuntimeOwnedQuery();
        rateLimited.Abuse.RateLimitOk = false;
        Require(EvaluatePermissionQuery(rateLimited) ==
                    EvaluatePermissionQueryDetailed(rateLimited).DecisionValue,
                "rate-limit detailed evaluation changed wrapper decision");

        PermissionQuery auditFailed = CompleteRuntimeOwnedQuery();
        auditFailed.Abuse.AuditOk = false;
        Require(EvaluatePermissionQuery(auditFailed) ==
                    EvaluatePermissionQueryDetailed(auditFailed).DecisionValue,
                "audit detailed evaluation changed wrapper decision");
    }

    void TestAllowsOnlyCompleteRuntimeOwnedCopiedPrincipal()
    {
        RequireDecision(EvaluatePermissionQuery(PermissionQuery{}),
                        Decision::Deny,
                        "default query returned allow");

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
        RequireEvaluation(notCopied,
                          Decision::Deny,
                          Flag(ReasonFlag::PrincipalNotCopied),
                          "borrowed principal detailed result mismatch");

        PermissionQuery missingHandle = CompleteRuntimeOwnedQuery();
        missingHandle.PrincipalValue.Handle = 0;
        RequireDecision(EvaluatePermissionQuery(missingHandle),
                        Decision::Deny,
                        "missing principal handle returned allow");
        RequireEvaluation(missingHandle,
                          Decision::Deny,
                          Flag(ReasonFlag::MissingPrincipalHandle),
                          "missing principal handle detailed result mismatch");

        PermissionQuery missingGeneration = CompleteRuntimeOwnedQuery();
        missingGeneration.PrincipalValue.HasGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingGeneration),
                        Decision::Unknown,
                        "missing principal generation returned allow");
        RequireEvaluation(missingGeneration,
                          Decision::Unknown,
                          Flag(ReasonFlag::MissingPrincipalGeneration),
                          "missing principal generation detailed result mismatch");

        PermissionQuery staleGeneration = CompleteRuntimeOwnedQuery();
        staleGeneration.PrincipalValue.CurrentGeneration = staleGeneration.PrincipalValue.Generation + 1;
        RequireDecision(EvaluatePermissionQuery(staleGeneration),
                        Decision::Unknown,
                        "stale principal generation returned allow");
        RequireEvaluation(staleGeneration,
                          Decision::Unknown,
                          Flag(ReasonFlag::StalePrincipalGeneration),
                          "stale principal generation detailed result mismatch");
    }

    void TestUnsupportedScopeFailsClosed()
    {
        PermissionQuery clusterStable = CompleteRuntimeOwnedQuery();
        clusterStable.PrincipalValue.Scope = PrincipalScope::ClusterStable;
        RequireDecision(EvaluatePermissionQuery(clusterStable),
                        Decision::Unknown,
                        "cluster-stable principal scope returned allow");
        RequireEvaluation(clusterStable,
                          Decision::Unknown,
                          Flag(ReasonFlag::UnsupportedPrincipalScope),
                          "unsupported scope detailed result mismatch");

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
        RequireEvaluation(processMismatch,
                          Decision::Unknown,
                          Flag(ReasonFlag::CrossProcessPrincipal),
                          "process mismatch detailed result mismatch");
    }

    void TestOwnerAndCapabilityFailClosed()
    {
        PermissionQuery missingOwner = CompleteRuntimeOwnedQuery();
        missingOwner.Owner.HasOwnerToken = false;
        RequireDecision(EvaluatePermissionQuery(missingOwner),
                        Decision::Deny,
                        "missing owner token returned allow");
        RequireEvaluation(missingOwner,
                          Decision::Deny,
                          Flag(ReasonFlag::MissingOwnerToken),
                          "missing owner token detailed result mismatch");

        PermissionQuery zeroOwnerToken = CompleteRuntimeOwnedQuery();
        zeroOwnerToken.Owner.OwnerTokenNonZero = false;
        RequireDecision(EvaluatePermissionQuery(zeroOwnerToken),
                        Decision::Deny,
                        "zero owner token returned allow");
        RequireEvaluation(zeroOwnerToken,
                          Decision::Deny,
                          Flag(ReasonFlag::ZeroOwnerToken),
                          "zero owner token detailed result mismatch");

        PermissionQuery unknownOwner = CompleteRuntimeOwnedQuery();
        unknownOwner.Owner.OwnerKnown = false;
        RequireDecision(EvaluatePermissionQuery(unknownOwner),
                        Decision::Deny,
                        "unknown owner token returned allow");
        RequireEvaluation(unknownOwner,
                          Decision::Deny,
                          Flag(ReasonFlag::UnknownOwner),
                          "unknown owner token detailed result mismatch");

        PermissionQuery unloadingOwner = CompleteRuntimeOwnedQuery();
        unloadingOwner.Owner.OwnerUnloading = true;
        RequireDecision(EvaluatePermissionQuery(unloadingOwner),
                        Decision::Deny,
                        "unloading owner token returned allow");
        RequireEvaluation(unloadingOwner,
                          Decision::Deny,
                          Flag(ReasonFlag::OwnerUnloading),
                          "unloading owner token detailed result mismatch");

        PermissionQuery missingCapability = CompleteRuntimeOwnedQuery();
        missingCapability.Owner.HasCapability = false;
        RequireDecision(EvaluatePermissionQuery(missingCapability),
                        Decision::Deny,
                        "missing capability returned allow");
        RequireEvaluation(missingCapability,
                          Decision::Deny,
                          Flag(ReasonFlag::MissingCapability),
                          "missing capability detailed result mismatch");
    }

    void TestActionAndResourceScopeFailClosed()
    {
        PermissionQuery missingAction = CompleteRuntimeOwnedQuery();
        missingAction.Text.Action = nullptr;
        missingAction.Text.ActionSize = 10;
        RequireDecision(EvaluatePermissionQuery(missingAction),
                        Decision::Deny,
                        "missing copied action returned allow");
        RequireEvaluation(missingAction,
                          Decision::Deny,
                          Flag(ReasonFlag::MalformedQueryText),
                          "missing copied action detailed result mismatch");

        PermissionQuery emptyAction = CompleteRuntimeOwnedQuery();
        emptyAction.Text.Action = "";
        emptyAction.Text.ActionSize = 0;
        RequireDecision(EvaluatePermissionQuery(emptyAction),
                        Decision::Deny,
                        "empty action returned allow");

        PermissionQuery oversizedAction = CompleteRuntimeOwnedQuery();
        oversizedAction.Text.ActionSize = 129;
        RequireDecision(EvaluatePermissionQuery(oversizedAction),
                        Decision::Deny,
                        "oversized action returned allow");
        RequireEvaluation(oversizedAction,
                          Decision::Deny,
                          Flag(ReasonFlag::MalformedQueryText),
                          "oversized action detailed result mismatch");

        PermissionQuery missingResourceScope = CompleteRuntimeOwnedQuery();
        missingResourceScope.Text.ResourceScope = nullptr;
        missingResourceScope.Text.ResourceScopeSize = 1;
        RequireDecision(EvaluatePermissionQuery(missingResourceScope),
                        Decision::Deny,
                        "missing copied resource scope returned allow");
        RequireEvaluation(missingResourceScope,
                          Decision::Deny,
                          Flag(ReasonFlag::MalformedQueryText),
                          "missing copied resource scope detailed result mismatch");

        PermissionQuery oversizedResourceScope = CompleteRuntimeOwnedQuery();
        oversizedResourceScope.Text.ResourceScope = "ark:scope";
        oversizedResourceScope.Text.ResourceScopeSize = 257;
        RequireDecision(EvaluatePermissionQuery(oversizedResourceScope),
                        Decision::Deny,
                        "oversized resource scope returned allow");
        RequireEvaluation(oversizedResourceScope,
                          Decision::Deny,
                          Flag(ReasonFlag::MalformedQueryText),
                          "oversized resource scope detailed result mismatch");

        PermissionQuery scoped = CompleteRuntimeOwnedQuery();
        scoped.Text.ResourceScope = "ark:global";
        scoped.Text.ResourceScopeSize = 10;
        RequireDecision(EvaluatePermissionQuery(scoped),
                        Decision::Allow,
                        "well-formed copied action and resource scope was not allowed");

        Require(HasWellFormedCopiedQueryText(scoped.Text),
                "well-formed copied query text helper rejected scoped query");
    }

    void TestOwnerProvenanceAndScopeMustAllBeValidForAllow()
    {
        PermissionQuery processLocal = CompleteRuntimeOwnedQuery();
        processLocal.PrincipalValue.Scope = PrincipalScope::ProcessLocal;
        RequireDecision(EvaluatePermissionQuery(processLocal),
                        Decision::Allow,
                        "complete process-local runtime-owned query was not allowed");

        PermissionQuery missingOwnerWithValidScopeAndProvenance = processLocal;
        missingOwnerWithValidScopeAndProvenance.Owner.HasOwnerToken = false;
        RequireDecision(EvaluatePermissionQuery(missingOwnerWithValidScopeAndProvenance),
                        Decision::Deny,
                        "valid scope and provenance authorized without owner token");

        PermissionQuery unsupportedScopeWithValidOwnerAndProvenance = processLocal;
        unsupportedScopeWithValidOwnerAndProvenance.PrincipalValue.Scope = PrincipalScope::ClusterStable;
        RequireDecision(EvaluatePermissionQuery(unsupportedScopeWithValidOwnerAndProvenance),
                        Decision::Unknown,
                        "valid owner token and provenance authorized unsupported scope");

        PermissionQuery missingProvenanceWithValidOwnerAndScope = processLocal;
        missingProvenanceWithValidOwnerAndScope.Provenance.HasPolicyEpoch = false;
        RequireDecision(EvaluatePermissionQuery(missingProvenanceWithValidOwnerAndScope),
                        Decision::Unknown,
                        "valid owner token and scope authorized missing provenance");

        PermissionQuery selfAttestedWithValidOwnerAndScope = processLocal;
        selfAttestedWithValidOwnerAndScope.Provenance.SuppliedByPlugin = true;
        RequireDecision(EvaluatePermissionQuery(selfAttestedWithValidOwnerAndScope),
                        Decision::Deny,
                        "valid owner token and scope authorized plugin-supplied provenance");
    }

    void TestOperatorConfigAllowCapabilityRequiresRuntimePrincipalAndAuthorityPromotion()
    {
        PermissionQuery operatorConfigWithValidPrincipal = CompleteRuntimeOwnedQuery();
        operatorConfigWithValidPrincipal.Provenance.Authority = PolicyAuthority::OperatorConfig;
        RequireDecision(EvaluatePermissionQuery(operatorConfigWithValidPrincipal),
                        Decision::Unknown,
                        "operator-config authority authorized with valid principal generation, scope, and capability");

        PermissionQuery operatorConfigMissingGeneration = operatorConfigWithValidPrincipal;
        operatorConfigMissingGeneration.PrincipalValue.HasGeneration = false;
        RequireDecision(EvaluatePermissionQuery(operatorConfigMissingGeneration),
                        Decision::Unknown,
                        "operator-config authority authorized without principal generation");

        PermissionQuery operatorConfigUnsupportedScope = operatorConfigWithValidPrincipal;
        operatorConfigUnsupportedScope.PrincipalValue.Scope = PrincipalScope::ClusterStable;
        RequireDecision(EvaluatePermissionQuery(operatorConfigUnsupportedScope),
                        Decision::Unknown,
                        "operator-config authority authorized unsupported principal scope");
    }

    void TestPolicyProvenanceFailsClosed()
    {
        PermissionQuery missingSource = CompleteRuntimeOwnedQuery();
        missingSource.Provenance.HasSourceId = false;
        RequireDecision(EvaluatePermissionQuery(missingSource),
                        Decision::Unknown,
                        "missing policy source returned allow");
        RequireEvaluation(missingSource,
                          Decision::Unknown,
                          Flag(ReasonFlag::MissingPolicySourceId),
                          "missing policy source detailed result mismatch");

        PermissionQuery missingSourceGeneration = CompleteRuntimeOwnedQuery();
        missingSourceGeneration.Provenance.HasSourceGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingSourceGeneration),
                        Decision::Unknown,
                        "missing policy source generation returned allow");
        RequireEvaluation(missingSourceGeneration,
                          Decision::Unknown,
                          Flag(ReasonFlag::MissingPolicySourceGeneration),
                          "missing policy source generation detailed result mismatch");

        PermissionQuery missingEpoch = CompleteRuntimeOwnedQuery();
        missingEpoch.Provenance.HasPolicyEpoch = false;
        RequireDecision(EvaluatePermissionQuery(missingEpoch),
                        Decision::Unknown,
                        "missing policy epoch returned allow");
        RequireEvaluation(missingEpoch,
                          Decision::Unknown,
                          Flag(ReasonFlag::MissingPolicyEpoch),
                          "missing policy epoch detailed result mismatch");

        PermissionQuery missingAuthorityGeneration = CompleteRuntimeOwnedQuery();
        missingAuthorityGeneration.Provenance.HasAuthorityGeneration = false;
        RequireDecision(EvaluatePermissionQuery(missingAuthorityGeneration),
                        Decision::Unknown,
                        "missing authority generation returned allow");
        RequireEvaluation(missingAuthorityGeneration,
                          Decision::Unknown,
                          Flag(ReasonFlag::MissingAuthorityGeneration),
                          "missing authority generation detailed result mismatch");

        PermissionQuery sourceMismatch = CompleteRuntimeOwnedQuery();
        sourceMismatch.Provenance.SourceGenerationMatches = false;
        RequireDecision(EvaluatePermissionQuery(sourceMismatch),
                        Decision::Unknown,
                        "policy source generation mismatch returned allow");
        RequireEvaluation(sourceMismatch,
                          Decision::Unknown,
                          Flag(ReasonFlag::PolicySourceGenerationMismatch),
                          "policy source generation mismatch detailed result mismatch");

        PermissionQuery authorityMismatch = CompleteRuntimeOwnedQuery();
        authorityMismatch.Provenance.AuthorityGenerationMatches = false;
        RequireDecision(EvaluatePermissionQuery(authorityMismatch),
                        Decision::Unknown,
                        "authority generation mismatch returned allow");
        RequireEvaluation(authorityMismatch,
                          Decision::Unknown,
                          Flag(ReasonFlag::AuthorityGenerationMismatch),
                          "authority generation mismatch detailed result mismatch");
    }

    void TestPluginSuppliedProvenanceFailsClosed()
    {
        PermissionQuery pluginAuthority = CompleteRuntimeOwnedQuery();
        pluginAuthority.Provenance.Authority = PolicyAuthority::PluginSupplied;
        RequireDecision(EvaluatePermissionQuery(pluginAuthority),
                        Decision::Deny,
                        "plugin-supplied authority returned allow");
        RequireEvaluation(pluginAuthority,
                          Decision::Deny,
                          Flag(ReasonFlag::PluginSuppliedProvenance),
                          "plugin-supplied authority detailed result mismatch");

        PermissionQuery selfAttested = CompleteRuntimeOwnedQuery();
        selfAttested.Provenance.SuppliedByPlugin = true;
        RequireDecision(EvaluatePermissionQuery(selfAttested),
                        Decision::Deny,
                        "plugin-self-attested provenance returned allow");
        RequireEvaluation(selfAttested,
                          Decision::Deny,
                          Flag(ReasonFlag::PluginSuppliedProvenance),
                          "plugin-self-attested provenance detailed result mismatch");
    }

    void TestRateLimitAndAuditFailuresFailClosed()
    {
        PermissionQuery rateLimited = CompleteRuntimeOwnedQuery();
        rateLimited.Abuse.RateLimitOk = false;
        RequireDecision(EvaluatePermissionQuery(rateLimited),
                        Decision::Deny,
                        "rate-limit failure returned allow");
        RequireEvaluation(rateLimited,
                          Decision::Deny,
                          Flag(ReasonFlag::RateLimited),
                          "rate-limit detailed result mismatch");

        PermissionQuery auditFailed = CompleteRuntimeOwnedQuery();
        auditFailed.Abuse.AuditOk = false;
        RequireDecision(EvaluatePermissionQuery(auditFailed),
                        Decision::Unknown,
                        "audit failure returned allow");
        RequireEvaluation(auditFailed,
                          Decision::Unknown,
                          Flag(ReasonFlag::AuditUnavailable),
                          "audit failure detailed result mismatch");
    }
}

int main()
{
    TestDetailedEvaluationPreservesWrapperDecision();
    TestAllowsOnlyCompleteRuntimeOwnedCopiedPrincipal();
    TestPrincipalGenerationFailsClosed();
    TestUnsupportedScopeFailsClosed();
    TestOwnerAndCapabilityFailClosed();
    TestActionAndResourceScopeFailClosed();
    TestOwnerProvenanceAndScopeMustAllBeValidForAllow();
    TestOperatorConfigAllowCapabilityRequiresRuntimePrincipalAndAuthorityPromotion();
    TestPolicyProvenanceFailsClosed();
    TestPluginSuppliedProvenanceFailsClosed();
    TestRateLimitAndAuditFailuresFailClosed();

    std::cout << "PermissionsAdminDecisionModelTests passed\n";
    return 0;
}
