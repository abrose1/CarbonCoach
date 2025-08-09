# Carbon Footprint Calculator & Advisory Tool

A conversational web application that helps users calculate their carbon footprint and provides personalized recommendations for reduction, including relevant government incentives and tax programs.

## 🌟 Features

- **Conversational Interface**: AI-powered chat experience using Claude
- **Comprehensive Calculations**: Home energy, transportation, and consumption emissions
- **Government Programs**: Integration with federal and state incentive databases
- **Mobile-Optimized**: Responsive design that works on all devices
- **Privacy-Focused**: Session-based tracking with no user accounts required
- **WCAG AA Compliant**: Accessible design with proper color contrast

## 🏗️ Architecture

- **Frontend**: HTML/CSS/Vanilla JavaScript
- **Backend**: Python Flask + SQLAlchemy + PostgreSQL
- **AI Integration**: Direct Anthropic Claude API integration
- **Database**: PostgreSQL with comprehensive emission factors for all 50 states

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Anthropic API key
- Node.js (optional, for development tools)

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Navigate to backend directory
cd carbon-calculator/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Install PostgreSQL (macOS with Homebrew)
brew install postgresql
brew services start postgresql

# Create database
createdb carbon_calculator

# Or use PostgreSQL command line
psql -c "CREATE DATABASE carbon_calculator;"
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
```

Required environment variables:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/carbon_calculator
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
```

### 4. Run the Application

```bash
# Start the Flask backend
python app.py
```

The backend will be available at `http://localhost:5000`

### 5. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Serve the frontend (using Python's built-in server)
python -m http.server 8000

# Or use any other static file server
# For example, with Node.js:
# npx serve .
```

The frontend will be available at `http://localhost:8000`

## 🗄️ Database Schema

The application uses the following main tables:

- **sessions**: Track user sessions and progress
- **user_responses**: Store user answers by section
- **carbon_calculations**: Store calculated carbon footprints
- **recommendations**: Personalized reduction recommendations
- **emission_factors**: CO2 emission factors for all 50 states
- **vehicle_mpg**: Vehicle fuel efficiency database
- **government_programs**: Federal and state incentive programs

## 🔧 Configuration

### Backend Configuration

The Flask app can be configured through environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `FLASK_ENV`: development or production
- `SECRET_KEY`: Flask secret key for sessions

### Frontend Configuration

Update the API base URL in `frontend/session.js` if deploying to different domains:

```javascript
this.apiBaseUrl = 'http://localhost:5000/api'; // Change for production
```

## 🧪 Testing

### Test the Backend API

```bash
# Health check
curl http://localhost:5000/api/health

# Create a session
curl -X GET http://localhost:5000/api/session/test-session-id

# Send a conversation message
curl -X POST http://localhost:5000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session-id", "message": "I live in Phoenix, Arizona"}'
```

### Test the Complete User Flow

1. Open `http://localhost:8000` in your browser
2. Complete the conversation flow:
   - **Introduction**: State/city, household size, housing type
   - **Home Energy**: Square footage, bills, heating type, solar
   - **Transportation**: Vehicle details, miles driven, flights
   - **Consumption**: Diet type, shopping frequency
3. Review results and recommendations

### Example Test Data

For Phoenix, AZ user testing:
- Location: Phoenix, Arizona
- Household: 2 people, house
- Home: 2000 sq ft, $150 electric bill, gas heating $80/month, no solar
- Transport: 2020 Honda Civic, 15,000 miles/year, 2 domestic flights
- Consumption: Meat eater, moderate shopping

Expected result: ~14-16 tons CO2/year with heat pump and solar recommendations

## 🚢 Deployment

### Railway Deployment

1. Create a Railway account and project
2. Connect your GitHub repository
3. Set environment variables in Railway dashboard
4. Deploy backend to Railway
5. Update frontend API URL to Railway backend URL
6. Deploy frontend to static hosting (Netlify, Vercel, etc.)

### Environment Variables for Production

```env
ANTHROPIC_API_KEY=your_production_api_key
DATABASE_URL=postgresql://user:pass@railway-postgres-url/dbname
FLASK_ENV=production
SECRET_KEY=strong_production_secret_key
```

## 📊 Data Sources

- **Electricity Grid Factors**: EPA eGRID 2021
- **Vehicle MPG**: EPA Fuel Economy Database
- **Emission Factors**: EPA greenhouse gas emission factors
- **Government Programs**: DSIRE database and federal program websites

## 🛠️ Development

### Adding New Emission Factors

```python
# In populate_data.py, add new factors:
factor = EmissionFactor(
    category='new_category',
    region='US',  # or state code
    co2_per_unit=0.123,
    unit='kg/unit',
    source='Data Source'
)
db.session.add(factor)
```

### Adding New Government Programs

```python
program = GovernmentProgram(
    name='Program Name',
    description='Program description',
    program_type='rebate',  # rebate, tax_credit, loan, etc.
    eligibility_criteria='Eligibility requirements',
    benefit_amount='$1,000',
    state='CA',  # or None for federal
    federal_flag=False,
    active_flag=True
)
```

### Customizing the Conversation Flow

Modify the conversation sections in `llm_service.py`:

```python
self.sections = ['introduction', 'home_energy', 'transportation', 'consumption', 'results']
self.section_progress = {
    'introduction': 20,
    'home_energy': 40,
    'transportation': 60,
    'consumption': 80,
    'results': 100
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database exists

2. **Anthropic API Error**
   - Verify API key is correct
   - Check API key permissions
   - Monitor API usage limits

3. **Frontend Can't Connect to Backend**
   - Verify backend is running on port 5000
   - Check CORS settings
   - Update API URL in session.js

4. **Empty Database**
   - Check if populate_data.py ran successfully
   - Manually run: `python -c "from app import create_app; from data.populate_data import populate_initial_data; app = create_app(); app.app_context().push(); populate_initial_data()"`

### Logging

Backend logs are printed to console. For production, configure proper logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📚 API Documentation

### Endpoints

- `GET /api/session/{session_id}` - Get or create session
- `POST /api/conversation` - Send message to conversation
- `POST /api/calculate` - Calculate carbon footprint
- `GET /api/calculations/{session_id}` - Get calculation results
- `GET /api/recommendations/{session_id}` - Get recommendations
- `GET /api/health` - Health check

### Response Formats

All API responses return JSON with consistent error handling:

```json
{
  "success": true,
  "data": {},
  "message": "Success message"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please open an issue on GitHub or contact the development team.

---

Built with ❤️ for a more sustainable future 🌍