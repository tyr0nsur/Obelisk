#include "PluginControl.h"
#include "core/GameplayCallbackScope.h"
#include "core/OwnerExecutionGate.h"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <mutex>
#include <poll.h>
#include <set>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
#include <utility>

namespace Obelisk::Runtime
{
    namespace
    {
        using Json = nlohmann::json;
        using Clock = PluginControl::Clock;
        constexpr size_t kMaxRequestBytes = 4096;
        constexpr size_t kMaxResponseBytes = 65536;

        bool SafeLabel(const std::string& value)
        {
            return !value.empty() && value.size() <= 64 &&
                std::all_of(value.begin(), value.end(), [](unsigned char c) {
                    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                           (c >= '0' && c <= '9') || c == '_' || c == '-';
                });
        }

        Json Error(const char* code, const std::string& requestId = {}, bool started = false)
        {
            return { {"ok", false}, {"error", code}, {"request_id", requestId}, {"started", started} };
        }

        bool ReadLine(int fd, std::string& line, const std::atomic_bool& stopping)
        {
            const auto deadline = Clock::now() + std::chrono::seconds(2);
            while (!stopping.load(std::memory_order_acquire) && Clock::now() < deadline)
            {
                pollfd poller{fd, POLLIN, 0};
                const int available = ::poll(&poller, 1, 100);
                if (available < 0 && errno == EINTR) continue;
                if (available < 0) return false;
                if (!available) continue;
                char bytes[512];
                const auto count = ::recv(fd, bytes, sizeof(bytes), 0);
                if (count <= 0) return false;
                line.append(bytes, static_cast<size_t>(count));
                const auto end = line.find('\n');
                if (end != std::string::npos)
                {
                    if (end > kMaxRequestBytes || end + 1 != line.size()) return false;
                    line.resize(end);
                    return true;
                }
                if (line.size() > kMaxRequestBytes) return false;
            }
            return false;
        }

