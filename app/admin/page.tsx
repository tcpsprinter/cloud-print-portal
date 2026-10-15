'use client'

import { useEffect, useState } from 'react'

type Job = {
  id: string
  user_name: string
  file_name: string
  copies: number
  status: string
  failure_reason?: string | null
  created_at: string
}

export default function Admin() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [pw, setPw] = useState('')
  const [logged, setLogged] = useState(false)
  const [error, setError] = useState('')
  const [passkey, setPasskey] = useState('')
  const [passkeySaving, setPasskeySaving] = useState(false)
  const [passkeyMessage, setPasskeyMessage] = useState('')

  async function loadPasskey() {
    const p = sessionStorage.getItem('admin_password') || ''
    const r = await fetch('/api/admin/passkey', { headers: { 'x-admin-password': p }, cache: 'no-store' })
    const j = await r.json()
    if (r.status === 401) { setLogged(false); sessionStorage.removeItem('admin_password'); setError('Invalid administrator password.'); return }
    if (!r.ok) throw new Error(j.error || 'Unable to load passkey.')
    setPasskey(j.passkey || '')
  }

  async function load() {
    const p = sessionStorage.getItem('admin_password') || ''
    const r = await fetch('/api/admin/jobs', { headers: { 'x-admin-password': p }, cache: 'no-store' })
    const j = await r.json()
    if (r.status === 401) { setLogged(false); sessionStorage.removeItem('admin_password'); setError('Invalid administrator password.') }
    else if (!r.ok) setError(j.error)
    else { setLogged(true); setJobs(j.jobs); await loadPasskey() }
  }

  async function login(e: React.FormEvent) { e.preventDefault(); setError(''); sessionStorage.setItem('admin_password', pw); await load() }

  async function savePasskey() {
    setError(''); setPasskeyMessage(''); setPasskeySaving(true)
    try {
      const p = sessionStorage.getItem('admin_password') || ''
      const r = await fetch('/api/admin/passkey', { method: 'PATCH', headers: { 'content-type': 'application/json', 'x-admin-password': p }, body: JSON.stringify({ passkey }) })
      const j = await r.json()
      if (r.status === 401) { setLogged(false); sessionStorage.removeItem('admin_password'); throw new Error('Administrator session expired.') }
      if (!r.ok) throw new Error(j.error || 'Unable to save passkey.')
      setPasskeyMessage('Shared print passkey updated. Users should use this code when submitting new print requests.')
    } catch (e: any) { setError(e.message || 'Unable to save passkey.') }
    finally { setPasskeySaving(false) }
  }

  async function copyPasskey() {
    try { await navigator.clipboard.writeText(passkey); setPasskeyMessage('Shared print passkey copied. You can now share it with users.') }
    catch { setPasskeyMessage('Select and copy the shared print passkey manually.') }
  }

  async function decide(id: string, status: 'approved' | 'rejected') {
    const p = sessionStorage.getItem('admin_password') || ''
    const r = await fetch('/api/admin/jobs', { method: 'PATCH', headers: { 'content-type': 'application/json', 'x-admin-password': p }, body: JSON.stringify({ id, status }) })
    if (!r.ok) { const j = await r.json(); setError(j.error || 'Update failed') }
    await load()
  }

  useEffect(() => { if (sessionStorage.getItem('admin_password')) load() }, [])

  if (!logged) return <main className="wrap"><section className="card"><h1>Administrator login</h1><p>Enter the administrator password.</p><form onSubmit={login}><div className="field"><label>Administrator password</label><input type="password" value={pw} onChange={e=>setPw(e.target.value)} autoComplete="current-password" /></div><button className="button">Sign in</button></form>{error&&<div className="notice">{error}</div>}<div className="admin-link"><a href="/">Back to upload</a></div></section></main>

  return <main className="wrap"><section className="card wide">
    <div className="admin-head"><div><h1>Administrator dashboard</h1><p>Review incoming print requests and manage the one shared print passkey.</p></div><button className="button" onClick={load}>Refresh</button></div>
    {error&&<div className="notice">{error}</div>}
    <div className="passkey-panel"><div><h2>Shared print passkey</h2><p className="small">This is the single passkey users enter to submit a print request. It is not the 4-digit tracking PIN generated after submission.</p></div><div className="passkey-row"><input value={passkey} onChange={e=>setPasskey(e.target.value)} placeholder="Enter one shared print passkey" maxLength={128} autoComplete="off" /><button className="button" onClick={savePasskey} disabled={passkeySaving||passkey.trim().length<4}>{passkeySaving?'Saving…':'Save passkey'}</button><button className="button secondary" onClick={copyPasskey} disabled={!passkey}>Copy</button></div>{passkeyMessage&&<div className="success small">{passkeyMessage}</div>}</div>
    <div className="table-wrap"><table><thead><tr><th>Name</th><th>PDF</th><th>Copies</th><th>Time</th><th>Status</th><th>Action</th></tr></thead><tbody>{jobs.map(j=><tr key={j.id}><td>{j.user_name}</td><td>{j.file_name}</td><td>{j.copies}</td><td>{new Date(j.created_at).toLocaleString()}</td><td>{j.status}{j.failure_reason&&<div className="small">Reason: {j.failure_reason}</div>}</td><td>{j.status==='pending'?<span className="actions"><button onClick={()=>decide(j.id,'approved')}>Approve</button><button onClick={()=>decide(j.id,'rejected')}>Reject</button></span>:<span>—</span>}</td></tr>)}{!jobs.length&&<tr><td colSpan={6}>No print requests yet.</td></tr>}</tbody></table></div>
    <div className="admin-link"><a href="/">Back to upload</a></div>
  </section></main>
}
