import os, platform, subprocess, tempfile, time
from pathlib import Path
import requests
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / '.env'
load_dotenv(ENV_FILE)


def required_env(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(
            f'Missing {name}. Create {ENV_FILE} from .env.example and fill in your Supabase/printer settings.'
        )
    return value


URL = required_env('SUPABASE_URL').rstrip('/')
KEY = required_env('SUPABASE_SERVICE_KEY')
PRINTER = required_env('PRINTER_NAME')
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


def download_pdf(path):
    """Download the private Storage object using the agent's service key."""
    clean_path = path.lstrip('/')
    r = requests.get(
        f'{URL}/storage/v1/object/print-files/{clean_path}',
        headers=H,
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def find_sumatra():
    if SUMATRA_PDF and Path(SUMATRA_PDF).is_file():
        return SUMATRA_PDF
    candidates = [
        Path(os.getenv('LOCALAPPDATA', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
        Path(os.getenv('PROGRAMFILES', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
        Path(os.getenv('PROGRAMFILES(X86)', '')) / 'SumatraPDF' / 'SumatraPDF.exe',
    ]
    return next((str(p) for p in candidates if p.is_file()), None)


def print_with_windows_shell(path):
    """Print a PDF using the Windows shell when SumatraPDF is unavailable."""
    ps_path = path.replace("'", "''")
    printer = PRINTER.replace("'", "''")
    command = f"""
$ErrorActionPreference = 'Stop'
$path = '{ps_path}'
$printer = '{printer}'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $path
$psi.UseShellExecute = $true
$verbs = @($psi.Verbs)

if ($verbs -contains 'PrintTo') {{
    $p = Start-Process -LiteralPath $path -Verb PrintTo -ArgumentList ('"' + $printer + '"') -PassThru
    if (-not $p) {{ throw 'Windows PDF handler could not start PrintTo.' }}
}} elseif ($verbs -contains 'Print') {{
    $network = New-Object -ComObject WScript.Network
    $oldDefault = (Get-CimInstance Win32_Printer | Where-Object {{ $_.Default }} | Select-Object -First 1 -ExpandProperty Name)
    try {{
        $network.SetDefaultPrinter($printer)
        $p = Start-Process -LiteralPath $path -Verb Print -PassThru
        if (-not $p) {{ throw 'Windows PDF handler could not start Print.' }}
    }} finally {{
        if ($oldDefault) {{ $network.SetDefaultPrinter($oldDefault) }}
    }}
}} else {{
    throw ('The installed PDF application does not provide Print or PrintTo. Available verbs: ' + ($verbs -join ', '))
}}
""".strip()
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', command],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or 'Windows shell printing failed').strip()
        raise RuntimeError(detail[:1000])
    time.sleep(PRINT_WAIT)


def print_pdf(pdf, copies):
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf)
        p = f.name

    try:
        if platform.system() == 'Windows':
            sumatra = find_sumatra()
            if sumatra:
                subprocess.run(
                    [sumatra, '-silent', '-print-to', PRINTER, '-print-settings', f'{copies}x', p],
                    check=True,
                    timeout=120,
                )
            else:
                if copies != 1:
                    print('Windows shell fallback does not reliably control PDF copies; install SumatraPDF for copy-count support.')
                print_with_windows_shell(p)
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
        print('Windows shell fallback active. For reliable PDF printing and copy counts, install SumatraPDF or set SUMATRA_PDF in .env.')

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
                    pdf = download_pdf(job['file_path'])
                    print_pdf(pdf, int(job.get('copies') or 1))
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
    try:
        main()
    except RuntimeError as exc:
        print(f'CONFIGURATION ERROR: {exc}')
        print(f'Expected config file: {ENV_FILE}')
        print('Copy .env.example to .env, fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, and PRINTER_NAME, then run python agent.py.')
        raise SystemExit(1)
