# CollectionCalc 📚

**AI-powered comic book collection valuation tool**

CollectionCalc uses a hybrid database + AI approach to provide fast, consistent, and accurate valuations for comic book collections.

## Features

- **Deterministic Valuations** - Same comic, same grade = same price (no AI variance)
- **Three-Tier Pricing Model** - Database → AI fallback → Manual entry
- **Grade Adjustments** - Automatic price scaling based on CGS/CGC grades
- **Key Issue Detection** - Identifies first appearances, classic covers, etc.
- **Batch Processing** - Value entire collections efficiently
- **User Feedback Loop** - Crowdsourced accuracy improvements

## Architecture

```
┌─────────────────┐
│   User Input    │
│ (comic details) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Local Database │────▶│  Found? Return  │
│   (SQLite)      │     │  cached value   │
└────────┬────────┘     └─────────────────┘
         │ Not found
         ▼
┌─────────────────┐     ┌─────────────────┐
│  AI Web Search  │────▶│  Cache result   │
│  (Anthropic)    │     │  for next time  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Valuation      │
│  Model          │
│  (deterministic)│
└─────────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/collectioncalc.git
cd collectioncalc

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database_schema import init_database; init_database()"

# Run API server
python api_server_v3.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/valuate` | POST | Value a single comic |
| `/api/batch` | POST | Value multiple comics |
| `/api/lookup` | GET | Check database for comic |
| `/api/feedback` | POST | Submit price correction |

## Example Request

```bash
curl -X POST http://localhost:5000/api/valuate \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Captain America Annual",
    "issue": "8",
    "grade": "VF",
    "publisher": "Marvel Comics",
    "year": 1986
  }'
```

Response:
```json
{
  "final_value": 36.75,
  "confidence": 85,
  "db_found": true,
  "steps": [
    "Base NM value: $50.00 (source: database)",
    "Grade adjustment (VF): $50.00 × 0.75 = $37.50",
    "Era adjustment (copper_age): $37.50 × 0.98 = $36.75"
  ]
}
```

## Cost Efficiency

| Approach | Cost per Comic | 600 Comics |
|----------|---------------|------------|
| Pure AI (web search) | ~$0.03 | ~$18 |
| **CollectionCalc (hybrid)** | ~$0.005 | **~$3** |

90% of lookups hit the local database = 85% cost savings.

## Documentation

- [Architecture Diagrams](docs/ARCHITECTURE.md)
- [Database Schema](docs/DATABASE.md)
- [Budget & Hosting](docs/BUDGET.md)
- [Roadmap](docs/ROADMAP.md)

## Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **AI**: Anthropic Claude API (fallback only)
- **Hosting**: Render (free tier) + Cloudflare Pages

## License

MIT

---

*Built as a portfolio project demonstrating AI product development, cost optimization, and practical system design.*
