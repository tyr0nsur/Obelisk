#include "ue/RuntimeReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
    using namespace Obelisk::UE::RuntimeReflection;

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
    void WriteObjectHeader(std::array<uint8_t, N>& buffer, int32_t nameIndex)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const int32_t internalIndex = nameIndex;
        const void* klass = reinterpret_cast<const void*>(0x20000);
        const FNameValue name{nameIndex, 0};
        const void* outer = reinterpret_cast<const void*>(0x30000);

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
                       int32_t nameIndex,
                       int32_t offset,
                       int32_t elementSize)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const int32_t internalIndex = nameIndex;
        const void* klass = reinterpret_cast<const void*>(0x20000);
        const FNameValue name{nameIndex, 0};
        WriteAt(buffer, 0x00, vtable);
        WriteAt(buffer, 0x08, flags);
        WriteAt(buffer, 0x0c, internalIndex);
        WriteAt(buffer, 0x10, klass);
        WriteAt(buffer, 0x18, name);
        WriteAt(buffer, 0x20, owner);

        const int32_t arrayDim = 1;
        const uint64_t propertyFlags = 0x80;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, elementSize);
        WriteAt(buffer, 0x38, propertyFlags);
        WriteAt(buffer, 0x4c, offset);
    }

    void TestGateRejectsBeforeReading()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        UFunctionView view;

        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = TryReadUFunction(reader, disabled, reinterpret_cast<const void*>(0x10000), view);
        Require(result.Status == ReadStatus::Disabled, "disabled gate did not reject");
        Require(context.Calls == 0, "disabled gate touched memory");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = TryReadUFunction(reader, unsupported, reinterpret_cast<const void*>(0x10000), view);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported binary did not reject");
        Require(context.Calls == 0, "unsupported gate touched memory");
    }

    void TestReadsBoundedFunctionPropertyChain()
    {
        std::array<uint8_t, 0xb0> function{};
        std::array<uint8_t, 0x80> propertyA{};
        std::array<uint8_t, 0x80> propertyB{};

        WriteObjectHeader(function, 9619);
        WriteProperty(propertyA, propertyB.data(), function.data(), 12001, 0x00, 0x10);
        WriteProperty(propertyB, nullptr, function.data(), 12002, 0x10, 0x10);

        const void* children = propertyA.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t numParms = 2;
        const uint16_t parmsSize = 0x20;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(function, 0x38, children);
        WriteAt(function, 0x90, functionFlags);
        WriteAt(function, 0x96, numParms);
        WriteAt(function, 0x98, parmsSize);
        WriteAt(function, 0x9a, returnValueOffset);

        ReaderContext context;
        context.Regions.push_back({function.data(), function.size()});
        context.Regions.push_back({propertyA.data(), propertyA.size()});
        context.Regions.push_back({propertyB.data(), propertyB.size()});

        MemoryReader reader{RegionReader, &context};
        ReadOptions options = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
        UFunctionView view;
        ReadResult result = TryReadUFunction(reader, options, function.data(), view);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(view.NumParms == 2, "NumParms mismatch");
        Require(view.ParmsSize == 0x20, "ParmsSize mismatch");
        Require(view.Parameters.size() == 2, "property count mismatch");
        Require(view.Parameters[0].OffsetInternal == 0x00, "first property offset mismatch");
        Require(view.Parameters[1].OffsetInternal == 0x10, "second property offset mismatch");
        Require(view.Parameters[1].ByteSize == 0x10, "property byte size mismatch");
    }

    void TestRejectsPropertyOutsideParmsSize()
    {
        std::array<uint8_t, 0xb0> function{};
        std::array<uint8_t, 0x80> property{};

        WriteObjectHeader(function, 9619);
        WriteProperty(property, nullptr, function.data(), 12001, 0x18, 0x10);

        const void* children = property.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t numParms = 1;
        const uint16_t parmsSize = 0x20;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(function, 0x38, children);
        WriteAt(function, 0x90, functionFlags);
        WriteAt(function, 0x96, numParms);
        WriteAt(function, 0x98, parmsSize);
        WriteAt(function, 0x9a, returnValueOffset);

        ReaderContext context;
        context.Regions.push_back({function.data(), function.size()});
        context.Regions.push_back({property.data(), property.size()});

        MemoryReader reader{RegionReader, &context};
        UFunctionView view;
        ReadResult result = TryReadUFunction(
            reader,
            MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true),
            function.data(),
            view);

        Require(result.Status == ReadStatus::OutOfBounds, "out-of-bounds property was accepted");
    }

    void TestRejectsPropertyOwnerMismatch()
    {
        std::array<uint8_t, 0xb0> function{};
        std::array<uint8_t, 0x80> property{};

        WriteObjectHeader(function, 9619);
        WriteProperty(property, nullptr, reinterpret_cast<const void*>(0x12345000), 12001, 0x00, 0x10);

        const void* children = property.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t numParms = 1;
        const uint16_t parmsSize = 0x10;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(function, 0x38, children);
        WriteAt(function, 0x90, functionFlags);
        WriteAt(function, 0x96, numParms);
        WriteAt(function, 0x98, parmsSize);
        WriteAt(function, 0x9a, returnValueOffset);

        ReaderContext context;
        context.Regions.push_back({function.data(), function.size()});
        context.Regions.push_back({property.data(), property.size()});

        MemoryReader reader{RegionReader, &context};
        UFunctionView view;
        ReadResult result = TryReadUFunction(
            reader,
            MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true),
            function.data(),
            view);

        Require(result.Status == ReadStatus::Implausible, "property owner mismatch was accepted");
    }

    void TestParameterRangeIsBounded()
    {
        std::array<uint8_t, 0x20> params{};
        params[0x10] = 0x42;

        UPropertyView property;
        property.OffsetInternal = 0x10;
        property.ByteSize = 0x10;

        ReaderContext context;
        context.Regions.push_back({params.data(), params.size()});
        MemoryReader reader{RegionReader, &context};

        ParamRange range;
        ReadResult result = TryGetParameterRange(reader, params.data(), 0x20, property, 0x10, range);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(range.Data == params.data() + 0x10, "parameter range data mismatch");
        Require(range.Size == 0x10, "parameter range size mismatch");

        result = TryGetParameterRange(reader, params.data(), 0x18, property, 0x10, range);
        Require(result.Status == ReadStatus::OutOfBounds, "truncated ParmsSize was accepted");

        result = TryGetParameterRange(reader, params.data(), 0x20, property, 0x08, range);
        Require(result.Status == ReadStatus::OutOfBounds, "maxBytes limit was ignored");
    }

    void TestFStringHeaderHelpersDoNotDecode()
    {
        std::array<uint8_t, 0x20> buffer{};
        FStringHeaderCandidate expected{
            reinterpret_cast<const void*>(0x12345000),
            5,
            8,
        };
        WriteAt(buffer, 0x08, expected.Data);
        WriteAt(buffer, 0x10, expected.ArrayNum);
        WriteAt(buffer, 0x14, expected.ArrayMax);

        FStringHeaderCandidate actual;
        ReadResult result = TryReadFStringHeaderFromBuffer(buffer.data(), buffer.size(), 0x08, actual);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(actual.Data == expected.Data, "FString Data mismatch");
        Require(actual.ArrayNum == expected.ArrayNum, "FString ArrayNum mismatch");
        Require(actual.ArrayMax == expected.ArrayMax, "FString ArrayMax mismatch");
        Require(IsPlausibleFStringHeader(actual), "plausible FString header was rejected");

        FStringHeaderCandidate empty;
        Require(IsPlausibleFStringHeader(empty), "empty FString header was rejected");

        FStringHeaderCandidate bad{reinterpret_cast<const void*>(0x12345000), 4096, 4096};
        Require(!IsPlausibleFStringHeader(bad, 2048), "oversized FString header was accepted");

        result = TryReadFStringHeaderFromBuffer(buffer.data(), buffer.size(), 0x18, actual);
        Require(result.Status == ReadStatus::OutOfBounds, "short FString header was accepted");
    }

    void TestDecodesUtf32FString()
    {
        std::array<uint32_t, 12> text{
            'P', 'l', 'a', 'y', 'e', 'r', 'N', 'a', 'm', 'e', 0, 0xaaaa,
        };
        FStringHeaderCandidate header{text.data(), 11, 11};
        ReaderContext context;
        context.Regions.push_back({reinterpret_cast<const uint8_t*>(text.data()), text.size() * sizeof(uint32_t)});
        MemoryReader reader{RegionReader, &context};

        std::string decoded;
        ReadResult result = TryDecodeFStringUtf32(reader, header, 512, decoded);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(decoded == "PlayerName", "UTF-32 FString decoded incorrectly");
    }

    void TestDecodesUtf32FStringUnicodeScalar()
    {
        std::array<uint32_t, 4> text{'A', 0x1f600, 'Z', 0};
        FStringHeaderCandidate header{text.data(), 4, 4};
        ReaderContext context;
        context.Regions.push_back({reinterpret_cast<const uint8_t*>(text.data()), text.size() * sizeof(uint32_t)});
        MemoryReader reader{RegionReader, &context};

        std::string decoded;
        ReadResult result = TryDecodeFStringUtf32(reader, header, 512, decoded);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(decoded == "A\xf0\x9f\x98\x80Z", "non-BMP UTF-32 FString decoded incorrectly");
    }

    void TestDecodesEmptyFString()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        std::string decoded = "not-empty";

        ReadResult result = TryDecodeFStringUtf32(reader, {}, 512, decoded);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(decoded.empty(), "empty FString did not decode to empty string");
    }

    void TestRejectsMalformedFString()
    {
        std::array<uint32_t, 4> noTerminator{'B', 'a', 'd', '!'};
        std::array<uint32_t, 4> earlyNull{'B', 0, 'd', 0};
        std::array<uint32_t, 2> invalidScalar{0xd800, 0};
        ReaderContext context;
        context.Regions.push_back({
            reinterpret_cast<const uint8_t*>(noTerminator.data()),
            noTerminator.size() * sizeof(uint32_t),
        });
        context.Regions.push_back({
            reinterpret_cast<const uint8_t*>(earlyNull.data()),
            earlyNull.size() * sizeof(uint32_t),
        });
        context.Regions.push_back({
            reinterpret_cast<const uint8_t*>(invalidScalar.data()),
            invalidScalar.size() * sizeof(uint32_t),
        });
        MemoryReader reader{RegionReader, &context};

        std::string decoded;
        ReadResult result = TryDecodeFStringUtf32(reader, {noTerminator.data(), 4, 4}, 512, decoded);
        Require(result.Status == ReadStatus::Implausible, "unterminated FString was accepted");

        result = TryDecodeFStringUtf32(reader, {earlyNull.data(), 4, 4}, 512, decoded);
        Require(result.Status == ReadStatus::Implausible, "early-NUL FString was accepted");

        result = TryDecodeFStringUtf32(reader, {invalidScalar.data(), 2, 2}, 512, decoded);
        Require(result.Status == ReadStatus::Implausible, "invalid UTF-32 scalar was accepted");

        result = TryDecodeFStringUtf32(reader, {reinterpret_cast<const void*>(0x12345000), 4, 4}, 512, decoded);
        Require(result.Status == ReadStatus::Unreadable, "unreadable FString data was accepted");

        result = TryDecodeFStringUtf32(reader, {noTerminator.data(), 4, 3}, 512, decoded);
        Require(result.Status == ReadStatus::Implausible, "ArrayMax < ArrayNum was accepted");

        result = TryDecodeFStringUtf32(reader, {noTerminator.data(), 513, 513}, 512, decoded);
        Require(result.Status == ReadStatus::Implausible, "oversized FString was accepted");
    }
}

int main()
{
    TestGateRejectsBeforeReading();
    TestReadsBoundedFunctionPropertyChain();
    TestRejectsPropertyOutsideParmsSize();
    TestRejectsPropertyOwnerMismatch();
    TestParameterRangeIsBounded();
    TestFStringHeaderHelpersDoNotDecode();
    TestDecodesUtf32FString();
    TestDecodesUtf32FStringUnicodeScalar();
    TestDecodesEmptyFString();
    TestRejectsMalformedFString();

    std::cout << "RuntimeReflectionTests passed\n";
    return 0;
}
