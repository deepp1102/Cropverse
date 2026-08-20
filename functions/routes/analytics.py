"""
Analytics Routes
================
API endpoints for analytics, trends, correlations, and reports.

Endpoints:
- GET /api/analytics/trends - Get sensor trends over time
- GET /api/analytics/correlations - Get sensor correlation matrix
- GET /api/analytics/summary - Get daily analytics summaries
- GET /api/analytics/summary/<date> - Get summary for specific date
- POST /api/analytics/report - Generate and download report

Security:
- All endpoints require Firebase Authentication in production
- Uses @login_required decorator (bypassed when TESTING_MODE=true)
"""

import os
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, Any

from utils.logger import setup_logger
from utils.validators import validate_date_range
from services.analytics_service import (
    get_trends,
    get_correlations,
    get_daily_summary,
    calculate_daily_summary
)
# from services.report_service import generate_csv_report, generate_pdf_report

# Testing mode bypass
TESTING_MODE = os.getenv('TESTING_MODE', 'false').lower() == 'true'

# Override login_required decorator in testing mode
if TESTING_MODE:
    def login_required(f):
        # No-op decorator in testing mode
        return f
else:
    from utils.decorators import login_required

logger = setup_logger(__name__)

# Create Blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')



def _parse_date_param(date_str: str, param_name: str = 'date') -> datetime:
    """
    Parse date string parameter to datetime object.
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        param_name: Parameter name for error messages
        
    Returns:
        datetime object
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid {param_name} format. Use YYYY-MM-DD (e.g., 2025-11-30)")


@analytics_bp.route('/trends', methods=['GET'])
@login_required
def get_sensor_trends():
    """
    Get sensor trends over specified time period.
    
    Query Parameters:
        days: int (optional, default=7) - Number of days to analyze (7, 30, or 90)
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "period_days": int,
                "start_date": string,
                "end_date": string,
                "temperature": {
                    "trend": string,  // "increasing", "decreasing", "stable"
                    "change": float,
                    "average": float,
                    "max": float,
                    "min": float
                },
                "humidity": {...},
                "methane": {...},
                "other_gases": {...},
                "alert_trend": {
                    "trend": string,
                    "total_alerts": int,
                    "critical_alerts": int,
                    "warning_alerts": int
                }
            },
            "timestamp": string
        }
    
    Example:
        GET /api/analytics/trends?days=30
    """
    try:
        # Get query parameters
        days = request.args.get('days', default=7, type=int)
        
        # Validate days parameter
        if days not in [7, 30, 90]:
            return jsonify({
                'success': False,
                'error': 'Invalid days parameter. Must be 7, 30, or 90.'
            }), 400
        
        user_id = getattr(request, 'user', {}).get('uid', 'test_user')
        logger.info(f"Fetching {days}-day trends for user {user_id}")
        
        # Get trends from service
        trends_data = get_trends(days=days)
        
        if not trends_data:
            return jsonify({
                'success': False,
                'error': 'Insufficient data for trend analysis',
                'message': f'Not enough sensor data available for {days}-day analysis.'
            }), 404
        
        logger.info(f"Trends calculated successfully for {days} days")
        
        return jsonify({
            'success': True,
            'data': trends_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch trends: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to calculate trends',
            'message': 'An error occurred while analyzing trends. Please try again.'
        }), 500


@analytics_bp.route('/correlations', methods=['GET'])
@login_required
def get_sensor_correlations():
    """
    Get correlation matrix between different sensors.
    
    Query Parameters:
        days: int (optional, default=7) - Number of days to analyze
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "period_days": int,
                "correlations": {
                    "temperature_humidity": float,
                    "temperature_methane": float,
                    "temperature_other_gases": float,
                    "humidity_methane": float,
                    "humidity_other_gases": float,
                    "methane_other_gases": float
                },
                "insights": [
                    {
                        "pair": string,
                        "correlation": float,
                        "strength": string,  // "strong", "moderate", "weak", "none"
                        "interpretation": string
                    }
                ]
            },
            "timestamp": string
        }
    
    Example:
        GET /api/analytics/correlations?days=30
    """
    try:
        # Get query parameters
        days = request.args.get('days', default=7, type=int)
        days = max(1, min(days, 90))  # Limit between 1-90 days
        
        logger.info(f"Calculating correlations for {days} days for user {getattr(request, 'user', {}).get('uid', 'test_user')}")
        
        # Get correlations from service
        correlation_data = get_correlations(days=days)
        
        if not correlation_data:
            return jsonify({
                'success': False,
                'error': 'Insufficient data for correlation analysis',
                'message': f'Not enough sensor data available for {days}-day analysis.'
            }), 404
        
        logger.info("Correlations calculated successfully")
        
        return jsonify({
            'success': True,
            'data': correlation_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to calculate correlations: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to calculate correlations',
            'message': 'An error occurred while analyzing sensor correlations. Please try again.'
        }), 500


@analytics_bp.route('/summary', methods=['GET'])
@login_required
def get_summaries():
    """
    Get daily analytics summaries for date range.
    
    Query Parameters:
        start_date: string (optional) - Start date in YYYY-MM-DD format (default: 7 days ago)
        end_date: string (optional) - End date in YYYY-MM-DD format (default: today)
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "summaries": [
                    {
                        "date": string,
                        "avg_temperature": float,
                        "max_temperature": float,
                        "min_temperature": float,
                        "avg_humidity": float,
                        "max_humidity": float,
                        "min_humidity": float,
                        "avg_methane": float,
                        "max_methane": float,
                        "min_methane": float,
                        "total_alert_count": int,
                        "critical_alert_count": int,
                        "warning_alert_count": int,
                        "data_quality_score": float,
                        "overall_status": string
                    }
                ],
                "count": int,
                "date_range": {
                    "start": string,
                    "end": string
                }
            },
            "timestamp": string
        }
    
    Example:
        GET /api/analytics/summary?start_date=2025-11-01&end_date=2025-11-30
    """
    try:
        # Get query parameters
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        if request.args.get('start_date'):
            start_date = _parse_date_param(request.args.get('start_date'), 'start_date')
        
        if request.args.get('end_date'):
            end_date = _parse_date_param(request.args.get('end_date'), 'end_date')
        
        # Validate date range
        validate_date_range(start_date, end_date)
        
        logger.info(f"Fetching summaries from {start_date.date()} to {end_date.date()}")
        
        # Get summaries from service
        summaries = get_daily_summary(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': {
                'summaries': [s.to_dict() for s in summaries],
                'count': len(summaries),
                'date_range': {
                    'start': start_date.date().isoformat(),
                    'end': end_date.date().isoformat()
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except ValueError as e:
        logger.warning(f"Invalid date parameters: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Failed to fetch summaries: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch analytics summaries',
            'message': 'An error occurred while retrieving summaries. Please try again.'
        }), 500


@analytics_bp.route('/summary/<date_str>', methods=['GET'])
@login_required
def get_summary_by_date(date_str: str):
    """
    Get analytics summary for specific date.
    
    URL Parameters:
        date_str: Date in YYYY-MM-DD format
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "date": string,
                "avg_temperature": float,
                "max_temperature": float,
                ... (all summary fields)
            },
            "timestamp": string
        }
    
    Response (404 Not Found):
        {
            "success": false,
            "error": "Summary not found for date"
        }
    
    Example:
        GET /api/analytics/summary/2025-11-30
    """
    try:
        # Parse date
        date = _parse_date_param(date_str, 'date')
        
        logger.info(f"Fetching summary for {date.date()}")
        
        # Get summary for single date
        summaries = get_daily_summary(date, date)
        
        if not summaries:
            return jsonify({
                'success': False,
                'error': 'Summary not found for date',
                'message': f'No analytics data available for {date.date().isoformat()}'
            }), 404
        
        summary = summaries[0]
        
        return jsonify({
            'success': True,
            'data': summary.to_dict(),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except ValueError as e:
        logger.warning(f"Invalid date parameter: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Failed to fetch summary: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch summary'
        }), 500


@analytics_bp.route('/summary/<date_str>/calculate', methods=['POST'])
@login_required
def calculate_summary_for_date(date_str: str):
    """
    Manually trigger calculation of analytics summary for specific date.
    (Useful for backfilling or recalculating data)
    
    URL Parameters:
        date_str: Date in YYYY-MM-DD format
        
    Response (200 OK):
        {
            "success": true,
            "message": "Summary calculated successfully",
            "data": {...}
        }
    
    Example:
        POST /api/analytics/summary/2025-11-30/calculate
    """
    try:
        # Parse date
        date = _parse_date_param(date_str, 'date')
        
        logger.info(f"Calculating summary for {date.date()}")
        
        # Calculate summary
        summary = calculate_daily_summary(date)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'Failed to calculate summary',
                'message': f'No sensor data available for {date.date().isoformat()}'
            }), 404
        
        logger.info(f"Summary calculated successfully for {date.date()}")
        
        return jsonify({
            'success': True,
            'message': 'Summary calculated successfully',
            'data': summary.to_dict(),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except ValueError as e:
        logger.warning(f"Invalid date parameter: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Failed to calculate summary: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to calculate summary'
        }), 500


# @analytics_bp.route('/report', methods=['POST'])
# @login_required
# def generate_report():
#     """
#     Generate and download analytics report.
    
