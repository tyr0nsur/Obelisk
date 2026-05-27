#include "hooks/ProcessEventChatReflection.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace
{
    thread_local bool g_CountAllocations = false;
    thread_local uint64_t g_AllocationCount = 0;
}

void* operator new(std::size_t size)
{
    if (void* ptr = std::malloc(size == 0 ? 1 : size))
    {
        if (g_CountAllocations)
            ++g_AllocationCount;
        return ptr;
    }
    throw std::bad_alloc();
}

void* operator new[](std::size_t size)
{
    return operator new(size);
}

void operator delete(void* ptr) noexcept
{
    std::free(ptr);
}

void operator delete[](void* ptr) noexcept
{
    std::free(ptr);
}

void operator delete(void* ptr, std::size_t) noexcept
{
    std::free(ptr);
}

void operator delete[](void* ptr, std::size_t) noexcept
{
    std::free(ptr);
}

namespace
{
    using namespace Obelisk::Hooks::ProcessEventChatReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kServerSendChatMessageNameIndex = 2697;
    constexpr int32_t kChatMessageNameIndex = 588;
    constexpr int32_t kSendModeNameIndex = 16753;
    constexpr int32_t kBytePropertyClassNameIndex = 1;
    constexpr int32_t kBytePropertyClassObjectIndex = 533;
    constexpr int32_t kStrPropertyClassNameIndex = 13;
    constexpr int32_t kStrPropertyClassObjectIndex = 547;
    constexpr char kFixtureChatText[] =
        "Obelisk benchmark message that exceeds small string optimization storage.";

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
        uint64_t Calls = 0;
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

    template <typename T, size_t N>
    void WriteAt(std::array<uint8_t, N>& buffer, size_t offset, const T& value)
    {
        if (offset > buffer.size() || sizeof(T) > buffer.size() - offset)
            throw std::runtime_error("benchmark fixture write out of bounds");
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

    struct Fixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x40> BytePropertyClass{};
        std::array<uint8_t, 0x40> StrPropertyClass{};
        std::array<uint8_t, 0x20> Params{};
        std::array<uint32_t, 128> FStringData{};
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

    Gate DisabledGate()
    {
        return {};
    }

    void BuildServerSendChatMessage(Fixture& fixture)
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
                      0x00,
                      0x10);
        WriteProperty(fixture.PropertyB,
                      nullptr,
                      fixture.Function.data(),
                      fixture.BytePropertyClass.data(),
                      kSendModeNameIndex,
                      0x10,
                      0x1);

        const size_t textLength = sizeof(kFixtureChatText) - 1;
        if (textLength + 1 > fixture.FStringData.size())
            throw std::runtime_error("benchmark fixture chat text is too long");
        for (size_t i = 0; i < textLength; ++i)
            fixture.FStringData[i] = static_cast<uint8_t>(kFixtureChatText[i]);
        fixture.FStringData[textLength] = 0;
        const FStringHeaderCandidate header{
            fixture.FStringData.data(),
            static_cast<int32_t>(textLength + 1),
            static_cast<int32_t>(textLength + 1),
        };
        WriteAt(fixture.Params, 0x00, header);
        fixture.Params[0x10] = 0;

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

    bool ReadNameIndexLikeHook(const MemoryReader& reader, void* function, int32_t& out)
    {
        const auto* name = static_cast<const uint8_t*>(function) + 0x18;
        if (!reader.CanRead(name, sizeof(FNameValue)))
            return false;

        FNameValue value;
        std::memcpy(&value, name, sizeof(value));
        out = value.ComparisonIndex;
        return true;
    }

    std::string SanitizeForSyntheticLog(std::string text)
    {
        std::string out;
        out.reserve(text.size());
        for (char ch : text)
        {
            if (ch == '"' || ch == '\\')
            {
                out.push_back('\\');
                out.push_back(ch);
                continue;
            }
            if (static_cast<unsigned char>(ch) < 0x20)
            {
                out.push_back('?');
                continue;
            }
            out.push_back(ch);
        }
        return out;
    }

    struct HookLikeOptions
    {
        const Gate* ChatGate = nullptr;
        bool HasCallbacks = false;
        bool DecodeText = false;
    };

    bool RunHookLikePath(const HookLikeOptions& options,
                         const MemoryReader& reader,
                         void* function,
                         void* params)
    {
        const bool chatReflectionEnabled = options.ChatGate && options.ChatGate->Enabled();
        int32_t nameIndex = -1;
        if ((options.HasCallbacks || chatReflectionEnabled) &&
            !ReadNameIndexLikeHook(reader, function, nameIndex))
        {
            return false;
        }

        const Gate disabledGate = DisabledGate();
        const Gate& chatGate = options.ChatGate ? *options.ChatGate : disabledGate;
        Attempt attempt = TryIdentifyInvocation(chatGate, nameIndex, reader, function, params);
        if (attempt.Status != AttemptStatus::Matched)
            return attempt.Status == AttemptStatus::Disabled ||
                   attempt.Status == AttemptStatus::NonChatFunction;

        uint8_t sendMode = 0xff;
        if (!ChatReflection::TryGetSendMode(attempt.Invocation, sendMode) ||
            !ChatReflection::IsKnownSendMode(sendMode))
        {
            return false;
        }

        if (options.DecodeText)
        {
            std::string text;
            ReadResult result = TryDecodeUtf32Field(
                reader, attempt.Invocation, ChatReflection::ChatField::ChatMessage, 512, text);
            if (!result)
                return false;
            volatile size_t sanitizedSize = SanitizeForSyntheticLog(std::move(text)).size();
            (void)sanitizedSize;
        }

        return true;
    }

