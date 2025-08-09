import anthropic
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from models import db, Session, UserResponse, ConversationLog

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self):
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"
        
        # Conversation flow sections
        self.sections = ['introduction', 'home_energy', 'transportation', 'consumption', 'results']
        
        # All required fields for progress calculation (19 total)
        self.all_required_fields = [
            # introduction (5 fields)
            'name', 'city', 'state', 'household_size', 'housing_type',
            # home_energy (5 fields)  
            'square_footage', 'monthly_electricity', 'heating_type', 'heating_bill', 'solar_panels',
            # transportation (6 fields)
            'vehicle_year', 'vehicle_make', 'vehicle_model', 'annual_miles', 'domestic_flights', 'international_flights',
            # consumption (2 fields)
            'diet_type', 'shopping_frequency'
        ]
    
    def _get_client(self):
        """Initialize Anthropic client lazily when first needed"""
        if self.client is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                raise
        return self.client
    
    def calculate_question_progress(self, responses: List) -> int:
        """Calculate progress percentage based on questions answered (0-100)."""
        if not responses:
            return 0
            
        # Get all answered question keys
        answered_keys = {r.question_key for r in responses}
        
        # Count how many required fields have been answered
        answered_count = sum(1 for field in self.all_required_fields if field in answered_keys)
        
        # Calculate percentage (round to nearest integer)
        progress_pct = int(round((answered_count / len(self.all_required_fields)) * 100))
        
        return min(progress_pct, 100)  # Cap at 100%
    
    def get_system_prompt(self, current_section: str, user_responses: List[Dict] = None, db_responses: List = None) -> str:
        """Generate system prompt based on current conversation section and previous responses."""
        
        base_prompt = """You are a friendly carbon footprint calculator assistant. Your role is to guide users through calculating their carbon emissions and provide personalized recommendations.

GUARDRAILS:
- Stay focused on carbon footprint calculation topics only
- For off-topic questions, respond: "I'm sorry, but as a prototype I cannot factor that into your carbon emissions calculation. Let me help you with [current section topic]."
- Ask follow-up questions when you need clarification, but try to avoid asking questions that don't directly address the required data fields
- Be encouraging and supportive about environmental action
- Each message you send should clearly ask a question to find out the answer for the next required answer field
- When available in square brackets in REQUIRED DATA FIELD NAMES AND TYPES, we should suggest those options and try and match the user's response to one of them when sending data back to the database
- If you do list options use dashes instead of numbered lists, and use plain-text but don't stray too far from the actual options or try and guess what they mean
- Provide specific, actionable recommendations

CONVERSATION STRUCTURE:
You are currently in the "{section}" section. Guide the user through these topics systematically:

1. Introduction: Name, location (city, state), household size, housing type
2. Home Energy: Square footage, electricity bill, heating type and bill, solar panels
3. Transportation: Primary vehicle details, annual miles, flights
4. Consumption: Diet type (amount of meat), online shopping frequency (specifically online)
5. Results: Carbon footprint breakdown and recommendations

RESPONSE FORMAT:
Always respond in JSON format:
{{
    "message": "Your conversational response here",
    "data_collected": {{"key": "value"}},
    "section_complete": false,
    "next_section": "section_name or null",
    "needs_clarification": ["list of items needing clarification"]
}}

REQUIRED DATA FIELD NAMES AND TYPES:
Use these exact field names only - never create new ones. The content in parentheses is the expected data type.
If options are listed in square brackets that's an array of the values/options

Introduction section:
- "name" (text)
- "city" (text)
- "state" (use 2-letter codes)
- "household_size" (number)
- "housing_type" [house, apartment, condo]

Home Energy section:
- "square_footage" (number)
- "monthly_electricity" (number in dollars)
- "heating_type" [gas, electric, heat_pump, oil]
- "heating_bill" (number in dollars, use 0 if included in electricity)
- "solar_panels" (boolean)

Transportation section:
- "vehicle_year" (number)
- "vehicle_make" (text)
- "vehicle_model" (text)
- "annual_miles" (number)
- "domestic_flights" (number per year)
- "international_flights" (number per year)

Consumption section:
- "diet_type" [vegan, vegetarian, light_meat, moderate_meat, heavy_meat]
- "shopping_frequency" [low, moderate, high, very_high]

TONE: Friendly but professional. Ask follow-up questions when needed."""

        # Add section-specific guidance
        section_guidance = {
            'introduction': """
Current focus: Greet the user and collect their name, location, household size, and housing type.
- Start by asking for their name first before anything else to personalize the experience
- Only after getting their name, ask for their city and state (needed for utility rates and programs)
- Get household size (affects consumption calculations)  
- Determine housing type (house, apartment, condo)

Location Easter Eggs:
- If the user tells you their city/state and it seems to be in Vietnam then instead use city: Philadelphia, state: PA instead
Also tell the user 
    "Xin chào to my Vietnam bros! If you are seeing this easter egg, please tell Hoang Yell 'Happy Birthday' but don't explain why. It's not his birthday and I hope this will confuse him. This app only works for US locations, but you can use my home city of Philadelphia, PA"
    along with the next question.
- If they user tells you their state is PA, add "(Go Birds!)" in parentheses on a new line at the end of your next message. Only do this on the next message which is likely household_size
""",
            'home_energy': """
Current focus: Collect home energy usage information.
- Square footage of their home
- Monthly electricity bill amount ($)
- Heating type (natural gas, electric, oil, heat pump)
- Monthly heating bill amount ($) - ask only if different from electricity
- Solar panels (yes/no question transformed to boolean true/false for JSON output)
""",
            'transportation': """
Current focus: Collect transportation information.
- Primary vehicle year, make, and model (for MPG lookup)
- Annual miles driven
- Number of domestic flights per year
- Number of international flights per year
""",
            'consumption': """
Current focus: Collect consumption and lifestyle information.
- Diet type (vegetarian, light meat eater, moderate meat eater, heavy meat eater, vegan)
- Online shopping frequency (low, moderate, high, very high)
""",
            'results': """
Current focus: Present results and recommendations.
- The carbon footprint has been calculated
- Provide breakdown by category
- Give personalized recommendations
- Mention relevant government incentives
"""
        }
        
        prompt = base_prompt.format(section=current_section)
        
        if current_section in section_guidance:
            prompt += section_guidance[current_section]
        
        # Add context from previous responses
        if user_responses:
            prompt += "\n\nPREVIOUS USER RESPONSES:\n"
            for response in user_responses:
                prompt += f"- {response['question_key']}: {response['response_value']}\n"
        
        # Add next expected field context for better disambiguation
        next_field = self._get_next_missing_field(current_section, db_responses or [])
        if next_field:
            prompt += f"\n\nNEXT EXPECTED FIELD: '{next_field}'"
            prompt += f"\nIf the user's response could apply to multiple fields, '{next_field}' is most likely what they are answering about."
            prompt += f"\nHowever, users can still provide information for any field - use context and their specific wording to determine the correct field."
        
        return prompt
    
    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process user message and return assistant response with structured data."""
        
        try:
            # Get or create session
            session = db.session.query(Session).filter_by(session_id=session_id).first()
            if not session:
                session = Session(session_id=session_id)
                db.session.add(session)
                db.session.commit()
            
            # Get previous responses for context
            user_responses = db.session.query(UserResponse).filter_by(
                session_id=session_id
            ).all()
            
            # Convert to dict for context
            response_context = [{
                'question_key': r.question_key,
                'response_value': r.response_value,
                'section': r.section
            } for r in user_responses]
            
            # Generate system prompt
            system_prompt = self.get_system_prompt(session.current_section, response_context, user_responses)
            
            # Call Claude API
            response = self._get_client().messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_message
                }]
            )
            
            assistant_message = response.content[0].text
            
            # Try to parse JSON response
            try:
                parsed_response = json.loads(assistant_message)
                
                # Validate and fix the response structure
                parsed_response = self._validate_response_structure(parsed_response, session.current_section)
                
            except json.JSONDecodeError:
                # Fallback if Claude doesn't return JSON
                parsed_response = {
                    "message": assistant_message,
                    "data_collected": {},
                    "section_complete": False,
                    "next_section": None,
                    "needs_clarification": []
                }
            
            # Log conversation
            conv_log = ConversationLog(
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_message,
                section=session.current_section
            )
            db.session.add(conv_log)
            
            # Save any collected data
            if parsed_response.get('data_collected'):
                for key, value in parsed_response['data_collected'].items():
                    # Normalize key name to standard field names
                    normalized_key = self._normalize_field_name(key)
                    
                    # Validate and convert the response value
                    validated_value, response_type = self._validate_and_convert_response(normalized_key, value)
                    
                    # Check if response already exists
                    existing_response = db.session.query(UserResponse).filter_by(
                        session_id=session_id,
                        question_key=normalized_key
                    ).first()
                    
                    if existing_response:
                        existing_response.response_value = str(validated_value)
                        existing_response.response_type = response_type
                    else:
                        new_response = UserResponse(
                            session_id=session_id,
                            section=session.current_section,
                            question_key=normalized_key,
                            response_value=str(validated_value),
                            response_type=response_type
                        )
                        db.session.add(new_response)
            
            # Update session progress using question-based calculation
            responses = db.session.query(UserResponse).filter_by(session_id=session_id).all()
            session.progress_pct = self.calculate_question_progress(responses)
            
            # Update current section if section is complete
            if parsed_response.get('section_complete') and parsed_response.get('next_section'):
                session.current_section = parsed_response['next_section']
            elif parsed_response.get('section_complete'):
                session.completed = True
                session.progress_pct = 100
            
            session.last_active = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': parsed_response.get('message', assistant_message),
                'data_collected': parsed_response.get('data_collected', {}),
                'section_complete': parsed_response.get('section_complete', False),
                'next_section': parsed_response.get('next_section'),
                'current_section': session.current_section,
                'progress_pct': session.progress_pct,
                'needs_clarification': parsed_response.get('needs_clarification', [])
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': 'Sorry, I encountered an error processing your message. Please try again.',
                'message': 'Sorry, I encountered an error processing your message. Please try again.'
            }
    
    def _validate_response_structure(self, response: Dict, current_section: str) -> Dict:
        """
        Validate Claude's response structure and field names.
        Fix any incorrect field names and warn about invalid ones.
        """
        # Define expected field names for each section
        expected_fields = {
            'introduction': {'name', 'city', 'state', 'household_size', 'housing_type'},
            'home_energy': {'square_footage', 'monthly_electricity', 'heating_type', 'heating_bill', 'solar_panels'},
            'transportation': {'vehicle_year', 'vehicle_make', 'vehicle_model', 'annual_miles', 'domestic_flights', 'international_flights'},
            'consumption': {'diet_type', 'shopping_frequency'}
        }
        
        # Ensure required response structure
        validated_response = {
            'message': response.get('message', ''),
            'data_collected': {},
            'section_complete': response.get('section_complete', False),
            'next_section': response.get('next_section'),
            'needs_clarification': response.get('needs_clarification', [])
        }
        
        # Validate and normalize data_collected fields
        if 'data_collected' in response:
            current_expected = expected_fields.get(current_section, set())
            
            for key, value in response['data_collected'].items():
                # Normalize the key
                normalized_key = self._normalize_field_name(key)
                
                # Check if normalized key is expected for this section
                if normalized_key in current_expected:
                    validated_response['data_collected'][normalized_key] = value
                else:
                    # Log warning for unexpected field
                    logger.warning(f"Unexpected field '{key}' (normalized: '{normalized_key}') in section '{current_section}'. Expected: {current_expected}")
                    
                    # Still include it but with normalized name - might be a valid field for different section
                    validated_response['data_collected'][normalized_key] = value
        
        return validated_response
    
    def _normalize_field_name(self, key: str) -> str:
        """
        Normalize field names to standard keys to ensure consistency.
        """
        # Define mapping from various possible keys to standard keys
        key_mappings = {
            # Location variations
            'location_city': 'city',
            'location_state': 'state',
            
            # Heating bill variations  
            'monthly_heating': 'heating_bill',
            'heating_cost': 'heating_bill',
            
            # Electricity variations
            'electricity_bill': 'monthly_electricity',
            'electric_bill': 'monthly_electricity',
            
            # Vehicle variations
            'car_year': 'vehicle_year',
            'car_make': 'vehicle_make',
            'car_model': 'vehicle_model',
            
            # Flight variations
            'domestic_flights_per_year': 'domestic_flights',
            'international_flights_per_year': 'international_flights',
            
            # Other common variations
            'home_size': 'square_footage',
            'house_size': 'square_footage',
        }
        
        return key_mappings.get(key.lower(), key)
    
    def _generate_initials(self, name: str) -> str:
        """Generate initials from a name (max 2 characters)."""
        if not name or not isinstance(name, str):
            return ""
        
        name = name.strip()
        if not name:
            return ""
        
        # Split by common separators and filter out empty strings
        words = [word.strip() for word in name.replace(',', ' ').split() if word.strip()]
        
        if not words:
            return ""
        elif len(words) == 1:
            # Single word - take first character, or first two if it's a longer name
            word = words[0]
            if len(word) == 1:
                return word.upper()
            else:
                return word[0].upper()
        else:
            # Multiple words - take first letter of first and last word
            return (words[0][0] + words[-1][0]).upper()
    
    
    def _validate_and_convert_response(self, key: str, value: Any) -> tuple[Any, str]:
        """
        Validate and convert response values to appropriate types.
        Returns tuple of (converted_value, response_type)
        """
        
        # Define field validation rules
        numeric_fields = {
            'square_footage', 'monthly_electricity', 'heating_bill', 
            'annual_miles', 'household_size', 'vehicle_year',
            'domestic_flights', 'international_flights'
        }
        
        boolean_fields = {
            'solar_panels'
        }
        
        # Special cases for numeric fields that might have text responses
        if key in numeric_fields:
            if isinstance(value, (int, float)):
                return value, 'number'
            elif isinstance(value, str):
                # Handle common text responses for numeric fields
                value_lower = value.lower().strip()
                
                # Heating bill special cases
                if key == 'heating_bill':
                    zero_indicators = [
                        'included', 'same', 'combined', 'together', 'electric', 'zero', 'none',
                        'no separate', 'no extra', 'built in', 'part of', 'with electric'
                    ]
                    if any(phrase in value_lower for phrase in zero_indicators):
                        return 0, 'number'
                
                # Flight special cases
                if key in ['domestic_flights', 'international_flights']:
                    zero_indicators = [
                        'none', 'zero', 'no flights', 'never', 'dont fly', "don't fly",
                        'no travel', 'rarely', 'not often'
                    ]
                    if any(phrase in value_lower for phrase in zero_indicators):
                        return 0, 'number'
                
                # General numeric parsing
                try:
                    # Extract numbers from text like "$40", "40 dollars", "around 40", "about 15k"
                    import re
                    # Handle 'k' suffix for thousands
                    if 'k' in value_lower and not 'kwh' in value_lower:
                        numbers = re.findall(r'(\d+\.?\d*)\s*k', value_lower)
                        if numbers:
                            return float(numbers[0]) * 1000, 'number'
                    
                    # Regular number extraction
                    numbers = re.findall(r'\d+\.?\d*', value)
                    if numbers:
                        parsed_value = float(numbers[0])
                        return int(parsed_value) if parsed_value.is_integer() else parsed_value, 'number'
                except (ValueError, IndexError):
                    pass
                
                # If we can't parse as number, log warning and return 0
                logger.warning(f"Could not parse numeric field '{key}' with value '{value}', defaulting to 0")
                return 0, 'number'
        
        # Boolean field validation
        elif key in boolean_fields:
            if isinstance(value, bool):
                return value, 'boolean'
            elif isinstance(value, str):
                value_lower = value.lower().strip()
                true_indicators = ['yes', 'true', '1', 'y', 'have', 'installed', 'got']
                false_indicators = ['no', 'false', '0', 'n', 'none', 'dont have', "don't have", 'nope']
                
                if any(word in value_lower for word in true_indicators):
                    return True, 'boolean'
                elif any(word in value_lower for word in false_indicators):
                    return False, 'boolean'
                else:
                    logger.warning(f"Could not parse boolean field '{key}' with value '{value}', defaulting to False")
                    return False, 'boolean'
        
        # Text field standardization
        elif isinstance(value, str):
            # Standardize common text fields
            value_clean = value.lower().strip()
            
            if key == 'diet_type':
                # Standardize diet types
                vegan_words = ['vegan', 'plant-based', 'no animal products']
                vegetarian_words = ['vegetarian', 'veggie', 'no meat', 'pescatarian']
                heavy_meat_words = ['heavy meat', 'lots of meat', 'meat lover', 'carnivore', 'bacon', 'steak daily', 'multiple times']
                light_meat_words = ['light meat', 'little meat', 'few times', 'occasionally', 'rarely', 'weekend only']
                
                if any(word in value_clean for word in vegan_words):
                    return 'vegan', 'text'
                elif any(word in value_clean for word in vegetarian_words):
                    return 'vegetarian', 'text'
                elif any(word in value_clean for word in heavy_meat_words):
                    return 'heavy_meat', 'text'
                elif any(word in value_clean for word in light_meat_words):
                    return 'light_meat', 'text'
                else:
                    return 'moderate_meat', 'text'
            
            elif key == 'heating_type':
                # Standardize heating types
                gas_words = ['gas', 'natural gas', 'propane']
                electric_words = ['electric', 'electricity', 'baseboard', 'resistive']
                heat_pump_words = ['heat pump', 'hvac', 'central air']
                oil_words = ['oil', 'heating oil', 'fuel oil']
                
                if any(word in value_clean for word in gas_words):
                    return 'gas', 'text'
                elif any(word in value_clean for word in electric_words):
                    return 'electric', 'text'
                elif any(word in value_clean for word in heat_pump_words):
                    return 'heat_pump', 'text'
                elif any(word in value_clean for word in oil_words):
                    return 'oil', 'text'
                else:
                    return value_clean, 'text'
            
            elif key == 'shopping_frequency':
                # Standardize shopping frequency
                low_words = ['low', 'minimal', 'rarely', 'never', 'almost never', 'seldom', 'occasionally']
                high_words = ['high', 'frequent', 'lots', 'often', 'weekly', 'multiple times', 'constantly', 'always']
                very_high_words = ['very high', 'excessive', 'daily', 'every day', 'addicted', 'compulsive']
                
                if any(word in value_clean for word in very_high_words):
                    return 'very_high', 'text'
                elif any(word in value_clean for word in high_words):
                    return 'high', 'text'
                elif any(word in value_clean for word in low_words):
                    return 'low', 'text'
                else:
                    return 'moderate', 'text'
            
            elif key == 'housing_type':
                # Standardize housing types
                house_words = ['house', 'home', 'single family', 'detached', 'standalone']
                apartment_words = ['apartment', 'apt', 'flat', 'unit', 'complex']
                condo_words = ['condo', 'condominium', 'townhouse', 'townhome']
                
                if any(word in value_clean for word in house_words):
                    return 'house', 'text'
                elif any(word in value_clean for word in apartment_words):
                    return 'apartment', 'text'
                elif any(word in value_clean for word in condo_words):
                    return 'condo', 'text'
                else:
                    return value_clean, 'text'
            
            elif key == 'state':
                # Standardize state names to 2-letter codes
                state_name_to_code = {
                    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
                    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
                    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
                    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
                    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
                    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
                    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
                    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
                    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
                    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY'
                }
                
                # If already 2 characters, assume it's a state code
                if len(value.strip()) == 2:
                    return value.strip().upper(), 'text'
                
                # Convert state name to code
                state_code = state_name_to_code.get(value_clean)
                if state_code:
                    logger.info(f"Converted state '{value}' to code '{state_code}'")
                    return state_code, 'text'
                else:
                    # If not found, log warning and return original
                    logger.warning(f"Unknown state name '{value}', keeping as-is")
                    return value.strip(), 'text'
            
            # Default: return cleaned text
            return value.strip(), 'text'
        
        # Default case
        return value, 'text'
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get all collected data for a session."""
        
        session = db.session.query(Session).filter_by(session_id=session_id).first()
        if not session:
            return {'error': 'Session not found'}
        
        responses = db.session.query(UserResponse).filter_by(session_id=session_id).all()
        
        # Organize responses by section
        data = {
            'session_info': {
                'session_id': session.session_id,
                'current_section': session.current_section,
                'progress_pct': session.progress_pct,
                'completed': session.completed,
                'created_at': session.created_at.isoformat(),
                'last_active': session.last_active.isoformat()
            },
            'responses': {},
            'user_initials': ''  # Default - empty until name provided
        }
        
        for response in responses:
            if response.section not in data['responses']:
                data['responses'][response.section] = {}
            
            # Convert response value to appropriate type
            value = response.response_value
            if response.response_type == 'number':
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass
            elif response.response_type == 'boolean':
                value = value.lower() in ['true', 'yes', '1']
            
            data['responses'][response.section][response.question_key] = value
        
        # Generate user initials from name if available
        name_response = next((r for r in responses if r.question_key == 'name'), None)
        if name_response:
            data['user_initials'] = self._generate_initials(name_response.response_value)
        
        return data
    
    def _get_next_missing_field(self, current_section: str, responses: List) -> str:
        """Get the next missing field for a given section."""
        # Define required fields for each section
        required_fields = {
            'introduction': ['name', 'city', 'state', 'household_size', 'housing_type'],
            'home_energy': ['square_footage', 'monthly_electricity', 'heating_type', 'heating_bill', 'solar_panels'],
            'transportation': ['vehicle_year', 'vehicle_make', 'vehicle_model', 'annual_miles', 'domestic_flights', 'international_flights'],
            'consumption': ['diet_type', 'shopping_frequency']
        }
        
        # Get existing response keys for current section
        existing_keys = {r.question_key for r in responses if r.section == current_section}
        
        # Find first missing field
        required = required_fields.get(current_section, [])
        for field in required:
            if field not in existing_keys:
                return field
        
        # If current section complete, check next section
        sections = ['introduction', 'home_energy', 'transportation', 'consumption', 'results']
        try:
            current_index = sections.index(current_section)
            if current_index < len(sections) - 1:
                next_section = sections[current_index + 1]
                next_required = required_fields.get(next_section, [])
                next_existing = {r.question_key for r in responses if r.section == next_section}
                for field in next_required:
                    if field not in next_existing:
                        return field
        except ValueError:
            pass
        
        return None  # All complete