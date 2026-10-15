# Local printer agent

This process runs on the Windows/Linux computer that can reach the HP M126nw. It polls Supabase for `approved` jobs, downloads the private uploaded file, converts supported formats to PDF when needed, prints through the computer's configured printer, and changes the job to `printed` or `failed`.

## Supported upload formats

The portal accepts PDF, Word (DOC/DOCX), OpenDocument text (ODT), RTF, TXT, Excel (XLS/XLSX), OpenDocument spreadsheets (ODS), CSV, PowerPoint (PPT/PPTX), OpenDocument presentations (ODP), and JPG/JPEG, PNG, BMP, GIF, TIFF, and WEBP images. The portal limits uploads to 10 MB each. Unknown extensions are rejected.

- PDFs print directly.
- Images are converted to PDF by Pillow; TXT files are converted to a simple PDF.
- Word, Excel, PowerPoint, OpenDocument, RTF, and CSV files require **LibreOffice** installed on the printer computer. The agent uses its headless conversion mode. Install LibreOffice from https://www.libreoffice.org/download/download-libreoffice/ and restart the agent after installation.
- File conversion can change page layout. For critical documents, review the PDF output before printing.

## Windows EXE (no Python required)
1. Extract the `CloudPrintAgent-Windows` ZIP to a folder you control.
2. Copy `CloudPrintAgent.env.example` and rename the copy to `.env` (make sure Windows does not append `.txt`).
3. Open `.env` in Notepad and fill in `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `PRINTER_NAME`. Use the exact Windows queue name; for this setup it is `HP LaserJet Pro MFP M126nw`.
4. Install LibreOffice if you need to print Office/OpenDocument/RTF/CSV files (PDF, images, and TXT do not require it).\n5. Save `.env` beside `CloudPrintAgent.exe`, then double-click `CloudPrintAgent.exe`. Keep its console window open while printing.

The `.env` file contains a secret key. Do not upload it or share it.

## Windows with Python
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

The Python agent loads `.env` from its source folder. The packaged EXE loads `.env` from the folder beside the EXE. If configuration is missing, it shows a clear configuration error instead of a Python `KeyError`. Dependencies in `requirements.txt` include the image and text conversion libraries.

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
