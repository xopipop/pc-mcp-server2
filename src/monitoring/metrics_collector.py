"""
Metrics collection for PC Control MCP Server.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict
import psutil

from ..core import (
    StructuredLogger,
    get_config,
    MonitoringException
)

log = StructuredLogger(__name__)


class MetricPoint:
    """Single metric data point."""
    
    def __init__(self, value: float, timestamp: Optional[float] = None):
        self.value = value
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }


class Metric:
    """Metric with history."""
    
    def __init__(self, name: str, max_history: int = 1000):
        self.name = name
        self.max_history = max_history
        self.history = deque(maxlen=max_history)
        self.current_value = None
        self.last_update = None
    
    def add_point(self, value: float, timestamp: Optional[float] = None):
        """Add a data point."""
        point = MetricPoint(value, timestamp)
        self.history.append(point)
        self.current_value = value
        self.last_update = point.timestamp
    
    def get_latest(self) -> Optional[float]:
        """Get latest value."""
        return self.current_value
    
    def get_history(self, duration: Optional[timedelta] = None) -> List[MetricPoint]:
        """Get history, optionally filtered by duration."""
        if not duration:
            return list(self.history)
        
        cutoff = time.time() - duration.total_seconds()
        return [p for p in self.history if p.timestamp >= cutoff]
    
    def get_stats(self, duration: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get statistics for the metric."""
        points = self.get_history(duration)
        
        if not points:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'current': self.current_value
            }
        
        values = [p.value for p in points]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'current': self.current_value,
            'last_update': self.last_update
        }


class MetricsCollector:
    """Collects and manages system metrics."""
    
    def __init__(self):
        self.config = get_config()
        self.metrics: Dict[str, Metric] = {}
        self._collectors: Dict[str, Callable] = {}
        self._collection_interval = 5.0  # Default 5 seconds
        self._collection_task = None
        self._running = False
        
        # Initialize default collectors
        self._setup_default_collectors()
    
    def _setup_default_collectors(self):
        """Setup default metric collectors."""
        # CPU metrics
        self.register_collector('cpu.percent', self._collect_cpu_percent)
        self.register_collector('cpu.count', lambda: psutil.cpu_count())
        
        # Memory metrics
        self.register_collector('memory.percent', self._collect_memory_percent)
        self.register_collector('memory.used', self._collect_memory_used)
        self.register_collector('memory.available', self._collect_memory_available)
        
        # Disk metrics
        self.register_collector('disk.usage_percent', self._collect_disk_usage)
        
        # Network metrics
        self.register_collector('network.bytes_sent', self._collect_network_bytes_sent)
        self.register_collector('network.bytes_recv', self._collect_network_bytes_recv)
        
        # Process metrics
        self.register_collector('process.count', lambda: len(psutil.pids()))
    
    def register_collector(self, metric_name: str, collector: Callable):
        """Register a metric collector function."""
        self._collectors[metric_name] = collector
        if metric_name not in self.metrics:
            self.metrics[metric_name] = Metric(metric_name)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        return self.metrics.get(name)
    
    def add_metric_value(self, name: str, value: float, timestamp: Optional[float] = None):
        """Manually add a metric value."""
        if name not in self.metrics:
            self.metrics[name] = Metric(name)
        self.metrics[name].add_point(value, timestamp)
    
    async def start(self, interval: Optional[float] = None):
        """Start collecting metrics."""
        if self._running:
            log.warning("Metrics collector already running")
            return
        
        self._collection_interval = interval or self._collection_interval
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        log.info(f"Started metrics collection with interval: {self._collection_interval}s")
    
    async def stop(self):
        """Stop collecting metrics."""
        if not self._running:
            return
        
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        log.info("Stopped metrics collection")
    
    async def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_all_metrics()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in metrics collection: {e}", exception=e)
                await asyncio.sleep(self._collection_interval)
    
    async def _collect_all_metrics(self):
        """Collect all registered metrics."""
        timestamp = time.time()
        
        for metric_name, collector in self._collectors.items():
            try:
                # Run collector
                if asyncio.iscoroutinefunction(collector):
                    value = await collector()
                else:
                    value = await asyncio.get_event_loop().run_in_executor(
                        None, collector
                    )
                
                # Store value
                if value is not None:
                    self.add_metric_value(metric_name, float(value), timestamp)
                    
            except Exception as e:
                log.warning(f"Failed to collect metric {metric_name}: {e}")
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all current metric values."""
        result = {}
        
        for name, metric in self.metrics.items():
            result[name] = {
                'current': metric.get_latest(),
                'last_update': metric.last_update,
                'stats': metric.get_stats()
            }
        
        return result
    
    def get_metrics_summary(self, duration: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {
            'metrics': {},
            'collection_interval': self._collection_interval,
            'is_running': self._running,
            'timestamp': time.time()
        }
        
        for name, metric in self.metrics.items():
            summary['metrics'][name] = metric.get_stats(duration)
        
        return summary
    
    # Collector implementations
    def _collect_cpu_percent(self) -> float:
        """Collect CPU usage percentage without blocking the event loop."""
        return psutil.cpu_percent(interval=0)
    
    def _collect_memory_percent(self) -> float:
        """Collect memory usage percentage."""
        return psutil.virtual_memory().percent
    
    def _collect_memory_used(self) -> float:
        """Collect used memory in bytes."""
        return psutil.virtual_memory().used
    
    def _collect_memory_available(self) -> float:
        """Collect available memory in bytes."""
        return psutil.virtual_memory().available
    
    def _collect_disk_usage(self) -> float:
        """Collect disk usage percentage for root."""
        return psutil.disk_usage('/').percent
    
    def _collect_network_bytes_sent(self) -> float:
        """Collect total network bytes sent."""
        return psutil.net_io_counters().bytes_sent
    
    def _collect_network_bytes_recv(self) -> float:
        """Collect total network bytes received."""
        return psutil.net_io_counters().bytes_recv


class AlertRule:
    """Alert rule definition."""
    
    def __init__(self, name: str, metric: str, condition: str, 
                 threshold: float, duration: Optional[timedelta] = None):
        self.name = name
        self.metric = metric
        self.condition = condition  # 'gt', 'lt', 'gte', 'lte', 'eq'
        self.threshold = threshold
        self.duration = duration
        self.triggered = False
        self.trigger_time = None
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if alert should trigger."""
        if value is None:
            return False
        
        conditions = {
            'gt': value > self.threshold,
            'lt': value < self.threshold,
            'gte': value >= self.threshold,
            'lte': value <= self.threshold,
            'eq': value == self.threshold
        }
        
        return conditions.get(self.condition, False)


