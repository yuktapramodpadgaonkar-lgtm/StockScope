# StockScope AI

StockScope AI is a stock research platform for CMPE-258.

This repository currently contains the Market Movers slice (Person 1 scope)
with:

- FastAPI app bootstrap and CORS for the Next.js UI
- Market movers API route
- Provider abstraction for market data
- Deterministic ranking logic
- Universe files for index filtering
- Next.js + TypeScript + Tailwind **Market Movers** page (`/market-movers`)

## Isolated Python environment (recommended)

Keep dependencies inside this repo so they do not affect your system Python or other projects.

**Prerequisite:** Python 3.10+ installed and available as `python` (or `py` on Windows).

All commands below assume your **current directory is the repo root**:

`C:\Users\018464615\Downloads\Sem2\CMPE-258\Project\StockScope`

### Windows (PowerShell)

1. Create the virtual environment (once):

   ```powershell
   python -m venv .venv
   ```

2. Activate it **every time** you open a new terminal for this project:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If you see an execution policy error, run PowerShell as Administrator once:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

   Or use **Command Prompt** activation instead (see below).

3. Your prompt should show `(.venv)`. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r backend\requirements.txt
   ```

4. When you are done, you can deactivate:

   ```powershell
   deactivate
   ```

### Windows (Command Prompt)

```cmd
cd C:\Users\018464615\Downloads\Sem2\CMPE-258\Project\StockScope
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### macOS / Linux

```bash
cd /path/to/StockScope
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

The folder `.venv/` is listed in `.gitignore` and should **not** be committed.

## Quick Start (Backend)

1. Create and activate the virtual environment (see above).
2. Copy env file:

   - Windows: `copy backend\.env.example backend\.env`
   - macOS/Linux: `cp backend/.env.example backend/.env`

3. Start API (from **repo root**, with `.venv` activated):

   ```powershell
   uvicorn app.main:app --reload --app-dir backend
   ```

4. Open `http://127.0.0.1:8000/docs` for interactive API docs.

5. For browser access from the frontend, ensure `backend/.env` includes
   `CORS_ORIGINS` with `http://localhost:3000` and `http://127.0.0.1:3000`
   (see `backend/.env.example`).

## Frontend (Market Movers UI)

**Prerequisite:** [Node.js](https://nodejs.org/) 20+ (includes `npm`).

The frontend does **not** use Python or the repo’s `.venv`—only Node and `npm`.
(You can use **nvm** / **fnm** on your machine to pin a Node version; that is
separate from the backend virtual environment.)

1. From the repo root:

   ```powershell
   cd frontend
   copy .env.local.example .env.local
   npm install
   npm run dev
   ```

2. Open `http://localhost:3000` — use **Open Market Movers** or go to
   `http://localhost:3000/market-movers`.

3. Keep the FastAPI server running on `http://127.0.0.1:8000`. The UI reads
   `NEXT_PUBLIC_API_BASE_URL` from `frontend/.env.local` (default in the example
   file matches that URL).

The page includes category tabs, universe and time-mode filters, a sortable
table, refresh, row modal, and a **Run research** placeholder for your buy/sell
or chat flow.

**Market movers (API, yfinance, ranking, caching):** see
[`docs/MARKET_MOVERS.md`](docs/MARKET_MOVERS.md).

## Notes

- Market movers use **`yfinance`** as the default provider (see [`docs/MARKET_MOVERS.md`](docs/MARKET_MOVERS.md)).
- Optional API keys for other providers (Finnhub, Alpha Vantage) are placeholders for future work.
- Index universes are driven by `data/universes/*.csv`; regenerate them with
  `python scripts/fetch_universes_polygon.py` when you need updated constituents.
