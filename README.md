# CarbonCoach

**Conversational carbon footprint calculator with incentive-aware reduction advice**

[![Live app](https://img.shields.io/badge/demo-carboncoach.up.railway.app-52B788?style=for-the-badge)](https://carboncoach.up.railway.app)
[![API health](https://img.shields.io/badge/API-health_check-1B4332?style=for-the-badge)](https://carbonbackend.up.railway.app/api/health)

CarbonCoach guides people through a mobile-friendly chat to estimate annual CO₂ emissions (home, transport, consumption), then surfaces **actionable upgrades** matched to **federal and state rebate programs**—not generic “drive less” tips.

> **Design principle:** Claude runs the conversation; **Python owns the math**. Footprints and savings come from deterministic engines and curated datasets, so results stay auditable and repeatable.

---

## Why it’s interesting

| Area | What we built |
|------|----------------|
| **Hybrid AI + engineering** | Structured data collection via Claude (`claude-sonnet-4-6`); emissions from `carbon_calc.py`, not LLM guesses |
| **Real-world data** | Production PostgreSQL: **13,041** vehicle MPG rows, **680** DSIRE-style programs, grid factors for all **50** states |
| **Decision support** | Diagnostic engine (tech upgrades + program matching) and lifestyle engine (behavioral changes from calculation breakdowns) |
| **Shipped product** | Live on Railway: NGINX frontend + Gunicorn Flask API + managed Postgres ([deployment notes](RAILWAY_SETUP.md)) |
| **Accessible UX** | WCAG AA palette, session-based privacy (no accounts), dedicated recommendations UI |

**Example flow:** User in Phoenix with gas heat and no heat pump → high heating emissions → recommend heat pump → surface relevant utility rebates and federal credits with links.

---

## Try it

- **App:** https://carboncoach.up.railway.app  
- **API:** https://carbonbackend.up.railway.app  
- **Health:** `GET /api/health`

---

## How it works

```mermaid
flowchart LR
  User[User browser] --> FE[Static frontend\nHTML / CSS / JS]
  FE --> API[Flask REST API]
  API --> LLM[Claude conversation\nllm_service.py]
  API --> Calc[Carbon engine\ncarbon_calc.py]
  API --> Rec[Recommendation engines\ndiagnostic + lifestyle]
  Calc --> DB[(PostgreSQL)]
  Rec --> DB
  LLM --> API
```

1. **Conversation** — Five sections (intro → home → transport → consumption → results); progress tracked per session.  
2. **Calculation** — Bills, MPG lookup, flights, diet, and grid factors produce kg CO₂/year with line-item breakdowns.  
3. **Recommendations** — Opportunities scored and paired with DSIRE-mapped programs (rebates, tax credits, links).

---

## Tech stack

| Layer | Choices |
|-------|---------|
| Frontend | Vanilla JS, mobile-first CSS, `localStorage` sessions |
| Backend | Python 3, Flask, SQLAlchemy, Flask-Migrate |
| AI | Anthropic API (direct integration, validated JSON extraction) |
| Data | PostgreSQL (prod); SQLite bundle for local dev (`instance/carbon_calculator.db`) |
| Deploy | Railway — separate frontend (NGINX) and API (Gunicorn) services |

---

## Repository layout

```
CarbonCoach/
├── README.md                 ← you are here
├── RAILWAY_SETUP.md          ← production ops & CLI cheatsheet
└── carbon-calculator/
    ├── backend/              ← Flask API, engines, migrations
    └── frontend/             ← chat UI + recommendations page
```

---

## Quick start (local)

**Prerequisites:** Python 3.8+, [Anthropic API key](https://console.anthropic.com/)

### Fast path — SQLite (no Postgres install)

```bash
cd carbon-calculator/backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env (DATABASE_URL optional — defaults to SQLite)
python3 app.py
```

Backend: **http://localhost:5001** (default `PORT`)

```bash
# Separate terminal
cd carbon-calculator/frontend
python3 -m http.server 8000
```

For local API calls, point `carbon-calculator/frontend/session.js` at `http://localhost:5001/api` (production already uses Railway).

Open **http://localhost:8000** and walk through the chat, then open the recommendations view.

### Full path — PostgreSQL (matches production)

```bash
brew install postgresql && brew services start postgresql   # macOS example
createdb carbon_calculator
```

```env
# .env
ANTHROPIC_API_KEY=your_key
DATABASE_URL=postgresql://username:password@localhost:5432/carbon_calculator
FLASK_ENV=development
SECRET_KEY=your_secret_key
```

Populate or migrate data as needed via `data/populate_data.py` and Flask-Migrate.

---

## Features

- **Conversational onboarding** — Claude-led chat with section guardrails and progress (0–100%)
- **Transparent calculations** — Home (electricity, heating, solar), transport (MPG DB + flights), consumption (diet + shopping)
- **Incentive matching** — Federal/state programs filtered by technology and location
- **Two recommendation modes** — Technology diagnostics vs. lifestyle changes from breakdown analysis
- **Privacy-first** — UUID sessions in `localStorage`; no user accounts

---

## Database (high level)

| Tables / data | Role |
|---------------|------|
| `sessions`, `user_responses` | Conversation state |
| `carbon_calculations`, `calculation_breakdowns` | Results and audit trail |
| `vehicle_mpg` | Year/make/model efficiency lookup |
| `federal_programs`, `state_programs`, technology mappings | DSIRE-derived incentive data |
| `emission_factors`, `electricity_rates` | Regional grid and unit factors |

---

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/session/{session_id}` | Create or resume session |
| `POST` | `/api/conversation` | Chat turn + structured extraction |
| `POST` | `/api/calculate` | Run footprint calculation |
| `GET` | `/api/calculations/{session_id}` | Stored results + breakdown |
| `GET` | `/api/recommendations/{session_id}` | Diagnostic + lifestyle recs |
| `GET` | `/api/health` | Liveness check |

```bash
curl http://localhost:5001/api/health
curl -X POST http://localhost:5001/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session", "message": "I live in Phoenix, Arizona"}'
```

---

## Test scenario (Phoenix, AZ)

| Input | Value |
|-------|--------|
| Location | Phoenix, Arizona · 2 people · house |
| Home | 2000 sq ft · $150/mo electric · gas heat $80/mo · no solar |
| Transport | 2020 Honda Civic · 15,000 mi/yr · 2 domestic flights |
| Consumption | Meat eater · moderate shopping |

**Expected:** ~14–16 t CO₂/year; heat pump and solar opportunities with state/federal program references.

---

## Deployment

Production runs on **Railway** (three services: API, NGINX frontend, Postgres). See **[RAILWAY_SETUP.md](RAILWAY_SETUP.md)** for domains, env vars, and CLI workflows.

```env
ANTHROPIC_API_KEY=...
DATABASE_URL=postgresql://...
FLASK_ENV=production
SECRET_KEY=...
```

---

## Data sources

- EPA **eGRID** (electricity), **GHG emission factors**, **Fuel Economy** (vehicle MPG)
- **DSIRE**-style federal/state program imports (rebates, credits, technology tags)

---

## Extending the project

**Emission factors** — `carbon-calculator/backend/data/populate_data.py`  
**Conversation flow** — `llm_service.py` (`sections`, `section_progress`)  
**Recommendation logic** — `diagnostic_recommendations.py`, `lifestyle_recommendations.py`

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| DB errors | `DATABASE_URL`, Postgres running, or use default SQLite |
| API key | `ANTHROPIC_API_KEY` in `.env` |
| Frontend ↔ backend | Backend on **5001**; CORS enabled; `session.js` `apiBaseUrl` |
| Empty recommendations | DB populated; complete all conversation sections before calculate |

---

## Contributing

Issues and PRs welcome. Fork → branch → test the full chat → results → recommendations path → open a PR.

---

Climate tech prototype built to show **usable AI** paired with **rigorous domain logic** and **real incentive data**.
