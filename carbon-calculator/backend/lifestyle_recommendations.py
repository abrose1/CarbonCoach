#!/usr/bin/env python3
"""
Lifestyle Recommendations Engine
Generates actionable lifestyle changes based on existing carbon calculation breakdowns.
"""

from typing import Dict, List, Tuple, Optional
from models import db, VehicleMPG, CalculationBreakdown
from diagnostic_recommendations import BASELINES
import logging

logger = logging.getLogger(__name__)

# Cost estimation constants
DOMESTIC_FLIGHT_AVG_COST = 400  # Average cost of domestic round-trip flight
INTERNATIONAL_FLIGHT_AVG_COST = 1200  # Average cost of international round-trip flight
GAS_PRICE_PER_GALLON = 3.50  # Average gas price

class LifestyleRecommendation:
    """Represents a lifestyle change recommendation"""
    def __init__(self, category: str, action_type: str, current_co2_kg: int, 
                 co2_savings_kg: int, recommendation_text: str, cost_savings: int = None):
        self.category = category  # 'transportation', 'consumption', 'home_energy'
        self.action_type = action_type  # 'reduce_flights', 'drive_less', 'reduce_meat', etc.
        self.current_co2_kg = current_co2_kg  # Current annual CO2 impact
        self.co2_savings_kg = co2_savings_kg  # Annual CO2 savings potential from recommendation
        self.recommendation_text = recommendation_text  # User-friendly recommendation
        self.cost_savings = cost_savings  # Annual cost savings in dollars (optional)

def get_latest_breakdown_data(session_id: str) -> Dict[str, float]:
    """
    Get the most recent breakdown data for each emission source for a session.
    Returns dict mapping emission_source to CO2 value.
    """
    try:
        # Get the most recent calculation_id for this session
        latest_calculation = db.session.query(CalculationBreakdown.calculation_id).filter_by(
            session_id=session_id
        ).order_by(CalculationBreakdown.id.desc()).first()
        
        if not latest_calculation:
            return {}
        
        # Get all breakdowns for the latest calculation, taking most recent for each source
        breakdowns = db.session.query(CalculationBreakdown).filter_by(
            session_id=session_id,
            calculation_id=latest_calculation.calculation_id
        ).all()
        
        # Build dict with most recent value for each emission source
        breakdown_data = {}
        for breakdown in breakdowns:
            # Use the latest entry for each emission source
            breakdown_data[breakdown.emission_source] = breakdown.value
            
        logger.info(f"Retrieved {len(breakdown_data)} breakdown entries for session {session_id}")
        return breakdown_data
        
    except Exception as e:
        logger.error(f"Error retrieving breakdown data: {e}")
        return {}

def analyze_lifestyle_opportunities(session_id: str, responses: Dict) -> List[LifestyleRecommendation]:
    """
    Analyze breakdown data to identify lifestyle change opportunities.
    Returns list of recommendations ordered by current CO2 impact.
    """
    recommendations = []
    
    # Get the latest breakdown data
    breakdown_data = get_latest_breakdown_data(session_id)
    if not breakdown_data:
        logger.warning(f"No breakdown data found for session {session_id}")
        return []
    
    intro_data = responses.get('introduction', {})
    home_data = responses.get('home_energy', {})
    transport_data = responses.get('transportation', {})
    consumption_data = responses.get('consumption', {})
    
    # 1. Check flight usage
    flight_rec = analyze_flight_usage_from_breakdown(breakdown_data, transport_data)
    if flight_rec:
        recommendations.append(flight_rec)
    
    # 2. Check driving habits  
    driving_rec = analyze_driving_from_breakdown(breakdown_data, transport_data)
    if driving_rec:
        recommendations.append(driving_rec)
    
    # 3. Check energy usage
    energy_rec = analyze_energy_from_breakdown(breakdown_data, home_data, intro_data)
    if energy_rec:
        recommendations.append(energy_rec)
    
    # 4. Check meat consumption
    diet_rec = analyze_diet_from_breakdown(breakdown_data, consumption_data)
    if diet_rec:
        recommendations.append(diet_rec)
    
    # 5. Check shopping habits
    shopping_rec = analyze_shopping_from_breakdown(breakdown_data, consumption_data)
    if shopping_rec:
        recommendations.append(shopping_rec)
    
    # Sort by current CO2 impact (highest current emissions first)
    recommendations.sort(key=lambda x: x.current_co2_kg, reverse=True)
    
    return recommendations

