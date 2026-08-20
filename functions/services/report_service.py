"""
Report Service
==============
Generate downloadable reports (CSV, PDF) for sensor data, alerts, and analytics.

Functions:
- generate_csv_report(start_date, end_date, report_type='readings') - Generate CSV report
- generate_pdf_report(start_date, end_date, report_type='summary') - Generate PDF report
- upload_to_storage(file_path, destination_path) - Upload file to Firebase Storage
- get_signed_url(file_path, expiration_minutes=60) - Get temporary download URL
- delete_report(file_path) - Delete report from storage
- cleanup_old_reports(days_old=7) - Remove old reports from storage

Report Types:
- 'readings': Raw sensor readings with timestamps
- 'alerts': Alert history with resolution status
- 'summary': Daily analytics summaries
- 'full': Complete data export (readings + alerts + summaries)

Features:
- Date range filtering
- CSV export with pandas
- PDF generation with ReportLab
- Firebase Storage integration
- Signed URLs with expiration
- Automatic cleanup of old reports
"""

import os
import csv
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from firebase_admin import firestore, storage

from utils.logger import setup_logger
from models.sensor_reading import SensorReading
from models.alert import Alert
from models.analytics_summary import AnalyticsSummary
from utils.validators import validate_date_range

logger = setup_logger(__name__)

# Initialize Firestore and Storage
db = firestore.client()
bucket = storage.bucket()

# Report configuration
REPORTS_FOLDER = 'reports'
DEFAULT_EXPIRATION_MINUTES = 60


def _query_sensor_readings(start_date: datetime, end_date: datetime) -> List[SensorReading]:
    """
    Query sensor readings within date range.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        List of SensorReading objects
    """
    try:
        logger.info(f"Querying sensor readings from {start_date} to {end_date}")
        
        readings_ref = db.collection('sensor_readings')
        query = readings_ref.where('timestamp', '>=', start_date).where('timestamp', '<=', end_date)
        query = query.order_by('timestamp', direction=firestore.Query.ASCENDING)
        
        readings = []
        for doc in query.stream():
            reading = SensorReading.from_dict(doc.to_dict())
            readings.append(reading)
        
        logger.info(f"Retrieved {len(readings)} sensor readings")
        return readings
        
    except Exception as e:
        logger.error(f"Failed to query sensor readings: {str(e)}")
        return []


def _query_alerts(start_date: datetime, end_date: datetime) -> List[Alert]:
    """
    Query alerts within date range.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        List of Alert objects
    """
    try:
        logger.info(f"Querying alerts from {start_date} to {end_date}")
        
        alerts_ref = db.collection('alerts')
        query = alerts_ref.where('created_at', '>=', start_date).where('created_at', '<=', end_date)
        query = query.order_by('created_at', direction=firestore.Query.ASCENDING)
        
        alerts = []
        for doc in query.stream():
            alert = Alert.from_dict(doc.to_dict())
            alerts.append(alert)
        
        logger.info(f"Retrieved {len(alerts)} alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to query alerts: {str(e)}")
        return []


def _query_analytics_summaries(start_date: datetime, end_date: datetime) -> List[AnalyticsSummary]:
    """
    Query analytics summaries within date range.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        List of AnalyticsSummary objects
    """
    try:
        logger.info(f"Querying analytics summaries from {start_date} to {end_date}")
        
        # Convert to date objects for comparison
        start_date_only = start_date.date()
        end_date_only = end_date.date()
        
        summaries_ref = db.collection('analytics_summary')
        query = summaries_ref.where('date', '>=', start_date_only).where('date', '<=', end_date_only)
        query = query.order_by('date', direction=firestore.Query.ASCENDING)
        
        summaries = []
        for doc in query.stream():
            summary = AnalyticsSummary.from_dict(doc.to_dict())
            summaries.append(summary)
        
        logger.info(f"Retrieved {len(summaries)} analytics summaries")
        return summaries
        
    except Exception as e:
        logger.error(f"Failed to query analytics summaries: {str(e)}")
        return []


