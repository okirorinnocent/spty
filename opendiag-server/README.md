# OpenDiag Server (Vercel + Supabase)

The internet-facing part of OpenDiag. It receives hardware-health reports from agents, validates them strictly, and stores them in Supabase.

Endpoints: `POST /api/v1/reports` (bearer token), `GET /api/health`.

## Deploy in 4 steps (zero-config: Vercel auto-detects the Flask `app.py`)

**1. Supabase (database)**
- Create a project at supabase.com.
- SQL Editor -> paste `supabase_schema.sql` -> Run.
- Project Settings -> API: copy the **Project URL** and the **service_role** key.

**2. GitHub**
- Push this folder to a new GitHub repo.

**3. Vercel**
- Add New -> Project -> import the repo (root directory = this folder).
- Environment Variables:
  - `OPENDIAG_TOKEN` = a long random string (e.g. run `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
  - `SUPABASE_URL` = your Project URL
  - `SUPABASE_SERVICE_KEY` = your service_role key
- Deploy. Visit `https://YOUR-APP.vercel.app/api/health` (also `/` shows a short status line). It should return `{"status":"ok"}`.

**4. Point the agent at it** (on the employee PC, `%LOCALAPPDATA%\OpenDiag\policy.json`)
```json
"reporting_enabled": true,
"endpoint": "https://YOUR-APP.vercel.app/api/v1/reports",
"allowed_hosts": ["YOUR-APP.vercel.app"],
"dev_mode": false
```
Then `python -m opendiag.main set-token` (paste the same `OPENDIAG_TOKEN`) and `python -m opendiag.main report`. Check the `reports` table in Supabase.

## Security notes
- Keep the `service_role` key only in Vercel env vars. It bypasses row-level security.
- The table has RLS enabled with no policies, so the public/anon key cannot read it.
- Agent retries are safe: duplicates are ignored by a unique constraint.
- Rotate `OPENDIAG_TOKEN` by changing it in Vercel and re-running `set-token` on agents.

## Local test
```
pip install -r requirements.txt
python -m unittest discover -s tests
```
