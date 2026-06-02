#include "hooks/ProcessEventTransferReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventTransferReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kServerTransferredPlayerConfirmationResultNameIndex = 2759;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kServerTransferredPlayerConfirmationResultObjectIndex = 10494;
    constexpr int32_t kBAcceptObjectIndex = 10495;
    constexpr int32_t kShooterPlayerControllerObjectIndex = 50;
    constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
    constexpr int32_t kBAcceptNameIndex = 21480;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint8_t kBAcceptBoolFieldSize = 0x01;
    constexpr uint8_t kBAcceptBoolByteOffset = 0x00;
    constexpr uint8_t kBAcceptBoolByteMask = 0x01;
    constexpr uint8_t kBAcceptBoolFieldMask = 0xff;

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
        size_t ReadCalls = 0;
    };

    bool RegionReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
        ++reader->ReadCalls;
        const auto* ptr = static_cast<const uint8_t*>(address);
        for (const Region& region : reader->Regions)
        {
            if (ptr < region.Start)
                continue;
            const size_t offset = static_cast<size_t>(ptr - region.Start);
            if (offset <= region.Size && size <= region.Size - offset)
                return true;
        }
        return false;
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("expected transfer reflection reader exception");
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    template <typename T, size_t N>
    void WriteAt(std::array<uint8_t, N>& buffer, size_t offset, const T& value)
    {
        Require(offset <= buffer.size() && sizeof(T) <= buffer.size() - offset, "test write out of bounds");
        std::memcpy(buffer.data() + offset, &value, sizeof(T));
    }

    template <size_t N>
    void WriteObject(std::array<uint8_t, N>& buffer,
                     int32_t nameIndex,
                     int32_t internalIndex,
                     const void* klass,
                     const void* outer)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const FNameValue name{nameIndex, 0};

        WriteAt(buffer, 0x00, vtable);
        WriteAt(buffer, 0x08, flags);
        WriteAt(buffer, 0x0c, internalIndex);
        WriteAt(buffer, 0x10, klass);
        WriteAt(buffer, 0x18, name);
        WriteAt(buffer, 0x20, outer);
    }

    template <size_t N>
    void WriteProperty(std::array<uint8_t, N>& buffer,
                       const void* next,
                       const void* owner,
                       const void* klass)
    {
        WriteObject(buffer, kBAcceptNameIndex, kBAcceptObjectIndex, klass, owner);

        const int32_t arrayDim = 1;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, int32_t{1});
        WriteAt(buffer, 0x38, kBoolInputPropertyFlags);
        WriteAt(buffer, 0x4c, int32_t{0});
        WriteAt(buffer, 0x70, kBAcceptBoolFieldSize);
        WriteAt(buffer, 0x71, kBAcceptBoolByteOffset);
        WriteAt(buffer, 0x72, kBAcceptBoolByteMask);
        WriteAt(buffer, 0x73, kBAcceptBoolFieldMask);
    }

    struct TransferFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> Property{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> FunctionClass{};
        std::array<uint8_t, 0x40> Outer{};
        std::array<uint8_t, 0x08> Params{};
        ReaderContext Context;

        MemoryReader Reader()
        {
            Context.Regions.clear();
            Context.Regions.push_back({Function.data(), Function.size()});
            Context.Regions.push_back({Property.data(), Property.size()});
            Context.Regions.push_back({BoolPropertyClass.data(), BoolPropertyClass.size()});
            Context.Regions.push_back({FunctionClass.data(), FunctionClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            Context.ReadCalls = 0;
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    const char* SupportedSha()
    {
        return kSupportedShooterGameServerSha256.data();
    }

    void BuildConfirmationResult(TransferFixture& fixture)
    {
        WriteObject(fixture.BoolPropertyClass,
                    kBoolPropertyClassNameIndex,
                    kBoolPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
        WriteObject(fixture.Outer,
                    kShooterPlayerControllerNameIndex,
                    kShooterPlayerControllerObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    kServerTransferredPlayerConfirmationResultNameIndex,
                    kServerTransferredPlayerConfirmationResultObjectIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());
        WriteProperty(fixture.Property, nullptr, fixture.Function.data(), fixture.BoolPropertyClass.data());

        WriteAt(fixture.Function, 0x38, fixture.Property.data());
        WriteAt(fixture.Function, 0x90, uint32_t{0x220cc0});
        WriteAt(fixture.Function, 0x96, uint16_t{1});
        WriteAt(fixture.Function, 0x98, uint16_t{0x01});
        WriteAt(fixture.Function, 0x9a, uint16_t{0xffff});
    }

    void TestGateAndCheapPrefilters()
    {
        Require(!EvaluateGate(nullptr, true, true, true, SupportedSha()).Enabled(),
                "null transfer gate was enabled");
        Require(EvaluateGate("1", false, true, true, SupportedSha()).Status ==
                    GateStatus::MissingObserverDebugProfile,
                "transfer gate ignored missing observer debug profile");
        Require(EvaluateGate("1", true, false, true, SupportedSha()).Status ==
                    GateStatus::MissingObserverDebugWindow,
                "transfer gate ignored missing observer debug window");
        Require(EvaluateGate("1", true, true, false, SupportedSha()).Status ==
                    GateStatus::MissingInstanceMarker,
                "transfer gate ignored missing instance marker");
        Require(EvaluateGate("1", true, true, true, nullptr).Status == GateStatus::MissingBinarySha256,
                "transfer gate ignored missing SHA");
        Require(EvaluateGate("1", true, true, true, "not-this-binary").Status ==
                    GateStatus::UnsupportedBinarySha256,
                "transfer gate ignored unsupported SHA");
        Require(EvaluateGate("1", true, true, true, SupportedSha()).Enabled(),
                "valid transfer gate was not enabled");

        Require(IsReflectedTransferNameIndex(kServerTransferredPlayerConfirmationResultNameIndex),
                "transfer FName prefilter rejected bAccept target");
        Require(!IsReflectedTransferNameIndex(9999), "transfer FName prefilter accepted non-target");
        Require(!ShouldAttemptNameObservation(kServerTransferredPlayerConfirmationResultNameIndex, 0),
                "transfer name observation ignored zero budget");
        Require(!ShouldAttemptNameObservation(9999, 1), "transfer name observation accepted non-target");
        Require(ShouldAttemptNameObservation(kServerTransferredPlayerConfirmationResultNameIndex, 1),
                "transfer name observation rejected target with budget");
        Require(!ShouldAttemptTransferBAcceptBridgeObservation(EnabledGate(),
                                                               kServerTransferredPlayerConfirmationResultNameIndex,
                                                               1,
                                                               0),
                "transfer bridge observation attempted with zero subscribers");
        Require(!ShouldAttemptTransferBAcceptBridgeObservation(EnabledGate(),
                                                               kServerTransferredPlayerConfirmationResultNameIndex,
                                                               0,
                                                               1),
                "transfer bridge observation attempted with zero budget");
        Require(!ShouldAttemptTransferBAcceptBridgeObservation(EnabledGate(), 9999, 1, 1),
                "transfer bridge observation attempted non-target");
        Require(ShouldAttemptTransferBAcceptBridgeObservation(EnabledGate(),
                                                              kServerTransferredPlayerConfirmationResultNameIndex,
                                                              1,
                                                              1),
                "transfer bridge observation rejected target with subscriber and budget");
    }

    void TestRejectsBeforeReadingWithoutGateNameOrBudget()
    {
        MemoryReader throwing{ThrowingReader, nullptr};
        uint64_t observationNumber = 99;
        std::atomic<uint64_t> counter{0};

        Attempt disabled = TryObserveInvocation({},
                                                kServerTransferredPlayerConfirmationResultNameIndex,
                                                throwing,
                                                reinterpret_cast<void*>(0x11110000),
                                                reinterpret_cast<void*>(0x22220000),
                                                counter,
                                                1,
                                                observationNumber);
        Require(disabled.Status == AttemptStatus::Disabled, "disabled transfer attempt status mismatch");
        Require(observationNumber == 0, "disabled transfer attempt left stale observation number");
        Require(counter.load() == 0, "disabled transfer attempt reserved budget");

        Attempt nonTarget = TryObserveInvocation(EnabledGate(),
                                                 9999,
                                                 throwing,
                                                 reinterpret_cast<void*>(0x11110000),
                                                 reinterpret_cast<void*>(0x22220000),
                                                 counter,
                                                 1,
                                                 observationNumber);
        Require(nonTarget.Status == AttemptStatus::NonTransferFunction,
                "non-target transfer attempt status mismatch");
        Require(observationNumber == 0, "non-target transfer attempt left stale observation number");
        Require(counter.load() == 0, "non-target transfer attempt reserved budget");

        Attempt noBudget = TryObserveInvocation(EnabledGate(),
                                                kServerTransferredPlayerConfirmationResultNameIndex,
                                                throwing,
                                                reinterpret_cast<void*>(0x11110000),
                                                reinterpret_cast<void*>(0x22220000),
                                                counter,
                                                0,
                                                observationNumber);
        Require(noBudget.Status == AttemptStatus::BudgetExhausted,
                "zero-budget transfer attempt status mismatch");
        Require(noBudget.Result.Status == ReadStatus::Disabled,
                "zero-budget transfer attempt result status mismatch");
        Require(observationNumber == 0, "zero-budget transfer attempt left stale observation number");
        Require(counter.load() == 0, "zero-budget transfer attempt reserved budget");
    }

    void TestMatchesAndCopiesCanonicalBAccept()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 1;
            std::atomic<uint64_t> counter{0};
            uint64_t observationNumber = 0;

            Attempt attempt = TryObserveInvocation(EnabledGate(),
                                                   kServerTransferredPlayerConfirmationResultNameIndex,
                                                   fixture.Reader(),
                                                   fixture.Function.data(),
                                                   fixture.Params.data(),
                                                   counter,
                                                   2,
                                                   observationNumber);
            Require(attempt.Status == AttemptStatus::Matched, "valid transfer bAccept attempt was not matched");
            Require(counter.load() == 1, "valid transfer bAccept attempt did not reserve budget");
            Require(observationNumber == 1, "valid transfer bAccept observation number mismatch");

            CopiedTransferBAcceptObservation copied;
            Require(TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                    "valid transfer bAccept was not copied");
            Require(copied.FunctionNameIndex == kServerTransferredPlayerConfirmationResultNameIndex,
                    "copied transfer function FName mismatch");
            Require(copied.OuterNameIndex == kShooterPlayerControllerNameIndex,
                    "copied transfer outer FName mismatch");
            Require(copied.Accepted, "copied transfer bAccept did not preserve true");

            copied = {};
            Require(TryBuildCopiedTransferBAcceptObservationAfterOriginal(true, attempt, copied),
                    "post-original transfer bAccept copy failed");
            Require(copied.Accepted, "post-original transfer bAccept did not preserve true");
            Require(!TryBuildCopiedTransferBAcceptObservationAfterOriginal(false, attempt, copied),
                    "transfer bAccept copied before original completed");
            Require(copied.FunctionNameIndex == -1 && !copied.Accepted,
                    "transfer bAccept left stale output when original was not called");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 0;

            Attempt attempt = TryIdentifyInvocation(EnabledGate(),
                                                    kServerTransferredPlayerConfirmationResultNameIndex,
                                                    fixture.Reader(),
                                                    fixture.Function.data(),
                                                    fixture.Params.data());
            CopiedTransferBAcceptObservation copied;
            Require(TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                    "valid false transfer bAccept was not copied");
            Require(!copied.Accepted, "copied transfer bAccept did not preserve false");
        }
    }

    void TestRejectsNonCanonicalBoolAndClearsOutput()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 2;

            Attempt attempt = TryIdentifyInvocation(EnabledGate(),
                                                    kServerTransferredPlayerConfirmationResultNameIndex,
                                                    fixture.Reader(),
                                                    fixture.Function.data(),
                                                    fixture.Params.data());
            Require(attempt.Status == AttemptStatus::Rejected,
                    "non-canonical transfer bAccept attempt was accepted");
            Require(attempt.Invocation.FunctionNameIndex == -1,
                    "rejected transfer bAccept attempt left stale function name");
            Require(attempt.Invocation.Fields.empty(), "rejected transfer bAccept attempt left stale fields");

            CopiedTransferBAcceptObservation copied;
            copied.FunctionNameIndex = kServerTransferredPlayerConfirmationResultNameIndex;
            copied.OuterNameIndex = kShooterPlayerControllerNameIndex;
            copied.Accepted = true;
            Require(!TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                    "non-matched transfer bAccept attempt produced copied output");
            Require(copied.FunctionNameIndex == -1 && copied.OuterNameIndex == -1 && !copied.Accepted,
                    "non-matched transfer bAccept attempt left stale copied output");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 1;

            Attempt attempt = TryIdentifyInvocation(EnabledGate(),
                                                    kServerTransferredPlayerConfirmationResultNameIndex,
                                                    fixture.Reader(),
                                                    fixture.Function.data(),
                                                    fixture.Params.data());
            Require(attempt.Status == AttemptStatus::Matched,
                    "valid transfer bAccept attempt was not available for builder canonical check");

            fixture.Params[0] = 2;
            CopiedTransferBAcceptObservation copied;
            copied.FunctionNameIndex = kServerTransferredPlayerConfirmationResultNameIndex;
            copied.OuterNameIndex = kShooterPlayerControllerNameIndex;
            copied.Accepted = true;
            Require(!TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                    "transfer bAccept builder accepted non-canonical copied bool");
            Require(copied.FunctionNameIndex == -1 && copied.OuterNameIndex == -1 && !copied.Accepted,
                    "transfer bAccept builder left stale output after non-canonical copied bool");
        }
    }

    void TestRejectsMetadataOnlyAndForgedRanges()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);
        fixture.Params[0] = 1;

        Attempt metadataOnly = TryIdentifyInvocation(EnabledGate(),
                                                     kServerTransferredPlayerConfirmationResultNameIndex,
                                                     fixture.Reader(),
                                                     fixture.Function.data(),
                                                     nullptr);
        Require(metadataOnly.Status == AttemptStatus::Matched, "metadata-only transfer recognition failed");

        CopiedTransferBAcceptObservation copied;
        copied.FunctionNameIndex = kServerTransferredPlayerConfirmationResultNameIndex;
        copied.OuterNameIndex = kShooterPlayerControllerNameIndex;
        copied.Accepted = true;
        Require(!TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(metadataOnly, copied),
                "metadata-only transfer recognition produced copied bAccept output");
        Require(copied.FunctionNameIndex == -1 && copied.OuterNameIndex == -1 && !copied.Accepted,
                "metadata-only transfer recognition left stale copied output");

        Attempt attempt = TryIdentifyInvocation(EnabledGate(),
                                                kServerTransferredPlayerConfirmationResultNameIndex,
                                                fixture.Reader(),
                                                fixture.Function.data(),
                                                fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, "valid transfer bAccept fixture was not matched");

        attempt.Invocation.Fields[0].Range.Data = fixture.Params.data() + 1;
        Require(!TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                "forged transfer bAccept range was copied");
        Require(copied.FunctionNameIndex == -1 && copied.OuterNameIndex == -1 && !copied.Accepted,
                "forged transfer bAccept range left stale copied output");

        attempt = TryIdentifyInvocation(EnabledGate(),
                                        kServerTransferredPlayerConfirmationResultNameIndex,
                                        fixture.Reader(),
                                        fixture.Function.data(),
                                        fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, "valid transfer bAccept fixture was not rematched");
        attempt.Invocation.Fields[0].PropertyNameIndex = 9999;
        Require(!TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, copied),
                "wrong transfer bAccept property FName was copied");
    }

    void TestBudgetHelpers()
    {
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;

        Require(!HasObservationBudgetRemaining(counter, 0), "zero transfer budget reported remaining");
        Require(HasObservationBudgetRemaining(counter, 1), "available transfer budget not reported");
        Require(TryReserveObservationBudget(counter, 1, observationNumber),
                "failed to reserve available transfer budget");
        Require(counter.load() == 1 && observationNumber == 1, "reserved transfer budget state mismatch");
        Require(!TryReserveObservationBudget(counter, 1, observationNumber),
                "reserved transfer budget beyond limit");
        Require(observationNumber == 0, "exhausted transfer budget left stale observation number");
        Require(!ShouldLogObservation(0, 1), "transfer log helper accepted zero observation number");
        Require(ShouldLogObservation(1, 1), "transfer log helper rejected in-budget observation");
        Require(!ShouldLogObservation(2, 1), "transfer log helper accepted out-of-budget observation");
    }
}

int main()
{
    TestGateAndCheapPrefilters();
    TestRejectsBeforeReadingWithoutGateNameOrBudget();
    TestMatchesAndCopiesCanonicalBAccept();
    TestRejectsNonCanonicalBoolAndClearsOutput();
    TestRejectsMetadataOnlyAndForgedRanges();
    TestBudgetHelpers();

    std::cout << "ProcessEventTransferReflectionTests passed\n";
    return 0;
}
