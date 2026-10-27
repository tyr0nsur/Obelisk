import { Activity, AlertTriangle, MapPin, ShieldCheck } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext.jsx';
import { DASHBOARD_TAB_META } from '../../constants/dashboard';
import { roleInfo } from '../../constants/roles';

function statusClasses(status) {
    if (status === 'online') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300';
    if (status === 'error' || status === 'stale') return 'border-amber-500/25 bg-amber-500/10 text-amber-300';
    return 'border-red-500/25 bg-red-500/10 text-red-300';
}

export function OperationalContextBar() {
    const {
        activeTab,
        userRole,
        selectedMap,
        clusterMaps,
        liveData,
        liveDataError,
        liveDataUpdatedAt,
        liveDataStale,
        clusterMapsError,
        clusterStatusError,
    } = useDashboard();

    const meta = DASHBOARD_TAB_META[activeTab] || DASHBOARD_TAB_META.cluster;
    const currentRole = roleInfo(userRole);
    const selectedMapMeta = clusterMaps.find(map => map.id === selectedMap);
    const selectedMapName = selectedMapMeta?.name || selectedMap || 'Sin mapa';
    const status = liveDataStale ? 'stale' : (liveData?.status || 'offline');
    const statusLabel = liveDataStale ? 'Desconocido' : status === 'online' ? 'Online' : status === 'error' ? 'Degradado' : 'Offline';
    const lastLiveDataLabel = liveDataUpdatedAt ? new Date(liveDataUpdatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Sin lectura';
    const warning = clusterMapsError || liveDataError || (liveDataStale ? 'Telemetría del mapa sin actualizar; las acciones sensibles quedan bloqueadas.' : '') || clusterStatusError;

    return (
        <section
            className="mb-4 shrink-0 rounded-lg border border-zinc-800/70 bg-[#111114] px-3 py-2 shadow-sm sm:px-4 sm:py-3"
            aria-label="Contexto operacional actual"
            aria-live="polite"
        >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
                        <span>{meta.section}</span>
                        <span className="text-zinc-700">/</span>
                        <span className="text-cyan-400">{meta.label}</span>
                    </div>
                    <p className="mt-1 truncate text-sm text-zinc-300 sm:text-base">{meta.description}</p>
                </div>

                <div className="grid w-full min-w-0 grid-cols-1 gap-2 sm:grid-cols-3 lg:w-auto lg:min-w-[520px]">
                    <div className="flex min-w-0 items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
                        <MapPin size={15} className="shrink-0 text-cyan-400" />
                        <div className="min-w-0">
                            <p className="text-[10px] uppercase tracking-wide text-zinc-500">Mapa objetivo</p>
                            <p className="truncate text-xs font-semibold text-zinc-200">{selectedMapName}</p>
                        </div>
                    </div>

                    <div className={`flex min-w-0 items-center gap-2 rounded-md border px-3 py-2 ${statusClasses(status)}`}>
                        <Activity size={15} className="shrink-0" />
                        <div className="min-w-0">
                            <p className="text-[10px] uppercase tracking-wide opacity-70">Estado</p>
                            <p className="truncate text-xs font-semibold">{statusLabel}</p>
                            {liveDataStale && <p className="truncate text-[10px] opacity-70">{lastLiveDataLabel}</p>}
                        </div>
                    </div>

                    <div className="flex min-w-0 items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
                        <ShieldCheck size={15} className="shrink-0 text-indigo-300" />
                        <div className="min-w-0">
                            <p className="text-[10px] uppercase tracking-wide text-zinc-500">Permiso</p>
                            <p className="truncate text-xs font-semibold text-zinc-200">{currentRole.label}</p>
                        </div>
                    </div>
                </div>
            </div>

            {warning && (
                <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                    <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                    <span>{warning}</span>
                </div>
            )}
        </section>
    );
}
