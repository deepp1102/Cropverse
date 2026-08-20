"""
Daily Analytics Summary Job
============================
Scheduled Cloud Function that calculates daily analytics summaries.

This job runs every day at midnight UTC to:
1. Aggregate all sensor readings from the previous day
2. Calculate statistics (avg, min, max for all sensors)
3. Count alerts generated during the day
4. Assess data quality and overall system status
5. Save summary to analytics_summary collection
6. Send email notification to admins with summary

Functions:
- calculate_and_save_daily_summary() - Main job function
- manual_trigger_summary() - Manual trigger for specific dates
- _send_summary_email() - Send completion email to admins
- _calculate_for_date() - Core calculation logic
"""

import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
from firebase_admin import firestore

from utils.logger import setup_logger
from services.analytics_service import calculate_daily_summary
from services.notification_service import send_email_notification

logger = setup_logger(__name__)
db = firestore.client()


def calculate_and_save_daily_summary(target_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate and save daily analytics summary for a specific date.
    
    This is the main function called by the scheduled Cloud Function.
    It aggregates all sensor data from the target date and saves a summary.
    
    Args:
        target_date: Date to calculate summary for (defaults to yesterday)
        
    Returns:
        Dictionary containing:
        - success (bool): Whether calculation succeeded
        - date (str): Date that was processed
        - summary (dict): The calculated summary data
        - message (str): Success/error message
        
    Example:
        >>> result = calculate_and_save_daily_summary()
        >>> print(result['message'])
        'Daily summary calculated successfully for 2024-01-15'
    """
    try:
        # Default to yesterday if no date provided
        if target_date is None:
            target_date = (datetime.utcnow().date() - timedelta(days=1))
        
        logger.info(f"Starting daily summary calculation for {target_date}")
        
        # Calculate summary using analytics service
        summary_data = calculate_daily_summary(target_date)
        
        if not summary_data:
            logger.warning(f"No data available for {target_date}")
            return {
                'success': False,
                'date': str(target_date),
                'summary': None,
                'message': f'No sensor data available for {target_date}'
            }
        
        # Log key metrics
        logger.info(
            f"Summary calculated for {target_date}: "
            f"{summary_data.get('total_readings', 0)} readings, "
            f"{summary_data.get('alert_count', 0)} alerts, "
            f"avg temp: {summary_data.get('avg_temperature', 0):.1f}°C, "
            f"status: {summary_data.get('overall_status', 'unknown')}"
        )
        
        # Send email notification to admin
        try:
            _send_summary_email(target_date, summary_data)
        except Exception as email_error:
            logger.error(f"Failed to send summary email: {str(email_error)}")
            # Don't fail the entire job if email fails
        
        return {
            'success': True,
            'date': str(target_date),
            'summary': summary_data,
            'message': f'Daily summary calculated successfully for {target_date}'
        }
        
    except Exception as e:
        error_msg = f"Failed to calculate daily summary for {target_date}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Send error notification to admin
        try:
            _send_error_email(target_date, str(e))
        except Exception as email_error:
            logger.error(f"Failed to send error email: {str(email_error)}")
        
        return {
            'success': False,
            'date': str(target_date) if target_date else 'unknown',
            'summary': None,
            'message': error_msg
        }


def manual_trigger_summary(start_date: date, end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Manually trigger daily summary calculation for a date range.
    
    Useful for:
    - Backfilling historical data
    - Recalculating summaries after data corrections
    - Testing the summary calculation
    
    Args:
        start_date: First date to calculate summary for
        end_date: Last date to calculate (defaults to start_date)
        
    Returns:
        Dictionary containing:
        - total (int): Total number of dates processed
        - successful (int): Number of successful calculations
        - failed (int): Number of failed calculations
        - results (list): List of individual results for each date
        
    Example:
        >>> from datetime import date
        >>> result = manual_trigger_summary(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 7)
        ... )
        >>> print(f"Processed {result['successful']}/{result['total']} dates")
    """
    try:
        if end_date is None:
            end_date = start_date
        
        logger.info(f"Manual trigger: calculating summaries from {start_date} to {end_date}")
        
        results = []
        current_date = start_date
        successful = 0
        failed = 0
        
        # Process each date in range
        while current_date <= end_date:
            result = calculate_and_save_daily_summary(current_date)
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
            
            current_date += timedelta(days=1)
        
        total = successful + failed
        logger.info(
            f"Manual trigger completed: {successful}/{total} successful, {failed}/{total} failed"
        )
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Manual trigger failed: {str(e)}", exc_info=True)
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'error': str(e)
        }


