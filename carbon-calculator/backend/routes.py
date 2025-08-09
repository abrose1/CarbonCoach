from flask import Blueprint, request, jsonify
from models import db, Session, UserResponse, CarbonCalculation, Recommendation, CalculationBreakdown, DsireFederalProgram, DsireStateProgram
from llm_service import ConversationManager
from carbon_calc import calculate_home_emissions, calculate_transport_emissions, calculate_consumption_emissions, calculate_total_footprint
from diagnostic_recommendations import generate_diagnostic_recommendations
# Removed financial formatting imports - now handled by frontend
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)
conversation_manager = ConversationManager()

@api_bp.route('/session/<session_id>', methods=['GET'])
def get_or_create_session(session_id):
    """Get existing session or create new one if it doesn't exist."""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        session = db.session.query(Session).filter_by(session_id=session_id).first()
        
        if not session:
            session = Session(session_id=session_id)
            db.session.add(session)
            db.session.commit()
        else:
            # Update last active
            session.last_active = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'session_id': session.session_id,
            'current_section': session.current_section,
            'progress_pct': session.progress_pct,
            'completed': session.completed,
            'created_at': session.created_at.isoformat(),
            'last_active': session.last_active.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in get_or_create_session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/conversation', methods=['POST'])
def process_conversation():
    """Process user message and return assistant response."""
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data or 'message' not in data:
            return jsonify({'error': 'Missing session_id or message'}), 400
        
        session_id = data['session_id']
        user_message = data['message']
        
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Process message through conversation manager
        result = conversation_manager.process_message(session_id, user_message)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_conversation: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Sorry, I encountered an error. Please try again.'
        }), 500

