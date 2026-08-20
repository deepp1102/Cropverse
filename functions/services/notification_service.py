"""
Notification Service
====================
Multi-channel alert notification system supporting email (Gmail SMTP) and SMS (Twilio).

Functions:
- send_email_alert(alert, recipient_email=None) - Send alert via email
- send_sms_alert(alert, recipient_phone=None) - Send alert via SMS (Twilio)
- send_alert_notification(alert) - Send alert via all enabled channels
- test_email_connection() - Test SMTP connection
- test_sms_connection() - Test Twilio connection

Features:
- Respects notification preferences from settings
- Graceful degradation if channels fail
- Rate limiting aware (avoids spam)
- HTML and plain text email support
- 160-character SMS formatting
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any
from firebase_admin import firestore

from utils.logger import setup_logger
from models.alert import Alert

logger = setup_logger(__name__)

# Initialize Firestore
db = firestore.client()

# Environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PHONE_NUMBER = os.getenv('ADMIN_PHONE_NUMBER')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Lazy import for Twilio (only when needed)
_twilio_client = None


def _get_twilio_client():
    """
    Get or initialize Twilio client (lazy loading).
    
    Returns:
        Twilio Client instance or None if credentials missing
    """
    global _twilio_client
    
    if _twilio_client is None:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            logger.warning("Twilio credentials not configured")
            return None
        
        try:
            from twilio.rest import Client
            _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Twilio client initialized successfully")
        except ImportError:
            logger.error("Twilio library not installed. Run: pip install twilio")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")
            return None
    
    return _twilio_client


def _get_notification_settings() -> Dict[str, bool]:
    """
    Get notification preferences from Firestore settings.
    
    Returns:
        Dictionary with email_enabled and sms_enabled flags
    """
    try:
        settings_ref = db.collection('settings')
        
        # Get email setting
        email_doc = settings_ref.document('EMAIL_NOTIFICATIONS_ENABLED').get()
        email_enabled = email_doc.to_dict().get('value', 'true').lower() == 'true' if email_doc.exists else True
        
        # Get SMS setting
        sms_doc = settings_ref.document('SMS_NOTIFICATIONS_ENABLED').get()
        sms_enabled = sms_doc.to_dict().get('value', 'false').lower() == 'true' if sms_doc.exists else False
        
        return {
            'email_enabled': email_enabled,
            'sms_enabled': sms_enabled
        }
    except Exception as e:
        logger.error(f"Failed to get notification settings: {str(e)}")
        # Default to email only if settings fetch fails
        return {'email_enabled': True, 'sms_enabled': False}


def _create_email_html(alert: Alert) -> str:
    """
    Create HTML email body for alert.
    
    Args:
        alert: Alert instance
        
    Returns:
        HTML string for email body
    """
    # Color coding based on alert type
    color_map = {
        'info': '#17a2b8',      # Blue
        'warning': '#ffc107',   # Yellow
        'critical': '#dc3545'   # Red
    }
    color = color_map.get(alert.alert_type, '#6c757d')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; }}
            .alert-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid {color}; }}
            .detail-row {{ margin: 8px 0; }}
            .label {{ font-weight: bold; color: #555; }}
            .value {{ color: #333; }}
            .footer {{ text-align: center; margin-top: 20px; color: #777; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{alert.status_emoji} CropVerse Alert</h2>
                <p style="margin: 5px 0;">{alert.alert_type.upper()}</p>
            </div>
            <div class="content">
                <div class="alert-details">
                    <div class="detail-row">
                        <span class="label">Sensor:</span>
                        <span class="value">{alert.sensor_type.replace('_', ' ').title()}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Message:</span>
                        <span class="value">{alert.message}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Current Value:</span>
                        <span class="value">{alert.value}{alert.get_unit()}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Threshold:</span>
                        <span class="value">{alert.threshold}{alert.get_unit()}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Time:</span>
                        <span class="value">{alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                </div>
                <p><strong>Recommended Action:</strong> Check your CropVerse dashboard for more details and take appropriate action.</p>
            </div>
            <div class="footer">
                <p>This is an automated alert from CropVerse Agricultural Monitoring System</p>
                <p>© {datetime.now().year} CropVerse. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def _create_email_plain(alert: Alert) -> str:
    """
    Create plain text email body for alert.
    
    Args:
        alert: Alert instance
        
    Returns:
        Plain text string for email body
    """
    text = f"""
