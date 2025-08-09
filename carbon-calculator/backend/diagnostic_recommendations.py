#!/usr/bin/env python3
"""
Diagnostic-Driven Recommendations Engine
Analyzes user responses to identify biggest carbon footprint drivers and targets those with relevant programs.
"""

from typing import Dict, List, Tuple, Optional
from models import (
    db, DsireFederalProgram, DsireStateProgram, 
    DsireFederalProgramTechnology, DsireStateProgramTechnology,
    Recommendation, VehicleMPG
)
from carbon_calc import calculate_home_emissions, calculate_transport_emissions
import logging

logger = logging.getLogger(__name__)

# Baseline data for comparisons (2024 data, properly adjusted for per-person vs per-household)
BASELINES = {
    # National averages - adjusted for individual responsibility
    'electricity_monthly_per_person': 58,  # $150 household / 2.6 people
    'annual_miles_per_driver': 13482,  # Per licensed driver (FHWA 2024)
    'square_feet_per_person': 850,  # 2210 household / 2.6 people
    'domestic_flights_per_person': 1.2,  # Estimated from travel surveys
    'international_flights_per_person': 0.3,  # Estimated from travel surveys
    
    # State-specific electricity costs per person (monthly)
    'electricity_monthly_by_state': {
        'AL': 50, 'AK': 58, 'AZ': 46, 'AR': 42, 'CA': 79,
        'CO': 37, 'CT': 77, 'DE': 54, 'FL': 54, 'GA': 50,
        'HI': 82, 'ID': 31, 'IL': 46, 'IN': 42, 'IA': 40,
        'KS': 42, 'KY': 40, 'LA': 44, 'ME': 62, 'MD': 58,
        'MA': 69, 'MI': 50, 'MN': 49, 'MS': 46, 'MO': 42,
        'MT': 35, 'NE': 40, 'NV': 42, 'NH': 65, 'NJ': 62,
        'NM': 33, 'NY': 65, 'NC': 46, 'ND': 38, 'OH': 46,
        'OK': 40, 'OR': 42, 'PA': 54, 'RI': 69, 'SC': 50,
        'SD': 42, 'TN': 44, 'TX': 66, 'UT': 33, 'VT': 62,
        'VA': 50, 'WA': 37, 'WV': 42, 'WI': 50, 'WY': 35
    },
    
    # State-specific heating costs per person (monthly during heating season)
    'heating_monthly_by_state': {
        # Natural gas heating costs per person (winter 2024-25)
        'gas': {
            'RI': 73, 'AK': 59, 'MI': 52, 'MO': 51, 'CT': 51,
            'OH': 48, 'IL': 47, 'IN': 46, 'WI': 45, 'PA': 44,
            'NY': 44, 'NJ': 43, 'MA': 42, 'MN': 41, 'IA': 40,
            'KS': 39, 'NE': 38, 'ND': 37, 'SD': 36, 'WY': 35,
            'CO': 34, 'OK': 33, 'TX': 32, 'NM': 31, 'UT': 30,
            'NV': 29, 'CA': 35, 'OR': 33, 'WA': 31, 'ID': 29,
            'MT': 32, 'AL': 28, 'AR': 27, 'FL': 25, 'GA': 26,
            'KY': 29, 'LA': 26, 'NC': 28, 'SC': 27, 'TN': 28,
            'VA': 30, 'WV': 31, 'AZ': 27, 'DE': 35, 'MD': 36,
            'ME': 38, 'NH': 40, 'VT': 41, 'HI': 45  # Propane mostly
        },
        # Electric heating (roughly 2.5x electricity rate during winter)
        'electric': {
            'AL': 125, 'AK': 145, 'AZ': 115, 'AR': 105, 'CA': 198,
            'CO': 93, 'CT': 193, 'DE': 135, 'FL': 135, 'GA': 125,
            'HI': 205, 'ID': 78, 'IL': 115, 'IN': 105, 'IA': 100,
            'KS': 105, 'KY': 100, 'LA': 110, 'ME': 155, 'MD': 145,
            'MA': 173, 'MI': 125, 'MN': 123, 'MS': 115, 'MO': 105,
            'MT': 88, 'NE': 100, 'NV': 105, 'NH': 163, 'NJ': 155,
            'NM': 83, 'NY': 163, 'NC': 115, 'ND': 95, 'OH': 115,
            'OK': 100, 'OR': 105, 'PA': 135, 'RI': 173, 'SC': 125,
            'SD': 105, 'TN': 110, 'TX': 165, 'UT': 83, 'VT': 155,
            'VA': 125, 'WA': 93, 'WV': 105, 'WI': 125, 'WY': 88
        },
        # Other heating types (per person monthly)
        'oil': 104,  # $1610 / 6 months / 2.6 people
        'propane': 83,  # $1300 / 6 months / 2.6 people
        'heat_pump': 75  # More efficient than electric resistance
    }
}

