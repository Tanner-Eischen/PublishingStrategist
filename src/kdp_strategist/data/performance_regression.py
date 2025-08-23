"""
Performance regression testing and monitoring for KDP Strategist.

This module provides tools for tracking performance metrics over time,
detecting regressions, and storing baseline performance data.
"""
import os
import json
import time
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    name: str
    value: float
    unit: str
    timestamp: float = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PerformanceBaseline:
    """Performance baseline for regression comparison."""
    metric_name: str
    mean: float
    p95: float
    min_value: float
    max_value: float
    std_dev: float
    unit: str
    sample_size: int
    created_at: float
    context: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceBaseline':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_metrics(cls, metrics: List[PerformanceMetric]) -> 'PerformanceBaseline':
        """Create baseline from a list of metrics."""
        if not metrics:
            raise ValueError("Cannot create baseline from empty metrics list")
        
        values = [m.value for m in metrics]
        
        return cls(
            metric_name=metrics[0].name,
            mean=statistics.mean(values),
            p95=sorted(values)[int(len(values) * 0.95)],
            min_value=min(values),
            max_value=max(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            unit=metrics[0].unit,
            sample_size=len(metrics),
            created_at=time.time(),
            context=metrics[0].context
        )


class PerformanceRegressionTracker:
    """Track performance metrics and detect regressions."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize performance regression tracker.
        
        Args:
            storage_dir: Directory to store baseline data (default: ~/.kdp_strategist/performance)
        """
        if storage_dir is None:
            home_dir = os.path.expanduser("~")
            storage_dir = os.path.join(home_dir, ".kdp_strategist", "performance")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_metrics: Dict[str, List[PerformanceMetric]] = {}
        self.baselines: Dict[str, PerformanceBaseline] = {}
        
        # Load existing baselines
        self._load_baselines()
    
    def _get_baseline_path(self, metric_name: str) -> Path:
        """Get path for baseline file."""
        safe_name = metric_name.replace("/", "_").replace("\\", "_")
        return self.storage_dir / f"{safe_name}_baseline.json"
    
    def _load_baselines(self) -> None:
        """Load existing baselines from storage."""
        if not self.storage_dir.exists():
            return
            
        for file_path in self.storage_dir.glob("*_baseline.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    baseline = PerformanceBaseline.from_dict(data)
                    self.baselines[baseline.metric_name] = baseline
                    logger.debug(f"Loaded baseline for {baseline.metric_name}")
            except Exception as e:
                logger.error(f"Error loading baseline from {file_path}: {e}")
    
    def _save_baseline(self, baseline: PerformanceBaseline) -> None:
        """Save baseline to storage."""
        file_path = self._get_baseline_path(baseline.metric_name)
        try:
            with open(file_path, "w") as f:
                json.dump(baseline.to_dict(), f, indent=2)
            logger.debug(f"Saved baseline for {baseline.metric_name}")
        except Exception as e:
            logger.error(f"Error saving baseline to {file_path}: {e}")
    
    def record_metric(self, name: str, value: float, unit: str, 
                     context: Optional[Dict[str, Any]] = None) -> PerformanceMetric:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement (e.g., "ms", "req/s")
            context: Additional context information
            
        Returns:
            Recorded metric
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            context=context or {}
        )
        
        if name not in self.current_metrics:
            self.current_metrics[name] = []
            
        self.current_metrics[name].append(metric)
        return metric
    
    def create_baseline(self, metric_name: str, save: bool = True) -> Optional[PerformanceBaseline]:
        """
        Create a baseline from recorded metrics.
        
        Args:
            metric_name: Name of metric to create baseline for
            save: Whether to save baseline to storage
            
        Returns:
            Created baseline or None if no metrics available
        """
        if metric_name not in self.current_metrics or not self.current_metrics[metric_name]:
            logger.warning(f"No metrics available for {metric_name}")
            return None
            
        baseline = PerformanceBaseline.from_metrics(self.current_metrics[metric_name])
        self.baselines[metric_name] = baseline
        
        if save:
            self._save_baseline(baseline)
            
        return baseline
    
    def compare_with_baseline(self, metric_name: str, current_value: float, 
                             regression_threshold: float = 0.2) -> Tuple[bool, float]:
        """
        Compare current value with baseline to detect regression.
        
        Args:
            metric_name: Name of metric to compare
            current_value: Current metric value
            regression_threshold: Threshold for regression detection (0.2 = 20% worse)
            
        Returns:
            Tuple of (is_regression, percent_change)
        """
        if metric_name not in self.baselines:
            logger.warning(f"No baseline available for {metric_name}")
            return False, 0.0
            
        baseline = self.baselines[metric_name]
        
        # For metrics where higher is better (e.g., throughput)
        if baseline.unit in ["req/s", "ops/s", "items/s"]:
            percent_change = (baseline.mean - current_value) / baseline.mean
            is_regression = percent_change > regression_threshold
        # For metrics where lower is better (e.g., response time)
        else:
            percent_change = (current_value - baseline.mean) / baseline.mean
            is_regression = percent_change > regression_threshold
        
        return is_regression, percent_change
    
    def detect_regression(self, metric_name: str, 
                         regression_threshold: float = 0.2) -> Optional[Tuple[bool, float]]:
        """
        Detect regression for a metric using recent measurements.
        
        Args:
            metric_name: Name of metric to check
            regression_threshold: Threshold for regression detection (0.2 = 20% worse)
            
        Returns:
            Tuple of (is_regression, percent_change) or None if insufficient data
        """
        if metric_name not in self.current_metrics or not self.current_metrics[metric_name]:
            logger.warning(f"No current metrics for {metric_name}")
            return None
            
        if metric_name not in self.baselines:
            logger.warning(f"No baseline for {metric_name}")
            return None
            
        # Use average of recent metrics
        recent_values = [m.value for m in self.current_metrics[metric_name]]
        current_avg = statistics.mean(recent_values)
        
        return self.compare_with_baseline(metric_name, current_avg, regression_threshold)
    
    def get_regression_report(self, regression_threshold: float = 0.2) -> Dict[str, Any]:
        """
        Generate regression report for all metrics.
        
        Args:
            regression_threshold: Threshold for regression detection
            
        Returns:
            Dictionary with regression analysis
        """
        report = {
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "metrics_analyzed": 0,
            "regressions_detected": 0,
            "details": {}
        }
        
        for metric_name in self.current_metrics:
            if not self.current_metrics[metric_name] or metric_name not in self.baselines:
                continue
                
            recent_values = [m.value for m in self.current_metrics[metric_name]]
            current_avg = statistics.mean(recent_values)
            
            is_regression, percent_change = self.compare_with_baseline(
                metric_name, current_avg, regression_threshold
            )
            
            report["metrics_analyzed"] += 1
            if is_regression:
                report["regressions_detected"] += 1
                
            report["details"][metric_name] = {
                "baseline_mean": self.baselines[metric_name].mean,
                "current_mean": current_avg,
                "percent_change": percent_change * 100,
                "is_regression": is_regression,
                "unit": self.baselines[metric_name].unit,
                "sample_size": len(recent_values)
            }
        
        return report
    
    def clear_metrics(self, metric_name: Optional[str] = None) -> None:
        """
        Clear recorded metrics.
        
        Args:
            metric_name: Name of metric to clear, or None to clear all
        """
        if metric_name is None:
            self.current_metrics = {}
        elif metric_name in self.current_metrics:
            self.current_metrics[metric_name] = []
    
    def export_metrics_to_file(self, file_path: str) -> None:
        """
        Export all metrics to a JSON file.
        
        Args:
            file_path: Path to export file
        """
        data = {
            "export_time": time.time(),
            "export_date": datetime.now().isoformat(),
            "metrics": {
                name: [m.to_dict() for m in metrics]
                for name, metrics in self.current_metrics.items()
            },
            "baselines": {
                name: baseline.to_dict()
                for name, baseline in self.baselines.items()
            }
        }
        
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported metrics to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting metrics to {file_path}: {e}")


# Default tracker instance
default_tracker = PerformanceRegressionTracker()


def track_execution_time(metric_name: str, unit: str = "s"):
    """
    Decorator to track execution time of a function.
    
    Args:
        metric_name: Name for this metric
        unit: Unit of measurement (default: "s" for seconds)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            result = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            default_tracker.record_metric(metric_name, execution_time, unit)
            
            return result
        return wrapper
    return decorator


async def track_async_execution_time(metric_name: str, unit: str = "s"):
    """
    Decorator to track execution time of an async function.
    
    Args:
        metric_name: Name for this metric
        unit: Unit of measurement (default: "s" for seconds)
        
    Returns:
        Decorated async function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            result = await func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            default_tracker.record_metric(metric_name, execution_time, unit)
            
            return result
        return wrapper
    return decorator