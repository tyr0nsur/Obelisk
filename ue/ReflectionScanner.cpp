#include "ReflectionScanner.h"

#include "runtime/Logger.h"
#include "ue/Memory.h"
#include "ue/Reflection.h"

#include <subhook.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <mutex>
#include <vector>

namespace Obelisk::UE
{
    namespace
    {
        struct Mapping
        {
            uintptr_t Start = 0;
            uintptr_t End = 0;
            uintptr_t FileOffset = 0;
            std::string Perms;
            std::string Path;

            bool Readable() const { return !Perms.empty() && Perms[0] == 'r'; }
            bool Executable() const { return Perms.size() > 2 && Perms[2] == 'x'; }
            bool Writable() const { return Perms.size() > 1 && Perms[1] == 'w'; }
            size_t Size() const { return End > Start ? static_cast<size_t>(End - Start) : 0; }
        };

        struct TargetScan
        {
            const char* Name;
            std::vector<uintptr_t> StringAddresses;
            std::vector<uintptr_t> References;
            std::vector<uintptr_t> CandidateGlobals;
        };

        struct GlobalWatch
        {
            std::string Name;
            uintptr_t Address = 0;
        };

        using NativeExecFn = void (*)(void* context, void* stack, void* result);

        struct NativeExecSlot
        {
            subhook_t Hook = nullptr;
            uintptr_t Target = 0;
            std::string Name;
            std::atomic<uint64_t> Calls{0};
        };

        std::array<NativeExecSlot, 32> s_NativeExecSlots;
        std::mutex s_NativeExecMutex;

        bool NativeExecProbesEnabled()
        {
            static bool enabled = [] {
                const char* value = std::getenv("OBELISK_ENABLE_NATIVE_EXEC_PROBES");
                return value && std::string(value) == "1";
            }();
            return enabled;
        }

        bool FNameRejectLoggingEnabled()
        {
            static bool enabled = [] {
                const char* value = std::getenv("OBELISK_REFLECTION_LOG_FNAME_REJECTS");
                return value && std::string(value) == "1";
            }();
            return enabled;
        }

        bool StaticFNameRootSamplingEnabled()
        {
            static bool enabled = [] {
                const char* value = std::getenv("OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS");
                return value && std::string(value) == "1";
            }();
            return enabled;
        }

        std::vector<uintptr_t> StaticFNameRootSlots()
        {
            std::vector<uintptr_t> slots;
            const char* value = std::getenv("OBELISK_REFLECTION_STATIC_FNAME_ROOTS");
            if (!value || *value == '\0')
                return slots;

            std::stringstream stream(value);
            std::string token;
            while (std::getline(stream, token, ','))
            {
                token.erase(std::remove_if(token.begin(), token.end(), [](unsigned char c) {
                    return std::isspace(c) != 0;
                }), token.end());

                if (token.empty())
                    continue;

                char* end = nullptr;
                const unsigned long long parsed = std::strtoull(token.c_str(), &end, 0);
                if (end == token.c_str() || *end != '\0' || parsed == 0)
                {
                    OBELISK_WARN("[ReflectionScanner] Ignoring invalid OBELISK_REFLECTION_STATIC_FNAME_ROOTS entry '{}'", token);
                    continue;
                }

                const uintptr_t slot = static_cast<uintptr_t>(parsed);
                if (std::find(slots.begin(), slots.end(), slot) == slots.end())
                    slots.push_back(slot);
            }

            return slots;
        }

        void CallOriginalNativeExec(size_t index, void* context, void* stack, void* result)
        {
            NativeExecSlot& slot = s_NativeExecSlots[index];
            uint64_t call = ++slot.Calls;
            if (call <= 64 || (call % 1000) == 0)
            {
                OBELISK_INFO("[NativeExecProbe] hit #{} slot={} name={} target=0x{:X} context={} stack={} result={}",
                             call, index, slot.Name, slot.Target, context, stack, result);
            }

            auto original = reinterpret_cast<NativeExecFn>(subhook_get_trampoline(slot.Hook));
            if (original)
                original(context, stack, result);
        }

        template <size_t Index>
        void NativeExecDetour(void* context, void* stack, void* result)
        {
            CallOriginalNativeExec(Index, context, stack, result);
        }

        using DetourFn = void (*)(void*, void*, void*);

        constexpr std::array<DetourFn, 32> s_NativeExecDetours = {
            &NativeExecDetour<0>,  &NativeExecDetour<1>,  &NativeExecDetour<2>,  &NativeExecDetour<3>,
            &NativeExecDetour<4>,  &NativeExecDetour<5>,  &NativeExecDetour<6>,  &NativeExecDetour<7>,
            &NativeExecDetour<8>,  &NativeExecDetour<9>,  &NativeExecDetour<10>, &NativeExecDetour<11>,
            &NativeExecDetour<12>, &NativeExecDetour<13>, &NativeExecDetour<14>, &NativeExecDetour<15>,
            &NativeExecDetour<16>, &NativeExecDetour<17>, &NativeExecDetour<18>, &NativeExecDetour<19>,
            &NativeExecDetour<20>, &NativeExecDetour<21>, &NativeExecDetour<22>, &NativeExecDetour<23>,
            &NativeExecDetour<24>, &NativeExecDetour<25>, &NativeExecDetour<26>, &NativeExecDetour<27>,
            &NativeExecDetour<28>, &NativeExecDetour<29>, &NativeExecDetour<30>, &NativeExecDetour<31>,
        };

