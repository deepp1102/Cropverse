"""
Analytics Service
=================
Statistical analysis and trend calculation service.

This service processes sensor data to generate insights:
- Trend analysis (7/30/90 day trends)
- Correlation analysis (sensor relationships)
- Daily summaries (pre-calculated aggregations)
- Statistical metrics (mean, median, std, min, max)

Uses pandas and numpy for efficient data processing.

Functions:
- get_trends(days): Calculate trend data for specified period
- get_correlations(): Calculate correlation matrix between sensors
- calculate_daily_summary(date): Generate daily aggregated summary
- get_summary_for_date_range(start_date, end_date): Get summaries for date range
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np

from models import SensorReading, AnalyticsSummary
from utils.logger import setup_logger
from .firestore_service import (
    get_readings_in_range,
    get_analytics_summary,
    save_analytics_summary,
    get_recent_alerts
)

# Initialize logger
logger = setup_logger(__name__)


def get_trends(days: int = 7) -> Dict[str, Any]:
    """
    Calculate trend analysis for the specified number of days.
    
    Retrieves sensor readings from the past N days and calculates:
    - Daily averages for each sensor
    - Overall trends (increasing/decreasing/stable)
    - Min/max values
    - Standard deviation
    
    Args:
        days: Number of days to analyze (default: 7)
              Common values: 7 (week), 30 (month), 90 (quarter)
              
    Returns:
        Dictionary with trend data:
        {
            'period': {start_date, end_date, days},
            'temperature': {daily_avg, trend, min, max, std},
            'humidity': {daily_avg, trend, min, max, std},
            'methane': {daily_avg, trend, min, max, std},
            'other_gases': {daily_avg, trend, min, max, std},
            'data_points': number of readings analyzed
        }
        
    Example:
        >>> trends = get_trends(7)
        >>> print(f"Temperature trend: {trends['temperature']['trend']}")
        >>> print(f"Avg temp last 7 days: {trends['temperature']['overall_avg']:.1f}°C")
    """
    try:
        logger.info(f"Calculating trends for last {days} days")
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Fetch readings
        readings = get_readings_in_range(start_date, end_date)
        
        if not readings:
            logger.warning(f"No readings found for {days}-day period")
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'error': 'No data available for this period',
                'data_points': 0
            }
        
        logger.info(f"Analyzing {len(readings)} readings")
        
        # Convert to pandas DataFrame
        df = _readings_to_dataframe(readings)
        
        # Calculate trends for each sensor
        temperature_trends = _calculate_sensor_trends(df, 'temperature')
        humidity_trends = _calculate_sensor_trends(df, 'humidity')
        methane_trends = _calculate_sensor_trends(df, 'methane')
        other_gases_trends = _calculate_sensor_trends(df, 'other_gases')
        
        result = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'temperature': temperature_trends,
            'humidity': humidity_trends,
            'methane': methane_trends,
            'other_gases': other_gases_trends,
            'data_points': len(readings)
        }
        
        logger.info(f"Trend analysis completed for {days} days")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating trends: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'data_points': 0
        }


def _readings_to_dataframe(readings: List[SensorReading]) -> pd.DataFrame:
    """
    Convert list of SensorReading objects to pandas DataFrame.
    
    Args:
        readings: List of SensorReading objects
        
    Returns:
        DataFrame with columns: timestamp, temperature, humidity, methane, other_gases
    """
    data = []
    for reading in readings:
        data.append({
            'timestamp': reading.timestamp,
            'temperature': reading.temperature,
            'humidity': reading.humidity,
            'methane': reading.methane,
            'other_gases': reading.other_gases
        })
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    return df


def _calculate_sensor_trends(df: pd.DataFrame, sensor_name: str) -> Dict[str, Any]:
    """
    Calculate trend statistics for a single sensor.
    
    Args:
        df: DataFrame with sensor data
        sensor_name: Name of sensor column
        
    Returns:
        Dictionary with trend statistics
    """
    try:
        values = df[sensor_name]
        
        # Basic statistics
        overall_avg = float(values.mean())
        overall_min = float(values.min())
        overall_max = float(values.max())
        overall_std = float(values.std())
        
        # Daily averages
        df['date'] = df['timestamp'].dt.date
        daily_avg = df.groupby('date')[sensor_name].mean()
        
        # Calculate trend direction
        if len(daily_avg) >= 2:
            # Linear regression to determine trend
            x = np.arange(len(daily_avg))
            y = daily_avg.values
            slope = np.polyfit(x, y, 1)[0]
            
            # Classify trend
            if abs(slope) < 0.1:  # Threshold for "stable"
                trend = 'stable'
            elif slope > 0:
                trend = 'increasing'
            else:
                trend = 'decreasing'
            
            trend_strength = abs(slope)
        else:
            trend = 'insufficient_data'
            trend_strength = 0.0
        
        # Daily breakdown
        daily_data = []
        for date_val, avg_val in daily_avg.items():
            daily_data.append({
                'date': date_val.isoformat(),
                'average': float(avg_val)
            })
        
        return {
            'overall_avg': round(overall_avg, 2),
            'overall_min': round(overall_min, 2),
            'overall_max': round(overall_max, 2),
            'overall_std': round(overall_std, 2),
            'trend': trend,
            'trend_strength': round(trend_strength, 4),
            'daily_averages': daily_data
        }
        
    except Exception as e:
        logger.error(f"Error calculating trends for {sensor_name}: {str(e)}")
        return {
            'error': str(e)
        }


def get_correlations() -> Dict[str, Any]:
    """
    Calculate correlation matrix between sensor readings.
    
    Shows how different sensors relate to each other:
    - Positive correlation: sensors increase/decrease together
    - Negative correlation: one increases when other decreases
    - Zero correlation: no relationship
    
    Returns:
        Dictionary with correlation matrix:
        {
            'matrix': {
                'temperature_humidity': 0.65,
                'temperature_methane': -0.23,
                ...
            },
            'data_points': number of readings analyzed,
            'period': date range analyzed
        }
        
    Example:
        >>> correlations = get_correlations()
        >>> temp_humidity = correlations['matrix']['temperature_humidity']
        >>> print(f"Temperature-Humidity correlation: {temp_humidity:.2f}")
    """
    try:
        logger.info("Calculating sensor correlations")
        
        # Get last 7 days of data for correlation analysis
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        readings = get_readings_in_range(start_date, end_date)
        
        if len(readings) < 10:
            logger.warning("Insufficient data for correlation analysis")
            return {
                'error': 'Insufficient data (minimum 10 readings required)',
                'data_points': len(readings)
            }
        
        # Convert to DataFrame
        df = _readings_to_dataframe(readings)
        
        # Calculate correlation matrix
        sensors = ['temperature', 'humidity', 'methane', 'other_gases']
        corr_matrix = df[sensors].corr()
        
        # Convert to dictionary format
        correlations = {}
        for i, sensor1 in enumerate(sensors):
            for j, sensor2 in enumerate(sensors):
                if i < j:  # Only upper triangle (avoid duplicates)
                    key = f"{sensor1}_{sensor2}"
                    value = float(corr_matrix.loc[sensor1, sensor2])
                    correlations[key] = round(value, 3)
        
        result = {
            'matrix': correlations,
            'data_points': len(readings),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
        
        logger.info("Correlation analysis completed")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating correlations: {str(e)}", exc_info=True)
        return {
            'error': str(e)
        }


def calculate_daily_summary(target_date: date) -> Optional[AnalyticsSummary]:
    """
    Calculate and save daily summary for a specific date.
    
    This function aggregates all sensor readings from a single day into
    a summary document. This makes analytics queries 99.99% faster!
    
    Called by: Scheduled Cloud Function (runs at midnight daily)
    
    Args:
        target_date: Date to summarize (typically yesterday)
        
    Returns:
        AnalyticsSummary object if successful, None if failed
        
    Example:
        >>> from datetime import date, timedelta
        >>> yesterday = date.today() - timedelta(days=1)
        >>> summary = calculate_daily_summary(yesterday)
        >>> if summary:
        ...     print(f"Avg temp: {summary.avg_temperature}°C")
        ...     print(f"Total alerts: {summary.alert_count}")
    """
    try:
        logger.info(f"Calculating daily summary for {target_date}")
        
        # Define date range (midnight to midnight)
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Fetch all readings for the day
        readings = get_readings_in_range(start_datetime, end_datetime)
        
        if not readings:
            logger.warning(f"No readings found for {target_date}")
            return None
        
        logger.info(f"Processing {len(readings)} readings for {target_date}")
        
        # Convert to DataFrame
        df = _readings_to_dataframe(readings)
        
        # Calculate aggregations
        avg_temperature = float(df['temperature'].mean())
        max_temperature = float(df['temperature'].max())
        min_temperature = float(df['temperature'].min())
        
        avg_humidity = float(df['humidity'].mean())
        max_humidity = float(df['humidity'].max())
        min_humidity = float(df['humidity'].min())
        
        avg_methane = float(df['methane'].mean())
        max_methane = int(df['methane'].max())
        
        avg_other_gases = float(df['other_gases'].mean())
        
        # Count alerts for the day
        # Note: This is a simple count. Could be optimized by querying alerts collection.
        alert_count = _count_alerts_for_date(start_datetime, end_datetime)
        critical_alert_count = _count_critical_alerts_for_date(start_datetime, end_datetime)
        
        # Create summary object
        summary = AnalyticsSummary(
            summary_date=target_date,
            avg_temperature=avg_temperature,
            max_temperature=max_temperature,
            min_temperature=min_temperature,
            avg_humidity=avg_humidity,
            max_humidity=max_humidity,
            min_humidity=min_humidity,
            avg_methane=avg_methane,
            max_methane=max_methane,
            avg_other_gases=avg_other_gases,
            alert_count=alert_count,
            critical_alert_count=critical_alert_count,
            reading_count=len(readings)
        )
        
        # Save to Firestore
        save_analytics_summary(summary)
        
        logger.info(f"Daily summary saved for {target_date}: "
                   f"Temp={avg_temperature:.1f}°C, "
                   f"Humidity={avg_humidity:.1f}%, "
                   f"Alerts={alert_count}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error calculating daily summary for {target_date}: {str(e)}", exc_info=True)
        return None


def _count_alerts_for_date(start_datetime: datetime, end_datetime: datetime) -> int:
    """
    Count alerts created within date range.
    
    Args:
        start_datetime: Start of range
        end_datetime: End of range
        
    Returns:
        Number of alerts
    """
    try:
        # Get recent alerts (this is not optimal, but works for MVP)
        # In production, would query alerts collection with date filter
        alerts = get_recent_alerts(limit=1000, unresolved_only=False)
        
        count = 0
        for alert in alerts:
            if alert.created_at and start_datetime <= alert.created_at <= end_datetime:
                count += 1
        
        return count
        
    except Exception as e:
        logger.error(f"Error counting alerts: {str(e)}")
        return 0


def _count_critical_alerts_for_date(start_datetime: datetime, end_datetime: datetime) -> int:
    """
    Count critical alerts created within date range.
    
    Args:
        start_datetime: Start of range
        end_datetime: End of range
        
    Returns:
        Number of critical alerts
    """
    try:
        alerts = get_recent_alerts(limit=1000, unresolved_only=False)
        
        count = 0
        for alert in alerts:
            if (alert.created_at and 
                start_datetime <= alert.created_at <= end_datetime and
                alert.is_critical()):
                count += 1
        
        return count
        
    except Exception as e:
        logger.error(f"Error counting critical alerts: {str(e)}")
        return 0


def get_summary_for_date_range(start_date: date, end_date: date) -> List[AnalyticsSummary]:
    """
    Get pre-calculated daily summaries for a date range.
    
    This is MUCH faster than querying raw sensor readings!
    Instead of 120,960 documents (7 days × 17,280 readings/day),
    we query just 7 summary documents.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        
    Returns:
        List of AnalyticsSummary objects, ordered by date
        
    Example:
        >>> from datetime import date, timedelta
        >>> end = date.today()
        >>> start = end - timedelta(days=7)
        >>> summaries = get_summary_for_date_range(start, end)
        >>> for summary in summaries:
        ...     print(f"{summary.summary_date}: Avg temp {summary.avg_temperature}°C")
    """
    try:
        logger.info(f"Fetching summaries from {start_date} to {end_date}")
        
        summaries = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            summary = get_analytics_summary(date_str)
            
            if summary:
                summaries.append(summary)
            else:
                logger.warning(f"No summary found for {date_str}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"Fetched {len(summaries)} daily summaries")
        return summaries
        
    except Exception as e:
        logger.error(f"Error fetching summary range: {str(e)}", exc_info=True)
        return []


def get_sensor_statistics(days: int = 7) -> Dict[str, Any]:
    """
    Get comprehensive statistics for all sensors.
    
    Combines trend analysis with additional statistical metrics.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dictionary with comprehensive statistics
        
    Example:
        >>> stats = get_sensor_statistics(30)
        >>> print(f"Temperature median: {stats['temperature']['median']}")
        >>> print(f"Methane 95th percentile: {stats['methane']['p95']}")
    """
    try:
        logger.info(f"Calculating statistics for {days} days")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        readings = get_readings_in_range(start_date, end_date)
        
        if not readings:
            return {'error': 'No data available'}
        
        df = _readings_to_dataframe(readings)
        
        result = {}
        for sensor in ['temperature', 'humidity', 'methane', 'other_gases']:
            values = df[sensor]
            
            result[sensor] = {
                'mean': round(float(values.mean()), 2),
                'median': round(float(values.median()), 2),
                'std': round(float(values.std()), 2),
                'min': round(float(values.min()), 2),
                'max': round(float(values.max()), 2),
                'p25': round(float(values.quantile(0.25)), 2),  # 25th percentile
                'p75': round(float(values.quantile(0.75)), 2),  # 75th percentile
                'p95': round(float(values.quantile(0.95)), 2),  # 95th percentile
                'range': round(float(values.max() - values.min()), 2)
            }
        
        result['data_points'] = len(readings)
        result['period'] = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days
        }
        
        logger.info("Statistics calculation completed")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {str(e)}", exc_info=True)
        return {'error': str(e)}


def generate_analytics_report(days: int = 7) -> Dict[str, Any]:
    """
    Generate comprehensive analytics report.
    
    Combines trends, correlations, statistics, and alerts into one report.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dictionary with complete analytics report
        
    Example:
        >>> report = generate_analytics_report(30)
        >>> print(f"Report period: {report['period']['days']} days")
        >>> print(f"Data quality: {report['data_quality_score']}%")
    """
    try:
        logger.info(f"Generating analytics report for {days} days")
        
        trends = get_trends(days)
        correlations = get_correlations()
        statistics = get_sensor_statistics(days)
        
        # Calculate data quality score
        expected_readings = days * 24 * 60 * 12  # Assuming 1 reading per 5 seconds
        actual_readings = trends.get('data_points', 0)
        data_quality_score = min(100, (actual_readings / expected_readings) * 100) if expected_readings > 0 else 0
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'period': trends.get('period', {}),
            'data_quality_score': round(data_quality_score, 2),
            'trends': trends,
            'correlations': correlations,
            'statistics': statistics
        }
        
        logger.info("Analytics report generated successfully")
        return report
        
    except Exception as e:
        logger.error(f"Error generating analytics report: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'generated_at': datetime.utcnow().isoformat()
        }
    

def get_daily_summary(target_date: date) -> Optional[AnalyticsSummary]:
    """
    Get (or compute) the daily summary for a single date.

    This is a convenience wrapper used by the routes.
    It first tries to fetch a pre-calculated summary.
    If none exists, it will calculate and save it.
    """
    try:
        logger.info(f"Fetching daily summary for {target_date}")

        # 1. Try to fetch pre-calculated summary
        date_str = target_date.isoformat()
        summary = get_analytics_summary(date_str)

        if summary:
            logger.info(f"Found existing summary for {date_str}")
            return summary

        logger.info(f"No existing summary for {date_str}, calculating now")
        # 2. If not present, calculate (this also saves it)
        return calculate_daily_summary(target_date)

    except Exception as e:
        logger.error(f"Error in get_daily_summary for {target_date}: {str(e)}", exc_info=True)
        return None    