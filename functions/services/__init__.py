"""
Business Logic Services for CropVerse
======================================
This package contains all business logic services that sit between
API routes and data models.

Service Modules:
- firestore_service: Common Firestore database operations
- arduino_handler: Process incoming Arduino sensor data
- alert_service: Threshold checking and alert generation
- analytics_service: Statistical analysis and trend calculations
- ai_chatbot_service: Claude AI chatbot integration
- notification_service: Multi-channel notifications (email, SMS)
- report_service: Generate and export reports (CSV, PDF)

Architecture:
    Routes → Services → Models → Firestore
    
Example:
    from services import process_sensor_data, check_thresholds
    
    # Process Arduino data
    result = process_sensor_data(sensor_data)
    
    # Check if alerts should be triggered
    alerts = check_thresholds(result['reading'])
"""

# Firestore service
from .firestore_service import (
    get_latest_readings,
    get_recent_alerts,
    get_setting,
    update_setting,
    get_all_settings,
    get_user_by_email,
    create_user,
    update_user,
    get_user_by_uid,
    update_user_last_login,
)


# Arduino handler
from .arduino_handler import (
    process_sensor_data,
    validate_arduino_data
)

# Alert service
from .alert_service import (
    check_thresholds,
    create_alert,
    resolve_alert,
    get_active_alerts,
    get_unresolved_alerts
)

# Analytics service
from .analytics_service import (
    get_trends,
    get_correlations,
    calculate_daily_summary,
    get_summary_for_date_range
)

# AI Chatbot service
from .ai_chatbot_service import (
    get_ai_response,
    build_sensor_context,
    build_alert_context,
    get_conversation_suggestions,
    test_claude_connection
)

# Notification service
from .notification_service import (
    send_email_alert,
    send_sms_alert,
    send_alert_notification
)

# Report service
# from .report_service import (
#     generate_csv_report,
#     generate_pdf_report,
#     upload_to_storage
# )

__all__ = [
    # Firestore service
    'get_latest_readings',
    'get_recent_alerts',
    'get_setting',
    'update_setting',
    'get_all_settings',
    'get_user_by_email',
    'create_user',
    'update_user',
    'get_user_by_uid',
    'update_user_last_login',
    
    # Arduino handler
    'process_sensor_data',
    'validate_arduino_data',
    
    # Alert service
    'check_thresholds',
    'create_alert',
    'resolve_alert',
    'get_active_alerts',
    'get_unresolved_alerts',
    
    # Analytics service
    'get_trends',
    'get_correlations',
    'calculate_daily_summary',
    'get_summary_for_date_range',
    
    # AI Chatbot service
    'get_ai_response',
    'build_sensor_context',
    'build_alert_context',
    'get_conversation_suggestions',
    'test_claude_connection',
    
    # Notification service
    'send_email_alert',
    'send_sms_alert',
    'send_alert_notification',
    # # Report service
    # 'generate_csv_report',
    # 'generate_pdf_report',
    # 'upload_to_storage'
]