#     Request Body (JSON):
#         {
#             "start_date": string,     // YYYY-MM-DD
#             "end_date": string,       // YYYY-MM-DD
#             "format": string,         // "csv" or "pdf"
#             "report_type": string     // "readings", "alerts", "summary", "full"
#         }
    
#     Response (200 OK):
#         {
#             "success": true,
#             "data": {
#                 "download_url": string,    // Signed URL (expires in 60 min)
#                 "filename": string,
#                 "size_bytes": int,
#                 "row_count": int,
#                 "report_type": string,
#                 "format": string,
#                 "date_range": string
#             },
#             "timestamp": string
#         }
    
#     Response (400 Bad Request):
#         {
#             "success": false,
#             "error": "Error message"
#         }
    
#     Example:
#         POST /api/analytics/report
#         Body: {
#             "start_date": "2025-11-01",
#             "end_date": "2025-11-30",
#             "format": "csv",
#             "report_type": "summary"
#         }
#     """
#     try:
#         # Get request data
#         data = request.get_json()
#         if not data:
#             return jsonify({
#                 'success': False,
#                 'error': 'Request body is required'
#             }), 400
        
#         # Extract parameters
#         start_date_str = data.get('start_date')
#         end_date_str = data.get('end_date')
#         report_format = data.get('format', 'csv').lower()
#         report_type = data.get('report_type', 'summary').lower()
        
