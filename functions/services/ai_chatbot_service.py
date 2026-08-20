"""
AI Chatbot Service
==================
Claude AI integration for agricultural assistance and monitoring insights.

Functions:
- get_ai_response(message, user_id=None) - Get Claude AI response with context
- build_sensor_context() - Build current sensor data context
- build_alert_context() - Build recent alerts context
- build_system_prompt() - Create agricultural expert system prompt
- format_conversation_history(messages) - Format chat history for Claude
- test_claude_connection() - Test Claude API connection

Features:
- Context-aware responses with live sensor data
- Agricultural domain expertise
- Conversation history support
- Alert awareness
- Graceful error handling
- Rate limiting friendly
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from firebase_admin import firestore

from utils.logger import setup_logger
from models.sensor_reading import SensorReading
from models.alert import Alert

logger = setup_logger(__name__)

# Initialize Firestore
db = firestore.client()

# Claude API configuration
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
CLAUDE_MODEL = 'claude-sonnet-4-20250514'  # Latest Sonnet model
CLAUDE_MAX_TOKENS = 1000

# Lazy import for Anthropic (only when needed)
_anthropic_client = None


def _get_anthropic_client():
    """
    Get or initialize Anthropic client (lazy loading).
    
    Returns:
        Anthropic Client instance or None if API key missing
    """
    global _anthropic_client
    
    if _anthropic_client is None:
        if not CLAUDE_API_KEY:
            logger.error("CLAUDE_API_KEY not configured")
            return None
        
        try:
            from anthropic import Anthropic
            _anthropic_client = Anthropic(api_key=CLAUDE_API_KEY)
            logger.info("Anthropic client initialized successfully")
        except ImportError:
            logger.error("Anthropic library not installed. Run: pip install anthropic")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            return None
    
    return _anthropic_client


def build_sensor_context() -> str:
    """
    Build context string with current sensor readings.
    
    Returns:
        Formatted string with latest sensor data
        
    Example:
        >>> context = build_sensor_context()
        >>> print(context)
        Current Sensor Readings (as of 2025-11-30 14:30:00):
        - Temperature: 28.5°C (Optimal ✓)
        - Humidity: 65% (Optimal ✓)
        ...
    """
    try:
        # Get latest sensor reading
        readings_ref = db.collection('sensor_readings')
        latest_docs = readings_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
        
        latest_reading = None
        for doc in latest_docs:
            latest_reading = SensorReading.from_dict(doc.to_dict())
            break
        
        if not latest_reading:
            return "No sensor data available at this time."
        
        # Format sensor data with status
        context = f"Current Sensor Readings (as of {latest_reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}):\n"
        context += f"- Temperature: {latest_reading.temperature}°C ({latest_reading.get_temperature_status()})\n"
        context += f"- Humidity: {latest_reading.humidity}% ({latest_reading.get_humidity_status()})\n"
        context += f"- Methane: {latest_reading.methane} ppm ({latest_reading.get_methane_status()})\n"
        context += f"- Other Gases: {latest_reading.other_gases} ppm\n"
        context += f"- Air Quality: {latest_reading.calculate_air_quality_status()}\n"
        context += f"- Exhaust Fan: {'ON' if latest_reading.exhaust_fan else 'OFF'}\n"
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to build sensor context: {str(e)}")
        return "Unable to retrieve current sensor data."


def build_alert_context() -> str:
    """
    Build context string with recent unresolved alerts.
    
    Returns:
        Formatted string with active alerts
        
    Example:
        >>> context = build_alert_context()
        >>> print(context)
        Active Alerts (3):
        1. 🚨 CRITICAL - Temperature: 38.5°C exceeded threshold of 35.0°C
        ...
    """
    try:
        # Get unresolved alerts from last 24 hours
        alerts_ref = db.collection('alerts')
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        query = alerts_ref.where('is_resolved', '==', False).where('created_at', '>=', cutoff_time)
        alert_docs = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(10).stream()
        
        alerts = []
        for doc in alert_docs:
            alert_data = doc.to_dict()
            alerts.append(Alert.from_dict(alert_data))
        
        if not alerts:
            return "No active alerts at this time. All systems normal."
        
        # Format alerts
        context = f"Active Alerts ({len(alerts)}):\n"
        for i, alert in enumerate(alerts, 1):
            age_str = alert.get_age_string()
            context += f"{i}. {alert.status_emoji} {alert.alert_type.upper()} - {alert.sensor_type.replace('_', ' ').title()}: "
            context += f"{alert.value}{alert.get_unit()} exceeded threshold of {alert.threshold}{alert.get_unit()} ({age_str})\n"
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to build alert context: {str(e)}")
        return "Unable to retrieve alert information."


def build_system_prompt() -> str:
    """
    Build system prompt for Claude with agricultural expertise and current context.
    
    Returns:
        System prompt string
    """
    sensor_context = build_sensor_context()
    alert_context = build_alert_context()
    
    system_prompt = f"""You are an expert agricultural AI assistant for CropVerse, a smart agricultural monitoring system. Your role is to help farmers and agricultural professionals understand their sensor data, troubleshoot issues, and optimize growing conditions.

