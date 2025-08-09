from models import db, EmissionFactor, VehicleMPG, ElectricityRate
import logging

logger = logging.getLogger(__name__)

def populate_initial_data():
    """Populate database with initial emission factors, vehicle data, and government programs."""
    
    try:
        # Check if data already exists
        if db.session.query(EmissionFactor).count() > 0:
            logger.info("Sample data already exists, skipping population")
            return
        
        logger.info("Populating initial data...")
        
        # Electricity emission factors for all 50 states + DC (kg CO2 per kWh)
        # Data from EPA eGRID 2021 - state grid emission factors
        state_electricity_factors = [
            {'state': 'AL', 'factor': 0.514, 'rate': 0.127},  # Alabama
            {'state': 'AK', 'factor': 0.450, 'rate': 0.234},  # Alaska  
            {'state': 'AZ', 'factor': 0.427, 'rate': 0.132},  # Arizona
            {'state': 'AR', 'factor': 0.476, 'rate': 0.103},  # Arkansas
            {'state': 'CA', 'factor': 0.259, 'rate': 0.280},  # California
            {'state': 'CO', 'factor': 0.590, 'rate': 0.124},  # Colorado
            {'state': 'CT', 'factor': 0.244, 'rate': 0.219},  # Connecticut
            {'state': 'DE', 'factor': 0.453, 'rate': 0.134},  # Delaware
            {'state': 'DC', 'factor': 0.450, 'rate': 0.139},  # District of Columbia
            {'state': 'FL', 'factor': 0.429, 'rate': 0.125},  # Florida
            {'state': 'GA', 'factor': 0.456, 'rate': 0.123},  # Georgia
            {'state': 'HI', 'factor': 0.623, 'rate': 0.334},  # Hawaii
            {'state': 'ID', 'factor': 0.079, 'rate': 0.105},  # Idaho
            {'state': 'IL', 'factor': 0.371, 'rate': 0.129},  # Illinois
            {'state': 'IN', 'factor': 0.726, 'rate': 0.134},  # Indiana
            {'state': 'IA', 'factor': 0.504, 'rate': 0.124},  # Iowa
            {'state': 'KS', 'factor': 0.554, 'rate': 0.134},  # Kansas
            {'state': 'KY', 'factor': 0.742, 'rate': 0.114},  # Kentucky
            {'state': 'LA', 'factor': 0.428, 'rate': 0.095},  # Louisiana
            {'state': 'ME', 'factor': 0.232, 'rate': 0.165},  # Maine
            {'state': 'MD', 'factor': 0.340, 'rate': 0.138},  # Maryland
            {'state': 'MA', 'factor': 0.264, 'rate': 0.234},  # Massachusetts
            {'state': 'MI', 'factor': 0.459, 'rate': 0.164},  # Michigan
            {'state': 'MN', 'factor': 0.446, 'rate': 0.136},  # Minnesota
            {'state': 'MS', 'factor': 0.477, 'rate': 0.115},  # Mississippi
            {'state': 'MO', 'factor': 0.656, 'rate': 0.112},  # Missouri
            {'state': 'MT', 'factor': 0.642, 'rate': 0.115},  # Montana
            {'state': 'NE', 'factor': 0.515, 'rate': 0.108},  # Nebraska
            {'state': 'NV', 'factor': 0.371, 'rate': 0.123},  # Nevada
            {'state': 'NH', 'factor': 0.181, 'rate': 0.207},  # New Hampshire
            {'state': 'NJ', 'factor': 0.245, 'rate': 0.163},  # New Jersey
            {'state': 'NM', 'factor': 0.526, 'rate': 0.133},  # New Mexico
            {'state': 'NY', 'factor': 0.266, 'rate': 0.198},  # New York
            {'state': 'NC', 'factor': 0.362, 'rate': 0.116},  # North Carolina
            {'state': 'ND', 'factor': 0.817, 'rate': 0.104},  # North Dakota
            {'state': 'OH', 'factor': 0.519, 'rate': 0.131},  # Ohio
            {'state': 'OK', 'factor': 0.578, 'rate': 0.108},  # Oklahoma
            {'state': 'OR', 'factor': 0.235, 'rate': 0.118},  # Oregon
            {'state': 'PA', 'factor': 0.336, 'rate': 0.143},  # Pennsylvania
            {'state': 'RI', 'factor': 0.358, 'rate': 0.244},  # Rhode Island
            {'state': 'SC', 'factor': 0.321, 'rate': 0.134},  # South Carolina
            {'state': 'SD', 'factor': 0.414, 'rate': 0.125},  # South Dakota
            {'state': 'TN', 'factor': 0.470, 'rate': 0.115},  # Tennessee
            {'state': 'TX', 'factor': 0.434, 'rate': 0.127},  # Texas
            {'state': 'UT', 'factor': 0.659, 'rate': 0.107},  # Utah
            {'state': 'VT', 'factor': 0.002, 'rate': 0.187},  # Vermont (almost all renewable)
            {'state': 'VA', 'factor': 0.364, 'rate': 0.126},  # Virginia
            {'state': 'WA', 'factor': 0.122, 'rate': 0.105},  # Washington
            {'state': 'WV', 'factor': 0.821, 'rate': 0.119},  # West Virginia
            {'state': 'WI', 'factor': 0.530, 'rate': 0.155},  # Wisconsin
            {'state': 'WY', 'factor': 0.769, 'rate': 0.113},  # Wyoming
        ]
        
        # Create emission factors for electricity
        for state_data in state_electricity_factors:
            factor = EmissionFactor(
                category='electricity',
                region=state_data['state'],
                co2_per_unit=state_data['factor'],
                unit='kg/kWh',
                source='EPA eGRID 2021'
            )
            db.session.add(factor)
            
            # Also add electricity rate
            rate = ElectricityRate(
                state=state_data['state'],
                avg_rate_per_kwh=state_data['rate'],
                grid_emission_factor=state_data['factor']
            )
            db.session.add(rate)
        
        # US average electricity factor
        us_avg_factor = EmissionFactor(
            category='electricity',
            region='US',
            co2_per_unit=0.386,
            unit='kg/kWh',
            source='EPA eGRID 2021'
        )
        db.session.add(us_avg_factor)
        
        # Other emission factors (national averages)
        other_factors = [
            # Natural gas (kg CO2 per therm) - same across all states
            {'category': 'natural_gas', 'region': 'US', 'co2_per_unit': 5.3, 'unit': 'kg/therm', 'source': 'EPA'},
            
            # Gasoline (kg CO2 per gallon) - national average
            {'category': 'gasoline', 'region': 'US', 'co2_per_unit': 8.89, 'unit': 'kg/gallon', 'source': 'EPA'},
            
            # Heating oil (kg CO2 per gallon) - national average
            {'category': 'heating_oil', 'region': 'US', 'co2_per_unit': 10.15, 'unit': 'kg/gallon', 'source': 'EPA'},
            
            # Diesel (kg CO2 per gallon)
            {'category': 'diesel', 'region': 'US', 'co2_per_unit': 10.19, 'unit': 'kg/gallon', 'source': 'EPA'},
        ]
        
        for factor_data in other_factors:
            factor = EmissionFactor(**factor_data)
            db.session.add(factor)
        
        # Sample Vehicle MPG Data (expanded with more vehicles)
        vehicle_mpg_data = [
            # 2023 Models
            {'year': 2023, 'make': 'Toyota', 'model': 'Camry', 'mpg_city': 28, 'mpg_highway': 39, 'mpg_combined': 32},
            {'year': 2023, 'make': 'Honda', 'model': 'Civic', 'mpg_city': 31, 'mpg_highway': 40, 'mpg_combined': 35},
            {'year': 2023, 'make': 'Ford', 'model': 'F-150', 'mpg_city': 20, 'mpg_highway': 24, 'mpg_combined': 22},
            {'year': 2023, 'make': 'Chevrolet', 'model': 'Silverado', 'mpg_city': 16, 'mpg_highway': 22, 'mpg_combined': 18},
            {'year': 2023, 'make': 'Tesla', 'model': 'Model 3', 'mpg_city': 142, 'mpg_highway': 132, 'mpg_combined': 137},
            {'year': 2023, 'make': 'Tesla', 'model': 'Model Y', 'mpg_city': 129, 'mpg_highway': 112, 'mpg_combined': 122},
            {'year': 2023, 'make': 'Toyota', 'model': 'Prius', 'mpg_city': 57, 'mpg_highway': 56, 'mpg_combined': 57},
            {'year': 2023, 'make': 'Honda', 'model': 'CR-V', 'mpg_city': 28, 'mpg_highway': 34, 'mpg_combined': 31},
            {'year': 2023, 'make': 'Subaru', 'model': 'Outback', 'mpg_city': 26, 'mpg_highway': 35, 'mpg_combined': 29},
            {'year': 2023, 'make': 'Nissan', 'model': 'Altima', 'mpg_city': 28, 'mpg_highway': 39, 'mpg_combined': 32},
            
            # 2022 Models
            {'year': 2022, 'make': 'Honda', 'model': 'Accord', 'mpg_city': 30, 'mpg_highway': 38, 'mpg_combined': 33},
            {'year': 2022, 'make': 'BMW', 'model': '3 Series', 'mpg_city': 26, 'mpg_highway': 36, 'mpg_combined': 30},
            {'year': 2022, 'make': 'Audi', 'model': 'A4', 'mpg_city': 27, 'mpg_highway': 35, 'mpg_combined': 30},
            {'year': 2022, 'make': 'Jeep', 'model': 'Grand Cherokee', 'mpg_city': 19, 'mpg_highway': 26, 'mpg_combined': 22},
            {'year': 2022, 'make': 'Ford', 'model': 'Escape', 'mpg_city': 28, 'mpg_highway': 34, 'mpg_combined': 30},
            
            # 2021 Models
            {'year': 2021, 'make': 'Mazda', 'model': 'CX-5', 'mpg_city': 25, 'mpg_highway': 31, 'mpg_combined': 27},
            {'year': 2021, 'make': 'Volkswagen', 'model': 'Jetta', 'mpg_city': 30, 'mpg_highway': 41, 'mpg_combined': 34},
            {'year': 2021, 'make': 'Hyundai', 'model': 'Elantra', 'mpg_city': 31, 'mpg_highway': 41, 'mpg_combined': 35},
            {'year': 2021, 'make': 'Kia', 'model': 'Optima', 'mpg_city': 27, 'mpg_highway': 37, 'mpg_combined': 31},
            
            # 2020 and older popular models
            {'year': 2020, 'make': 'Toyota', 'model': 'Corolla', 'mpg_city': 31, 'mpg_highway': 40, 'mpg_combined': 35},
            {'year': 2019, 'make': 'Jeep', 'model': 'Wrangler', 'mpg_city': 17, 'mpg_highway': 25, 'mpg_combined': 20},
            {'year': 2018, 'make': 'Ford', 'model': 'Focus', 'mpg_city': 26, 'mpg_highway': 36, 'mpg_combined': 30},
            {'year': 2017, 'make': 'Chevrolet', 'model': 'Malibu', 'mpg_city': 27, 'mpg_highway': 36, 'mpg_combined': 31},
        ]
        
        for vehicle_data in vehicle_mpg_data:
            # Only use fields that exist in VehicleMPG model
            clean_data = {
                'year': vehicle_data['year'],
                'make': vehicle_data['make'], 
                'model': vehicle_data['model'],
                'mpg_combined': vehicle_data['mpg_combined'],
                'vehicle_type': vehicle_data.get('vehicle_type', 'gas')
            }
            vehicle = VehicleMPG(**clean_data)
            db.session.add(vehicle)
        
        # Government Programs (comprehensive list with focus on major states)
        government_programs = [
            # Federal Programs
            {
                'name': 'Federal Solar Investment Tax Credit (ITC)',
                'description': '30% federal tax credit for solar panel installations through 2032, then steps down to 26% in 2033 and 22% in 2034',
                'program_type': 'tax_credit',
                'eligibility_criteria': 'Homeowners who install solar panels on their primary or secondary residence',
                'benefit_amount': '30% of installation cost',
                'state': None,
                'federal_flag': True,
                'active_flag': True
            },
            {
                'name': 'Federal Electric Vehicle Tax Credit',
                'description': 'Up to $7,500 tax credit for new electric vehicles that meet assembly and battery requirements',
                'program_type': 'tax_credit',
                'eligibility_criteria': 'Purchase of new qualifying electric vehicle, income and price limits apply',
                'benefit_amount': 'Up to $7,500',
                'state': None,
                'federal_flag': True,
                'active_flag': True
            },
            {
                'name': 'Federal Energy Efficient Home Improvement Credit',
                'description': '30% tax credit for heat pumps, water heaters, and other efficient equipment',
                'program_type': 'tax_credit',
                'eligibility_criteria': 'Installation of qualifying energy efficient equipment in primary residence',
                'benefit_amount': 'Up to $2,000 per year',
                'state': None,
                'federal_flag': True,
                'active_flag': True
            },
            {
                'name': 'Federal Weatherization Assistance Program',
                'description': 'Free weatherization services for low-income households',
                'program_type': 'assistance',
                'eligibility_criteria': 'Household income at or below 200% of federal poverty level',
                'benefit_amount': 'Up to $8,000 in services',
                'state': None,
                'federal_flag': True,
                'active_flag': True
            },
            
            # Arizona Programs (as specified in requirements)
            {
                'name': 'APS Heat Pump Rebate Program',
                'description': 'Arizona Public Service rebate for high-efficiency heat pump installations',
                'program_type': 'rebate',
                'eligibility_criteria': 'APS customers installing ENERGY STAR certified heat pumps with SEER 16+ and HSPF 9.0+',
                'benefit_amount': 'Up to $1,000',
                'state': 'AZ',
                'federal_flag': False,
                'active_flag': True
            },
            {
                'name': 'SRP Cool Cash for Heat Pumps',
                'description': 'Salt River Project rebate for heat pump installations in Phoenix area',
                'program_type': 'rebate',
                'eligibility_criteria': 'SRP customers installing qualifying heat pumps',
                'benefit_amount': 'Up to $1,200',
                'state': 'AZ',
                'federal_flag': False,
                'active_flag': True
            },
            {
                'name': 'Arizona Solar Equipment Sales Tax Exemption',
                'description': 'Exemption from state sales tax on solar equipment purchases',
                'program_type': 'tax_exemption',
                'eligibility_criteria': 'Purchase of solar equipment in Arizona',
                'benefit_amount': '100% sales tax exemption',
                'state': 'AZ',
                'federal_flag': False,
                'active_flag': True
            },
            
            # California Programs
            {
                'name': 'California Clean Vehicle Rebate',
                'description': 'Rebate for electric vehicle purchases in California',
                'program_type': 'rebate',
                'eligibility_criteria': 'California residents purchasing new electric vehicles, income limits apply',
                'benefit_amount': 'Up to $7,000',
                'state': 'CA',
                'federal_flag': False,
                'active_flag': True
            },
            {
                'name': 'California Solar Initiative',
                'description': 'Performance-based incentives for solar installations',
                'program_type': 'incentive',
                'eligibility_criteria': 'California residents installing grid-tied solar systems',
                'benefit_amount': 'Varies by utility',
                'state': 'CA',
                'federal_flag': False,
                'active_flag': True
            },
            
            # Texas Programs
            {
                'name': 'Texas Solar Rights Act',
                'description': 'Property tax exemption for solar installations',
                'program_type': 'tax_exemption',
                'eligibility_criteria': 'Texas residents installing solar energy systems',
                'benefit_amount': '100% property tax exemption',
                'state': 'TX',
                'federal_flag': False,
                'active_flag': True
            },
            
            # New York Programs
            {
                'name': 'NY-Sun Solar Incentive Program',
                'description': 'Incentives for solar installations in New York',
                'program_type': 'incentive',
                'eligibility_criteria': 'New York residents installing solar systems',
                'benefit_amount': 'Up to $5,000',
                'state': 'NY',
                'federal_flag': False,
                'active_flag': True
            },
            
            # Florida Programs
            {
                'name': 'Florida Solar and CHP Sales Tax Exemption',
                'description': 'Sales tax exemption for solar equipment in Florida',
                'program_type': 'tax_exemption',
                'eligibility_criteria': 'Purchase of solar equipment in Florida',
                'benefit_amount': '100% sales tax exemption',
                'state': 'FL',
                'federal_flag': False,
                'active_flag': True
            },
        ]
        
        for program_data in government_programs:
            program = GovernmentProgram(**program_data)
            db.session.add(program)
        
        # Commit all data
        db.session.commit()
        logger.info("Successfully populated initial data for all 50 states")
        
    except Exception as e:
        logger.error(f"Error populating initial data: {e}")
        db.session.rollback()
        raise