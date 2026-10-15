import os, platform, subprocess, tempfile, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
URL=os.environ['SUPABASE_URL'].rstrip('/')
KEY=os.environ['SUPABASE_SERVICE_KEY']
PRINTER=os.environ['PRINTER_NAME']
POLL=float(os.getenv('POLL_SECONDS','8'))
H={'apikey':KEY,'Authorization':f'Bearer {KEY}'}


def db(method,path,**kwargs):
    r=requests.request(method,f'{URL}/rest/v1/{path}',headers={**H,'Content-Type':'application/json','Prefer':'return=representation'},timeout=30,**kwargs)
    r.raise_for_status(); return r.json() if r.content else None

def signed_url(path):
    r=requests.post(f'{URL}/storage/v1/object/sign/print-files/{path.lstrip("/")}',headers=H,json={'expiresIn':300},timeout=30); r.raise_for_status(); data=r.json(); return URL+data['signedURL'] if data['signedURL'].startswith('/') else data['signedURL']

def print_pdf(pdf,copies):
    with tempfile.NamedTemporaryFile(suffix='.pdf',delete=False) as f: f.write(pdf); p=f.name
    try:
        if platform.system()=='Windows':
            # Requires the HP printer to be the configured Windows default printer.
            for _ in range(copies): os.startfile(p,'print')
        else:
            subprocess.run(['lp','-d',PRINTER,'-n',str(copies),p],check=True,timeout=60)
    finally:
        try: Path(p).unlink()
        except OSError: pass

def main():
    print(f'Printer agent online: {PRINTER}')
    while True:
        try:
            jobs=db('GET','print_jobs?select=id,file_path,copies&status=eq.approved&order=created_at.asc&limit=1') or []
            for job in jobs:
                jid=job['id']
                # Claim the job first so two agents cannot print it concurrently.
                claimed=db('PATCH',f'print_jobs?id=eq.{jid}&status=eq.approved',json={'status':'printing'})
                if not claimed: continue
                try:
                    u=signed_url(job['file_path']); pdf=requests.get(u,timeout=60); pdf.raise_for_status(); print_pdf(pdf.content,int(job.get('copies') or 1))
                    db('PATCH',f'print_jobs?id=eq.{jid}&status=eq.printing',json={'status':'printed'})
                except Exception as exc:
                    print('print failed:',exc)
                    db('PATCH',f'print_jobs?id=eq.{jid}&status=eq.printing',json={'status':'failed'})
        except Exception as exc: print('agent error:',exc)
        time.sleep(POLL)

if __name__=='__main__': main()
