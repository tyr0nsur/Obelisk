#pragma once
#include "obelisk/ObeliskChatSessionApi.h"
#include <cstdint>
#include <mutex>
#include <string>
#include <string_view>
#include <thread>
#include <vector>
namespace Obelisk::Core {
class ChatSessionRegistry {
public:
    struct Endpoint { void* Controller=nullptr; void* Connection=nullptr; void* PlayerState=nullptr; };
    using Validate = bool (*)(const Endpoint&, void*) noexcept;
    using Send = bool (*)(const Endpoint&, std::string_view, void*) noexcept;
    static ChatSessionRegistry& Get();
    bool Configure(uint64_t epoch, Validate validate, Send send, void* data=nullptr) noexcept;
    bool Available() const noexcept;
    uint64_t Observe(const Endpoint&, std::string_view name, bool pendingLogin=false) noexcept;
    bool Activate(uint64_t token) noexcept;
    void InvalidateController(void*) noexcept;
    void InvalidateToken(uint64_t) noexcept;
    bool Snapshot(uint64_t, ObeliskChatSession*) noexcept;
    bool List(ObeliskChatSession*, size_t capacity, size_t* written, size_t* total) noexcept;
    bool Deliver(uint64_t, uint64_t epoch, std::string_view) noexcept;
private:
    struct Record { Endpoint Target; std::string Name; uint64_t Token=0; bool Pending=false; };
    bool MainThread() const noexcept;
    static void Copy(const Record&, uint64_t, ObeliskChatSession&) noexcept;
    mutable std::mutex m_Mutex;
    std::vector<Record> m_Records;
    uint64_t m_Epoch=0, m_Next=1;
    std::thread::id m_Thread;
    Validate m_Validate=nullptr; Send m_Send=nullptr; void* m_Data=nullptr;
};
}
