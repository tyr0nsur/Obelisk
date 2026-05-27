#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace Obelisk::UE::RuntimeReflection
{
    constexpr std::string_view kSupportedShooterGameServerSha256 =
        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520";

    struct MemoryReader
    {
        using IsReadableFn = bool (*)(const void* address, size_t size, void* context);

        IsReadableFn IsReadable = nullptr;
        void* Context = nullptr;

        bool CanRead(const void* address, size_t size) const;
    };

    struct FieldLayout
    {
        std::string_view BinarySha256;

        size_t UObjectVTable = 0x00;
        size_t UObjectObjectFlags = 0x08;
        size_t UObjectInternalIndex = 0x0c;
        size_t UObjectClassPrivate = 0x10;
        size_t UObjectNamePrivate = 0x18;
        size_t UObjectOuterPrivate = 0x20;

        size_t UFieldNext = 0x28;
        size_t UStructChildren = 0x38;
        size_t UFunctionFunctionFlags = 0x90;
        size_t UFunctionNumParms = 0x96;
        size_t UFunctionParmsSize = 0x98;
        size_t UFunctionReturnValueOffset = 0x9a;

        size_t UPropertyArrayDim = 0x30;
        size_t UPropertyElementSize = 0x34;
        size_t UPropertyPropertyFlags = 0x38;
        size_t UPropertyOffsetInternal = 0x4c;
    };

    const FieldLayout* FindSupportedLayout(std::string_view binarySha256);

    struct ReadOptions
    {
        bool Enabled = false;
        const FieldLayout* Layout = nullptr;
        size_t MaxProperties = 16;
        uint16_t MaxParmsSize = 0x400;
        int32_t MaxArrayDim = 16;
        int32_t MaxElementSize = 0x400;
        bool RequireNonZeroFunctionFlags = true;
    };

    ReadOptions MakeReadOptionsForBinary(std::string_view binarySha256, bool enabled);

    enum class ReadStatus
    {
        Ok,
        Disabled,
        UnsupportedLayout,
        InvalidArgument,
        Unreadable,
        Implausible,
        OutOfBounds,
    };

    struct ReadResult
    {
        ReadStatus Status = ReadStatus::Ok;
        std::string Reason;

        explicit operator bool() const { return Status == ReadStatus::Ok; }
        static ReadResult Ok();
        static ReadResult Fail(ReadStatus status, std::string reason);
    };

    struct FNameValue
    {
        int32_t ComparisonIndex = -1;
        int32_t Number = -1;
    };

    struct UObjectView
    {
        const void* Address = nullptr;
        const void* VTable = nullptr;
        int32_t ObjectFlags = 0;
        int32_t InternalIndex = -1;
        const void* ClassPrivate = nullptr;
        FNameValue NamePrivate;
        const void* OuterPrivate = nullptr;
    };

    struct UPropertyView
    {
        const void* Address = nullptr;
        UObjectView Object;
        const void* Next = nullptr;
        int32_t ArrayDim = 0;
        int32_t ElementSize = 0;
        uint64_t PropertyFlags = 0;
        int32_t OffsetInternal = -1;
        size_t ByteSize = 0;
    };

    template <typename T, size_t CapacityValue>
    struct FixedVector
    {
        std::array<T, CapacityValue> Items{};
        size_t Count = 0;

        size_t size() const { return Count; }
        constexpr size_t capacity() const { return CapacityValue; }
        bool empty() const { return Count == 0; }
        void reserve(size_t) {}
        void clear() { Count = 0; }

        T* begin() { return Items.data(); }
        T* end() { return Items.data() + Count; }
        const T* begin() const { return Items.data(); }
        const T* end() const { return Items.data() + Count; }

        T& operator[](size_t index) { return Items[index]; }
        const T& operator[](size_t index) const { return Items[index]; }

        void push_back(const T& value)
        {
            Items[Count++] = value;
        }

        void push_back(T&& value)
        {
            Items[Count++] = std::move(value);
        }
    };

    struct UFunctionView
    {
        const void* Address = nullptr;
        UObjectView Object;
        const void* Children = nullptr;
        uint32_t FunctionFlags = 0;
        uint16_t NumParms = 0;
        uint16_t ParmsSize = 0;
        uint16_t ReturnValueOffset = 0xffff;
        FixedVector<UPropertyView, 16> Parameters;
    };

    struct ParamRange
    {
        const uint8_t* Data = nullptr;
        size_t Size = 0;
    };

    struct FStringHeaderCandidate
    {
        const void* Data = nullptr;
        int32_t ArrayNum = 0;
        int32_t ArrayMax = 0;
    };

    ReadResult TryReadUObject(const MemoryReader& reader,
                              const FieldLayout& layout,
                              const void* object,
                              UObjectView& out);

    ReadResult TryReadUFunction(const MemoryReader& reader,
                                const ReadOptions& options,
                                const void* function,
                                UFunctionView& out);

    ReadResult TryGetParameterRange(const MemoryReader& reader,
                                    const void* params,
                                    uint16_t parmsSize,
                                    const UPropertyView& property,
                                    size_t maxBytes,
                                    ParamRange& out);

    bool IsPlausibleFStringHeader(const FStringHeaderCandidate& header, int32_t maxChars = 2048);

    ReadResult TryReadFStringHeaderFromBuffer(const uint8_t* buffer,
                                              size_t bufferSize,
                                              size_t offset,
                                              FStringHeaderCandidate& out);

    ReadResult TryDecodeFStringUtf32(const MemoryReader& reader,
                                     const FStringHeaderCandidate& header,
                                     int32_t maxChars,
                                     std::string& out);
}
