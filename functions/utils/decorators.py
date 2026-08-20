"""
Authentication and Authorization Decorators
===========================================
Decorators for protecting API routes with Firebase Authentication.

Decorators:
- @login_required: Requires valid Firebase Auth token
- @admin_required: Requires valid token AND admin role
- @optional_auth: Optional authentication
- @rate_limit: Rate limiting
- @log_execution_time: Log function execution time
- @log_function_call: Log function calls with arguments

Usage:
    @app.route('/api/protected')
    @login_required
    def protected_route():
        user_id = request.user['uid']
        return {'message': 'Access granted'}
    
    @app.route('/api/admin/settings')
    @admin_required
    def admin_route():
        user_id = request.user['uid']
        return {'message': 'Admin access granted'}
"""

import time
from functools import wraps
from flask import request, jsonify
from typing import Callable, Any
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Firebase Admin SDK imports
try:
    import firebase_admin
    from firebase_admin import auth
except ImportError:
    logger.error("Firebase Admin SDK not installed. Run: pip install firebase-admin")
    auth = None


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(f: Callable) -> Callable:
    """
    Decorator to require valid Firebase Authentication token.
    
    Checks Authorization header for 'Bearer <token>' format.
    Verifies token with Firebase Auth and attaches user info to request object.
    
    Usage:
        @app.route('/api/protected')
        @login_required
        def protected_route():
            user_id = request.user['uid']
            user_email = request.user['email']
            return {'message': f'Hello {user_email}'}
    
    Returns:
        - If valid: Calls the wrapped function with request.user populated
        - If invalid: Returns 401 Unauthorized JSON response
    
    Request.user contains:
        - uid: User's unique ID
        - email: User's email address
        - email_verified: Boolean if email is verified
        - custom_claims: Dict of custom claims (e.g., {'admin': True})
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Check if Firebase Admin is available
        if auth is None:
            logger.error("Firebase Admin SDK not initialized")
            return jsonify({
                'error': 'Authentication service unavailable',
                'message': 'Server configuration error'
            }), 500
        
        # Get Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        # Check header format
        if not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            return jsonify({
                'error': 'Missing authorization header',
                'message': 'Please provide Authorization: Bearer <token> header'
            }), 401
        
        # Extract token
        token = auth_header.split('Bearer ')[1].strip()
        
        if not token:
            logger.warning("Empty token provided")
            return jsonify({
                'error': 'Empty token',
                'message': 'Authorization token is empty'
            }), 401
        
        try:
            # Verify token with Firebase
            decoded_token = auth.verify_id_token(token)
            
            # Attach user info to request object
            request.user = decoded_token
            
            # Log successful authentication (without sensitive data)
            logger.info(f"User authenticated: {decoded_token.get('uid')}")
            
            # Call the wrapped function
            return f(*args, **kwargs)
            
        except auth.ExpiredIdTokenError:
            logger.warning("Expired token provided")
            return jsonify({
                'error': 'Token expired',
                'message': 'Your session has expired. Please login again.'
            }), 401
            
        except auth.RevokedIdTokenError:
            logger.warning("Revoked token provided")
            return jsonify({
                'error': 'Token revoked',
                'message': 'Your session has been revoked. Please login again.'
            }), 401
            
        except auth.InvalidIdTokenError:
            logger.warning("Invalid token provided")
            return jsonify({
                'error': 'Invalid token',
                'message': 'Authentication token is invalid'
            }), 401
            
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Unable to verify authentication token',
                'details': str(e)
            }), 401
    
    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require valid Firebase Auth token AND admin role.
    
    This decorator:
    1. Verifies the user is authenticated (like @login_required)
    2. Checks if user has admin custom claim in Firebase
    3. If both pass, allows access
    
    To set admin custom claim for a user in Firebase:
        from firebase_admin import auth
        auth.set_custom_user_claims(uid, {'admin': True})
    
    Usage:
        @app.route('/api/admin/settings')
        @admin_required
        def admin_only_route():
            return {'message': 'Admin access granted'}
    
    Returns:
        - If valid admin: Calls the wrapped function
        - If not authenticated: Returns 401 Unauthorized
        - If not admin: Returns 403 Forbidden
    """
    @wraps(f)
    @login_required  # First check authentication
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # At this point, @login_required has already verified the token
        # and attached user info to request.user
        
        # Get custom claims
        custom_claims = request.user.get('custom_claims', {})
        
        # Check if user has admin claim
        is_admin = custom_claims.get('admin', False)
        
        if not is_admin:
            user_id = request.user.get('uid', 'unknown')
            logger.warning(f"Non-admin user attempted admin access: {user_id}")
            return jsonify({
                'error': 'Admin access required',
                'message': 'You do not have permission to access this resource'
            }), 403
        
        # Log admin access
        logger.info(f"Admin access granted: {request.user.get('uid')}")
        
        # Call the wrapped function
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication.
    
    If token is provided and valid, attaches user info to request.
    If token is missing or invalid, continues without authentication.
    
    Useful for routes that behave differently for authenticated vs anonymous users.
    
    Usage:
        @app.route('/api/dashboard')
        @optional_auth
        def dashboard():
            if hasattr(request, 'user'):
                # User is authenticated
                return {'message': f'Welcome back, {request.user["email"]}'}
            else:
                # User is anonymous
                return {'message': 'Welcome, guest'}
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Check if Firebase Admin is available
        if auth is None:
            # Continue without authentication
            return f(*args, **kwargs)
        
        # Get Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        # If no header, continue without authentication
        if not auth_header.startswith('Bearer '):
            return f(*args, **kwargs)
        
        # Extract token
        token = auth_header.split('Bearer ')[1].strip()
        
        if not token:
            return f(*args, **kwargs)
        
        try:
            # Verify token
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token
            logger.info(f"Optional auth: User authenticated {decoded_token.get('uid')}")
        except Exception as e:
            # Token invalid, but continue anyway
            logger.debug(f"Optional auth: Invalid token, continuing as anonymous: {str(e)}")
        
        # Call wrapped function (with or without request.user)
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator for rate limiting API requests.
    
    NOTE: This is a simple in-memory rate limiter.
    For production, use Redis or Firebase Realtime Database for distributed rate limiting.
    
    Args:
        max_requests: Maximum requests allowed in the time window
        window_seconds: Time window in seconds
    
    Usage:
        @app.route('/api/chatbot/message')
        @login_required
        @rate_limit(max_requests=10, window_seconds=60)
        def chatbot():
            return {'response': 'AI response here'}
    """
    from collections import defaultdict
    from time import time
    
    # In-memory storage (user_id -> list of timestamps)
    request_history = defaultdict(list)
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Get user ID (requires @login_required or @optional_auth)
            user_id = getattr(request, 'user', {}).get('uid', request.remote_addr)
            
            current_time = time()
            
            # Clean old requests outside the window
            request_history[user_id] = [
                timestamp for timestamp in request_history[user_id]
                if current_time - timestamp < window_seconds
            ]
            
            # Check rate limit
            if len(request_history[user_id]) >= max_requests:
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per {window_seconds} seconds',
                    'retry_after': window_seconds
                }), 429
            
            # Add current request
            request_history[user_id].append(current_time)
            
            # Call wrapped function
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_user() -> dict:
    """
    Helper function to get current authenticated user from request context.
    
    Must be called within a route protected by @login_required or @admin_required.
    
    Returns:
        Dictionary with user info (uid, email, custom_claims, etc.)
        
    Raises:
        AttributeError: If called outside authenticated route
        
    Usage:
        @app.route('/api/profile')
        @login_required
        def get_profile():
            user = get_current_user()
            return {
                'uid': user['uid'],
                'email': user['email'],
                'is_admin': user.get('custom_claims', {}).get('admin', False)
            }
    """
    if not hasattr(request, 'user'):
        raise AttributeError("get_current_user() called outside authenticated route")
    return request.user


def is_current_user_admin() -> bool:
    """
    Helper function to check if current user is admin.
    
    Returns:
        True if current user has admin custom claim, False otherwise
        
    Usage:
        @app.route('/api/data')
        @login_required
        def get_data():
            if is_current_user_admin():
                # Return admin-level data
                return {'data': 'sensitive admin data'}
            else:
                # Return limited data
                return {'data': 'public data'}
    """
    try:
        user = get_current_user()
        custom_claims = user.get('custom_claims', {})
        return custom_claims.get('admin', False)
    except AttributeError:
        return False


# ============================================================================
# LOGGING DECORATORS
# ============================================================================

def log_execution_time(f: Callable) -> Callable:
    """
    Decorator to log function execution time.
    
    Useful for monitoring performance of API endpoints and services.
    
    Usage:
        @app.route('/api/analytics/trends')
        @log_execution_time
        def get_trends():
            # ... complex calculations ...
            return {'trends': data}
    
    Logs:
        INFO: Function 'get_trends' completed in 1.23 seconds
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function '{f.__name__}' completed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function '{f.__name__}' failed after {execution_time:.2f} seconds: {str(e)}"
            )
            raise
    
    return decorated_function


def log_function_call(f: Callable) -> Callable:
    """
    Decorator to log when a function is called with its arguments.
    
    Useful for debugging and tracking function usage.
    
    Usage:
        @log_function_call
        def process_sensor_data(device_id, temperature, humidity):
            # ... processing logic ...
            return result
    
    Logs:
        INFO: Calling 'process_sensor_data' with args=('ARDUINO_001',) kwargs={'temperature': 25.5, 'humidity': 65.0}
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Don't log sensitive data like passwords or tokens
        safe_kwargs = {
            k: v for k, v in kwargs.items() 
            if k not in ['password', 'token', 'api_key', 'auth_token']
        }
        
        logger.info(
            f"Calling '{f.__name__}' with args={args} kwargs={safe_kwargs}"
        )
        
        return f(*args, **kwargs)
    
    return decorated_function