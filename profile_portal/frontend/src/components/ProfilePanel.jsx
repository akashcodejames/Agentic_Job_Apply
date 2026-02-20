import { useState } from 'react'
import {
    User, Mail, Phone, MapPin, Briefcase, GraduationCap,
    Code2, Target, DollarSign, Clock, Globe, RefreshCw, ExternalLink,
    Sparkles,
} from 'lucide-react'
import { deleteProfileKey } from '../api/client.js'

const Section = ({ icon: Icon, label, children }) => (
    <div style={{ marginBottom: 18 }}>
        <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            marginBottom: 8,
        }}>
            <Icon size={12} color="#7c3aed" />
            <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--text-muted)' }}>
                {label}
            </span>
        </div>
        {children}
    </div>
)

const Pill = ({ children, color = 'accent' }) => (
    <span style={{
        display: 'inline-flex', alignItems: 'center',
        padding: '3px 9px',
        borderRadius: 20,
        fontSize: 11.5, fontWeight: 500,
        background: color === 'accent' ? 'rgba(124,58,237,.15)' : 'rgba(255,255,255,.06)',
        color: color === 'accent' ? '#a78bfa' : 'var(--text-sub)',
        border: `1px solid ${color === 'accent' ? 'rgba(124,58,237,.25)' : 'var(--border)'}`,
        margin: '2px 3px 2px 0',
    }}>
        {children}
    </span>
)

const InfoRow = ({ label, value }) => (
    <div style={{
        display: 'grid', gridTemplateColumns: '90px 1fr',
        gap: 8, marginBottom: 6, fontSize: 12.5,
    }}>
        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span style={{ color: 'var(--text)' }}>{value || '—'}</span>
    </div>
)

// All fields explicitly rendered — everything else goes to the catch-all section
const KNOWN_KEYS = new Set([
    'name', 'email', 'phone', 'location', 'linkedin', 'github', 'portfolio',
    'education', 'experience_years', 'experience_months',
    'current_ctc', 'expected_ctc', 'notice_period',
    'work_authorization', 'relocation', 'remote',
    'target_roles', 'skills', 'about', 'projects',
])