class DiagnosticInsight:
    """Represents a diagnostic insight about user's carbon footprint drivers"""
    def __init__(self, category: str, severity: str, co2_savings_kg: int, 
                 description: str, technologies: List[str]):
        self.category = category  # 'home_heating', 'home_efficiency', 'transport', etc.
        self.severity = severity  # 'high', 'medium', 'low'
        self.co2_savings_kg = co2_savings_kg  # Actual kg CO2 savings potential per year
        self.description = description  # Human readable explanation
        self.technologies = technologies  # DSIRE technology categories to target

def analyze_user_inefficiencies(responses: Dict) -> List[DiagnosticInsight]:
    """
    Analyze user responses to identify biggest carbon footprint drivers and inefficiencies.
    Focus on clear "boxes to check" - what they DON'T have rather than bill analysis.
    Returns list of insights ordered by potential impact.
    """
    insights = []
    
    intro_data = responses.get('introduction', {})
    home_data = responses.get('home_energy', {})
    transport_data = responses.get('transportation', {})
    consumption_data = responses.get('consumption', {})
    
    state = intro_data.get('state', 'CA')
    
    # PRIMARY FOCUS: Clear boxes to check (what they don't have)
    
    # 1. High-carbon heating source (gas/oil/propane)
    heating_insight = analyze_heating_source(home_data, intro_data)
    if heating_insight:
        insights.append(heating_insight)
    
    # 2. No solar panels (if suitable housing)
    solar_insight = analyze_solar_opportunity(home_data, intro_data)
    if solar_insight:
        insights.append(solar_insight)
    
    # 3. Low-efficiency vehicle (using actual MPG database)
    transport_insight = analyze_vehicle_efficiency(transport_data)
    if transport_insight:
        insights.append(transport_insight)
    
    # SECONDARY: Bill analysis only if very high
    energy_insight = analyze_extreme_energy_costs(home_data, intro_data)
    if energy_insight:
        insights.append(energy_insight)
    
    # Sort by CO2 savings potential (highest first)
    insights.sort(key=lambda x: x.co2_savings_kg, reverse=True)
    
    return insights

