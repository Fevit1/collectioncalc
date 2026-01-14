# CollectionCalc Budget & Hosting Strategy

**Priority Order: Cheap > Good > Fast**

## Cost Summary

| Component | Free Tier | Paid (When Ready) |
|-----------|-----------|-------------------|
| **Hosting** | $0/mo | $7-20/mo |
| **Database** | $0/mo | $0-15/mo |
| **API (Anthropic)** | Pay-per-use | Pay-per-use |
| **Domain** | Already owned | ~$12/yr |
| **Documentation** | $0/mo | $0/mo |
| **Total MVP** | **~$0-3/mo** | **~$20-50/mo** |

---

## Phase 1: Free/Nearly Free (Current)

### Frontend Hosting: GitHub Pages or Cloudflare Pages
**Cost: $0**

```
collectioncalc.com → Cloudflare Pages → Static React App
```

**Why Cloudflare Pages:**
- Free SSL
- Free custom domain
- Unlimited bandwidth
- Global CDN
- Auto-deploys from GitHub

**Setup:**
1. Push frontend to GitHub repo
2. Connect to Cloudflare Pages
3. Point collectioncalc.com DNS to Cloudflare

### Backend Hosting: PythonAnywhere or Render
**Cost: $0 (free tier) or $7/mo (basic)**

| Platform | Free Tier | Paid | Notes |
|----------|-----------|------|-------|
| **PythonAnywhere** | 1 web app, limited CPU | $5/mo | Great for Python, always-on |
| **Render** | 750 hrs/mo, sleeps | $7/mo | Modern, auto-deploy |
| **Railway** | $5 credit/mo | Pay-as-go | Simple, good DX |
| **Fly.io** | 3 shared VMs | Pay-as-go | Fast deploys |

**Recommendation: Start with Render free tier**
- Sleeps after 15min inactivity (fine for demo)
- Auto-wakes on request (~30 sec cold start)
- Upgrade to $7/mo when you need always-on

### Database: SQLite (Keep It!)
**Cost: $0**

SQLite is perfect for this stage:
- No hosting costs
- No connection limits
- Backs up with simple file copy
- Fast for our scale (10K comics is tiny)

**When to switch to Postgres:**
- Multiple concurrent users (>50 simultaneous)
- Need replication/backups
- Exceeding ~100K records

### Documentation: GitHub + Mermaid
**Cost: $0**

GitHub renders Mermaid diagrams natively!
- Architecture diagrams in markdown
- Database schemas in markdown
- Auto-updates when you push
- No separate hosting needed

**Structure:**
```
github.com/yourusername/collectioncalc/
├── docs/
│   ├── ARCHITECTURE.md  ← Mermaid diagrams render here!
│   ├── DATABASE.md
│   └── API.md
├── README.md
└── ...
```

### API Costs (Anthropic)
**Cost: Variable, ~$0.01-0.05 per comic**

| Operation | Tokens | Cost |
|-----------|--------|------|
| Photo extraction | ~2K | ~$0.006 |
| Web search valuation | ~8K | ~$0.024 |
| **Per comic (DB hit)** | 0 | **$0.00** |
| **Per comic (web fallback)** | ~10K | ~$0.03 |

**With database: 600 comics ≈ $3-6**
**Without database: 600 comics ≈ $18**

---

## Phase 2: Low-Cost Production (~$15-25/mo)

When you have users and need reliability:

### Upgrade Path

| Component | Free → Paid |
|-----------|-------------|
| Backend | Render $0 → Render $7/mo |
| Database | SQLite → Turso $0 (free tier) or Supabase $0 |
| Monitoring | None → BetterStack free tier |
| Analytics | None → Plausible $9/mo or Umami (self-host free) |

### Recommended Stack

```
User → Cloudflare (free)
         ↓
    React App (Cloudflare Pages, free)
         ↓
    API (Render, $7/mo)
         ↓
    SQLite (bundled, $0)
         ↓
    Anthropic API (pay-per-use)
```

**Monthly cost: ~$7 + API usage**

---

