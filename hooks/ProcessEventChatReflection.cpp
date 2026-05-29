#include "ProcessEventChatReflection.h"

#include <cstring>
#include <limits>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventChatReflection
{
    namespace
    {
        bool IsInvalidUnicodeScalar(uint32_t codepoint)
        {
            return codepoint > 0x10ffff || (codepoint >= 0xd800 && codepoint <= 0xdfff);
        }

        size_t EncodeUtf8(uint32_t codepoint, char (&buffer)[4])
        {
            if (codepoint <= 0x7f)
            {
                buffer[0] = static_cast<char>(codepoint);
                return 1;
            }
            if (codepoint <= 0x7ff)
            {
                buffer[0] = static_cast<char>(0xc0 | (codepoint >> 6));
                buffer[1] = static_cast<char>(0x80 | (codepoint & 0x3f));
                return 2;
            }
            if (codepoint <= 0xffff)
            {
                buffer[0] = static_cast<char>(0xe0 | (codepoint >> 12));
                buffer[1] = static_cast<char>(0x80 | ((codepoint >> 6) & 0x3f));
                buffer[2] = static_cast<char>(0x80 | (codepoint & 0x3f));
                return 3;
            }

            buffer[0] = static_cast<char>(0xf0 | (codepoint >> 18));
            buffer[1] = static_cast<char>(0x80 | ((codepoint >> 12) & 0x3f));
            buffer[2] = static_cast<char>(0x80 | ((codepoint >> 6) & 0x3f));
            buffer[3] = static_cast<char>(0x80 | (codepoint & 0x3f));
            return 4;
        }

        void AppendSanitizedUtf8(std::string_view text, std::string& out, size_t maxLoggedBytes, bool& truncated)
        {
            for (size_t i = 0; i < text.size();)
            {
                const unsigned char byte = static_cast<unsigned char>(text[i]);
                if (out.size() >= maxLoggedBytes)
                {
                    truncated = true;
                    return;
                }

                if (byte == '"' || byte == '\\')
                {
                    if (out.size() + 2 > maxLoggedBytes)
                    {
                        truncated = true;
                        return;
                    }
                    out.push_back('\\');
                    out.push_back(static_cast<char>(byte));
                    ++i;
                    continue;
                }
                if (byte < 0x20 || byte == 0x7f)
                {
                    const std::string_view replacement = byte == '\n' ? std::string_view{"\\n"} : std::string_view{"?"};
                    if (out.size() + replacement.size() > maxLoggedBytes)
                    {
                        truncated = true;
                        return;
                    }
                    out.append(replacement);
                    ++i;
                    continue;
                }

                size_t sequenceLength = 1;
                if ((byte & 0xe0) == 0xc0)
                    sequenceLength = 2;
                else if ((byte & 0xf0) == 0xe0)
                    sequenceLength = 3;
                else if ((byte & 0xf8) == 0xf0)
                    sequenceLength = 4;
                if (sequenceLength > text.size() - i || out.size() + sequenceLength > maxLoggedBytes)
                {
                    truncated = true;
                    return;
                }
                out.append(text.substr(i, sequenceLength));
                i += sequenceLength;
            }
        }

        Obelisk::UE::RuntimeReflection::ReadResult ReadChatFieldFStringHeader(
            const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
            Obelisk::UE::ChatReflection::ChatField field,
            Obelisk::UE::RuntimeReflection::FStringHeaderCandidate& header)
        {
            for (const Obelisk::UE::ChatReflection::ChatFieldRange& candidate : invocation.Fields)
            {
                if (candidate.Field != field)
                    continue;
                if (!candidate.Range.Data || candidate.Range.Size == 0)
                {
                    return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                        Obelisk::UE::RuntimeReflection::ReadStatus::Unreadable,
                        "chat field has no readable parameter range");
                }

                return Obelisk::UE::RuntimeReflection::TryReadFStringHeaderFromBuffer(
                    candidate.Range.Data, candidate.Range.Size, 0, header);
            }

            return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                Obelisk::UE::RuntimeReflection::ReadStatus::InvalidArgument,
                "chat field is not present in invocation");
        }
    }

    Gate EvaluateGate(const char* enableChatReflection, bool observerDebugGateEnabled, const char* binarySha256)
    {
        if (!enableChatReflection || std::strcmp(enableChatReflection, "1") != 0)
            return {};

        if (!observerDebugGateEnabled)
            return {GateStatus::MissingInstanceMarker, {}};

        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};

        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        return {GateStatus::Enabled, binarySha256};
    }

    bool IsReflectedChatNameIndex(int32_t nameIndex)
    {
        return nameIndex == 1865 ||
               nameIndex == 1983 ||
               nameIndex == 1984 ||
               nameIndex == 2697 ||
               nameIndex == 9801 ||
               nameIndex == 9619 ||
               nameIndex == 9620 ||
               nameIndex == 9621 ||
               nameIndex == 28549;
    }

    bool ShouldAttemptObservation(uint64_t limit)
    {
        return limit != 0;
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && observationNumber != 0 && observationNumber <= limit;
    }

    Obelisk::UE::RuntimeReflection::ReadResult TryDecodeUtf32Field(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        Obelisk::UE::ChatReflection::ChatField field,
        int32_t maxChars,
        std::string& out)
    {
        out.clear();
        Obelisk::UE::RuntimeReflection::FStringHeaderCandidate header;
        Obelisk::UE::RuntimeReflection::ReadResult headerResult =
            ReadChatFieldFStringHeader(invocation, field, header);
        if (!headerResult)
            return headerResult;

        return Obelisk::UE::RuntimeReflection::TryDecodeFStringUtf32(reader, header, maxChars, out);
    }

    Obelisk::UE::RuntimeReflection::ReadResult TryDecodeUtf32FieldForLog(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        Obelisk::UE::ChatReflection::ChatField field,
        int32_t maxChars,
        std::string& out,
        size_t maxLoggedBytes)
    {
        out.clear();
        Obelisk::UE::RuntimeReflection::FStringHeaderCandidate header;
        Obelisk::UE::RuntimeReflection::ReadResult headerResult =
            ReadChatFieldFStringHeader(invocation, field, header);
        if (!headerResult)
            return headerResult;

        if (maxChars <= 0)
            return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                Obelisk::UE::RuntimeReflection::ReadStatus::InvalidArgument,
                "maxChars must be positive");
        if (header.ArrayNum == 0 && header.ArrayMax == 0 && header.Data == nullptr)
            return Obelisk::UE::RuntimeReflection::ReadResult::Ok();
        if (!Obelisk::UE::RuntimeReflection::IsPlausibleFStringHeader(header, maxChars))
            return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                "FString header is implausible");

        const auto charCount = static_cast<size_t>(header.ArrayNum);
        if (charCount > std::numeric_limits<size_t>::max() / sizeof(uint32_t))
            return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                Obelisk::UE::RuntimeReflection::ReadStatus::OutOfBounds,
                "FString byte size overflow");
        const size_t byteSize = charCount * sizeof(uint32_t);
        if (!reader.CanRead(header.Data, byteSize))
            return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                Obelisk::UE::RuntimeReflection::ReadStatus::Unreadable,
                "FString data is unreadable");

        out.reserve(charCount - 1 < maxLoggedBytes ? charCount - 1 : maxLoggedBytes);
        bool truncated = false;
        const auto* cursor = static_cast<const uint8_t*>(header.Data);
        for (size_t i = 0; i < charCount; ++i)
        {
            uint32_t codepoint = 0;
            std::memcpy(&codepoint, cursor + i * sizeof(uint32_t), sizeof(codepoint));

            if (i == charCount - 1)
            {
                if (codepoint != 0)
                    return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                        Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                        "FString is not NUL terminated");
                break;
            }

            if (codepoint == 0)
                return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "FString contains an early NUL");
            if (IsInvalidUnicodeScalar(codepoint))
                return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "FString contains an invalid UTF-32 codepoint");

            if (!truncated)
            {
                char encoded[4]{};
                const size_t encodedSize = EncodeUtf8(codepoint, encoded);
                AppendSanitizedUtf8(std::string_view(encoded, encodedSize), out, maxLoggedBytes, truncated);
            }
        }
        if (truncated)
            out += "...";

        return Obelisk::UE::RuntimeReflection::ReadResult::Ok();
    }

    void SanitizeTextForLog(std::string_view text, std::string& out, size_t maxLoggedBytes)
    {
        out.clear();
        if (maxLoggedBytes == 0)
            return;

        out.reserve(text.size() < maxLoggedBytes ? text.size() : maxLoggedBytes);
        bool truncated = false;
        AppendSanitizedUtf8(text, out, maxLoggedBytes, truncated);
        if (truncated)
            out += "...";
    }

    std::string SanitizeTextForLog(std::string_view text, size_t maxLoggedBytes)
    {
        std::string out;
        SanitizeTextForLog(text, out, maxLoggedBytes);
        return out;
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedChatNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonChatFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::ChatReflection::ChatInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result =
            Obelisk::UE::ChatReflection::TryIdentifyChatInvocation(
                reader, options, function, params, invocation);
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }
}
