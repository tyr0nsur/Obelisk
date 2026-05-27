#include "RuntimeReflection.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <string>
#include <utility>

namespace Obelisk::UE::RuntimeReflection
{
    namespace
    {
        constexpr FieldLayout kShooterGameServerLayout{
            .BinarySha256 = kSupportedShooterGameServerSha256,
        };

        bool IsCanonicalUserPointer(uintptr_t address)
        {
            return address >= 0x10000 && address <= 0x00007FFFFFFFFFFF;
        }

        bool IsNullOrCanonical(const void* address)
        {
            return address == nullptr || IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(address));
        }

        bool IsPlausibleFName(const FNameValue& name)
        {
            return name.ComparisonIndex >= 0 &&
                   name.ComparisonIndex < 10000000 &&
                   name.Number >= 0 &&
                   name.Number < 1000000;
        }

        bool AddWouldOverflow(size_t a, size_t b)
        {
            return a > std::numeric_limits<size_t>::max() - b;
        }

        template <typename T>
        ReadResult ReadAt(const MemoryReader& reader, const void* base, size_t offset, T& out)
        {
            if (!base)
                return ReadResult::Fail(ReadStatus::InvalidArgument, "null base pointer");
            if (AddWouldOverflow(reinterpret_cast<size_t>(base), offset))
                return ReadResult::Fail(ReadStatus::OutOfBounds, "address overflow");

            const auto* address = reinterpret_cast<const uint8_t*>(base) + offset;
            if (!reader.CanRead(address, sizeof(T)))
                return ReadResult::Fail(ReadStatus::Unreadable, "field is unreadable");

            std::memcpy(&out, address, sizeof(T));
            return ReadResult::Ok();
        }

        ReadResult ValidateGate(const ReadOptions& options)
        {
            if (!options.Enabled)
                return ReadResult::Fail(ReadStatus::Disabled, "runtime reflection is disabled");
            if (!options.Layout)
                return ReadResult::Fail(ReadStatus::UnsupportedLayout, "no supported layout for binary");
            if (options.MaxProperties == 0)
                return ReadResult::Fail(ReadStatus::InvalidArgument, "MaxProperties must be non-zero");
            if (options.MaxParmsSize == 0)
                return ReadResult::Fail(ReadStatus::InvalidArgument, "MaxParmsSize must be non-zero");
            return ReadResult::Ok();
        }

        ReadResult ReadProperty(const MemoryReader& reader,
                                const ReadOptions& options,
                                const void* owner,
                                const void* property,
                                uint16_t parmsSize,
                                UPropertyView& out)
        {
            UObjectView object;
            ReadResult objectResult = TryReadUObject(reader, *options.Layout, property, object);
            if (!objectResult)
                return objectResult;

            UPropertyView value;
            value.Address = property;
            value.Object = object;

            if (ReadResult result = ReadAt(reader, property, options.Layout->UFieldNext, value.Next); !result)
                return result;
            if (ReadResult result = ReadAt(reader, property, options.Layout->UPropertyArrayDim, value.ArrayDim); !result)
                return result;
            if (ReadResult result = ReadAt(reader, property, options.Layout->UPropertyElementSize, value.ElementSize); !result)
                return result;
            if (ReadResult result = ReadAt(reader, property, options.Layout->UPropertyPropertyFlags, value.PropertyFlags); !result)
                return result;
            if (ReadResult result = ReadAt(reader, property, options.Layout->UPropertyOffsetInternal, value.OffsetInternal); !result)
                return result;

            if (!IsNullOrCanonical(value.Next))
                return ReadResult::Fail(ReadStatus::Implausible, "property Next pointer is not canonical");
            if (value.ArrayDim <= 0 || value.ArrayDim > options.MaxArrayDim)
                return ReadResult::Fail(ReadStatus::Implausible, "property ArrayDim is implausible");
            if (value.ElementSize <= 0 || value.ElementSize > options.MaxElementSize)
                return ReadResult::Fail(ReadStatus::Implausible, "property ElementSize is implausible");
            if (value.OffsetInternal < 0)
                return ReadResult::Fail(ReadStatus::Implausible, "property Offset_Internal is negative");
            if (value.Object.OuterPrivate != owner)
                return ReadResult::Fail(ReadStatus::Implausible, "property owner does not match UFunction");

            const auto arrayDim = static_cast<size_t>(value.ArrayDim);
            const auto elementSize = static_cast<size_t>(value.ElementSize);
            if (arrayDim > std::numeric_limits<size_t>::max() / elementSize)
                return ReadResult::Fail(ReadStatus::OutOfBounds, "property byte size overflow");

            value.ByteSize = arrayDim * elementSize;
            const auto offset = static_cast<size_t>(value.OffsetInternal);
            if (offset > parmsSize || value.ByteSize > static_cast<size_t>(parmsSize) - offset)
                return ReadResult::Fail(ReadStatus::OutOfBounds, "property range exceeds ParmsSize");

            out = std::move(value);
            return ReadResult::Ok();
        }

