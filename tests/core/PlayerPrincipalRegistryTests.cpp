#include "core/PlayerPrincipalRegistry.h"

#ifndef OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS
#error PlayerPrincipalRegistry tests must explicitly enable internal test hooks.
#endif

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <unordered_set>
#include <vector>

namespace
{
    using Obelisk::Core::PlayerPrincipalInvalidationFlag;
    using Obelisk::Core::PlayerPrincipalInvalidationFlags;
    using Obelisk::Core::PlayerPrincipalInvalidationReason;
    using Obelisk::Core::PlayerPrincipalLookupStatus;
    using Obelisk::Core::PlayerPrincipalRegistry;
    using Obelisk::Core::PlayerPrincipalToken;

    static_assert(std::is_trivially_copyable_v<PlayerPrincipalToken>,
                  "principal tokens must stay copy-only internal values");

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    constexpr PlayerPrincipalInvalidationFlags Flag(PlayerPrincipalInvalidationReason reason)
    {
        return PlayerPrincipalInvalidationFlag(reason);
    }

    void TestAllocatedPrincipalIsNonZeroAndValid()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();

        Require(token.Handle != 0, "allocated principal returned zero handle");
        Require(token.Generation != 0, "allocated principal returned zero generation");
        Require(token.RegistryId != 0, "allocated principal returned zero registry id");
        Require(registry.Validate(token), "allocated principal did not validate");

