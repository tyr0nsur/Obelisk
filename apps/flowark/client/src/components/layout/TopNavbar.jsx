import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Users, Server, Menu, Key, ShieldCheck, LogOut, ChevronDown } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext.jsx';
import { ADMIN_PASSWORD_MAX_BYTES, adminPasswordValidationMessage, isValidAdminPassword } from '../../constants/adminValidation';
import { PLAYER_PANEL_DESKTOP_TABS, canAccessDashboardTab, dashboardNavSectionsForRole } from '../../constants/dashboard';
import { roleInfo } from '../../constants/roles';


export function TopNavbar() {
    const { activeTab, setActiveTab, user, userRole, handleLogout, logoutPending, mobileNavOpen, setMobileNavOpen, mobilePlayersOpen, setMobilePlayersOpen, addToast } = useDashboard();
    const [profileOpen, setProfileOpen] = useState(false);
    const [openNavSection, setOpenNavSection] = useState(null);
    const [passwordOpen, setPasswordOpen] = useState(false);
    const [passwordForm, setPasswordForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
    const [passwordSaving, setPasswordSaving] = useState(false);
    const passwordSavingRef = useRef(false);
    const dropdownRef = useRef(null);
    const systemDropdownRef = useRef(null);
    const canOperate = ['operator', 'owner'].includes(userRole);
    const canOwn = userRole === 'owner';
    const currentRole = roleInfo(userRole);
    const navSections = dashboardNavSectionsForRole(userRole);
    const activeNavSectionId = navSections.find(section => section.items.some(item => item.id === activeTab))?.id;
    const currentTab = canAccessDashboardTab(activeTab, userRole) ? activeTab : 'cluster';
    const playersDockedOnCurrentTab = PLAYER_PANEL_DESKTOP_TABS.has(currentTab);
    const passwordValidationMessage = adminPasswordValidationMessage(passwordForm.newPassword);
    const passwordMismatch = passwordForm.confirmPassword && passwordForm.newPassword !== passwordForm.confirmPassword;
    const passwordValid = passwordForm.currentPassword &&
        isValidAdminPassword(passwordForm.newPassword) &&
        passwordForm.newPassword === passwordForm.confirmPassword;

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setProfileOpen(false);
                setPasswordOpen(false);
            }
            if (systemDropdownRef.current && !systemDropdownRef.current.contains(event.target)) {
                setOpenNavSection(null);
            }
        }
        function handleEscape(event) {
            if (event.key === 'Escape') {
                setProfileOpen(false);
                setPasswordOpen(false);
                setOpenNavSection(null);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
        };
    }, []);

    const closeNavigationOverlays = () => {
        setProfileOpen(false);
        setPasswordOpen(false);
        setOpenNavSection(null);
        setMobileNavOpen(false);
        setMobilePlayersOpen(false);
    };

    const navigateTopTab = tab => {
        setActiveTab(tab);
        closeNavigationOverlays();
    };

    const handlePasswordChange = async event => {
        event.preventDefault();
        if (!passwordValid || passwordSavingRef.current) return;
        passwordSavingRef.current = true;
        setPasswordSaving(true);
        try {
            const res = await axios.post('/api/auth/password', {
                currentPassword: passwordForm.currentPassword,
                newPassword: passwordForm.newPassword,
            });
            setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
            setPasswordOpen(false);
            setProfileOpen(false);
            addToast(res.data?.message || 'Contraseña actualizada', 'success');
        } catch (err) {
            addToast(err.response?.data?.error || 'No se pudo cambiar la contraseña', 'error');
        } finally {
            passwordSavingRef.current = false;
            setPasswordSaving(false);
        }
    };

    return (
        <header className="w-full h-14 bg-[#18181b] border-b border-zinc-800 flex items-center justify-between px-4 sm:px-6 shrink-0 z-[80]">
            {/* Logo area */}
            <div className="flex items-center gap-3">
                {/* Mobile Menu Button */}
		                <button
		                    onClick={() => { setMobilePlayersOpen(false); setMobileNavOpen(!mobileNavOpen); }}
		                    className="xl:hidden flex h-11 w-11 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
	                    aria-label={mobileNavOpen ? 'Cerrar navegación de servidor' : 'Abrir navegación de servidor'}
	                    aria-controls="server-navigation-drawer"
	                    aria-expanded={mobileNavOpen}
	                >
                    <Menu size={20} />
                </button>

                <div className="hidden sm:flex w-8 h-8 rounded-lg bg-cyan-500 items-center justify-center shadow-sm">
                    <Server size={16} className="text-[#09090b]" />
                </div>
                <div>
                    <h1 className="font-bold text-[16px] tracking-tight text-white leading-none flex items-center gap-1.5">
                        Obelisk<span className="text-cyan-400">Native</span> <span className="hidden sm:inline text-xs text-zinc-500 font-normal ml-1">Panel</span>
                    </h1>
                </div>
            </div>

            {/* Main Navigation */}
            <nav ref={systemDropdownRef} className="hidden xl:flex items-center justify-center h-full ml-8 flex-1 whitespace-nowrap">
                {navSections.map(section => {
                    const isOpen = openNavSection === section.id;
                    const isActive = activeNavSectionId === section.id;
                    return (
                        <div
                            key={section.id}
                            className="relative h-full flex items-center"
                            onMouseEnter={() => setOpenNavSection(section.id)}
                            onMouseLeave={() => setOpenNavSection(null)}
                            onFocus={() => setOpenNavSection(section.id)}
                            onBlur={event => {
                                if (!event.currentTarget.contains(event.relatedTarget)) {
                                    setOpenNavSection(null);
                                }
                            }}
                        >
                            <button
                                type="button"
                                onClick={() => setOpenNavSection(current => current === section.id ? null : section.id)}
                                aria-haspopup="menu"
                                aria-expanded={isOpen}
                                aria-controls={`top-nav-section-${section.id}`}
                                className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors flex items-center gap-1 ${isActive ? 'border-cyan-500 text-white bg-zinc-800/30' : 'border-transparent text-zinc-400 hover:text-white hover:bg-zinc-800/30'}`}
                            >
                                {section.shortLabel}
                                <ChevronDown size={14} className={`opacity-50 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                            </button>
                            <div
                                id={`top-nav-section-${section.id}`}
                                role="menu"
                                aria-label={section.label}
                                className={`absolute left-0 top-full z-50 ${isOpen ? 'flex' : 'hidden'} max-h-[calc(100dvh-4rem)] w-72 flex-col overflow-hidden rounded-b-lg border border-zinc-800 bg-[#18181b] shadow-xl`}
                            >
                                <div className="border-b border-zinc-800 bg-[#09090b] px-4 py-3">
                                    <p className="text-xs font-semibold text-zinc-200">{section.label}</p>
                                    <p className="mt-0.5 whitespace-normal text-[11px] leading-snug text-zinc-500">{section.description}</p>
                                </div>
                                <div className="min-h-0 overflow-y-auto custom-scrollbar">
                                {section.items.map(item => {
                                    const Icon = item.Icon;
                                    const itemActive = activeTab === item.id;
                                    return (
                                        <button
                                            key={item.id}
                                            role="menuitem"
                                            aria-current={itemActive ? 'page' : undefined}
                                            onClick={() => navigateTopTab(item.id)}
                                            className={`flex min-h-11 w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm transition-colors ${itemActive ? 'bg-cyan-500/[0.08] text-cyan-300' : 'text-zinc-300 hover:bg-zinc-800 hover:text-white'}`}
                                        >
                                            <Icon size={14} className="shrink-0 text-zinc-500" />
                                            <span className="min-w-0">
                                                <span className="block truncate">{item.label}</span>
                                                <span className="block truncate text-[10px] text-zinc-500">{item.description}</span>
                                            </span>
                                        </button>
                                    );
                                })}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </nav>

            {/* User Area */}
	            <div className="flex items-center gap-2 relative sm:gap-3" ref={dropdownRef}>
                {canOperate && (
                    <button
                        onClick={() => { setMobileNavOpen(false); setMobilePlayersOpen(!mobilePlayersOpen); }}
	                        className={`flex h-11 w-11 items-center justify-center rounded-lg text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors relative ${playersDockedOnCurrentTab ? '2xl:hidden' : ''}`}
                        title="Jugadores"
                        aria-label={mobilePlayersOpen ? 'Cerrar panel de jugadores' : 'Abrir panel de jugadores'}
                        aria-controls="players-navigation-drawer"
                        aria-expanded={mobilePlayersOpen}
                    >
                        <Users size={18} />
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-cyan-500 rounded-full border border-[#18181b]"></span>
                    </button>
                )}

	                <button
	                    onClick={handleLogout}
	                    disabled={logoutPending}
		                    className="flex h-11 w-11 items-center justify-center rounded-lg text-zinc-400 hover:bg-red-500/10 hover:text-red-300 transition-colors disabled:cursor-not-allowed disabled:opacity-45"
	                    title="Cerrar Sesión"
	                    aria-label="Cerrar Sesión"
	                >
                    <LogOut size={18} />
                </button>

                {/* Profile Dropdown Trigger */}
                <button
                    onClick={() => {
                        setOpenNavSection(null);
                        setProfileOpen(!profileOpen);
                    }}
	                    className="flex min-h-11 items-center gap-1.5 rounded-lg border border-transparent p-1.5 transition-colors hover:border-zinc-700 hover:bg-zinc-800/50 sm:gap-3 group"
                    aria-label="Abrir perfil"
                    aria-haspopup="menu"
                    aria-expanded={profileOpen}
                >
                    <div className="hidden sm:block text-right">
                        <div className="text-sm font-semibold text-white leading-none">{user}</div>
                        <div className="text-[10px] text-cyan-500 mt-1 uppercase tracking-wider" title={`Permiso verificado: ${currentRole.description}`}>{currentRole.label}</div>
                    </div>
                    <div className="w-9 h-9 rounded-full bg-zinc-800 flex items-center justify-center border border-zinc-700 group-hover:border-cyan-500/50 transition-colors">
                        <Users size={16} className="text-zinc-400 group-hover:text-cyan-400 transition-colors" />
                    </div>
	                    <ChevronDown size={14} className={`hidden text-zinc-500 transition-transform sm:block ${profileOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Dropdown Menu */}
                <AnimatePresence>
                    {profileOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.95 }}
                            transition={{ duration: 0.15 }}
	                            className="absolute right-0 top-full z-50 mt-2 max-h-[calc(100dvh-4rem)] w-[min(22rem,calc(100vw-1rem))] origin-top-right overflow-y-auto rounded-lg border border-zinc-800 bg-[#18181b] shadow-2xl shadow-black/50 custom-scrollbar"
                        >
                            <div className="p-3 border-b border-zinc-800 bg-[#09090b]">
                                <p className="text-xs text-zinc-500 font-medium">Sesión Iniciada como</p>
                                <p className="text-sm text-white font-bold truncate mt-0.5">{user}</p>
                                <p className="text-[10px] text-cyan-500 uppercase tracking-wider mt-1">{currentRole.label}</p>
                                <p className="mt-1 text-[11px] leading-snug text-zinc-500">{currentRole.description}</p>
                            </div>
                            <div className="p-1.5 flex flex-col gap-0.5">
                                <button
                                    onClick={() => setPasswordOpen(!passwordOpen)}
                                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                                >
                                    <Key size={15} className="text-purple-400" /> Cambiar Contraseña
                                </button>
	                                {passwordOpen && (
	                                    <form onSubmit={handlePasswordChange} className="px-2 pb-2 pt-1 flex flex-col gap-2">
	                                        <label htmlFor="profile-current-password" className="sr-only">Contraseña actual</label>
	                                        <input
	                                            id="profile-current-password"
	                                            type="password"
                                            value={passwordForm.currentPassword}
                                            onChange={e => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
	                                            placeholder="Contraseña actual"
	                                            className="bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-purple-500"
	                                            autoComplete="current-password"
	                                            maxLength={72}
	                                            disabled={passwordSaving}
	                                        />
	                                        <label htmlFor="profile-new-password" className="sr-only">Nueva contraseña</label>
	                                        <input
	                                            id="profile-new-password"
	                                            type="password"
                                            value={passwordForm.newPassword}
                                            onChange={e => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
	                                            placeholder="Nueva contraseña (12-72)"
	                                            maxLength={72}
		                                            title={`Contraseña de al menos 12 caracteres y ${ADMIN_PASSWORD_MAX_BYTES} bytes o menos`}
		                                            disabled={passwordSaving}
		                                            className="bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-purple-500"
		                                            autoComplete="new-password"
		                                            aria-describedby={passwordValidationMessage ? 'profile-new-password-help' : undefined}
		                                        />
		                                        {passwordValidationMessage && (
		                                            <p id="profile-new-password-help" className="px-1 text-[11px] text-amber-300">{passwordValidationMessage}</p>
		                                        )}
		                                        <label htmlFor="profile-confirm-password" className="sr-only">Confirmar nueva contraseña</label>
		                                        <input
	                                            id="profile-confirm-password"
	                                            type="password"
                                            value={passwordForm.confirmPassword}
                                            onChange={e => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
	                                            placeholder="Confirmar nueva"
	                                            maxLength={72}
	                                            disabled={passwordSaving}
	                                            className="bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-purple-500"
		                                            autoComplete="new-password"
		                                            aria-describedby={passwordMismatch ? 'profile-confirm-password-help' : undefined}
		                                        />
		                                        {passwordMismatch && (
		                                            <p id="profile-confirm-password-help" className="px-1 text-[11px] text-amber-300">Las contraseñas no coinciden.</p>
		                                        )}
	                                        <button
                                            type="submit"
                                            disabled={!passwordValid || passwordSaving}
                                            className="w-full rounded-lg bg-purple-500 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-purple-400 disabled:opacity-40 disabled:cursor-not-allowed"
                                        >
                                            {passwordSaving ? 'Guardando...' : 'Actualizar contraseña'}
                                        </button>
                                    </form>
                                )}
                                {canOwn && <button onClick={() => navigateTopTab('global_settings')} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-zinc-300 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors">
                                    <ShieldCheck size={15} className="text-emerald-400" /> Seguridad del Panel
                                </button>}
                            </div>
                            <div className="p-1.5 border-t border-zinc-800">
	                                <button
	                                    onClick={handleLogout}
	                                    disabled={logoutPending}
	                                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-45"
	                                >
                                    <LogOut size={15} /> Cerrar Sesión
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </header>
    );
}
