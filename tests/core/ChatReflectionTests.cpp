#include "ue/ChatReflection.h"

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

    constexpr int32_t kServerSendChatMessageNameIndex = 2697;
    constexpr int32_t kServerChatNameIndex = 9619;
    constexpr int32_t kServerChatToNameIndex = 9620;
    constexpr int32_t kServerChatToPlayerNameIndex = 9621;
    constexpr int32_t kChatMessageNameIndex = 588;
    constexpr int32_t kMessageTextNameIndex = 21409;
    constexpr int32_t kSendModeNameIndex = 16753;
    constexpr int32_t kSteamIDNameIndex = 20681;
    constexpr int32_t kPlayerNameNameIndex = 16693;
    constexpr int32_t kBytePropertyClassNameIndex = 1;
    constexpr int32_t kBytePropertyClassObjectIndex = 533;
    constexpr int32_t kStrPropertyClassNameIndex = 13;
    constexpr int32_t kStrPropertyClassObjectIndex = 547;

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
    };

    bool RegionReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
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

    struct ChatFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x40> BytePropertyClass{};
        std::array<uint8_t, 0x40> StrPropertyClass{};
        std::array<uint8_t, 0x20> Params{};
        ReaderContext Context;

        MemoryReader Reader()
        {
            Context.Regions.clear();
            Context.Regions.push_back({Function.data(), Function.size()});
            Context.Regions.push_back({PropertyA.data(), PropertyA.size()});
            Context.Regions.push_back({PropertyB.data(), PropertyB.size()});
            Context.Regions.push_back({BytePropertyClass.data(), BytePropertyClass.size()});
            Context.Regions.push_back({StrPropertyClass.data(), StrPropertyClass.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    void BuildFunction(ChatFixture& fixture,
                       int32_t functionNameIndex,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       int32_t firstPropertyNameIndex,
                       int32_t firstOffset,
                       int32_t secondPropertyNameIndex = -1,
                       int32_t secondOffset = -1,
                       int32_t firstElementSize = 0x10,
                       int32_t secondElementSize = 0x10,
                       const void* firstPropertyClass = nullptr,
                       const void* secondPropertyClass = nullptr)
    {
        WriteObject(fixture.BytePropertyClass,
                    kBytePropertyClassNameIndex,
                    kBytePropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.StrPropertyClass,
                    kStrPropertyClassNameIndex,
                    kStrPropertyClassObjectIndex,
                    nullptr,
                    nullptr);

        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    reinterpret_cast<const void*>(0x20000),
                    reinterpret_cast<const void*>(0x30000));

        const void* second = numParms > 1 ? fixture.PropertyB.data() : nullptr;
        WriteProperty(fixture.PropertyA,
                      second,
                      fixture.Function.data(),
                      firstPropertyClass ? firstPropertyClass : fixture.StrPropertyClass.data(),
                      firstPropertyNameIndex,
                      firstOffset,
                      firstElementSize);

        if (numParms > 1)
        {
            WriteProperty(fixture.PropertyB,
                          nullptr,
                          fixture.Function.data(),
                          secondPropertyClass ? secondPropertyClass : fixture.StrPropertyClass.data(),
                          secondPropertyNameIndex,
                          secondOffset,
                          secondElementSize);
        }

        const void* children = fixture.PropertyA.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(fixture.Function, 0x38, children);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    ReadOptions Options()
    {
        return MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
    }

    void TestRecognizesServerChatWithBorrowedRange()
    {
        ChatFixture fixture;
        BuildFunction(fixture, kServerChatNameIndex, 1, 0x10, kMessageTextNameIndex, 0x00);
        fixture.Params[0] = 0x42;

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ChatReflection::ChatFunction::ServerChat, "ServerChat kind mismatch");
        Require(invocation.FunctionNameIndex == kServerChatNameIndex, "ServerChat FName mismatch");
        Require(invocation.HasParameterRanges, "params range flag not set");
        Require(invocation.Fields.size() == 1, "ServerChat field count mismatch");
        Require(invocation.Fields[0].Field == ChatReflection::ChatField::MessageText, "ServerChat field mismatch");
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(), "ServerChat range pointer mismatch");
        Require(invocation.Fields[0].Range.Size == 0x10, "ServerChat range size mismatch");
    }

    void TestRecognizesServerChatToWithoutParams()
    {
        ChatFixture fixture;
        BuildFunction(fixture,
                      kServerChatToNameIndex,
                      2,
                      0x20,
                      kSteamIDNameIndex,
                      0x00,
                      kMessageTextNameIndex,
                      0x10);

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            nullptr,
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ChatReflection::ChatFunction::ServerChatTo, "ServerChatTo kind mismatch");
        Require(!invocation.HasParameterRanges, "params range flag set for null params");
        Require(invocation.Fields.size() == 2, "ServerChatTo field count mismatch");
        Require(invocation.Fields[0].Field == ChatReflection::ChatField::SteamID, "SteamID field mismatch");
        Require(invocation.Fields[0].Range.Data == nullptr, "null params produced range data");
        Require(invocation.Fields[1].Field == ChatReflection::ChatField::MessageText, "MessageText field mismatch");
    }

    void TestRecognizesServerChatToPlayer()
    {
        ChatFixture fixture;
        BuildFunction(fixture,
                      kServerChatToPlayerNameIndex,
                      2,
                      0x20,
                      kPlayerNameNameIndex,
                      0x00,
                      kMessageTextNameIndex,
                      0x10);

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ChatReflection::ChatFunction::ServerChatToPlayer,
                "ServerChatToPlayer kind mismatch");
        Require(invocation.Fields.size() == 2, "ServerChatToPlayer field count mismatch");
        Require(invocation.Fields[0].Field == ChatReflection::ChatField::PlayerName, "PlayerName field mismatch");
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x10,
                "ServerChatToPlayer MessageText range pointer mismatch");
    }

    void TestRecognizesServerSendChatMessage()
    {
        ChatFixture fixture;
        BuildFunction(fixture,
                      kServerSendChatMessageNameIndex,
                      2,
                      0x11,
                      kChatMessageNameIndex,
                      0x00,
                      kSendModeNameIndex,
                      0x10,
                      0x10,
                      0x1,
                      fixture.StrPropertyClass.data(),
                      fixture.BytePropertyClass.data());
        fixture.Params[0x10] = 0x02;

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ChatReflection::ChatFunction::ServerSendChatMessage,
                "ServerSendChatMessage kind mismatch");
        Require(invocation.FunctionNameIndex == kServerSendChatMessageNameIndex,
                "ServerSendChatMessage FName mismatch");
        Require(invocation.Fields.size() == 2, "ServerSendChatMessage field count mismatch");
        Require(invocation.Fields[0].Field == ChatReflection::ChatField::ChatMessage,
                "ChatMessage field mismatch");
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(),
                "ChatMessage range pointer mismatch");
        Require(invocation.Fields[0].Range.Size == 0x10, "ChatMessage range size mismatch");
        Require(invocation.Fields[1].Field == ChatReflection::ChatField::SendMode, "SendMode field mismatch");
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x10,
                "SendMode range pointer mismatch");
        Require(invocation.Fields[1].Range.Size == 0x1, "SendMode range size mismatch");

        uint8_t sendMode = 0xff;
        Require(ChatReflection::TryGetSendMode(invocation, sendMode), "SendMode helper failed");
        Require(sendMode == 0x02, "SendMode helper returned wrong byte");
    }

    void TestRejectsSameFNameWithWrongShape()
    {
        ChatFixture fixture;
        BuildFunction(fixture,
                      kServerChatNameIndex,
                      2,
                      0x20,
                      kSteamIDNameIndex,
                      0x00,
                      kMessageTextNameIndex,
                      0x10);

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "wrong ServerChat shape was accepted");
    }

    void TestRejectsSameFNameWithWrongPropertyName()
    {
        ChatFixture fixture;
        BuildFunction(fixture, kServerChatNameIndex, 1, 0x10, kSteamIDNameIndex, 0x00);

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "wrong ServerChat property name was accepted");
    }

    void TestRejectsWrongStrPropertyClass()
    {
        ChatFixture fixture;
        BuildFunction(fixture, kServerChatNameIndex, 1, 0x10, kMessageTextNameIndex, 0x00);
        WriteObject(fixture.StrPropertyClass, 999, kStrPropertyClassObjectIndex, nullptr, nullptr);

        ChatReflection::ChatInvocation invocation;
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "wrong StrProperty class was accepted");
    }

    void TestGateRejectsBeforeReading()
    {
        ChatFixture fixture;
        BuildFunction(fixture, kServerChatNameIndex, 1, 0x10, kMessageTextNameIndex, 0x00);

        ChatReflection::ChatInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled chat reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = ChatReflection::TryIdentifyChatInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported chat reflection was accepted");
    }
}

int main()
{
    TestRecognizesServerChatWithBorrowedRange();
    TestRecognizesServerChatToWithoutParams();
    TestRecognizesServerChatToPlayer();
    TestRecognizesServerSendChatMessage();
    TestRejectsSameFNameWithWrongShape();
    TestRejectsSameFNameWithWrongPropertyName();
    TestRejectsWrongStrPropertyClass();
    TestGateRejectsBeforeReading();

    std::cout << "ChatReflectionTests passed\n";
    return 0;
}
