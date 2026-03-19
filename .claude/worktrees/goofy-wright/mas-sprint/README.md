# MAS Job Search Sprint

Multi-Agent System for proactive job search automation. Three-tab application: Intelligence Dashboard, MUSE Outreach Generator, and COMPASS Weekly Brief.

## Architecture

```
Browser (martechb2c.com/mas)  →  Express Proxy (Render)  →  Anthropic API
         ↑ Password gate                    ↑ API key in env var only
```

## Quick Start (Local Development)

1. **Backend setup:**
   ```bash
   cd backend
   npm install
   cp .env.example .env
   # Edit .env — add your ANTHROPIC_API_KEY and MAS_PASSWORD
   node server.js
   ```

2. **Open in browser:**
   ```
   http://localhost:3001
   ```
   The Express server serves both the API proxy and frontend static files.

3. **Enter your MAS_PASSWORD at the login screen.**

## Deploy to Production

### Backend (Render)

1. Push this repo to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect the repo, set **Root Directory** to `backend`
4. Set environment variables in Render dashboard:
   - `ANTHROPIC_API_KEY` — your key from console.anthropic.com
   - `MAS_PASSWORD` — the password for the login screen
5. Deploy — the service will be available at `https://mas-proxy.onrender.com`

Or use `render.yaml` for Blueprint deployment.

### Frontend (martechb2c.com)

1. In `frontend/index.html`, set `window.MAS_API_URL` to your Render URL:
   ```js
   window.MAS_API_URL = 'https://mas-proxy.onrender.com';
   ```
2. Upload the `frontend/` directory contents to `public_html/mas/` on martechb2c.com
3. Access at `martechb2c.com/mas`

**Alternative:** Point subdomain `mas.martechb2c.com` via DNS CNAME.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (sk-ant-...) |
| `MAS_PASSWORD` | Shared password for login screen |
| `NODE_ENV` | Set to `production` for Render |
| `PORT` | Server port (default: 3001) |

## File Structure

```
mas-sprint/
├── frontend/
│   ├── index.html          ← Entry point + password gate
│   ├── App.jsx             ← Main three-tab shell
│   ├── tabs/
│   │   ├── Dashboard.jsx   ← Tab 1: Track 2 Intelligence
│   │   ├── Muse.jsx        ← Tab 2: Outreach Generator
│   │   └── Compass.jsx     ← Tab 3: Weekly Brief
│   └── data/
│       └── tier1.js        ← Target 23 company data
├── backend/
│   ├── server.js           ← Express proxy + password auth
│   ├── package.json
│   └── .env.example
├── render.yaml             ← Render deployment config
└── README.md
```

## Security Notes

- API key NEVER appears in frontend code — only in Render env var
- Password sent as `x-mas-password` header on every API call
- CORS restricted to martechb2c.com and localhost
- Model: `claude-sonnet-4-20250514` for all API calls
- COMPASS uses `web_search_20250305` tool for live signals
