# Local printer agent

This process runs on the Windows/Linux computer that can reach the HP M126nw. It polls Supabase for `approved` jobs, downloads the private PDF, prints it through the computer's configured printer, and changes the job to `printed` or `failed`.

## Windows
1. Install Python 3.11+.
2. Install the HP printer driver and make sure a PDF can be printed manually.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in the Supabase URL, Supabase service/secret key, and printer name.
5. Run `python agent.py`.
6. Later, run it as a Windows startup service/task so the agent is always online.

## Linux
Install CUPS and make sure `lpstat -p` lists the HP printer. Then install the Python dependencies and run the same agent.

The service key must never be placed in the browser or committed to GitHub.
