#include "ReflectionScanner.h"

#include "runtime/Logger.h"
#include "ue/Memory.h"
#include "ue/Reflection.h"

#include <subhook.h>

#include <algorithm>
#include <array>
#include <atomic>
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

        void LogUObjectValidation(const std::vector<Mapping>& mappings, const char* name, void* value, const UObjectProbe& object)
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

        void DumpGlobalPointer(const std::vector<Mapping>& mappings, const char* name, uintptr_t global)
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
                LogUObjectValidation(mappings, name, value, object);
            }

            const uintptr_t* qwords = reinterpret_cast<const uintptr_t*>(value);
            OBELISK_INFO("[ReflectionScanner] {} object probe: +00=0x{:X} +08=0x{:X} +10=0x{:X} +18=0x{:X} +20=0x{:X} +28=0x{:X} +30=0x{:X} +38=0x{:X}",
                         name, qwords[0], qwords[1], qwords[2], qwords[3], qwords[4], qwords[5], qwords[6], qwords[7]);

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

        void StartDelayedGlobalProbe(std::vector<GlobalWatch> watches)
        {
            if (watches.empty())
                return;

            std::thread([watches = std::move(watches)]() mutable {
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
                        DumpGlobalPointer(mappings, watch.Name.c_str(), watch.Address);
                    }
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
                DumpGlobalPointer(mappings, scan.Name, global);
                watches.push_back({scan.Name, global});
            }
        }

        StartDelayedGlobalProbe(std::move(watches));
    }
}