export default function ProfilePanel({ profile, updatedAt, onProfileChange }) {
    const [refreshing, setRefreshing] = useState(false)
    const [deleting, setDeleting] = useState(null)  // key being deleted

    if (!profile) {
        return (
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100%', flexDirection: 'column', gap: 12,
                color: 'var(--text-muted)',
            }}>
                <div style={{
                    width: 32, height: 32, borderRadius: '50%',
                    border: '2px solid var(--accent)',
                    borderTopColor: 'transparent',
                    animation: 'spin 1s linear infinite',
                }} />
                <span style={{ fontSize: 12 }}>Loading profile…</span>
            </div>
        )
    }

    const handleRefresh = async () => {
        setRefreshing(true)
        try {
            const { fetchProfile } = await import('../api/client.js')
            const data = await fetchProfile()
            onProfileChange(data.profile)
        } finally {
            setTimeout(() => setRefreshing(false), 600)
        }
    }

    const formatINR = (n) => {
        if (!n) return '—'
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
    }

    // Any key the LLM added that isn't in KNOWN_KEYS gets rendered here
    const extraKeys = Object.keys(profile).filter(k => !KNOWN_KEYS.has(k))

    return (
        <div style={{
            display: 'flex', flexDirection: 'column',
            height: '100%', overflowY: 'auto',
            background: 'rgba(255,255,255,0.015)',
        }}>
            {/* Header strip */}
            <div style={{
                padding: '16px 18px 14px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--grad-subtle)',
                flexShrink: 0,
            }}>
                {/* Avatar + name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <div style={{
                        width: 46, height: 46, borderRadius: 14,
                        background: 'var(--grad)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 20, fontWeight: 700, color: '#fff', flexShrink: 0,
                    }}>
                        {(profile.name || 'U')[0]}
                    </div>
                    <div>
                        <h2 style={{ fontSize: 15, fontWeight: 700 }}>{profile.name || '—'}</h2>
                        <p style={{ fontSize: 11.5, color: 'var(--text-sub)' }}>
                            {(profile.target_roles || [])[0] || 'Developer'}
                        </p>
                    </div>
                    <button onClick={handleRefresh} title="Refresh" style={{
                        marginLeft: 'auto', background: 'none', border: 'none',
                        cursor: 'pointer', color: 'var(--text-muted)', padding: 6,
                        borderRadius: 6, display: 'flex', transition: 'color .2s',
                    }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--text)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                    >
                        <RefreshCw size={14} style={{ animation: refreshing ? 'spin .6s linear infinite' : 'none' }} />
                    </button>
                </div>

                {/* Contact quick links */}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {profile.linkedin && (
                        <a href={profile.linkedin} target="_blank" rel="noreferrer" style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            fontSize: 11, color: '#a78bfa',
                            textDecoration: 'none',
                        }}>
                            <ExternalLink size={10} /> LinkedIn
                        </a>
                    )}
                    {profile.github && (
                        <a href={profile.github} target="_blank" rel="noreferrer" style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            fontSize: 11, color: '#a78bfa',
                            textDecoration: 'none',
                        }}>
                            <ExternalLink size={10} /> GitHub
                        </a>
                    )}
                    {profile.portfolio && (
                        <a href={profile.portfolio} target="_blank" rel="noreferrer" style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            fontSize: 11, color: '#a78bfa',
                            textDecoration: 'none',
                        }}>
                            <ExternalLink size={10} /> Portfolio
                        </a>
                    )}
                </div>

                {/* Last updated */}
                {updatedAt && (
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8 }}>
                        Last updated: {new Date(updatedAt + 'Z').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </p>
                )}
            </div>

            {/* ── Body ── */}
            <div style={{ padding: '16px 18px', flex: 1 }}>

                {/* Contact */}
                <Section icon={User} label="Contact">
                    <InfoRow label="Email" value={profile.email} />
                    <InfoRow label="Phone" value={profile.phone} />
                    <InfoRow label="Location" value={profile.location} />
                </Section>

                {/* Education */}
                <Section icon={GraduationCap} label="Education">
                    <p style={{ fontSize: 12.5, color: 'var(--text-sub)', lineHeight: 1.5 }}>
                        {profile.education || '—'}
                    </p>
                </Section>

                {/* Experience */}
                <Section icon={Briefcase} label="Experience">
                    <InfoRow label="Years" value={`${profile.experience_years || 0} yr ${profile.experience_months || 0} mo`} />
                    <InfoRow label="Notice" value={profile.notice_period} />
                    <InfoRow label="Remote" value={profile.remote ? 'Open to remote' : 'On-site only'} />
                    <InfoRow label="Relocate" value={profile.relocation ? 'Open to relocation' : 'No'} />
                </Section>

                {/* Salary */}
                <Section icon={DollarSign} label="Compensation">
                    <InfoRow label="Current CTC" value={formatINR(profile.current_ctc)} />
                    <InfoRow label="Expected CTC" value={formatINR(profile.expected_ctc)} />
                </Section>

                {/* Skills */}
                <Section icon={Code2} label="Skills">
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {(profile.skills || []).map(s => <Pill key={s}>{s}</Pill>)}
                    </div>
                </Section>

                {/* Target Roles */}
                <Section icon={Target} label="Target Roles">
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {(profile.target_roles || []).map(r => <Pill key={r} color="neutral">{r}</Pill>)}
                    </div>
                </Section>

                {/* About */}
                <Section icon={Globe} label="About">
                    <p style={{ fontSize: 12, color: 'var(--text-sub)', lineHeight: 1.6 }}>
                        {profile.about || '—'}
                    </p>
                </Section>

                {/* Projects */}
                {(profile.projects || []).length > 0 && (
                    <Section icon={Code2} label="Projects">
                        {profile.projects.map((p, i) => (
                            <div key={i} style={{
                                background: 'var(--surface)', border: '1px solid var(--border)',
                                borderRadius: 10, padding: '10px 12px', marginBottom: 8,
                            }}>
                                <p style={{ fontWeight: 600, fontSize: 12.5, marginBottom: 3 }}>{p.name}</p>
                                <p style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 4, fontFamily: 'var(--mono)' }}>{p.stack}</p>
                                <p style={{ fontSize: 11.5, color: 'var(--text-sub)', lineHeight: 1.5 }}>{p.description}</p>
                            </div>
                        ))}
                    </Section>
                )}

                {/* ── Catch-all: any new keys added via chat ── */}
                {extraKeys.length > 0 && (
                    <Section icon={Sparkles} label="Additional Info">
                        {extraKeys.map(key => {
                            const val = profile[key]
                            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                            const isDeleting = deleting === key

                            const handleDelete = async () => {
                                if (!window.confirm(`Delete the "${label}" field from your profile?`)) return
                                setDeleting(key)
                                try {
                                    const data = await deleteProfileKey(key)
                                    onProfileChange(data.profile)
                                } catch (e) {
                                    alert('Failed to delete: ' + e.message)
                                } finally {
                                    setDeleting(null)
                                }
                            }

                            const DeleteBtn = () => (
                                <button
                                    onClick={handleDelete}
                                    disabled={isDeleting}
                                    title={`Delete "${label}" field`}
                                    style={{
                                        background: 'none', border: 'none', cursor: isDeleting ? 'wait' : 'pointer',
                                        color: 'var(--text-muted)', padding: '2px 4px',
                                        borderRadius: 4, fontSize: 13, lineHeight: 1,
                                        transition: 'color .15s',
                                        marginLeft: 'auto', flexShrink: 0,
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                    {isDeleting ? '…' : '×'}
                                </button>
                            )

                            // Array → pills
                            if (Array.isArray(val)) {
                                return (
                                    <div key={key} style={{ marginBottom: 10 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                                            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</p>
                                            <DeleteBtn />
                                        </div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                                            {val.map((item, i) => (
                                                <Pill key={i} color="neutral">
                                                    {typeof item === 'object' ? JSON.stringify(item) : String(item)}
                                                </Pill>
                                            ))}
                                        </div>
                                    </div>
                                )
                            }
                            // Object → JSON block
                            if (typeof val === 'object' && val !== null) {
                                return (
                                    <div key={key} style={{ marginBottom: 10 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                                            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</p>
                                            <DeleteBtn />
                                        </div>
                                        <pre style={{
                                            fontSize: 11, fontFamily: 'var(--mono)',
                                            background: 'var(--surface)', borderRadius: 6,
                                            padding: '8px 10px', overflowX: 'auto',
                                            color: 'var(--text-sub)', border: '1px solid var(--border)',
                                        }}>
                                            {JSON.stringify(val, null, 2)}
                                        </pre>
                                    </div>
                                )
                            }
                            // Primitive → row with delete
                            return (
                                <div key={key} style={{
                                    display: 'grid', gridTemplateColumns: '90px 1fr auto',
                                    gap: 8, marginBottom: 6, fontSize: 12.5, alignItems: 'center',
                                }}>
                                    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                                    <span style={{ color: 'var(--text)' }}>{String(val)}</span>
                                    <DeleteBtn />
                                </div>
                            )
                        })}
                    </Section>
                )}
            </div>
        </div>
    )
}
