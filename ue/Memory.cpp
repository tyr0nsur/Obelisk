#include "Memory.h"
#include "runtime/Logger.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <cstring>
#include <mutex>

namespace Obelisk::Memory
{
    namespace
    {
        struct ReadableRange
        {
            uintptr_t Start = 0;
            uintptr_t End = 0;
        };

        std::mutex s_ReadableRangesMutex;
        std::vector<ReadableRange> s_ReadableRanges;

        bool AddWouldOverflow(uintptr_t address, size_t size)
        {
            return size > 0 && address > UINTPTR_MAX - (size - 1);
        }

        bool ParseMapsReadableRanges(std::vector<ReadableRange>& ranges)
        {
            std::ifstream maps("/proc/self/maps");
            if (!maps)
                return false;

            std::vector<ReadableRange> parsed;
            std::string line;
            while (std::getline(maps, line))
            {
                std::istringstream iss(line);
                std::string addressRange;
                std::string perms;
                iss >> addressRange >> perms;
                if (addressRange.empty() || perms.empty() || perms[0] != 'r')
                    continue;

                size_t dash = addressRange.find('-');
                if (dash == std::string::npos)
                    continue;

                uintptr_t start = 0;
                uintptr_t end = 0;
                try
                {
                    start = std::stoull(addressRange.substr(0, dash), nullptr, 16);
                    end = std::stoull(addressRange.substr(dash + 1), nullptr, 16);
                }
                catch (...)
                {
                    continue;
                }

                if (start < end)
                    parsed.push_back({start, end});
            }

            std::sort(parsed.begin(), parsed.end(), [](const ReadableRange& lhs, const ReadableRange& rhs) {
                return lhs.Start < rhs.Start;
            });
            ranges = std::move(parsed);
            return true;
        }

        bool RangeContains(const std::vector<ReadableRange>& ranges, uintptr_t start, uintptr_t end)
        {
            auto it = std::upper_bound(
                ranges.begin(),
                ranges.end(),
                start,
                [](uintptr_t value, const ReadableRange& range) {
                    return value < range.Start;
                });
            if (it == ranges.begin())
                return false;

            --it;
            return start >= it->Start && end <= it->End;
        }

        bool RefreshReadableRangesLocked()
        {
            std::vector<ReadableRange> ranges;
            if (!ParseMapsReadableRanges(ranges))
                return false;
            s_ReadableRanges = std::move(ranges);
            return true;
        }
    }

    ModuleInfo GetMainModuleInfo()
    {
        ModuleInfo info = {0, 0, 0, false};
        std::ifstream maps("/proc/self/maps");
        std::string line;

        while (std::getline(maps, line))
        {
            if (line.find("ShooterGameServer") == std::string::npos)
                continue;

            std::istringstream iss(line);
            std::string addressRange;
            std::string perms;
            std::string offsetText;
            iss >> addressRange >> perms >> offsetText;

            size_t dash = addressRange.find('-');
            if (dash == std::string::npos)
                continue;

            uintptr_t start = std::stoull(addressRange.substr(0, dash), nullptr, 16);
            uintptr_t end = std::stoull(addressRange.substr(dash + 1), nullptr, 16);
            uintptr_t fileOffset = std::stoull(offsetText, nullptr, 16);
            uintptr_t loadBias = start - fileOffset;

            if (info.imageBase == 0 || loadBias < info.imageBase)
                info.imageBase = loadBias;

            if (perms.find("r-xp") != std::string::npos)
            {
                info.start = start;
                info.end = end;
                info.found = true;
                OBELISK_TRACE("Main module executable segment: 0x{:X} - 0x{:X}, ELF base: 0x{:X}", info.start, info.end, info.imageBase);
            }
        }

        if (!info.found)
            OBELISK_ERROR("Failed to find ShooterGameServer executable segment in /proc/self/maps");

        return info;
    }

    static bool ParsePattern(const std::string& pattern, std::vector<uint8_t>& bytes, std::vector<bool>& mask)
    {
        std::istringstream iss(pattern);
        std::string word;
        while (iss >> word)
        {
            if (word == "?" || word == "??")
            {
                bytes.push_back(0);
                mask.push_back(false);
            }
            else
            {
                bytes.push_back(static_cast<uint8_t>(std::stoul(word, nullptr, 16)));
                mask.push_back(true);
            }
        }
        return !bytes.empty() && bytes.size() == mask.size();
    }

    std::vector<void*> FindPatternAll(const std::string& pattern, size_t maxResults)
    {
        std::vector<void*> results;
        ModuleInfo module = GetMainModuleInfo();
        if (!module.found)
        {
            OBELISK_ERROR("Failed to find ShooterGameServer code segment in memory!");
            return results;
        }

        std::vector<uint8_t> bytes;
        std::vector<bool> mask;
        if (!ParsePattern(pattern, bytes, mask))
        {
            OBELISK_WARN("Invalid pattern: {}", pattern);
            return results;
        }

        size_t patternLength = bytes.size();
        uint8_t* scanBytes = reinterpret_cast<uint8_t*>(module.start);
        size_t scanSize = module.end - module.start;

        if (scanSize < patternLength)
        {
            OBELISK_WARN("Invalid pattern scan size. Pattern length: {}, scan size: {}", patternLength, scanSize);
            return results;
        }

        for (size_t i = 0; i <= scanSize - patternLength; ++i)
        {
            bool found = true;
            for (size_t j = 0; j < patternLength; ++j)
            {
                if (mask[j] && scanBytes[i + j] != bytes[j])
                {
                    found = false;
                    break;
                }
            }

            if (found)
            {
                results.push_back(reinterpret_cast<void*>(scanBytes + i));
                if (maxResults != 0 && results.size() >= maxResults)
                    break;
            }
        }

        return results;
    }

    void* FindPattern(const std::string& pattern)
    {
        std::vector<void*> results = FindPatternAll(pattern, 1);
        if (results.empty())
        {
            OBELISK_WARN("Pattern not found: {}", pattern);
            return nullptr;
        }
        return results.front();
    }

    __attribute__((visibility("default"))) bool IsReadable(void* ptr, size_t size)
    {
        if (!ptr || size == 0)
            return false;

        const uintptr_t start = reinterpret_cast<uintptr_t>(ptr);
        if (AddWouldOverflow(start, size))
            return false;
        const uintptr_t end = start + size;

        std::lock_guard<std::mutex> lock(s_ReadableRangesMutex);
        if (s_ReadableRanges.empty() && !RefreshReadableRangesLocked())
            return false;

        if (RangeContains(s_ReadableRanges, start, end))
            return true;

        // Mappings can appear after startup when shared objects are loaded. Refresh once
        // on a miss before rejecting the address.
        if (!RefreshReadableRangesLocked())
            return false;
        return RangeContains(s_ReadableRanges, start, end);
    }
}
