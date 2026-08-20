"""
CropVerse Main Application
==========================
Entry point for Firebase Cloud Functions.

This module defines:
- Flask app with all API routes mounted
- CORS configuration for frontend communication
- Scheduled Cloud Functions (daily analytics job)
- Global error handlers
- Health check endpoint

Functions:
- app() - Main Flask application (handles all HTTP requests)
- daily_analytics_job() - Scheduled function (runs daily at midnight)
"""

import os
import logging

from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from firebase_admin import initialize_app, firestore
from firebase_functions import https_fn, scheduler_fn

from utils.logger import setup_logger, get_api_logger
from utils.decorators import log_execution_time



from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# # Initialize Firebase Admin SDK
# initialize_app()
# db = firestore.client()



# Initialize Firebase Admin SDK
import os
from firebase_admin import credentials


# Setup loggers
logger = setup_logger(__name__)
api_logger = get_api_logger()


# Check if running locally or on Cloud Functions
if os.path.exists('serviceAccountKey.json'):
    # Local development - use service account key
    cred = credentials.Certificate('serviceAccountKey.json')
    initialize_app(cred)
    logger.info("Firebase initialized with service account key (local)")
else:
    # Cloud Functions - use default credentials
    initialize_app()
    logger.info("Firebase initialized with default credentials (cloud)")

db = firestore.client()


# Create Flask app
flask_app = Flask(__name__)

#\
            'arduino': '/api/arduino/*',
            'dashboard': '/api/dashboard/*',
            'analytics': '/api/analytics/*',
            'chatbot': '/api/chatbot/*',
            'settings': '/api/settings/*',
            'auth': '/api/auth/*'
        }
    }), 200


@flask_app.route('/health')
@log_execution_time
def health_check():
    """
    Health check endpoint.
    
    Verifies:
    - Flask app is running
    - Firestore connection is working
    - Environment variables are loaded
    
    Returns:
        JSON response with health status
    """
    try:
        # Test Firestore connection
        db.collection('settings').limit(1).get()
        
        # Check critical environment variables
        required_env_vars = ['FIREBASE_PROJECT_ID', 'CLAUDE_API_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {missing_vars}")
            return jsonify({
                'status': 'degraded',
                'message': \
        'status_code': 403
    }), 403


@flask_app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    api_logger.info(f"Resource not found: {request.path}")
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }), 404


@flask_app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 Too Many Requests errors."""
    api_logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({
        'error': 'Too Many Requests',
        'message': 'Rate limit exceeded. Please try again later.',
        'status_code': 429
    }), 429


@flask_app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server Error."""
    api_logger.error\==============
# FIREBASE CLOUD FUNCTIONS EXPORTS
# ============================================================================

@https_fn.on_request(
    timeout_sec=300,
    memory=512,
    min_instances=0,
    max_instances=10
)
def app(req: https_fn.Request) -> https_fn.Response:
    """
    Main HTTP Cloud \
        req: Firebase HTTP request object
        
    Returns:
        Firebase HTTP response object
    """
    with flask_app.request_context(req.environ):
        return flask_app.full_dispatch_request()


@scheduler_fn.on_schedule(
    schedule="0 0 * * *",  # Every day at midnight UTC
    timezone="UTC",
    memory=256,
    timeout_sec=540
)
def daily_analytics_job(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled Cloud Function - Daily Analytics Summary.
    
    This function runs automatically every day at midnight UTC.
    It calculates analytics for the previous day and stores the summary
    in the analytics_summary collection.
    
    What it does:
    1. Gets \
            f"Daily analytics job failed for {yesterday}: {str(e)}", 
            exc_info=True
        )
        # Don't re-raise - we don't want the job to be marked as failed
        # It will retry automatically next day


# ============================================================================
# DEVELOPMENT SERVER (for local testing only)
# ============================================================================

if __name__ == '__main__':
    """
    Local development server.
    
    This runs only when you execute 'python main.py' directly.
    Firebase Cloud Functions don't use this - they call the app() function.
    
    Usage:
        python main.py
        
    Then access: http://localhost:8080
    """
    print("=" * 60)
    print("🌱 CropVerse API - Development Server")
    print("=" * 60)
    
    
    
    flask_app.run(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
