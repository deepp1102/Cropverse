"""
Auth Routes
===========
API endpoints for authentication and user management.

Endpoints:
- POST /api/auth/verify - Verify Firebase Auth token
- GET /api/auth/user - Get current user info
- POST /api/auth/refresh - Refresh user session
- POST /api/auth/logout - Logout user
- GET /api/auth/permissions - Get user permissions

Security:
- Most endpoints require @login_required
- Some use @optional_auth for public access
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any

from utils.logger import setup_logger
from utils.decorators import login_required, optional_auth, get_current_user, is_current_user_admin
from services.firestore_service import get_user_by_uid, update_user_last_login

logger = setup_logger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _format_user_info(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format user data for API response.
    
    Args:
        user_data: Raw user data from Firestore
        
    Returns:
        Formatted user info
    """
    return {
        'uid': user_data.get('uid'),
        'email': user_data.get('email'),
        'display_name': user_data.get('display_name'),
        'role': user_data.get('role', 'user'),
        'phone_number': user_data.get('phone_number'),
        'created_at': user_data.get('created_at').isoformat() if user_data.get('created_at') else None,
        'last_login': user_data.get('last_login').isoformat() if user_data.get('last_login') else None
    }


@auth_bp.route('/verify', methods=['POST'])
@optional_auth
def verify_token():
    """
    Verify Firebase Auth token and return user info.
    
    Request Headers:
        Authorization: Bearer <firebase_auth_token>
    
    Response (200 OK):
        {
            "success": true,
            "authenticated": true,
            "user": {
                "uid": string,
                "email": string,
                "display_name": string,
                "role": string,
                "permissions": {...}
            },
            "timestamp": string
        }
    
    Response (401 Unauthorized):
        {
            "success": false,
            "authenticated": false,
            "error": "Invalid token"
        }
    
    Example:
        POST /api/auth/verify
        Headers: Authorization: Bearer eyJhbGc...
    """
    try:
        user = get_current_user()
        
        if not user:
            return jsonify({
                'success': False,
                'authenticated': False,
                'error': 'Invalid or missing authentication token'
            }), 401
        
        # Get full user info from Firestore
        user_doc = get_user_by_uid(user.get('uid'))
        
        if user_doc:
            user_info = _format_user_info(user_doc.to_dict())
        else:
            # User exists in Firebase Auth but not in Firestore
            user_info = {
                'uid': user.get('uid'),
                'email': user.get('email'),
                'display_name': user.get('name'),
                'role': 'user',
                'permissions': {}
            }
        
        # Add permissions
        is_admin = is_current_user_admin()
        user_info['permissions'] = {
            'can_view_dashboard': True,
            'can_view_analytics': True,
            'can_use_chatbot': True,
            'can_modify_settings': is_admin,
            'can_resolve_alerts': is_admin,
            'can_manage_users': is_admin,
            'can_generate_reports': True
        }
        
        logger.info(f"Token verified for user {user.get('uid')}")
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': user_info,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to verify token: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': 'Token verification failed'
        }), 401


@auth_bp.route('/user', methods=['GET'])
@login_required
def get_user_info():
    """
    Get current authenticated user's information.
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "uid": string,
                "email": string,
                "display_name": string,
                "role": string,
                "phone_number": string,
                "created_at": string,
                "last_login": string,
                "permissions": {...}
            },
            "timestamp": string
        }
    
    Example:
        GET /api/auth/user
    """
    try:
        user = request.user
        uid = user.get('uid')
        
        logger.info(f"Fetching user info for {uid}")
        
        # Get user from Firestore
        user_doc = get_user_by_uid(uid)
        
        if not user_doc:
            return jsonify({
                'success': False,
                'error': 'User not found in database'
            }), 404
        
        user_info = _format_user_info(user_doc.to_dict())
        
        # Add permissions
        is_admin = is_current_user_admin()
        user_info['permissions'] = {
            'can_view_dashboard': True,
            'can_view_analytics': True,
            'can_use_chatbot': True,
            'can_modify_settings': is_admin,
            'can_resolve_alerts': is_admin,
            'can_manage_users': is_admin,
            'can_generate_reports': True
        }
        
        return jsonify({
            'success': True,
            'data': user_info,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch user info: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch user information'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@login_required
def refresh_session():
    """
    Refresh user session and update last login time.
    
    Response (200 OK):
        {
            "success": true,
            "message": "Session refreshed",
            "last_login": string
        }
    
    Example:
        POST /api/auth/refresh
    """
    try:
        uid = request.user.get('uid')
        
        logger.info(f"Refreshing session for user {uid}")
        
        # Update last login time
        success = update_user_last_login(uid)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to refresh session'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Session refreshed',
            'last_login': datetime.now().isoformat(),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to refresh session: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to refresh session'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout user (client-side should clear token).
    
    Response (200 OK):
        {
            "success": true,
            "message": "Logged out successfully"
        }
    
    Example:
        POST /api/auth/logout
    """
    try:
        uid = request.user.get('uid')
        logger.info(f"User {uid} logged out")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Logout failed'
        }), 500


@auth_bp.route('/permissions', methods=['GET'])
@login_required
def get_permissions():
    """
    Get current user's permissions.
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "role": string,
                "is_admin": bool,
                "permissions": {
                    "can_view_dashboard": bool,
                    "can_view_analytics": bool,
                    "can_use_chatbot": bool,
                    "can_modify_settings": bool,
                    "can_resolve_alerts": bool,
                    "can_manage_users": bool,
                    "can_generate_reports": bool
                }
            },
            "timestamp": string
        }
    
    Example:
        GET /api/auth/permissions
    """
    try:
        uid = request.user.get('uid')
        is_admin = is_current_user_admin()
        
        # Get user doc for role
        user_doc = get_user_by_uid(uid)
        role = user_doc.to_dict().get('role', 'user') if user_doc else 'user'
        
        permissions = {
            'can_view_dashboard': True,
            'can_view_analytics': True,
            'can_use_chatbot': True,
            'can_modify_settings': is_admin,
            'can_resolve_alerts': is_admin,
            'can_manage_users': is_admin,
            'can_generate_reports': True
        }
        
        return jsonify({
            'success': True,
            'data': {
                'role': role,
                'is_admin': is_admin,
                'permissions': permissions
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch permissions: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch permissions'
        }), 500


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """
    Check authentication status (public endpoint).
    
    Response (200 OK):
        {
            "service": "auth",
            "status": "available",
            "timestamp": string
        }
    
    Example:
        GET /api/auth/status
    """
    return jsonify({
        'service': 'auth',
        'status': 'available',
        'firebase_auth': 'enabled',
        'timestamp': datetime.now().isoformat()
    }), 200


# Error handlers for this blueprint
@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'code': 'UNAUTHORIZED',
        'message': 'Please log in to access this resource'
    }), 401


@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return jsonify({
        'success': False,
        'error': 'Forbidden',
        'code': 'FORBIDDEN',
        'message': 'You do not have permission to access this resource'
    }), 403


@auth_bp.errorhandler(500)
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
    print("Auth Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- POST /api/auth/verify - Verify Firebase token")
    print("- GET  /api/auth/user - Get current user info")
    print("- POST /api/auth/refresh - Refresh session")
    print("- POST /api/auth/logout - Logout")
    print("- GET  /api/auth/permissions - Get user permissions")
    print("- GET  /api/auth/status - Check auth service status")
    print("\nAuthentication: Firebase Auth token required (except status)")