def analyze_heating_source(home_data: Dict, intro_data: Dict) -> Optional[DiagnosticInsight]:
    """Calculate CO2 savings from switching to heat pump"""
    heating_type = home_data.get('heating_type', '').lower()
    
    if not heating_type:
        return None
    
    # High carbon heating types - clear box to check
    high_carbon_fuels = ['gas', 'natural gas', 'oil', 'propane']
    is_high_carbon = any(fuel in heating_type for fuel in high_carbon_fuels)
    
    if is_high_carbon:
        try:
            # Calculate current heating emissions
            current_sqft = home_data.get('square_footage', 1500)
            current_electric = home_data.get('monthly_electricity', 100)
            current_heating_bill = home_data.get('heating_bill', 100)
            current_state = intro_data.get('state', 'CA')
            current_household = intro_data.get('household_size', 2)
            
            current_emissions, _ = calculate_home_emissions(
                sqft=current_sqft,
                electric_bill=current_electric,
                heating_type=heating_type,
                heating_bill=current_heating_bill,
                state=current_state,
                household_size=current_household,
                session_id='temp-heating-calc'
            )
            
            # Calculate emissions with heat pump (more efficient electric heating)
            hp_sqft = home_data.get('square_footage', 1500)
            hp_electric = home_data.get('monthly_electricity', 100)
            hp_heating_bill = home_data.get('heating_bill', 100) * 0.6
            hp_state = intro_data.get('state', 'CA')
            hp_household = intro_data.get('household_size', 2)
            
            heat_pump_emissions, _ = calculate_home_emissions(
                sqft=hp_sqft,
                electric_bill=hp_electric,
                heating_type='heat_pump',  # Efficient electric heating
                heating_bill=hp_heating_bill,  # Heat pumps ~40% more efficient
                state=hp_state,
                household_size=hp_household,
                session_id='temp-heating-calc'
            )
            
            co2_savings = current_emissions - heat_pump_emissions
            
            if co2_savings > 500:  # Only recommend if meaningful savings
                severity = 'high' if co2_savings > 2000 else 'medium'
                description = f"I noticed you are using {heating_type} heating which produces high carbon emissions. You could reduce your carbon emissions by ~{co2_savings:,.0f} kg CO2/year by upgrading to a heat pump"
                
                insight = DiagnosticInsight(
                    category='home_heating',
                    severity=severity,
                    co2_savings_kg=int(co2_savings),
                    description=description,
                    technologies=['heat_pumps']
                )
                return insight
        except Exception as e:
            logger.error(f"Error calculating heating CO2 savings: {e}")
            # Fallback to estimated savings
            co2_savings = 1500  # Rough estimate for gas heating
            description = f"I noticed you are using {heating_type} heating which produces high carbon emissions"
            
            return DiagnosticInsight(
                category='home_heating',
                severity='medium',
                co2_savings_kg=co2_savings,
                description=description,
                technologies=['heat_pumps']
            )
    
    return None


def analyze_vehicle_efficiency(transport_data: Dict) -> Optional[DiagnosticInsight]:
    """Calculate CO2 savings from switching to EV"""
    annual_miles = transport_data.get('annual_miles', 0)
    vehicle_year = transport_data.get('vehicle_year')
    vehicle_make = transport_data.get('vehicle_make', '').lower()
    vehicle_model = transport_data.get('vehicle_model', '').lower()
    
    if not annual_miles or not vehicle_year or not vehicle_make or not vehicle_model:
        return None
    
    # Look up actual vehicle MPG from database
    try:
        vehicle_mpg = db.session.query(VehicleMPG).filter(
            VehicleMPG.year == vehicle_year,
            VehicleMPG.make.ilike(f'%{vehicle_make}%'),
            VehicleMPG.model.ilike(f'%{vehicle_model}%')
        ).first()
        
        if vehicle_mpg:
            mpg = vehicle_mpg.mpg_combined
        else:
            # Fallback: estimate based on vehicle type
            if any(keyword in f"{vehicle_make} {vehicle_model}" for keyword in [
                'truck', 'suv', 'suburban', 'tahoe', 'escalade', 'navigator', 
                'expedition', 'f-150', 'silverado', 'ram', 'tundra', 'titan'
            ]):
                mpg = 20  # Typical truck/SUV
            else:
                return None  # Can't determine efficiency
    except Exception as e:
        logger.error(f"Error looking up vehicle MPG: {e}")
        return None
    
    # Calculate CO2 savings from switching to EV
    try:
        # Current vehicle emissions
        current_emissions, _ = calculate_transport_emissions(
            vehicle_data={'year': vehicle_year, 'make': vehicle_make, 'model': vehicle_model},
            annual_miles=annual_miles,
            flights={'domestic': 0, 'international': 0},  # Only comparing vehicle emissions
            session_id='temp-vehicle-calc'
        )
        
        # EV emissions (assume efficient EV like Tesla Model 3)
        ev_emissions, _ = calculate_transport_emissions(
            vehicle_data={'year': 2023, 'make': 'tesla', 'model': 'model 3'},
            annual_miles=annual_miles,  # Same mileage
            flights={'domestic': 0, 'international': 0},
            session_id='temp-vehicle-calc'
        )
        
        co2_savings = current_emissions - ev_emissions
        
        # Only recommend if meaningful savings (EVs have ~70-90% lower emissions)
        if co2_savings > 1000:  # Significant savings threshold
            severity = 'high' if co2_savings > 4000 else 'medium'
            description = f"I noticed you are driving {annual_miles:,} miles/year in your {vehicle_year} {vehicle_make} {vehicle_model} ({mpg} MPG). You could reduce your carbon emissions by {co2_savings:,.0f} kg CO2/year by upgrading to an EV"
            
            return DiagnosticInsight(
                category='transportation',
                severity=severity,
                co2_savings_kg=int(co2_savings),
                description=description,
                technologies=['electric_vehicles']
            )
    except Exception as e:
        logger.error(f"Error calculating vehicle CO2 savings: {e}")
        # Fallback calculation based on MPG and miles
        if mpg < 30:  # Low efficiency worth recommending
            # Rough estimate: (annual_miles / mpg) * 8.9 kg CO2/gallon - EV equivalent
            gas_emissions = (annual_miles / mpg) * 8.9
            ev_emissions = annual_miles * 0.2  # Rough EV emissions kg CO2/mile
            co2_savings = int(gas_emissions - ev_emissions)
            
            if co2_savings > 1000:
                severity = 'high' if co2_savings > 4000 else 'medium'
                description = f"I noticed you are driving {annual_miles:,} miles/year in your {vehicle_year} {vehicle_make} {vehicle_model} ({mpg} MPG)"
                
                return DiagnosticInsight(
                    category='transportation',
                    severity=severity,
                    co2_savings_kg=co2_savings,
                    description=description,
                    technologies=['electric_vehicles']
                )
    
    return None

