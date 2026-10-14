#include "runtime/PluginControl.h"
#include "core/GameplayCallbackScope.h"
#include "core/OwnerExecutionGate.h"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <poll.h>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
#include <cstring>

namespace
{
    using Control = Obelisk::Runtime::PluginControl;
    using Json = nlohmann::json;
    using namespace std::chrono_literals;

    void Require(bool value, const char* message)
    {
        if (!value) throw std::runtime_error(message);
    }

    struct Directory
    {
        std::filesystem::path Path;
        Directory()
        {
            char pattern[] = "/tmp/obelisk-plugin-control-test-XXXXXX";
            const char* created = ::mkdtemp(pattern);
            Require(created != nullptr, "cannot create private test directory");
            Path = created;
        }
        ~Directory() { std::error_code error; std::filesystem::remove_all(Path, error); }
    };

    struct Client
    {
        pid_t Pid = -1;
        int ReadFd = -1;
        Client(const std::filesystem::path& socketPath, const std::string& request)
        {
            int descriptors[2];
            Require(::pipe(descriptors) == 0, "cannot create child result pipe");
            sockaddr_un address{};
            address.sun_family = AF_UNIX;
            const auto path = socketPath.string();
            std::memcpy(address.sun_path, path.c_str(), path.size() + 1);
            Pid = ::fork();
            Require(Pid >= 0, "cannot fork operator client");
            if (Pid == 0)
            {
                // Only syscalls after fork from this multi-threaded process.
                ::close(descriptors[0]);
                const int channel = ::socket(AF_UNIX, SOCK_STREAM, 0);
                if (channel < 0 || ::connect(channel, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0)
                    ::_exit(2);
                if (::write(channel, request.data(), request.size()) != static_cast<ssize_t>(request.size()))
                    ::_exit(3);
                char response[65537];
                size_t size = 0;
                while (size < sizeof(response))
                {
                    pollfd poller{channel, POLLIN, 0};
                    if (::poll(&poller, 1, 7000) <= 0) ::_exit(4);
                    const auto count = ::read(channel, response + size, sizeof(response) - size);
                    if (count <= 0) break;
                    size += static_cast<size_t>(count);
                    if (::memchr(response, '\n', size)) break;
                }
                ::write(descriptors[1], response, size);
                ::close(channel);
                ::close(descriptors[1]);
                ::_exit(0);
            }
            ::close(descriptors[1]);
            ReadFd = descriptors[0];
        }
        bool Ready()
        {
            pollfd poller{ReadFd, POLLIN | POLLHUP, 0};
            return ::poll(&poller, 1, 0) > 0;
        }
        Json Result()
        {
            pollfd poller{ReadFd, POLLIN | POLLHUP, 0};
            Require(::poll(&poller, 1, 7000) > 0, "operator request did not return");
            char bytes[65537];
            const auto size = ::read(ReadFd, bytes, sizeof(bytes));
            Require(size > 0, "operator client received no JSON response");
            int status;
            ::waitpid(Pid, &status, 0);
            Pid = -1;
            Require(WIFEXITED(status) && WEXITSTATUS(status) == 0, "operator child failed");
            return Json::parse(bytes, bytes + size);
        }
        ~Client()
        {
            if (ReadFd >= 0) ::close(ReadFd);
            if (Pid > 0) { ::kill(Pid, SIGKILL); ::waitpid(Pid, nullptr, 0); }
        }
    };

    struct HandlerState
    {
        std::atomic<unsigned> Calls{0};
        std::thread::id Executor = std::this_thread::get_id();
        bool CorrectThread = true;
        bool CorrectDeadline = true;
    };

    Json Handler(const Control::Request& request, void* data)
    {
        auto& state = *static_cast<HandlerState*>(data);
        ++state.Calls;
        state.CorrectThread = state.CorrectThread && std::this_thread::get_id() == state.Executor;
        const auto remaining = request.OperationDeadline - Control::Clock::now();
        state.CorrectDeadline = state.CorrectDeadline && remaining > 0s && remaining <= 5s;
        return {{"ok", true}, {"action", request.Action}, {"plugin_id", request.PluginId}};
    }

    void PumpUntilReply(Control& control, Client& client)
    {
        const auto deadline = Control::Clock::now() + 2s;
        while (!client.Ready())
        {
            Require(Control::Clock::now() < deadline, "executor did not receive queued operation");
            control.PumpPending();
            std::this_thread::yield();
        }
    }

