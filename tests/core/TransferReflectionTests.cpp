#include "ue/TransferReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
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
                     const void* outer,
                     int32_t nameNumber = 0)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const FNameValue name{nameIndex, nameNumber};

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
                       int32_t objectIndex,
                       int32_t offset,
                       int32_t elementSize,
                       uint64_t propertyFlags)
    {
        WriteObject(buffer, nameIndex, objectIndex, klass, owner);

        const int32_t arrayDim = 1;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, elementSize);
        WriteAt(buffer, 0x38, propertyFlags);
        WriteAt(buffer, 0x4c, offset);
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
            return {RegionReader, &Context};
        }
    };

    ReadOptions Options()
    {
        return MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
    }

    void BuildConfirmationResult(TransferFixture& fixture,
                                 int32_t functionNameIndex = kServerTransferredPlayerConfirmationResultNameIndex)
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
                    functionNameIndex,
                    kServerTransferredPlayerConfirmationResultObjectIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());
        WriteProperty(fixture.Property,
                      nullptr,
                      fixture.Function.data(),
                      fixture.BoolPropertyClass.data(),
                      kBAcceptNameIndex,
                      kBAcceptObjectIndex,
                      0x00,
                      0x01,
                      kBoolInputPropertyFlags);

        WriteAt(fixture.Function, 0x38, fixture.Property.data());
        WriteAt(fixture.Function, 0x90, uint32_t{0x220cc0});
        WriteAt(fixture.Function, 0x96, uint16_t{1});
        WriteAt(fixture.Function, 0x98, uint16_t{0x01});
        WriteAt(fixture.Function, 0x9a, uint16_t{0xffff});
    }

    void RequireAccepted(TransferFixture& fixture, const void* params)
    {
        TransferReflection::TransferInvocation invocation;
        ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            params,
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == TransferReflection::TransferFunction::ServerTransferredPlayerConfirmationResult,
                "transfer function mismatch");
        Require(invocation.FunctionNameIndex == kServerTransferredPlayerConfirmationResultNameIndex,
                "transfer function name mismatch");
        Require(invocation.OuterNameIndex == kShooterPlayerControllerNameIndex,
                "transfer outer name mismatch");
        Require(invocation.Fields.size() == 1, "transfer field count mismatch");
        Require(invocation.Fields[0].Field == TransferReflection::TransferField::BAccept,
                "transfer field semantic mismatch");
        Require(invocation.Fields[0].PropertyNameIndex == kBAcceptNameIndex,
                "transfer property name mismatch");
        Require(invocation.Fields[0].Offset == 0x00, "transfer property offset mismatch");
        Require(invocation.Fields[0].Size == 0x01, "transfer property size mismatch");
        Require(invocation.Fields[0].ExposesRange, "transfer bAccept should expose one copied scalar range");
        if (params)
        {
            Require(invocation.HasParameterRanges, "transfer params should be recorded as present");
            Require(invocation.ParameterData == fixture.Params.data(), "transfer parameter provenance data mismatch");
            Require(invocation.ParameterSize == 0x01, "transfer parameter provenance size mismatch");
            Require(invocation.Fields[0].Range.Data ==
                        invocation.ParameterData + static_cast<size_t>(invocation.Fields[0].Offset),
                    "transfer bAccept range data mismatch");
            Require(invocation.Fields[0].Range.Size == 1, "transfer bAccept range must stay one byte");
        }
        else
        {
            Require(!invocation.HasParameterRanges, "metadata-only transfer recognition reported parameter ranges");
            Require(invocation.ParameterData == nullptr, "metadata-only transfer recorded parameter data");
            Require(invocation.ParameterSize == 0, "metadata-only transfer recorded parameter size");
            Require(invocation.Fields[0].Range.Data == nullptr, "metadata-only transfer range exposed data");
            Require(invocation.Fields[0].Range.Size == 0, "metadata-only transfer range exposed size");
        }
    }

    void TestRecognizesBAccept()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);
        fixture.Params[0] = 1;

        RequireAccepted(fixture, fixture.Params.data());
    }

    void TestAcceptsMetadataOnlyRecognition()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);

        RequireAccepted(fixture, nullptr);
    }

    void TestRejectsWrongOuterNameNumberAndClass()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Outer, 9999, 9999, nullptr, nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer outer was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Outer, kShooterPlayerControllerNameIndex, kShooterPlayerControllerNameIndex, nullptr, nullptr, 1);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered transfer outer FName was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Outer,
                        kShooterPlayerControllerNameIndex,
                        9999,
                        nullptr,
                        nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer outer object index was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Function,
                        kServerTransferredPlayerConfirmationResultNameIndex,
                        kServerTransferredPlayerConfirmationResultObjectIndex,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data(),
                        1);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered transfer UFunction FName was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Function,
                        kServerTransferredPlayerConfirmationResultNameIndex,
                        9999,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data());

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer UFunction object index was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.FunctionClass, 9999, kFunctionClassObjectIndex, nullptr, nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer UFunction class was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, 9999, nullptr, nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong transfer UFunction class object index was accepted");
        }
    }

    void TestRejectsWrongShape()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{0x220cc1});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer FunctionFlags were accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Function, 0x96, uint16_t{2});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer NumParms were accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{2});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer ParmsSize was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Function, 0x9a, uint16_t{0x00});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer ReturnValueOffset was accepted");
        }
    }

    void TestRejectsWrongPropertyShape()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            const FNameValue wrongName{12345, 0};
            WriteAt(fixture.Property, 0x18, wrongName);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer property name was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.Property,
                        kBAcceptNameIndex,
                        9999,
                        fixture.BoolPropertyClass.data(),
                        fixture.Function.data());
            WriteAt(fixture.Property, 0x28, static_cast<const void*>(nullptr));
            WriteAt(fixture.Property, 0x30, int32_t{1});
            WriteAt(fixture.Property, 0x34, int32_t{1});
            WriteAt(fixture.Property, 0x38, uint64_t{kBoolInputPropertyFlags});
            WriteAt(fixture.Property, 0x4c, int32_t{0});
            WriteAt(fixture.Property, 0x70, kBAcceptBoolFieldSize);
            WriteAt(fixture.Property, 0x71, kBAcceptBoolByteOffset);
            WriteAt(fixture.Property, 0x72, kBAcceptBoolByteMask);
            WriteAt(fixture.Property, 0x73, kBAcceptBoolFieldMask);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer property object index was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.BoolPropertyClass, 9999, kBoolPropertyClassObjectIndex, nullptr, nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer property class was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteObject(fixture.BoolPropertyClass, kBoolPropertyClassNameIndex, 9999, nullptr, nullptr);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong transfer BoolProperty class object index was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x4c, int32_t{1});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::OutOfBounds, "wrong transfer property offset was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x34, int32_t{2});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::OutOfBounds, "wrong transfer property size was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x38, uint64_t{kBoolInputPropertyFlags ^ 0x400});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer property flags were accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x30, int32_t{2});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::OutOfBounds, "wrong transfer property ArrayDim was accepted");
        }
    }

    void TestRejectsWrongBoolPropertyMetadata()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x70, uint8_t{2});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer bool field size was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x71, uint8_t{1});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer bool byte offset was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x72, uint8_t{0xff});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "native transfer bool marker was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x72, uint8_t{0x02});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer bool byte mask was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x73, uint8_t{0x01});

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong transfer bool field mask was accepted");
        }
    }

    void TestRejectsNonCanonicalCopiedBoolParams()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);
        fixture.Params[0] = 2;

        TransferReflection::TransferInvocation invocation;
        ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "non-canonical transfer bool parameter was accepted");
        Require(invocation.FunctionNameIndex == -1, "rejected transfer bool left stale function name");
        Require(invocation.OuterNameIndex == -1, "rejected transfer bool left stale outer name");
        Require(!invocation.HasParameterRanges, "rejected transfer bool left stale parameter range state");
        Require(invocation.Fields.empty(), "rejected transfer bool left stale fields");
    }

    void TestRejectsPropertyChainDrift()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Function, 0x38, static_cast<const void*>(nullptr));

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "missing transfer property was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            WriteAt(fixture.Property, 0x28, fixture.Property.data());

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "cyclic transfer property chain was accepted");
        }
    }

    void TestRejectsUnsupportedTarget()
    {
        TransferFixture fixture;
        TransferReflection::TransferInvocation invocation;
        BuildConfirmationResult(fixture);
        ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.FunctionNameIndex == kServerTransferredPlayerConfirmationResultNameIndex,
                "valid transfer invocation did not populate unsupported-target stale source");

        BuildConfirmationResult(fixture, 9999);
        result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "unsupported transfer target was accepted");
        Require(invocation.FunctionNameIndex == -1, "unsupported transfer target left stale function name");
        Require(invocation.OuterNameIndex == -1, "unsupported transfer target left stale outer name");
        Require(!invocation.HasParameterRanges, "unsupported transfer target left stale range state");
        Require(invocation.ParameterData == nullptr, "unsupported transfer target left stale parameter data");
        Require(invocation.ParameterSize == 0, "unsupported transfer target left stale parameter size");
        Require(invocation.Fields.empty(), "unsupported transfer target left stale fields");
    }

    void TestGateRejectsBeforeReading()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);

        TransferReflection::TransferInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        MemoryReader reader = fixture.Reader();
        ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
            reader,
            disabled,
            reinterpret_cast<const void*>(0x44440000),
            reinterpret_cast<const void*>(0x55550000),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled transfer reflection was accepted");
        Require(fixture.Context.ReadCalls == 0, "disabled transfer reflection read memory before gate rejection");
        Require(invocation.FunctionNameIndex == -1, "disabled transfer reflection left stale function name");
        Require(invocation.ParameterData == nullptr, "disabled transfer reflection recorded parameter data");
        Require(invocation.ParameterSize == 0, "disabled transfer reflection recorded parameter size");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        fixture.Context.ReadCalls = 0;
        reader = fixture.Reader();
        result = TransferReflection::TryIdentifyTransferInvocation(
            reader,
            unsupported,
            reinterpret_cast<const void*>(0x44440000),
            reinterpret_cast<const void*>(0x55550000),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout,
                "unsupported transfer reflection read memory before failing closed");
        Require(fixture.Context.ReadCalls == 0, "unsupported transfer reflection read memory before gate rejection");
        Require(invocation.ParameterData == nullptr, "unsupported transfer reflection recorded parameter data");
        Require(invocation.ParameterSize == 0, "unsupported transfer reflection recorded parameter size");
    }

    void TestRejectsNullAndUnreadableParams()
    {
        {
            TransferFixture fixture;
            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                nullptr,
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::InvalidArgument, "null transfer UFunction pointer was accepted");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);

            TransferReflection::TransferInvocation invocation;
            ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                reinterpret_cast<const void*>(0x33330000),
                invocation);
            Require(result.Status == ReadStatus::Unreadable, "unreadable transfer params were accepted");
        }
    }

    void TestRejectsClearStaleInvocation()
    {
        TransferFixture fixture;
        BuildConfirmationResult(fixture);

        TransferReflection::TransferInvocation invocation;
        ReadResult result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.FunctionNameIndex == kServerTransferredPlayerConfirmationResultNameIndex,
                "valid transfer invocation did not populate stale source");
        Require(invocation.Fields.size() == 1, "valid transfer invocation did not populate fields");

        WriteAt(fixture.Function, 0x98, uint16_t{0x02});
        result = TransferReflection::TryIdentifyTransferInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "invalid transfer invocation was accepted");
        Require(invocation.FunctionNameIndex == -1, "rejected transfer invocation left stale function name");
        Require(invocation.OuterNameIndex == -1, "rejected transfer invocation left stale outer name");
        Require(!invocation.HasParameterRanges, "rejected transfer invocation left stale range state");
        Require(invocation.ParameterData == nullptr, "rejected transfer invocation left stale parameter data");
        Require(invocation.ParameterSize == 0, "rejected transfer invocation left stale parameter size");
        Require(invocation.Fields.empty(), "rejected transfer invocation left stale fields");
    }

    void TestTryCopyBAccept()
    {
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 0;

            bool accepted = true;
            ReadResult result = TransferReflection::TryCopyBAccept(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                accepted);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(!accepted, "transfer bAccept helper did not copy false");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 1;

            bool accepted = false;
            ReadResult result = TransferReflection::TryCopyBAccept(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                accepted);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(accepted, "transfer bAccept helper did not copy true");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);

            bool accepted = true;
            ReadResult result = TransferReflection::TryCopyBAccept(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                nullptr,
                accepted);

            Require(result.Status == ReadStatus::InvalidArgument, "transfer bAccept helper accepted null params");
            Require(!accepted, "transfer bAccept helper left stale output after null params");
        }
        {
            TransferFixture fixture;
            BuildConfirmationResult(fixture);
            fixture.Params[0] = 2;

            bool accepted = true;
            ReadResult result = TransferReflection::TryCopyBAccept(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                accepted);

            Require(result.Status == ReadStatus::Implausible,
                    "transfer bAccept helper accepted non-canonical bool");
            Require(!accepted, "transfer bAccept helper left stale output after non-canonical bool");
        }
    }
}

int main()
{
    TestRecognizesBAccept();
    TestAcceptsMetadataOnlyRecognition();
    TestRejectsWrongOuterNameNumberAndClass();
    TestRejectsWrongShape();
    TestRejectsWrongPropertyShape();
    TestRejectsWrongBoolPropertyMetadata();
    TestRejectsNonCanonicalCopiedBoolParams();
    TestRejectsPropertyChainDrift();
    TestRejectsUnsupportedTarget();
    TestGateRejectsBeforeReading();
    TestRejectsNullAndUnreadableParams();
    TestRejectsClearStaleInvocation();
    TestTryCopyBAccept();

    std::cout << "TransferReflectionTests passed\n";
    return 0;
}
