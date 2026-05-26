#include "Logger.h"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>

namespace Obelisk
{
    std::shared_ptr<spdlog::logger> Logger::s_Logger;

    void Logger::Init()
    {
        // Create a console sink and a file sink
        auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
        console_sink->set_pattern("%^[%T] [Obelisk] %v%$");

        auto file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>("Obelisk.log", true);
        file_sink->set_pattern("[%T] [%l] %v");

        std::vector<spdlog::sink_ptr> sinks { console_sink, file_sink };

        s_Logger = std::make_shared<spdlog::logger>("Obelisk", sinks.begin(), sinks.end());
        spdlog::register_logger(s_Logger);
        s_Logger->set_level(spdlog::level::trace);
        s_Logger->flush_on(spdlog::level::trace);
    }

    std::shared_ptr<spdlog::logger>& Logger::Get()
    {
        return s_Logger;
    }
}