## Phase 3: Scale (~$50-100/mo)

When you have paying customers:

| Component | Option | Cost |
|-----------|--------|------|
| Backend | Render Pro or Railway | $20-25/mo |
| Database | Supabase Pro or PlanetScale | $25/mo |
| CDN | Cloudflare Pro | $20/mo |
| Monitoring | BetterStack | $24/mo |
| Email | Resend | $20/mo |

But **don't think about this yet!**

---

## Free Tools We're Using

| Tool | Purpose | Cost |
|------|---------|------|
| GitHub | Code hosting, docs, diagrams | Free |
| Mermaid | Architecture diagrams | Free |
| Cloudflare | DNS, CDN, Pages | Free |
| SQLite | Database | Free |
| Let's Encrypt | SSL (via Cloudflare) | Free |
| VS Code | Development | Free |

---

## Hosting Setup Guide

### 1. GitHub Repository

```bash
# Create repo
gh repo create collectioncalc --public

# Push code
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 2. Cloudflare Pages (Frontend)

1. Go to dash.cloudflare.com → Pages
2. Connect GitHub repo
3. Build settings:
   - Build command: (none for static)
   - Output directory: `/`
4. Add custom domain: collectioncalc.com

### 3. Render (Backend)

1. Go to render.com
2. New → Web Service
3. Connect GitHub repo
4. Settings:
   ```
   Runtime: Python 3
   Build: pip install -r requirements.txt
   Start: python api_server_v3.py
   ```
5. Environment variables:
   ```
   ANTHROPIC_API_KEY=sk-...
   PORT=8000
   ```

### 4. DNS Setup (Cloudflare)

```
collectioncalc.com     → Cloudflare Pages (frontend)
api.collectioncalc.com → Render (backend)
```

---

## Budget Tracking

### Current Spend

| Item | Date | Amount |
|------|------|--------|
| Domain (collectioncalc.com) | 2024 | ~$12/yr |
| Anthropic API testing | Jan 2024 | $2.85 |
| **Total to date** | | **~$15** |

### Projected Monthly (Phase 1)

| Item | Cost |
|------|------|
| Hosting | $0 |
| Database | $0 |
| API (est. 100 valuations) | $3 |
| **Total** | **~$3/mo** |

---

## Cost Optimization Tips

### 1. Maximize Database Hits
Every DB hit = $0. Every web search = $0.03.
- Build comprehensive database
- Use fuzzy matching to find close matches
- Only fallback to web for true unknowns

### 2. Cache Web Search Results
When you do hit the API, save the result:
```python
# After web search, save to DB for next time
save_to_database(title, issue, nm_value)
```

### 3. Batch Operations
API calls have overhead. Batch when possible.

### 4. Use Haiku for Simple Tasks
```
Sonnet: $0.003/1K input, $0.015/1K output
Haiku:  $0.00025/1K input, $0.00125/1K output (12x cheaper!)
```

Use Haiku for:
- Simple extractions
- Validation tasks
- Non-critical operations

Use Sonnet for:
- Photo analysis
- Complex valuations
- Web search synthesis

---

## When to Spend Money

### Spend when you have:
- Real users (not just you)
- Revenue potential
- Time constraints (your time > hosting cost)

### Don't spend on:
- Features no one asked for
- Scaling before you need it
- Fancy tools with free alternatives

---

## Monetization Path

### Free Tier
- 25 comics/month
- Basic valuation
- No export

### Pro ($9/mo)
- Unlimited comics
- Excel export
- Personal adjustments
- Priority support

### Dealer ($29/mo)
- API access
- Bulk operations
- White-label options

**Break-even: ~3-5 Pro subscribers covers hosting**

---

## Summary

| Phase | Monthly Cost | Trigger |
|-------|--------------|---------|
| **MVP (Now)** | ~$0-3 | Personal project |
| **Beta** | ~$7-15 | First 10 users |
| **Production** | ~$25-50 | First paying customer |
| **Scale** | ~$100+ | 100+ active users |

**Current priority: Ship the MVP for ~$0, prove value, then invest.**