def analyze_solar_opportunity(home_data: Dict, intro_data: Dict) -> Optional[DiagnosticInsight]:
    """Calculate CO2 savings from installing solar panels"""
    has_solar = home_data.get('solar_panels', False)
    housing_type = intro_data.get('housing_type', '').lower()
    electricity_bill = home_data.get('monthly_electricity', 0)
    
    # Clear box to check: No solar panels + suitable housing
    if has_solar:
        return None
    
    # Solar is not viable for apartments/condos
    if 'apartment' in housing_type or 'condo' in housing_type:
        return None
    
    # Estimate CO2 savings from solar (rough calculation)
    # Higher electricity bills = more potential savings
    if electricity_bill > 80:  # Above minimal usage
        # Rough estimate: solar typically offsets 70-90% of electricity emissions
        # Assume average home uses ~10,000 kWh/year, user's usage proportional to bill
        annual_kwh = (electricity_bill / 0.16) * 12  # Estimate kWh from bill
        
        # US grid average ~0.4 kg CO2/kWh, solar ~0.05 kg CO2/kWh
        grid_emissions = annual_kwh * 0.4
        solar_emissions = annual_kwh * 0.05
        co2_savings = int(grid_emissions - solar_emissions)
        
        if co2_savings > 800:  # Meaningful savings threshold
            severity = 'medium'
            description = f"I noticed you do not have solar panels on your {housing_type}. You could reduce your carbon emissions by ~{co2_savings:,.0f} kg CO2/year by installing them"
            
            return DiagnosticInsight(
                category='solar_opportunity',
                severity=severity,
                co2_savings_kg=co2_savings,
                description=description,
                technologies=['solar']
            )
    
    return None

