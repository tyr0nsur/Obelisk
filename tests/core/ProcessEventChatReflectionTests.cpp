#include "hooks/ProcessEventChatReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventChatReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kServerSendChatMessageNameIndex = 2697;
    constexpr int32_t kServerChatNameIndex = 9619;
    constexpr int32_t kServerChatToPlayerNameIndex = 9621;
    constexpr int32_t kClientChatMessageNameIndex = 1865;
    constexpr int32_t kClientServerChatDirectMessageNameIndex = 1983;
    constexpr int32_t kClientServerChatMessageNameIndex = 1984;
    constexpr int32_t kSendServerChatMessageNameIndex = 9801;
    constexpr int32_t kOnServerChatMessageDelegateNameIndex = 28549;
    constexpr int32_t kChatMessageNameIndex = 588;
    constexpr int32_t kMessageTextNameIndex = 21409;
    constexpr int32_t kSendModeNameIndex = 16753;
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
                       int32_t elementSize = 0x10)
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
        std::array<uint32_t, 16> FStringData{};
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
            Context.Regions.push_back(
                {reinterpret_cast<const uint8_t*>(FStringData.data()), FStringData.size() * sizeof(uint32_t)});
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    void BuildServerChatToPlayer(ChatFixture& fixture)
    {
        WriteObject(fixture.StrPropertyClass,
                    kStrPropertyClassNameIndex,
                    kStrPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    kServerChatToPlayerNameIndex,
                    kServerChatToPlayerNameIndex,
                    reinterpret_cast<const void*>(0x20000),
                    reinterpret_cast<const void*>(0x30000));

        WriteProperty(fixture.PropertyA,
                      fixture.PropertyB.data(),
                      fixture.Function.data(),
                      fixture.StrPropertyClass.data(),
                      kPlayerNameNameIndex,
                      0x00);
        WriteProperty(fixture.PropertyB,
                      nullptr,
                      fixture.Function.data(),
                      fixture.StrPropertyClass.data(),
                      kMessageTextNameIndex,
                      0x10);

        const void* children = fixture.PropertyA.data();
        const uint32_t functionFlags = 0x204000;
        const uint16_t numParms = 2;
        const uint16_t parmsSize = 0x20;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(fixture.Function, 0x38, children);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildServerSendChatMessage(ChatFixture& fixture)
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
                    kServerSendChatMessageNameIndex,
                    kServerSendChatMessageNameIndex,
                    reinterpret_cast<const void*>(0x20000),
                    reinterpret_cast<const void*>(0x30000));

        WriteProperty(fixture.PropertyA,
                      fixture.PropertyB.data(),
                      fixture.Function.data(),
                      fixture.StrPropertyClass.data(),
                      kChatMessageNameIndex,
                      0x00);
        WriteProperty(fixture.PropertyB,
                      nullptr,
                      fixture.Function.data(),
                      fixture.BytePropertyClass.data(),
                      kSendModeNameIndex,
                      0x10,
                      0x1);

        const void* children = fixture.PropertyA.data();
        const uint32_t functionFlags = 0x220cc0;
        const uint16_t numParms = 2;
        const uint16_t parmsSize = 0x11;
        const uint16_t returnValueOffset = 0xffff;
        WriteAt(fixture.Function, 0x38, children);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void TestGateEvaluation()
    {
        const char* supportedSha = kSupportedShooterGameServerSha256.data();

        Require(EvaluateGate(nullptr, true, supportedSha).Status == GateStatus::Disabled,
                "missing enable env should disable chat reflection");
        Require(EvaluateGate("0", true, supportedSha).Status == GateStatus::Disabled,
                "non-1 enable env should disable chat reflection");
        Require(EvaluateGate("1", false, supportedSha).Status == GateStatus::MissingInstanceMarker,
                "missing instance marker gate was not rejected");
        Require(EvaluateGate("1", true, nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, "").Status == GateStatus::MissingBinarySha256,
                "empty binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, "not-this-binary").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary SHA gate was not rejected");

        Gate gate = EvaluateGate("1", true, supportedSha);
        Require(gate.Status == GateStatus::Enabled, "supported chat reflection gate did not enable");
        Require(gate.Enabled(), "enabled chat reflection gate did not report enabled");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "enabled gate did not retain binary SHA");
    }

    void TestObservationLogLimit()
    {
        Require(!ShouldAttemptObservation(0), "zero chat reflection log limit should skip observation");
        Require(ShouldAttemptObservation(1), "non-zero chat reflection log limit should allow observation");
        Require(!ShouldLogObservation(0, 25), "zero observation number should not log");
        Require(!ShouldLogObservation(1, 0), "zero chat reflection log limit should disable logs");
        Require(ShouldLogObservation(1, 1), "first observation should log at limit one");
        Require(!ShouldLogObservation(2, 1), "observation beyond limit should not log");
        Require(ShouldLogObservation(25, 25), "observation equal to limit should log");
        Require(!ShouldLogObservation(26, 25), "observation after default limit should not log");
    }

    void TestSanitizesChatTextForLog()
    {
        std::string out;
        SanitizeTextForLog("plain", out);
        Require(out == "plain", "plain text sanitizer mismatch");

        SanitizeTextForLog("quote\"slash\\", out);
        Require(out == "quote\\\"slash\\\\", "quote/backslash sanitizer mismatch");

        SanitizeTextForLog("line\nzero\x01", out);
        Require(out == "line\\nzero?", "control sanitizer mismatch");

        SanitizeTextForLog("abcdef", out, 4);
        Require(out == "abcd...", "truncation sanitizer mismatch");

        SanitizeTextForLog("\xF0\x9F\x98\x80!", out, 4);
        Require(out == "\xF0\x9F\x98\x80...", "utf8 boundary sanitizer mismatch");

        SanitizeTextForLog("\xF0\x9F\x98\x80!", out, 3);
        Require(out == "...", "partial utf8 sanitizer mismatch");
    }

    void TestReflectedChatNameFilterIncludesServerSendChatMessage()
    {
        Require(IsReflectedChatNameIndex(kClientChatMessageNameIndex),
                "ClientChatMessage FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kClientServerChatDirectMessageNameIndex),
                "ClientServerChatDirectMessage FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kClientServerChatMessageNameIndex),
                "ClientServerChatMessage FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kSendServerChatMessageNameIndex),
                "SendServerChatMessage FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kOnServerChatMessageDelegateNameIndex),
                "OnServerChatMessage delegate FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kServerSendChatMessageNameIndex),
                "ServerSendChatMessage FName was not accepted by cheap filter");
        Require(IsReflectedChatNameIndex(kServerChatNameIndex), "ServerChat FName was not accepted by cheap filter");
        Require(!IsReflectedChatNameIndex(42), "unrelated FName was accepted by cheap filter");
    }

    void TestDisabledGateDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            {},
            kServerChatNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Disabled, "disabled gate did not short-circuit");
        Require(context.Calls == 0, "disabled gate touched UFunction memory");
    }

    void TestNonChatNameDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            42,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::NonChatFunction, "non-chat FName did not short-circuit");
        Require(context.Calls == 0, "non-chat FName touched UFunction memory");
    }

    void TestUnreadableChatFunctionIsRejected()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kServerChatNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Rejected, "unreadable chat function was not rejected");
        Require(context.Calls > 0, "chat FName did not attempt bounded reflection read");
    }

    void TestMatchedChatInvocationReturnsBorrowedRanges()
    {
        ChatFixture fixture;
        BuildServerChatToPlayer(fixture);
        fixture.Params[0x10] = 0x42;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kServerChatToPlayerNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(attempt.Invocation.Function == ChatReflection::ChatFunction::ServerChatToPlayer,
                "matched invocation function mismatch");
        Require(attempt.Invocation.Fields.size() == 2, "matched invocation field count mismatch");
        Require(attempt.Invocation.Fields[0].Field == ChatReflection::ChatField::PlayerName,
                "first field should be PlayerName");
        Require(attempt.Invocation.Fields[1].Field == ChatReflection::ChatField::MessageText,
                "second field should be MessageText");
        Require(attempt.Invocation.Fields[1].Range.Data == fixture.Params.data() + 0x10,
                "message range should be borrowed from params");
        Require(fixture.Context.Calls > 0, "matched invocation did not read through injected reader");
    }

    void TestMatchedServerSendChatMessageReturnsByteRange()
    {
        ChatFixture fixture;
        BuildServerSendChatMessage(fixture);
        fixture.Params[0x10] = 0x02;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kServerSendChatMessageNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(attempt.Invocation.Function == ChatReflection::ChatFunction::ServerSendChatMessage,
                "matched ServerSendChatMessage function mismatch");
        Require(attempt.Invocation.Fields.size() == 2, "matched ServerSendChatMessage field count mismatch");
        Require(attempt.Invocation.Fields[0].Field == ChatReflection::ChatField::ChatMessage,
                "first field should be ChatMessage");
        Require(attempt.Invocation.Fields[0].Range.Data == fixture.Params.data(),
                "ChatMessage range should be borrowed from params");
        Require(attempt.Invocation.Fields[1].Field == ChatReflection::ChatField::SendMode,
                "second field should be SendMode");
        Require(attempt.Invocation.Fields[1].Range.Data == fixture.Params.data() + 0x10,
                "SendMode range should be borrowed from params");
        Require(attempt.Invocation.Fields[1].Range.Size == 0x1, "SendMode range size mismatch");
    }

    void TestDecodesServerSendChatMessageText()
    {
        ChatFixture fixture;
        BuildServerSendChatMessage(fixture);
        fixture.FStringData[0] = 'H';
        fixture.FStringData[1] = 'i';
        fixture.FStringData[2] = 0;

        RuntimeReflection::FStringHeaderCandidate header{
            fixture.FStringData.data(),
            3,
            3,
        };
        WriteAt(fixture.Params, 0x00, header);
        fixture.Params[0x10] = 0x00;

        MemoryReader reader = fixture.Reader();
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kServerSendChatMessageNameIndex,
            reader,
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        std::string text;
        RuntimeReflection::ReadResult result = TryDecodeUtf32Field(
            reader,
            attempt.Invocation,
            ChatReflection::ChatField::ChatMessage,
            512,
            text);
        Require(result.Status == RuntimeReflection::ReadStatus::Ok, result.Reason.c_str());
        Require(text == "Hi", "decoded chat text mismatch");

        result = TryDecodeUtf32Field(
            reader,
            attempt.Invocation,
            ChatReflection::ChatField::MessageText,
            512,
            text);
        Require(result.Status == RuntimeReflection::ReadStatus::InvalidArgument,
                "missing chat field did not fail closed");
    }

    void TestDecodesServerSendChatMessageTextForLog()
    {
        ChatFixture fixture;
        BuildServerSendChatMessage(fixture);
        fixture.FStringData[0] = 'Q';
        fixture.FStringData[1] = '"';
        fixture.FStringData[2] = '\n';
        fixture.FStringData[3] = 0x1f600;
        fixture.FStringData[4] = 0;

        RuntimeReflection::FStringHeaderCandidate header{
            fixture.FStringData.data(),
            5,
            5,
        };
        WriteAt(fixture.Params, 0x00, header);
        fixture.Params[0x10] = 0x00;

        MemoryReader reader = fixture.Reader();
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kServerSendChatMessageNameIndex,
            reader,
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        std::string text;
        RuntimeReflection::ReadResult result = TryDecodeUtf32FieldForLog(
            reader,
            attempt.Invocation,
            ChatReflection::ChatField::ChatMessage,
            512,
            text);
        Require(result.Status == RuntimeReflection::ReadStatus::Ok, result.Reason.c_str());
        Require(text == "Q\\\"\\n\xF0\x9F\x98\x80", "sanitized decoded chat text mismatch");

        result = TryDecodeUtf32FieldForLog(
            reader,
            attempt.Invocation,
            ChatReflection::ChatField::ChatMessage,
            512,
            text,
            3);
        Require(result.Status == RuntimeReflection::ReadStatus::Ok, result.Reason.c_str());
        Require(text == "Q\\\"...", "sanitized decoded chat truncation mismatch");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationLogLimit();
    TestSanitizesChatTextForLog();
    TestReflectedChatNameFilterIncludesServerSendChatMessage();
    TestDisabledGateDoesNotRead();
    TestNonChatNameDoesNotRead();
    TestUnreadableChatFunctionIsRejected();
    TestMatchedChatInvocationReturnsBorrowedRanges();
    TestMatchedServerSendChatMessageReturnsByteRange();
    TestDecodesServerSendChatMessageText();
    TestDecodesServerSendChatMessageTextForLog();

    std::cout << "ProcessEventChatReflectionTests passed\n";
    return 0;
}