        bool IsInvalidUnicodeScalar(uint32_t codepoint)
        {
            return codepoint > 0x10ffff || (codepoint >= 0xd800 && codepoint <= 0xdfff);
        }

        void AppendUtf8(uint32_t codepoint, std::string& out)
        {
            if (codepoint <= 0x7f)
            {
                out.push_back(static_cast<char>(codepoint));
            }
            else if (codepoint <= 0x7ff)
            {
                out.push_back(static_cast<char>(0xc0 | (codepoint >> 6)));
                out.push_back(static_cast<char>(0x80 | (codepoint & 0x3f)));
            }
            else if (codepoint <= 0xffff)
            {
                out.push_back(static_cast<char>(0xe0 | (codepoint >> 12)));
                out.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3f)));
                out.push_back(static_cast<char>(0x80 | (codepoint & 0x3f)));
            }
            else
            {
                out.push_back(static_cast<char>(0xf0 | (codepoint >> 18)));
                out.push_back(static_cast<char>(0x80 | ((codepoint >> 12) & 0x3f)));
                out.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3f)));
                out.push_back(static_cast<char>(0x80 | (codepoint & 0x3f)));
            }
        }
    }

    bool MemoryReader::CanRead(const void* address, size_t size) const
    {
        if (!address || size == 0 || !IsReadable)
            return false;
        return IsReadable(address, size, Context);
    }

    const FieldLayout* FindSupportedLayout(std::string_view binarySha256)
    {
        if (binarySha256 == kShooterGameServerLayout.BinarySha256)
            return &kShooterGameServerLayout;
        return nullptr;
    }

    ReadOptions MakeReadOptionsForBinary(std::string_view binarySha256, bool enabled)
    {
        ReadOptions options;
        options.Enabled = enabled;
        options.Layout = FindSupportedLayout(binarySha256);
        return options;
    }

    ReadResult ReadResult::Ok()
    {
        return {};
    }

    ReadResult ReadResult::Fail(ReadStatus status, std::string reason)
    {
        return {status, std::move(reason)};
    }

    ReadResult TryReadUObject(const MemoryReader& reader,
                              const FieldLayout& layout,
                              const void* object,
                              UObjectView& out)
    {
        if (!object)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "null UObject pointer");
        if (!IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(object)))
            return ReadResult::Fail(ReadStatus::Implausible, "UObject pointer is not canonical");

        UObjectView value;
        value.Address = object;

        if (ReadResult result = ReadAt(reader, object, layout.UObjectVTable, value.VTable); !result)
            return result;
        if (ReadResult result = ReadAt(reader, object, layout.UObjectObjectFlags, value.ObjectFlags); !result)
            return result;
        if (ReadResult result = ReadAt(reader, object, layout.UObjectInternalIndex, value.InternalIndex); !result)
            return result;
        if (ReadResult result = ReadAt(reader, object, layout.UObjectClassPrivate, value.ClassPrivate); !result)
            return result;
        if (ReadResult result = ReadAt(reader, object, layout.UObjectNamePrivate, value.NamePrivate); !result)
            return result;
        if (ReadResult result = ReadAt(reader, object, layout.UObjectOuterPrivate, value.OuterPrivate); !result)
            return result;

        if (!IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(value.VTable)))
            return ReadResult::Fail(ReadStatus::Implausible, "UObject vtable is not canonical");
        if (value.ObjectFlags < 0)
            return ReadResult::Fail(ReadStatus::Implausible, "UObject flags are negative");
        if (value.InternalIndex < -1 || value.InternalIndex >= 10000000)
            return ReadResult::Fail(ReadStatus::Implausible, "UObject internal index is implausible");
        if (!IsNullOrCanonical(value.ClassPrivate))
            return ReadResult::Fail(ReadStatus::Implausible, "UObject class pointer is not canonical");
        if (!IsPlausibleFName(value.NamePrivate))
            return ReadResult::Fail(ReadStatus::Implausible, "UObject FName is implausible");
        if (!IsNullOrCanonical(value.OuterPrivate))
            return ReadResult::Fail(ReadStatus::Implausible, "UObject outer pointer is not canonical");

        out = value;
        return ReadResult::Ok();
    }

    ReadResult TryReadUFunction(const MemoryReader& reader,
                                const ReadOptions& options,
                                const void* function,
                                UFunctionView& out)
    {
        if (ReadResult gate = ValidateGate(options); !gate)
            return gate;
        if (!function)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "null UFunction pointer");

        UObjectView object;
        if (ReadResult result = TryReadUObject(reader, *options.Layout, function, object); !result)
            return result;

        UFunctionView value;
        value.Address = function;
        value.Object = object;

        if (ReadResult result = ReadAt(reader, function, options.Layout->UStructChildren, value.Children); !result)
            return result;
        if (ReadResult result = ReadAt(reader, function, options.Layout->UFunctionFunctionFlags, value.FunctionFlags); !result)
            return result;
        if (ReadResult result = ReadAt(reader, function, options.Layout->UFunctionNumParms, value.NumParms); !result)
            return result;
        if (ReadResult result = ReadAt(reader, function, options.Layout->UFunctionParmsSize, value.ParmsSize); !result)
            return result;
        if (ReadResult result = ReadAt(reader, function, options.Layout->UFunctionReturnValueOffset, value.ReturnValueOffset); !result)
            return result;

        if (!IsNullOrCanonical(value.Children))
            return ReadResult::Fail(ReadStatus::Implausible, "UStruct Children pointer is not canonical");
        if (options.RequireNonZeroFunctionFlags && value.FunctionFlags == 0)
            return ReadResult::Fail(ReadStatus::Implausible, "UFunction FunctionFlags is zero");
        if (value.NumParms > options.MaxProperties)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "UFunction NumParms exceeds MaxProperties");
        if (value.ParmsSize > options.MaxParmsSize)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "UFunction ParmsSize exceeds MaxParmsSize");
        if (value.NumParms > 0 && value.ParmsSize == 0)
            return ReadResult::Fail(ReadStatus::Implausible, "UFunction has params with zero ParmsSize");
        if (value.NumParms > 0 && !value.Children)
            return ReadResult::Fail(ReadStatus::Implausible, "UFunction has params with null Children");
        if (value.ReturnValueOffset != 0xffff && value.ReturnValueOffset >= value.ParmsSize)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "ReturnValueOffset exceeds ParmsSize");

        value.Parameters.reserve(value.NumParms);
        std::vector<const void*> visited;
        visited.reserve(value.NumParms);
        const void* current = value.Children;
        for (uint16_t i = 0; i < value.NumParms; ++i)
        {
            if (!current)
                return ReadResult::Fail(ReadStatus::Implausible, "property chain ended before NumParms");
            if (std::find(visited.begin(), visited.end(), current) != visited.end())
                return ReadResult::Fail(ReadStatus::Implausible, "property chain cycle detected");
            visited.push_back(current);

            UPropertyView property;
            if (ReadResult result = ReadProperty(reader, options, function, current, value.ParmsSize, property); !result)
                return result;

            current = property.Next;
            value.Parameters.push_back(std::move(property));
        }

        if (current)
            return ReadResult::Fail(ReadStatus::Implausible, "property chain continues past NumParms");

        out = std::move(value);
        return ReadResult::Ok();
    }

    ReadResult TryGetParameterRange(const MemoryReader& reader,
                                    const void* params,
                                    uint16_t parmsSize,
                                    const UPropertyView& property,
                                    size_t maxBytes,
                                    ParamRange& out)
    {
        if (!params)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "null params pointer");
        if (property.OffsetInternal < 0 || property.ByteSize == 0)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "invalid property range");
        if (property.ByteSize > maxBytes)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "property range exceeds maxBytes");

        const auto offset = static_cast<size_t>(property.OffsetInternal);
        if (offset > parmsSize || property.ByteSize > static_cast<size_t>(parmsSize) - offset)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "property range exceeds ParmsSize");
        if (AddWouldOverflow(reinterpret_cast<size_t>(params), offset))
            return ReadResult::Fail(ReadStatus::OutOfBounds, "parameter address overflow");

        const auto* data = reinterpret_cast<const uint8_t*>(params) + offset;
        if (!reader.CanRead(data, property.ByteSize))
            return ReadResult::Fail(ReadStatus::Unreadable, "parameter range is unreadable");

        out = {data, property.ByteSize};
        return ReadResult::Ok();
    }

    bool IsPlausibleFStringHeader(const FStringHeaderCandidate& header, int32_t maxChars)
    {
        if (maxChars <= 0)
            return false;
        if (header.ArrayNum == 0 && header.ArrayMax == 0 && header.Data == nullptr)
            return true;
        if (!header.Data)
            return false;
        if (!IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(header.Data)))
            return false;
        if (header.ArrayNum <= 0 || header.ArrayNum > maxChars)
            return false;
        if (header.ArrayMax < header.ArrayNum || header.ArrayMax > maxChars * 2)
            return false;
        return true;
    }

    ReadResult TryReadFStringHeaderFromBuffer(const uint8_t* buffer,
                                              size_t bufferSize,
                                              size_t offset,
                                              FStringHeaderCandidate& out)
    {
        if (!buffer)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "null buffer");
        constexpr size_t kHeaderSize = sizeof(void*) + sizeof(int32_t) + sizeof(int32_t);
        if (offset > bufferSize || kHeaderSize > bufferSize - offset)
            return ReadResult::Fail(ReadStatus::OutOfBounds, "FString header exceeds buffer");

        FStringHeaderCandidate value;
        const uint8_t* cursor = buffer + offset;
        std::memcpy(&value.Data, cursor, sizeof(value.Data));
        cursor += sizeof(value.Data);
        std::memcpy(&value.ArrayNum, cursor, sizeof(value.ArrayNum));
        cursor += sizeof(value.ArrayNum);
        std::memcpy(&value.ArrayMax, cursor, sizeof(value.ArrayMax));

        out = value;
        return ReadResult::Ok();
    }

    ReadResult TryDecodeFStringUtf32(const MemoryReader& reader,
                                     const FStringHeaderCandidate& header,
                                     int32_t maxChars,
                                     std::string& out)
    {
        out.clear();
        if (maxChars <= 0)
            return ReadResult::Fail(ReadStatus::InvalidArgument, "maxChars must be positive");
        if (header.ArrayNum == 0 && header.ArrayMax == 0 && header.Data == nullptr)
            return ReadResult::Ok();
        if (!IsPlausibleFStringHeader(header, maxChars))
            return ReadResult::Fail(ReadStatus::Implausible, "FString header is implausible");

        const auto charCount = static_cast<size_t>(header.ArrayNum);
        if (charCount > std::numeric_limits<size_t>::max() / sizeof(uint32_t))
            return ReadResult::Fail(ReadStatus::OutOfBounds, "FString byte size overflow");
        const size_t byteSize = charCount * sizeof(uint32_t);
        if (!reader.CanRead(header.Data, byteSize))
            return ReadResult::Fail(ReadStatus::Unreadable, "FString data is unreadable");

        const auto* cursor = static_cast<const uint8_t*>(header.Data);
        for (size_t i = 0; i < charCount; ++i)
        {
            uint32_t codepoint = 0;
            std::memcpy(&codepoint, cursor + i * sizeof(uint32_t), sizeof(codepoint));

            if (i == charCount - 1)
            {
                if (codepoint != 0)
                    return ReadResult::Fail(ReadStatus::Implausible, "FString is not NUL terminated");
                break;
            }

            if (codepoint == 0)
                return ReadResult::Fail(ReadStatus::Implausible, "FString contains an early NUL");
            if (IsInvalidUnicodeScalar(codepoint))
                return ReadResult::Fail(ReadStatus::Implausible, "FString contains an invalid UTF-32 codepoint");

            AppendUtf8(codepoint, out);
        }

        return ReadResult::Ok();
    }
}
