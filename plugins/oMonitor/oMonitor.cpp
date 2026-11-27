#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstring>
#include <deque>
#include <fcntl.h>
#include <fstream>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <vector>

// Original ObeliskNative monitor resource. Managed timer callbacks perform only
// OS reads and writes of copied values. No UE pointer is retained or dereferenced.
namespace {
using Json = nlohmann::json;
using Clock = std::chrono::steady_clock;
ObeliskApi api{};
uint64_t owner = 0, timer = 0, lifecycle = 0;
struct State {
    int directory = -1;
    std::string instance, startTicks;
    std::mutex mutex;
    std::deque<Json> events;
    uint64_t logins = 0, logouts = 0, sequence = 0;
    std::atomic<uint64_t> dropped{0};
    Clock::time_point previous = Clock::now();
    double previousCpu = 0;
    bool lifecycleAvailable = false, writeErrorLogged = false;
    ~State() { if (directory >= 0) ::close(directory); }
};
std::unique_ptr<State> state;
constexpr const char* defaults = "{\"enabled\":false,\"allow_all_instances\":false,\"instance_allowlist\":[]}";

int PrivateDirectory(const std::string& path) {
    if (path.empty() || path.front() != '/' || path.back() == '/') return -1;
    int fd = ::open("/", O_PATH | O_DIRECTORY | O_CLOEXEC);
    std::istringstream parts(path.substr(1)); std::string part;
    while (fd >= 0 && std::getline(parts, part, '/')) {
        if (part.empty() || part == "." || part == "..") { ::close(fd); return -1; }
        int next = ::openat(fd, part.c_str(), O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        ::close(fd); fd = next;
        struct stat info{};
        if (fd >= 0 && (::fstat(fd, &info) || (info.st_uid != 0 && info.st_uid != ::geteuid()) ||
            ((info.st_mode & 0022) && !(info.st_uid == 0 && (info.st_mode & S_ISVTX))))) {
            ::close(fd); return -1;
        }
    }
    struct stat info{};
    if (fd >= 0 && (::fstat(fd, &info) || info.st_uid != ::geteuid() || (info.st_mode & 0077))) {
        ::close(fd); return -1;
    }
    return fd;
}
std::string StartTicks() {
    std::ifstream input("/proc/self/stat"); std::string line;
    std::getline(input, line); auto end = line.rfind(')');
    if (end == std::string::npos) return {};
    std::istringstream fields(line.substr(end + 2)); std::string field;
    for (int number = 3; number <= 22; ++number) if (!(fields >> field)) return {};
    if (field.empty() || field.find_first_not_of("0123456789") != std::string::npos) return {};
    return field;
}
double CpuSeconds() {
    timespec value{}; if (::clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value)) throw 1;
    return value.tv_sec + value.tv_nsec / 1e9;
}
Json CopyString(const ObeliskPlayerLifecycleStringView& text, bool available) {
    if (!available || !text.data || !text.size || text.size > 256) return nullptr;
    std::string copy(text.data, text.size);
    for (char& ch : copy) if (static_cast<unsigned char>(ch) < 32 || ch == 127) ch = ' ';
    return copy;
}
void OnLifecycle(const ObeliskPlayerLifecycleEvent* event, void*) {
    if (!state || !event || event->abi_version != OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION ||
        event->struct_size < sizeof(*event) || !event->sequence || !event->process_epoch ||
        (event->flags & ~OBELISK_PLAYER_LIFECYCLE_FLAGS_SUPPORTED_MASK) ||
        (event->kind != OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED && event->kind != OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED)) return;
    try {
        std::unique_lock<std::mutex> lock(state->mutex, std::try_to_lock);
        if (!lock.owns_lock()) { state->dropped.fetch_add(1); return; }
        const bool login = event->kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED;
        if (login) ++state->logins; else ++state->logouts;
        if (state->events.size() == 32) state->events.pop_front();
        state->events.push_back({{"kind", login ? "login_observed" : "logout_observed"},
            {"sequence", std::to_string(event->sequence)}, {"process_epoch", std::to_string(event->process_epoch)},
            {"observed_at_ms", std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count()},
            {"name", CopyString(event->player_name, event->flags & OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE)},
            {"opaque_id", CopyString(event->platform_id, event->flags & OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE)}});
    } catch (...) { state->dropped.fetch_add(1); }
}
void Publish(uint64_t, void*) {
    if (!state) return;
    try {
        const auto now = Clock::now(); const double cpu = CpuSeconds();
        const double elapsed = std::chrono::duration<double>(now - state->previous).count();
        const double percent = elapsed > 0 ? std::clamp(100.0 * (cpu - state->previousCpu) / elapsed, 0.0, 65536.0) : 0;
        state->previous = now; state->previousCpu = cpu;
        std::ifstream memory("/proc/self/statm"); uint64_t total = 0, resident = 0;
        if (!(memory >> total >> resident)) throw 1;
        timespec boot{}; if (::clock_gettime(CLOCK_BOOTTIME, &boot)) throw 1;
        const long hz = ::sysconf(_SC_CLK_TCK), page = ::sysconf(_SC_PAGESIZE);
        if (hz <= 0 || page <= 0) throw 1;
        Json events; uint64_t logins, logouts;
        { std::lock_guard<std::mutex> lock(state->mutex); events = state->events; logins = state->logins; logouts = state->logouts; }
        Json snapshot = {{"schema", "obelisk.monitor.v1"}, {"resource_version", "0.1.0"}, {"instance_id", state->instance},
            {"pid", ::getpid()}, {"process_start_ticks", state->startTicks}, {"sequence", ++state->sequence},
            {"generated_at_ms", std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count()},
            {"process", {{"cpu_percent", percent}, {"rss_bytes", resident * uint64_t(page)},
                {"uptime_seconds", std::max(0.0, boot.tv_sec + boot.tv_nsec / 1e9 - std::stod(state->startTicks) / hz)}}},
            {"lifecycle", {{"available", state->lifecycleAvailable}, {"login_observations", logins},
                {"logout_observations", logouts}, {"dropped_observations", state->dropped.load()}, {"recent_events", events}}},
            {"player_census", nullptr}, {"game_thread", nullptr}};
        const std::string bytes = snapshot.dump(); if (bytes.size() > 60000) throw 1;
        // The private directory fd is pinned. Never truncate an unchecked node.
        int fd = ::openat(state->directory, "monitor.tmp", O_WRONLY | O_CREAT | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0600);
        if (fd < 0) throw 1;
        struct stat info{};
        if (::fstat(fd, &info) || !S_ISREG(info.st_mode) || info.st_uid != ::geteuid() || info.st_nlink != 1 || (info.st_mode & 0077) || ::ftruncate(fd, 0)) { ::close(fd); throw 1; }
        size_t offset = 0;
        while (offset < bytes.size()) { ssize_t count = ::write(fd, bytes.data() + offset, bytes.size() - offset); if (count <= 0) { ::close(fd); throw 1; } offset += size_t(count); }
        if (::close(fd) || ::renameat(state->directory, "monitor.tmp", state->directory, "monitor.snapshot.json")) throw 1;
    } catch (...) {
        if (!state->writeErrorLogged && api.LogError) api.LogError("[oMonitor] Snapshot unavailable: check the private directory and process metrics access.");
        state->writeErrorLogged = true;
    }
}
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out) {
    if (!out) return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(*out), "oMonitor", "oMonitor", "0.1.0", "config.json", defaults}; return true;
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* input, const ObeliskPluginInitContext* context) {
    if (!input || !context || state || input->abi_version != OBELISK_API_ABI_VERSION ||
        input->struct_size < offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) + sizeof(input->UnregisterTimerWithOwnerToken) ||
        !(input->capabilities & OBELISK_API_CAPABILITY_TIMERS) || !input->RegisterTimerWithOwnerTokenHandle || !input->UnregisterTimerWithOwnerToken ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION || context->struct_size < sizeof(*context) ||
        !context->plugin_owner_token || !context->config_path || !context->config_dir || !context->instance_id) return false;
    std::memcpy(&api, input, std::min<size_t>(sizeof(api), input->struct_size));
    try {
        std::ifstream file(context->config_path); std::string text(8193, '\0'); file.read(text.data(), text.size());
        if (file.gcount() > 8192 || file.bad()) return false; text.resize(size_t(file.gcount()));
        const auto config = Json::parse(text);
        if (!config.is_object() || !config.value("enabled", false)) return true;
        const auto allow = config.at("instance_allowlist").get<std::vector<std::string>>();
        if (std::find(allow.begin(), allow.end(), context->instance_id) == allow.end() && !config.value("allow_all_instances", false)) return true;
        state = std::make_unique<State>(); state->instance = context->instance_id; state->startTicks = StartTicks();
        state->directory = PrivateDirectory(context->config_dir);
        if (state->directory < 0 || state->startTicks.empty()) {
            if (api.LogError) api.LogError(state->directory < 0 ? "[oMonitor] Config directory must have trusted ancestors and owner-only mode 0700." : "[oMonitor] Process start identity cannot be read.");
            state.reset(); return false;
        }
        std::memcpy(&api, input, std::min<size_t>(sizeof(api), input->struct_size)); owner = context->plugin_owner_token;
        if (input->struct_size >= offsetof(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) + sizeof(input->UnregisterPlayerLifecycleWithOwnerToken) &&
            (input->capabilities & OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS) && input->RegisterPlayerLifecycleWithOwnerTokenHandle && input->UnregisterPlayerLifecycleWithOwnerToken) {
            lifecycle = api.RegisterPlayerLifecycleWithOwnerTokenHandle(owner, OnLifecycle, nullptr);
            state->lifecycleAvailable = lifecycle != 0;
        }
        state->previousCpu = CpuSeconds();
        timer = api.RegisterTimerWithOwnerTokenHandle(owner, 1000, 2000, OBELISK_TIMER_FLAG_REPEATING, Publish, nullptr);
        if (!timer) { if (api.LogError) api.LogError("[oMonitor] Managed repeating timer registration rejected."); return false; }
        if (api.LogInfo) api.LogInfo("[oMonitor] Native process metrics and copied lifecycle events enabled; private snapshots every 2 seconds.");
        return true;
    } catch (...) { if (api.LogError) api.LogError("[oMonitor] Configuration or process metrics initialization failed."); return false; }
}
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown() {
    if (timer && api.UnregisterTimerWithOwnerToken) api.UnregisterTimerWithOwnerToken(owner, timer);
    if (lifecycle && api.UnregisterPlayerLifecycleWithOwnerToken) api.UnregisterPlayerLifecycleWithOwnerToken(owner, lifecycle);
    timer = lifecycle = owner = 0; state.reset(); api = {};
}
extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities() { return OBELISK_PLUGIN_LIFECYCLE_MANAGED_CALLBACKS_ONLY; }
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload() { return true; }
