#include "Logger.h"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/spdlog.h>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>

namespace Obelisk
{
    std::shared_ptr<spdlog::logger> Logger::s_Logger;

    namespace
    {
        void ValidateExistingPathComponentsNoSymlinks(const std::filesystem::path& path, const char* label)
        {
            std::filesystem::path current;
            for (const auto& component : path)
            {
                if (component == path.root_name())
                {
                    current = component;
                    continue;
                }
                if (component == path.root_directory())
                {
                    current = current.empty() ? component : current / component;
                    continue;
                }

                current = current.empty() ? component : current / component;
                std::error_code ec;
                const std::filesystem::file_status status = std::filesystem::symlink_status(current, ec);
                if (status.type() == std::filesystem::file_type::not_found)
                    return;
                if (ec)
                    throw std::runtime_error(std::string(label) + " path component is not accessible: " + ec.message());
                if (std::filesystem::is_symlink(status))
                    throw std::runtime_error(std::string(label) + " path component must not be a symlink");
                if (current != path && !std::filesystem::is_directory(status))
                    throw std::runtime_error(std::string(label) + " path component must be a directory");
            }
        }

        void ValidateOrCreateLogDirectory(const std::filesystem::path& path, const char* label)
        {
            if (path.empty())
                throw std::runtime_error(std::string(label) + " is empty");
            if (!path.is_absolute())
                throw std::runtime_error(std::string(label) + " must be absolute");

            ValidateExistingPathComponentsNoSymlinks(path, label);

            std::error_code ec;
            const std::filesystem::file_status symlinkStatus = std::filesystem::symlink_status(path, ec);
            if (symlinkStatus.type() == std::filesystem::file_type::not_found)
            {
                std::filesystem::create_directories(path, ec);
                if (ec)
                    throw std::runtime_error(std::string("failed to create ") + label + ": " + ec.message());
            }
            else
            {
                if (ec)
                    throw std::runtime_error(std::string(label) + " is not accessible: " + ec.message());
                if (std::filesystem::is_symlink(symlinkStatus))
                    throw std::runtime_error(std::string(label) + " must not be a symlink");
                if (!std::filesystem::is_directory(symlinkStatus))
                    throw std::runtime_error(std::string(label) + " must be a directory");
            }

            ValidateExistingPathComponentsNoSymlinks(path, label);

            const std::filesystem::file_status finalStatus = std::filesystem::symlink_status(path, ec);
            if (ec)
                throw std::runtime_error(std::string(label) + " status failed: " + ec.message());
            if (std::filesystem::is_symlink(finalStatus))
                throw std::runtime_error(std::string(label) + " must not be a symlink");
            if (!std::filesystem::is_directory(finalStatus))
                throw std::runtime_error(std::string(label) + " must be a directory");
        }

        std::string GetLogDir()
        {
            const char* logDir = std::getenv("OBELISK_LOG_DIR");
            if (logDir && logDir[0] != '\0')
            {
                std::filesystem::path path(logDir);
                ValidateOrCreateLogDirectory(path, "OBELISK_LOG_DIR");
                return path.string();
            }

            const char* root = std::getenv("OBELISK_ROOT");
            if (root && root[0] != '\0')
            {
                std::filesystem::path rootPath(root);
                if (!rootPath.is_absolute())
                    throw std::runtime_error("OBELISK_ROOT must be absolute before deriving log directory");
                ValidateExistingPathComponentsNoSymlinks(rootPath, "OBELISK_ROOT");
                std::error_code ec;
                const std::filesystem::file_status rootStatus = std::filesystem::symlink_status(rootPath, ec);
                if (ec)
                    throw std::runtime_error("OBELISK_ROOT is not accessible before deriving log directory: " + ec.message());
                if (std::filesystem::is_symlink(rootStatus))
                    throw std::runtime_error("OBELISK_ROOT must not be a symlink before deriving log directory");
                if (std::filesystem::exists(rootStatus) && !std::filesystem::is_directory(rootStatus))
                    throw std::runtime_error("OBELISK_ROOT must be a directory before deriving log directory");

                std::filesystem::path path = std::filesystem::path(root) / "logs";
                ValidateOrCreateLogDirectory(path, "OBELISK_ROOT/logs");
                return path.string();
            }

            throw std::runtime_error("OBELISK_LOG_DIR or OBELISK_ROOT is required for runtime logging");
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

        std::string SanitizeIdentifier(const char* value)
        {
            if (!value || value[0] == '\0')
                return "";

            std::string sanitized;
            for (const unsigned char ch : std::string(value))
            {
                if (std::isalnum(ch) || ch == '_' || ch == '-')
                    sanitized.push_back(static_cast<char>(ch));
            }

            return sanitized;
        }

        std::string GetInstanceLogName()
        {
            const std::string mapName = GetMapNameFromCmdline();
            return "Obelisk-" + mapName + ".log";
        }

        std::filesystem::path GetInstanceLogDir(const std::filesystem::path& baseLogDir)
        {
            const std::string instanceId = SanitizeIdentifier(std::getenv("OBELISK_INSTANCE_ID"));
            if (instanceId.empty())
                return baseLogDir;

            std::filesystem::path path = baseLogDir / instanceId;
            ValidateOrCreateLogDirectory(path, "OBELISK instance log directory");
            return path;
        }
    }

    void Logger::Init()
    {
        if (s_Logger)
            return;

        auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
        console_sink->set_pattern("%^[%T] [Obelisk] %v%$");

        std::filesystem::path logDir = GetLogDir();
        std::filesystem::path instanceLogDir = GetInstanceLogDir(logDir);
        auto shared_file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((instanceLogDir / "Obelisk.log").string(), true);
        shared_file_sink->set_pattern("[%T] [%l] %v");

        auto instance_file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>((instanceLogDir / GetInstanceLogName()).string(), true);
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
