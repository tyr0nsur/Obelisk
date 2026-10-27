import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Server, Lock, User, ArrowRight, AlertTriangle, Fingerprint } from 'lucide-react';

const API_BASE = '/api';

export default function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const loginRequestRef = useRef(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (loginRequestRef.current) return;
        loginRequestRef.current = true;
        setError('');
        setLoading(true);

        try {
            const res = await axios.post(`${API_BASE}/auth/login`, { username, password });
            onLogin(res.data.user || { username: res.data.username, role: res.data.role });
        } catch (err) {
            setError(err.response?.data?.error || 'Credenciales inválidas');
        } finally {
            loginRequestRef.current = false;
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#050505] flex items-center justify-center p-4 relative overflow-hidden font-sans">

            {/* Background Glow Effects */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full pointer-events-none overflow-hidden">
                <div className="absolute top-[20%] left-[20%] w-96 h-96 bg-cyan-600/20 rounded-full blur-[120px] mix-blend-screen animate-pulse duration-1000"></div>
                <div className="absolute bottom-[20%] right-[20%] w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] mix-blend-screen"></div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="w-full max-w-[420px] relative z-10"
            >
                {/* Main Card */}
                <div className="bg-[#0f0f13]/80 backdrop-blur-2xl border border-white/5 rounded-[2rem] p-8 sm:p-10 shadow-2xl shadow-cyan-900/20 relative overflow-hidden">

                    {/* Top Accent Line */}
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400 opacity-80"></div>

                    <div className="relative z-10">
                        {/* Branding / Logo */}
                        <div className="flex flex-col items-center mb-10 mt-2">
                            <motion.div
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                transition={{ delay: 0.2, type: "spring", stiffness: 200, damping: 15 }}
                                className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_30px_rgba(34,211,238,0.3)] mb-5 relative"
                            >
                                <div className="absolute inset-0 bg-white/20 rounded-2xl blur-[2px]"></div>
                                <Server size={28} className="text-[#09090b] relative z-10" />
                            </motion.div>

                            <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-1.5">
                                Obelisk<span className="text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.5)]">Native</span>
                            </h1>
                            <p className="text-[14px] text-zinc-400 mt-2 font-medium tracking-wide">
                                Terminal de Administración
                            </p>
                        </div>

                        {/* Login Form */}
                        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm font-medium"
                                >
                                    <AlertTriangle size={16} className="shrink-0" />
                                    {error}
                                </motion.div>
                            )}

	                            <div className="space-y-2 group">
	                                <label htmlFor="login-username" className="sr-only">Nombre de usuario</label>
	                                <div className="relative">
	                                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
	                                        <User size={18} className="text-zinc-500 group-focus-within:text-cyan-400 transition-colors" />
	                                    </div>
	                                    <input
	                                        id="login-username"
	                                        type="text"
                                        className="w-full bg-[#18181b]/50 border border-zinc-800 rounded-xl pl-11 pr-4 py-3.5 text-white text-[15px] outline-none transition-all placeholder:text-zinc-600 focus:border-cyan-500/50 focus:bg-[#18181b] focus:shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                                        value={username}
                                        onChange={e => setUsername(e.target.value)}
                                        placeholder="Nombre de usuario"
                                        autoComplete="username"
                                        required
                                    />
                                </div>
                            </div>

	                            <div className="space-y-2 group">
	                                <label htmlFor="login-password" className="sr-only">Contraseña de acceso</label>
	                                <div className="relative">
	                                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
	                                        <Lock size={18} className="text-zinc-500 group-focus-within:text-cyan-400 transition-colors" />
	                                    </div>
	                                    <input
	                                        id="login-password"
	                                        type="password"
                                        className="w-full bg-[#18181b]/50 border border-zinc-800 rounded-xl pl-11 pr-4 py-3.5 text-white text-[15px] outline-none transition-all placeholder:text-zinc-600 focus:border-cyan-500/50 focus:bg-[#18181b] focus:shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                                        value={password}
                                        onChange={e => setPassword(e.target.value)}
                                        placeholder="Contraseña de acceso"
                                        autoComplete="current-password"
                                        required
                                    />
                                </div>
                            </div>

                            <motion.button
                                type="submit"
                                disabled={loading}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className="mt-4 w-full bg-cyan-500 text-[#09090b] font-bold text-[15px] py-4 rounded-xl transition-all shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 relative overflow-hidden group"
                            >
                                {/* Button Hover Effect */}
                                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>

                                <span className="relative z-10 flex items-center gap-2">
                                    {loading ? (
                                        <>
                                            <div className="w-5 h-5 border-2 border-[#09090b]/30 border-t-[#09090b] rounded-full animate-spin"></div>
                                            Accediendo…
                                        </>
                                    ) : (
                                        <>
                                            Acceder al Sistema
                                            <ArrowRight size={18} />
                                        </>
                                    )}
                                </span>
                            </motion.button>
                        </form>

                        <div className="mt-8 pt-6 border-t border-zinc-800/50 flex flex-col items-center gap-2 text-center">
                            <Fingerprint size={24} className="text-zinc-600 mb-1" />
                            <p className="text-[12px] text-zinc-500 uppercase tracking-widest font-semibold">
                                Acceso Restringido
                            </p>
                            <p className="text-[11px] text-zinc-600">
                                Las conexiones son monitorizadas y registradas.
                            </p>
                        </div>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