        void InstallNativeExecProbe(const char* name, uintptr_t target)
        {
            if (!NativeExecProbesEnabled())
                return;

            std::lock_guard<std::mutex> lock(s_NativeExecMutex);

            for (const NativeExecSlot& slot : s_NativeExecSlots)
            {
                if (slot.Target == target)
                    return;
            }

            for (size_t i = 0; i < s_NativeExecSlots.size(); ++i)
            {
                NativeExecSlot& slot = s_NativeExecSlots[i];
                if (slot.Hook)
                    continue;

                subhook_t hook = subhook_new(reinterpret_cast<void*>(target), reinterpret_cast<void*>(s_NativeExecDetours[i]));
                if (!hook)
                {
                    OBELISK_WARN("[NativeExecProbe] failed to allocate hook for {} target=0x{:X}", name, target);
                    return;
                }

                if (subhook_install(hook) != 0)
                {
                    OBELISK_WARN("[NativeExecProbe] failed to install hook for {} target=0x{:X}", name, target);
                    subhook_free(hook);
                    return;
                }

                slot.Hook = hook;
                slot.Target = target;
                slot.Name = name;
                OBELISK_INFO("[NativeExecProbe] installed slot={} name={} target=0x{:X}", i, slot.Name, slot.Target);
                return;
            }

            OBELISK_WARN("[NativeExecProbe] no free hook slots for {} target=0x{:X}", name, target);
        }

        std::vector<Mapping> GetShooterMappings()
        {
            std::vector<Mapping> mappings;
            bool includeAdjacentAnonymous = false;
            std::ifstream maps("/proc/self/maps");
            std::string line;

            while (std::getline(maps, line))
            {
                std::istringstream iss(line);
                std::string range;
                std::string offsetText;
                std::string dev;
                std::string inode;
                Mapping mapping;

                iss >> range >> mapping.Perms >> offsetText >> dev >> inode;
                std::getline(iss, mapping.Path);
                if (!mapping.Path.empty() && mapping.Path.front() == ' ')
                    mapping.Path.erase(mapping.Path.begin());

                size_t dash = range.find('-');
                if (dash == std::string::npos)
                    continue;

                mapping.Start = std::stoull(range.substr(0, dash), nullptr, 16);
                mapping.End = std::stoull(range.substr(dash + 1), nullptr, 16);
                mapping.FileOffset = std::stoull(offsetText, nullptr, 16);

                bool isShooterMapping = mapping.Path.find("ShooterGameServer") != std::string::npos;
                bool isAdjacentAnonymousImageMapping = includeAdjacentAnonymous &&
                                                       mapping.Path.empty() &&
                                                       !mappings.empty() &&
                                                       mapping.Start == mappings.back().End &&
                                                       mapping.Start < 0x10000000ULL;

                if (mapping.End > mapping.Start && (isShooterMapping || isAdjacentAnonymousImageMapping))
                    mappings.push_back(std::move(mapping));

                includeAdjacentAnonymous = isShooterMapping || isAdjacentAnonymousImageMapping;
            }

            return mappings;
        }

        std::vector<uint8_t> ToUtf32Le(const char* text)
        {
            std::vector<uint8_t> bytes;
            for (const unsigned char* p = reinterpret_cast<const unsigned char*>(text); *p; ++p)
            {
                uint32_t c = *p;
                bytes.push_back(static_cast<uint8_t>(c & 0xFF));
                bytes.push_back(static_cast<uint8_t>((c >> 8) & 0xFF));
                bytes.push_back(static_cast<uint8_t>((c >> 16) & 0xFF));
                bytes.push_back(static_cast<uint8_t>((c >> 24) & 0xFF));
            }
            bytes.insert(bytes.end(), {0, 0, 0, 0});
            return bytes;
        }

        bool BytesMatch(const uint8_t* haystack, const std::vector<uint8_t>& needle)
        {
            return std::memcmp(haystack, needle.data(), needle.size()) == 0;
        }

        std::vector<uintptr_t> FindBytesInMappings(const std::vector<Mapping>& mappings, const std::vector<uint8_t>& needle)
        {
            std::vector<uintptr_t> results;
            if (needle.empty())
                return results;

            for (const Mapping& mapping : mappings)
            {
                if (!mapping.Readable() || mapping.Size() < needle.size())
                    continue;

                const uint8_t* start = reinterpret_cast<const uint8_t*>(mapping.Start);
                const size_t limit = mapping.Size() - needle.size();
                for (size_t i = 0; i <= limit; ++i)
                {
                    if (BytesMatch(start + i, needle))
                        results.push_back(mapping.Start + i);
                }
            }

            return results;
        }

        bool ContainsAddress(const std::vector<Mapping>& mappings, uintptr_t address, bool writableOnly)
        {
            return std::any_of(mappings.begin(), mappings.end(), [&](const Mapping& mapping) {
                if (writableOnly && !mapping.Writable())
                    return false;
                return address >= mapping.Start && address < mapping.End;
            });
        }

        bool IsExecutableAddress(const std::vector<Mapping>& mappings, uintptr_t address)
        {
            return std::any_of(mappings.begin(), mappings.end(), [&](const Mapping& mapping) {
                return mapping.Executable() && address >= mapping.Start && address < mapping.End;
            });
        }

        bool IsCanonicalUserPointer(uintptr_t address)
        {
            return address >= 0x10000 && address <= 0x00007FFFFFFFFFFF;
        }

        bool IsNullOrReadablePointer(void* value, size_t size)
        {
            if (!value)
                return true;

            return IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(value)) &&
                   Obelisk::Memory::IsReadable(value, size);
        }

        bool IsPlausibleFName(const FName& name)
        {
            return name.ComparisonIndex >= 0 &&
                   name.ComparisonIndex < 10000000 &&
                   name.Number >= 0 &&
                   name.Number < 1000000;
        }

        bool IsPlausibleObjectFlags(int32_t flags)
        {
            return flags >= 0;
        }

        bool IsPlausibleInternalIndex(int32_t index)
        {
            return index >= -1 && index < 10000000;
        }

        template <typename T>
        bool ReadMemory(uintptr_t address, T& out)
        {
            if (!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(address), sizeof(T)))
                return false;

