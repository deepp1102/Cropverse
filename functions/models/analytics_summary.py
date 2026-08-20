"""
Analytics Summary Model
=======================
Represents pre-calculated daily analytics for fast data retrieval.

Instead of querying 17,280 sensor readings for a day (1 reading/5 sec),
we query ONE summary document = 99.99% faster! 

This model is populated by the daily_summary scheduled job that runs at midnight.

Fields:
- summary_date: Date of the summary (used as document ID)
- avg_temperature: Average temperature for the day
- max_temperature: Maximum temperature recorded
- min_temperature: Minimum temperature recorded
- avg_humidity: Average humidity for the day
- max_humidity: Maximum humidity recorded
- min_humidity: Minimum humidity recorded
- avg_methane: Average methane level
- max_methane: Maximum methane level
- avg_other_gases: Average other gases level
- alert_count: Total alerts triggered
- critical_alert_count: Critical alerts only
- reading_count: Number of sensor readings processed
"""

from datetime import date, datetime
from typing import Dict, Any, Optional


class AnalyticsSummary:
    """Represents pre-calculated daily analytics summary"""
    
    def __init__(
        self,
        summary_date: date,
        avg_temperature: float,
        max_temperature: float,
        min_temperature: float,
        avg_humidity: float,
        max_humidity: float,
        min_humidity: float,
        avg_methane: float,
        max_methane: int,
        avg_other_gases: float,
        alert_count: int,
        critical_alert_count: int,
        reading_count: int,
        doc_id: Optional[str] = None
    ):
        """
        Initialize an analytics summary.
        
        Args:
            summary_date: Date of the summary
            avg_temperature: Average temperature (°C)
            max_temperature: Maximum temperature (°C)
            min_temperature: Minimum temperature (°C)
            avg_humidity: Average humidity (%)
            max_humidity: Maximum humidity (%)
            min_humidity: Minimum humidity (%)
            avg_methane: Average methane level (ppm)
            max_methane: Maximum methane level (ppm)
            avg_other_gases: Average other gases level
            alert_count: Total number of alerts
            critical_alert_count: Number of critical alerts
            reading_count: Number of sensor readings processed
            doc_id: Firestore document ID (typically date string: YYYY-MM-DD)
        """
        self.summary_date = summary_date
        self.avg_temperature = round(avg_temperature, 2)
        self.max_temperature = round(max_temperature, 2)
        self.min_temperature = round(min_temperature, 2)
        self.avg_humidity = round(avg_humidity, 2)
        self.max_humidity = round(max_humidity, 2)
        self.min_humidity = round(min_humidity, 2)
        self.avg_methane = round(avg_methane, 2)
        self.max_methane = int(max_methane)
        self.avg_other_gases = round(avg_other_gases, 2)
        self.alert_count = int(alert_count)
        self.critical_alert_count = int(critical_alert_count)
        self.reading_count = int(reading_count)
        self.doc_id = doc_id or summary_date.isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for Firestore storage.
        
        Returns:
            Dictionary with all analytics data
        """
        return {
            'date': self.summary_date.isoformat(),
            'avg_temperature': self.avg_temperature,
            'max_temperature': self.max_temperature,
            'min_temperature': self.min_temperature,
            'avg_humidity': self.avg_humidity,
            'max_humidity': self.max_humidity,
            'min_humidity': self.min_humidity,
            'avg_methane': self.avg_methane,
            'max_methane': self.max_methane,
            'avg_other_gases': self.avg_other_gases,
            'alert_count': self.alert_count,
            'critical_alert_count': self.critical_alert_count,
            'reading_count': self.reading_count
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], doc_id: Optional[str] = None) -> 'AnalyticsSummary':
        """
        Create AnalyticsSummary from Firestore document.
        
        Args:
            data: Dictionary from Firestore
            doc_id: Document ID
            
        Returns:
            AnalyticsSummary instance
        """
        # Parse date from string
        date_str = data.get('date', '')
        summary_date = datetime.fromisoformat(date_str).date() if date_str else date.today()
        
        return AnalyticsSummary(
            summary_date=summary_date,
            avg_temperature=data.get('avg_temperature', 0.0),
            max_temperature=data.get('max_temperature', 0.0),
            min_temperature=data.get('min_temperature', 0.0),
            avg_humidity=data.get('avg_humidity', 0.0),
            max_humidity=data.get('max_humidity', 0.0),
            min_humidity=data.get('min_humidity', 0.0),
            avg_methane=data.get('avg_methane', 0.0),
            max_methane=data.get('max_methane', 0),
            avg_other_gases=data.get('avg_other_gases', 0.0),
            alert_count=data.get('alert_count', 0),
            critical_alert_count=data.get('critical_alert_count', 0),
            reading_count=data.get('reading_count', 0),
            doc_id=doc_id
        )
    
    def get_temperature_range(self) -> float:
        """
        Calculate temperature range (max - min).
        
        Returns:
            Temperature range in °C
        """
        return round(self.max_temperature - self.min_temperature, 2)
    
    def get_humidity_range(self) -> float:
        """
        Calculate humidity range (max - min).
        
        Returns:
            Humidity range in %
        """
        return round(self.max_humidity - self.min_humidity, 2)
    
    def get_alert_rate(self) -> float:
        """
        Calculate alert rate (alerts per reading).
        
        Returns:
            Percentage of readings that triggered alerts
        """
        if self.reading_count == 0:
            return 0.0
        return round((self.alert_count / self.reading_count) * 100, 2)
    
    def get_critical_alert_percentage(self) -> float:
        """
        Calculate percentage of alerts that were critical.
        
        Returns:
            Percentage of critical alerts
        """
        if self.alert_count == 0:
            return 0.0
        return round((self.critical_alert_count / self.alert_count) * 100, 2)
    
    def is_temperature_stable(self, threshold: float = 5.0) -> bool:
        """
        Check if temperature was stable (low variation).
        
        Args:
            threshold: Maximum acceptable range in °C (default: 5.0)
            
        Returns:
            True if temperature range is within threshold
        """
        return self.get_temperature_range() <= threshold
    
    def is_humidity_stable(self, threshold: float = 10.0) -> bool:
        """
        Check if humidity was stable (low variation).
        
        Args:
            threshold: Maximum acceptable range in % (default: 10.0)
            
        Returns:
            True if humidity range is within threshold
        """
        return self.get_humidity_range() <= threshold
    
    def had_critical_alerts(self) -> bool:
        """
        Check if any critical alerts occurred.
        
        Returns:
            True if critical alerts were triggered
        """
        return self.critical_alert_count > 0
    
    def get_data_quality_score(self) -> float:
        """
        Calculate data quality score based on reading count.
        Expected: 17,280 readings per day (1 reading every 5 seconds)
        
        Returns:
            Quality score from 0-100
        """
        expected_readings = 17280  # 24 hours * 60 min * 60 sec / 5 sec
        if self.reading_count >= expected_readings:
            return 100.0
        return round((self.reading_count / expected_readings) * 100, 2)
    
    def get_overall_status(self) -> str:
        """
        Get overall status for the day based on multiple factors.
        
        Returns:
            Status string: 'Excellent', 'Good', 'Fair', 'Poor', 'Critical'
        """
        # Critical if any critical alerts
        if self.critical_alert_count > 0:
            return 'Critical'
        
        # Poor if many alerts
        if self.alert_count > 20:
            return 'Poor'
        
        # Fair if some alerts or unstable conditions
        if self.alert_count > 5 or not self.is_temperature_stable() or not self.is_humidity_stable():
            return 'Fair'
        
        # Good if few alerts
        if self.alert_count > 0:
            return 'Good'
        
        # Excellent if no alerts
        return 'Excellent'
    
    def get_status_emoji(self) -> str:
        """
        Get emoji representing overall status.
        
        Returns:
            Emoji string
        """
        status_emojis = {
            'Excellent': '✅',
            'Good': '👍',
            'Fair': '⚠️',
            'Poor': '😟',
            'Critical': '🚨'
        }
        return status_emojis.get(self.get_overall_status(), '❓')
    
    def format_summary_report(self) -> str:
        """
        Format a human-readable summary report.
        
        Returns:
            Multi-line summary report string
        """
        emoji = self.get_status_emoji()
        status = self.get_overall_status()
        
        return f"""
