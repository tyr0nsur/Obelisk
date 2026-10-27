import { useState } from 'react';
import { motion } from 'framer-motion';
import { MonitorCog, HardDrive, Globe, ChevronRight, Activity, Users, Layers, AlertTriangle, RefreshCw, Power } from 'lucide-react';
import { ResourceLegend, ResourceTrendChart } from '../components/charts/ResourceTrendChart.jsx';
import { useDashboard } from '../context/DashboardContext.jsx';

export function ClusterOverview() {
  const {
    clusterStatus,
    clusterStatusError,
    setSelectedMap,
    setActiveTab,
    setChartData,
    setSettingsLoaded,
    chartData,
    userRole,
    fetchClusterStatus
  } = useDashboard();
  const canOperate = ['operator', 'owner'].includes(userRole);
  const [clusterRetrying, setClusterRetrying] = useState(false);
  const retryClusterStatus = async () => {
    if (clusterRetrying) return;
    setClusterRetrying(true);
    try {
      await fetchClusterStatus();
    } finally {
      setClusterRetrying(false);
    }
  };

  const maps = clusterStatus.maps || [];

  // Calculate Global Metrics
  let totalPlayers = 0;
  let maxPlayers = 0;
  let onlineServers = 0;
  let totalProcessCpu = 0;
  let totalProcessRam = 0;

  maps.forEach(m => {
      totalPlayers += m.players || 0;
      maxPlayers += m.maxPlayers || 0;
      if (m.status === 'online') onlineServers++;
      totalProcessCpu += m.cpu || 0;
      totalProcessRam += m.ram || 0;
  });

  const avgProcessCpu = maps.length > 0 ? (totalProcessCpu / maps.length).toFixed(1) : 0;
  const avgProcessRam = maps.length > 0 ? (totalProcessRam / maps.length).toFixed(1) : 0;
  const hasManagedMaps = maps.length > 0;
  const clusterHealthStatus = !hasManagedMaps ? 'Sin mapas' : onlineServers === maps.length ? '100% Operativo' : onlineServers === 0 ? 'Fuera de Línea' : 'Degradado';
  const clusterHealthColor = !hasManagedMaps ? 'text-zinc-400 border-zinc-700/50 bg-zinc-800/20' : onlineServers === maps.length ? 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' : onlineServers === 0 ? 'text-red-400 border-red-500/30 bg-red-500/10' : 'text-amber-400 border-amber-500/30 bg-amber-500/10';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto flex h-full min-h-0 w-full max-w-6xl flex-col gap-3 overflow-hidden"
    >
      <div className="shrink-0 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 bg-[#121214] border border-zinc-800/80 px-4 py-2.5 rounded-xl shadow-sm relative overflow-hidden">
          {/* Decorative glow */}
          <div className="absolute -top-16 -right-16 w-32 h-32 bg-indigo-500/10 rounded-full blur-[60px] pointer-events-none"></div>
          <div className="relative z-10 flex items-center gap-3">
            <Layers className="text-indigo-400 shrink-0" size={20} />
            <div>
              <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white leading-none">
                  Cluster Command Center
              </h2>
              <p className="text-[11px] text-zinc-400 mt-1">Telemetría global y control maestro del ecosistema ARK.</p>
            </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 flex flex-col gap-3 overflow-y-auto pr-1 pb-2 custom-scrollbar">
      {clusterStatusError && (
        <div className="flex flex-col gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-start gap-2">
            <AlertTriangle size={14} className="shrink-0 text-amber-300" />
            <span className="min-w-0 break-words font-medium">Error de telemetría: {clusterStatusError}</span>
          </div>
          <button type="button" onClick={retryClusterStatus} disabled={clusterRetrying} className="inline-flex min-h-7 shrink-0 items-center justify-center gap-1.5 rounded-md bg-amber-500/20 border border-amber-500/30 px-3 text-[10px] font-bold text-amber-300 transition-colors hover:bg-amber-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-50" aria-label="Reintentar telemetría">
            <RefreshCw size={12} className={clusterRetrying ? 'animate-spin' : ''} />
            {clusterRetrying ? 'Reintentando...' : 'Reintentar'}
          </button>
        </div>
      )}

      {/* Compact Global Ribbon */}
      <div className={`grid grid-cols-2 gap-3 ${canOperate ? 'md:grid-cols-4' : 'md:grid-cols-2'}`}>

          <div className="flex flex-col justify-center gap-1 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 shadow-sm backdrop-blur-md relative overflow-hidden group">
              <div className="absolute -top-6 -right-6 w-20 h-20 bg-indigo-500/10 rounded-full blur-[30px] pointer-events-none transition-opacity group-hover:opacity-100 opacity-50"></div>
              <div className="flex items-center gap-1.5 relative z-10">
                  <div className="w-5 h-5 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30 shrink-0">
                      <Users className="text-indigo-400" size={10} />
                  </div>
                  <p className="text-[9px] text-indigo-200/70 uppercase tracking-widest font-bold">Global Players</p>
              </div>
              <p className="truncate text-xl font-black text-white sm:text-2xl relative z-10 ml-0.5 mt-0.5 leading-none">{totalPlayers} <span className="text-xs text-indigo-400/60 font-semibold">/ {maxPlayers}</span></p>
          </div>

          {canOperate && (
          <div className="flex flex-col justify-center gap-1 rounded-xl border border-purple-500/20 bg-purple-500/5 p-3 shadow-sm backdrop-blur-md relative overflow-hidden group">
              <div className="absolute -top-6 -right-6 w-20 h-20 bg-purple-500/10 rounded-full blur-[30px] pointer-events-none transition-opacity group-hover:opacity-100 opacity-50"></div>
              <div className="flex items-center gap-1.5 relative z-10">
                  <div className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center border border-purple-500/30 shrink-0">
                      <MonitorCog className="text-purple-400" size={10} />
                  </div>
                  <p className="text-[9px] text-purple-200/70 uppercase tracking-widest font-bold">CPU Instancias</p>
              </div>
              <p className="truncate text-xl font-black text-white sm:text-2xl relative z-10 ml-0.5 mt-0.5 leading-none">{avgProcessCpu}<span className="text-xs text-purple-400/60 font-medium ml-0.5">%</span></p>
          </div>
          )}

          {canOperate && (
          <div className="flex flex-col justify-center gap-1 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 shadow-sm backdrop-blur-md relative overflow-hidden group">
              <div className="absolute -top-6 -right-6 w-20 h-20 bg-amber-500/10 rounded-full blur-[30px] pointer-events-none transition-opacity group-hover:opacity-100 opacity-50"></div>
              <div className="flex items-center gap-1.5 relative z-10">
                  <div className="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center border border-amber-500/30 shrink-0">
                      <HardDrive className="text-amber-400" size={10} />
                  </div>
                  <p className="text-[9px] text-amber-200/70 uppercase tracking-widest font-bold">RAM Instancias</p>
              </div>
              <p className="truncate text-xl font-black text-white sm:text-2xl relative z-10 ml-0.5 mt-0.5 leading-none">{avgProcessRam}<span className="text-xs text-amber-400/60 font-medium ml-0.5">%</span></p>
          </div>
          )}

          <div className={`flex flex-col justify-center gap-1 rounded-xl border p-3 shadow-sm backdrop-blur-md relative overflow-hidden group ${clusterHealthColor.replace('bg-', 'bg-').replace('/10', '/5').replace('/20', '/10')}`}>
              <div className="absolute -top-6 -right-6 w-20 h-20 bg-current opacity-10 rounded-full blur-[30px] pointer-events-none transition-opacity group-hover:opacity-20"></div>
              <p className="text-[9px] uppercase tracking-widest font-bold opacity-80 mb-0.5 relative z-10">Estado del Clúster</p>
              <div className="flex items-center gap-1.5 relative z-10">
                  <Activity size={18} className={onlineServers > 0 ? "animate-pulse" : ""} />
                  <p className="truncate text-sm font-black uppercase tracking-wide sm:text-base leading-none">{clusterHealthStatus}</p>
              </div>
          </div>
      </div>

      {/* Map Cards Compact Grid */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {!hasManagedMaps && (
              <div className="lg:col-span-2 rounded-xl border border-zinc-800/80 bg-[#121214] p-8 text-center text-zinc-500 shadow-sm flex flex-col items-center justify-center min-h-[150px]">
                  <Globe size={32} className="mx-auto mb-2 opacity-20" />
                  <p className="text-base font-bold text-zinc-300">No hay mapas gestionados</p>
              </div>
          )}
          {maps.map(map => {
          const isOnline = map.status === 'online';
          return (
              <motion.div
                  key={map.id}
                  whileHover={{ y: -2 }}
                  className={`dashboard-card group relative flex flex-col overflow-hidden rounded-xl border bg-[#121214] p-3.5 shadow-sm transition-all duration-300 ${
                  isOnline ? 'border-cyan-500/20 hover:border-cyan-400/40 hover:shadow-[0_0_20px_rgba(34,211,238,0.05)]' : 'border-zinc-800/80 hover:border-zinc-700/80'
              }`}>
                  {/* Subtle Background Glow for online cards */}
                  {isOnline && <div className="absolute -top-16 -right-16 w-32 h-32 bg-cyan-500/10 rounded-full blur-[40px] pointer-events-none"></div>}

                  <div className="relative z-10 mb-3 flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center border backdrop-blur-md shrink-0 shadow-inner ${
                              isOnline ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                          }`}>
                              {isOnline ? <Globe size={20} className="drop-shadow-md" /> : <Power size={20} />}
                          </div>
                          <div className="min-w-0 flex-1">
                              <h3 className="truncate text-base font-bold tracking-tight text-white leading-tight" title={map.serverName || map.name}>{map.serverName || map.name}</h3>
                              <div className="flex items-center gap-2 mt-1 flex-wrap">
                                  <div className="flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-[#09090b] border border-zinc-800/80">
                                      <div className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(34,211,238,0.8)]' : 'bg-red-500'}`}></div>
                                      <span className={`text-[9px] font-black uppercase tracking-wider ${isOnline ? 'text-cyan-400' : 'text-red-500'}`}>{map.status}</span>
                                  </div>
                                  <span className="text-[10px] text-zinc-500 font-medium px-1.5 py-0.5 rounded bg-zinc-800/30 border border-zinc-800/50" title="Instancia de configuración">{map.name}</span>
                              </div>
                          </div>
                      </div>
                      <div className="text-right shrink-0 bg-[#09090b] border border-zinc-800/80 rounded-lg px-3 py-1.5 flex flex-col items-center justify-center">
                          <p className="text-xl font-black text-white leading-none tracking-tighter">{map.players}</p>
                          <p className="text-[8px] text-zinc-500 uppercase font-bold tracking-widest mt-0.5">Jugadores</p>
                      </div>
                  </div>

                  {canOperate && <div className="relative z-10 mb-3 grid grid-cols-2 gap-3">
                      <div className="bg-[#09090b]/80 border border-zinc-800/80 rounded-lg px-3 py-1.5 flex justify-between items-center shadow-inner">
                          <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-bold">CPU Proc.</span>
                          <span className="text-sm font-bold text-purple-400">{(map.cpu || 0).toFixed(1)}%</span>
                      </div>
                      <div className="bg-[#09090b]/80 border border-zinc-800/80 rounded-lg px-3 py-1.5 flex justify-between items-center shadow-inner">
                          <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-bold">RAM Proc.</span>
                          <span className="text-sm font-bold text-amber-400">{(map.ram || 0).toFixed(1)}%</span>
                      </div>
                  </div>}

                  <button
                      onClick={() => { setSelectedMap(map.id); setActiveTab('dashboard'); setChartData([]); setSettingsLoaded(false); }}
                      className={`relative z-10 mt-auto flex w-full items-center justify-center gap-1.5 rounded-lg border py-1.5 text-[11px] font-black uppercase tracking-wide transition-all shadow-sm ${
                          isOnline
                            ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500 hover:text-cyan-950 hover:shadow-[0_0_15px_rgba(34,211,238,0.2)]'
                            : 'bg-zinc-800/50 text-zinc-300 border-zinc-700/50 hover:bg-zinc-700 hover:text-white'
                      }`}
                  >
                      Gestionar Instancia <ChevronRight size={14} strokeWidth={2.5} />
                  </button>
              </motion.div>
          );
      })}
      </div>

      {/* Flexible Area Chart */}
      {canOperate && <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#121214] p-3 shadow-sm flex flex-col flex-1 min-h-0">
          <div className="relative z-10 mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between shrink-0">
              <div className="flex items-center gap-2">
                  <Activity className="text-indigo-400" size={16} />
                  <div>
                      <h3 className="text-sm font-bold text-white leading-none">Tendencias de instancia</h3>
                      <p className="text-[10px] text-zinc-500 mt-0.5">Consumo histórico del proceso del mapa activo</p>
                  </div>
              </div>
              <div className="bg-[#09090b] border border-zinc-800/80 rounded-md px-2 py-1 transform scale-90 origin-right">
                  <ResourceLegend />
              </div>
          </div>
          <div className="relative z-10 flex-1 min-h-[160px] w-full mt-1">
              <ResourceTrendChart data={chartData} mode="area" gradientId="cluster-resource-trend" />
          </div>
      </div>}
      </div>
    </motion.div>
  );
}