**Your Expertise:**
- Agricultural best practices and crop management
- Environmental monitoring and interpretation
- Greenhouse management and climate control
- Pest and disease prevention
- Irrigation and humidity management
- Soil health and nutrient management
- Alert interpretation and troubleshooting

**Current System Status:**

{sensor_context}

{alert_context}

**Guidelines:**
1. Be friendly, clear, and concise in your responses
2. Reference the current sensor data when relevant to the question
3. Provide actionable advice and specific recommendations
4. Explain technical concepts in simple terms
5. If critical issues are present, prioritize safety and immediate actions
6. When discussing thresholds: Temperature (optimal: 18-32°C), Humidity (optimal: 45-75%), Methane (warning: >200 ppm, critical: >300 ppm)
7. If you don't have enough information, ask clarifying questions
8. Suggest checking the dashboard or analytics for more detailed information when appropriate

**Important:** You have access to real-time sensor data shown above. Always consider this context when answering questions about current conditions, alerts, or recommendations."""

    return system_prompt


def format_conversation_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format conversation history for Claude API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
                 Example: [{'role': 'user', 'content': 'Hello'}, {'role': 'assistant', 'content': 'Hi!'}]
    
    Returns:
        Formatted messages for Claude API
        
    Note:
        Claude API requires alternating user/assistant messages.
        System prompt is handled separately.
    """
    if not messages:
        return []
    
    formatted = []
    for msg in messages:
        if msg.get('role') in ['user', 'assistant'] and msg.get('content'):
            formatted.append({
                'role': msg['role'],
                'content': msg['content'].strip()
            })
    
    return formatted


