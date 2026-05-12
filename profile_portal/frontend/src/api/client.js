const BASE = '/api'

export async function fetchProfile() {
  const res = await fetch(`${BASE}/profile`)
  if (!res.ok) throw new Error('Failed to fetch profile')
  return res.json()
}

export async function updateProfile(updates) {
  const res = await fetch(`${BASE}/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ updates }),
  })
  if (!res.ok) throw new Error('Failed to update profile')
  return res.json()
}

export async function sendMessage(message, sessionId = 'default') {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) {
    let detail = `Chat request failed (${res.status})`
    try {
      const err = await res.json()
      if (err.detail) detail = err.detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export async function fetchHistory(sessionId = 'default') {
  const res = await fetch(`${BASE}/chat/history?session_id=${sessionId}`)
  if (!res.ok) throw new Error('Failed to fetch history')
  return res.json()
}

export async function clearHistory(sessionId = 'default') {
  const res = await fetch(`${BASE}/chat/history?session_id=${sessionId}`, {
    method: 'DELETE',
  })
  return res.json()
}

export async function deleteProfileKey(keyName) {
  const res = await fetch(`${BASE}/profile/key/${encodeURIComponent(keyName)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete key: ${keyName}`)
  return res.json()
}

// ── Auto Apply ──────────────────────────────────────────────────────────────

export async function startApply() {
  const res = await fetch(`${BASE}/apply/start`, { method: 'POST' })
  if (!res.ok) {
    let detail = `Failed to start auto apply (${res.status})`
    try {
      const err = await res.json()
      if (err.detail) detail = err.detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export async function stopApply() {
  const res = await fetch(`${BASE}/apply/stop`, { method: 'POST' })
  return res.json()
}

export async function getApplyStatus() {
  const res = await fetch(`${BASE}/apply/status`)
  return res.json()
}