def analyze_flight_usage_from_breakdown(breakdown_data: Dict[str, float], transport_data: Dict) -> Optional[LifestyleRecommendation]:
    """Analyze flight usage from breakdown data"""
    domestic_flights = transport_data.get('domestic_flights', 0)
    international_flights = transport_data.get('international_flights', 0)
    
    # Get current flight emissions from breakdown
    domestic_co2 = breakdown_data.get('Domestic Flights', 0)
    international_co2 = breakdown_data.get('International Flights', 0)
    total_flight_co2 = domestic_co2 + international_co2
    
    if total_flight_co2 == 0:
        return None
    
    # Check thresholds: >3 domestic OR >1 international
    high_domestic = domestic_flights > 3
    high_international = international_flights > 1
    
    if high_domestic and high_international:
        # Both high - prioritize international reduction (~1200 kg CO2 per flight)
        co2_savings = 1200
        rec_text = f"Your {domestic_flights} domestic and {international_flights} international flights produce {total_flight_co2:,.0f} kg CO2 annually. Consider taking one less international round trip each year - perhaps take longer but fewer trips abroad. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='transportation',
            action_type='reduce_flights',
            current_co2_kg=int(total_flight_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text,
            cost_savings=INTERNATIONAL_FLIGHT_AVG_COST  # Saving from not taking 1 international flight
        )
    
    elif high_international:
        # Only international high
        co2_savings = 1200
        rec_text = f"Your {international_flights} international flights produce {total_flight_co2:,.0f} kg CO2 annually. Consider taking one less round trip each year- perhaps take longer but fewer trips abroad. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='transportation',
            action_type='reduce_international_flights',
            current_co2_kg=int(total_flight_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text,
            cost_savings=INTERNATIONAL_FLIGHT_AVG_COST
        )
    
    elif high_domestic:
        # Only domestic high
        co2_savings = 450
        rec_text = f"Your {domestic_flights} domestic flights produce {total_flight_co2:,.0f} kg CO2 annually. Consider taking one less round trip each year - perhaps combine trips or explore closer destinations. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='transportation',
            action_type='reduce_domestic_flights',
            current_co2_kg=int(total_flight_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text,
            cost_savings=DOMESTIC_FLIGHT_AVG_COST
        )
    
    return None

def analyze_driving_from_breakdown(breakdown_data: Dict[str, float], transport_data: Dict) -> Optional[LifestyleRecommendation]:
    """Analyze driving habits from breakdown data"""
    annual_miles = transport_data.get('annual_miles', 0)
    vehicle_year = transport_data.get('vehicle_year')
    vehicle_make = transport_data.get('vehicle_make', '').lower()
    vehicle_model = transport_data.get('vehicle_model', '').lower()
    
    # Find vehicle emissions in breakdown data
    vehicle_co2 = 0
    for source, value in breakdown_data.items():
        if source.startswith('Vehicle (') and vehicle_year and str(vehicle_year) in source:
            vehicle_co2 = value
            break
    
    if vehicle_co2 == 0 or not annual_miles:
        return None
    
    # Check if driving above 1.25x average
    if annual_miles <= BASELINES['annual_miles_per_driver'] * 1.25:
        return None
    
    # Get vehicle MPG using same logic as diagnostic recommendations
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
    
    # Only recommend if vehicle gets <50 MPG
    if mpg >= 50:
        return None
    
    # Calculate 10% driving reduction savings
    co2_savings = int(vehicle_co2 * 0.1)
    miles_to_reduce = int(annual_miles * 0.1)
    
    # Calculate cost savings from reduced gas usage
    gas_savings_per_year = int((miles_to_reduce / mpg) * GAS_PRICE_PER_GALLON)
    
    rec_text = f"Your {vehicle_year} {vehicle_make} {vehicle_model} produces {vehicle_co2:,.0f} kg CO2 annually from {annual_miles:,} miles of driving. Consider reducing your driving by 10% ({miles_to_reduce:,} miles) through carpooling, combining errands, or working from home more often. This could save around {co2_savings} kg CO2 annually."
    
    return LifestyleRecommendation(
        category='transportation',
        action_type='drive_less',
        current_co2_kg=int(vehicle_co2),
        co2_savings_kg=co2_savings,
        recommendation_text=rec_text,
        cost_savings=gas_savings_per_year
    )

def analyze_energy_from_breakdown(breakdown_data: Dict[str, float], home_data: Dict, intro_data: Dict) -> Optional[LifestyleRecommendation]:
    """Analyze energy usage from breakdown data"""
    electricity_bill = home_data.get('monthly_electricity', 0)
    square_footage = home_data.get('square_footage', 1500)
    state = intro_data.get('state', 'CA')
    household_size = intro_data.get('household_size', 2)
    
    # Get electricity emissions from breakdown
    electricity_co2 = breakdown_data.get('Electricity', 0)
    
    if electricity_co2 == 0 or not electricity_bill:
        return None
    
    # Calculate expected cost (same logic as diagnostic recommendations)
    state_baseline_per_person = BASELINES['electricity_monthly_by_state'].get(state, 58)
    expected_cost_household = state_baseline_per_person * household_size
    
    if square_footage > 0:
        sqft_per_person = square_footage / household_size
        sqft_multiplier = sqft_per_person / BASELINES['square_feet_per_person']
        expected_cost_household = expected_cost_household * sqft_multiplier
    
    cost_ratio = electricity_bill / expected_cost_household if expected_cost_household > 0 else 1
    
    # Check for high usage (>1.8x baseline)
    if cost_ratio <= 1.8:
        return None
    
    # Calculate 10% energy reduction savings
    co2_savings = int(electricity_co2 * 0.1)
    monthly_savings = int(electricity_bill * 0.1)
    annual_savings = monthly_savings * 12
    
    rec_text = f"Your electricity usage produces {electricity_co2:,.0f} kg CO2 annually, with bills {(cost_ratio-1)*100:.0f}% above typical usage for your area. Consider reducing energy use by 10% through adjusting your thermostat, using LED bulbs, and unplugging devices when not in use. This could save around {co2_savings} kg CO2 and ${monthly_savings}/month."
    
    return LifestyleRecommendation(
        category='home_energy',
        action_type='reduce_energy_use',
        current_co2_kg=int(electricity_co2),
        co2_savings_kg=co2_savings,
        recommendation_text=rec_text,
        cost_savings=annual_savings
    )

