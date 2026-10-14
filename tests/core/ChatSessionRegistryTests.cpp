#include "core/ChatSessionRegistry.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <unordered_set>
using namespace Obelisk::Core;
namespace {
void Require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
struct Fake {std::unordered_set<void*> Alive;unsigned Calls=0;void* Last=nullptr;std::string Text;};
bool Validate(const ChatSessionRegistry::Endpoint& e,void* context)noexcept{return static_cast<Fake*>(context)->Alive.count(e.Controller)&&e.Connection&&e.PlayerState;}
bool Send(const ChatSessionRegistry::Endpoint& e,std::string_view text,void* context)noexcept{
 try{auto& fake=*static_cast<Fake*>(context);++fake.Calls;fake.Last=e.Controller;fake.Text=text;return true;}catch(...){return false;}
}
}
int main(){try{
 Fake fake;ChatSessionRegistry registry;Require(!registry.Configure(0,Validate,Send,&fake),"zero epoch");Require(registry.Configure(17,Validate,Send,&fake),"configure");
 int a,b,c,d;fake.Alive={&a,&b};auto ea=ChatSessionRegistry::Endpoint{&a,&c,&d};auto eb=ChatSessionRegistry::Endpoint{&b,&c,&d};
 std::string name="España";auto first=registry.Observe(ea,name);name="changed";
 ObeliskChatSession value{};value.struct_size=sizeof(value);Require(first&&registry.Snapshot(first,&value)&&std::string(value.player_name,value.player_name_size)=="España","copy name");
 auto second=registry.Observe(eb,"same");Require(second!=first&&registry.Deliver(second,17,"private")&&fake.Last==&b,"target isolation");
 Require(!registry.Deliver(second,18,"wrong epoch")&&!registry.Deliver(second,17,std::string("bad\0text",8))&&!registry.Deliver(second,17,"\xc0\xaf"),"bad context/text reached send");
 bool workerAccepted=true;std::thread worker([&]{workerAccepted=registry.Deliver(second,17,"worker");});worker.join();Require(!workerAccepted,"worker send");
 registry.InvalidateController(&b);auto reconnect=registry.Observe(eb,"same");Require(reconnect&&reconnect!=second&&!registry.Deliver(second,17,"stale"),"stale token revived");
 auto pending=registry.Observe(eb,"login",true);Require(pending&&!registry.Snapshot(pending,&value)&&!registry.Deliver(pending,17,"premature"),"pending login usable");
 Require(registry.Activate(pending)&&registry.Snapshot(pending,&value),"login activate");
 std::array<ObeliskChatSession,1> out{};out[0].struct_size=sizeof(out[0]);size_t written=0,total=0;
 Require(registry.List(out.data(),1,&written,&total)&&written==1&&total==2,"truncation visibility");
 fake.Alive.erase(&a);Require(!registry.Deliver(first,17,"disconnected"),"dead endpoint sent");
 registry.InvalidateToken(pending);Require(!registry.Snapshot(pending,&value),"explicit retirement");
 Fake capacity;ChatSessionRegistry full;Require(full.Configure(19,Validate,Send,&capacity),"capacity configure");
 for(uintptr_t i=1;i<=1024;++i){auto* endpoint=reinterpret_cast<void*>(i);capacity.Alive.insert(endpoint);Require(full.Observe({endpoint,&c,&d},"player"),"capacity prefill");}
 capacity.Alive.clear();capacity.Alive.insert(&a);Require(full.Observe(ea,"new")!=0,"dead endpoints exhausted registry");
 std::cout<<"Chat session registry: PASS\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
