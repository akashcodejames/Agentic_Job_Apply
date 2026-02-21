import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Trash2, Bot, User, Loader2, Brain } from 'lucide-react'
import { sendMessage, fetchHistory, clearHistory } from '../api/client.js'

const TypingDots = () => (
    <div style={{ display: 'flex', gap: 4, padding: '4px 0' }}>
        {[0, 1, 2].map(i => (
            <span key={i} style={{
                width: 7, height: 7, borderRadius: '50%',
                background: 'var(--accent)',
                display: 'inline-block',
                animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
            }} />
        ))}
    </div>
)

const Bubble = ({ role, content, createdAt }) => {
    const isUser = role === 'user'
    return (
        <div style={{
            display: 'flex',
            flexDirection: isUser ? 'row-reverse' : 'row',
            gap: 10,
            alignItems: 'flex-start',
            animation: 'fadeIn .25s ease',
        }}>
            {/* Avatar */}
            <div style={{
                width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                background: isUser ? 'var(--grad)' : 'rgba(255,255,255,0.08)',
                border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
                {isUser
                    ? <User size={14} color="#fff" />
                    : <Bot size={14} color="#7c3aed" />
                }
            </div>

            {/* Message */}
            <div style={{
                maxWidth: '78%',
                background: isUser
                    ? 'var(--grad)'
                    : 'rgba(255,255,255,0.05)',
                border: isUser ? 'none' : '1px solid var(--border)',
                borderRadius: isUser ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
                padding: '10px 14px',
                fontSize: 13.5,
                lineHeight: 1.65,
                color: isUser ? '#fff' : 'var(--text)',
            }}>
                {isUser
                    ? <p>{content}</p>
                    : <div className="md-content"><ReactMarkdown>{content}</ReactMarkdown></div>
                }
                {createdAt && (
                    <p style={{ fontSize: 10, color: isUser ? 'rgba(255,255,255,.5)' : 'var(--text-muted)', marginTop: 4 }}>
                        {new Date(createdAt + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                )}
            </div>
        </div>
    )
}

export default function ChatPanel({ sessionId, onProfileUpdated }) {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [summary, setSummary] = useState('')
    const [histLoaded, setHistLoaded] = useState(false)
    const bottomRef = useRef(null)
    const textareaRef = useRef(null)

    /* Load conversation history on mount */
    useEffect(() => {
        const load = async () => {
            try {
                const data = await fetchHistory(sessionId)
                setMessages(data.messages || [])
                setSummary(data.summary || '')
            } catch {
                // ignore — histLoaded still flips so the welcome screen shows
            } finally {
                setHistLoaded(true)
            }
        }
        load()
    }, [sessionId])

    /* Scroll to bottom on new message */
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, loading])

    const handleSend = async () => {
        const text = input.trim()
        if (!text || loading) return

        const userMsg = { role: 'user', content: text, created_at: new Date().toISOString() }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setLoading(true)

        try {
            const data = await sendMessage(text, sessionId)

            const assistantMsg = {
                role: 'assistant',
                content: data.response,
                created_at: new Date().toISOString(),
            }
            setMessages(prev => [...prev, assistantMsg])

            if (data.profile_updated) {
                onProfileUpdated(data.profile)
            }
        } catch (e) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `⚠️ **Error:** ${e.message}`,
                created_at: new Date().toISOString(),
            }])
        } finally {
            setLoading(false)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
    }

    const handleClear = async () => {
        await clearHistory(sessionId)
        setMessages([])
        setSummary('')
    }

    const SUGGESTIONS = [
        "What skills should I add to get more interviews?",
        "Update my expected CTC to 700000",
        "How can I improve my About section?",
        "Add TensorFlow and PyTorch to my skills",
    ]

    return (
        <div style={{
            display: 'flex', flexDirection: 'column',
            height: '100%', background: 'var(--bg)',
            overflow: 'hidden',
        }}>
            {/* ── Chat header ── */}
            <div style={{
                padding: '14px 20px',
                borderBottom: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                flexShrink: 0,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Brain size={16} color="#7c3aed" />
                    <span style={{ fontWeight: 600, fontSize: 14 }}>Profile Assistant</span>
                    <span style={{
                        fontSize: 10, padding: '2px 8px',
                        background: 'rgba(124,58,237,.15)',
                        color: '#a78bfa', borderRadius: 20,
                        border: '1px solid rgba(124,58,237,.25)',
                    }}>
                        ConversationSummaryBuffer
                    </span>
                </div>
                {messages.length > 0 && (
                    <button onClick={handleClear} title="Clear conversation" style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', padding: 6, borderRadius: 6,
                        display: 'flex', alignItems: 'center', gap: 4, fontSize: 12,
                        transition: 'color .2s',
                    }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                    >
                        <Trash2 size={14} /> Clear
                    </button>
                )}
            </div>

            {/* ── Compressed memory badge ── */}
            {summary && (
                <div style={{
                    margin: '10px 16px 0',
                    padding: '8px 12px',
                    background: 'rgba(124,58,237,.08)',
                    border: '1px solid rgba(124,58,237,.2)',
                    borderRadius: 8,
                    fontSize: 11, color: '#a78bfa', flexShrink: 0,
                }}>
                    <strong>📝 Conversation context compressed</strong> — older messages summarized into memory.
                </div>
            )}

            {/* ── Messages ── */}
            <div style={{
                flex: 1, overflowY: 'auto',
                padding: '16px 20px',
                display: 'flex', flexDirection: 'column', gap: 14,
            }}>
                {/* Welcome state */}
                {histLoaded && messages.length === 0 && (
                    <div style={{
                        margin: 'auto',
                        textAlign: 'center',
                        maxWidth: 380,
                    }}>
                        <div style={{
                            width: 56, height: 56, borderRadius: 16,
                            background: 'var(--grad)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            margin: '0 auto 16px',
                        }}>
                            <Bot size={26} color="#fff" />
                        </div>
                        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                            Profile Intelligence
                        </h2>
                        <p style={{ color: 'var(--text-sub)', fontSize: 13, marginBottom: 24 }}>
                            Chat with me to review or improve your LinkedIn profile.
                            I'll only update the database when you explicitly ask me to.
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {SUGGESTIONS.map(s => (
                                <button key={s} onClick={() => setInput(s)} style={{
                                    background: 'var(--surface)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 10, padding: '9px 14px',
                                    color: 'var(--text)', cursor: 'pointer',
                                    textAlign: 'left', fontSize: 12.5,
                                    transition: 'background .2s, border-color .2s',
                                }}
                                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.borderColor = 'rgba(124,58,237,.4)' }}
                                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.borderColor = 'var(--border)' }}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) => (
                    <Bubble key={i} role={m.role} content={m.content} createdAt={m.created_at} />
                ))}

                {loading && (
                    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <div style={{
                            width: 30, height: 30, borderRadius: 8,
                            background: 'rgba(255,255,255,0.08)',
                            border: '1px solid var(--border)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                            <Bot size={14} color="#7c3aed" />
                        </div>
                        <div style={{
                            background: 'rgba(255,255,255,.05)',
                            border: '1px solid var(--border)',
                            borderRadius: '4px 14px 14px 14px',
                            padding: '12px 16px',
                        }}>
                            <TypingDots />
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* ── Input ── */}
            <div style={{
                padding: '12px 16px',
                borderTop: '1px solid var(--border)',
                flexShrink: 0,
                background: 'rgba(255,255,255,0.02)',
            }}>
                <div style={{
                    display: 'flex', gap: 10, alignItems: 'flex-end',
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 12, padding: '8px 8px 8px 14px',
                    transition: 'border-color .2s',
                }}
                    onFocusCapture={e => e.currentTarget.style.borderColor = 'rgba(124,58,237,.5)'}
                    onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={e => {
                            setInput(e.target.value)
                            e.target.style.height = 'auto'
                            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                        }}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about your profile or request changes…"
                        rows={1}
                        style={{
                            flex: 1, background: 'none', border: 'none', outline: 'none',
                            color: 'var(--text)', fontSize: 13.5, resize: 'none',
                            fontFamily: 'var(--font)', lineHeight: 1.5,
                            maxHeight: 120, overflow: 'auto',
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        style={{
                            width: 36, height: 36, borderRadius: 8, border: 'none',
                            background: (input.trim() && !loading) ? 'var(--grad)' : 'rgba(255,255,255,.06)',
                            cursor: (input.trim() && !loading) ? 'pointer' : 'not-allowed',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            transition: 'background .2s', flexShrink: 0,
                        }}
                    >
                        {loading
                            ? <Loader2 size={16} color="#fff" style={{ animation: 'spin 1s linear infinite' }} />
                            : <Send size={16} color={input.trim() ? '#fff' : 'var(--text-muted)'} />
                        }
                    </button>
                </div>
                <p style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6, textAlign: 'center' }}>
                    Press <kbd style={{ background: 'rgba(255,255,255,.06)', padding: '1px 5px', borderRadius: 4 }}>Enter</kbd> to send
                    · <kbd style={{ background: 'rgba(255,255,255,.06)', padding: '1px 5px', borderRadius: 4 }}>Shift+Enter</kbd> for new line
                </p>
            </div>
        </div>
    )
}
