"""
Analytics service for tracking agent metrics and insights.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import Counter, defaultdict

from src.core.logging import get_logger
from src.agents.conversation_manager import (
    ConversationManager,
    ConversationStats,
    ConversationMetadata
)


logger = get_logger(__name__)


class TimeGranularity(Enum):
    """Time granularity for analytics."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricType(Enum):
    """Types of metrics to track."""
    QUERY_COUNT = "query_count"
    RESPONSE_TIME = "response_time"
    CONFIDENCE_SCORE = "confidence_score"
    TOOL_USAGE = "tool_usage"
    REFLECTION_RATE = "reflection_rate"
    REFINEMENT_RATE = "refinement_rate"
    ERROR_RATE = "error_rate"
    CONVERSATION_LENGTH = "conversation_length"
    USER_ENGAGEMENT = "user_engagement"
    SUCCESS_RATE = "success_rate"


@dataclass
class MetricDataPoint:
    """A single data point for a metric."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels,
            "metadata": self.metadata
        }


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    metric_type: str
    count: int
    sum_value: float
    avg_value: float
    min_value: float
    max_value: float
    median_value: float
    std_dev: float
    percentile_25: float
    percentile_75: float
    time_range: Tuple[datetime, datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type,
            "count": self.count,
            "sum": self.sum_value,
            "avg": self.avg_value,
            "min": self.min_value,
            "max": self.max_value,
            "median": self.median_value,
            "std_dev": self.std_dev,
            "percentile_25": self.percentile_25,
            "percentile_75": self.percentile_75,
            "time_range": (self.time_range[0].isoformat(), self.time_range[1].isoformat())
        }


@dataclass
class TrendAnalysis:
    """Analysis of metric trends."""
    metric_type: str
    trend: str  # "increasing", "decreasing", "stable", "volatile"
    slope: float  # Rate of change per day
    r_squared: float  # Correlation coefficient
    prediction_7d: Optional[float] = None  # Predicted value in 7 days
    confidence_interval: Optional[Tuple[float, float]] = None
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type,
            "trend": self.trend,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "prediction_7d": self.prediction_7d,
            "confidence_interval": self.confidence_interval,
            "anomalies": self.anomalies
        }


@dataclass
class Insight:
    """An analytical insight."""
    title: str
    description: str
    metric_type: str
    insight_type: str  # "trend", "anomaly", "recommendation", "observation"
    severity: str  # "info", "warning", "critical"
    value: Optional[float] = None
    comparison: Optional[str] = None
    action_suggestion: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "metric_type": self.metric_type,
            "insight_type": self.insight_type,
            "severity": self.severity,
            "value": self.value,
            "comparison": self.comparison,
            "action_suggestion": self.action_suggestion,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""
    generated_at: datetime
    time_range: Tuple[datetime, datetime]
    summaries: Dict[str, MetricSummary]
    trends: Dict[str, TrendAnalysis]
    insights: List[Insight]
    top_conversations: List[Dict[str, Any]]
    tool_usage: Dict[str, int]
    error_distribution: Dict[str, int]
    user_activity: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "time_range": (self.time_range[0].isoformat(), self.time_range[1].isoformat()),
            "summaries": {k: v.to_dict() for k, v in self.summaries.items()},
            "trends": {k: v.to_dict() for k, v in self.trends.items()},
            "insights": [i.to_dict() for i in self.insights],
            "top_conversations": self.top_conversations,
            "tool_usage": self.tool_usage,
            "error_distribution": self.error_distribution,
            "user_activity": self.user_activity
        }


class AnalyticsService:
    """
    Analytics service for tracking and analyzing agent metrics.
    
    Features:
    - Metric tracking and aggregation
    - Trend analysis and prediction
    - Anomaly detection
    - Insight generation
    - Custom reports
    - Real-time monitoring
    """
    
    def __init__(
        self,
        conversation_manager: ConversationManager,
        enable_anomaly_detection: bool = True,
        anomaly_threshold: float = 2.0  # Standard deviations
    ):
        """
        Initialize analytics service.
        
        Args:
            conversation_manager: Conversation manager instance
            enable_anomaly_detection: Whether to detect anomalies
            anomaly_threshold: Standard deviation threshold for anomalies
        """
        self.conversation_manager = conversation_manager
        self.enable_anomaly_detection = enable_anomaly_detection
        self.anomaly_threshold = anomaly_threshold
        
        # Metric storage
        self.metrics: Dict[str, List[MetricDataPoint]] = defaultdict(list)
        
        logger.info(
            "Analytics service initialized",
            enable_anomaly_detection=enable_anomaly_detection,
            anomaly_threshold=anomaly_threshold
        )
    
    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a metric data point.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            labels: Labels for grouping (e.g., {"tool": "retrieval"})
            timestamp: Timestamp (defaults to now)
            metadata: Additional metadata
        """
        data_point = MetricDataPoint(
            timestamp=timestamp or datetime.now(),
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.metrics[metric_type.value].append(data_point)
        
        logger.debug(
            "Metric recorded",
            metric_type=metric_type.value,
            value=value,
            labels=labels
        )
    
    def get_metric_summary(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[MetricSummary]:
        """
        Get summary statistics for a metric.
        
        Args:
            metric_type: Type of metric
            start_time: Start of time range
            end_time: End of time range
            labels: Filter by labels
            
        Returns:
            MetricSummary or None if no data
        """
        data_points = self._filter_metrics(
            metric_type.value,
            start_time,
            end_time,
            labels
        )
        
        if not data_points:
            return None
        
        values = [dp.value for dp in data_points]
        timestamps = [dp.timestamp for dp in data_points]
        
        try:
            return MetricSummary(
                metric_type=metric_type.value,
                count=len(values),
                sum_value=sum(values),
                avg_value=statistics.mean(values),
                min_value=min(values),
                max_value=max(values),
                median_value=statistics.median(values),
                std_dev=statistics.stdev(values) if len(values) > 1 else 0,
                percentile_25=statistics.quantiles(values, n=4)[0] if len(values) > 3 else min(values),
                percentile_75=statistics.quantiles(values, n=4)[2] if len(values) > 3 else max(values),
                time_range=(min(timestamps), max(timestamps))
            )
        except statistics.StatisticsError:
            return None
    
    def analyze_trend(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> Optional[TrendAnalysis]:
        """
        Analyze trend of a metric over time.
        
        Args:
            metric_type: Type of metric
            start_time: Start of analysis period
            end_time: End of analysis period
            granularity: Time granularity for analysis
            
        Returns:
            TrendAnalysis or None
        """
        data_points = self._filter_metrics(
            metric_type.value,
            start_time,
            end_time
        )
        
        if len(data_points) < 3:
            return None
        
        # Group by time granularity
        grouped = self._group_by_time(data_points, granularity)
        
        # Calculate linear regression
        times = [(t - grouped[0][0]).total_seconds() / 86400 for t, _ in grouped]  # Days
        values = [v for _, v in grouped]
        
        try:
            # Simple linear regression
            n = len(times)
            sum_x = sum(times)
            sum_y = sum(values)
            sum_xy = sum(t * v for t, v in zip(times, values))
            sum_x2 = sum(t ** 2 for t in times)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate R²
            y_mean = statistics.mean(values)
            ss_tot = sum((v - y_mean) ** 2 for v in values)
            ss_res = sum((v - (slope * t + intercept)) ** 2 for t, v in zip(times, values))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Determine trend
            if abs(slope) < 0.01:
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            # Check volatility
            volatility = statistics.stdev(values) if len(values) > 1 else 0
            if volatility > abs(statistics.mean(values)) * 0.5:
                trend = "volatile"
            
            # Predict 7 days ahead
            prediction_7d = slope * (times[-1] + 7) + intercept if times else None
            
            # Detect anomalies
            anomalies = []
            if self.enable_anomaly_detection and len(values) > 2:
                mean_val = statistics.mean(values)
                std_val = statistics.stdev(values)
                threshold = self.anomaly_threshold * std_val
                
                for i, (t, v) in enumerate(grouped):
                    if abs(v - mean_val) > threshold:
                        anomalies.append({
                            "timestamp": t.isoformat(),
                            "value": v,
                            "deviation": abs(v - mean_val) / std_val
                        })
            
            return TrendAnalysis(
                metric_type=metric_type.value,
                trend=trend,
                slope=slope,
                r_squared=r_squared,
                prediction_7d=prediction_7d,
                anomalies=anomalies
            )
            
        except (statistics.StatisticsError, ZeroDivisionError):
            return None
    
    def generate_insights(
        self,
        time_range: Tuple[datetime, datetime] = None
    ) -> List[Insight]:
        """
        Generate insights from analytics data.
        
        Args:
            time_range: Time range to analyze (defaults to last 7 days)
            
        Returns:
            List of insights
        """
        if not time_range:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            time_range = (start_time, end_time)
        
        insights = []
        
        # Analyze each metric type
        for metric_type in MetricType:
            try:
                summary = self.get_metric_summary(metric_type, *time_range)
                trend = self.analyze_trend(metric_type, *time_range)
                
                if summary and trend:
                    insights.extend(self._generate_metric_insights(metric_type, summary, trend))
            except Exception as e:
                logger.warning("Failed to generate insights for metric", metric_type=metric_type.value, error=str(e))
        
        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        insights.sort(key=lambda i: severity_order.get(i.severity, 3))
        
        return insights
    
    def _generate_metric_insights(
        self,
        metric_type: MetricType,
        summary: MetricSummary,
        trend: TrendAnalysis
    ) -> List[Insight]:
        """Generate insights for a specific metric."""
        insights = []
        
        # Trend-based insights
        if trend.trend == "increasing" and metric_type in [MetricType.ERROR_RATE, MetricType.RESPONSE_TIME]:
            insights.append(Insight(
                title=f"Rising {metric_type.value}",
                description=f"{metric_type.value.replace('_', ' ').title()} is increasing by {abs(trend.slope * 100):.1f}% per day",
                metric_type=metric_type.value,
                insight_type="trend",
                severity="warning",
                value=trend.slope,
                action_suggestion="Investigate the root cause and implement optimizations"
            ))
        
        if trend.trend == "decreasing" and metric_type == MetricType.CONFIDENCE_SCORE:
            insights.append(Insight(
                title="Declining Confidence",
                description=f"Agent confidence scores are dropping at {abs(trend.slope * 100):.1f}% per day",
                metric_type=metric_type.value,
                insight_type="trend",
                severity="warning",
                value=trend.slope,
                action_suggestion="Review recent queries and consider adjusting prompts or tools"
            ))
        
        # Anomaly insights
        if trend.anomalies:
            insights.append(Insight(
                title=f"Anomalies Detected in {metric_type.value}",
                description=f"Found {len(trend.anomalies)} anomalies in the data",
                metric_type=metric_type.value,
                insight_type="anomaly",
                severity="info" if len(trend.anomalies) < 3 else "warning",
                action_suggestion="Review the anomalous data points for potential issues"
            ))
        
        # Performance insights
        if metric_type == MetricType.RESPONSE_TIME:
            if summary.avg_value > 10.0:  # 10 seconds
                insights.append(Insight(
                    title="High Response Time",
                    description=f"Average response time is {summary.avg_value:.2f}s, which is above 10s",
                    metric_type=metric_type.value,
                    insight_type="recommendation",
                    severity="warning",
                    value=summary.avg_value,
                    action_suggestion="Consider optimizing tools or reducing query complexity"
                ))
        
        if metric_type == MetricType.SUCCESS_RATE:
            if summary.avg_value < 0.95:  # 95%
                insights.append(Insight(
                    title="Low Success Rate",
                    description=f"Success rate is {summary.avg_value * 100:.1f}%, below the 95% target",
                    metric_type=metric_type.value,
                    insight_type="recommendation",
                    severity="warning" if summary.avg_value < 0.9 else "info",
                    value=summary.avg_value,
                    action_suggestion="Review failed queries and improve error handling"
                ))
        
        return insights
    
    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_conversations: int = 10
    ) -> AnalyticsReport:
        """
        Generate a comprehensive analytics report.
        
        Args:
            start_time: Start of report period
            end_time: End of report period
            include_conversations: Number of top conversations to include
            
        Returns:
            AnalyticsReport
        """
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        # Generate summaries
        summaries = {}
        for metric_type in MetricType:
            summary = self.get_metric_summary(metric_type, start_time, end_time)
            if summary:
                summaries[metric_type.value] = summary
        
        # Analyze trends
        trends = {}
        for metric_type in MetricType:
            trend = self.analyze_trend(metric_type, start_time, end_time)
            if trend:
                trends[metric_type.value] = trend
        
        # Generate insights
        insights = self.generate_insights((start_time, end_time))
        
        # Get top conversations
        conversations = self.conversation_manager.list_conversations(limit=100)
        top_conversations = sorted(
            conversations,
            key=lambda c: c.get("metadata", {}).get("message_count", 0),
            reverse=True
        )[:include_conversations]
        
        # Aggregate tool usage from all conversations
        tool_usage = Counter()
        error_distribution = Counter()
        user_activity = Counter()
        
        for conv_id in self.conversation_manager.conversations:
            conv = self.conversation_manager.get_conversation(conv_id)
            if conv:
                stats = self.conversation_manager.get_conversation_stats(conv_id)
                if stats:
                    tool_usage.update(stats.tool_usage_count)
                    error_distribution.update({str(stats.error_count): 1})
                
                meta = self.conversation_manager.get_conversation_metadata(conv_id)
                if meta:
                    user_activity[meta.user_id] += 1
        
        return AnalyticsReport(
            generated_at=datetime.now(),
            time_range=(start_time, end_time),
            summaries=summaries,
            trends=trends,
            insights=insights,
            top_conversations=top_conversations,
            tool_usage=dict(tool_usage.most_common(10)),
            error_distribution=dict(error_distribution.most_common(10)),
            user_activity=dict(user_activity.most_common(10))
        )
    
    def get_realtime_metrics(
        self,
        metric_types: Optional[List[MetricType]] = None,
        last_minutes: int = 60
    ) -> Dict[str, List[MetricDataPoint]]:
        """
        Get recent metrics for real-time monitoring.
        
        Args:
            metric_types: Types to retrieve (all if None)
            last_minutes: How many minutes of data to retrieve
            
        Returns:
            Dictionary of metric type to data points
        """
        cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
        
        if not metric_types:
            metric_types = list(MetricType)
        
        result = {}
        for metric_type in metric_types:
            filtered = [
                dp for dp in self.metrics[metric_type.value]
                if dp.timestamp >= cutoff_time
            ]
            result[metric_type.value] = filtered
        
        return result
    
    def _filter_metrics(
        self,
        metric_type: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        labels: Optional[Dict[str, str]] = None
    ) -> List[MetricDataPoint]:
        """Filter metrics by time and labels."""
        filtered = self.metrics[metric_type]
        
        if start_time:
            filtered = [dp for dp in filtered if dp.timestamp >= start_time]
        if end_time:
            filtered = [dp for dp in filtered if dp.timestamp <= end_time]
        if labels:
            for key, value in labels.items():
                filtered = [dp for dp in filtered if dp.labels.get(key) == value]
        
        return filtered
    
    def _group_by_time(
        self,
        data_points: List[MetricDataPoint],
        granularity: TimeGranularity
    ) -> List[Tuple[datetime, float]]:
        """Group data points by time granularity."""
        if not data_points:
            return []
        
        grouped = defaultdict(list)
        
        for dp in data_points:
            timestamp = dp.timestamp
            
            if granularity == TimeGranularity.HOURLY:
                key = timestamp.replace(minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.DAILY:
                key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.WEEKLY:
                key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                key = key - timedelta(days=key.weekday())
            elif granularity == TimeGranularity.MONTHLY:
                key = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                key = timestamp
            
            grouped[key].append(dp.value)
        
        # Average values in each group
        result = [(k, statistics.mean(v)) for k, v in sorted(grouped.items())]
        
        return result
    
    def clear_old_metrics(self, days: int = 30) -> int:
        """
        Clear metrics older than specified days.
        
        Args:
            days: Days to keep
            
        Returns:
            Number of metrics cleared
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cleared = 0
        
        for metric_type in self.metrics:
            original_count = len(self.metrics[metric_type])
            self.metrics[metric_type] = [
                dp for dp in self.metrics[metric_type]
                if dp.timestamp >= cutoff_time
            ]
            cleared += original_count - len(self.metrics[metric_type])
        
        logger.info("Old metrics cleared", count=cleared, days=days)
        return cleared
