#pragma once

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <memory>
#include <string>
#include <nlohmann/json.hpp>

namespace Obelisk::Runtime
{
    // Local OS operator transport. No handler runs on its socket worker, and
    // neither player commands nor plugin callbacks have administrative authority.
    class PluginControl
    {
    public:
        using Clock = std::chrono::steady_clock;
        struct Request
        {
            std::string Action;
            std::string PluginId;
            std::string RequestId;
            Clock::time_point OperationDeadline;
        };
        using HandlerFn = nlohmann::json (*)(const Request&, void*);

        PluginControl();
        ~PluginControl();
        PluginControl(const PluginControl&) = delete;
        PluginControl& operator=(const PluginControl&) = delete;
        static PluginControl& Get();

        // Lifecycle calls are serialized by the runtime. Parent must exist,
        // belong to the current UID/root and have no group/other access. Existing
        // nodes (including stale sockets/symlinks) are refused rather than removed.
        bool Start(const std::filesystem::path&, HandlerFn, void* data = nullptr, std::string* error = nullptr);
        void Stop() noexcept;
        bool BindExecutorThread() noexcept;
        bool HasPending() const noexcept;
        size_t PumpPending(size_t maxRequests = 1) noexcept;
        static bool IsOperatorPeer(uint32_t uid, int32_t pid) noexcept;

        // timeout_ms bounds the queue window only. Once execution starts, a new
        // <=5s deadline is given to the handler. A response "in_progress" means
        // its outcome remains unknown, not cancellation or rollback.
        // Stop cancels queued requests and joins transport; it does not interrupt
        // a handler already running on the executor. Lifecycle must drain/join
        // that executor before destroying its HandlerFn/userdata.
    private:
        struct Impl;
        std::unique_ptr<Impl> m_Impl;
    };
}
