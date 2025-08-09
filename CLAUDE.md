This was your initial prompt. We have since expanded passed it to improve the recommendation algorithm and databases of vehicles. The database is stored in carbon-calculator/backend/instance/carbon_calculator.db

Carbon Footprint Calculator & Advisory Tool - Technical Specification
Project Overview
Building a conversational web application that helps users calculate their carbon footprint and provides personalized recommendations for reduction, including relevant government incentives and tax programs. This is an MVP prototype designed to showcase AI/climate tech capabilities.
Key Differentiators:
Conversational interface with memory and nuance understanding
Integration with government incentive databases (DSIRE, etc.)
Decision support beyond just calculation
Mobile-optimized experience
Example Use Case: User in Phoenix with gas heating → Calculate footprint → Recommend heat pump + identify APS utility rebates + Federal tax credits
Technical Architecture Decisions
Frontend: HTML/CSS/Vanilla JavaScript
- Mobile-first responsive design
- WCAG AA compliant color palette
- Session-based state management (no user accounts) via localStorage
- Progress tracking through conversation sections (0-100%)
- Dedicated recommendations page (recommendations.html) with interactive UI
- Conversational chat interface with typing indicators

Backend: Python3 Flask + SQLAlchemy + SQLite
- Session-based user tracking (UUID in localStorage)
- Direct Anthropic Claude API integration (claude-3-5-sonnet-20241022)
- Python3-based carbon calculations (not LLM) with detailed breakdown tracking
- RESTful API endpoints with comprehensive error handling
- Diagnostic & lifestyle recommendation engines
- Government program database (DSIRE) with 1000+ programs

Deployment: Local development (backend: port 5001, frontend: port 8000) for now, eventually Railway
Data Strategy: Curated government programs, static emission factors, comprehensive vehicle MPG database
Database Schema
sql
-- Core user flow
sessions: session_id (UUID - int), created_at, last_active, current_section, progress_pct, completed

user_responses: session_id, section, question_key, response_value, response_type

carbon_calculations: session_id, total_annual_co2_kg, home_emissions, transport_emissions, consumption_emissions, calculation_date

recommendations: session_id, recommendation_text, category, priority_score, government_program_id, created_at

-- Reference data
emission_factors: factor_id, category, region, co2_per_unit, unit, source, last_updated

vehicle_mpg: year, make, model, mpg_combined, vehicle_type

electricity_rates: state, utility_company, avg_rate_per_kwh, grid_emission_factor

-- DSIRE Government Programs Database (1000+ programs imported)
federal_programs: id, name, category, program_type, summary, website_url, last_updated, created_at, credibility_boost

state_programs: id, name, state, category, program_type, summary, website_url, last_updated, created_at, credibility_boost

federal_program_technologies: id, program_id, technology_name, technology_category

state_program_technologies: id, program_id, technology_name, technology_category

federal_program_details: id, program_id, detail_type, detail_value, display_order

state_program_details: id, program_id, detail_type, detail_value, display_order

-- Legacy (kept for now)
government_programs: program_id, name, description, program_type, eligibility_criteria, benefit_amount, state, federal_flag, active_flag

-- Debug/development
conversation_logs: session_id, timestamp, user_message, assistant_response, section

calculation_breakdowns: session_id, calculation_id, emission_source, value, units, calculation_method
Conversation Flow Structure
5 Main Sections with Progress Tracking:
Introduction & Setup
Location (state + city)
Household size
Housing type
Home Energy
Square footage
Monthly electricity bill ($)
Heating type (gas/electric/oil/heat pump)
Monthly heating bill ($)
Solar panels (Y/N)
Transportation
Primary vehicle (year/make/model for MPG lookup)
Annual miles driven
Additional vehicles
Flight count (domestic/international)
Consumption
Diet type (vegetarian/meat-eater/heavy meat)
Online shopping frequency
Results & Recommendations
Carbon footprint breakdown
Personalized reduction strategies
Government incentive matching
Guardrails: Any off-topic input gets: "I'm sorry, but as a prototype I cannot factor that into your carbon emissions calculation. Let me help you with [current section topic]."
The tone should be friendly but professional, and ask follow up questions whenever clarification is needed
Carbon Calculation Requirements (Implemented in carbon_calc.py)
Core Calculation Functions:
- calculate_home_emissions(): Handles electricity, heating (gas/electric/oil/heat pump), solar panels
- calculate_transport_emissions(): Vehicle MPG database lookup, domestic/international flights  
- calculate_consumption_emissions(): Diet types (5 levels) and shopping frequency (4 levels)
- calculate_total_footprint(): Aggregates all components with detailed breakdown tracking

Implemented Features:
- State-specific electricity grid emission factors
- Comprehensive vehicle MPG database with year/make/model lookup
- Detailed breakdown tracking in calculation_breakdowns table
- Support for heat pumps, solar panels, and multiple housing types
- Real emission factors for diet types and shopping patterns
Sample Data Required:
State electricity grid emission factors
Vehicle MPG database (sample entries)
Flight emission factors
Diet emission factors
Phoenix area government programs (heat pump incentives example)
Recommendation System Architecture (Implemented)