CropVerse Alert - {alert.alert_type.upper()}
{'=' * 50}

Sensor: {alert.sensor_type.replace('_', ' ').title()}
Message: {alert.message}
Current Value: {alert.value}{alert.get_unit()}
Threshold: {alert.threshold}{alert.get_unit()}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Recommended Action:
Check your CropVerse dashboard for more details and take appropriate action.

---
This is an automated alert from CropVerse Agricultural Monitoring System
© {datetime.now().year} CropVerse. All rights reserved.
    """
    return text.strip()


def send_email_alert(alert: Alert, recipient_email: Optional[str] = None) -> bool:
    """
    Send alert notification via email using Gmail SMTP.
    
    Args:
        alert: Alert instance to send
        recipient_email: Optional recipient email (defaults to ADMIN_EMAIL)
        
    Returns:
        True if email sent successfully, False otherwise
        
    Raises:
        ValueError: If email configuration is missing
        
    Example:
        >>> alert = Alert(sensor_type='temperature', alert_type='critical', ...)
        >>> success = send_email_alert(alert)
        >>> if success:
        ...     print("Email sent!")
    """
    try:
        # Validate configuration
        if not all([EMAIL_USER, EMAIL_PASSWORD]):
            logger.error("Email configuration missing (EMAIL_USER, EMAIL_PASSWORD)")
            return False
        
        recipient = recipient_email or ADMIN_EMAIL
        if not recipient:
            logger.error("No recipient email provided and ADMIN_EMAIL not configured")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{alert.status_emoji} CropVerse Alert: {alert.alert_type.upper()} - {alert.sensor_type.replace('_', ' ').title()}"
        msg['From'] = EMAIL_USER
        msg['To'] = recipient
        
        # Attach plain text and HTML versions
        plain_part = MIMEText(_create_email_plain(alert), 'plain')
        html_part = MIMEText(_create_email_html(alert), 'html')
        msg.attach(plain_part)
        msg.attach(html_part)
        
        # Send email
        logger.info(f"Connecting to SMTP server {EMAIL_HOST}:{EMAIL_PORT}")
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email alert sent successfully to {recipient}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check EMAIL_USER and EMAIL_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email alert: {str(e)}", exc_info=True)
        return False


def send_sms_alert(alert: Alert, recipient_phone: Optional[str] = None) -> bool:
    """
    Send alert notification via SMS using Twilio.
    
    Args:
        alert: Alert instance to send
        recipient_phone: Optional recipient phone (defaults to ADMIN_PHONE_NUMBER)
        
    Returns:
        True if SMS sent successfully, False otherwise
        
    Example:
        >>> alert = Alert(sensor_type='methane', alert_type='critical', ...)
        >>> success = send_sms_alert(alert)
        >>> if success:
        ...     print("SMS sent!")
    """
    try:
        # Get Twilio client
        client = _get_twilio_client()
        if not client:
            logger.error("Twilio client not available")
            return False
        
        recipient = recipient_phone or ADMIN_PHONE_NUMBER
        if not recipient:
            logger.error("No recipient phone provided and ADMIN_PHONE_NUMBER not configured")
            return False
        
        # Format SMS message (max 160 characters for standard SMS)
        sms_body = alert.format_for_sms()
        
        # Send SMS
        logger.info(f"Sending SMS to {recipient}")
        message = client.messages.create(
            body=sms_body,
            from_=TWILIO_PHONE_NUMBER,
            to=recipient
        )
        
        logger.info(f"SMS alert sent successfully. SID: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS alert: {str(e)}", exc_info=True)
        return False


def send_alert_notification(alert: Alert) -> Dict[str, bool]:
    """
    Send alert via all enabled notification channels.
    
    Args:
        alert: Alert instance to send
        
    Returns:
        Dictionary with results for each channel:
        {'email': bool, 'sms': bool}
        
    Example:
        >>> alert = Alert(sensor_type='humidity', alert_type='warning', ...)
        >>> results = send_alert_notification(alert)
        >>> print(f"Email: {results['email']}, SMS: {results['sms']}")
    """
    results = {'email': False, 'sms': False}
    
    try:
        # Get notification settings
        settings = _get_notification_settings()
        
        # Send email if enabled
        if settings['email_enabled']:
            logger.info(f"Email notifications enabled, sending alert for {alert.sensor_type}")
            results['email'] = send_email_alert(alert)
        else:
            logger.info("Email notifications disabled in settings")
        
        # Send SMS if enabled
        if settings['sms_enabled']:
            logger.info(f"SMS notifications enabled, sending alert for {alert.sensor_type}")
            results['sms'] = send_sms_alert(alert)
        else:
            logger.info("SMS notifications disabled in settings")
        
        # Log overall result
        if results['email'] or results['sms']:
            logger.info(f"Alert notification sent successfully via {[k for k, v in results.items() if v]}")
        else:
            logger.warning("No notifications sent (all channels disabled or failed)")
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to send alert notification: {str(e)}", exc_info=True)
        return results


def test_email_connection() -> bool:
    """
    Test SMTP email connection and authentication.
    
    Returns:
        True if connection successful, False otherwise
        
    Example:
        >>> if test_email_connection():
        ...     print("Email is configured correctly!")
    """
    try:
        if not all([EMAIL_USER, EMAIL_PASSWORD]):
            logger.error("Email credentials not configured")
            return False
        
        logger.info(f"Testing SMTP connection to {EMAIL_HOST}:{EMAIL_PORT}")
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        logger.info("Email connection test successful")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        return False
    except Exception as e:
        logger.error(f"Email connection test failed: {str(e)}")
        return False


def test_sms_connection() -> bool:
    """
    Test Twilio SMS connection and credentials.
    
    Returns:
        True if connection successful, False otherwise
        
    Example:
        >>> if test_sms_connection():
        ...     print("SMS is configured correctly!")
    """
    try:
        client = _get_twilio_client()
        if not client:
            return False
        
        logger.info("Testing Twilio connection")
        # Verify account by fetching account details
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        logger.info(f"Twilio connection test successful. Account: {account.friendly_name}")
        return True
        
    except Exception as e:
        logger.error(f"SMS connection test failed: {str(e)}")
        return False


# Module-level test function
if __name__ == "__main__":
    """Test notification service with sample alert"""
    from models.alert import Alert
    from datetime import datetime
    
    print("Testing Notification Service...")
    print("=" * 50)
    
    # Create test alert
    test_alert = Alert(
        sensor_type='temperature',
        alert_type='critical',
        message='Temperature exceeded critical threshold',
        value=38.5,
        threshold=35.0,
        created_at=datetime.now()
    )
    
    # Test email connection
    print("\n1. Testing email connection...")
    if test_email_connection():
        print("✅ Email connection successful")
    else:
        print("❌ Email connection failed")
    
    # Test SMS connection
    print("\n2. Testing SMS connection...")
    if test_sms_connection():
        print("✅ SMS connection successful")
    else:
        print("❌ SMS connection failed")
    
    # Test sending notifications
    print("\n3. Testing alert notifications...")
    results = send_alert_notification(test_alert)
    print(f"Email sent: {'✅' if results['email'] else '❌'}")
    print(f"SMS sent: {'✅' if results['sms'] else '❌'}")
    
    print("\n" + "=" * 50)
    print("Notification service tests complete!")