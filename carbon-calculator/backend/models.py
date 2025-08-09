from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Session(db.Model):
    __tablename__ = 'sessions'
    
    session_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    current_section = db.Column(db.String(50), default='introduction')
    progress_pct = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    
    responses = db.relationship('UserResponse', backref='session', lazy=True)
    calculations = db.relationship('CarbonCalculation', backref='session', lazy=True)
    recommendations = db.relationship('Recommendation', backref='session', lazy=True)
    conversation_logs = db.relationship('ConversationLog', backref='session', lazy=True)

class UserResponse(db.Model):
    __tablename__ = 'user_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), nullable=False)
    section = db.Column(db.String(50), nullable=False)
    question_key = db.Column(db.String(100), nullable=False)
    response_value = db.Column(db.Text, nullable=False)
    response_type = db.Column(db.String(20), nullable=False)  # text, number, boolean, choice
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CarbonCalculation(db.Model):
    __tablename__ = 'carbon_calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), nullable=False)
    total_annual_co2_kg = db.Column(db.Float, nullable=False)
    home_emissions = db.Column(db.Float, nullable=False)
    transport_emissions = db.Column(db.Float, nullable=False)
    consumption_emissions = db.Column(db.Float, nullable=False)
    calculation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    breakdowns = db.relationship('CalculationBreakdown', backref='calculation', lazy=True)

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), nullable=False)
    recommendation_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # home, transport, consumption
    priority_score = db.Column(db.Integer, nullable=False)
    co2_savings_kg = db.Column(db.Float, nullable=True)  # Annual CO2 savings in kg
    # DSIRE program references
    federal_program_id = db.Column(db.Integer, db.ForeignKey('dsire_federal_programs.id'), nullable=True)
    state_program_id = db.Column(db.Integer, db.ForeignKey('dsire_state_programs.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmissionFactor(db.Model):
    __tablename__ = 'emission_factors'
    
    factor_id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # electricity, natural_gas, gasoline, etc.
    region = db.Column(db.String(50), nullable=False)  # state code or 'US'
    co2_per_unit = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # kg/kwh, kg/therm, kg/gallon
    source = db.Column(db.String(100), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class VehicleMPG(db.Model):
    __tablename__ = 'vehicle_mpg'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    mpg_combined = db.Column(db.Float, nullable=False)
    vehicle_type = db.Column(db.String(20), nullable=False, default='gas')

class ElectricityRate(db.Model):
    __tablename__ = 'electricity_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(2), nullable=False)
    utility_company = db.Column(db.String(100), nullable=True)
    avg_rate_per_kwh = db.Column(db.Float, nullable=False)
    grid_emission_factor = db.Column(db.Float, nullable=False)  # kg CO2 per kWh


class ConversationLog(db.Model):
    __tablename__ = 'conversation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_message = db.Column(db.Text, nullable=False)
    assistant_response = db.Column(db.Text, nullable=False)
    section = db.Column(db.String(50), nullable=False)

class CalculationBreakdown(db.Model):
    __tablename__ = 'calculation_breakdowns'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.session_id'), nullable=False)
    calculation_id = db.Column(db.Integer, db.ForeignKey('carbon_calculations.id'), nullable=False)
    emission_source = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    units = db.Column(db.String(20), nullable=False)
    calculation_method = db.Column(db.Text, nullable=False)







# New DSIRE-integrated tables with structured financial data
class DsireFederalProgram(db.Model):
    __tablename__ = 'dsire_federal_programs'
    
    # Base fields (same as existing FederalProgram)
    id = db.Column(db.Integer, primary_key=True)
    dsire_id = db.Column(db.Integer, nullable=False, unique=True)  # DSIRE program ID for API updates
    name = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=True)  # financial_incentive, regulatory_policy
    program_type = db.Column(db.String(100), nullable=True)  # rebate, tax_credit, loan, grant, tax_exemption
    summary = db.Column(db.Text, nullable=True)
    website_url = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    credibility_boost = db.Column(db.Boolean, default=False)
    
    # NEW: Extracted financial data from ProgramParameters (nullable - not all programs have this)
    incentive_amount = db.Column(db.Float, nullable=True)           # Primary $ amount (rebate/tax credit cap/loan limit)
    percent_of_cost = db.Column(db.Float, nullable=True)            # 40.0 (from "40% of cost")
    percent_of_cost_cap = db.Column(db.Float, nullable=True)        # Max $ limit on % of cost
    per_unit_rate = db.Column(db.Float, nullable=True)              # 0.25 (for performance incentives)
    per_unit_type = db.Column(db.String(20), nullable=True)         # "$/W", "$/kW", "$/kWh"
    
    # NEW: Consumer-scale requirements (nullable - filter out >50kW during import)
    min_system_size_kw = db.Column(db.Float, nullable=True)         # 1.0, 3.0  
    max_system_size_kw = db.Column(db.Float, nullable=True)         # 25.0, 50.0
    min_project_cost = db.Column(db.Float, nullable=True)           # $900
    
    # NEW: Clean consumer summary (nullable - generated when financial data available)
    incentive_summary = db.Column(db.Text, nullable=True)           # "$1000 rebate" / "35% tax credit up to $2250"
    
    # Relationships (same pattern as existing)
    technologies = db.relationship('DsireFederalProgramTechnology', backref='program', lazy=True, cascade='all, delete-orphan')
    parameters = db.relationship('DsireFederalProgramParameter', backref='program', lazy=True, cascade='all, delete-orphan')

class DsireStateProgram(db.Model):
    __tablename__ = 'dsire_state_programs'
    
    # Base fields (same as existing StateProgram) 
    id = db.Column(db.Integer, primary_key=True)
    dsire_id = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(500), nullable=False)
    state = db.Column(db.String(2), nullable=False)  # Consistent with existing system
    category = db.Column(db.String(100), nullable=True)
    program_type = db.Column(db.String(100), nullable=True)  # This IS our incentive type
    summary = db.Column(db.Text, nullable=True)
    website_url = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    credibility_boost = db.Column(db.Boolean, default=False)
    
    # NEW: Same financial fields as federal (all nullable)
    incentive_amount = db.Column(db.Float, nullable=True)
    percent_of_cost = db.Column(db.Float, nullable=True)
    percent_of_cost_cap = db.Column(db.Float, nullable=True)
    per_unit_rate = db.Column(db.Float, nullable=True)
    per_unit_type = db.Column(db.String(20), nullable=True)
    min_system_size_kw = db.Column(db.Float, nullable=True)
    max_system_size_kw = db.Column(db.Float, nullable=True)
    min_project_cost = db.Column(db.Float, nullable=True)
    incentive_summary = db.Column(db.Text, nullable=True)
    
    # Relationships
    technologies = db.relationship('DsireStateProgramTechnology', backref='program', lazy=True, cascade='all, delete-orphan')
    parameters = db.relationship('DsireStateProgramParameter', backref='program', lazy=True, cascade='all, delete-orphan')

class DsireFederalProgramTechnology(db.Model):
    __tablename__ = 'dsire_federal_program_technologies'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('dsire_federal_programs.id'), nullable=False)
    dsire_technology_id = db.Column(db.Integer, nullable=False)  # Original DSIRE technology ID
    technology_name = db.Column(db.String(100), nullable=False)
    technology_category = db.Column(db.String(50), nullable=True)  # solar, heat_pumps, electric_vehicles, etc.
    
    __table_args__ = (db.Index('idx_dsire_federal_tech', 'program_id', 'technology_category'),)