Diagnostic Recommendations Engine (diagnostic_recommendations.py):
- Analyzes user responses against efficiency baselines to identify technology upgrade opportunities
- Categories: solar_opportunity, home_heating, transportation, home_efficiency
- Compares user data to state/household baselines (e.g. electricity usage 1.5x above baseline)
- Matches opportunities to DSIRE government programs by technology category and location (specifically state)
- Returns structured recommendations with CO2 savings, priority scores (0-100), and government programs

Lifestyle Recommendations Engine (lifestyle_recommendations.py):
- Analyzes detailed breakdown data to identify behavioral change opportunities
- Categories: flights (>3 domestic OR >1 international), driving (>1.25x average), energy usage (>1.8x baseline)
- Diet recommendations (heavy/moderate → light meat), shopping frequency (very_high/high → moderate)
- Calculates CO2 savings and cost savings for each recommendation
- Uses actual emission calculations rather than generic suggestions

Government Program Integration:
- DSIRE database with 1000+ federal and state programs
- Technology matching: solar panels, heat pumps, electric vehicles, home efficiency
- Financial incentive formatting: percentages, fixed amounts, per-unit rates, and combinations of those
- Program credibility tracking and website links for application
- State-specific program filtering and relevance scoring

Sample Matching Logic:
- No heat pump + gas heating + state with heat pump incentives → heat pump upgrade recommendation
- High electricity usage + good solar potential → solar panel recommendation
- Gas vehicle + >15k annual miles → electric vehicle recommendation
- Each recommendation includes relevant government programs with financial details
UI/UX Requirements
Color Palette (WCAG AA Compliant):
Primary: #1B4332 (deep forest green)
Secondary: #2D5A27 (rich green)
Accent: #52B788 (bright green)
Text: #212529 (near black), #495057 (dark gray)
Backgrounds: #FFFFFF (white), #F8F9FA (light gray)
Success: #E9F7EF, Error: #DC3545
Typography:
css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
Headers: 28px/600, Body: 16px/400, line-height: 1.5
Mobile-First Design:
Clean, modern climate tech aesthetic
Conversational interface with chat bubbles
Progress bar across top
Touch-friendly buttons and inputs
API Endpoints Structure
- GET  /api/session/{session_id}     # Get or create session with progress tracking
- POST /api/conversation             # Send user message, get Claude response with data extraction
- GET  /api/calculations/{session_id} # Get stored calculations with breakdown
- POST /api/calculate                # Trigger carbon footprint calculation with detailed breakdowns
- GET  /api/recommendations/{session_id} # Get diagnostic + lifestyle recommendations with government programs
LLM Integration Specifications
Anthropic Claude Integration:
- Model: claude-3-5-sonnet-20241022
- Direct API calls from Flask routes via llm_service.py
- Dynamic system prompts with section-specific guidance and easter eggs
- Structured JSON responses with data validation and field normalization
- Environment variable for API key (ANTHROPIC_API_KEY)

Conversation Management:
- Track current section and progress (5 sections: introduction, home_energy, transportation, consumption, results)
- Remember previous responses within session with context building
- Guide user through 19 required fields across structured data collection
- Smart response validation with text-to-numeric conversion and standardization
- Progress calculation based on completed fields (0-100%)
Development Requirements
Code Quality:
Comprehensive comments throughout
Clear error states with descriptive messages
Console logging for debugging
Basic test cases for core functionality, adding as we go
Error Handling:
Graceful API failure handling
Input validation with friendly messages
Database connection error handling
Network timeout handling
Test Cases Required:
Complete user conversation flow
Carbon calculation accuracy
Government program matching logic
Session management
Mobile responsiveness
File Structure (Cleaned & Optimized)
carbon-calculator/
├── backend/ (7 essential files after cleanup from 82+ files)
│   ├── app.py                      # Flask application with CORS and database initialization
│   ├── models.py                   # SQLAlchemy models for sessions, responses, calculations, programs
│   ├── routes.py                   # RESTful API endpoints
│   ├── carbon_calc.py              # Carbon calculation engine with breakdown tracking
│   ├── llm_service.py              # Claude API integration with conversation management
│   ├── diagnostic_recommendations.py # Technology upgrade recommendations with government program matching
│   ├── lifestyle_recommendations.py  # Lifestyle change recommendations based on breakdown analysis
│   ├── data/populate_data.py       # Database population script
│   └── instance/carbon_calculator.db # SQLite database file
├── frontend/ (Clean, production-ready files)
│   ├── index.html              # Main chat interface
│   ├── recommendations.html    # Dedicated recommendations page with interactive UI
│   ├── styles.css              # Climate tech styling with mobile responsiveness
│   ├── script.js               # Main application logic (496 lines, clean)
│   ├── recommendations.js      # Recommendations page logic with government program display
│   ├── session.js              # Session management and API communication
│   ├── carbon_coach_avatar.png # Assistant avatar image
│   └── Gemini_Generated_Image_*.png # Background images (3 available, 1 active)
└── README.md                   # Setup instructions
Success Criteria
Working Prototype That:
Completes full conversation flow from introduction to recommendations
Calculates reasonably accurate carbon footprints
Provides relevant government program recommendations
Works smoothly on mobile devices
Specific Example to Implement: User in Phoenix, AZ with gas heating and no heat pump → System calculates high heating emissions → Recommends heat pump installation → Identifies APS utility rebate + Federal tax credit → Provides implementation guidance
Please build a complete, working prototype with all components integrated, sample data populated, and test cases included. Focus on clean, well-commented code that can be easily debugged and iterated upon.

