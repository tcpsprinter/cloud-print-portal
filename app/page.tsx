'use client'

import { useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
const supabase = createClient(url, key)

export default function Home() {
  const [name,setName]=useState('')
  const [copies,setCopies]=useState('1')
  const [file,setFile]=useState<File|null>(null)
  const [busy,setBusy]=useState(false)
  const [result,setResult]=useState<{id:string;pin:string;expires_at:string}|null>(null)
  const [error,setError]=useState('')

  async function submit(e:React.FormEvent){
    e.preventDefault(); setError(''); setResult(null)
    if(!name.trim()){setError('Please enter your name.');return}
    if(!file || file.type!=='application/pdf'){setError('Please select a PDF file.');return}
    if(file.size>10*1024*1024){setError('PDF must be 10 MB or smaller.');return}
    setBusy(true)
    try{
      const path=`public/${crypto.randomUUID()}-${file.name.replace(/[^a-zA-Z0-9._-]/g,'_')}`
      const upload=await supabase.storage.from('print-files').upload(path,file,{contentType:'application/pdf',upsert:false})
      if(upload.error) throw upload.error
      const {data,error}=await supabase.rpc('create_print_job',{p_user_name:name.trim(),p_file_name:file.name,p_file_path:path,p_copies:Number(copies)})
      if(error) throw error
      setResult(data); setFile(null)
    }catch(err:any){setError(err?.message||'Unable to submit the print job.')}
    finally{setBusy(false)}
  }

  return <main className="wrap"><section className="card">
    <h1>Cloud Print Portal</h1><p>Upload a PDF and send it to the office printer for approval.</p>
    {result ? <div className="success"><h2>Request submitted</h2><p>Give this PIN to the administrator.</p><div className="pin">{result.pin}</div><p className="small">Your request is pending approval. Keep this PIN until printing is complete.</p><button className="button" onClick={()=>setResult(null)}>Submit another document</button></div> : <form onSubmit={submit}>
      <div className="field"><label htmlFor="name">Your name</label><input id="name" value={name} onChange={e=>setName(e.target.value)} placeholder="Enter your name" maxLength={80}/></div>
      <div className="field"><label htmlFor="file">PDF document</label><input id="file" type="file" accept="application/pdf,.pdf" onChange={e=>setFile(e.target.files?.[0]||null)}/></div>
      <div className="field"><label htmlFor="copies">Copies</label><select id="copies" value={copies} onChange={e=>setCopies(e.target.value)}>{Array.from({length:10},(_,i)=><option key={i+1} value={i+1}>{i+1}</option>)}</select></div>
      <button className="button" disabled={busy}>{busy?'Submitting…':'Submit print request'}</button>
      {error&&<div className="notice">{error}</div>}
    </form>}
    <div className="admin-link"><a href="/admin">Administrator dashboard</a></div>
  </section></main>
}