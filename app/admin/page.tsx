'use client'

import { useEffect, useState } from 'react'

type Job = { id:string; user_name:string; file_name:string; copies:number; status:string; created_at:string; expires_at:string|null }

export default function Admin() {
  const [jobs,setJobs]=useState<Job[]>([])
  const [error,setError]=useState('')
  async function load(){ const r=await fetch('/api/admin/jobs',{cache:'no-store'}); const j=await r.json(); if(!r.ok) setError(j.error); else setJobs(j.jobs) }
  async function decide(id:string,status:'approved'|'rejected'){ const r=await fetch('/api/admin/jobs',{method:'PATCH',headers:{'content-type':'application/json'},body:JSON.stringify({id,status})}); if(!r.ok){const j=await r.json();setError(j.error||'Update failed')} await load() }
  useEffect(()=>{load(); const t=setInterval(load,5000); return()=>clearInterval(t)},[])
  return <main className="wrap"><section className="card wide"><div className="admin-head"><div><h1>Administrator dashboard</h1><p>Review incoming print requests.</p></div><button className="button" onClick={load}>Refresh</button></div>{error&&<div className="notice">{error}</div>}<div className="table-wrap"><table><thead><tr><th>Name</th><th>PDF</th><th>Copies</th><th>Time</th><th>Status</th><th>Action</th></tr></thead><tbody>{jobs.map(j=><tr key={j.id}><td>{j.user_name}</td><td>{j.file_name}</td><td>{j.copies}</td><td>{new Date(j.created_at).toLocaleString()}</td><td>{j.status}</td><td>{j.status==='pending'?<span className="actions"><button onClick={()=>decide(j.id,'approved')}>Approve</button><button onClick={()=>decide(j.id,'rejected')}>Reject</button></span>:<span>—</span>}</td></tr>)}{jobs.length===0&&<tr><td colSpan={6}>No print requests yet.</td></tr>}</tbody></table></div><div className="admin-link"><a href="/">Back to upload</a></div></section></main>
}