def analyze_extreme_energy_costs(home_data: Dict, intro_data: Dict) -> Optional[DiagnosticInsight]:
    """Analyze only extreme energy costs that clearly indicate inefficiency"""
    electricity_bill = home_data.get('monthly_electricity', 0)
    square_footage = home_data.get('square_footage', 1500)
    state = intro_data.get('state', 'CA')
    household_size = intro_data.get('household_size', 2)
    
    if not electricity_bill:
        return None
    
    # Calculate expected electricity cost per person
    state_baseline_per_person = BASELINES['electricity_monthly_by_state'].get(state, 58)
    expected_cost_household = state_baseline_per_person * household_size
    
    # Adjust for square footage (larger homes use more electricity)
    if square_footage > 0:
        sqft_per_person = square_footage / household_size
        sqft_multiplier = sqft_per_person / BASELINES['square_feet_per_person']
        expected_cost_household = expected_cost_household * sqft_multiplier
    
    cost_ratio = electricity_bill / expected_cost_household if expected_cost_household > 0 else 1
    
    # Only flag EXTREME costs (likely indicates major inefficiency)
    if cost_ratio > 1.8:  # 80% above expected - clearly inefficient
        # Estimate CO2 savings from comprehensive efficiency improvements
        excess_bill = electricity_bill - expected_cost_household
        excess_kwh = (excess_bill / 0.16) * 12  # Convert to annual excess kWh
        
        # Assume 30-50% of excess usage can be eliminated through efficiency
        potential_kwh_savings = excess_kwh * 0.4
        co2_savings = int(potential_kwh_savings * 0.4)  # Grid emissions factor
        
        severity = 'high'
        description = f"I noticed your electricity bill ${electricity_bill}/month seems unusually high. You could reduce your carbon emissions by ~{co2_savings:,.0f} kg CO2/year through efficiency upgrades to your HVAC, insulation, appliances, or lighting"
        
        return DiagnosticInsight(
            category='home_efficiency',
            severity=severity,
            co2_savings_kg=co2_savings,
            description=description,
            technologies=['hvac', 'insulation', 'appliances', 'lighting']
        )
    
    return None

def get_programs_for_technologies(state_code: str, technologies: List[str], limit: int = 20) -> List[Tuple[object, bool]]:
    """
    Get relevant programs for specified technologies.
    Returns list of (program, is_federal) tuples.
    No arbitrary federal/state limits - let scoring determine the best programs.
    """
    programs = []
    
    # Get ALL federal programs for these technologies
    federal_programs = db.session.query(DsireFederalProgram).join(
        DsireFederalProgramTechnology
    ).filter(
        DsireFederalProgramTechnology.technology_category.in_(technologies)
    ).distinct().all()  # No limit - get all relevant federal programs
    
    for program in federal_programs:
        programs.append((program, True))
    
    # Get ALL state programs for these technologies
    state_programs = db.session.query(DsireStateProgram).join(
        DsireStateProgramTechnology
    ).filter(
        DsireStateProgram.state == state_code,
        DsireStateProgramTechnology.technology_category.in_(technologies)
    ).distinct().all()  # No limit - get all relevant state programs
    
    for program in state_programs:
        programs.append((program, False))
    
    return programs

