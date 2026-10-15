# Local printer agent

This process runs on the Windows/Linux computer that can reach the HP M126nw. It polls Supabase for `approved` jobs, downloads the private PDF, prints it through the computer's configured printer, and changes the job to `printed` or `failed`.

## Windows
1. Install Python 3.11+.
2. Install the HP printer driver and make sure a PDF can be printed manually.
3. Open PowerShell in the `printer-agent` folder.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Create your local config by copying `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
6. Open `.env` and fill in `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `PRINTER_NAME`.
7. Run `python agent.py`.

The agent now loads `.env` from its own folder, so it works even if PowerShell is started from another directory. If configuration is missing, it shows a clear configuration error instead of a Python `KeyError`.

### Finding the printer name

Run this in PowerShell:

```powershell
Get-Printer | Select-Object Name
```

Put the exact printer name into `PRINTER_NAME` in `.env`.

### Important security note

`.env` contains the Supabase service/secret key. Never commit `.env` to GitHub or put the service/secret key in browser/frontend code. Keep `.env` local to the printer computer.

## Linux
Install CUPS and make sure `lpstat -p` lists the HP printer. Then install the Python dependencies, create `.env` from `.env.example`, fill in the settings, and run the same agent.