class AlertManager:
    """Manages metric alerts."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.alert_handlers: List[Callable] = []
        self._check_interval = 10.0
        self._check_task = None
        self._running = False
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        log.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, name: str):
        """Remove an alert rule."""
        if name in self.rules:
            del self.rules[name]
            log.info(f"Removed alert rule: {name}")
    
    def add_handler(self, handler: Callable):
        """Add alert handler function."""
        self.alert_handlers.append(handler)
    
    async def start(self):
        """Start alert monitoring."""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        log.info("Started alert monitoring")
    
    async def stop(self):
        """Stop alert monitoring."""
        if not self._running:
            return
        
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        log.info("Stopped alert monitoring")
    
    async def _check_loop(self):
        """Main alert checking loop."""
        while self._running:
            try:
                await self._check_all_rules()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in alert checking: {e}", exception=e)
                await asyncio.sleep(self._check_interval)
    
    async def _check_all_rules(self):
        """Check all alert rules."""
        for rule in self.rules.values():
            try:
                metric = self.metrics_collector.get_metric(rule.metric)
                if not metric:
                    continue
                
                # Get value to check
                if rule.duration:
                    # Check average over duration
                    stats = metric.get_stats(rule.duration)
                    value = stats.get('avg')
                else:
                    # Check current value
                    value = metric.get_latest()
                
                if value is None:
                    continue
                
                # Evaluate rule
                should_trigger = rule.evaluate(value)
                
                if should_trigger and not rule.triggered:
                    # New alert
                    rule.triggered = True
                    rule.trigger_time = time.time()
                    await self._trigger_alert(rule, value)
                    
                elif not should_trigger and rule.triggered:
                    # Alert resolved
                    rule.triggered = False
                    await self._resolve_alert(rule, value)
                    
            except Exception as e:
                log.error(f"Error checking rule {rule.name}: {e}")
    
    async def _trigger_alert(self, rule: AlertRule, value: float):
        """Trigger an alert."""
        alert = {
            'rule': rule.name,
            'metric': rule.metric,
            'condition': f"{rule.condition} {rule.threshold}",
            'value': value,
            'triggered_at': rule.trigger_time,
            'status': 'triggered'
        }
        
        self.alerts.append(alert)
        log.warning(f"Alert triggered: {rule.name} - {rule.metric}={value}")
        
        # Call handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, handler, alert
                    )
            except Exception as e:
                log.error(f"Error in alert handler: {e}")
    
    async def _resolve_alert(self, rule: AlertRule, value: float):
        """Resolve an alert."""
        alert = {
            'rule': rule.name,
            'metric': rule.metric,
            'value': value,
            'resolved_at': time.time(),
            'status': 'resolved'
        }
        
        self.alerts.append(alert)
        log.info(f"Alert resolved: {rule.name} - {rule.metric}={value}")
        
        # Call handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, handler, alert
                    )
            except Exception as e:
                log.error(f"Error in alert handler: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        active = []
        
        for rule in self.rules.values():
            if rule.triggered:
                metric = self.metrics_collector.get_metric(rule.metric)
                active.append({
                    'rule': rule.name,
                    'metric': rule.metric,
                    'condition': f"{rule.condition} {rule.threshold}",
                    'current_value': metric.get_latest() if metric else None,
                    'triggered_at': rule.trigger_time
                })
        
        return active
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self.alerts[-limit:]