@api_bp.route('/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get lightweight session status for dynamic welcome messages."""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        session = db.session.query(Session).filter_by(session_id=session_id).first()
        
        if not session:
            # New session - return defaults
            return jsonify({
                'current_section': 'introduction',
                'user_name': None,
                'next_missing_field': 'name',
                'progress_pct': 0
            })
        
        # Check if session is complete
        if session.current_section == 'results' or session.progress_pct >= 100:
            # Get user name
            responses = db.session.query(UserResponse).filter_by(session_id=session_id).all()
            user_name = None
            user_initials = ''
            name_response = next((r for r in responses if r.question_key == 'name'), None)
            if name_response:
                user_name = name_response.response_value.split(' ')[0] if name_response.response_value else None
                user_initials = conversation_manager._generate_initials(name_response.response_value)
            
            return jsonify({
                'current_section': session.current_section,
                'user_name': user_name,
                'user_initials': user_initials,
                'next_missing_field': None,  # Complete - no missing fields
                'progress_pct': session.progress_pct
            })
        
        # Get user responses
        responses = db.session.query(UserResponse).filter_by(session_id=session_id).all()
        
        # Get user name and initials
        user_name = None
        user_initials = ''
        name_response = next((r for r in responses if r.question_key == 'name'), None)
        if name_response:
            user_name = name_response.response_value.split(' ')[0] if name_response.response_value else None
            user_initials = conversation_manager._generate_initials(name_response.response_value)
        
        # Calculate current progress based on critical questions answered
        current_progress_pct = conversation_manager.calculate_question_progress(responses)
        
        # Update session progress if it has changed
        if session.progress_pct != current_progress_pct:
            session.progress_pct = current_progress_pct
            db.session.commit()
        
        # Determine next missing field
        next_missing_field = conversation_manager._get_next_missing_field(session.current_section, responses)
        
        return jsonify({
            'current_section': session.current_section,
            'user_name': user_name,
            'user_initials': user_initials,
            'next_missing_field': next_missing_field,
            'progress_pct': current_progress_pct
        })
        
    except Exception as e:
        logger.error(f"Error in get_session_status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/session/<session_id>/data', methods=['GET'])
def get_session_data(session_id):
    """Get all collected data for a session."""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        data = conversation_manager.get_session_data(session_id)
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in get_session_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/calculate', methods=['POST'])
def calculate_carbon_footprint():
    """Calculate carbon footprint based on collected session data."""
    try:
        logger.info("Starting carbon footprint calculation")
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'Missing session_id'}), 400
        
        session_id = data['session_id']
        
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Get session data
        logger.info(f"Getting session data for session_id: {session_id}")
        session_data = conversation_manager.get_session_data(session_id)
        
        if 'error' in session_data:
            logger.error(f"Session not found: {session_id}")
            return jsonify({'error': 'Session not found'}), 404
        
        logger.info("Session data retrieved successfully")
        responses = session_data['responses']
        logger.info(f"Response sections: {list(responses.keys())}")
        
        # Extract data for calculations
        intro_data = responses.get('introduction', {})
        home_data = responses.get('home_energy', {})
        transport_data = responses.get('transportation', {})
        consumption_data = responses.get('consumption', {})
        
        # Calculate home emissions
        logger.info("Starting home emissions calculation")
        logger.info(f"Home data: {home_data}")
        logger.info(f"Intro data: {intro_data}")
        
        try:
            home_emissions, home_breakdowns = calculate_home_emissions(
                sqft=home_data.get('square_footage', 1500),
                electric_bill=home_data.get('monthly_electricity', 100),  # Fixed field name
                heating_type=home_data.get('heating_type', 'gas'),
                heating_bill=home_data.get('heating_bill', 50),
                state=intro_data.get('state', 'CA'),
                household_size=intro_data.get('household_size', 1),
                session_id=session_id
            )
            logger.info(f"Home emissions calculated: {home_emissions} kg CO2")
        except Exception as e:
            logger.error(f"Error in home emissions calculation: {type(e).__name__}: {e}")
            raise
        
        # Calculate transport emissions
        vehicle_info = {
            'year': transport_data.get('vehicle_year'),
            'make': transport_data.get('vehicle_make'),
            'model': transport_data.get('vehicle_model')
        }
        
        flights_info = {
            'domestic': transport_data.get('domestic_flights', 0),
            'international': transport_data.get('international_flights', 0)
        }
        
        logger.info("Starting transport emissions calculation")
        logger.info(f"Vehicle info: {vehicle_info}")
        logger.info(f"Annual miles: {transport_data.get('annual_miles', 12000)}")
        logger.info(f"Flights info: {flights_info}")
        
        try:
            transport_emissions, transport_breakdowns = calculate_transport_emissions(
                vehicle_data=vehicle_info,
                annual_miles=transport_data.get('annual_miles', 12000),
                flights=flights_info,
                session_id=session_id
            )
            logger.info(f"Transport emissions calculated: {transport_emissions} kg CO2")
        except Exception as e:
            logger.error(f"Error in transport emissions calculation: {type(e).__name__}: {e}")
            raise
        
        # Calculate consumption emissions
        logger.info("Starting consumption emissions calculation")
        logger.info(f"Consumption data: {consumption_data}")
        
        try:
            consumption_emissions, consumption_breakdowns = calculate_consumption_emissions(
                diet_type=consumption_data.get('diet_type', 'moderate_meat'),
                shopping_frequency=consumption_data.get('shopping_frequency', 'moderate'),
                household_size=intro_data.get('household_size', 2),
                session_id=session_id
            )
            logger.info(f"Consumption emissions calculated: {consumption_emissions} kg CO2")
        except Exception as e:
            logger.error(f"Error in consumption emissions calculation: {type(e).__name__}: {e}")
            raise
        
        # Calculate total footprint
        logger.info("Calculating total footprint")
        try:
            footprint_summary = calculate_total_footprint(
                home_emissions, transport_emissions, consumption_emissions
            )
            logger.info(f"Total footprint calculated: {footprint_summary['total_kg_co2']} kg CO2")
        except Exception as e:
            logger.error(f"Error in total footprint calculation: {type(e).__name__}: {e}")
            raise
        
        # Save or update calculation in database
        logger.info("Saving/updating calculation in database")
        try:
            # Check if calculation already exists for this session
            existing_calculation = db.session.query(CarbonCalculation).filter_by(session_id=session_id).first()
            
            if existing_calculation:
                # Update existing calculation
                logger.info(f"Updating existing calculation with ID: {existing_calculation.id}")
                existing_calculation.total_annual_co2_kg = footprint_summary['total_kg_co2']
                existing_calculation.home_emissions = home_emissions
                existing_calculation.transport_emissions = transport_emissions
                existing_calculation.consumption_emissions = consumption_emissions
                existing_calculation.calculation_date = datetime.utcnow()
                calculation = existing_calculation
            else:
                # Create new calculation
                logger.info("Creating new calculation")
                calculation = CarbonCalculation(
                    session_id=session_id,
                    total_annual_co2_kg=footprint_summary['total_kg_co2'],
                    home_emissions=home_emissions,
                    transport_emissions=transport_emissions,
                    consumption_emissions=consumption_emissions
                )
                db.session.add(calculation)
            
            db.session.flush()  # Get the calculation ID
            logger.info(f"Calculation saved with ID: {calculation.id}")
        except Exception as e:
            logger.error(f"Error saving calculation to database: {type(e).__name__}: {e}")
            raise
        
        # Replace existing calculation breakdowns
        logger.info("Replacing calculation breakdowns")
        try:
            # Delete existing breakdowns for this session to avoid duplicates
            deleted_count = db.session.query(CalculationBreakdown).filter_by(session_id=session_id).delete()
            logger.info(f"Deleted {deleted_count} existing breakdown records")
            
            # Store new breakdowns
            all_breakdowns = home_breakdowns + transport_breakdowns + consumption_breakdowns
            logger.info(f"Total breakdowns to store: {len(all_breakdowns)}")
            
            for i, breakdown in enumerate(all_breakdowns):
                logger.info(f"Storing breakdown {i+1}: {breakdown['source']}")
                calc_breakdown = CalculationBreakdown(
                    session_id=session_id,
                    calculation_id=calculation.id,
                    emission_source=breakdown['source'],
                    value=breakdown['value'],
                    units=breakdown['units'],
                    calculation_method=breakdown['method']
                )
                db.session.add(calc_breakdown)
            logger.info("All breakdowns stored successfully")
        except Exception as e:
            logger.error(f"Error storing breakdowns: {type(e).__name__}: {e}")
            raise
        
        # Recommendations are now handled by the dedicated /api/recommendations endpoint
        
        # Commit all changes
        logger.info("Committing database transaction")
        try:
            db.session.commit()
            logger.info("Database transaction committed successfully")
        except Exception as e:
            logger.error(f"Error committing database transaction: {type(e).__name__}: {e}")
            db.session.rollback()
            raise
        
        return jsonify({
            'success': True,
            'footprint': footprint_summary,
            'breakdowns': {
                'home': home_breakdowns,
                'transport': transport_breakdowns,
                'consumption': consumption_breakdowns
            }
        })
        
    except Exception as e:
        logger.error(f"FATAL ERROR in calculate_carbon_footprint: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/calculations/<session_id>', methods=['GET'])
def get_calculations(session_id):
    """Get stored carbon calculations for a session."""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        calculations = db.session.query(CarbonCalculation).filter_by(
            session_id=session_id
        ).order_by(CarbonCalculation.calculation_date.desc()).all()
        
        if not calculations:
            return jsonify({'error': 'No calculations found for session'}), 404
        
        latest_calc = calculations[0]
        
        return jsonify({
            'session_id': session_id,
            'calculation_date': latest_calc.calculation_date.isoformat(),
            'total_annual_co2_kg': latest_calc.total_annual_co2_kg,
            'home_emissions': latest_calc.home_emissions,
            'transport_emissions': latest_calc.transport_emissions,
            'consumption_emissions': latest_calc.consumption_emissions,
            'total_tons_co2': latest_calc.total_annual_co2_kg / 1000
        })
        
    except Exception as e:
        logger.error(f"Error in get_calculations: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/recommendations/<session_id>', methods=['GET'])
def get_recommendations(session_id):
    """Get personalized recommendations for a session using the same logic as calculation."""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Get session data (same as calculation endpoint)
        session_data = conversation_manager.get_session_data(session_id)
        
        if 'error' in session_data:
            logger.error(f"Session not found: {session_id}")
            return jsonify({'error': 'Session not found'}), 404
        
        responses = session_data['responses']
        
        # Generate technology upgrade recommendations using diagnostic approach (same as calculation)
        try:
            tech_recommendations = generate_diagnostic_recommendations(session_id, responses, {})
            logger.info(f"Generated {len(tech_recommendations)} diagnostic recommendations")
        except Exception as e:
            logger.error(f"Error generating diagnostic recommendations: {type(e).__name__}: {e}")
            tech_recommendations = []
        
        # Generate lifestyle recommendations (same as calculation)
        try:
            from lifestyle_recommendations import generate_lifestyle_recommendations
            lifestyle_recommendations = generate_lifestyle_recommendations(session_id, responses, len(tech_recommendations))
            logger.info(f"Generated {len(lifestyle_recommendations)} lifestyle recommendations")
        except Exception as e:
            logger.error(f"Error generating lifestyle recommendations: {type(e).__name__}: {e}")
            lifestyle_recommendations = []
        
        # Get the stored technology recommendation objects with full metadata
        recommendations = db.session.query(Recommendation).filter_by(
            session_id=session_id
        ).order_by(Recommendation.priority_score.desc()).all()
        
        # Process stored technology recommendations
        tech_recs_structured = []
        
        for rec in recommendations:
            # Get the associated government program data from DSIRE tables
            government_program = None
            if rec.federal_program_id:
                federal_program = db.session.query(DsireFederalProgram).filter_by(id=rec.federal_program_id).first()
                if federal_program:
                    government_program = {
                        'id': federal_program.id,
                        'name': federal_program.name,
                        'program_type': federal_program.program_type,
                        'summary': federal_program.summary,
                        'website_url': federal_program.website_url,
                        'is_federal': True,
                        'state': None,
                        'credibility_boost': federal_program.credibility_boost,
                        # Raw DSIRE financial data for frontend formatting
                        'incentive_amount': federal_program.incentive_amount,
                        'percent_of_cost': federal_program.percent_of_cost,
                        'percent_of_cost_cap': federal_program.percent_of_cost_cap,
                        'per_unit_rate': federal_program.per_unit_rate,
                        'per_unit_type': federal_program.per_unit_type,
                        'incentive_summary': federal_program.incentive_summary
                    }
            elif rec.state_program_id:
                state_program = db.session.query(DsireStateProgram).filter_by(id=rec.state_program_id).first()
                if state_program:
                    government_program = {
                        'id': state_program.id,
                        'name': state_program.name,
                        'program_type': state_program.program_type,
                        'summary': state_program.summary,
                        'website_url': state_program.website_url,
                        'is_federal': False,
                        'state': state_program.state,
                        'credibility_boost': state_program.credibility_boost,
                        # Raw DSIRE financial data for frontend formatting
                        'incentive_amount': state_program.incentive_amount,
                        'percent_of_cost': state_program.percent_of_cost,
                        'percent_of_cost_cap': state_program.percent_of_cost_cap,
                        'per_unit_rate': state_program.per_unit_rate,
                        'per_unit_type': state_program.per_unit_type,
                        'incentive_summary': state_program.incentive_summary
                    }
            
            rec_data = {
                'recommendation_text': rec.recommendation_text,
                'category': rec.category,
                'priority_score': rec.priority_score,
                'co2_savings_kg': rec.co2_savings_kg,
                'government_program': government_program
            }
            
            # Only include technology categories from stored recommendations
            if rec.category in ['home_heating', 'home_efficiency', 'solar_opportunity', 'transportation']:
                tech_recs_structured.append(rec_data)
        
        # Convert fresh lifestyle recommendations to structured format
        lifestyle_recs_structured = []
        for lifestyle_rec in lifestyle_recommendations:
            # lifestyle_recommendations are LifestyleRecommendation objects, not strings
            if hasattr(lifestyle_rec, 'action_type'):
                # Use the structured LifestyleRecommendation object
                lifestyle_recs_structured.append({
                    'recommendation_text': lifestyle_rec.recommendation_text,
                    'category': lifestyle_rec.category,  # Use actual category: transportation, consumption, home_energy
                    'action_type': lifestyle_rec.action_type,  # Use action_type: reduce_flights, drive_less, etc.
                    'priority_score': lifestyle_rec.current_co2_kg,  # Use current CO2 impact for prioritization
                    'co2_savings_kg': lifestyle_rec.co2_savings_kg,  # Use actual CO2 savings
                    'cost_savings': lifestyle_rec.cost_savings,  # Annual cost savings in dollars (optional)
                    'government_program': None  # Lifestyle recommendations don't have government programs
                })
            else:
                # Fallback for legacy string format
                lifestyle_recs_structured.append({
                    'recommendation_text': str(lifestyle_rec),
                    'category': 'lifestyle',
                    'action_type': 'unknown',
                    'priority_score': 50,
                    'co2_savings_kg': None,
                    'government_program': None
                })
        
        # Group technology recommendations by category and calculate combined financial pills
        grouped_tech_recs = {}
        for rec in tech_recs_structured:
            category = rec['category']
            if category not in grouped_tech_recs:
                grouped_tech_recs[category] = []
            grouped_tech_recs[category].append(rec)
        
        # Frontend now handles all financial pill calculations using raw data
        
        # Return structured recommendation objects
        result = {
            'technology_upgrades': tech_recs_structured,
            'lifestyle_adjustments': lifestyle_recs_structured
        }
        
        return jsonify({'recommendations': result})
        
    except Exception as e:
        logger.error(f"Error in get_recommendations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})