    uint64_t Percentile(const std::vector<uint64_t>& sorted, double percentile)
    {
        if (sorted.empty())
            return 0;
        const double rank = percentile * static_cast<double>(sorted.size() - 1);
        return sorted[static_cast<size_t>(rank)];
    }

    template <typename Fn>
    void RunCase(const char* name, int iterations, ReaderContext& context, Fn&& fn)
    {
        context.Calls = 0;
        std::vector<uint64_t> samples;
        samples.reserve(static_cast<size_t>(iterations));
        uint64_t accepted = 0;
        g_AllocationCount = 0;
        g_CountAllocations = true;
        for (int i = 0; i < iterations; ++i)
        {
            auto start = std::chrono::steady_clock::now();
            accepted += fn() ? 1 : 0;
            auto end = std::chrono::steady_clock::now();
            samples.push_back(static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count()));
        }
        g_CountAllocations = false;
        std::sort(samples.begin(), samples.end());
        uint64_t total = 0;
        for (uint64_t sample : samples)
            total += sample;

        std::cout << name
                  << " iterations=" << iterations
                  << " ns_avg=" << (total / static_cast<uint64_t>(iterations))
                  << " ns_min=" << samples.front()
                  << " ns_p50=" << Percentile(samples, 0.50)
                  << " ns_p95=" << Percentile(samples, 0.95)
                  << " ns_p99=" << Percentile(samples, 0.99)
                  << " ns_max=" << samples.back()
                  << " reader_calls_per_iter=" << (context.Calls / static_cast<uint64_t>(iterations))
                  << " allocations=" << g_AllocationCount
                  << " allocations_per_iter=" << (g_AllocationCount / static_cast<uint64_t>(iterations))
                  << " accepted=" << accepted
                  << "\n";
    }
}

int main(int argc, char** argv)
{
    int iterations = 100000;
    if (argc > 1)
        iterations = std::stoi(argv[1]);
    if (iterations <= 0)
        throw std::runtime_error("iterations must be positive");

    Fixture fixture;
    BuildServerSendChatMessage(fixture);
    MemoryReader reader = fixture.Reader();

    Fixture nonChatFixture;
    BuildServerSendChatMessage(nonChatFixture);
    WriteAt(nonChatFixture.Function, 0x18, FNameValue{42, 0});
    MemoryReader nonChatReader = nonChatFixture.Reader();

    const Gate gate = EnabledGate();
    const Gate disabledGate = DisabledGate();

    RunCase("non_chat_filter", iterations, fixture.Context, [&] {
        Attempt attempt = TryIdentifyInvocation(
            gate, 42, reader, fixture.Function.data(), fixture.Params.data());
        return attempt.Status == AttemptStatus::NonChatFunction;
    });

    RunCase("server_send_chat_match", iterations, fixture.Context, [&] {
        Attempt attempt = TryIdentifyInvocation(
            gate, kServerSendChatMessageNameIndex, reader, fixture.Function.data(), fixture.Params.data());
        return attempt.Status == AttemptStatus::Matched;
    });

    ChatReflection::ChatInvocation invocation;
    Attempt attempt = TryIdentifyInvocation(
        gate, kServerSendChatMessageNameIndex, reader, fixture.Function.data(), fixture.Params.data());
    if (attempt.Status == AttemptStatus::Matched)
        invocation = std::move(attempt.Invocation);

    RunCase("server_send_chat_decode_utf32", iterations, fixture.Context, [&] {
        std::string out;
        ReadResult result = TryDecodeUtf32Field(
            reader, invocation, ChatReflection::ChatField::ChatMessage, 512, out);
        return result.Status == ReadStatus::Ok && out == kFixtureChatText;
    });

    RunCase("hook_like_disabled", iterations, fixture.Context, [&] {
        return RunHookLikePath(
            {&disabledGate, false, false}, reader, fixture.Function.data(), fixture.Params.data());
    });

    RunCase("hook_like_enabled_non_chat", iterations, nonChatFixture.Context, [&] {
        return RunHookLikePath(
            {&gate, false, false}, nonChatReader, nonChatFixture.Function.data(), nonChatFixture.Params.data());
    });

    RunCase("hook_like_server_send_chat", iterations, fixture.Context, [&] {
        return RunHookLikePath(
            {&gate, false, false}, reader, fixture.Function.data(), fixture.Params.data());
    });

    RunCase("hook_like_server_send_chat_text", iterations, fixture.Context, [&] {
        return RunHookLikePath(
            {&gate, false, true}, reader, fixture.Function.data(), fixture.Params.data());
    });

    return 0;
}
