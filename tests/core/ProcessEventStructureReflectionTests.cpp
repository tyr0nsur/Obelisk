#include "hooks/ProcessEventStructureReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventStructureReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kVerifyPinCodeNameIndex = 7636;
    constexpr int32_t kPrimalStructureItemContainerNameIndex = 7617;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kPinCodeNameIndex = 22699;
    constexpr int32_t kReturnValueNameIndex = 17716;

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
        int Calls = 0;
    };

    bool RegionReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
        ++reader->Calls;
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
                       const void* klass,
                       int32_t nameIndex,
                       int32_t offset,
                       int32_t elementSize)
    {
        WriteObject(buffer, nameIndex, nameIndex, klass, owner);

        const int32_t arrayDim = 1;
        const uint64_t propertyFlags = 0x80;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, elementSize);
        WriteAt(buffer, 0x38, propertyFlags);
        WriteAt(buffer, 0x4c, offset);
    }

    struct StructureFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> IntPropertyClass{};
        std::array<uint8_t, 0x40> Outer{};
        std::array<uint8_t, 0x08> Params{};
        ReaderContext Context;

        MemoryReader Reader()
        {
            Context.Regions.clear();
            Context.Regions.push_back({Function.data(), Function.size()});
            Context.Regions.push_back({PropertyA.data(), PropertyA.size()});
            Context.Regions.push_back({PropertyB.data(), PropertyB.size()});
            Context.Regions.push_back({BoolPropertyClass.data(), BoolPropertyClass.size()});
            Context.Regions.push_back({IntPropertyClass.data(), IntPropertyClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    void BuildVerifyPinCode(StructureFixture& fixture)
    {
        WriteObject(fixture.BoolPropertyClass,
                    kBoolPropertyClassNameIndex,
                    kBoolPropertyClassNameIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.IntPropertyClass,
                    kIntPropertyClassNameIndex,
                    kIntPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Outer,
                    kPrimalStructureItemContainerNameIndex,
                    kPrimalStructureItemContainerNameIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    kVerifyPinCodeNameIndex,
                    kVerifyPinCodeNameIndex,
                    reinterpret_cast<const void*>(0x20000),
                    fixture.Outer.data());

        WriteProperty(fixture.PropertyA,
                      fixture.PropertyB.data(),
                      fixture.Function.data(),
                      fixture.IntPropertyClass.data(),
                      kPinCodeNameIndex,
                      0x00,
                      0x04);
        WriteProperty(fixture.PropertyB,
                      nullptr,
                      fixture.Function.data(),
                      fixture.BoolPropertyClass.data(),
                      kReturnValueNameIndex,
                      0x04,
                      0x01);

        const void* children = fixture.PropertyA.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t numParms = 2;
        const uint16_t parmsSize = 0x05;
        const uint16_t returnValueOffset = 0x04;
        WriteAt(fixture.Function, 0x38, children);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void TestGateEvaluation()
    {
        const char* supportedSha = kSupportedShooterGameServerSha256.data();

        Require(EvaluateGate(nullptr, supportedSha).Status == GateStatus::Disabled,
                "missing enable env should disable structure reflection");
        Require(EvaluateGate("0", supportedSha).Status == GateStatus::Disabled,
                "non-1 enable env should disable structure reflection");
        Require(EvaluateGate("1", nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary SHA gate was not rejected");
        Require(EvaluateGate("1", "").Status == GateStatus::MissingBinarySha256,
                "empty binary SHA gate was not rejected");
        Require(EvaluateGate("1", "not-this-binary").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary SHA gate was not rejected");

        Gate gate = EvaluateGate("1", supportedSha);
        Require(gate.Status == GateStatus::Enabled, "supported structure reflection gate did not enable");
        Require(gate.Enabled(), "enabled structure reflection gate did not report enabled");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "enabled gate did not retain binary SHA");
    }

    void TestObservationLogLimit()
    {
        Require(!ShouldAttemptObservation(0), "zero structure reflection log limit should skip observation");
        Require(ShouldAttemptObservation(1), "non-zero structure reflection log limit should allow observation");
        Require(!ShouldLogObservation(0, 25), "zero observation number should not log");
        Require(!ShouldLogObservation(1, 0), "zero structure reflection log limit should disable logs");
        Require(ShouldLogObservation(1, 1), "first observation should log at limit one");
        Require(!ShouldLogObservation(2, 1), "observation beyond limit should not log");
    }

    void TestReflectedStructureNameFilter()
    {
        Require(IsReflectedStructureNameIndex(7541), "AllowStructureAccess FName was not accepted");
        Require(IsReflectedStructureNameIndex(7574), "IsAllowedToDemolish FName was not accepted");
        Require(IsReflectedStructureNameIndex(7605), "SetVariant FName was not accepted");
        Require(IsReflectedStructureNameIndex(7620), "AllowToggleActivation FName was not accepted");
        Require(IsReflectedStructureNameIndex(7636), "VerifyPinCode FName was not accepted");
        Require(IsReflectedStructureNameIndex(8481), "CanSeat FName was not accepted");
        Require(!IsReflectedStructureNameIndex(42), "unrelated FName was accepted");
    }

    void TestDisabledGateDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            {},
            kVerifyPinCodeNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Disabled, "disabled gate did not short-circuit");
        Require(context.Calls == 0, "disabled gate touched UFunction memory");
    }

    void TestNonStructureNameDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            42,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::NonStructureFunction, "non-structure name did not short-circuit");
        Require(context.Calls == 0, "non-structure name touched UFunction memory");
    }

    void TestIdentifiesVerifyPinCodeWithoutPinRange()
    {
        StructureFixture fixture;
        BuildVerifyPinCode(fixture);
        fixture.Params[4] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kVerifyPinCodeNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(attempt.Invocation.Function == StructureReflection::StructureFunction::VerifyPinCode,
                "VerifyPinCode function mismatch");
        Require(attempt.Invocation.Fields.size() == 2, "VerifyPinCode field count mismatch");
        Require(attempt.Invocation.Fields[0].Sensitive, "pinCode should be sensitive");
        Require(attempt.Invocation.Fields[0].Range.Data == nullptr, "pinCode range was exposed");
        Require(attempt.Invocation.Fields[1].Range.Data == fixture.Params.data() + 4,
                "ReturnValue range mismatch");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationLogLimit();
    TestReflectedStructureNameFilter();
    TestDisabledGateDoesNotRead();
    TestNonStructureNameDoesNotRead();
    TestIdentifiesVerifyPinCodeWithoutPinRange();

    std::cout << "ProcessEventStructureReflectionTests passed\n";
    return 0;
}
