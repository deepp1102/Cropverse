"""
Chatbot Routes
==============
API endpoints for AI chatbot interactions using Claude.

Endpoints:
- POST /api/chatbot/message - Send message to AI chatbot
- GET /api/chatbot/suggestions - Get conversation starter suggestions
- GET /api/chatbot/context - Get current sensor context for chatbot
- POST /api/chatbot/test - Test Claude API connection

Security:
- All endpoints require Firebase Authentication in production
- Uses @login_required decorator (bypassed if TESTING_MODE=true)
"""

import os
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import List, Dict, Any

from utils.logger import setup_logger
from services.ai_chatbot_service import (
    get_ai_response,
    get_conversation_suggestions,
    test_claude_connection,
    build_sensor_context,
    build_alert_context
)

# ────────────────────────────────────────────
# 🔧 TESTING MODE AUTH BYPASS
# ────────────────────────────────────────────
TESTING_MODE = os.getenv('TESTING_MODE', 'false').lower() == 'true'

if TESTING_MODE:
    # No-op decorator to disable authentication
    def login_required(f):
        return f
else:
    from utils.decorators import login_required
# ────────────────────────────────────────────

logger = setup_logger(__name__)

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

# Conversation history limits
MAX_HISTORY_LENGTH = 10      # limit recent messages
MAX_MESSAGE_LENGTH = 2000    # max user input chars


def _validate_message(message: str) -> tuple[bool, str]:
    """
    Validate user message.
    
    Args:
        message: User's message text
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed."
    
    return True, ""


def _validate_conversation_history(history: List[Dict[str, str]]) -> tuple[bool, str]:
    """
    Validate conversation history format.
    
    Args:
        history: List of conversation messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(history, list):
        return False, "Conversation history must be an array"
    
    if len(history) > MAX_HISTORY_LENGTH:
        return False, f"Conversation history too long. Maximum {MAX_HISTORY_LENGTH} messages allowed."
    
    for i, msg in enumerate(history):
        if not isinstance(msg, dict):
            return False, f"Message {i} must be an object"
        
        if 'role' not in msg or 'content' not in msg:
            return False, f"Message {i} must have 'role' and 'content' fields"
        
        if msg['role'] not in ['user', 'assistant']:
            return False, f"Message {i} has invalid role. Must be 'user' or 'assistant'"
        
        if not isinstance(msg['content'], str):
            return False, f"Message {i} content must be a string"
    
    return True, ""


