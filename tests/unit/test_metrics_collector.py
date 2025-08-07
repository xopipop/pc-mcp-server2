"""
Unit tests for MetricsCollector.
"""

import pytest
import asyncio
import time
from datetime import timedelta
from unittest.mock import Mock, patch

from src.monitoring import MetricsCollector, AlertManager, AlertRule


@pytest.fixture
def metrics_collector():
    """Create MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def alert_manager(metrics_collector):
    """Create AlertManager instance."""
    return AlertManager(metrics_collector)


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    def test_register_collector(self, metrics_collector):
        """Test registering a custom collector."""
        # Register a simple collector
        def custom_collector():
            return 42.0
        
        metrics_collector.register_collector('custom.metric', custom_collector)
        
        assert 'custom.metric' in metrics_collector._collectors
        assert 'custom.metric' in metrics_collector.metrics
    
    def test_add_metric_value(self, metrics_collector):
        """Test manually adding metric values."""
        # Add some values
        metrics_collector.add_metric_value('test.metric', 10.0)
        metrics_collector.add_metric_value('test.metric', 20.0)
        metrics_collector.add_metric_value('test.metric', 30.0)
        
        # Get the metric
        metric = metrics_collector.get_metric('test.metric')
        assert metric is not None
        assert metric.get_latest() == 30.0
        
        # Check stats
        stats = metric.get_stats()
        assert stats['count'] == 3
        assert stats['min'] == 10.0
        assert stats['max'] == 30.0
        assert stats['avg'] == 20.0
    
    @pytest.mark.asyncio
    async def test_start_stop_collection(self, metrics_collector):
        """Test starting and stopping metrics collection."""
        # Start collection
        await metrics_collector.start(interval=0.1)
        assert metrics_collector._running is True
        
        # Wait a bit
        await asyncio.sleep(0.3)
        
        # Stop collection
        await metrics_collector.stop()
        assert metrics_collector._running is False
        
        # Check that some metrics were collected
        cpu_metric = metrics_collector.get_metric('cpu.percent')
        assert cpu_metric is not None
        assert cpu_metric.get_latest() is not None
    
    def test_get_all_metrics(self, metrics_collector):
        """Test getting all metrics."""
        # Add some test metrics
        metrics_collector.add_metric_value('test1', 10.0)
        metrics_collector.add_metric_value('test2', 20.0)
        
        all_metrics = metrics_collector.get_all_metrics()
        
        assert 'test1' in all_metrics
        assert 'test2' in all_metrics
        assert all_metrics['test1']['current'] == 10.0
        assert all_metrics['test2']['current'] == 20.0
    
    def test_get_metrics_summary(self, metrics_collector):
        """Test getting metrics summary."""
        # Add some test metrics
        metrics_collector.add_metric_value('test.metric', 15.0)
        
        summary = metrics_collector.get_metrics_summary()
        
        assert 'metrics' in summary
        assert 'collection_interval' in summary
        assert 'is_running' in summary
        assert 'timestamp' in summary
        
        assert 'test.metric' in summary['metrics']
        assert summary['metrics']['test.metric']['current'] == 15.0
    
    def test_metric_history_with_duration(self, metrics_collector):
        """Test getting metric history with duration filter."""
        # Add values at different times
        now = time.time()
        
        metric = metrics_collector.metrics['test.metric'] = \
            metrics_collector.metrics.get('test.metric', 
                                        type(metrics_collector.metrics['cpu.percent'])('test.metric'))
        
        # Add old value
        metric.add_point(10.0, now - 120)  # 2 minutes ago
        
        # Add recent values
        metric.add_point(20.0, now - 30)   # 30 seconds ago
        metric.add_point(30.0, now - 10)   # 10 seconds ago
        
        # Get stats for last minute
        stats = metric.get_stats(timedelta(minutes=1))
        
        assert stats['count'] == 2  # Only recent values
        assert stats['min'] == 20.0
        assert stats['max'] == 30.0


class TestAlertManager:
    """Test AlertManager class."""
    
    def test_add_remove_rule(self, alert_manager):
        """Test adding and removing alert rules."""
        # Create a rule
        rule = AlertRule(
            name='high_cpu',
            metric='cpu.percent',
            condition='gt',
            threshold=80.0
        )
        
        # Add rule
        alert_manager.add_rule(rule)
        assert 'high_cpu' in alert_manager.rules
        
        # Remove rule
        alert_manager.remove_rule('high_cpu')
        assert 'high_cpu' not in alert_manager.rules
    
    def test_alert_rule_evaluation(self):
        """Test alert rule evaluation."""
        rule = AlertRule(
            name='test_rule',
            metric='test.metric',
            condition='gt',
            threshold=50.0
        )
        
        assert rule.evaluate(60.0) is True   # 60 > 50
        assert rule.evaluate(40.0) is False  # 40 < 50
        assert rule.evaluate(50.0) is False  # 50 = 50 (not >)
        
        # Test other conditions
        rule.condition = 'gte'
        assert rule.evaluate(50.0) is True   # 50 >= 50
        
        rule.condition = 'lt'
        assert rule.evaluate(40.0) is True   # 40 < 50
        
        rule.condition = 'eq'
        assert rule.evaluate(50.0) is True   # 50 == 50
    
    @pytest.mark.asyncio
    async def test_alert_triggering(self, metrics_collector, alert_manager):
        """Test alert triggering and resolution."""
        # Track alerts
        triggered_alerts = []
        resolved_alerts = []
        
        def alert_handler(alert):
            if alert['status'] == 'triggered':
                triggered_alerts.append(alert)
            else:
                resolved_alerts.append(alert)
        
        alert_manager.add_handler(alert_handler)
        
        # Add alert rule
        rule = AlertRule(
            name='high_test',
            metric='test.metric',
            condition='gt',
            threshold=50.0
        )
        alert_manager.add_rule(rule)
        
        # Start alert monitoring
        alert_manager._check_interval = 0.1
        await alert_manager.start()
        
        # Add metric value that triggers alert
        metrics_collector.add_metric_value('test.metric', 60.0)
        await asyncio.sleep(0.2)
        
        # Check alert was triggered
        assert len(triggered_alerts) > 0
        assert triggered_alerts[0]['rule'] == 'high_test'
        assert rule.triggered is True
        
        # Add metric value that resolves alert
        metrics_collector.add_metric_value('test.metric', 40.0)
        await asyncio.sleep(0.2)
        
        # Check alert was resolved
        assert len(resolved_alerts) > 0
        assert resolved_alerts[0]['rule'] == 'high_test'
        assert rule.triggered is False
        
        # Stop monitoring
        await alert_manager.stop()
    
    def test_get_active_alerts(self, metrics_collector, alert_manager):
        """Test getting active alerts."""
        # Add some rules
        rule1 = AlertRule('rule1', 'metric1', 'gt', 50.0)
        rule2 = AlertRule('rule2', 'metric2', 'lt', 10.0)
        
        alert_manager.add_rule(rule1)
        alert_manager.add_rule(rule2)
        
        # Trigger one rule
        rule1.triggered = True
        rule1.trigger_time = time.time()
        
        # Add metric for triggered rule
        metrics_collector.add_metric_value('metric1', 60.0)
        
        active = alert_manager.get_active_alerts()
        
        assert len(active) == 1
        assert active[0]['rule'] == 'rule1'
        assert active[0]['current_value'] == 60.0