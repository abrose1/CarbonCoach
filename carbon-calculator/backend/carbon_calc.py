from models import db, EmissionFactor, VehicleMPG, ElectricityRate, CalculationBreakdown
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)

def calculate_home_emissions(sqft: float, electric_bill: float, heating_type: str, 
                           heating_bill: float, state: str, household_size: int = 1, session_id: str = None) -> Tuple[float, List[Dict]]:
    """
    Calculate home energy emissions based on square footage, bills, and heating type.
    Returns tuple of (total_emissions_kg_co2, breakdown_list)
    """
    breakdowns = []
    total_emissions = 0.0
    
    # Ensure numeric inputs
    try:
        sqft = float(sqft)
        electric_bill = float(electric_bill)
        heating_bill = float(heating_bill)
    except (ValueError, TypeError):
        logger.error(f"Invalid numeric inputs: sqft={sqft}, electric_bill={electric_bill}, heating_bill={heating_bill}")
        return 0.0, []
    
    try:
        # Get state electricity emission factor
        electricity_factor = db.session.query(EmissionFactor).filter_by(
            category='electricity', region=state
        ).first()
        
        if not electricity_factor:
            # Fall back to US average
            electricity_factor = db.session.query(EmissionFactor).filter_by(
                category='electricity', region='US'
            ).first()
        
        # Calculate electricity emissions from bill
        # Assume average $0.13/kWh if no specific rate found
        avg_kwh_rate = 0.13
        electricity_rate = db.session.query(ElectricityRate).filter_by(state=state).first()
        if electricity_rate:
            avg_kwh_rate = electricity_rate.avg_rate_per_kwh
        
        # Divide electricity bill by household size (shared cost)
        individual_electric_bill = electric_bill / household_size
        monthly_kwh = individual_electric_bill / avg_kwh_rate
        annual_kwh = monthly_kwh * 12
        
        if electricity_factor:
            electricity_emissions = annual_kwh * electricity_factor.co2_per_unit
            total_emissions += electricity_emissions
            
            breakdowns.append({
                'source': 'Electricity',
                'value': electricity_emissions,
                'units': 'kg CO2',
                'method': f'${electric_bill}/month ÷ {household_size} people = ${individual_electric_bill:.2f}/month → {annual_kwh:.1f} kWh/year × {electricity_factor.co2_per_unit} kg CO2/kWh'
            })
        
        # Calculate heating emissions based on type
        heating_emissions = 0.0
        if heating_type.lower() in ['gas', 'natural gas']:
            # Natural gas heating - convert bill to therms (divide by household size)
            avg_therm_rate = 1.20  # $1.20 per therm average
            individual_heating_bill = heating_bill / household_size
            monthly_therms = individual_heating_bill / avg_therm_rate
            annual_therms = monthly_therms * 12
            
            gas_factor = db.session.query(EmissionFactor).filter_by(
                category='natural_gas', region=state
            ).first()
            if not gas_factor:
                gas_factor = db.session.query(EmissionFactor).filter_by(
                    category='natural_gas', region='US'
                ).first()
            
            if gas_factor:
                heating_emissions = annual_therms * gas_factor.co2_per_unit
                breakdowns.append({
                    'source': 'Natural Gas Heating',
                    'value': heating_emissions,
                    'units': 'kg CO2',
                    'method': f'${heating_bill}/month ÷ {household_size} people = ${individual_heating_bill:.2f}/month → {annual_therms:.1f} therms/year × {gas_factor.co2_per_unit} kg CO2/therm'
                })
        
        elif heating_type.lower() in ['oil', 'heating oil']:
            # Heating oil - estimate gallons from bill (divide by household size)
            avg_oil_rate = 3.50  # $3.50 per gallon average
            individual_heating_bill = heating_bill / household_size
            monthly_gallons = individual_heating_bill / avg_oil_rate
            annual_gallons = monthly_gallons * 12
            
            oil_factor = db.session.query(EmissionFactor).filter_by(
                category='heating_oil', region='US'
            ).first()
            
            if oil_factor:
                heating_emissions = annual_gallons * oil_factor.co2_per_unit
                breakdowns.append({
                    'source': 'Heating Oil',
                    'value': heating_emissions,
                    'units': 'kg CO2',
                    'method': f'{annual_gallons:.1f} gallons/year × {oil_factor.co2_per_unit} kg CO2/gallon'
                })
        
        elif heating_type.lower() in ['electric', 'heat pump']:
            # Electric heating - add to electricity usage (divide by household size)
            individual_heating_bill = heating_bill / household_size
            monthly_heating_kwh = individual_heating_bill / avg_kwh_rate
            annual_heating_kwh = monthly_heating_kwh * 12
            
            if electricity_factor:
                heating_emissions = annual_heating_kwh * electricity_factor.co2_per_unit
                breakdowns.append({
                    'source': 'Electric Heating',
                    'value': heating_emissions,
                    'units': 'kg CO2',
                    'method': f'{annual_heating_kwh:.1f} kWh/year × {electricity_factor.co2_per_unit} kg CO2/kWh'
                })
        
        total_emissions += heating_emissions
        
        # Note: Breakdowns will be stored by the calling function after calculation is saved
        
        return total_emissions, breakdowns
        
    except Exception as e:
        logger.error(f"Error calculating home emissions: {e}")
        return 0.0, []