def select_most_specific_program(programs: List[Tuple[object, bool]], insight: 'DiagnosticInsight') -> Tuple[object, bool]:
    """
    Select the program most specific to the improvement area.
    Scores programs based on how well they match the specific technology category.
    """
    
    # Keywords that indicate program specificity for each technology
    specificity_keywords = {
        'electric_vehicles': ['electric vehicle', 'ev', 'vehicle', 'plug-in'],
        'heat_pumps': ['heat pump', 'electrification', 'hvac', 'heating', 'cooling'],
        'solar': ['solar', 'photovoltaic', 'pv', 'renewable energy'],
        'comprehensive': ['energy efficiency', 'weatherization', 'home improvement'],
        'hvac': ['hvac', 'heating', 'cooling', 'air conditioning'],
        'insulation': ['insulation', 'weatherization', 'envelope'],
        'appliances': ['appliance', 'refrigerator', 'washer', 'dryer'],
        'water_heating': ['water heat', 'hot water'],
        'lighting': ['lighting', 'led', 'lamp'],
        'energy_storage': ['battery', 'storage', 'backup power']
    }
    
    def score_program_specificity(program, is_federal):
        """Score how specific this program is to the insight's technologies"""
        score = 0
        program_text = (program.name + ' ' + (program.summary or '')).lower()
        
        # Check for keyword relevance with threshold-based scoring (no stacking)
        total_target_keywords = 0
        matched_keywords = 0
        
        for tech in insight.technologies:
            keywords = specificity_keywords.get(tech, [])
            total_target_keywords += len(keywords)
            for keyword in keywords:
                if keyword in program_text:
                    matched_keywords += 1
        
        # Threshold-based scoring instead of stacking
        if total_target_keywords > 0:
            match_percentage = matched_keywords / total_target_keywords
            if match_percentage >= 0.25:  # 25% or more keywords match
                score += 10
            elif matched_keywords > 0:  # At least one keyword matches
                score += 5
        
        # Note: We don't penalize "generic" words like "program", "rebate", etc. since we're already
        # filtering by technology and these words are actually descriptive of the incentive type
        
        # No preference between state/federal - let them compete on specificity and type
            
        # Prefer rebates and grants over loans and tax incentives for user experience
        program_type_preference = {
            'rebate': 5,
            'grant': 4, 
            'tax_credit': 3,
            'tax_deduction': 2,
            'loan': 1,
            'tax_incentive': 1,
            'other_financial': 0
        }
        score += program_type_preference.get(program.program_type, 0)
        
        # Add credibility boost for well-known programs
        if hasattr(program, 'credibility_boost') and program.credibility_boost:
            score += 5  # Modest boost for credible programs
        
        return score
    
    # Score all programs and pick the highest
    if not programs:
        return None, False
    
    scored_programs = [
        (program, is_federal, score_program_specificity(program, is_federal))
        for program, is_federal in programs
    ]
    
    # Sort by score (highest first)
    scored_programs.sort(key=lambda x: x[2], reverse=True)
    
    # Return the best program
    best_program, is_federal, score = scored_programs[0]
    logger.info(f"Selected program '{best_program.name}' (score: {score}) for {insight.technologies}")
    
    return best_program, is_federal

def select_top_programs(programs: List[Tuple[object, bool]], insight: 'DiagnosticInsight', count: int) -> List[Tuple[object, bool]]:
    """
    Select the top N programs most specific to the improvement area.
    Returns list of (program, is_federal) tuples.
    """
    
    # Keywords that indicate program specificity for each technology
    specificity_keywords = {
        'electric_vehicles': ['electric vehicle', 'ev', 'vehicle', 'plug-in'],
        'heat_pumps': ['heat pump', 'electrification', 'hvac', 'heating', 'cooling'],
        'solar': ['solar', 'photovoltaic', 'pv', 'renewable energy'],
        'comprehensive': ['energy efficiency', 'weatherization', 'home improvement'],
        'hvac': ['hvac', 'heating', 'cooling', 'air conditioning'],
        'insulation': ['insulation', 'weatherization', 'envelope'],
        'appliances': ['appliance', 'refrigerator', 'washer', 'dryer'],
        'water_heating': ['water heat', 'hot water'],
        'lighting': ['lighting', 'led', 'lamp'],
        'energy_storage': ['battery', 'storage', 'backup power']
    }
    
    def score_program_specificity(program, is_federal):
        """Score how specific this program is to the insight's technologies"""
        score = 0
        program_text = (program.name + ' ' + (program.summary or '')).lower()
        
        # Check for keyword relevance with threshold-based scoring (no stacking)
        total_target_keywords = 0
        matched_keywords = 0
        
        for tech in insight.technologies:
            keywords = specificity_keywords.get(tech, [])
            total_target_keywords += len(keywords)
            for keyword in keywords:
                if keyword in program_text:
                    matched_keywords += 1
        
        # Threshold-based scoring instead of stacking
        if total_target_keywords > 0:
            match_percentage = matched_keywords / total_target_keywords
            if match_percentage >= 0.25:  # 25% or more keywords match
                score += 10
            elif matched_keywords > 0:  # At least one keyword matches
                score += 5
            
        # Prefer rebates and grants over loans and tax incentives for user experience
        program_type_preference = {
            'rebate': 5,
            'grant': 4, 
            'tax_credit': 3,
            'tax_deduction': 2,
            'loan': 1,
            'tax_incentive': 1,
            'other_financial': 0
        }
        score += program_type_preference.get(program.program_type, 0)
        
        # Add credibility boost for well-known programs
        if hasattr(program, 'credibility_boost') and program.credibility_boost:
            score += 5  # Modest boost for credible programs
        
        return score
    
    # Score all programs
    if not programs:
        return []
    
    scored_programs = [
        (program, is_federal, score_program_specificity(program, is_federal))
        for program, is_federal in programs
    ]
    
    # Sort by score (highest first) and return top N
    scored_programs.sort(key=lambda x: x[2], reverse=True)
    
    # Return the top programs (without scores)
    return [(program, is_federal) for program, is_federal, score in scored_programs[:count]]