def generate_csv_report(
    start_date: datetime,
    end_date: datetime,
    report_type: str = 'readings'
) -> Dict[str, Any]:
    """
    Generate CSV report for specified date range and type.
    
    Args:
        start_date: Start datetime for report
        end_date: End datetime for report
        report_type: Type of report ('readings', 'alerts', 'summary', 'full')
        
    Returns:
        Dictionary with report metadata:
        {
            'success': bool,
            'file_path': str (Storage path),
            'download_url': str (Signed URL),
            'filename': str,
            'size_bytes': int,
            'row_count': int,
            'error': str (if failed)
        }
        
    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(days=7)
        >>> result = generate_csv_report(start, end, 'readings')
        >>> if result['success']:
        ...     print(f"Download: {result['download_url']}")
    """
    try:
        # Validate date range
        validate_date_range(start_date, end_date)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cropverse_{report_type}_{timestamp}.csv"
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', newline='', delete=False, suffix='.csv')
        temp_path = temp_file.name
        
        try:
            writer = csv.writer(temp_file)
            row_count = 0
            
            # Generate report based on type
            if report_type == 'readings':
                # Sensor readings report
                writer.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'Methane (ppm)', 
                               'Other Gases (ppm)', 'Exhaust Fan', 'Air Quality'])
                
                readings = _query_sensor_readings(start_date, end_date)
                for reading in readings:
                    writer.writerow([
                        reading.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        reading.temperature,
                        reading.humidity,
                        reading.methane,
                        reading.other_gases,
                        'ON' if reading.exhaust_fan else 'OFF',
                        reading.calculate_air_quality_status()
                    ])
                    row_count += 1
            
            elif report_type == 'alerts':
                # Alerts report
                writer.writerow(['Created At', 'Sensor Type', 'Alert Type', 'Message', 
                               'Value', 'Threshold', 'Unit', 'Resolved', 'Resolved At'])
                
                alerts = _query_alerts(start_date, end_date)
                for alert in alerts:
                    writer.writerow([
                        alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        alert.sensor_type,
                        alert.alert_type,
                        alert.message,
                        alert.value,
                        alert.threshold,
                        alert.get_unit(),
                        'Yes' if alert.is_resolved else 'No',
                        alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else 'N/A'
                    ])
                    row_count += 1
            
            elif report_type == 'summary':
                # Analytics summary report
                writer.writerow(['Date', 'Avg Temp (°C)', 'Max Temp (°C)', 'Min Temp (°C)',
                               'Avg Humidity (%)', 'Max Humidity (%)', 'Min Humidity (%)',
                               'Avg Methane (ppm)', 'Max Methane (ppm)', 'Min Methane (ppm)',
                               'Total Alerts', 'Critical Alerts', 'Warning Alerts', 
                               'Data Quality', 'Overall Status'])
                
                summaries = _query_analytics_summaries(start_date, end_date)
                for summary in summaries:
                    writer.writerow([
                        summary.date.strftime('%Y-%m-%d'),
                        round(summary.avg_temperature, 2),
                        round(summary.max_temperature, 2),
                        round(summary.min_temperature, 2),
                        round(summary.avg_humidity, 2),
                        round(summary.max_humidity, 2),
                        round(summary.min_humidity, 2),
                        round(summary.avg_methane, 2),
                        round(summary.max_methane, 2),
                        round(summary.min_methane, 2),
                        summary.total_alert_count,
                        summary.critical_alert_count,
                        summary.warning_alert_count,
                        f"{summary.data_quality_score:.1f}%",
                        summary.overall_status
                    ])
                    row_count += 1
            
            elif report_type == 'full':
                # Full export with multiple sheets (CSV doesn't support sheets, so separate sections)
                writer.writerow(['=== SENSOR READINGS ==='])
                writer.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'Methane (ppm)', 
                               'Other Gases (ppm)', 'Exhaust Fan', 'Air Quality'])
                
                readings = _query_sensor_readings(start_date, end_date)
                for reading in readings:
                    writer.writerow([
                        reading.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        reading.temperature,
                        reading.humidity,
                        reading.methane,
                        reading.other_gases,
                        'ON' if reading.exhaust_fan else 'OFF',
                        reading.calculate_air_quality_status()
                    ])
                    row_count += 1
                
                writer.writerow([])  # Empty row separator
                writer.writerow(['=== ALERTS ==='])
                writer.writerow(['Created At', 'Sensor Type', 'Alert Type', 'Message', 
                               'Value', 'Threshold', 'Resolved'])
                
                alerts = _query_alerts(start_date, end_date)
                for alert in alerts:
                    writer.writerow([
                        alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        alert.sensor_type,
                        alert.alert_type,
                        alert.message,
                        alert.value,
                        alert.threshold,
                        'Yes' if alert.is_resolved else 'No'
                    ])
                    row_count += 1
            
            else:
                raise ValueError(f"Invalid report_type: {report_type}. Must be 'readings', 'alerts', 'summary', or 'full'")
            
            temp_file.close()
            
            # Upload to Firebase Storage
            storage_path = f"{REPORTS_FOLDER}/{filename}"
            upload_result = upload_to_storage(temp_path, storage_path)
            
            if not upload_result['success']:
                raise Exception(f"Upload failed: {upload_result['error']}")
            
            # Get signed download URL
            download_url = get_signed_url(storage_path, DEFAULT_EXPIRATION_MINUTES)
            
            # Get file size
            file_size = os.path.getsize(temp_path)
            
            logger.info(f"CSV report generated successfully: {filename} ({row_count} rows, {file_size} bytes)")
            
            return {
                'success': True,
                'file_path': storage_path,
                'download_url': download_url,
                'filename': filename,
                'size_bytes': file_size,
                'row_count': row_count,
                'report_type': report_type,
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'error': None
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
        
    except ValueError as e:
        logger.warning(f"Invalid input for CSV report: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'file_path': None,
            'download_url': None,
            'filename': None,
            'size_bytes': 0,
            'row_count': 0
        }
    except Exception as e:
        logger.error(f"Failed to generate CSV report: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f"Report generation failed: {str(e)}",
            'file_path': None,
            'download_url': None,
            'filename': None,
            'size_bytes': 0,
            'row_count': 0
        }


def generate_pdf_report(
    start_date: datetime,
    end_date: datetime,
    report_type: str = 'summary'
) -> Dict[str, Any]:
    """
    Generate PDF report for specified date range and type.
    
    Note: PDF generation requires reportlab library. If not available,
          this function will return an error suggesting CSV format instead.
    
    Args:
        start_date: Start datetime for report
        end_date: End datetime for report
        report_type: Type of report ('summary' recommended for PDF)
        
    Returns:
        Dictionary with report metadata (same format as generate_csv_report)
        
    Example:
        >>> result = generate_pdf_report(start, end, 'summary')
        >>> if result['success']:
        ...     print(f"Download: {result['download_url']}")
    """
    try:
        # Check if reportlab is available
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
        except ImportError:
            logger.error("ReportLab library not installed")
            return {
                'success': False,
                'error': 'PDF generation not available. Please use CSV format instead or install reportlab library.',
                'file_path': None,
                'download_url': None,
                'filename': None,
                'size_bytes': 0,
                'row_count': 0
            }
        
        # Validate date range
        validate_date_range(start_date, end_date)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cropverse_{report_type}_{timestamp}.pdf"
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(temp_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2E7D32'),
                alignment=TA_CENTER
            )
            story.append(Paragraph("CropVerse Agricultural Report", title_style))
            story.append(Spacer(1, 0.3 * inch))
            
            # Report metadata
            meta_style = styles['Normal']
            story.append(Paragraph(f"<b>Report Type:</b> {report_type.title()}", meta_style))
            story.append(Paragraph(f"<b>Date Range:</b> {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", meta_style))
            story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
            story.append(Spacer(1, 0.5 * inch))
            
            row_count = 0
            
            # Generate content based on report type
            if report_type == 'summary':
                summaries = _query_analytics_summaries(start_date, end_date)
                
                if summaries:
                    # Create table data
                    data = [['Date', 'Avg Temp', 'Avg Humid', 'Avg CH₄', 'Alerts', 'Status']]
                    
                    for summary in summaries:
                        data.append([
                            summary.date.strftime('%Y-%m-%d'),
                            f"{summary.avg_temperature:.1f}°C",
                            f"{summary.avg_humidity:.1f}%",
                            f"{summary.avg_methane:.0f}ppm",
                            str(summary.total_alert_count),
                            summary.overall_status
                        ])
                        row_count += 1
                    
                    # Create table
                    table = Table(data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                else:
                    story.append(Paragraph("No data available for the selected date range.", styles['Normal']))
            
            else:
                story.append(Paragraph(f"PDF format is best suited for 'summary' reports. For detailed '{report_type}' data, please use CSV format.", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            # Upload to Firebase Storage
            storage_path = f"{REPORTS_FOLDER}/{filename}"
            upload_result = upload_to_storage(temp_path, storage_path)
            
            if not upload_result['success']:
                raise Exception(f"Upload failed: {upload_result['error']}")
            
            # Get signed download URL
            download_url = get_signed_url(storage_path, DEFAULT_EXPIRATION_MINUTES)
            
            # Get file size
            file_size = os.path.getsize(temp_path)
            
            logger.info(f"PDF report generated successfully: {filename} ({row_count} rows, {file_size} bytes)")
            
            return {
                'success': True,
                'file_path': storage_path,
                'download_url': download_url,
                'filename': filename,
                'size_bytes': file_size,
                'row_count': row_count,
                'report_type': report_type,
                'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'error': None
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
        
    except ValueError as e:
        logger.warning(f"Invalid input for PDF report: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'file_path': None,
            'download_url': None,
            'filename': None,
            'size_bytes': 0,
            'row_count': 0
        }
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f"Report generation failed: {str(e)}",
            'file_path': None,
            'download_url': None,
            'filename': None,
            'size_bytes': 0,
            'row_count': 0
        }


def upload_to_storage(local_path: str, storage_path: str) -> Dict[str, Any]:
    """
    Upload file to Firebase Storage.
    
    Args:
        local_path: Path to local file
        storage_path: Destination path in Firebase Storage
        
    Returns:
        Dictionary with upload result:
        {'success': bool, 'path': str, 'error': str}
    """
    try:
        logger.info(f"Uploading {local_path} to {storage_path}")
        
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(local_path)
        
        logger.info(f"File uploaded successfully to {storage_path}")
        return {
            'success': True,
            'path': storage_path,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Failed to upload to storage: {str(e)}")
        return {
            'success': False,
            'path': None,
            'error': str(e)
        }


def get_signed_url(storage_path: str, expiration_minutes: int = 60) -> Optional[str]:
    """
    Get signed URL for temporary file access.
    
    Args:
        storage_path: Path in Firebase Storage
        expiration_minutes: URL expiration time in minutes (default: 60)
        
    Returns:
        Signed URL string or None if failed
        
    Example:
        >>> url = get_signed_url('reports/cropverse_readings_20251130.csv', 120)
        >>> print(f"Download (valid for 2 hours): {url}")
    """
    try:
        blob = bucket.blob(storage_path)
        expiration = timedelta(minutes=expiration_minutes)
        
        url = blob.generate_signed_url(expiration=expiration)
        logger.info(f"Generated signed URL for {storage_path} (expires in {expiration_minutes} minutes)")
        
        return url
        
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {str(e)}")
        return None


def delete_report(storage_path: str) -> bool:
    """
    Delete report from Firebase Storage.
    
    Args:
        storage_path: Path in Firebase Storage
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        blob = bucket.blob(storage_path)
        blob.delete()
        
        logger.info(f"Deleted report: {storage_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete report: {str(e)}")
        return False


def cleanup_old_reports(days_old: int = 7) -> Dict[str, Any]:
    """
    Delete reports older than specified days from Firebase Storage.
    
    Args:
        days_old: Delete reports older than this many days (default: 7)
        
    Returns:
        Dictionary with cleanup results:
        {'success': bool, 'deleted_count': int, 'error': str}
        
    Example:
        >>> result = cleanup_old_reports(days_old=30)
        >>> print(f"Deleted {result['deleted_count']} old reports")
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        logger.info(f"Cleaning up reports older than {cutoff_date}")
        
        blobs = bucket.list_blobs(prefix=REPORTS_FOLDER)
        deleted_count = 0
        
        for blob in blobs:
            # Check if blob is older than cutoff
            if blob.time_created and blob.time_created.replace(tzinfo=None) < cutoff_date:
                blob.delete()
                deleted_count += 1
                logger.debug(f"Deleted old report: {blob.name}")
        
        logger.info(f"Cleanup complete: deleted {deleted_count} old reports")
        return {
            'success': True,
            'deleted_count': deleted_count,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old reports: {str(e)}")
        return {
            'success': False,
            'deleted_count': 0,
            'error': str(e)
        }


# Module-level test function
if __name__ == "__main__":
    """Test report service"""
    from datetime import datetime, timedelta
    
    print("Testing Report Service...")
    print("=" * 50)
    
    # Define test date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"\nDate Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Test CSV report generation
    print("\n1. Generating CSV report (readings)...")
    csv_result = generate_csv_report(start_date, end_date, 'readings')
    
    if csv_result['success']:
        print(f"✅ CSV report generated successfully")
        print(f"   Filename: {csv_result['filename']}")
        print(f"   Rows: {csv_result['row_count']}")
        print(f"   Size: {csv_result['size_bytes']} bytes")
        print(f"   Download: {csv_result['download_url'][:80]}...")
    else:
        print(f"❌ CSV generation failed: {csv_result['error']}")
    
    # Test PDF report generation
    print("\n2. Generating PDF report (summary)...")
    pdf_result = generate_pdf_report(start_date, end_date, 'summary')
    
    if pdf_result['success']:
        print(f"✅ PDF report generated successfully")
        print(f"   Filename: {pdf_result['filename']}")
        print(f"   Rows: {pdf_result['row_count']}")
        print(f"   Size: {pdf_result['size_bytes']} bytes")
    else:
        print(f"❌ PDF generation failed: {pdf_result['error']}")
    
    # Test cleanup (optional - commented out to avoid accidental deletion)
    # print("\n3. Testing cleanup of old reports...")
    # cleanup_result = cleanup_old_reports(days_old=30)
    # print(f"Deleted {cleanup_result['deleted_count']} old reports")
    
    print("\n" + "=" * 50)
    print("Report service tests complete!")