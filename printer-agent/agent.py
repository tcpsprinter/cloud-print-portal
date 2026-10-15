import os, platform, subprocess, tempfile, time, sys, shutil
from pathlib import Path
import requests
from dotenv import load_dotenv

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
ENV_FILE = APP_DIR / '.env'
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


SUPPORTED_OFFICE_EXTENSIONS = {
    '.doc', '.docx', '.odt', '.rtf',
    '.xls', '.xlsx', '.ods', '.csv',
    '.ppt', '.pptx', '.odp',
}
SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp',
}
SUPPORTED_EXTENSIONS = SUPPORTED_OFFICE_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS | {'.pdf', '.txt'}


def find_libreoffice():
    """Return a LibreOffice executable path, if installed."""
    candidates = [
        shutil.which('soffice'),
        shutil.which('soffice.exe'),
        str(Path(os.getenv('PROGRAMFILES', 'C:/Program Files')) / 'LibreOffice' / 'program' / 'soffice.exe'),
        str(Path(os.getenv('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'LibreOffice' / 'program' / 'soffice.exe'),
    ]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def convert_to_pdf(file_bytes, file_name):
    """Convert an allowed uploaded document/image to PDF bytes for the print pipeline."""
    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise RuntimeError(f'Unsupported file format: {extension or "(no extension)"}')

    if extension == '.pdf':
        return file_bytes

    with tempfile.TemporaryDirectory(prefix='cloudprint-convert-') as folder:
        workdir = Path(folder)
        source = workdir / ('input' + extension)
        source.write_bytes(file_bytes)
        output = workdir / 'input.pdf'

        if extension in SUPPORTED_IMAGE_EXTENSIONS:
            from PIL import Image, ImageOps
            with Image.open(source) as image:
                frames = []
                try:
                    while True:
                        frame = ImageOps.exif_transpose(image.copy()).convert('RGB')
                        frames.append(frame)
                        image.seek(image.tell() + 1)
                except EOFError:
                    pass
                if not frames:
                    raise RuntimeError('The uploaded image could not be read.')
                frames[0].save(output, 'PDF', save_all=True, append_images=frames[1:])
                for frame in frames:
                    frame.close()

        elif extension == '.txt':
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            page = canvas.Canvas(str(output), pagesize=A4)
            page_width, page_height = A4
            left, top, line_height = 42, page_height - 48, 14
            y = top
            text = file_bytes.decode('utf-8-sig', errors='replace')
            for raw_line in text.splitlines() or ['']:
                # Wrap long lines and replace characters unsupported by ReportLab's built-in font.
                line = raw_line.expandtabs(4)
                chunks = [line[i:i + 105] for i in range(0, max(len(line), 1), 105)]
                for chunk in chunks:
                    if y < 42:
                        page.showPage()
                        y = top
                    safe = chunk.encode('cp1252', errors='replace').decode('cp1252')
                    page.drawString(left, y, safe)
                    y -= line_height
            page.save()

        else:
            office = find_libreoffice()
            if not office:
                raise RuntimeError(
                    f'{extension} files require LibreOffice on the printer computer. '
                    'Install LibreOffice, then restart CloudPrintAgent.'
                )
            result = subprocess.run(
                [office, '--headless', '--convert-to', 'pdf', '--outdir', str(workdir), str(source)],
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0 or not output.is_file():
                detail = (result.stderr or result.stdout or 'LibreOffice did not create a PDF').strip()
                raise RuntimeError(f'Could not convert {extension} to PDF: {detail[:500]}')

        if not output.is_file():
            raise RuntimeError(f'Conversion did not create a PDF for {file_name}.')
        return output.read_bytes()


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
    $p = Start-Process -FilePath $path -Verb PrintTo -ArgumentList ('"' + $printer + '"') -PassThru
    if (-not $p) {{ throw 'Windows PDF handler could not start PrintTo.' }}
}} elseif ($verbs -contains 'Print') {{
    $network = New-Object -ComObject WScript.Network
    $oldDefault = (Get-CimInstance Win32_Printer | Where-Object {{ $_.Default }} | Select-Object -First 1 -ExpandProperty Name)
    try {{
        $network.SetDefaultPrinter($printer)
        $p = Start-Process -FilePath $path -Verb Print -PassThru
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