Daily Summary Report - {self.summary_date.strftime('%B %d, %Y')}
{'=' * 60}
Overall Status: {emoji} {status}

Temperature:
  Average: {self.avg_temperature}°C
  Range: {self.min_temperature}°C - {self.max_temperature}°C (Δ {self.get_temperature_range()}°C)
  Stability: {'✓ Stable' if self.is_temperature_stable() else '✗ Unstable'}

Humidity:
  Average: {self.avg_humidity}%
  Range: {self.min_humidity}% - {self.max_humidity}% (Δ {self.get_humidity_range()}%)
  Stability: {'✓ Stable' if self.is_humidity_stable() else '✗ Unstable'}

Methane:
  Average: {self.avg_methane} ppm
  Maximum: {self.max_methane} ppm

Alerts:
  Total Alerts: {self.alert_count}
  Critical Alerts: {self.critical_alert_count}
  Alert Rate: {self.get_alert_rate()}%

Data Quality:
  Readings Collected: {self.reading_count:,}
  Quality Score: {self.get_data_quality_score()}%
{'=' * 60}
        """
    
    def __str__(self) -> str:
        """String representation of analytics summary"""
        return (
            f"AnalyticsSummary({self.summary_date}): "
            f"Temp={self.avg_temperature}°C, "
            f"Humidity={self.avg_humidity}%, "
            f"Alerts={self.alert_count} "
            f"[{self.get_overall_status()}]"
        )
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return (
            f"AnalyticsSummary(date={self.summary_date}, "
            f"readings={self.reading_count}, "
            f"alerts={self.alert_count})"
        )