#include "ChatSessionRegistry.h"
#include <algorithm>
#include <cstring>
#include <limits>
namespace Obelisk::Core {
namespace {
bool Utf8(std::string_view s) noexcept {
    if (!s.data()) return s.empty();
    for(size_t i=0;i<s.size();) {
        unsigned c=static_cast<unsigned char>(s[i++]); if(!c)return false;if(c<128)continue;
        unsigned n=0,v=0,min=0;
        if(c>=0xc2&&c<=0xdf){n=1;v=c&31;min=0x80;}
        else if(c>=0xe0&&c<=0xef){n=2;v=c&15;min=0x800;}
        else if(c>=0xf0&&c<=0xf4){n=3;v=c&7;min=0x10000;}else return false;
        if(n>s.size()-i)return false;while(n--){c=static_cast<unsigned char>(s[i++]);if((c&0xc0)!=0x80)return false;v=(v<<6)|(c&63);}
        if(v<min||v>0x10ffff||(v>=0xd800&&v<=0xdfff))return false;
    }return true;
}
}
ChatSessionRegistry& ChatSessionRegistry::Get(){static auto* value=new ChatSessionRegistry;return *value;}
bool ChatSessionRegistry::Configure(uint64_t epoch,Validate validate,Send send,void* data) noexcept {
    try{std::lock_guard lock(m_Mutex);if(m_Epoch||!epoch||!validate||!send)return false;
    m_Epoch=epoch;m_Thread=std::this_thread::get_id();m_Validate=validate;m_Send=send;m_Data=data;return true;}catch(...){return false;}
}
bool ChatSessionRegistry::MainThread()const noexcept{return m_Epoch&&m_Thread==std::this_thread::get_id();}
bool ChatSessionRegistry::Available()const noexcept{return m_Epoch&&m_Validate&&m_Send;}
uint64_t ChatSessionRegistry::Observe(const Endpoint& endpoint,std::string_view name,bool pending) noexcept {
    if(!MainThread()||!endpoint.Controller||!endpoint.Connection||!endpoint.PlayerState||!m_Validate(endpoint,m_Data))return 0;
    try{
        std::string copied;if(name.size()<=256&&Utf8(name))copied=name;
        std::lock_guard lock(m_Mutex);
        auto current=std::find_if(m_Records.begin(),m_Records.end(),[&](const auto& r){return r.Target.Controller==endpoint.Controller;});
        if(current!=m_Records.end()){
            if(!pending&&current->Target.Connection==endpoint.Connection&&current->Target.PlayerState==endpoint.PlayerState){
                if(current->Pending)return 0;current->Name=std::move(copied);return current->Token;
            }
            m_Records.erase(current);
        }
        if(m_Records.size()>=1024)std::erase_if(m_Records,[&](const auto& r){return !m_Validate(r.Target,m_Data);});
        if(m_Records.size()>=1024||m_Next==std::numeric_limits<uint64_t>::max())return 0;
        const auto token=m_Next++;m_Records.push_back({endpoint,std::move(copied),token,pending});return token;
    }catch(...){return 0;}
}
bool ChatSessionRegistry::Activate(uint64_t token) noexcept {
    if(!MainThread()||!token)return false;
    try{std::lock_guard lock(m_Mutex);for(auto& r:m_Records)if(r.Token==token){if(!m_Validate(r.Target,m_Data)){r.Pending=true;return false;}r.Pending=false;return true;}return false;}catch(...){return false;}
}
void ChatSessionRegistry::InvalidateController(void* controller) noexcept {
    if(!MainThread())return;try{std::lock_guard lock(m_Mutex);std::erase_if(m_Records,[&](const auto& r){return r.Target.Controller==controller;});}catch(...){}
}
void ChatSessionRegistry::InvalidateToken(uint64_t token) noexcept {
    if(!MainThread())return;try{std::lock_guard lock(m_Mutex);std::erase_if(m_Records,[&](const auto& r){return r.Token==token;});}catch(...){}
}
void ChatSessionRegistry::Copy(const Record& r,uint64_t epoch,ObeliskChatSession& out) noexcept {
    out={};out.abi_version=OBELISK_CHAT_SESSION_ABI_VERSION;out.struct_size=sizeof(out);out.session_token=r.Token;out.process_epoch=epoch;
    if(!r.Name.empty()){out.flags=OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE;out.player_name_size=r.Name.size();std::memcpy(out.player_name,r.Name.data(),r.Name.size());}
}
bool ChatSessionRegistry::Snapshot(uint64_t token,ObeliskChatSession* out) noexcept {
    if(!MainThread()||!out||out->struct_size<sizeof(*out))return false;
    try{std::lock_guard lock(m_Mutex);for(const auto& r:m_Records)if(r.Token==token&&!r.Pending&&m_Validate(r.Target,m_Data)){Copy(r,m_Epoch,*out);return true;}return false;}catch(...){return false;}
}
bool ChatSessionRegistry::List(ObeliskChatSession* records,size_t capacity,size_t* written,size_t* total) noexcept {
    if(!MainThread()||!written||!total||written==total||capacity>64||(capacity&&!records))return false;
    for(size_t i=0;i<capacity;++i)if(records[i].struct_size<sizeof(*records))return false;
    *written=*total=0;try{std::lock_guard lock(m_Mutex);for(const auto& r:m_Records)if(!r.Pending&&m_Validate(r.Target,m_Data)){
        if(*written<capacity)Copy(r,m_Epoch,records[(*written)++]);++*total;
    }return true;}catch(...){*written=*total=0;return false;}
}
bool ChatSessionRegistry::Deliver(uint64_t token,uint64_t epoch,std::string_view text) noexcept {
    if(!MainThread()||!token||epoch!=m_Epoch||text.empty()||text.size()>1024||!Utf8(text))return false;
    Endpoint endpoint;
    try{{std::lock_guard lock(m_Mutex);auto r=std::find_if(m_Records.begin(),m_Records.end(),[&](const auto& r){return r.Token==token&&!r.Pending;});
        if(r==m_Records.end())return false;endpoint=r->Target;}
        if(!m_Validate(endpoint,m_Data)){InvalidateToken(token);return false;}
        return m_Send(endpoint,text,m_Data);
    }catch(...){return false;}
}
}