def calculate_transport_emissions(vehicle_data: Dict, annual_miles: float, 
                                flights: Dict, session_id: str = None) -> Tuple[float, List[Dict]]:
    """
    Calculate transportation emissions from vehicles and flights.
    Returns tuple of (total_emissions_kg_co2, breakdown_list)
    """
    breakdowns = []
    total_emissions = 0.0
    
    try:
        # Calculate primary vehicle emissions
        if vehicle_data and annual_miles > 0:
            year = vehicle_data.get('year')
            make = vehicle_data.get('make', '').lower()
            model = vehicle_data.get('model', '').lower()
            
            # Look up vehicle MPG
            vehicle_mpg = db.session.query(VehicleMPG).filter(
                VehicleMPG.year == year,
                VehicleMPG.make.ilike(f'%{make}%'),
                VehicleMPG.model.ilike(f'%{model}%')
            ).first()
            
            # Default MPG if not found
            mpg_combined = vehicle_mpg.mpg_combined if vehicle_mpg else 25.0
            
            # Calculate gallons used
            annual_gallons = annual_miles / mpg_combined
            
            # Get gasoline emission factor
            gas_factor = db.session.query(EmissionFactor).filter_by(
                category='gasoline', region='US'
            ).first()
            
            if gas_factor:
                vehicle_emissions = annual_gallons * gas_factor.co2_per_unit
                total_emissions += vehicle_emissions
                
                breakdowns.append({
                    'source': f'Vehicle ({year} {make.title()} {model.title()})',
                    'value': vehicle_emissions,
                    'units': 'kg CO2',
                    'method': f'{annual_miles:.0f} miles ÷ {mpg_combined:.1f} MPG × {gas_factor.co2_per_unit} kg CO2/gallon'
                })
        
        # Calculate flight emissions
        domestic_flights = flights.get('domestic', 0)
        international_flights = flights.get('international', 0)
        
        # Average emission factors for flights (kg CO2 per flight)
        domestic_flight_factor = 400  # ~400 kg CO2 per domestic round trip
        international_flight_factor = 1500  # ~1500 kg CO2 per international round trip
        
        if domestic_flights > 0:
            domestic_emissions = domestic_flights * domestic_flight_factor
            total_emissions += domestic_emissions
            
            breakdowns.append({
                'source': 'Domestic Flights',
                'value': domestic_emissions,
                'units': 'kg CO2',
                'method': f'{domestic_flights} flights × {domestic_flight_factor} kg CO2/flight'
            })
        
        if international_flights > 0:
            international_emissions = international_flights * international_flight_factor
            total_emissions += international_emissions
            
            breakdowns.append({
                'source': 'International Flights',
                'value': international_emissions,
                'units': 'kg CO2',
                'method': f'{international_flights} flights × {international_flight_factor} kg CO2/flight'
            })
        
        # Note: Breakdowns will be stored by the calling function after calculation is saved
        
        return total_emissions, breakdowns
        
    except Exception as e:
        logger.error(f"Error calculating transport emissions: {e}")
        return 0.0, []