            std::memcpy(&out, reinterpret_cast<void*>(address), sizeof(T));
            return true;
        }

        std::string ReadAnsiPreview(uintptr_t address, size_t maxChars)
        {
            std::string result;
            for (size_t i = 0; i < maxChars; ++i)
            {
                char c = 0;
                if (!ReadMemory(address + i, c))
                    return {};
                if (c == '\0')
                    return result;
                if (c < 0x20 || c > 0x7E)
                    return {};
                result.push_back(c);
            }
            return result;
        }

        std::string ReadUtf32Preview(uintptr_t address, size_t maxChars)
        {
            std::string result;
            for (size_t i = 0; i < maxChars; ++i)
            {
                uint32_t c = 0;
                if (!ReadMemory(address + (i * sizeof(c)), c))
                    return {};
                if (c == 0)
                    return result;
                if (c < 0x20 || c > 0x7E)
                    return {};
                result.push_back(static_cast<char>(c));
            }
            return result;
        }

        std::string ReadFNameEntryPreview(uintptr_t entry)
        {
            constexpr std::array<size_t, 4> candidateNameOffsets = {0x8, 0xC, 0x10, 0x14};
            for (size_t offset : candidateNameOffsets)
            {
                std::string value = ReadAnsiPreview(entry + offset, 48);
                if (!value.empty())
                    return value;

                value = ReadUtf32Preview(entry + offset, 48);
                if (!value.empty())
                    return value;
            }

            return {};
        }

        struct FNameEntryClue
        {
            int32_t Index;
            const char* ExpectedName;
        };

        constexpr std::array<FNameEntryClue, 3> s_FNameClues = {
            FNameEntryClue{0, "None"},
            FNameEntryClue{4884, "ClientMessage"},
            FNameEntryClue{9619, "ServerChat"},
        };

        enum class FNameProbeFailure
        {
            None,
            InvalidIndex,
            UnreadableChunkPointer,
            UnreadableEntryPointer,
            EmptyEntryPreview,
        };

        const char* ToString(FNameProbeFailure failure)
        {
            switch (failure)
            {
            case FNameProbeFailure::None:
                return "none";
            case FNameProbeFailure::InvalidIndex:
                return "invalid_index";
            case FNameProbeFailure::UnreadableChunkPointer:
                return "unreadable_chunk_pointer";
            case FNameProbeFailure::UnreadableEntryPointer:
                return "unreadable_entry_pointer";
            case FNameProbeFailure::EmptyEntryPreview:
                return "empty_entry_preview";
            }
            return "unknown";
        }

        bool ProbeFNameEntry(uintptr_t table, const FNameEntryClue& clue, std::string& preview, FNameProbeFailure& failure)
        {
            failure = FNameProbeFailure::None;
            if (clue.Index < 0)
            {
                failure = FNameProbeFailure::InvalidIndex;
                return false;
            }

            uintptr_t chunk = 0;
            const int32_t chunkIndex = clue.Index / FNameIndirectArrayProbe::ChunkSize;
            const int32_t withinChunk = clue.Index % FNameIndirectArrayProbe::ChunkSize;
            const uintptr_t chunkPointerAddress = table + FNameIndirectArrayProbe::InlineChunksOffset +
                                                  (static_cast<uintptr_t>(chunkIndex) * sizeof(uintptr_t));
            if (!ReadMemory(chunkPointerAddress, chunk) ||
                !IsCanonicalUserPointer(chunk) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(chunk), sizeof(uintptr_t)))
            {
                failure = FNameProbeFailure::UnreadableChunkPointer;
                return false;
            }

            uintptr_t entry = 0;
            const uintptr_t entryPointerAddress = chunk + (static_cast<uintptr_t>(withinChunk) * sizeof(uintptr_t));
            if (!ReadMemory(entryPointerAddress, entry) ||
                !IsCanonicalUserPointer(entry) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(entry), 0x40))
            {
                failure = FNameProbeFailure::UnreadableEntryPointer;
                return false;
            }

            preview = ReadFNameEntryPreview(entry);
            if (preview.empty())
            {
                failure = FNameProbeFailure::EmptyEntryPreview;
                return false;
            }

            return true;
        }

        struct FNameTableProbeResult
        {
            int32_t NumElements = 0;
            int32_t NumChunks = 0;
            int ReadableClues = 0;
            int MatchedClues = 0;
            int Score = 0;
            std::array<std::string, s_FNameClues.size()> Previews;
            const char* RejectReason = nullptr;
        };

        FNameTableProbeResult ProbeFNameIndirectTable(uintptr_t table)
        {
            FNameTableProbeResult result;
            ReadMemory(table + FNameIndirectArrayProbe::NumElementsOffset, result.NumElements);
            ReadMemory(table + FNameIndirectArrayProbe::NumChunksOffset, result.NumChunks);

            const bool elementCountPlausible = result.NumElements > 9622 && result.NumElements < 10000000;
            const bool chunkCountPlausible = result.NumChunks > 0 && result.NumChunks <= FNameIndirectArrayProbe::MaxChunks;

            FNameProbeFailure firstFailure = FNameProbeFailure::None;
            for (size_t i = 0; i < s_FNameClues.size(); ++i)
            {
                FNameProbeFailure failure = FNameProbeFailure::None;
                if (!ProbeFNameEntry(table, s_FNameClues[i], result.Previews[i], failure))
                {
                    if (firstFailure == FNameProbeFailure::None)
                        firstFailure = failure;
                    continue;
                }

                ++result.ReadableClues;
                if (result.Previews[i] == s_FNameClues[i].ExpectedName)
                    ++result.MatchedClues;
            }

            result.Score = (elementCountPlausible ? 1 : 0) +
                           (chunkCountPlausible ? 1 : 0) +
                           result.ReadableClues +
                           result.MatchedClues;

            if (result.Score < 2 || result.ReadableClues == 0)
            {
                result.RejectReason = !elementCountPlausible ? "implausible_num_elements"
                                      : !chunkCountPlausible ? "implausible_num_chunks"
                                      : firstFailure != FNameProbeFailure::None ? ToString(firstFailure)
                                      : "insufficient_score";
            }
            else if (result.MatchedClues < static_cast<int>(s_FNameClues.size()))
            {
                result.RejectReason = "preview_mismatch";
            }

            return result;
        }

        struct StaticFNameRootProbeResult
        {
            int32_t NumElements = 0;
            int32_t NumChunks = 0;
            int ReadableClues = 0;
            int HeaderIndexOk = 0;
            int MatchedClues = 0;
            int Score = 0;
            std::array<std::string, s_FNameClues.size()> Previews;
            const char* RejectReason = nullptr;
        };

        bool ProbeStaticLegacyGNamesEntry(uintptr_t table,
                                          const FNameEntryClue& clue,
                                          std::string& preview,
                                          bool& headerIndexOk,
                                          FNameProbeFailure& failure)
        {
            headerIndexOk = false;
            failure = FNameProbeFailure::None;
            if (clue.Index < 0)
            {
                failure = FNameProbeFailure::InvalidIndex;
                return false;
            }

            uintptr_t chunk = 0;
            const int32_t chunkIndex = clue.Index / FNameIndirectArrayProbe::ChunkSize;
            const int32_t withinChunk = clue.Index % FNameIndirectArrayProbe::ChunkSize;
            const uintptr_t chunkPointerAddress = table + FNameIndirectArrayProbe::InlineChunksOffset +
                                                  (static_cast<uintptr_t>(chunkIndex) * sizeof(uintptr_t));
            if (!ReadMemory(chunkPointerAddress, chunk) ||
                !IsCanonicalUserPointer(chunk) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(chunk), sizeof(uintptr_t)))
            {
                failure = FNameProbeFailure::UnreadableChunkPointer;
                return false;
            }

            uintptr_t entry = 0;
            const uintptr_t entryPointerAddress = chunk + (static_cast<uintptr_t>(withinChunk) * sizeof(uintptr_t));
            if (!ReadMemory(entryPointerAddress, entry) ||
                !IsCanonicalUserPointer(entry) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(entry), 0x40))
            {
                failure = FNameProbeFailure::UnreadableEntryPointer;
                return false;
            }

            uint32_t entryHeader = 0;
            if (!ReadMemory(entry, entryHeader))
            {
                failure = FNameProbeFailure::UnreadableEntryPointer;
                return false;
            }
            headerIndexOk = static_cast<int32_t>(entryHeader >> 1) == clue.Index;

            preview = ReadAnsiPreview(entry + 0x10, 48);
            if (preview.empty())
            {
                failure = FNameProbeFailure::EmptyEntryPreview;
                return false;
            }

            return true;
        }

        StaticFNameRootProbeResult ProbeStaticLegacyGNamesTable(uintptr_t table)
        {
            StaticFNameRootProbeResult result;
            ReadMemory(table + FNameIndirectArrayProbe::NumElementsOffset, result.NumElements);
            ReadMemory(table + FNameIndirectArrayProbe::NumChunksOffset, result.NumChunks);

            const bool elementCountPlausible = result.NumElements > 9622 && result.NumElements < 10000000;
            const bool chunkCountPlausible = result.NumChunks > 0 && result.NumChunks <= FNameIndirectArrayProbe::MaxChunks;

            FNameProbeFailure firstFailure = FNameProbeFailure::None;
            for (size_t i = 0; i < s_FNameClues.size(); ++i)
            {
                FNameProbeFailure failure = FNameProbeFailure::None;
                bool headerIndexOk = false;
                if (!ProbeStaticLegacyGNamesEntry(table, s_FNameClues[i], result.Previews[i], headerIndexOk, failure))
                {
                    if (firstFailure == FNameProbeFailure::None)
                        firstFailure = failure;
                    continue;
                }

                ++result.ReadableClues;
                if (headerIndexOk)
                    ++result.HeaderIndexOk;
                if (result.Previews[i] == s_FNameClues[i].ExpectedName)
                    ++result.MatchedClues;
            }

            result.Score = result.ReadableClues +
                           result.HeaderIndexOk +
                           result.MatchedClues;

            if (!elementCountPlausible)
                result.RejectReason = "implausible_num_elements";
            else if (!chunkCountPlausible)
                result.RejectReason = "implausible_num_chunks";
            else if (result.ReadableClues < static_cast<int>(s_FNameClues.size()))
                result.RejectReason = firstFailure != FNameProbeFailure::None ? ToString(firstFailure) : "unreadable_clues";
            else if (result.HeaderIndexOk < static_cast<int>(s_FNameClues.size()))
                result.RejectReason = "header_index_mismatch";
            else if (result.MatchedClues < static_cast<int>(s_FNameClues.size()))
                result.RejectReason = "preview_mismatch";

            return result;
        }

        struct StaticFNameRootTable
        {
            void* TableValue = nullptr;
            uintptr_t Table = 0;
            int32_t NumElements = 0;
            int32_t NumChunks = 0;
            const char* RejectReason = nullptr;
        };

        StaticFNameRootTable ResolveStaticFNameRootTable(uintptr_t slot)
        {
            StaticFNameRootTable result;
            if (!IsCanonicalUserPointer(slot) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(slot), sizeof(uintptr_t)))
            {
                result.RejectReason = "unreadable_slot";
                return result;
            }

            std::memcpy(&result.TableValue, reinterpret_cast<void*>(slot), sizeof(result.TableValue));
            result.Table = reinterpret_cast<uintptr_t>(result.TableValue);

            if (!result.TableValue ||
                !IsCanonicalUserPointer(result.Table) ||
                !Obelisk::Memory::IsReadable(result.TableValue, FNameIndirectArrayProbe::NumChunksOffset + sizeof(int32_t)))
            {
                result.RejectReason = "unreadable_table_header";
                return result;
            }

            ReadMemory(result.Table + FNameIndirectArrayProbe::NumElementsOffset, result.NumElements);
            ReadMemory(result.Table + FNameIndirectArrayProbe::NumChunksOffset, result.NumChunks);

            if (result.NumElements <= 0 || result.NumElements >= 10000000)
                result.RejectReason = "implausible_num_elements";
            else if (result.NumChunks <= 0 || result.NumChunks > FNameIndirectArrayProbe::MaxChunks)
                result.RejectReason = "implausible_num_chunks";

            return result;
        }

        struct StaticFNameSampleResult
        {
            std::string Name;
            bool HeaderIndexOk = false;
            const char* RejectReason = nullptr;
        };

        StaticFNameSampleResult SampleStaticLegacyGNamesEntry(uintptr_t table, int32_t index)
        {
            StaticFNameSampleResult result;
            if (index < 0)
            {
                result.RejectReason = "invalid_index";
                return result;
            }

            uintptr_t chunk = 0;
            const int32_t chunkIndex = index / FNameIndirectArrayProbe::ChunkSize;
            const int32_t withinChunk = index % FNameIndirectArrayProbe::ChunkSize;
            const uintptr_t chunkPointerAddress = table + FNameIndirectArrayProbe::InlineChunksOffset +
                                                  (static_cast<uintptr_t>(chunkIndex) * sizeof(uintptr_t));
            if (!ReadMemory(chunkPointerAddress, chunk) ||
                !IsCanonicalUserPointer(chunk) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(chunk), sizeof(uintptr_t)))
            {
                result.RejectReason = "unreadable_chunk_pointer";
                return result;
            }

            uintptr_t entry = 0;
            const uintptr_t entryPointerAddress = chunk + (static_cast<uintptr_t>(withinChunk) * sizeof(uintptr_t));
            if (!ReadMemory(entryPointerAddress, entry) ||
                !IsCanonicalUserPointer(entry) ||
                !Obelisk::Memory::IsReadable(reinterpret_cast<void*>(entry), 0x40))
            {
                result.RejectReason = "unreadable_entry_pointer";
                return result;
            }

            uint32_t entryHeader = 0;
            if (!ReadMemory(entry, entryHeader))
            {
                result.RejectReason = "unreadable_entry_header";
                return result;
            }

            result.HeaderIndexOk = static_cast<int32_t>(entryHeader >> 1) == index;
            result.Name = ReadAnsiPreview(entry + 0x10, 64);
            if (result.Name.empty())
            {
                result.RejectReason = "empty_entry_name";
                return result;
            }

            return result;
        }

        void SampleStaticFNameRootsForObject(const std::vector<uintptr_t>& slots,
                                             const char* target,
                                             uintptr_t sourceGlobal,
                                             void* object,
                                             const FName& name)
        {
            if (!StaticFNameRootSamplingEnabled() || slots.empty())
                return;

            if (!IsPlausibleFName(name))
                return;

            for (uintptr_t slot : slots)
            {
                const StaticFNameRootTable table = ResolveStaticFNameRootTable(slot);
                if (table.RejectReason)
                {
                    OBELISK_INFO("[ReflectionScanner] StaticFNameRoot FName sample: slot=0x{:X} table={} target={} source_global=0x{:X} object={} index={} header_index_ok=false name='' status=reject reason={}",
                                 slot,
                                 table.TableValue,
                                 target,
                                 sourceGlobal,
                                 object,
                                 name.ComparisonIndex,
                                 table.RejectReason);
                    continue;
                }

                if (name.ComparisonIndex >= table.NumElements)
                {
                    OBELISK_INFO("[ReflectionScanner] StaticFNameRoot FName sample: slot=0x{:X} table={} target={} source_global=0x{:X} object={} index={} header_index_ok=false name='' status=reject reason=index_out_of_range num_elements={} num_chunks={}",
                                 slot,
                                 table.TableValue,
                                 target,
                                 sourceGlobal,
                                 object,
                                 name.ComparisonIndex,
                                 table.NumElements,
                                 table.NumChunks);
                    continue;
                }

                const StaticFNameSampleResult sample = SampleStaticLegacyGNamesEntry(table.Table, name.ComparisonIndex);
                const bool matched = !sample.RejectReason && sample.HeaderIndexOk && sample.Name == target;
                const char* status = sample.RejectReason ? "reject" : matched ? "match" : "mismatch";
                const char* reason = sample.RejectReason ? sample.RejectReason
                                   : !sample.HeaderIndexOk ? "header_index_mismatch"
                                   : sample.Name != target ? "name_mismatch"
                                   : "none";

                OBELISK_INFO("[ReflectionScanner] StaticFNameRoot FName sample: slot=0x{:X} table={} target={} source_global=0x{:X} object={} index={} header_index_ok={} name='{}' status={} reason={} num_elements={} num_chunks={}",
                             slot,
                             table.TableValue,
                             target,
                             sourceGlobal,
                             object,
                             name.ComparisonIndex,
                             sample.HeaderIndexOk,
                             sample.Name,
                             status,
                             reason,
                             table.NumElements,
                             table.NumChunks);
            }
        }

        void LogFNameIndirectArrayReject(const char* name,
                                         uintptr_t sourceGlobal,
                                         void* value,
                                         const char* reason,
                                         int32_t numElements,
                                         int32_t numChunks,
                                         int readableClues,
                                         int matchedClues,
                                         const std::array<std::string, 3>& previews)
        {
            if (!FNameRejectLoggingEnabled())
                return;

            OBELISK_INFO("[ReflectionScanner] {} FName indirect-table reject: source_global=0x{:X} table={} reason={} readable_clues={}/3 matched_clues={}/3 num_elements={} num_chunks={} none='{}' client_message='{}' server_chat='{}'",
                         name,
                         sourceGlobal,
                         value,
                         reason,
                         readableClues,
                         matchedClues,
                         numElements,
                         numChunks,
                         previews[0],
                         previews[1],
                         previews[2]);
        }

        void LogFNameIndirectArrayCandidate(const char* name, uintptr_t sourceGlobal, void* value)
        {
            const std::array<std::string, 3> emptyPreviews = {};
            const uintptr_t table = reinterpret_cast<uintptr_t>(value);
            if (!value ||
                !Obelisk::Memory::IsReadable(value, FNameIndirectArrayProbe::NumChunksOffset + sizeof(int32_t)))
            {
                LogFNameIndirectArrayReject(name,
                                            sourceGlobal,
                                            value,
                                            "unreadable_table_header",
                                            0,
                                            0,
                                            0,
                                            0,
                                            emptyPreviews);
                return;
            }

            const FNameTableProbeResult result = ProbeFNameIndirectTable(table);

            if (result.RejectReason)
            {
                LogFNameIndirectArrayReject(name,
                                            sourceGlobal,
                                            value,
                                            result.RejectReason,
                                            result.NumElements,
                                            result.NumChunks,
                                            result.ReadableClues,
                                            result.MatchedClues,
                                            result.Previews);
                if (result.Score < 2 || result.ReadableClues == 0)
                    return;
            }

            OBELISK_INFO("[ReflectionScanner] {} FName indirect-table probe: source_global=0x{:X} table={} score={}/8 readable_clues={}/3 matched_clues={}/3 num_elements={} num_chunks={} none='{}' client_message='{}' server_chat='{}'",
                         name,
                         sourceGlobal,
                         value,
                         result.Score,
                         result.ReadableClues,
                         result.MatchedClues,
                         result.NumElements,
                         result.NumChunks,
                         result.Previews[0],
                         result.Previews[1],
                         result.Previews[2]);
        }

        void LogFNameStaticRootReject(uintptr_t slot,
                                      void* table,
                                      const char* reason,
                                      const StaticFNameRootProbeResult& result = {})
        {
            OBELISK_INFO("[ReflectionScanner] StaticFNameRoot FName static-root reject: slot=0x{:X} table={} reason={} readable_clues={}/3 matched_clues={}/3 header_index_ok={}/3 num_elements={} num_chunks={} none='{}' client_message='{}' server_chat='{}'",
                         slot,
                         table,
                         reason,
                         result.ReadableClues,
                         result.MatchedClues,
                         result.HeaderIndexOk,
                         result.NumElements,
                         result.NumChunks,
                         result.Previews[0],
                         result.Previews[1],
                         result.Previews[2]);
        }

        bool ProbeStaticFNameRootSlot(uintptr_t slot)
        {
            const StaticFNameRootTable table = ResolveStaticFNameRootTable(slot);
            if (table.RejectReason)
            {
                LogFNameStaticRootReject(slot, table.TableValue, table.RejectReason);
                return false;
            }

            const StaticFNameRootProbeResult result = ProbeStaticLegacyGNamesTable(table.Table);
            if (result.RejectReason)
            {
                LogFNameStaticRootReject(slot, table.TableValue, result.RejectReason, result);
                return false;
            }

            OBELISK_INFO("[ReflectionScanner] StaticFNameRoot FName static-root probe: slot=0x{:X} table={} score={}/9 readable_clues={}/3 matched_clues={}/3 header_index_ok={}/3 num_elements={} num_chunks={} none='{}' client_message='{}' server_chat='{}'",
                         slot,
                         table.TableValue,
                         result.Score,
                         result.ReadableClues,
                         result.MatchedClues,
                         result.HeaderIndexOk,
                         result.NumElements,
                         result.NumChunks,
                         result.Previews[0],
                         result.Previews[1],
                         result.Previews[2]);
            return true;
        }

        void ProbeStaticFNameRoots(const std::vector<uintptr_t>& slots)
        {
            if (slots.empty())
                return;

            OBELISK_INFO("[ReflectionScanner] StaticFNameRoot probing {} env-supplied slot(s).", slots.size());
            for (uintptr_t slot : slots)
                ProbeStaticFNameRootSlot(slot);
        }

        int LogUObjectValidation(const std::vector<Mapping>& mappings, const char* name, void* value, const UObjectProbe& object)
        {
            uintptr_t firstVtableEntry = 0;
            const bool vtableReadable = object.VTable &&
                                        IsCanonicalUserPointer(reinterpret_cast<uintptr_t>(object.VTable)) &&
                                        Obelisk::Memory::IsReadable(object.VTable, sizeof(firstVtableEntry));
            if (vtableReadable)
                std::memcpy(&firstVtableEntry, object.VTable, sizeof(firstVtableEntry));

            const bool vtableExecutable = firstVtableEntry != 0 &&
                                          IsExecutableAddress(mappings, firstVtableEntry);
            const bool classReadable = IsNullOrReadablePointer(object.ClassPrivate, sizeof(UObjectBase));
            const bool outerReadable = IsNullOrReadablePointer(object.OuterPrivate, sizeof(UObjectBase));
            const bool fnamePlausible = IsPlausibleFName(object.NamePrivate);
            const bool flagsPlausible = IsPlausibleObjectFlags(object.ObjectFlags);
            const bool internalPlausible = IsPlausibleInternalIndex(object.InternalIndex);
            const int score = (vtableExecutable ? 1 : 0) +
                              (classReadable ? 1 : 0) +
                              (outerReadable ? 1 : 0) +
                              (fnamePlausible ? 1 : 0) +
                              (flagsPlausible ? 1 : 0) +
                              (internalPlausible ? 1 : 0);

            OBELISK_INFO("[ReflectionScanner] {} UObject validation: object={} score={}/6 vtable_exec={} class_readable_or_null={} outer_readable_or_null={} fname_plausible={} flags_plausible={} internal_plausible={}",
                         name,
                         value,
                         score,
                         vtableExecutable,
                         classReadable,
                         outerReadable,
                         fnamePlausible,
                         flagsPlausible,
                         internalPlausible);
            return score;
        }

        bool ReadUintptrField(void* base, size_t offset, uintptr_t& out)
        {
            auto* address = static_cast<uint8_t*>(base) + offset;
            if (!Obelisk::Memory::IsReadable(address, sizeof(out)))
                return false;

            std::memcpy(&out, address, sizeof(out));
            return true;
        }

        void PushUniqueLimited(std::vector<uintptr_t>& values, uintptr_t value, size_t maxValues)
        {
            if (std::find(values.begin(), values.end(), value) != values.end())
                return;
            if (maxValues != 0 && values.size() >= maxValues)
                return;
            values.push_back(value);
        }

        std::vector<uintptr_t> FindMovImm32References(const std::vector<Mapping>& mappings, uintptr_t target, size_t maxResults)
        {
            std::vector<uintptr_t> refs;
            if (target > 0xFFFFFFFFULL)
                return refs;

            const uint32_t imm = static_cast<uint32_t>(target);
            const std::array<uint8_t, 5> opcodes = {0xB8, 0xB9, 0xBA, 0xBB, 0xBE};

            for (const Mapping& mapping : mappings)
            {
                if (!mapping.Readable() || !mapping.Executable() || mapping.Size() < 5)
                    continue;

                const uint8_t* bytes = reinterpret_cast<const uint8_t*>(mapping.Start);
                const size_t limit = mapping.Size() - 5;
                for (size_t i = 0; i <= limit; ++i)
                {
                    if (std::find(opcodes.begin(), opcodes.end(), bytes[i]) == opcodes.end())
                        continue;

                    uint32_t found = 0;
                    std::memcpy(&found, bytes + i + 1, sizeof(found));
                    if (found == imm)
                        PushUniqueLimited(refs, mapping.Start + i, maxResults);
                }
            }

            return refs;
        }

        std::vector<uintptr_t> FindRipRelativeStoresNear(const std::vector<Mapping>& mappings, uintptr_t ref, size_t maxResults)
        {
            std::vector<uintptr_t> globals;
            uintptr_t scanStart = ref > 0x300 ? ref - 0x300 : ref;
            uintptr_t scanEnd = ref + 0x700;

            for (uintptr_t at = scanStart; at + 7 < scanEnd; ++at)
            {
                if (!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(at), 7))
                    continue;

                const uint8_t* p = reinterpret_cast<const uint8_t*>(at);

                // Common UE generated code shape:
                //   48 89 1D disp32   mov %rbx, global(%rip)
                //   4C 89 35 disp32   mov %r14, global(%rip)
                bool isStore = (p[0] == 0x48 && p[1] == 0x89 && (p[2] == 0x1D || p[2] == 0x35 || p[2] == 0x3D)) ||
                               (p[0] == 0x4C && p[1] == 0x89 && (p[2] == 0x35 || p[2] == 0x3D));
                if (!isStore)
                    continue;

                int32_t disp = 0;
                std::memcpy(&disp, p + 3, sizeof(disp));
                uintptr_t global = at + 7 + disp;
                if (ContainsAddress(mappings, global, true))
                    PushUniqueLimited(globals, global, maxResults);
            }

            return globals;
        }

        void DumpGlobalPointer(const std::vector<Mapping>& mappings,
                               const std::vector<uintptr_t>& staticFNameRootSlots,
                               const char* name,
                               uintptr_t global)
        {
            if (!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(global), sizeof(void*)))
                return;

            void* value = nullptr;
            std::memcpy(&value, reinterpret_cast<void*>(global), sizeof(void*));
            OBELISK_INFO("[ReflectionScanner] {} candidate global 0x{:X} -> {}", name, global, value);

            if (!value || !Obelisk::Memory::IsReadable(value, 0x80))
                return;

            if (Obelisk::Memory::IsReadable(value, sizeof(UObjectProbe)))
            {
                UObjectProbe object{};
                std::memcpy(&object, value, sizeof(object));
                OBELISK_INFO("[ReflectionScanner] {} UObject probe: object={} vtable={} flags=0x{:X} internal={} class={} name_index={} name_number={} outer={}",
                             name,
                             value,
                             static_cast<void*>(object.VTable),
                             object.ObjectFlags,
                             object.InternalIndex,
                             object.ClassPrivate,
                             object.NamePrivate.ComparisonIndex,
                             object.NamePrivate.Number,
                             object.OuterPrivate);
                const int validationScore = LogUObjectValidation(mappings, name, value, object);
                if (validationScore >= 4)
                    SampleStaticFNameRootsForObject(staticFNameRootSlots, name, global, value, object.NamePrivate);
            }

            const uintptr_t* qwords = reinterpret_cast<const uintptr_t*>(value);
            OBELISK_INFO("[ReflectionScanner] {} object probe: +00=0x{:X} +08=0x{:X} +10=0x{:X} +18=0x{:X} +20=0x{:X} +28=0x{:X} +30=0x{:X} +38=0x{:X}",
                         name, qwords[0], qwords[1], qwords[2], qwords[3], qwords[4], qwords[5], qwords[6], qwords[7]);

            LogFNameIndirectArrayCandidate(name, global, value);

            size_t executableFields = 0;
            for (size_t offset = 0; offset < 0x200; offset += sizeof(uintptr_t))
            {
                uintptr_t field = 0;
                if (!ReadUintptrField(value, offset, field))
                    break;

                if (IsExecutableAddress(mappings, field))
                {
                    OBELISK_INFO("[ReflectionScanner] {} executable field candidate global=0x{:X} object={} offset=0x{:X} value=0x{:X}",
                                 name, global, value, offset, field);
                    uint8_t* base = reinterpret_cast<uint8_t*>(value);
                    if (Obelisk::Memory::IsReadable(base + 0xA0, 0x40))
                    {
                        uint64_t qA0 = 0;
                        uint64_t qA8 = 0;
                        uint64_t qB0 = 0;
                        uint64_t qB8 = 0;
                        uint64_t qC0 = 0;
                        uint64_t qC8 = 0;
                        std::memcpy(&qA0, base + 0xA0, sizeof(qA0));
                        std::memcpy(&qA8, base + 0xA8, sizeof(qA8));
                        std::memcpy(&qB0, base + 0xB0, sizeof(qB0));
                        std::memcpy(&qB8, base + 0xB8, sizeof(qB8));
                        std::memcpy(&qC0, base + 0xC0, sizeof(qC0));
                        std::memcpy(&qC8, base + 0xC8, sizeof(qC8));
                        OBELISK_INFO("[ReflectionScanner] {} UFunction tail window object={} +A0=0x{:X} +A8=0x{:X} +B0=0x{:X} +B8=0x{:X} +C0=0x{:X} +C8=0x{:X}",
                                     name, value, qA0, qA8, qB0, qB8, qC0, qC8);
                    }
                    if (offset == 0xA8)
                        InstallNativeExecProbe(name, field);
                    if (++executableFields >= 12)
                        break;
                }
            }
        }

        void StartDelayedGlobalProbe(std::vector<GlobalWatch> watches, std::vector<uintptr_t> staticFNameRootSlots)
        {
            if (watches.empty())
                return;

            std::thread([watches = std::move(watches), staticFNameRootSlots = std::move(staticFNameRootSlots)]() mutable {
                std::vector<void*> lastValues(watches.size(), nullptr);

                for (int iteration = 1; iteration <= 120; ++iteration)
                {
                    std::this_thread::sleep_for(std::chrono::seconds(5));
                    if (!Obelisk::Logger::IsInitialized())
                        return;

                    const auto mappings = GetShooterMappings();
                    for (size_t i = 0; i < watches.size(); ++i)
                    {
                        const GlobalWatch& watch = watches[i];
                        if (!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(watch.Address), sizeof(void*)))
                            continue;

                        void* value = nullptr;
                        std::memcpy(&value, reinterpret_cast<void*>(watch.Address), sizeof(void*));
                        if (value == nullptr || value == lastValues[i])
                            continue;

                        lastValues[i] = value;
                        OBELISK_INFO("[ReflectionScanner] delayed global resolved after {}s: {} 0x{:X} -> {}",
                                     iteration * 5, watch.Name, watch.Address, value);
                        DumpGlobalPointer(mappings, staticFNameRootSlots, watch.Name.c_str(), watch.Address);
                    }
                }
            }).detach();
        }

        void StartDelayedStaticFNameRootProbe(std::vector<uintptr_t> slots)
        {
            if (slots.empty())
                return;

            std::thread([slots = std::move(slots)]() {
                for (int iteration = 1; iteration <= 120; ++iteration)
                {
                    std::this_thread::sleep_for(std::chrono::seconds(5));
                    if (!Obelisk::Logger::IsInitialized())
                        return;

                    OBELISK_INFO("[ReflectionScanner] StaticFNameRoot delayed retry after {}s for {} slot(s).",
                                 iteration * 5,
                                 slots.size());
                    bool accepted = false;
                    for (uintptr_t slot : slots)
                        accepted = ProbeStaticFNameRootSlot(slot) || accepted;
                    if (accepted)
                        return;
                }
            }).detach();
        }
    }

    void ReflectionScanner::RunStartupScan()
    {
        const std::array<const char*, 5> targets = {
            "ServerSendChatMessage",
            "ServerChat",
            "ClientServerChatMessage",
            "ClientChatMessage",
            "ClientMessage",
        };

        const auto mappings = GetShooterMappings();
        if (mappings.empty())
        {
            OBELISK_WARN("[ReflectionScanner] No ShooterGameServer mappings found.");
            return;
        }

        size_t readableCount = 0;
        size_t executableCount = 0;
        for (const Mapping& mapping : mappings)
        {
            if (mapping.Readable())
                ++readableCount;
            if (mapping.Executable())
                ++executableCount;
        }

        OBELISK_INFO("[ReflectionScanner] Scanning {} ShooterGameServer mapping(s): {} readable, {} executable.",
                     mappings.size(), readableCount, executableCount);

        const std::vector<uintptr_t> staticFNameRootSlots = StaticFNameRootSlots();
        if (!staticFNameRootSlots.empty())
        {
            if (StaticFNameRootSamplingEnabled())
            {
                OBELISK_INFO("[ReflectionScanner] StaticFNameRoot sampling enabled for {} env-supplied slot(s). Fixed clue static-root probing is skipped while sampling observed UObject NamePrivate indices.",
                             staticFNameRootSlots.size());
            }
            else
            {
                ProbeStaticFNameRoots(staticFNameRootSlots);
                StartDelayedStaticFNameRootProbe(staticFNameRootSlots);
            }
        }

        std::vector<GlobalWatch> watches;
        for (const char* target : targets)
        {
            TargetScan scan;
            scan.Name = target;
            scan.StringAddresses = FindBytesInMappings(mappings, ToUtf32Le(target));

            for (uintptr_t stringAddress : scan.StringAddresses)
            {
                auto refs = FindMovImm32References(mappings, stringAddress, 16);
                for (uintptr_t ref : refs)
                    PushUniqueLimited(scan.References, ref, 24);
            }

            for (uintptr_t ref : scan.References)
            {
                auto globals = FindRipRelativeStoresNear(mappings, ref, 8);
                for (uintptr_t global : globals)
                    PushUniqueLimited(scan.CandidateGlobals, global, 16);
            }

            OBELISK_INFO("[ReflectionScanner] target={} utf32_strings={} refs={} globals={}",
                         scan.Name, scan.StringAddresses.size(), scan.References.size(), scan.CandidateGlobals.size());

            for (size_t i = 0; i < scan.StringAddresses.size() && i < 8; ++i)
                OBELISK_INFO("[ReflectionScanner] {} string[{}]=0x{:X}", scan.Name, i, scan.StringAddresses[i]);

            for (size_t i = 0; i < scan.References.size() && i < 12; ++i)
                OBELISK_INFO("[ReflectionScanner] {} ref[{}]=0x{:X}", scan.Name, i, scan.References[i]);

            for (uintptr_t global : scan.CandidateGlobals)
            {
                DumpGlobalPointer(mappings, staticFNameRootSlots, scan.Name, global);
                watches.push_back({scan.Name, global});
            }
        }

        StartDelayedGlobalProbe(std::move(watches), staticFNameRootSlots);
    }

    void ReflectionScanner::RunStaticFNameRootProbe(const std::vector<uintptr_t>& slots)
    {
        ProbeStaticFNameRoots(slots);
    }
}
