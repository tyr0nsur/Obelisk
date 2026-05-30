#include <cstdio>
#include <cstring>
#include <errno.h>
#include <exception>
#include <atomic>
#include <cstdlib>
#include <chrono>
#include <cctype>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <sys/prctl.h>
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include "hooks/HookManager.h"
#include "hooks/ProcessEventHook.h"
#include "core/PluginManager.h"
#include "ue/ReflectionScanner.h"

static bool g_ObeliskStarted = false;
static std::atomic<bool> g_DebugControlStopRequested{false};
static std::thread g_DebugControlThread;
static std::mutex g_DebugControlMutex;
static std::condition_variable g_DebugControlWake;

static std::string GetPluginDirectory()
{
    const char* specific = std::getenv("OBELISK_PLUGIN_DIR");
    if (specific && specific[0] != '\0')
        return specific;

    const char* root = std::getenv("OBELISK_ROOT");
    if (root && root[0] != '\0')
        return (std::filesystem::path(root) / "plugins").string();

    return {};
}

static void ConfigureDebugPtrace()
{
    if (!Obelisk::Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_DEBUG_ALLOW_PTRACE", "allow-ptrace"))
        return;

    if (prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0) == 0)
    {
        OBELISK_WARN("Debug ptrace attach enabled by OBELISK_DEBUG_ALLOW_PTRACE=1.");
        return;
    }

    OBELISK_ERROR("Failed to enable debug ptrace attach: errno={} ({})", errno, std::strerror(errno));
}

static std::string SanitizePathComponent(const char* value, const char* fallback)
{
    if (!value || value[0] == '\0')
        return fallback;

    std::string sanitized;
    for (unsigned char ch : std::string(value))
    {
        if (std::isalnum(ch) || ch == '_' || ch == '-')
            sanitized.push_back(static_cast<char>(ch));
    }

    return sanitized.empty() ? fallback : sanitized;
}

static std::filesystem::path GetDebugControlDirectory()
{
    const char* root = std::getenv("OBELISK_ROOT");
    const std::filesystem::path base = root && root[0] != '\0' ? std::filesystem::path(root) : std::filesystem::path(".");
    const std::string instance = SanitizePathComponent(std::getenv("OBELISK_INSTANCE_ID"), "default");
    return base / "state" / "instances" / instance;
}

static std::vector<uintptr_t> ParseAddressList(const std::string& contents)
{
    std::string normalized = contents;
    for (char& ch : normalized)
    {
        if (ch == ',' || ch == ';')
            ch = ' ';
    }

    std::vector<uintptr_t> addresses;
    std::istringstream stream(normalized);
    std::string token;
    while (stream >> token)
    {
        try
        {
            size_t consumed = 0;
            const unsigned long long value = std::stoull(token, &consumed, 0);
            if (consumed == token.size() && value != 0)
                addresses.push_back(static_cast<uintptr_t>(value));
            else
                OBELISK_WARN("Debug control ignored invalid address token '{}'.", token);
        }
        catch (const std::exception&)
        {
            OBELISK_WARN("Debug control ignored invalid address token '{}'.", token);
        }
    }

    return addresses;
}

static void ProcessStaticFNameProbeRequest(const std::filesystem::path& requestPath)
{
    std::ifstream file(requestPath);
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::vector<uintptr_t> slots = ParseAddressList(buffer.str());
    if (slots.empty())
    {
        OBELISK_WARN("Debug control static FName probe request had no valid slots: {}", requestPath.string());
        return;
    }

    OBELISK_INFO("Debug control running static FName probe for {} slot(s) from {}.", slots.size(), requestPath.string());
    Obelisk::UE::ReflectionScanner::RunStaticFNameRootProbe(slots);
}

static void MarkDebugControlRequestDone(const std::filesystem::path& requestPath)
{
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
    const std::filesystem::path donePath = requestPath.string() + ".done." + std::to_string(millis);

    std::error_code ec;
    std::filesystem::rename(requestPath, donePath, ec);
    if (ec)
    {
        OBELISK_WARN("Debug control could not archive request {}: {}", requestPath.string(), ec.message());
        std::filesystem::remove(requestPath, ec);
    }
}

