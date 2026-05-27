#include "ProcessEventChatReflection.h"

#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventChatReflection
{
    Gate EvaluateGate(const char* enableChatReflection, const char* binarySha256)
    {
        if (!enableChatReflection || std::strcmp(enableChatReflection, "1") != 0)
            return {};

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

            Obelisk::UE::RuntimeReflection::FStringHeaderCandidate header;
            Obelisk::UE::RuntimeReflection::ReadResult headerResult =
                Obelisk::UE::RuntimeReflection::TryReadFStringHeaderFromBuffer(
                    candidate.Range.Data, candidate.Range.Size, 0, header);
            if (!headerResult)
                return headerResult;

            return Obelisk::UE::RuntimeReflection::TryDecodeFStringUtf32(reader, header, maxChars, out);
        }

        return Obelisk::UE::RuntimeReflection::ReadResult::Fail(
            Obelisk::UE::RuntimeReflection::ReadStatus::InvalidArgument,
            "chat field is not present in invocation");
    }

    void SanitizeTextForLog(std::string_view text, std::string& out, size_t maxLoggedBytes)
    {
        out.clear();
        if (maxLoggedBytes == 0)
            return;

        out.reserve(text.size() < maxLoggedBytes ? text.size() : maxLoggedBytes);
        bool truncated = false;
        for (size_t i = 0; i < text.size();)
        {
            const unsigned char byte = static_cast<unsigned char>(text[i]);
            if (out.size() >= maxLoggedBytes)
            {
                truncated = true;
                break;
            }

            if (byte == '"' || byte == '\\')
            {
                if (out.size() + 2 > maxLoggedBytes)
                {
                    truncated = true;
                    break;
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
                    break;
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
                break;
            }
            out.append(text.substr(i, sequenceLength));
            i += sequenceLength;
        }
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