@chatbot_bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """
    Send message to AI chatbot and get response.
    
    Request Body (JSON):
        {
            "message": string,              // User's message (required, max 2000 chars)
            "conversation_history": [       // Optional previous messages
                {
                    "role": "user",
                    "content": "Previous user message"
                },
                {
                    "role": "assistant",
                    "content": "Previous AI response"
                }
            ]
        }
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "response": string,         // AI's response
                "model": string,            // Model used (e.g., "claude-sonnet-4")
                "tokens_used": int,         // Total tokens consumed
                "timestamp": string
            },
            "timestamp": string
        }
    
    Response (400 Bad Request):
        {
            "success": false,
            "error": "Error message"
        }
    
    Response (503 Service Unavailable):
        {
            "success": false,
            "error": "AI service temporarily unavailable"
        }
    
    Example:
        POST /api/chatbot/message
        Body: {
            "message": "Why is my temperature reading high?",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help with your crops today?"}
            ]
        }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Extract and validate message
        message = data.get('message', '').strip()
        is_valid, error_msg = _validate_message(message)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Extract and validate conversation history
        conversation_history = data.get('conversation_history', [])
        is_valid, error_msg = _validate_conversation_history(conversation_history)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Get user ID
        user_id = getattr(request, 'user', {}).get('uid', 'test_user')
        
        logger.info(f"Chatbot message from user {user_id}: '{message[:50]}...' (history_length={len(conversation_history)})")
        
        # Get AI response
        result = get_ai_response(
            message=message,
            user_id=user_id,
            conversation_history=conversation_history
        )
        
        if not result['success']:
            logger.error(f"AI service error: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': 'AI assistant is temporarily unavailable. Please try again in a moment.'
            }), 503
        
        logger.info(f"Chatbot response generated: {result['tokens_used']} tokens, model={result['model']}")
        
        return jsonify({
            'success': True,
            'data': {
                'response': result['response'],
                'model': result['model'],
                'tokens_used': result['tokens_used'],
                'timestamp': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to process chatbot message: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process message',
            'message': 'An unexpected error occurred. Please try again.'
        }), 500


@chatbot_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """
    Get conversation starter suggestions based on current system status.
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "suggestions": [
                    "What do my current sensor readings mean?",
                    "How can I optimize my growing conditions?",
                    ...
                ]
            },
            "timestamp": string
        }
    
    Example:
        GET /api/chatbot/suggestions
    """
    try:
        logger.info(f"Fetching chatbot suggestions for user {getattr(request, 'user', {}).get('uid', 'test_user')}")
        
        # Get contextual suggestions
        suggestions = get_conversation_suggestions()
        
        return jsonify({
            'success': True,
            'data': {
                'suggestions': suggestions
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get suggestions'
        }), 500


@chatbot_bp.route('/context', methods=['GET'])
@login_required
def get_context():
    """
    Get current sensor and alert context that the chatbot uses.
    (Useful for debugging or showing users what data the AI can see)
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "sensor_context": string,   // Current sensor readings summary
                "alert_context": string,    // Active alerts summary
                "timestamp": string
            },
            "timestamp": string
        }
    
    Example:
        GET /api/chatbot/context
    """
    try:
        logger.info(f"Fetching chatbot context for user {getattr(request, 'user', {}).get('uid', 'test_user')}")
        
        # Build context strings
        sensor_context = build_sensor_context()
        alert_context = build_alert_context()
        
        return jsonify({
            'success': True,
            'data': {
                'sensor_context': sensor_context,
                'alert_context': alert_context,
                'timestamp': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get context: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get context'
        }), 500


@chatbot_bp.route('/test', methods=['POST'])
@login_required
def test_connection():
    """
    Test Claude API connection and availability.
    (Admin endpoint for troubleshooting)
    
    Response (200 OK):
        {
            "success": true,
            "message": "Claude AI is available",
            "timestamp": string
        }
    
    Response (503 Service Unavailable):
        {
            "success": false,
            "error": "Claude AI is not available"
        }
    
    Example:
        POST /api/chatbot/test
    """
    try:
        logger.info(f"Testing Claude connection for user {getattr(request, 'user', {}).get('uid', 'test_user')}")
        
        # Test connection
        is_available = test_claude_connection()
        
        if is_available:
            return jsonify({
                'success': True,
                'message': 'Claude AI is available',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Claude AI is not available',
                'message': 'The AI service is not configured or not responding.'
            }), 503
        
    except Exception as e:
        logger.error(f"Failed to test connection: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Connection test failed'
        }), 500


@chatbot_bp.route('/limits', methods=['GET'])
@login_required
def get_limits():
    """
    Get chatbot usage limits and configuration.
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "max_message_length": int,
                "max_history_length": int,
                "model": string,
                "max_tokens_per_response": int
            },
            "timestamp": string
        }
    
    Example:
        GET /api/chatbot/limits
    """
    try:
        return jsonify({
            'success': True,
            'data': {
                'max_message_length': MAX_MESSAGE_LENGTH,
                'max_history_length': MAX_HISTORY_LENGTH,
                'model': 'claude-sonnet-4-20250514',
                'max_tokens_per_response': 1000,
                'features': [
                    'Real-time sensor data awareness',
                    'Active alert monitoring',
                    'Agricultural expertise',
                    'Conversation history support',
                    'Contextual recommendations'
                ]
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get limits: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get limits'
        }), 500


# Error handlers for this blueprint
@chatbot_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'code': 'UNAUTHORIZED'
    }), 401


@chatbot_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 errors"""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please wait a moment and try again.',
        'code': 'RATE_LIMIT_EXCEEDED'
    }), 429


@chatbot_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500


# Module-level info
if __name__ == "__main__":
    print("Chatbot Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- POST /api/chatbot/message - Send message to AI")
    print("- GET  /api/chatbot/suggestions - Get conversation starters")
    print("- GET  /api/chatbot/context - Get current sensor context")
    print("- POST /api/chatbot/test - Test Claude API connection")
    print("- GET  /api/chatbot/limits - Get usage limits")
    print("\nAuthentication: Firebase Auth token required")
    print("\nFeatures:")
    print("- Real-time sensor data awareness")
    print("- Active alert monitoring")
    print("- Agricultural domain expertise")
    print("- Conversation history support (up to 10 messages)")
    print("- Context-aware suggestions")