def calculate_consumption_emissions(diet_type: str, shopping_frequency: str, 
                                  household_size: int = 1, session_id: str = None) -> Tuple[float, List[Dict]]:
    """
    Calculate consumption emissions from diet and shopping habits.
    Returns tuple of (total_emissions_kg_co2, breakdown_list)
    """
    breakdowns = []
    total_emissions = 0.0
    
    try:
        # Diet emission factors (kg CO2 per person per year)
        diet_factors = {
            'heavy_meat': 3300,      # Heavy meat consumption (multiple times per day)
            'moderate_meat': 2500,   # Moderate meat consumption (once per day)  
            'light_meat': 1900,      # Light meat consumption (few times per week)
            'vegetarian': 1600,      # Vegetarian diet (no meat)
            'vegan': 1200           # Vegan diet (no animal products)
        }
        
        diet_key = diet_type.lower().replace(' ', '_').replace('-', '_')
        if diet_key not in diet_factors:
            diet_key = 'moderate_meat'  # Default
        
        diet_emissions = diet_factors[diet_key]  # Per individual, not household
        total_emissions += diet_emissions
        
        breakdowns.append({
            'source': f'Diet ({diet_type.title()})',
            'value': diet_emissions,
            'units': 'kg CO2',
            'method': f'{diet_factors[diet_key]} kg CO2/person/year (individual consumption)'
        })
        
        # Shopping emission factors (kg CO2 per person per year)
        shopping_factors = {
            'low': 500,        # Minimal consumption
            'moderate': 1000,   # Average consumption
            'high': 2000,      # High consumption
            'very_high': 3000  # Very high consumption
        }
        
        shopping_key = shopping_frequency.lower().replace(' ', '_')
        if shopping_key not in shopping_factors:
            shopping_key = 'moderate'  # Default
        
        shopping_emissions = shopping_factors[shopping_key]  # Per individual, not household
        total_emissions += shopping_emissions
        
        breakdowns.append({
            'source': f'Consumer goods ({shopping_frequency.title()})',
            'value': shopping_emissions,
            'units': 'kg CO2',
            'method': f'{shopping_factors[shopping_key]} kg CO2/person/year (individual consumption)'
        })
        
        # Note: Breakdowns will be stored by the calling function after calculation is saved
        
        return total_emissions, breakdowns
        
    except Exception as e:
        logger.error(f"Error calculating consumption emissions: {e}")
        return 0.0, []

def calculate_total_footprint(home_emissions: float, transport_emissions: float, 
                            consumption_emissions: float) -> Dict:
    """
    Calculate total carbon footprint and provide context.
    Returns dictionary with totals and comparisons.
    """
    total_annual_kg = home_emissions + transport_emissions + consumption_emissions
    total_annual_tons = total_annual_kg / 1000
    
    # US average is about 16 tons CO2 per person per year
    us_average_tons = 16.0
    percentage_of_average = (total_annual_tons / us_average_tons) * 100
    
    return {
        'total_kg_co2': total_annual_kg,
        'total_tons_co2': total_annual_tons,
        'home_emissions': home_emissions,
        'transport_emissions': transport_emissions,
        'consumption_emissions': consumption_emissions,
        'us_average_tons': us_average_tons,
        'percentage_of_us_average': percentage_of_average,
        'emissions_breakdown': {
            'home_percent': (home_emissions / total_annual_kg * 100) if total_annual_kg > 0 else 0,
            'transport_percent': (transport_emissions / total_annual_kg * 100) if total_annual_kg > 0 else 0,
            'consumption_percent': (consumption_emissions / total_annual_kg * 100) if total_annual_kg > 0 else 0
        }
    }