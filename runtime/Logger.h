#pragma once

#include <spdlog/spdlog.h>
#include <memory>

namespace Obelisk
{
    class Logger
    {
    public:
        static void Init();
        static std::shared_ptr<spdlog::logger>& Get();

    private:
        static std::shared_ptr<spdlog::logger> s_Logger;
    };
}

// Macros for easier usage across the runtime
#define OBELISK_TRACE(...)    ::Obelisk::Logger::Get()->trace(__VA_ARGS__)
#define OBELISK_INFO(...)     ::Obelisk::Logger::Get()->info(__VA_ARGS__)
#define OBELISK_WARN(...)     ::Obelisk::Logger::Get()->warn(__VA_ARGS__)
#define OBELISK_ERROR(...)    ::Obelisk::Logger::Get()->error(__VA_ARGS__)
#define OBELISK_CRITICAL(...) ::Obelisk::Logger::Get()->critical(__VA_ARGS__)