def _send_summary_email(target_date: date, summary_data: Dict[str, Any]) -> None:
    """
    Send daily summary email to admin.
    
    Args:
        target_date: Date that was processed
        summary_data: The calculated summary data
    """
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        logger.warning("ADMIN_EMAIL not configured, skipping summary email")
        return
    
    # Format email body
    subject = f"CropVerse Daily Summary - {target_date}"
    
    body = f"""
Daily Analytics Summary for {target_date}
{'=' * 60}

📊 SENSOR STATISTICS
{'─' * 60}
Temperature:
  • Average: {summary_data.get('avg_temperature', 0):.1f}°C
  • Maximum: {summary_data.get('max_temperature', 0):.1f}°C
  • Minimum: {summary_data.get('min_temperature', 0):.1f}°C

Humidity:
  • Average: {summary_data.get('avg_humidity', 0):.1f}%
  • Maximum: {summary_data.get('max_humidity', 0):.1f}%
  • Minimum: {summary_data.get('min_humidity', 0):.1f}%

Methane (CH4):
  • Average: {summary_data.get('avg_methane', 0):.0f} PPM
  • Maximum: {summary_data.get('max_methane', 0):.0f} PPM
  • Minimum: {summary_data.get('min_methane', 0):.0f} PPM

Other Gases:
  • Average: {summary_data.get('avg_other_gases', 0):.0f} PPM
  • Maximum: {summary_data.get('max_other_gases', 0):.0f} PPM
  • Minimum: {summary_data.get('min_other_gases', 0):.0f} PPM

🚨 ALERTS
{'─' * 60}
Total Alerts: {summary_data.get('alert_count', 0)}
  • Critical: {summary_data.get('critical_alert_count', 0)}
  • Warning: {summary_data.get('warning_alert_count', 0)}
  • Info: {summary_data.get('info_alert_count', 0)}

📈 DATA QUALITY
{'─' * 60}
Total Readings: {summary_data.get('total_readings', 0)}
Data Quality Score: {summary_data.get('data_quality_score', 0):.1f}%
Overall Status: {summary_data.get('overall_status', 'unknown').upper()}

💨 EXHAUST FAN
{'─' * 60}
Activations: {summary_data.get('exhaust_fan_activations', 0)} times
Total Runtime: {summary_data.get('exhaust_fan_runtime_minutes', 0):.0f} minutes

{'=' * 60}

This summary has been automatically saved to Firestore.
View detailed analytics at: https://cropverse-{os.getenv('FIREBASE_PROJECT_ID', 'xxxxx')}.web.app/analytics.html

---
CropVerse Agricultural Monitoring System
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
    
    # Send email
    send_email_notification(
        to_email=admin_email,
        subject=subject,
        body=body
    )
    
    logger.info(f"Summary email sent to {admin_email}")


def _send_error_email(target_date: date, error_message: str) -> None:
    """
    Send error notification email to admin.
    
    Args:
        target_date: Date that failed to process
        error_message: Error description
    """
    admin_email = os.getenv('ADMIN_EMAIL')
    if not admin_email:
        return
    
    subject = f"⚠️ CropVerse Daily Summary FAILED - {target_date}"
    
    body = f"""
Daily Analytics Summary Generation FAILED
{'=' * 60}

Date: {target_date}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

ERROR MESSAGE:
{error_message}

{'=' * 60}

Please investigate this issue. The daily summary for {target_date}
was not generated and may need to be manually calculated.

You can manually trigger the summary calculation using the
manual_trigger_summary() function in scheduled/daily_summary.py

---
CropVerse Agricultural Monitoring System
"""
    
    send_email_notification(
        to_email=admin_email,
        subject=subject,
        body=body
    )
    
    logger.info(f"Error email sent to {admin_email}")


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

def test_daily_summary():
    """
    Test function for local development.
    
    Calculates summary for yesterday and prints results.
    
    Usage:
        python -c "from scheduled.daily_summary import test_daily_summary; test_daily_summary()"
    """
    print("=" * 60)
    print("🧪 Testing Daily Summary Calculation")
    print("=" * 60)
    
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    print(f"📅 Calculating summary for: {yesterday}")
    print()
    
    result = calculate_and_save_daily_summary(yesterday)
    
    print("📊 RESULT:")
    print(f"  Success: {result['success']}")
    print(f"  Date: {result['date']}")
    print(f"  Message: {result['message']}")
    print()
    
    if result['success'] and result['summary']:
        summary = result['summary']
        print("📈 SUMMARY DATA:")
        print(f"  Total Readings: {summary.get('total_readings', 0)}")
        print(f"  Alerts: {summary.get('alert_count', 0)}")
        print(f"  Avg Temperature: {summary.get('avg_temperature', 0):.1f}°C")
        print(f"  Avg Humidity: {summary.get('avg_humidity', 0):.1f}%")
        print(f"  Status: {summary.get('overall_status', 'unknown')}")
    
    print("=" * 60)


if __name__ == '__main__':
    """Run test when executed directly."""
    test_daily_summary()