#         # Validate required fields
#         if not start_date_str or not end_date_str:
#             return jsonify({
#                 'success': False,
#                 'error': 'start_date and end_date are required'
#             }), 400
        
#         # Parse dates
#         start_date = _parse_date_param(start_date_str, 'start_date')
#         end_date = _parse_date_param(end_date_str, 'end_date')
        
#         # Validate date range
#         validate_date_range(start_date, end_date)
        
#         # Validate format
#         if report_format not in ['csv', 'pdf']:
#             return jsonify({
#                 'success': False,
#                 'error': 'Invalid format. Must be "csv" or "pdf".'
#             }), 400
        
#         # Validate report type
#         if report_type not in ['readings', 'alerts', 'summary', 'full']:
#             return jsonify({
#                 'success': False,
#                 'error': 'Invalid report_type. Must be "readings", "alerts", "summary", or "full".'
#             }), 400
        
#         logger.info(f"Generating {report_format.upper()} report: {report_type} from {start_date.date()} to {end_date.date()}")
        
#         # Generate report based on format
#         if report_format == 'csv':
#             result = generate_csv_report(start_date, end_date, report_type)
#         else:  # pdf
#             result = generate_pdf_report(start_date, end_date, report_type)
        
#         if not result['success']:
#             return jsonify({
#                 'success': False,
#                 'error': result['error']
#             }), 500
        
#         logger.info(f"Report generated successfully: {result['filename']}")
        
#         return jsonify({
#             'success': True,
#             'data': {
#                 'download_url': result['download_url'],
#                 'filename': result['filename'],
#                 'size_bytes': result['size_bytes'],
#                 'row_count': result['row_count'],
#                 'report_type': report_type,
#                 'format': report_format,
#                 'date_range': result['date_range']
#             },
#             'timestamp': datetime.now().isoformat()
#         }), 200
        
#     except ValueError as e:
#         logger.warning(f"Invalid report parameters: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         }), 400
        
#     except Exception as e:
#         logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
#         return jsonify({
#             'success': False,
#             'error': 'Failed to generate report',
#             'message': 'An error occurred while generating the report. Please try again.'
#         }), 500


# Error handlers for this blueprint
@analytics_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'code': 'UNAUTHORIZED'
    }), 401


@analytics_bp.errorhandler(500)
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
    print("Analytics Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- GET  /api/analytics/trends - Sensor trends over time")
    print("- GET  /api/analytics/correlations - Sensor correlations")
    print("- GET  /api/analytics/summary - Daily summaries (date range)")
    print("- GET  /api/analytics/summary/<date> - Summary for specific date")
    print("- POST /api/analytics/summary/<date>/calculate - Calculate summary")
    print("- POST /api/analytics/report - Generate downloadable report")
    print("\nAuthentication: Firebase Auth token required")