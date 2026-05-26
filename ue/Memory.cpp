#include "Memory.h"
#include "runtime/Logger.h"
#include <fstream>
#include <sstream>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

namespace Obelisk::Memory
{
    ModuleInfo GetMainModuleInfo()
    {
        ModuleInfo info = {0, 0, false};
        std::ifstream maps("/proc/self/maps");
        std::string line;
        
        while (std::getline(maps, line))
        {
            // We look for the executable segment of the main binary
            if (line.find("r-xp") != std::string::npos && line.find("ShooterGameServer") != std::string::npos)
            {
                std::istringstream iss(line);
                std::string address_range;
                iss >> address_range;
                
                size_t dash = address_range.find('-');
                if (dash != std::string::npos)
                {
                    info.start = std::stoull(address_range.substr(0, dash), nullptr, 16);
                    info.end = std::stoull(address_range.substr(dash + 1), nullptr, 16);
                    info.found = true;
                    OBELISK_TRACE("Main module code segment found: 0x{:X} - 0x{:X}", info.start, info.end);
                }
                break;
            }
        }
        return info;
    }

    void* FindPattern(const std::string& pattern)
    {
        ModuleInfo module = GetMainModuleInfo();
        if (!module.found)
        {
            OBELISK_ERROR("Failed to find ShooterGameServer code segment in memory!");
            return nullptr;
        }

        // Parse pattern string into bytes and mask
        std::vector<uint8_t> bytes;
        std::vector<bool> mask;
        
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

        // Scan memory
        size_t patternLength = bytes.size();
        uint8_t* scanBytes = reinterpret_cast<uint8_t*>(module.start);
        size_t scanSize = module.end - module.start;

        for (size_t i = 0; i < scanSize - patternLength; ++i)
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
                return reinterpret_cast<void*>(scanBytes + i);
            }
        }

        OBELISK_WARN("Pattern not found: {}", pattern);
        return nullptr;
    }

    bool IsReadable(void* ptr, size_t size)
    {
        if (!ptr || size == 0) return false;
        
        // Use the write() syscall trick to safely check if memory is readable
        // writing to /dev/random (or /dev/null) will fail with EFAULT if ptr is invalid
        int fd = open("/dev/random", O_WRONLY);
        if (fd < 0) return false;
        
        ssize_t ret = write(fd, ptr, size);
        close(fd);
        
        return ret >= 0;
    }
}
