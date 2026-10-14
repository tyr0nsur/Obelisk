#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cstring>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <string_view>
namespace {
ObeliskApi api{};uint64_t owner=0;std::array<uint64_t,4> handles{};
struct Saved {ObeliskCommandWorldInfo Pose;};
struct SessionHomes {uint64_t Epoch=0;std::map<std::string,Saved> Points;std::chrono::steady_clock::time_point NextTravel;};
std::map<uint64_t,SessionHomes> homes;
unsigned quota=3,cooldown=30;
constexpr const char* defaults=R"({"enabled":false,"allow_all_instances":false,"instance_allowlist":[],"max_homes":3,"cooldown_seconds":30})";
void Reply(const ObeliskCommandInvocation& e,std::string_view text){api.ReplyToCommandWithOwnerToken(owner,e.invocation_token,{text.data(),text.size()});}
std::string Fold(std::string_view v){std::string s(v);for(char& c:s)if(c>='A'&&c<='Z')c+=32;return s;}
bool Name(std::string_view s){if(s.empty()||s.size()>32)return false;for(char c:s)if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'||c=='-'))return false;return true;}
void Handle(const ObeliskCommandInvocation* e,void*)noexcept{
try{
 if(!e||e->abi_version!=1||e->struct_size<sizeof(*e)||!e->command_text.data||!e->command_text.size)return;
 std::string_view line(e->command_text.data,e->command_text.size);auto split=line.find_first_of(" \t");auto command=Fold(line.substr(0,split));
 auto arg=split==line.npos?std::string_view{}:line.substr(split);while(!arg.empty()&&(arg.front()==' '||arg.front()=='\t'))arg.remove_prefix(1);while(!arg.empty()&&(arg.back()==' '||arg.back()=='\t'))arg.remove_suffix(1);
 ObeliskChatSession session{};session.struct_size=sizeof(session);
 if(!api.GetCommandChatSessionWithOwnerToken(owner,e->invocation_token,&session)||!session.session_token){Reply(*e,"La sesión ya no está disponible.");return;}
 if(command=="/homes"){
   if(!arg.empty()){Reply(*e,"Uso: /homes. Los puntos duran esta sesión.");return;}
   auto found=homes.find(session.session_token);
   if(found==homes.end()||found->second.Epoch!=session.process_epoch||found->second.Points.empty()){Reply(*e,"Sin puntos de esta sesión. Usa /sethome nombre.");return;}
   std::string text="Puntos de esta sesión:";for(const auto& point:found->second.Points){text+=' ';text+=point.first;}
   Reply(*e,text);return;
 }
 if(!Name(arg)){Reply(*e,"Usa un nombre con letras minúsculas, números, _ o -. Máximo 32 caracteres.");return;}
 if(command=="/delhome"){
   auto found=homes.find(session.session_token);bool erased=found!=homes.end()&&found->second.Epoch==session.process_epoch&&found->second.Points.erase(std::string(arg));
   Reply(*e,erased?"Punto eliminado.":"No existe ese punto en esta sesión.");return;
 }
 if(command=="/sethome"){
   ObeliskCommandWorldInfo pose{};pose.struct_size=sizeof(pose);
   if(!api.GetCommandWorldInfoWithOwnerToken(owner,e->invocation_token,&pose)||!(pose.flags&OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE)||pose.session_token!=session.session_token||pose.process_epoch!=session.process_epoch||pose.abi_version!=1||!std::isfinite(pose.x)||!std::isfinite(pose.y)||!std::isfinite(pose.z)){Reply(*e,"Tu posición no está disponible ahora.");return;}
   if(homes.size()>=1024&&!homes.count(session.session_token)){Reply(*e,"No se pueden guardar más puntos ahora.");return;}
   auto& entry=homes[session.session_token];if(entry.Epoch!=session.process_epoch){entry={};entry.Epoch=session.process_epoch;}
   if(entry.Points.size()>=quota&&!entry.Points.count(std::string(arg))){Reply(*e,"Has alcanzado el límite de puntos de esta sesión.");return;}
   entry.Points[std::string(arg)]={pose};Reply(*e,"Punto guardado para esta sesión; se pierde al reconectar o recargar el plugin.");return;
 }
 if(command!="/home")return;
 auto found=homes.find(session.session_token);if(found==homes.end()||found->second.Epoch!=session.process_epoch||!found->second.Points.count(std::string(arg))){Reply(*e,"No existe ese punto en esta sesión.");return;}
 const auto now=std::chrono::steady_clock::now();if(now<found->second.NextTravel){Reply(*e,"Espera antes de volver a usar /home.");return;}
 if(!(api.capabilities&OBELISK_API_CAPABILITY_COMMAND_SELF_TELEPORT)||!api.TeleportCommandOriginWithOwnerToken){Reply(*e,"El desplazamiento está desactivado en este servidor.");return;}
 const auto pose=found->second.Points.at(std::string(arg)).Pose;
 if(api.TeleportCommandOriginWithOwnerToken(owner,e->invocation_token,&pose)){
   found->second.NextTravel=now+std::chrono::seconds(cooldown);
   ObeliskCommandWorldInfo after{};after.struct_size=sizeof(after);
   if(api.GetCommandWorldInfoWithOwnerToken(owner,e->invocation_token,&after)&&(after.flags&OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE)&&
       after.session_token==pose.session_token&&after.process_epoch==pose.process_epoch&&
       std::abs(after.x-pose.x)<=200&&std::abs(after.y-pose.y)<=200&&std::abs(after.z-pose.z)<=200)
       Reply(*e,"Posición confirmada cerca del punto de esta sesión.");
   else Reply(*e,"Desplazamiento pendiente de confirmar. Espera antes de reintentarlo.");
 }else Reply(*e,"No se pudo aceptar el desplazamiento. Debes estar despierto, vivo y sin montura.");
}catch(...){}
}
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out){if(!out)return false;*out={1,sizeof(*out),"oHomes","ObeliskNative Session Homes","0.1.0-prototype","config.json",defaults};return true;}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* in,const ObeliskPluginInitContext* ctx){
 if(!in||!ctx||in->abi_version!=1||ctx->abi_version!=1||ctx->struct_size<sizeof(*ctx)||!ctx->plugin_owner_token||owner||in->struct_size<offsetof(ObeliskApi,capabilities)+sizeof(in->capabilities))return false;
 std::memcpy(&api,in,std::min<size_t>(sizeof(api),in->struct_size));owner=ctx->plugin_owner_token;
 try{
  if(!ctx->config_path||!ctx->instance_id)return false;std::ifstream stream(ctx->config_path,std::ios::binary);std::string bytes(8193,'\0');stream.read(bytes.data(),bytes.size());if(stream.bad()||stream.gcount()>8192)return false;bytes.resize(stream.gcount());
  bool duplicate=false;std::set<std::string> keys;auto config=nlohmann::json::parse(bytes,[&](int,nlohmann::json::parse_event_t event,nlohmann::json& parsed){if(event==nlohmann::json::parse_event_t::key&&!keys.insert(parsed.get<std::string>()).second)duplicate=true;return true;},false);
  if(duplicate||!config.is_object()||config.size()!=5||!config.contains("enabled")||!config["enabled"].is_boolean()||!config.contains("allow_all_instances")||!config["allow_all_instances"].is_boolean()||!config.contains("instance_allowlist")||!config["instance_allowlist"].is_array()||!config.contains("max_homes")||!config["max_homes"].is_number_unsigned()||!config.contains("cooldown_seconds")||!config["cooldown_seconds"].is_number_unsigned())return false;
  auto configuredQuota=config["max_homes"].get<uint64_t>();auto configuredCooldown=config["cooldown_seconds"].get<uint64_t>();if(configuredQuota<1||configuredQuota>10||configuredCooldown>3600)return false;quota=static_cast<unsigned>(configuredQuota);cooldown=static_cast<unsigned>(configuredCooldown);
  bool allowed=config["allow_all_instances"].get<bool>();for(const auto& id:config["instance_allowlist"]){if(!id.is_string())return false;allowed|=id.get<std::string>()==ctx->instance_id;}
  if(!config["enabled"].get<bool>()||!allowed)return true;
  if(api.struct_size<offsetof(ObeliskApi,GetCommandWorldInfoWithOwnerToken)+sizeof(api.GetCommandWorldInfoWithOwnerToken)||!(api.capabilities&OBELISK_API_CAPABILITY_CHAT_SESSIONS)||!(api.capabilities&OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE)||!(api.capabilities&OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS)||!(api.capabilities&OBELISK_API_CAPABILITY_COMMAND_REPLIES)||!api.RegisterCommandWithOptionsWithOwnerTokenHandle||!api.GetCommandChatSessionWithOwnerToken||!api.GetCommandWorldInfoWithOwnerToken||!api.ReplyToCommandWithOwnerToken||!api.UnregisterCommandWithOwnerToken)return false;
  constexpr const char* names[]={"/sethome","/home","/homes","/delhome"};for(size_t i=0;i<4;++i){handles[i]=api.RegisterCommandWithOptionsWithOwnerTokenHandle(owner,names[i],3,Handle,nullptr);if(!handles[i])return false;}return true;
 }catch(...){return false;}
}
extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities(){return 1;}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload(){return true;}
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown(){for(auto& h:handles){if(h&&api.UnregisterCommandWithOwnerToken)api.UnregisterCommandWithOwnerToken(owner,h);h=0;}homes.clear();owner=0;api={};}
