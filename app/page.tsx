'use client'

import { useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!)
const MAX_FILE_SIZE = 10 * 1024 * 1024
const SUPPORTED_EXTENSIONS = new Set([
  'pdf', 'doc', 'docx', 'odt', 'rtf', 'txt',
  'xls', 'xlsx', 'ods', 'csv', 'ppt', 'pptx', 'odp',
  'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tif', 'tiff', 'webp',
])

export default function Home() {
  const [name,setName]=useState(''); const [copies,setCopies]=useState('1'); const [file,setFile]=useState<File|null>(null); const [passkey,setPasskey]=useState('')
  const [busy,setBusy]=useState(false); const [result,setResult]=useState<{id:string;pin:string;expires_at:string}|null>(null); const [error,setError]=useState('')
  const [statusPin,setStatusPin]=useState(''); const [status,setStatus]=useState<any>(null); const [checking,setChecking]=useState(false)
  async function submit(e:React.FormEvent){ e.preventDefault(); setError(''); setResult(null); if(!name.trim())return setError('Please enter your name.'); if(!file)return setError('Please choose a file to print.');
    const extension=file.name.split('.').pop()?.toLowerCase()||'';
    if(!SUPPORTED_EXTENSIONS.has(extension))return setError('Unsupported file type. Upload PDF, Word, Excel, PowerPoint, OpenDocument, CSV, TXT, or a JPG/PNG/BMP/GIF/TIFF/WEBP image.');
    if(file.size>MAX_FILE_SIZE)return setError('File must be 10 MB or smaller.'); if(!passkey.trim())return setError('Please enter the current shared print passkey.'); setBusy(true)
    try { const path=`public/${crypto.randomUUID()}-${file.name.replace(/[^a-zA-Z0-9._-]/g,'_')}`; const upload=await supabase.storage.from('print-files').upload(path,file,{contentType:file.type||'application/octet-stream',upsert:false}); if(upload.error)throw upload.error; const {data,error}=await supabase.rpc('create_print_job',{p_user_name:name.trim(),p_file_name:file.name,p_file_path:path,p_copies:Number(copies),p_admin_pin:passkey.trim()}); if(error)throw error; setResult(data); setFile(null); setPasskey('') } catch(err:any){setError(err?.message||'Unable to submit the print job.')} finally{setBusy(false)} }
  async function checkStatus(e:React.FormEvent){e.preventDefault();setChecking(true);setStatus(null);setError('');try{const r=await fetch('/api/print/status',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pin:statusPin})});const j=await r.json();if(!r.ok)throw new Error(j.error);setStatus(j.job)}catch(e:any){setError(e.message)}finally{setChecking(false)}}
  return <main className="wrap"><section className="card">
    <h1>Cloud Print Portal</h1><p>Upload a document or image and send it to the office printer using the shared print passkey.</p>
    {result?<div className="success"><h2>Print request accepted</h2><p>Your request was accepted using the shared print passkey and has been queued for the printer.</p><div className="pin">{result.pin}</div><p className="small"><strong>This is your tracking PIN.</strong> Keep it to check this request's status. It is not the shared print passkey.</p><button className="button" onClick={()=>setResult(null)}>Submit another document</button></div>:<form onSubmit={submit}><div className="field"><label>Your name</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Enter your name" maxLength={80}/></div><div className="field"><label>Document or image</label><input type="file" accept=".pdf,.doc,.docx,.odt,.rtf,.txt,.xls,.xlsx,.ods,.csv,.ppt,.pptx,.odp,.jpg,.jpeg,.png,.bmp,.gif,.tif,.tiff,.webp" onChange={e=>setFile(e.target.files?.[0]||null)}/><p className="small">PDF, Word, Excel, PowerPoint, OpenDocument, CSV, TXT, JPG, PNG, BMP, GIF, TIFF, and WEBP. Maximum 10 MB per file. Office files require LibreOffice on the printer computer.</p></div><div className="field"><label>Copies</label><select value={copies} onChange={e=>setCopies(e.target.value)}>{Array.from({length:10},(_,i)=><option key={i+1} value={i+1}>{i+1}</option>)}</select></div><div className="field"><label>Shared print passkey</label><input type="password" value={passkey} onChange={e=>setPasskey(e.target.value)} placeholder="Passkey shared by the administrator" autoComplete="off" maxLength={128}/><p className="small">Enter the current passkey provided by the administrator. A correct passkey automatically authorizes this print request; no separate approval is required.</p></div><button className="button" disabled={busy}>{busy?'Submitting…':'Submit print request'}</button></form>}
    {error&&<div className="notice">{error}</div>}
    <div className="tracker"><h2>Track a print request</h2><p className="small">Use the 4-digit tracking PIN you received after submitting. This is separate from the shared print passkey.</p><form onSubmit={checkStatus}><div className="field"><label>Tracking PIN</label><input inputMode="numeric" maxLength={4} value={statusPin} onChange={e=>setStatusPin(e.target.value.replace(/\D/g,'').slice(0,4))} placeholder="0000"/></div><button className="button" disabled={checking}>{checking?'Checking…':'Check status'}</button></form>{status&&<div className="status"><strong>{status.file_name}</strong><span>{status.status.toUpperCase()}</span><small>{status.user_name} · {status.copies} {status.copies===1?'copy':'copies'}</small></div>}</div>
    <div className="admin-link"><a href="/admin">Administrator dashboard</a></div>
  </section></main>
}