class DsireStateProgramTechnology(db.Model):
    __tablename__ = 'dsire_state_program_technologies'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('dsire_state_programs.id'), nullable=False)
    dsire_technology_id = db.Column(db.Integer, nullable=False)  # Original DSIRE technology ID
    technology_name = db.Column(db.String(100), nullable=False)
    technology_category = db.Column(db.String(50), nullable=True)  # solar, heat_pumps, electric_vehicles, etc.
    
    __table_args__ = (db.Index('idx_dsire_state_tech', 'program_id', 'technology_category'),)

# Store raw ProgramParameters for audit trail and complex cases
class DsireFederalProgramParameter(db.Model):
    __tablename__ = 'dsire_federal_program_parameters_logging'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('dsire_federal_programs.id'), nullable=False)
    parameter_name = db.Column(db.String(100), nullable=False)  # "Incentive Amount", "Maximum Incentive", etc.
    amount = db.Column(db.String(50), nullable=True)  # Raw amount from DSIRE
    units = db.Column(db.String(20), nullable=True)  # Units from DSIRE
    qualifier = db.Column(db.String(50), nullable=True)  # Qualifier from DSIRE
    raw_data = db.Column(db.Text, nullable=True)  # Store complete parameter JSON for debugging

class DsireStateProgramParameter(db.Model):
    __tablename__ = 'dsire_state_program_parameters_logging'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('dsire_state_programs.id'), nullable=False)
    parameter_name = db.Column(db.String(100), nullable=False)  # "Incentive Amount", "Maximum Incentive", etc.
    amount = db.Column(db.String(50), nullable=True)  # Raw amount from DSIRE
    units = db.Column(db.String(20), nullable=True)  # Units from DSIRE
    qualifier = db.Column(db.String(50), nullable=True)  # Qualifier from DSIRE
    raw_data = db.Column(db.Text, nullable=True)  # Store complete parameter JSON for debugging