def generate_diagnostic_recommendations(session_id: str, responses: Dict, footprint: Dict) -> List[str]:
    """
    Generate recommendations using diagnostic approach.
    Identifies user's biggest inefficiencies and targets those with relevant programs.
    """
    try:
        recommendations = []
        
        # Clear existing recommendations for this session before generating new ones
        logger.info(f"Clearing existing recommendations for session {session_id}")
        db.session.query(Recommendation).filter_by(session_id=session_id).delete()
        db.session.commit()
        
        # Get user's state
        intro_data = responses.get('introduction', {})
        state_code = intro_data.get('state', 'CA')
        if not state_code or len(state_code) != 2:
            state_code = 'CA'
        
        # Analyze user inefficiencies
        insights = analyze_user_inefficiencies(responses)
        
        if not insights:
            return ["Great job! Your energy usage appears efficient. Consider exploring additional energy-saving opportunities like LED lighting upgrades or smart thermostats."]
        
        logger.info(f"Found {len(insights)} diagnostic insights for session {session_id}")
        
        # Generate recommendations: up to 3 for most impactful, 1 each for others
        if insights:
            # Most impactful insight - show up to 3 programs
            top_insight = insights[0]
            programs = get_programs_for_technologies(state_code, top_insight.technologies, limit=10)
            
            if programs:
                # Get top 3 programs for the most impactful improvement
                top_programs = select_top_programs(programs, top_insight, min(3, len(programs)))
                
                for program, is_federal in top_programs:
                    # Format recommendation
                    location_text = "federal" if is_federal else f"{state_code} state"
                    rec_text = f"{top_insight.description}. The programs below can help cover the cost."
 
                    recommendations.append(rec_text)
                    
                    # Save to database with program reference
                    rec = Recommendation(
                        session_id=session_id,
                        recommendation_text=rec_text,
                        category=top_insight.category,
                        priority_score=min(top_insight.co2_savings_kg // 50, 100),
                        co2_savings_kg=top_insight.co2_savings_kg,
                        federal_program_id=program.id if is_federal else None,  # Now references dsire_federal_programs
                        state_program_id=program.id if not is_federal else None  # Now references dsire_state_programs
                    )
                    db.session.add(rec)
            
            # Other insights - show 1 program each for diversity
            for insight in insights[1:3]:  # Up to 2 more different categories
                programs = get_programs_for_technologies(state_code, insight.technologies, limit=10)
                
                if programs:
                    # Pick the best single program for this improvement area
                    program, is_federal = select_most_specific_program(programs, insight)
                    
                    # Format recommendation
                    location_text = "federal" if is_federal else f"{state_code} state"
                    rec_text = f"{insight.description}. The programs below can help cover the cost."
                    
                    recommendations.append(rec_text)
                    
                    # Save to database with program reference
                    rec = Recommendation(
                        session_id=session_id,
                        recommendation_text=rec_text,
                        category=insight.category,
                        priority_score=min(insight.co2_savings_kg // 50, 100),
                        co2_savings_kg=insight.co2_savings_kg,
                        federal_program_id=program.id if is_federal else None,  # Now references dsire_federal_programs
                        state_program_id=program.id if not is_federal else None  # Now references dsire_state_programs
                    )
                    db.session.add(rec)
        
        logger.info(f"Generated {len(recommendations)} diagnostic recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating diagnostic recommendations: {e}")
        return ["Consider exploring energy efficiency improvements to reduce your carbon footprint and save on utility costs."]