static void StartDebugControlThread()
{
    if (!Obelisk::Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ENABLE_DEBUG_CONTROL", "enable-debug-control"))
        return;

    if (g_DebugControlThread.joinable())
    {
        OBELISK_WARN("Debug control thread already running.");
        return;
    }

    const std::filesystem::path controlDir = GetDebugControlDirectory();
    std::error_code ec;
    std::filesystem::create_directories(controlDir, ec);
    if (ec)
    {
        OBELISK_ERROR("Debug control could not create {}: {}", controlDir.string(), ec.message());
        return;
    }

    OBELISK_WARN("Debug control enabled. Watching {} for marker requests.", controlDir.string());
    g_DebugControlStopRequested.store(false, std::memory_order_release);
    g_DebugControlThread = std::thread([controlDir]() {
        const std::filesystem::path staticFNameProbePath = controlDir / "request-static-fname-probe";

        while (!g_DebugControlStopRequested.load(std::memory_order_acquire) &&
               Obelisk::Logger::IsInitialized())
        {
            std::error_code existsEc;
            if (std::filesystem::exists(staticFNameProbePath, existsEc))
            {
                try
                {
                    ProcessStaticFNameProbeRequest(staticFNameProbePath);
                }
                catch (const std::exception& e)
                {
                    OBELISK_ERROR("Debug control static FName probe failed: {}", e.what());
                }
                catch (...)
                {
                    OBELISK_ERROR("Debug control static FName probe failed with unknown exception.");
                }
                MarkDebugControlRequestDone(staticFNameProbePath);
            }

            std::unique_lock<std::mutex> lock(g_DebugControlMutex);
            g_DebugControlWake.wait_for(lock, std::chrono::seconds(2), [] {
                return g_DebugControlStopRequested.load(std::memory_order_acquire);
            });
        }
    });
}

static void StopDebugControlThread()
{
    g_DebugControlStopRequested.store(true, std::memory_order_release);
    g_DebugControlWake.notify_all();
    if (g_DebugControlThread.joinable())
        g_DebugControlThread.join();
}

static bool RemoveHookBeforePluginUnload()
{
    if (Obelisk::Hooks::ProcessEventHook::Remove())
        return true;

    OBELISK_CRITICAL(
        "ProcessEvent hook removal failed; preserving plugins and logger to avoid unloading code while detour frames may still be active.");
    return false;
}

static bool ShutdownRuntimeAfterHookRemoval()
{
    StopDebugControlThread();
    if (!RemoveHookBeforePluginUnload())
        return false;

    Obelisk::Core::PluginManager::Get().UnloadAll();
    Obelisk::Logger::Shutdown();
    g_ObeliskStarted = false;
    return true;
}

// The constructor attribute ensures this function runs as soon as the shared library 
// is loaded into the target process via LD_PRELOAD.
__attribute__((constructor))
void Obelisk_Init() 
{
    // Avoid injecting into LinuxGSM scripts (bash, grep, tmux, etc)
    if (program_invocation_short_name != nullptr && strstr(program_invocation_short_name, "ShooterGameServer") == nullptr) 
    {
        return;
    }

    try
    {
        Obelisk::Logger::Init();
        g_ObeliskStarted = true;

    OBELISK_INFO("==========================================");
    OBELISK_INFO(" Obelisk Runtime Loaded Native (LD_PRELOAD)");
    OBELISK_INFO("==========================================");
    OBELISK_INFO("Starting runtime bootstrap...");

    ConfigureDebugPtrace();
    StartDebugControlThread();
    
    // Initialize hooking engine
    Obelisk::Hooks::HookManager::Init();

        if (Obelisk::Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ENABLE_REFLECTION_SCANNER", "enable-reflection-scanner"))
        {
            Obelisk::UE::ReflectionScanner::RunStartupScan();
        }
        else
        {
            OBELISK_INFO("ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 and enable-reflection-scanner marker to run the experimental scanner.");
        }

        const char* disablePlugins = std::getenv("OBELISK_DISABLE_PLUGINS");
        if (disablePlugins && std::strcmp(disablePlugins, "1") == 0)
        {
            OBELISK_WARN("Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.");
        }
        else
        {
            Obelisk::Core::PluginManager::Get().LoadPlugins(GetPluginDirectory());
        }
    }
    catch (const std::exception& e)
    {
        if (Obelisk::Logger::IsInitialized())
        {
            OBELISK_CRITICAL("Obelisk bootstrap failed: {}", e.what());
            if (!ShutdownRuntimeAfterHookRemoval())
                return;
        }
        g_ObeliskStarted = false;
    }
    catch (...)
    {
        if (Obelisk::Logger::IsInitialized())
        {
            OBELISK_CRITICAL("Obelisk bootstrap failed with unknown exception.");
            if (!ShutdownRuntimeAfterHookRemoval())
                return;
        }
        g_ObeliskStarted = false;
    }
}

__attribute__((destructor))
void Obelisk_Shutdown()
{
    if (!g_ObeliskStarted || !Obelisk::Logger::IsInitialized())
        return;

    OBELISK_INFO("Obelisk Runtime Shutting Down...");
    ShutdownRuntimeAfterHookRemoval();
}
