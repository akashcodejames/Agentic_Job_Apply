import { useState, useEffect, useCallback, useRef } from 'react'
import { Bot, Layers, Zap, Square } from 'lucide-react'
import ChatPanel from './components/ChatPanel.jsx'
import ProfilePanel from './components/ProfilePanel.jsx'
import { fetchProfile, startApply, stopApply, getApplyStatus } from './api/client.js'

const SESSION_ID = 'default'

export default function App() {
    const [profile, setProfile] = useState(null)
    const [profileUpdatedAt, setProfileUpdatedAt] = useState('')
    const [profileFlash, setProfileFlash] = useState(false)
    const [error, setError] = useState(null)

    // Auto-apply state
    const [applyStatus, setApplyStatus] = useState('idle')   // 'idle' | 'running'
    const [applyPid, setApplyPid] = useState(null)
    const [applyBusy, setApplyBusy] = useState(false)
    const pollRef = useRef(null)

    const loadProfile = useCallback(async () => {
        try {
            const data = await fetchProfile()
            setProfile(data.profile)
            setProfileUpdatedAt(data.updated_at)
        } catch (e) {
            setError('Cannot reach backend. Is the FastAPI server running on port 8000?')
        }
    }, [])

    useEffect(() => { loadProfile() }, [loadProfile])

    // Poll apply status every 5 s while running
    const pollStatus = useCallback(async () => {
        try {
            const s = await getApplyStatus()
            setApplyStatus(s.status)
            setApplyPid(s.pid)
            if (s.status === 'idle' && pollRef.current) {
                clearInterval(pollRef.current)
                pollRef.current = null
            }
        } catch { /* ignore network blips */ }
    }, [])

    useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

    const handleApplyToggle = async () => {
        setApplyBusy(true)
        try {
            if (applyStatus === 'running') {
                await stopApply()
                setApplyStatus('idle')
                setApplyPid(null)
                if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
            } else {
                const res = await startApply()
                if (res.status === 'running') {
                    setApplyStatus('running')
                    setApplyPid(res.pid)
                    pollRef.current = setInterval(pollStatus, 5000)
                } else {
                    setError(res.message || 'Failed to start auto apply')
                }
            }
        } catch (e) {
            setError('Auto apply error: ' + e.message)
        } finally {
            setApplyBusy(false)
        }
    }

    const onProfileUpdated = (updatedProfile) => {
        setProfile(updatedProfile)
        setProfileFlash(true)
        setTimeout(() => setProfileFlash(false), 3000)
        loadProfile()
    }

    const isRunning = applyStatus === 'running'

    return (
        <div style={{
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--bg)',
            overflow: 'hidden',
        }}>
            {/* ── Header ── */}
            <header style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 24px',
                borderBottom: '1px solid var(--border)',
                background: 'rgba(255,255,255,0.02)',
                flexShrink: 0,
            }}>
                <div style={{
                    width: 34, height: 34, borderRadius: 9,
                    background: 'var(--grad)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                }}>
                    <Layers size={16} color="#fff" />
                </div>
                <div>
                    <h1 style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-.3px' }}>
                        Profile Intelligence Portal
                    </h1>
                    <p style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
                        AI-powered profile editor · LinkedIn Easy Apply
                    </p>
                </div>

                {/* Auto Apply Button */}
                <button
                    onClick={handleApplyToggle}
                    disabled={applyBusy}
                    style={{
                        marginLeft: 'auto',
                        display: 'flex', alignItems: 'center', gap: 7,
                        padding: '7px 16px',
                        borderRadius: 22,
                        border: `1px solid ${isRunning ? 'rgba(239,68,68,.5)' : 'rgba(124,58,237,.5)'}`,
                        background: isRunning
                            ? 'rgba(239,68,68,.12)'
                            : 'rgba(124,58,237,.15)',
                        color: isRunning ? '#f87171' : '#a78bfa',
                        fontSize: 12.5, fontWeight: 600,
                        cursor: applyBusy ? 'wait' : 'pointer',
                        transition: 'all .2s',
                        outline: 'none',
                    }}
                    onMouseEnter={e => { if (!applyBusy) e.currentTarget.style.opacity = '.8' }}
                    onMouseLeave={e => e.currentTarget.style.opacity = '1'}
                >
                    {isRunning ? (
                        <>
                            <span style={{
                                width: 7, height: 7, borderRadius: '50%',
                                background: '#ef4444',
                                animation: 'pulse 1.2s ease-in-out infinite',
                                flexShrink: 0,
                            }} />
                            <Square size={12} />
                            Stop Auto Apply
                            {applyPid && <span style={{ opacity: .5, fontSize: 10 }}>pid:{applyPid}</span>}
                        </>
                    ) : (
                        <>
                            <Zap size={13} />
                            {applyBusy ? 'Starting…' : 'Start Auto Apply'}
                        </>
                    )}
                </button>

                {/* Profile updated flash */}
                {profileFlash && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        background: 'rgba(16,185,129,.15)',
                        border: '1px solid rgba(16,185,129,.3)',
                        borderRadius: 20, padding: '4px 12px',
                        fontSize: 12, color: '#10b981',
                        animation: 'fadeIn .3s ease',
                    }}>
                        <span>●</span> Profile updated
                    </div>
                )}

                {error && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        background: 'rgba(239,68,68,.12)',
                        border: '1px solid rgba(239,68,68,.3)',
                        borderRadius: 20, padding: '4px 12px',
                        fontSize: 12, color: '#ef4444',
                        maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                    }}
                        onClick={() => setError(null)} title="Click to dismiss"
                    >
                        ⚠ {error}
                    </div>
                )}
            </header>

            {/* ── Main two-panel layout ── */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '380px 1fr',
                flex: 1,
                overflow: 'hidden',
                gap: '1px',
                background: 'var(--border)',
            }}>
                <ProfilePanel
                    profile={profile}
                    updatedAt={profileUpdatedAt}
                    onProfileChange={(p) => setProfile(p)}
                />
                <ChatPanel
                    sessionId={SESSION_ID}
                    onProfileUpdated={onProfileUpdated}
                />
            </div>

            <style>{`
        @keyframes fadeIn { from { opacity:0; transform:translateY(-4px) } to { opacity:1; transform:translateY(0) } }
        @keyframes spin   { to { transform: rotate(360deg) } }
        @keyframes pulse  { 0%,100%{opacity:.4} 50%{opacity:1} }
      `}</style>
        </div>
    )
}