        const auto lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Valid,
                "allocated principal lookup was not valid");
        Require(lookup.Live, "allocated principal lookup was not live");
        Require(lookup.CurrentGeneration == token.Generation,
                "allocated principal generation mismatch");
        Require(lookup.CurrentRegistryId == token.RegistryId,
                "allocated principal registry id mismatch");
        Require(registry.LiveCount() == 1, "allocated principal live count mismatch");

        Require(!registry.Validate({0, token.Generation, token.RegistryId}), "zero principal handle validated");
        Require(registry.Lookup({0, token.Generation, token.RegistryId}).Status ==
                    PlayerPrincipalLookupStatus::ZeroHandle,
                "zero principal handle did not report zero-handle status");
        Require(!registry.Validate({token.Handle, 0, token.RegistryId}),
                "zero principal generation validated");
        Require(registry.Lookup({token.Handle, 0, token.RegistryId}).Status ==
                    PlayerPrincipalLookupStatus::ZeroGeneration,
                "zero principal generation did not report zero-generation status");
        Require(!registry.Validate({token.Handle, token.Generation, 0}),
                "zero principal registry id validated");
        Require(registry.Lookup({token.Handle, token.Generation, 0}).Status ==
                    PlayerPrincipalLookupStatus::ZeroRegistryId,
                "zero principal registry id did not report zero-registry-id status");
        Require(!registry.Validate({777, token.Generation, token.RegistryId}),
                "unknown principal handle validated");
    }

    void TestForeignRegistryTokenCollisionFailsClosed()
    {
        PlayerPrincipalRegistry sourceRegistry;
        PlayerPrincipalRegistry foreignRegistry;

        const PlayerPrincipalToken source = sourceRegistry.AllocatePrincipal();
        const PlayerPrincipalToken foreign = foreignRegistry.AllocatePrincipal();
        Require(source.HasValidShape(), "source registry fixture did not allocate principal");
        Require(foreign.HasValidShape(), "foreign registry fixture did not allocate principal");
        Require(source.Handle == foreign.Handle,
                "foreign registry fixture did not allocate a matching handle shape");
        Require(source.Generation == foreign.Generation,
                "foreign registry fixture did not allocate a matching generation shape");
        Require(source.RegistryId != foreign.RegistryId,
                "separate registries reused the same registry id");

        const auto foreignLookup = foreignRegistry.Lookup(source);
        Require(foreignLookup.Status == PlayerPrincipalLookupStatus::RegistryMismatch,
                "foreign registry accepted a colliding source token");
        Require(foreignLookup.RequestedRegistryId == source.RegistryId,
                "foreign registry lookup lost requested registry id");
        Require(foreignLookup.CurrentRegistryId == foreign.RegistryId,
                "foreign registry lookup lost current registry id");
        Require(!foreignRegistry.Validate(source),
                "foreign registry validated a colliding source token");
        Require(!foreignRegistry.LogoutPrincipal(source),
                "foreign registry invalidated a colliding source token");
        Require(foreignRegistry.Validate(foreign),
                "foreign registry collision invalidated its own principal");
        Require(sourceRegistry.Validate(source),
                "foreign registry collision invalidated the source principal");
        Require(sourceRegistry.Lookup(foreign).Status == PlayerPrincipalLookupStatus::RegistryMismatch,
                "source registry accepted a colliding foreign token");
    }

    void TestForeignRegistryTokenCannotReactivateCollision()
    {
        PlayerPrincipalRegistry sourceRegistry;
        PlayerPrincipalRegistry foreignRegistry;

        const PlayerPrincipalToken source = sourceRegistry.AllocatePrincipal();
        const PlayerPrincipalToken foreign = foreignRegistry.AllocatePrincipal();
        Require(source.HasValidShape(), "source reactivation fixture did not allocate principal");
        Require(foreign.HasValidShape(), "foreign reactivation fixture did not allocate principal");
        Require(source.Handle == foreign.Handle,
                "foreign reactivation fixture did not allocate a matching handle shape");
        Require(source.Generation == foreign.Generation,
                "foreign reactivation fixture did not allocate a matching generation shape");
        Require(source.RegistryId != foreign.RegistryId,
                "foreign reactivation fixture reused the same registry id");

        Require(foreignRegistry.InvalidatePrincipal(
                    foreign,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "foreign reactivation fixture could not invalidate principal");
        Require(!foreignRegistry.ReactivatePrincipal(source).HasValidShape(),
                "foreign registry token reactivated a colliding principal");

        const auto afterForeignReplay = foreignRegistry.Lookup(foreign);
        Require(afterForeignReplay.Status == PlayerPrincipalLookupStatus::Invalidated,
                "foreign token replay changed invalidated principal status");
        Require(afterForeignReplay.InvalidationReasons ==
                    Flag(PlayerPrincipalInvalidationReason::Reconnect),
                "foreign token replay changed invalidation reason");
        Require(!foreignRegistry.Validate(foreign),
                "foreign token replay validated invalidated principal");
        Require(sourceRegistry.Validate(source),
                "foreign token replay changed source registry principal");

        const PlayerPrincipalToken reactivated = foreignRegistry.ReactivatePrincipal(foreign);
        Require(reactivated.Handle == foreign.Handle,
                "matching registry token did not reactivate invalidated principal");
        Require(reactivated.Generation == foreign.Generation + 1,
                "matching registry token did not increment generation");
        Require(foreignRegistry.Validate(reactivated),
                "matching registry token did not validate");
    }

    void TestInvalidationReasonFlagsAndDuplicateLogout()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();
        const PlayerPrincipalInvalidationFlags reasons =
            Flag(PlayerPrincipalInvalidationReason::Logout) |
            Flag(PlayerPrincipalInvalidationReason::RuntimeReset);

        Require(registry.InvalidatePrincipal(token, reasons),
                "principal invalidation failed");
        Require(!registry.Validate(token), "invalidated principal still validated");

        auto lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "invalidated principal lookup did not report invalidated");
        Require(!lookup.Live, "invalidated principal lookup was live");
        Require(lookup.InvalidationReasons == reasons,
                "principal invalidation reason flags were not preserved");
        Require(registry.LiveCount() == 0, "principal invalidation live count mismatch");
        Require(registry.RetainedInvalidatedCount() == 1,
                "principal invalidation retained count mismatch");

        Require(!registry.LogoutPrincipal(token), "duplicate logout succeeded");
        lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "duplicate logout changed lookup status");
        Require(lookup.InvalidationReasons == reasons,
                "duplicate logout changed invalidation reason flags");
    }

    void TestDuplicateTerminalInvalidationDoesNotChangeRetainedPrincipal()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();
        Require(token.HasValidShape(), "duplicate terminal fixture did not allocate principal");

        const PlayerPrincipalInvalidationFlags logoutReason =
            Flag(PlayerPrincipalInvalidationReason::Logout);
        Require(registry.InvalidatePrincipal(token, logoutReason),
                "initial terminal invalidation failed");

        Require(!registry.InvalidatePrincipal(token,
                                              Flag(PlayerPrincipalInvalidationReason::RuntimeReset)),
                "duplicate terminal event replaced logout with runtime-reset");
        Require(!registry.InvalidatePrincipal(
                    token,
                    Flag(PlayerPrincipalInvalidationReason::Logout) |
                        Flag(PlayerPrincipalInvalidationReason::Superseded)),
                "duplicate terminal event widened retained invalidation reasons");

        const auto lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "duplicate terminal replay changed retained principal status");
        Require(lookup.InvalidationReasons == logoutReason,
                "duplicate terminal replay changed retained invalidation reason");
        Require(!lookup.Live, "duplicate terminal replay made retained principal live");
        Require(registry.LiveCount() == 0,
                "duplicate terminal replay changed live count");
        Require(registry.RetainedInvalidatedCount() == 1,
                "duplicate terminal replay changed retained invalidated count");
    }

    void TestInvalidLogoutTokensDoNotInvalidateLivePrincipal()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();
        Require(token.HasValidShape(), "invalid logout fixture did not allocate principal");

        Require(!registry.InvalidatePrincipal(token, 0),
                "zero invalidation reason mask invalidated a live principal");
        Require(!registry.LogoutPrincipal({0, token.Generation, token.RegistryId}),
                "zero-handle logout succeeded");
        Require(!registry.LogoutPrincipal({token.Handle, 0, token.RegistryId}),
                "zero-generation logout succeeded");
        Require(!registry.LogoutPrincipal({token.Handle + 1000, token.Generation, token.RegistryId}),
                "unknown-handle logout succeeded");

        const auto lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Valid,
                "invalid logout token changed live principal status");
        Require(lookup.Live, "invalid logout token changed live principal state");
        Require(lookup.InvalidationReasons == 0,
                "invalid logout token added invalidation reasons");
        Require(registry.Validate(token), "invalid logout token invalidated live principal");
        Require(registry.LiveCount() == 1, "invalid logout token changed live count");
    }

    void TestUnknownInvalidationReasonBitsRejected()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();
        Require(token.HasValidShape(), "unknown-reason fixture did not allocate principal");

        constexpr PlayerPrincipalInvalidationFlags unknownReason = 1ull << 63;
        Require(!registry.InvalidatePrincipal(token, unknownReason),
                "unknown invalidation reason invalidated a live principal");
        Require(!registry.InvalidatePrincipal(
                    token,
                    Flag(PlayerPrincipalInvalidationReason::Logout) | unknownReason),
                "mixed known/unknown invalidation reason invalidated a live principal");

        const auto lookup = registry.Lookup(token);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Valid,
                "unknown invalidation reason changed principal status");
        Require(lookup.InvalidationReasons == 0,
                "unknown invalidation reason was retained");
        Require(registry.Validate(token), "unknown invalidation reason invalidated principal");
        Require(registry.LiveCount() == 1,
                "unknown invalidation reason changed live count");
    }

    void TestStaleGenerationRejectedAfterReconnect()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "reconnect invalidation before reconnect failed");
        Require(registry.Lookup(first).Status == PlayerPrincipalLookupStatus::Invalidated,
                "reconnect-invalidated principal was not invalidated");

        const PlayerPrincipalToken reconnected = registry.ReactivatePrincipal(first);
        Require(reconnected.Handle == first.Handle, "reconnect did not reuse the requested handle");
        Require(reconnected.Generation == first.Generation + 1,
                "reconnect did not increment principal generation");
        Require(registry.Validate(reconnected), "reconnected principal did not validate");
        Require(registry.RetainedInvalidatedCount() == 0,
                "reconnected principal remained counted as retained invalidated");

        const auto stale = registry.Lookup(first);
        Require(stale.Status == PlayerPrincipalLookupStatus::StaleGeneration,
                "old principal generation was not rejected as stale");
        Require(stale.CurrentGeneration == reconnected.Generation,
                "stale lookup did not expose current generation");
        Require(!registry.Validate(first), "stale principal generation validated");
        Require(registry.Lookup(reconnected).InvalidationReasons == 0,
                "reconnected principal retained invalidation reasons");
    }

    void TestStaleLogoutDoesNotInvalidateReconnectedPrincipal()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "reconnect invalidation before stale logout fixture failed");
        const PlayerPrincipalToken reconnected = registry.ReactivatePrincipal(first);
        Require(reconnected.HasValidShape(), "stale logout fixture did not reactivate handle");

        Require(!registry.LogoutPrincipal(first), "stale logout succeeded");

        const auto stale = registry.Lookup(first);
        Require(stale.Status == PlayerPrincipalLookupStatus::StaleGeneration,
                "stale logout changed old token status");
        Require(stale.CurrentGeneration == reconnected.Generation,
                "stale logout changed current generation");

        const auto current = registry.Lookup(reconnected);
        Require(current.Status == PlayerPrincipalLookupStatus::Valid,
                "stale logout invalidated reconnected principal");
        Require(current.Live, "stale logout changed reconnected principal live state");
        Require(current.InvalidationReasons == 0,
                "stale logout changed reconnected principal invalidation reasons");
        Require(registry.LiveCount() == 1, "stale logout changed live count");
    }

    void TestStaleTerminalInvalidationDoesNotMutateReconnectedPrincipal()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "reconnect invalidation before stale terminal fixture failed");
        const PlayerPrincipalToken reconnected = registry.ReactivatePrincipal(first);
        Require(reconnected.HasValidShape(),
                "stale terminal fixture did not reactivate handle");

        Require(!registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Logout) |
                        Flag(PlayerPrincipalInvalidationReason::RuntimeReset)),
                "stale terminal event invalidated the current generation");

        const auto stale = registry.Lookup(first);
        Require(stale.Status == PlayerPrincipalLookupStatus::StaleGeneration,
                "stale terminal replay changed old generation status");
        Require(stale.CurrentGeneration == reconnected.Generation,
                "stale terminal replay changed current generation");

        const auto current = registry.Lookup(reconnected);
        Require(current.Status == PlayerPrincipalLookupStatus::Valid,
                "stale terminal replay invalidated reconnected principal");
        Require(current.Live, "stale terminal replay changed current live state");
        Require(current.InvalidationReasons == 0,
                "stale terminal replay added invalidation reasons to current principal");
        Require(registry.LiveCount() == 1,
                "stale terminal replay changed live count");
        Require(registry.RetainedInvalidatedCount() == 0,
                "stale terminal replay changed retained invalidated count");
    }

    void TestStaleTokenCannotReactivateLaterInvalidatedGeneration()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "first reconnect invalidation before token replay fixture failed");
        const PlayerPrincipalToken second = registry.ReactivatePrincipal(first);
        Require(second.Handle == first.Handle,
                "first reactivation did not reuse principal handle");
        Require(second.Generation == first.Generation + 1,
                "first reactivation did not increment generation");
        Require(registry.Validate(second),
                "first reactivation did not validate");

        Require(registry.InvalidatePrincipal(
                    second,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "second reconnect invalidation before stale replay failed");
        Require(!registry.ReactivatePrincipal(first).HasValidShape(),
                "stale token reactivated a later invalidated generation");

        auto lookup = registry.Lookup(first);
        Require(lookup.Status == PlayerPrincipalLookupStatus::StaleGeneration,
                "stale replay changed old generation status");
        Require(lookup.CurrentGeneration == second.Generation,
                "stale replay changed current generation");
        lookup = registry.Lookup(second);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "stale replay changed current invalidated status");
        Require(lookup.InvalidationReasons == Flag(PlayerPrincipalInvalidationReason::Reconnect),
                "stale replay changed current invalidation reason");
        Require(registry.LiveCount() == 0,
                "stale replay changed live count before valid reactivation");

        const PlayerPrincipalToken third = registry.ReactivatePrincipal(second);
        Require(third.Handle == second.Handle,
                "current token did not reactivate after stale replay rejection");
        Require(third.Generation == second.Generation + 1,
                "current token did not increment generation after stale replay rejection");
        Require(registry.Validate(third),
                "current token did not validate after stale replay rejection");
        Require(registry.LiveCount() == 1,
                "valid reactivation after stale replay changed live count");
    }

    void TestReconnectReasonCanReactivateAndPlainLogoutCannot()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken logout = registry.AllocatePrincipal();
        const PlayerPrincipalToken reconnect = registry.AllocatePrincipal();
        const PlayerPrincipalToken logoutReconnect = registry.AllocatePrincipal();
        Require(logout.HasValidShape(), "logout reactivation fixture did not allocate principal");
        Require(reconnect.HasValidShape(), "reconnect reactivation fixture did not allocate principal");
        Require(logoutReconnect.HasValidShape(),
                "logout+reconnect reactivation fixture did not allocate principal");

        Require(registry.LogoutPrincipal(logout), "logout invalidation before reactivation failed");
        Require(!registry.ReactivatePrincipal(logout).HasValidShape(),
                "plain logout invalidation reactivated without reconnect reason");
        auto lookup = registry.Lookup(logout);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "plain logout reactivation attempt changed lookup status");
        Require(lookup.InvalidationReasons == Flag(PlayerPrincipalInvalidationReason::Logout),
                "plain logout reactivation attempt changed invalidation reason");

        Require(registry.InvalidatePrincipal(
                    reconnect,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "reconnect invalidation before reactivation failed");
        const PlayerPrincipalToken afterReconnect = registry.ReactivatePrincipal(reconnect);
        Require(afterReconnect.Handle == reconnect.Handle,
                "reconnect-invalidated principal did not reactivate with same handle");
        Require(afterReconnect.Generation == reconnect.Generation + 1,
                "reconnect-invalidated principal did not increment generation");
        Require(registry.Validate(afterReconnect),
                "reconnect-reactivated principal did not validate");

        Require(registry.InvalidatePrincipal(
                    logoutReconnect,
                    Flag(PlayerPrincipalInvalidationReason::Logout) |
                        Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "logout+reconnect invalidation before reactivation failed");
        const PlayerPrincipalToken afterLogoutReconnect =
            registry.ReactivatePrincipal(logoutReconnect);
        Require(afterLogoutReconnect.Handle == logoutReconnect.Handle,
                "logout+reconnect invalidated principal did not reactivate with same handle");
        Require(afterLogoutReconnect.Generation == logoutReconnect.Generation + 1,
                "logout+reconnect invalidated principal did not increment generation");
        Require(registry.Validate(afterLogoutReconnect),
                "logout+reconnect reactivated principal did not validate");
        Require(registry.LiveCount() == 2, "reactivation safe-reason live count mismatch");
    }

    void TestTerminalInvalidationReasonsCannotReactivate()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken runtimeReset = registry.AllocatePrincipal();
        const PlayerPrincipalToken superseded = registry.AllocatePrincipal();
        const PlayerPrincipalToken mixed = registry.AllocatePrincipal();
        Require(runtimeReset.HasValidShape(), "runtime-reset fixture did not allocate principal");
        Require(superseded.HasValidShape(), "superseded fixture did not allocate principal");
        Require(mixed.HasValidShape(), "mixed terminal fixture did not allocate principal");

        Require(registry.InvalidatePrincipal(
                    runtimeReset,
                    Flag(PlayerPrincipalInvalidationReason::RuntimeReset)),
                "runtime-reset invalidation failed");
        Require(registry.InvalidatePrincipal(
                    superseded,
                    Flag(PlayerPrincipalInvalidationReason::Superseded)),
                "superseded invalidation failed");
        Require(registry.InvalidatePrincipal(
                    mixed,
                    Flag(PlayerPrincipalInvalidationReason::Logout) |
                        Flag(PlayerPrincipalInvalidationReason::RuntimeReset)),
                "mixed terminal invalidation failed");

        Require(!registry.ReactivatePrincipal(runtimeReset).HasValidShape(),
                "runtime-reset invalidated principal reactivated");
        Require(!registry.ReactivatePrincipal(superseded).HasValidShape(),
                "superseded principal reactivated");
        Require(!registry.ReactivatePrincipal(mixed).HasValidShape(),
                "mixed terminal invalidated principal reactivated");

        auto lookup = registry.Lookup(runtimeReset);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "runtime-reset reactivation attempt changed lookup status");
        Require(lookup.InvalidationReasons == Flag(PlayerPrincipalInvalidationReason::RuntimeReset),
                "runtime-reset reactivation attempt changed invalidation reason");
        lookup = registry.Lookup(superseded);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "superseded reactivation attempt changed lookup status");
        Require(lookup.InvalidationReasons == Flag(PlayerPrincipalInvalidationReason::Superseded),
                "superseded reactivation attempt changed invalidation reason");
        lookup = registry.Lookup(mixed);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "mixed terminal reactivation attempt changed lookup status");
        Require(lookup.InvalidationReasons ==
                    (Flag(PlayerPrincipalInvalidationReason::Logout) |
                     Flag(PlayerPrincipalInvalidationReason::RuntimeReset)),
                "mixed terminal reactivation attempt changed invalidation reasons");
        Require(registry.LiveCount() == 0,
                "terminal reactivation attempts changed live count");
    }

    void TestLiveHandleIsNotReused()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();

        registry.SetNextHandleForTesting(first.Handle);
        const PlayerPrincipalToken second = registry.AllocatePrincipal();

        Require(second.Handle != 0, "second principal allocation failed");
        Require(second.Handle != first.Handle, "allocator reused a live principal handle");
        Require(registry.ReactivatePrincipal(first).Handle == 0,
                "reactivation reused a live principal handle");
        Require(registry.Validate(first), "first live principal stopped validating");
        Require(registry.Validate(second), "second live principal did not validate");
        Require(registry.LiveCount() == 2, "live-handle reuse test live count mismatch");
    }

    void TestHandleOverflowFailsClosed()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken first = registry.AllocatePrincipal();
        Require(first.Handle == 1, "first principal allocation did not use initial handle");

        registry.SetNextHandleForTesting(std::numeric_limits<uint64_t>::max());

        const PlayerPrincipalToken last = registry.AllocatePrincipal();
        Require(last.Handle == std::numeric_limits<uint64_t>::max(),
                "max handle allocation did not return max handle");
        Require(last.Generation == 1, "max handle allocation returned wrong generation");
        Require(registry.Validate(last), "max handle principal did not validate");

        const PlayerPrincipalToken exhausted = registry.AllocatePrincipal();
        Require(exhausted.Handle == 0 && exhausted.Generation == 0,
                "handle counter overflow wrapped instead of failing closed");
        Require(!registry.Validate(exhausted), "overflow failure token validated");
        Require(registry.Validate(first), "overflow failure invalidated first principal");
        Require(registry.Validate(last), "overflow failure invalidated max-handle principal");
        Require(registry.LiveCount() == 2, "overflow failure changed live count");

        registry.SetNextHandleForTesting(0);
        const PlayerPrincipalToken zeroNext = registry.AllocatePrincipal();
        Require(zeroNext.Handle == 0 && zeroNext.Generation == 0,
                "zero next-handle test hook did not fail closed");
    }

    void TestGenerationOverflowFailsClosed()
    {
        PlayerPrincipalRegistry registry;
        const PlayerPrincipalToken token = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    token,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "reconnect invalidation before generation overflow setup failed");
        Require(registry.SetGenerationForTesting(token.Handle, std::numeric_limits<uint64_t>::max()),
                "could not set generation overflow test fixture");

        const PlayerPrincipalToken saturated{
            token.Handle,
            std::numeric_limits<uint64_t>::max(),
            token.RegistryId,
        };
        auto lookup = registry.Lookup(saturated);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "saturated generation fixture was not invalidated");
        Require(lookup.CurrentGeneration == std::numeric_limits<uint64_t>::max(),
                "saturated generation fixture changed generation");

        const PlayerPrincipalToken reactivated = registry.ReactivatePrincipal(token);
        Require(reactivated.Handle == 0 && reactivated.Generation == 0,
                "generation overflow did not fail closed");

        lookup = registry.Lookup(saturated);
        Require(lookup.Status == PlayerPrincipalLookupStatus::Invalidated,
                "failed generation overflow reactivation changed status");
        Require(lookup.CurrentGeneration == std::numeric_limits<uint64_t>::max(),
                "failed generation overflow reactivation wrapped generation");
        Require(!registry.Validate(saturated), "saturated invalidated generation validated");
    }

    void TestConcurrentAllocationProducesUniqueValidTokens()
    {
        PlayerPrincipalRegistry registry;
        constexpr size_t kThreadCount = 4;
        constexpr size_t kPerThread = 128;

        std::mutex tokensMutex;
        std::vector<PlayerPrincipalToken> tokens;
        tokens.reserve(kThreadCount * kPerThread);

        std::vector<std::thread> threads;
        threads.reserve(kThreadCount);
        for (size_t threadIndex = 0; threadIndex < kThreadCount; ++threadIndex)
        {
            threads.emplace_back([&]() {
                std::vector<PlayerPrincipalToken> local;
                local.reserve(kPerThread);
                for (size_t i = 0; i < kPerThread; ++i)
                    local.push_back(registry.AllocatePrincipal());

                std::lock_guard<std::mutex> lock(tokensMutex);
                tokens.insert(tokens.end(), local.begin(), local.end());
            });
        }

        for (std::thread& thread : threads)
            thread.join();

        std::unordered_set<uint64_t> handles;
        for (const PlayerPrincipalToken& token : tokens)
        {
            Require(token.Handle != 0, "concurrent allocation returned zero handle");
            Require(token.Generation != 0, "concurrent allocation returned zero generation");
            Require(registry.Validate(token), "concurrent allocation produced invalid token");
            Require(handles.insert(token.Handle).second,
                    "concurrent allocation reused a live principal handle");
        }

        Require(tokens.size() == kThreadCount * kPerThread,
                "concurrent allocation returned wrong token count");
        Require(registry.LiveCount() == tokens.size(),
                "concurrent allocation live count mismatch");
    }

    void TestInvalidatedPrincipalRetentionIsBoundedWithoutHandleReuse()
    {
        PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(2);

        const PlayerPrincipalToken first = registry.AllocatePrincipal();
        const PlayerPrincipalToken second = registry.AllocatePrincipal();
        const PlayerPrincipalToken third = registry.AllocatePrincipal();

        Require(registry.LogoutPrincipal(first), "first logout failed");
        Require(registry.LogoutPrincipal(second), "second logout failed");
        Require(registry.LogoutPrincipal(third), "third logout failed");

        Require(registry.LiveCount() == 0, "bounded retention changed live count");
        Require(registry.RetainedInvalidatedCount() == 2,
                "bounded retention did not prune oldest invalidated principal");
        Require(registry.Lookup(first).Status == PlayerPrincipalLookupStatus::UnknownHandle,
                "oldest invalidated principal was not pruned");
        Require(registry.Lookup(second).Status == PlayerPrincipalLookupStatus::Invalidated,
                "second invalidated principal was pruned too early");
        Require(registry.Lookup(third).Status == PlayerPrincipalLookupStatus::Invalidated,
                "third invalidated principal was pruned too early");

        registry.SetNextHandleForTesting(first.Handle);
        const PlayerPrincipalToken afterPrune = registry.AllocatePrincipal();
        Require(afterPrune.Handle > third.Handle,
                "registry reused an evicted principal handle");
        Require(afterPrune.Generation == 1,
                "post-prune allocation returned wrong generation");
        Require(registry.Validate(afterPrune),
                "post-prune allocation did not validate");
        Require(registry.Lookup(first).Status == PlayerPrincipalLookupStatus::UnknownHandle,
                "evicted stale token became valid after post-prune allocation");
    }

    void TestZeroRetentionCapPrunesInvalidatedPrincipalWithoutHandleReuse()
    {
        PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0);

        const PlayerPrincipalToken token = registry.AllocatePrincipal();
        Require(token.HasValidShape(), "zero-retention fixture did not allocate principal");

        Require(registry.InvalidatePrincipal(
                    token,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "zero-retention invalidation failed");
        Require(registry.LiveCount() == 0, "zero-retention invalidation changed live count");
        Require(registry.RetainedInvalidatedCount() == 0,
                "zero-retention cap retained an invalidated principal");
        Require(registry.Lookup(token).Status == PlayerPrincipalLookupStatus::UnknownHandle,
                "zero-retention cap did not prune invalidated principal");
        Require(!registry.ReactivatePrincipal(token).HasValidShape(),
                "zero-retention pruned principal reactivated");

        registry.SetNextHandleForTesting(token.Handle);
        const PlayerPrincipalToken next = registry.AllocatePrincipal();
        Require(next.Handle > token.Handle,
                "zero-retention pruning allowed evicted handle reuse");
        Require(next.Generation == 1, "zero-retention post-prune allocation generation mismatch");
        Require(registry.Validate(next), "zero-retention post-prune allocation did not validate");
    }

    void TestRetiredSequenceWrapPrunesChronologicalOldest()
    {
        PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(2);
        registry.SetNextRetiredSequenceForTesting(std::numeric_limits<uint64_t>::max() - 1);

        const PlayerPrincipalToken first = registry.AllocatePrincipal();
        const PlayerPrincipalToken second = registry.AllocatePrincipal();
        const PlayerPrincipalToken afterWrap = registry.AllocatePrincipal();

        Require(registry.InvalidatePrincipal(
                    first,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "first wrap invalidation failed");
        Require(registry.InvalidatePrincipal(
                    second,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "second wrap invalidation failed");
        Require(registry.InvalidatePrincipal(
                    afterWrap,
                    Flag(PlayerPrincipalInvalidationReason::Reconnect)),
                "post-wrap invalidation failed");

        Require(registry.RetainedInvalidatedCount() == 2,
                "retired sequence wrap did not keep retained state bounded");
        Require(registry.Lookup(first).Status == PlayerPrincipalLookupStatus::UnknownHandle,
                "retired sequence wrap did not prune the chronological oldest principal");
        Require(registry.Lookup(second).Status == PlayerPrincipalLookupStatus::Invalidated,
                "retired sequence wrap pruned the max-sequence principal too early");
        Require(registry.Lookup(afterWrap).Status == PlayerPrincipalLookupStatus::Invalidated,
                "retired sequence wrap pruned the newest post-wrap principal");

        const PlayerPrincipalToken reactivated = registry.ReactivatePrincipal(afterWrap);
        Require(reactivated.Handle == afterWrap.Handle,
                "post-wrap retained principal did not reactivate");
        Require(reactivated.Generation == afterWrap.Generation + 1,
                "post-wrap reactivation did not increment generation");
        Require(registry.Validate(reactivated),
                "post-wrap reactivated principal did not validate");
        Require(registry.RetainedInvalidatedCount() == 1,
                "post-wrap reactivation retained invalidated count mismatch");
        Require(registry.LiveCount() == 1,
                "post-wrap reactivation live count mismatch");
    }
}

int main()
{
    TestAllocatedPrincipalIsNonZeroAndValid();
    TestForeignRegistryTokenCollisionFailsClosed();
    TestForeignRegistryTokenCannotReactivateCollision();
    TestInvalidationReasonFlagsAndDuplicateLogout();
    TestDuplicateTerminalInvalidationDoesNotChangeRetainedPrincipal();
    TestInvalidLogoutTokensDoNotInvalidateLivePrincipal();
    TestUnknownInvalidationReasonBitsRejected();
    TestStaleGenerationRejectedAfterReconnect();
    TestStaleLogoutDoesNotInvalidateReconnectedPrincipal();
    TestStaleTerminalInvalidationDoesNotMutateReconnectedPrincipal();
    TestStaleTokenCannotReactivateLaterInvalidatedGeneration();
    TestReconnectReasonCanReactivateAndPlainLogoutCannot();
    TestTerminalInvalidationReasonsCannotReactivate();
    TestLiveHandleIsNotReused();
    TestHandleOverflowFailsClosed();
    TestGenerationOverflowFailsClosed();
    TestConcurrentAllocationProducesUniqueValidTokens();
    TestInvalidatedPrincipalRetentionIsBoundedWithoutHandleReuse();
    TestZeroRetentionCapPrunesInvalidatedPrincipalWithoutHandleReuse();
    TestRetiredSequenceWrapPrunesChronologicalOldest();

    std::cout << "PlayerPrincipalRegistryTests passed\n";
    return 0;
}
