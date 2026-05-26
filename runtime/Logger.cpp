#include "Logger.h"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/spdlog.h>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace Obelisk
{
    std::shared_ptr<spdlog::logger> Logger::s_Logger;

    namespace
    {
        std::string GetLogDir()
        {
            const char* logDir = std::getenv("OBELISK_LOG_DIR");
            if (logDir && logDir[0] != '\0')
            {
                std::filesystem::create_directories(logDir);
                return logDir;
            }

            const char* root = std::getenv("OBELISK_ROOT");
            if (root && root[0] != '\0')
            {
                std::filesystem::path path = std::filesystem::path(root) / "logs";
                std::filesystem::create_directories(path);
                return path.string();
            }

            return ".";
        }

        std::string GetMapNameFromCmdline()
        {
            std::ifstream cmdline("/proc/self/cmdline", std::ios::binary);
            std::string data((std::istreambuf_iterator<char>(cmdline)), std::istreambuf_iterator<char>());
            if (data.empty())
                return "unknown";

            size_t argStart = data.find('\0');
            if (argStart == std::string::npos || argStart + 1 >= data.size())
                return "unknown";
            ++argStart;

            size_t argEnd = data.find('\0', argStart);
            std::string firstArg = data.substr(argStart, argEnd == std::string::npos ? std::string::npos : argEnd - argStart);
            size_t optionStart = firstArg.find('?');
            std::string mapName = firstArg.substr(0, optionStart);

            std::string sanitized;
            for (unsigned char ch : mapName)
            {
                if (std::isalnum(ch) || ch == '_' || ch == '-')
                    sanitized.push_back(static_cast<char>(ch));
            }

            return sanitized.empty() ? "unknown" : sanitized;
        }
    }

    void Logger::Init()
    {
        if (s_Logger)
            return;

        auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
        console_sink->set_pattern("%^[%T] [Obelisk] %v%$");

        std::filesystem::path logDir = GetLogDir();
        auto shared_file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((logDir / "Obelisk.log").string(), true);
        shared_file_sink->set_pattern("[%T] [%l] %v");

        auto instance_file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((logDir / ("Obelisk-" + GetMapNameFromCmdline() + ".log")).string(), true);
        instance_file_sink->set_pattern("[%T] [%l] %v");

        std::vector<spdlog::sink_ptr> sinks { console_sink, shared_file_sink, instance_file_sink };

        s_Logger = std::make_shared<spdlog::logger>("Obelisk", sinks.begin(), sinks.end());
        spdlog::register_logger(s_Logger);
        s_Logger->set_level(spdlog::level::trace);
        s_Logger->flush_on(spdlog::level::trace);
    }

    void Logger::Shutdown()
    {
        if (!s_Logger)
            return;

        s_Logger->flush();
        spdlog::drop(s_Logger->name());
        s_Logger.reset();
    }

    bool Logger::IsInitialized()
    {
        return static_cast<bool>(s_Logger);
    }

    std::shared_ptr<spdlog::logger>& Logger::Get()
    {
        return s_Logger;
    }
}
