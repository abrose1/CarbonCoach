# Railway Deployment Configuration

## Project Structure
- **Project**: CarbonCoach
- **Environment**: production
- **Services**: 3 total (web-service, frontend, postgres)

## Service Architecture

### 1. web-service (Flask API Backend)
- **Domain**: https://carbonbackend.up.railway.app
- **Source**: `carbon-calculator/backend/` directory
- **Runtime**: Python 3.11 + Gunicorn
- **Database**: PostgreSQL with full production data
  - 13,041 vehicle MPG records
  - 680 DSIRE government programs (6 federal + 674 state)
  - 2,899 technology mappings
  - 56 emission factors + 51 electricity rates

### 2. frontend (NGINX Static Site)
- **Domain**: https://frontend-production-ab38.up.railway.app
- **Source**: `site/` directory (NGINX container)
- **Runtime**: NGINX Alpine serving static HTML/CSS/JS
- **API Calls**: Points to carbonbackend.up.railway.app backend

### 3. postgres (Database)
- **Internal**: postgres.railway.internal:5432
- **Public**: postgres-production-faa4.up.railway.app
- **Database**: railway

## Working CLI Commands

### Project Management
```bash
# Link to project (required first)
railway link --project CarbonCoach

# Check current status
railway status

# List all projects
railway list
```

### Service Management
```bash
# Link to specific service
railway service web-service
railway service frontend

# Deploy to specific service
railway up --service web-service
railway up --service frontend

# Check logs for specific service
railway logs --service web-service
railway logs --service frontend
```

### Environment Variables
```bash
# View variables for a service
railway variables --service web-service
railway variables --service frontend

# Set variables
railway variables --service web-service --set KEY=value
```

### Database Connection
```bash
# Connect to PostgreSQL (works!)
railway connect postgres

# Example queries through connection
echo "SELECT COUNT(*) FROM vehicle_mpg;" | railway connect postgres
echo "\\dt" | railway connect postgres
```

### Domain Management
```bash
# Get/create domain for service
railway domain --service web-service
railway domain --service frontend
```

### Key Environment Variables (web-service)
```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:...@postgres.railway.internal:5432/railway
FLASK_APP=app.py
SECRET_KEY=a9edb0b2...
```

### Dependencies Fixed
- **httpx==0.27.2** (pinned to avoid 'proxies' argument error)
- **anthropic==0.62.0** (latest version)

## File Structure That Works

```
CarbonCoach/
├── carbon-calculator/
│   ├── backend/          # Flask API (ROOT_PATH should point here)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── Procfile
│   │   └── ...
│   └── frontend/         # Source files for NGINX service
│       ├── index.html
│       ├── styles.css
│       └── ...
├── site/                 # NGINX deployment directory
└── Dockerfile           # NGINX container config
```

## Deployment Process

1. **Backend**: Deploys from `carbon-calculator/backend/` using Nixpacks Python detection
2. **Frontend**: Uses custom Dockerfile + NGINX to serve `site/` directory
3. **Database**: Managed PostgreSQL service, connect via `railway connect postgres`