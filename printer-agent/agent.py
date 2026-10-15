import os, platform, subprocess, tempfile, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
URL = os.environ['SUPABASE_URL'].rstrip('/')
KEY = os.environ['SUPABASE_SERVICE_KEY']
PRINTER = os.environ['PRINTER_NAME']
POLL = float(os.getenv('POLL_SECONDS', '8'))
PRINT_WAIT = int(os.getenv('PRINT_WAIT_SECONDS', '15'))
SUMATRA_PDF = os.getenv('SUMATRA_PDF', '').strip()
H = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}


def db(method, path, **kwargs):
    r = requests.request(
        method,
        f'{URL}/rest/v1/{path}',
        headers={**H, 'Content-Type': 'application/json', 'Prefer': 'return=representation'},
        timeout=30,
        **kwargs,
    )
    r.raise_for_status()
    return r.json() if r.content else None


def signed_url(path):
    r = requests.post(
        f'{URL}/storage/v1/object/sign/print-files/{path.lstrip("/")}',
        headers=H,
        json={'expiresIn': 300},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return URL + data['signedURL'] if data['signedURL'].startswith('/') else data['signedURL']


def find_sumatra():
    if SUMATRA_PDF and Path(SUMATRA_PDF).is_file():
        return SUMATRA_PDF
    candidates = [
        Path(os.getenv('LOCALAPPDATA', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
        Path(os.getenv('PROGRAMFILES', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
        Path(os.getenv('PROGRAMFILES(X86)', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
    ]
    return next((str(p) for p in candidates if p.is_file()), None)


def print_pdf(pdf, copies):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf)
        p = f.name

    try:
        if platform.system() == 'Windows':
            # Prefer SumatraPDF when installed: it prints directly to the named
            # printer and does not depend on a fragile PDF-app file association.
            sumatra = find_sumatra()
            if sumatra:
                subprocess.run(
                    [sumatra, '-silent', '-print-to', PRINTER, '-print-settings', f'{copies}x', p],
                    check=True,
                    timeout=120,
                )
            else:
                # Built-in fallback. This uses Windows' registered Print verb.
                ps_path = p.replace("'", "''")
                command = (
                    f"$p=Start-Process -LiteralPath '{ps_path}' -Verb Print -PassThru -Wait; "
                    f"if (-not $p) {{ exit 1 }}"
                )
                subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                    check=True,
                    timeout=120,
                )
                # Some PDF viewers hand the document to the spooler and exit
                # immediately. Give the spooler time to consume the temp file.
                time.sleep(PRINT_WAIT)
        else:
            subprocess.run(
                ['lp', '-d', PRINTER, '-n', str(copies), p],
                check=True,
                timeout=60,
            )
    finally:
        try:
            Path(p).unlink()
        except OSError:
            pass


def main():
    print(f'Printer agent online: {PRINTER}')
    if platform.system() == 'Windows' and not find_sumatra():
        print('Windows print fallback active. For most reliable printing, install SumatraPDF or set SUMATRA_PDF in .env.')

    while True:
        try:
            jobs = db(
                'GET',
                'print_jobs?select=id,file_path,copies&status=eq.approved&order=created_at.asc&limit=1',
            ) or []
            for job in jobs:
                jid = job['id']
                claimed = db(
                    'PATCH',
                    f'print_jobs?id=eq.{jid}&status=eq.approved',
                    json={'status': 'printing', 'failure_reason': None},
                )
                if not claimed:
                    continue
                try:
                    u = signed_url(job['file_path'])
                    pdf = requests.get(u, timeout=60)
                    pdf.raise_for_status()
                    print_pdf(pdf.content, int(job.get('copies') or 1))
                    db(
                        'PATCH',
                        f'print_jobs?id=eq.{jid}&status=eq.printing',
                        json={'status': 'printed', 'failure_reason': None},
                    )
                except Exception as exc:
                    reason = f'{type(exc).__name__}: {exc}'[:1000]
                    print('print failed:', reason)
                    try:
                        db(
                            'PATCH',
                            f'print_jobs?id=eq.{jid}&status=eq.printing',
                            json={'status': 'failed', 'failure_reason': reason},
                        )
                    except Exception as update_exc:
                        print('could not record print failure:', update_exc)
        except Exception as exc:
            print('agent error:', exc)
        time.sleep(POLL)


if __name__ == '__main__':
    main()