        void SendJson(int fd, Json response) noexcept
        {
            try
            {
                std::string bytes = response.dump();
                if (bytes.size() > kMaxResponseBytes) bytes = Error("response_too_large", {}, true).dump();
                bytes.push_back('\n');
                size_t offset = 0;
                const auto deadline = Clock::now() + std::chrono::seconds(1);
                while (offset < bytes.size() && Clock::now() < deadline)
                {
                    const auto written = ::send(fd, bytes.data() + offset, bytes.size() - offset, MSG_NOSIGNAL | MSG_DONTWAIT);
                    if (written > 0) { offset += static_cast<size_t>(written); continue; }
                    if (written < 0 && errno == EINTR) continue;
                    if (written < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
                    {
                        pollfd poller{fd, POLLOUT, 0};
                        ::poll(&poller, 1, 50);
                        continue;
                    }
                    break;
                }
            }
            catch (...) {}
        }

        int OpenParent(const std::filesystem::path& path, std::string& error)
        {
            const auto basename = path.filename().string();
            if (!path.is_absolute() || path.string().size() >= sizeof(sockaddr_un::sun_path) || basename.empty() || basename.size() > 80 ||
                !std::all_of(basename.begin(), basename.end(), [](unsigned char c) {
                    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                           (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
                })
                || path.filename() == "." || path.filename() == "..")
            {
                error = "socket path must be absolute with a safe basename";
                return -1;
            }
            int fd = ::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
            if (fd < 0) { error = "cannot open filesystem root"; return -1; }
            for (const auto& component : path.parent_path().relative_path())
            {
                const auto name = component.string();
                if (name == "." || name == ".." || name.empty())
                {
                    ::close(fd); error = "unsafe directory component"; return -1;
                }
                const int next = ::openat(fd, name.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
                ::close(fd);
                if (next < 0) { error = "socket parent inaccessible or contains a symlink"; return -1; }
                fd = next;
            }
            struct stat info{};
            if (::fstat(fd, &info) != 0 || !S_ISDIR(info.st_mode) ||
                (info.st_uid != ::geteuid() && info.st_uid != 0) || (info.st_mode & 0077) != 0)
            {
                ::close(fd); error = "socket parent must be owned by current UID/root with mode 0700"; return -1;
            }
            return fd;
        }
    }

    struct PluginControl::Impl
    {
        enum class Phase { Queued, Running, Finished, Cancelled };
        struct Pending
        {
            Request Value;
            Clock::time_point QueueDeadline;
            Phase CurrentPhase = Phase::Queued;
            Json Result;
        };
        std::mutex Mutex;
        std::condition_variable Wake;
        std::deque<std::shared_ptr<Pending>> Queue;
        std::thread Worker;
        std::thread::id Executor;
        std::atomic_bool Stopping{false};
        std::atomic_bool HasQueued{false};
        int Listener = -1;
        int Parent = -1;
        std::string Basename;
        dev_t SocketDevice = 0;
        ino_t SocketInode = 0;
        HandlerFn Handler = nullptr;
        void* Data = nullptr;
        bool Pumping = false;

        void Serve(int fd)
        {
            ucred peer{};
            socklen_t peerSize = sizeof(peer);
            if (::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &peer, &peerSize) != 0 || peerSize != sizeof(peer) ||
                !PluginControl::IsOperatorPeer(peer.uid, peer.pid))
            {
                SendJson(fd, Error("peer_not_authorized")); return;
            }
            std::string line;
            if (!ReadLine(fd, line, Stopping)) { SendJson(fd, Error("invalid_or_incomplete_request")); return; }
            bool duplicate = false;
            bool nested = false;
            std::set<std::string> observedKeys;
            const Json input = Json::parse(line, [&](int depth, Json::parse_event_t event, Json& value) {
                if (depth > 1) nested = true;
                if (event == Json::parse_event_t::key && !observedKeys.insert(value.get<std::string>()).second)
                    duplicate = true;
                return depth <= 1;
            }, false);
            if (!input.is_object() || nested || duplicate) { SendJson(fd, Error("invalid_json")); return; }
            const std::set<std::string> fields{"action", "plugin_id", "request_id", "timeout_ms"};
            for (auto it = input.begin(); it != input.end(); ++it)
                if (!fields.contains(it.key())) { SendJson(fd, Error("unknown_request_field")); return; }
            if (!input.contains("action") || !input["action"].is_string() ||
                !input.contains("request_id") || !input["request_id"].is_string())
            {
                SendJson(fd, Error("invalid_request")); return;
            }
            auto request = std::make_shared<Pending>();
            request->Value.Action = input["action"].get<std::string>();
            request->Value.RequestId = input["request_id"].get<std::string>();
            const std::set<std::string> actions{"status", "start", "pause", "resume", "stop", "reload"};
            if (!actions.contains(request->Value.Action) || !SafeLabel(request->Value.RequestId))
            {
                SendJson(fd, Error("invalid_action_or_request_id")); return;
            }
            if (input.contains("plugin_id"))
            {
                if (!input["plugin_id"].is_string()) { SendJson(fd, Error("invalid_plugin_id", request->Value.RequestId)); return; }
                request->Value.PluginId = input["plugin_id"].get<std::string>();
                if (!SafeLabel(request->Value.PluginId)) { SendJson(fd, Error("invalid_plugin_id", request->Value.RequestId)); return; }
            }
            if (request->Value.Action != "status" && request->Value.PluginId.empty())
            {
                SendJson(fd, Error("plugin_id_required", request->Value.RequestId)); return;
            }
            int timeoutMs = 2000;
            if (input.contains("timeout_ms"))
            {
                if (!input["timeout_ms"].is_number_integer() || input["timeout_ms"] < 1 || input["timeout_ms"] > 5000)
                { SendJson(fd, Error("invalid_timeout", request->Value.RequestId)); return; }
                timeoutMs = input["timeout_ms"].get<int>();
            }
            request->QueueDeadline = Clock::now() + std::chrono::milliseconds(timeoutMs);
            std::unique_lock lock(Mutex);
            if (Stopping.load(std::memory_order_acquire)) { lock.unlock(); SendJson(fd, Error("stopping", request->Value.RequestId)); return; }
            std::erase_if(Queue, [](const auto& item) { return item->CurrentPhase == Phase::Cancelled; });
            if (Queue.size() >= 32) { lock.unlock(); SendJson(fd, Error("busy", request->Value.RequestId)); return; }
            Queue.push_back(request);
            HasQueued.store(true, std::memory_order_release);
            Wake.notify_all();
            while (request->CurrentPhase == Phase::Queued && !Stopping.load(std::memory_order_acquire))
            {
                if (Wake.wait_until(lock, request->QueueDeadline) == std::cv_status::timeout && request->CurrentPhase == Phase::Queued)
                {
                    request->CurrentPhase = Phase::Cancelled;
                    request->Result = Error("request_expired", request->Value.RequestId);
                    HasQueued.store(std::any_of(Queue.begin(), Queue.end(), [](const auto& item) {
                        return item->CurrentPhase == Phase::Queued;
                    }), std::memory_order_release);
                    break;
                }
            }
            if (Stopping.load(std::memory_order_acquire) && request->CurrentPhase == Phase::Queued)
                request->CurrentPhase = Phase::Cancelled;
            if (request->CurrentPhase == Phase::Running)
            {
                Wake.wait_until(lock, request->Value.OperationDeadline, [&] {
                    return request->CurrentPhase != Phase::Running || Stopping.load(std::memory_order_acquire);
                });
            }
            Json response;
            if (request->CurrentPhase == Phase::Finished) response = request->Result;
            else if (request->CurrentPhase == Phase::Running) response = Error("in_progress", request->Value.RequestId, true);
            else if (!request->Result.is_null()) response = request->Result;
            else response = Error("stopping", request->Value.RequestId);
            lock.unlock();
            SendJson(fd, std::move(response));
        }

        void WorkerLoop() noexcept
        {
            while (!Stopping.load(std::memory_order_acquire))
            {
                pollfd poller{Listener, POLLIN, 0};
                const int ready = ::poll(&poller, 1, 100);
                if (ready < 0 && errno == EINTR) continue;
                if (ready <= 0) continue;
                const int fd = ::accept4(Listener, nullptr, nullptr, SOCK_CLOEXEC | SOCK_NONBLOCK);
                if (fd < 0) continue;
                try { Serve(fd); }
                catch (...) { try { SendJson(fd, Error("transport_failure")); } catch (...) {} }
                ::close(fd);
            }
        }

        void RemoveSocket() noexcept
        {
            if (Parent < 0) return;
            struct stat current{};
            if (::fstatat(Parent, Basename.c_str(), &current, AT_SYMLINK_NOFOLLOW) == 0 && S_ISSOCK(current.st_mode) &&
                current.st_dev == SocketDevice && current.st_ino == SocketInode)
                ::unlinkat(Parent, Basename.c_str(), 0);
            ::close(Parent);
            Parent = -1;
            SocketDevice = 0;
            SocketInode = 0;
        }
    };

    PluginControl::PluginControl() : m_Impl(std::make_unique<Impl>()) {}
    PluginControl::~PluginControl() { Stop(); }
    PluginControl& PluginControl::Get() { static auto* control = new PluginControl; return *control; }

    bool PluginControl::IsOperatorPeer(uint32_t uid, int32_t pid) noexcept
    {
        return pid > 0 && pid != ::getpid() && (uid == 0 || uid == ::geteuid());
    }

    bool PluginControl::Start(const std::filesystem::path& path, HandlerFn handler, void* data, std::string* outputError)
    {
        std::string error;
        if (!handler || m_Impl->Worker.joinable() || Core::OwnerExecutionGate::IsInsideExecution() || Core::GameplayCallbackScope::Current())
            error = "invalid handler, already started, or plugin callback context";
        else
        {
            const int parent = OpenParent(path, error);
            if (parent >= 0)
            {
                m_Impl->Parent = parent;
                m_Impl->Basename = path.filename().string();
                struct stat existing{};
                if (::fstatat(parent, m_Impl->Basename.c_str(), &existing, AT_SYMLINK_NOFOLLOW) == 0 || errno != ENOENT)
                    error = "socket node already exists or is inaccessible; refusing to remove it";
                else
                {
                    const auto boundPath = "/proc/self/fd/" + std::to_string(parent) + "/" + m_Impl->Basename;
                    sockaddr_un address{};
                    address.sun_family = AF_UNIX;
                    if (boundPath.size() >= sizeof(address.sun_path)) error = "socket basename too long";
                    else
                    {
                        std::memcpy(address.sun_path, boundPath.c_str(), boundPath.size() + 1);
                        m_Impl->Listener = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
                        if (m_Impl->Listener < 0 || ::bind(m_Impl->Listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0)
                            error = "cannot create/bind operator socket";
                        else
                        {
                            struct stat created{};
                            if (::fstatat(parent, m_Impl->Basename.c_str(), &created, AT_SYMLINK_NOFOLLOW) == 0)
                            { m_Impl->SocketDevice = created.st_dev; m_Impl->SocketInode = created.st_ino; }
                            if (!m_Impl->SocketInode || ::fchmodat(parent, m_Impl->Basename.c_str(), 0600, 0) != 0 ||
                                ::listen(m_Impl->Listener, 8) != 0)
                                error = "cannot secure/listen on operator socket";
                            else
                            {
                                m_Impl->Handler = handler;
                                m_Impl->Data = data;
                                m_Impl->Stopping.store(false, std::memory_order_release);
                                try { m_Impl->Worker = std::thread([this] { m_Impl->WorkerLoop(); }); return true; }
                                catch (...) { error = "cannot start operator socket worker"; }
                            }
                        }
                    }
                }
                if (m_Impl->Listener >= 0) { ::close(m_Impl->Listener); m_Impl->Listener = -1; }
                m_Impl->RemoveSocket();
            }
        }
        if (outputError) *outputError = error;
        return false;
    }

    void PluginControl::Stop() noexcept
    {
        if (Core::OwnerExecutionGate::IsInsideExecution() || Core::GameplayCallbackScope::Current()) return;
        m_Impl->Stopping.store(true, std::memory_order_release);
        try
        {
            {
                std::lock_guard lock(m_Impl->Mutex);
                for (auto& pending : m_Impl->Queue)
                    if (pending->CurrentPhase == Impl::Phase::Queued) pending->CurrentPhase = Impl::Phase::Cancelled;
                m_Impl->Queue.clear();
                m_Impl->HasQueued.store(false, std::memory_order_release);
                m_Impl->Wake.notify_all();
            }
            if (m_Impl->Worker.joinable() && m_Impl->Worker.get_id() != std::this_thread::get_id())
                m_Impl->Worker.join();
        }
        catch (...) { return; }
        if (m_Impl->Listener >= 0) { ::close(m_Impl->Listener); m_Impl->Listener = -1; }
        m_Impl->RemoveSocket();
    }

    bool PluginControl::BindExecutorThread() noexcept
    {
        if (Core::OwnerExecutionGate::IsInsideExecution() || Core::GameplayCallbackScope::Current()) return false;
        try
        {
            std::lock_guard lock(m_Impl->Mutex);
            const auto current = std::this_thread::get_id();
            if (m_Impl->Executor != std::thread::id{} && m_Impl->Executor != current) return false;
            m_Impl->Executor = current;
            return true;
        }
        catch (...) { return false; }
    }

    bool PluginControl::HasPending() const noexcept
    {
        return !m_Impl->Stopping.load(std::memory_order_acquire) && m_Impl->HasQueued.load(std::memory_order_acquire);
    }

    size_t PluginControl::PumpPending(size_t maximum) noexcept
    {
        if (!maximum || !HasPending() || Core::OwnerExecutionGate::IsInsideExecution() || Core::GameplayCallbackScope::Current()) return 0;
        size_t handled = 0;
        try
        {
            std::unique_lock lock(m_Impl->Mutex);
            if (m_Impl->Executor != std::this_thread::get_id() || m_Impl->Pumping || m_Impl->Stopping.load(std::memory_order_acquire))
                return 0;
            m_Impl->Pumping = true;
            while (handled < maximum && !m_Impl->Queue.empty())
            {
                auto pending = m_Impl->Queue.front();
                m_Impl->Queue.pop_front();
                m_Impl->HasQueued.store(std::any_of(m_Impl->Queue.begin(), m_Impl->Queue.end(), [](const auto& item) {
                    return item->CurrentPhase == Impl::Phase::Queued;
                }), std::memory_order_release);
                if (pending->CurrentPhase != Impl::Phase::Queued) continue;
                if (Clock::now() >= pending->QueueDeadline)
                {
                    pending->CurrentPhase = Impl::Phase::Cancelled;
                    pending->Result = Error("request_expired", pending->Value.RequestId);
                    m_Impl->Wake.notify_all();
                    continue;
                }
                pending->CurrentPhase = Impl::Phase::Running;
                pending->Value.OperationDeadline = Clock::now() + std::chrono::seconds(5);
                m_Impl->Wake.notify_all();
                const auto handler = m_Impl->Handler;
                void* data = m_Impl->Data;
                lock.unlock();
                Json result;
                try { result = handler(pending->Value, data); }
                catch (...) { result = Error("handler_failure", pending->Value.RequestId, true); }
                if (!result.is_object()) result = Error("invalid_handler_response", pending->Value.RequestId, true);
                result["request_id"] = pending->Value.RequestId;
                result["started"] = true;
                lock.lock();
                pending->Result = std::move(result);
                pending->CurrentPhase = Impl::Phase::Finished;
                ++handled;
                m_Impl->Wake.notify_all();
            }
            m_Impl->Pumping = false;
        }
        catch (...)
        {
            // No plugin/transport exception may escape into the game event.
            try { std::lock_guard lock(m_Impl->Mutex); m_Impl->Pumping = false; } catch (...) {}
        }
        return handled;
    }
}