def analyze_diet_from_breakdown(breakdown_data: Dict[str, float], consumption_data: Dict) -> Optional[LifestyleRecommendation]:
    """Analyze meat consumption from breakdown data"""
    diet_type = consumption_data.get('diet_type', 'moderate_meat')
    
    # Get diet emissions from breakdown
    diet_co2 = 0
    for source, value in breakdown_data.items():
        if source.startswith('Diet ('):
            diet_co2 = value
            break
    
    if diet_co2 == 0:
        return None
    
    # Only recommend for heavy and moderate meat eaters
    if diet_type == 'heavy_meat':
        # Heavy → Light meat: save 1400 kg CO2
        co2_savings = 1400
        rec_text = f"Your heavy meat diet produces {diet_co2:,.0f} kg CO2 annually. Consider eating meat just a few times per week. Try having 'Meatless Monday' or exploring plant-based proteins like beans, lentils, and tofu for some meals. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='consumption',
            action_type='reduce_meat_consumption',
            current_co2_kg=int(diet_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text
        )
    
    elif diet_type == 'moderate_meat':
        # Moderate → Light meat: save 600 kg CO2
        co2_savings = 600
        rec_text = f"Your meat diet produces {diet_co2:,.0f} kg CO2 annually. Consider eating meat just a few times per week. Try having 'Meatless Monday' or exploring plant-based proteins like beans, lentils, and tofu for some meals. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='consumption',
            action_type='reduce_meat_consumption',
            current_co2_kg=int(diet_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text
        )
    
    return None

def analyze_shopping_from_breakdown(breakdown_data: Dict[str, float], consumption_data: Dict) -> Optional[LifestyleRecommendation]:
    """Analyze shopping habits from breakdown data"""
    shopping_frequency = consumption_data.get('shopping_frequency', 'moderate')
    
    # Get shopping emissions from breakdown
    shopping_co2 = 0
    for source, value in breakdown_data.items():
        if 'Consumer goods' in source or 'consumer goods' in source:
            shopping_co2 = value
            break
    
    if shopping_co2 == 0:
        return None
    
    if shopping_frequency == 'very_high':
        # Very high → Moderate: save 2000 kg CO2
        co2_savings = 2000
        rec_text = f"Your very frequent shopping produces {shopping_co2:,.0f} kg CO2 annually. Consider reducing to moderate shopping by waiting to bundle online purchases, buying higher-quality items that last longer, and asking yourself if you really need new items before purchasing. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='consumption',
            action_type='reduce_shopping_frequency',
            current_co2_kg=int(shopping_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text
        )
    
    elif shopping_frequency == 'high':
        # High → Moderate: save 1000 kg CO2
        co2_savings = 1000
        rec_text = f"Your frequent shopping produces {shopping_co2:,.0f} kg CO2 annually. Consider reducing to moderate shopping by waiting a day before making non-essential purchases, focusing on experiences over things, and buying second-hand when possible. This could save around {co2_savings} kg CO2 annually."
        
        return LifestyleRecommendation(
            category='consumption',
            action_type='reduce_shopping_frequency',
            current_co2_kg=int(shopping_co2),
            co2_savings_kg=co2_savings,
            recommendation_text=rec_text
        )
    
    return None

def generate_lifestyle_recommendations(session_id: str, responses: Dict, existing_tech_rec_count: int) -> List[LifestyleRecommendation]:
    """
    Generate lifestyle recommendations based on breakdown data.
    
    Args:
        session_id: User session ID
        responses: User survey responses
        existing_tech_rec_count: Number of existing technology upgrade recommendations
    
    Returns:
        List of LifestyleRecommendation objects
    """
    try:
        # Get all lifestyle opportunities (ranked by current CO2 impact)
        lifestyle_insights = analyze_lifestyle_opportunities(session_id, responses)
        
        if not lifestyle_insights:
            return []
        
        # Determine how many to show based on existing tech recommendations
        if existing_tech_rec_count >= 3:
            # Show only top lifestyle change
            selected_insights = lifestyle_insights[:1]
        else:
            # Show up to 3 lifestyle improvements
            selected_insights = lifestyle_insights[:3]
        
        logger.info(f"Generated {len(selected_insights)} lifestyle recommendations for session {session_id}")
        
        # Return the full LifestyleRecommendation objects (not just text)
        return selected_insights
        
    except Exception as e:
        logger.error(f"Error generating lifestyle recommendations: {e}")
        return []