def get_ai_response(
    message: str,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Get AI response from Claude with agricultural context.
    
    Args:
        message: User's message/question
        user_id: Optional user ID for logging
        conversation_history: Optional previous messages in conversation
                            Format: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    
    Returns:
        Dictionary with response and metadata:
        {
            'success': bool,
            'response': str,
            'model': str,
            'tokens_used': int,
            'error': str (if success=False)
        }
    
    Raises:
        ValueError: If message is empty
    
    Example:
        >>> result = get_ai_response("Why is my temperature high?")
        >>> if result['success']:
        ...     print(result['response'])
        >>> else:
        ...     print(f"Error: {result['error']}")
    """
    try:
        # Validate input
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        
        # Get Anthropic client
        client = _get_anthropic_client()
        if not client:
            return {
                'success': False,
                'error': 'AI service not configured. Please contact administrator.',
                'response': None,
                'model': None,
                'tokens_used': 0
            }
        
        # Build system prompt with current context
        system_prompt = build_system_prompt()
        
        # Format conversation history
        messages = format_conversation_history(conversation_history or [])
        
        # Add current user message
        messages.append({
            'role': 'user',
            'content': message.strip()
        })
        
        # Log request
        logger.info(f"Sending message to Claude (user_id={user_id}, message_length={len(message)})")
        
        # Call Claude API
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=messages
        )
        
        # Extract response text
        response_text = ""
        if response.content:
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
        
        # Log success
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        logger.info(f"Claude response received (tokens={tokens_used}, stop_reason={response.stop_reason})")
        
        return {
            'success': True,
            'response': response_text.strip(),
            'model': response.model,
            'tokens_used': tokens_used,
            'stop_reason': response.stop_reason,
            'error': None
        }
        
    except ValueError as e:
        logger.warning(f"Invalid input: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'response': None,
            'model': None,
            'tokens_used': 0
        }
    except Exception as e:
        logger.error(f"Failed to get AI response: {str(e)}", exc_info=True)
        
        # Provide user-friendly error message
        error_message = "I'm having trouble connecting to the AI service right now. Please try again in a moment."
        if "rate_limit" in str(e).lower():
            error_message = "The AI service is experiencing high demand. Please wait a moment and try again."
        elif "invalid" in str(e).lower() or "authentication" in str(e).lower():
            error_message = "AI service configuration error. Please contact administrator."
        
        return {
            'success': False,
            'error': error_message,
            'response': None,
            'model': None,
            'tokens_used': 0
        }


def test_claude_connection() -> bool:
    """
    Test Claude API connection and authentication.
    
    Returns:
        True if connection successful, False otherwise
    
    Example:
        >>> if test_claude_connection():
        ...     print("Claude AI is configured correctly!")
    """
    try:
        client = _get_anthropic_client()
        if not client:
            return False
        
        logger.info("Testing Claude API connection")
        
        # Send simple test message
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=50,
            messages=[{
                'role': 'user',
                'content': 'Hello, please respond with just "OK" if you receive this.'
            }]
        )
        
        logger.info(f"Claude API test successful. Model: {response.model}")
        return True
        
    except Exception as e:
        logger.error(f"Claude API test failed: {str(e)}")
        return False


def get_conversation_suggestions() -> List[str]:
    """
    Get contextual conversation starters based on current system status.
    
    Returns:
        List of suggested questions/topics
    
    Example:
        >>> suggestions = get_conversation_suggestions()
        >>> for suggestion in suggestions:
        ...     print(f"- {suggestion}")
    """
    suggestions = [
        "What do my current sensor readings mean?",
        "How can I optimize my growing conditions?",
        "What should I do about the active alerts?",
        "What's the ideal temperature range for my crops?",
        "How does humidity affect plant growth?",
        "When should the exhaust fan be running?",
        "What are signs of poor air quality?",
        "How often should I check the sensors?"
    ]
    
    try:
        # Add context-specific suggestions based on alerts
        alerts_ref = db.collection('alerts')
        unresolved_query = alerts_ref.where('is_resolved', '==', False).limit(1).stream()
        
        has_alerts = False
        for _ in unresolved_query:
            has_alerts = True
            break
        
        if has_alerts:
            suggestions.insert(0, "What do these alerts mean and how should I respond?")
            suggestions.insert(1, "Are my current conditions safe for my crops?")
        
    except Exception as e:
        logger.warning(f"Failed to customize suggestions: {str(e)}")
    
    return suggestions


# Module-level test function
if __name__ == "__main__":
    """Test AI chatbot service"""
    print("Testing AI Chatbot Service...")
    print("=" * 50)
    
    # Test Claude connection
    print("\n1. Testing Claude API connection...")
    if test_claude_connection():
        print("✅ Claude API connection successful")
    else:
        print("❌ Claude API connection failed")
        exit(1)
    
    # Test sensor context building
    print("\n2. Building sensor context...")
    sensor_ctx = build_sensor_context()
    print(sensor_ctx)
    
    # Test alert context building
    print("\n3. Building alert context...")
    alert_ctx = build_alert_context()
    print(alert_ctx)
    
    # Test AI response
    print("\n4. Testing AI response...")
    test_message = "What are my current sensor readings and are they optimal?"
    result = get_ai_response(test_message)
    
    if result['success']:
        print(f"✅ Response received ({result['tokens_used']} tokens)")
        print(f"\nResponse:\n{result['response']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    # Test conversation suggestions
    print("\n5. Getting conversation suggestions...")
    suggestions = get_conversation_suggestions()
    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"   {i}. {suggestion}")
    
    print("\n" + "=" * 50)
    print("AI Chatbot service tests complete!")