    void TestMainThreadPumpAndQueueExpiry()
    {
        Directory directory;
        Control control;
        HandlerState state;
        const auto socketPath = directory.Path / "plugin-control.sock";
        std::string error;
        Require(control.BindExecutorThread() && control.Start(socketPath, Handler, &state, &error), "operator socket start failed");
        struct stat info{};
        Require(::lstat(socketPath.c_str(), &info) == 0 && (info.st_mode & 0777) == 0600, "operator socket is not private0600");
        {
            Client expired(socketPath, "{\"action\":\"pause\",\"plugin_id\":\"oPing\",\"request_id\":\"expired\",\"timeout_ms\":30}\n");
            const auto response = expired.Result(); // No Pump: must cancel before mutation.
            Require(response["error"] == "request_expired" && response["started"] == false, "queued timeout pretended execution");
            Require(control.PumpPending() == 0 && state.Calls == 0, "expired request ran late after its client timed out");
        }
        {
            Client successful(socketPath, "{\"action\":\"resume\",\"plugin_id\":\"oPing\",\"request_id\":\"success\",\"timeout_ms\":2000}\n");
            std::atomic<size_t> wrongThreadPumped{99};
            std::thread worker([&] { wrongThreadPumped = control.PumpPending(); });
            worker.join();
            Require(wrongThreadPumped == 0, "socket/foreign worker executed runtime handler");
            PumpUntilReply(control, successful);
            const auto response = successful.Result();
            Require(response["ok"] == true && response["started"] == true && response["request_id"] == "success" &&
                    state.Calls == 1 && state.CorrectThread && state.CorrectDeadline,
                    "operator operation lost request/thread/deadline attribution");
        }
        {
            Client callbackRequest(socketPath, "{\"action\":\"stop\",\"plugin_id\":\"oPing\",\"request_id\":\"callback\",\"timeout_ms\":30}\n");
            using Scope = Obelisk::Core::GameplayCallbackScope;
            Scope scope(Obelisk::Core::GameplayCallbackFamily::ProcessEvent, Scope::TrackingMode::CurrentOnly);
            Require(control.PumpPending() == 0, "raw callback context executed hot control");
            const auto response = callbackRequest.Result();
            Require(response["error"] == "request_expired" && state.Calls == 1, "callback request was not cancelled");
        }
        Require(control.PumpPending() == 0 && state.Calls == 1, "cancelled callback-context request ran late");
        control.Stop();
        Require(!std::filesystem::exists(socketPath), "stopped transport left its own socket node");
    }

    void TestMalformedInputPeerPolicyAndSafeNodeCleanup()
    {
        Directory directory;
        Control control;
        HandlerState state;
        const auto socketPath = directory.Path / "plugin-control.sock";
        std::string error;
        Require(Control::IsOperatorPeer(::geteuid(), ::getpid() + 1) && Control::IsOperatorPeer(0, ::getpid() + 1),
                "current/root OS operator denied");
        Require(!Control::IsOperatorPeer(::geteuid() == 12345 ? 12346 : 12345, ::getpid() + 1) &&
                !Control::IsOperatorPeer(::geteuid(), ::getpid()) && !Control::IsOperatorPeer(::geteuid(), 0),
                "wrong UID/runtime peer bypassed operator policy");
        Require(control.BindExecutorThread() && control.Start(socketPath, Handler, &state, &error), "validation socket start failed");
        {
            const int ownProcess = ::socket(AF_UNIX, SOCK_STREAM, 0);
            sockaddr_un address{};
            address.sun_family = AF_UNIX;
            const auto path = socketPath.string();
            std::memcpy(address.sun_path, path.c_str(), path.size() + 1);
            Require(ownProcess >= 0 && ::connect(ownProcess, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0,
                    "cannot exercise real runtime peer credentials");
            pollfd poller{ownProcess, POLLIN, 0};
            const int ready = ::poll(&poller, 1, 2000);
            char bytes[512];
            const auto size = ready > 0 ? ::read(ownProcess, bytes, sizeof(bytes)) : -1;
            ::close(ownProcess);
            Require(size > 0 && Json::parse(bytes, bytes + size)["error"] == "peer_not_authorized" && state.Calls == 0,
                    "real SO_PEERCRED allowed plugin/runtime process to administer itself");
        }
        const std::string invalid[] = {
            "{\"action\":\"reload\",\"plugin_id\":\"../oPing\",\"request_id\":\"bad\"}\n",
            "{\"action\":\"admin-player\",\"plugin_id\":\"oPing\",\"request_id\":\"bad\"}\n",
            "{\"action\":\"status\",\"request_id\":\"bad\",\"steam_id\":123}\n",
            "{\"action\":\"status\",\"request_id\":\"bad\",\"action\":\"reload\"}\n",
            "{\"action\":\"status\",\"request_id\":\"bad\",\"timeout_ms\":-1}\n",
            std::string(4097, 'x') + '\n',
        };
        for (const auto& request : invalid)
        {
            Client client(socketPath, request);
            const auto response = client.Result();
            Require(response["ok"] == false && response["started"] == false && state.Calls == 0,
                    "invalid/authority input reached runtime handler");
        }
        const auto moved = directory.Path / "original.sock";
        std::filesystem::rename(socketPath, moved);
        std::filesystem::create_symlink("untouched-target", socketPath);
        control.Stop();
        Require(std::filesystem::is_symlink(socketPath) && std::filesystem::exists(moved),
                "Stop removed a replacement node rather than only its owned inode");
        Require(!control.Start(socketPath, Handler, &state, &error) && std::filesystem::is_symlink(socketPath),
                "Start removed/followed a stale/symlink socket node");
        std::filesystem::remove(socketPath);
        ::chmod(directory.Path.c_str(), 0755);
        Require(!control.Start(socketPath, Handler, &state, &error), "non-private socket directory accepted");
        ::chmod(directory.Path.c_str(), 0700);
        const auto linkedParent = directory.Path / "link";
        std::filesystem::create_symlink(directory.Path, linkedParent);
        Require(!control.Start(linkedParent / "control.sock", Handler, &state, &error), "symlink directory accepted");
    }
}

int main()
{
    try
    {
        TestMainThreadPumpAndQueueExpiry();
        TestMalformedInputPeerPolicyAndSafeNodeCleanup();
        std::cout << "PluginControlTests passed\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "PluginControlTests failed: " << error.what() << '\n';
        return 1;
    }
}
