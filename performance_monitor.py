"""
performance_monitor.py
Performance monitoring and optimization for the Stock Arbitrage Bot
"""

import time
import psutil
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    opportunities_per_second: float
    processing_time_ms: float
    error_rate: float

class PerformanceMonitor:
    """Monitor system performance and optimize operations"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_time = datetime.now()
        self.total_opportunities = 0
        self.total_errors = 0
        self.processing_times = []
        
    def record_processing_time(self, start_time: float):
        """Record processing time for an operation"""
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        self.processing_times.append(processing_time)
        
        # Keep only recent processing times
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-500:]
    
    def record_opportunity(self):
        """Record that an opportunity was detected"""
        self.total_opportunities += 1
    
    def record_error(self):
        """Record that an error occurred"""
        self.total_errors += 1
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)
            
            # Application metrics
            runtime = (datetime.now() - self.start_time).total_seconds()
            opportunities_per_second = self.total_opportunities / max(runtime, 1)
            
            avg_processing_time = (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times else 0
            )
            
            total_operations = self.total_opportunities + self.total_errors
            error_rate = self.total_errors / max(total_operations, 1)
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                opportunities_per_second=opportunities_per_second,
                processing_time_ms=avg_processing_time,
                error_rate=error_rate
            )
            
            self.metrics_history.append(metrics)
            
            # Keep only recent metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-500:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0,
                memory_mb=0,
                opportunities_per_second=0,
                processing_time_ms=0,
                error_rate=1.0
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics_history:
            return {"status": "No metrics available"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 readings
        
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_mb for m in recent_metrics) / len(recent_metrics)
        avg_processing_time = sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics)
        
        latest = self.metrics_history[-1]
        
        return {
            "runtime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_opportunities": self.total_opportunities,
            "total_errors": self.total_errors,
            "current_cpu_percent": latest.cpu_percent,
            "current_memory_mb": latest.memory_mb,
            "average_cpu_percent": round(avg_cpu, 2),
            "average_memory_mb": round(avg_memory, 2),
            "average_processing_time_ms": round(avg_processing_time, 2),
            "opportunities_per_second": round(latest.opportunities_per_second, 3),
            "error_rate": round(latest.error_rate, 4),
            "status": self._get_status_assessment()
        }
    
    def _get_status_assessment(self) -> str:
        """Assess current performance status"""
        if not self.metrics_history:
            return "INITIALIZING"
        
        latest = self.metrics_history[-1]
        
        if latest.error_rate > 0.1:  # More than 10% errors
            return "HIGH_ERROR_RATE"
        elif latest.cpu_percent > 80:
            return "HIGH_CPU_USAGE"
        elif latest.memory_mb > 1000:  # More than 1GB
            return "HIGH_MEMORY_USAGE"
        elif latest.processing_time_ms > 100:  # More than 100ms
            return "SLOW_PROCESSING"
        else:
            return "OPTIMAL"
    
    def get_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        if not self.metrics_history:
            return ["System initializing - no recommendations yet"]
        
        summary = self.get_performance_summary()
        status = summary["status"]
        
        if status == "HIGH_ERROR_RATE":
            recommendations.append("🔴 High error rate detected - check logs and data quality")
            recommendations.append("Consider reducing update frequency")
        
        if status == "HIGH_CPU_USAGE":
            recommendations.append("🟡 High CPU usage - consider reducing processing frequency")
            recommendations.append("Optimize calculations or add processing delays")
        
        if status == "HIGH_MEMORY_USAGE":
            recommendations.append("🟡 High memory usage - implement data cleanup")
            recommendations.append("Reduce MAX_OPPORTUNITIES_IN_MEMORY setting")
        
        if status == "SLOW_PROCESSING":
            recommendations.append("🟡 Slow processing detected - optimize algorithms")
            recommendations.append("Consider using more efficient data structures")
        
        if summary["opportunities_per_second"] < 0.01:
            recommendations.append("🔵 Low opportunity detection - consider adjusting threshold")
        
        if not recommendations:
            recommendations.append("✅ System performing optimally")
        
        return recommendations
    
    def should_throttle(self) -> bool:
        """Determine if processing should be throttled"""
        if not self.metrics_history:
            return False
        
        latest = self.metrics_history[-1]
        
        # Throttle if system is under stress
        return (
            latest.cpu_percent > 90 or
            latest.memory_mb > 2000 or  # 2GB
            latest.error_rate > 0.2 or
            latest.processing_time_ms > 200
        )
    
    def get_optimal_update_interval(self) -> float:
        """Get recommended update interval based on performance"""
        base_interval = Config.PRICE_UPDATE_INTERVAL
        
        if not self.metrics_history:
            return base_interval
        
        latest = self.metrics_history[-1]
        
        # Adjust interval based on performance
        if latest.cpu_percent > 80:
            return base_interval * 1.5  # Slow down
        elif latest.processing_time_ms > 100:
            return base_interval * 1.2  # Slow down slightly
        elif latest.cpu_percent < 30 and latest.processing_time_ms < 20:
            return max(0.1, base_interval * 0.8)  # Speed up slightly
        
        return base_interval
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics_history = []
        self.start_time = datetime.now()
        self.total_opportunities = 0
        self.total_errors = 0
        self.processing_times = []
        logger.info("Performance metrics reset")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            performance_monitor.record_processing_time(start_time)
            return result
        except Exception as e:
            performance_monitor.record_error()
            performance_monitor.record_processing_time(start_time)
            raise
    return wrapper

if __name__ == "__main__":
    # Test performance monitoring
    monitor = PerformanceMonitor()
    
    # Simulate some operations
    for i in range(10):
        start = time.time()
        time.sleep(0.01)  # Simulate work
        monitor.record_processing_time(start)
        
        if i % 3 == 0:
            monitor.record_opportunity()
        
        if i % 7 == 0:
            monitor.record_error()
    
    # Collect metrics
    metrics = monitor.collect_metrics()
    summary = monitor.get_performance_summary()
    recommendations = monitor.get_recommendations()
    
    print("Performance Test Results:")
    print(f"Summary: {summary}")
    print(f"Recommendations: {recommendations}")
