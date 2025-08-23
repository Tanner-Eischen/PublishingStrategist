"""
Automated incident response system for Simple Trends Replacement.

This module provides automated incident detection, response, and recovery
capabilities for the KDP Strategist system.
"""

import asyncio
import logging
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .simple_trends_monitoring import TrendsMonitor
from .simple_trends_recovery import TrendsRecovery
from .simple_trends_logger import TrendsLogger
from .cache_manager import CacheManager
from .http_client import SyncHTTPClient, HTTPClientConfig


class IncidentSeverity(Enum):
    """Incident severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Incident status states."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    """Represents a system incident."""
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)


@dataclass
class ResponseAction:
    """Defines an automated response action."""
    name: str
    description: str
    severity_threshold: IncidentSeverity
    action_func: Callable
    timeout: int = 300  # 5 minutes default
    retry_count: int = 3
    cooldown: int = 60  # 1 minute cooldown between retries


class AutomatedIncidentResponse:
    """
    Automated incident response system that monitors for issues,
    creates incidents, and executes appropriate response actions.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = TrendsLogger().get_logger(__name__)
        self.monitor = TrendsMonitor()
        self.recovery = TrendsRecovery()
        self.cache_manager = CacheManager()
        
        # Initialize HTTP client for webhook notifications
        http_config = HTTPClientConfig(
            timeout=10,
            max_retries=2,
            base_delay=1.0
        )
        self.http_client = SyncHTTPClient(http_config, self.logger)
        
        # Incident storage
        self.incidents: Dict[str, Incident] = {}
        self.incident_counter = 0
        
        # Response actions registry
        self.response_actions: List[ResponseAction] = []
        self.action_history: Dict[str, List[datetime]] = {}
        
        # Configuration
        self.notification_config = self.config.get('notifications', {})
        self.escalation_config = self.config.get('escalation', {})
        self.auto_resolve_timeout = self.config.get('auto_resolve_timeout', 3600)  # 1 hour
        
        # Initialize response actions
        self._register_default_actions()
        
        # Start monitoring
        self.monitoring_task = None
        self.is_running = False
    
    def _register_default_actions(self):
        """Register default automated response actions."""
        
        # Cache clearing action
        self.register_action(ResponseAction(
            name="clear_cache",
            description="Clear system cache to resolve data inconsistencies",
            severity_threshold=IncidentSeverity.MEDIUM,
            action_func=self._clear_cache_action,
            timeout=60,
            retry_count=2
        ))
        
        # Service restart action
        self.register_action(ResponseAction(
            name="restart_trends_service",
            description="Restart trends data service",
            severity_threshold=IncidentSeverity.HIGH,
            action_func=self._restart_trends_service,
            timeout=120,
            retry_count=1
        ))
        
        # Fallback activation
        self.register_action(ResponseAction(
            name="activate_fallback",
            description="Activate fallback data sources",
            severity_threshold=IncidentSeverity.HIGH,
            action_func=self._activate_fallback,
            timeout=30,
            retry_count=1
        ))
        
        # Rate limit adjustment
        self.register_action(ResponseAction(
            name="adjust_rate_limits",
            description="Adjust API rate limits to reduce load",
            severity_threshold=IncidentSeverity.MEDIUM,
            action_func=self._adjust_rate_limits,
            timeout=10,
            retry_count=1
        ))
    
    def register_action(self, action: ResponseAction):
        """Register a new response action."""
        self.response_actions.append(action)
        self.action_history[action.name] = []
        self.logger.info(f"Registered response action: {action.name}")
    
    async def start_monitoring(self):
        """Start the incident monitoring and response system."""
        if self.is_running:
            self.logger.warning("Incident response system is already running")
            return
        
        self.is_running = True
        self.logger.info("Starting automated incident response system")
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start incident aging task
        asyncio.create_task(self._incident_aging_loop())
    
    async def stop_monitoring(self):
        """Stop the incident monitoring system."""
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped automated incident response system")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that checks for incidents."""
        while self.is_running:
            try:
                # Check system health
                health_status = await self.monitor.get_system_health()
                
                # Detect incidents based on health status
                await self._detect_incidents(health_status)
                
                # Process existing incidents
                await self._process_incidents()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _detect_incidents(self, health_status: Dict):
        """Detect new incidents based on system health."""
        
        # API failure detection
        if health_status.get('api_failures', 0) > 5:
            await self.create_incident(
                title="High API Failure Rate",
                description=f"API failure rate: {health_status['api_failures']} failures",
                severity=IncidentSeverity.HIGH,
                tags=["api", "failures"],
                metadata={"failure_count": health_status['api_failures']}
            )
        
        # Response time detection
        avg_response_time = health_status.get('avg_response_time', 0)
        if avg_response_time > 5000:  # 5 seconds
            await self.create_incident(
                title="High Response Times",
                description=f"Average response time: {avg_response_time}ms",
                severity=IncidentSeverity.MEDIUM,
                tags=["performance", "response_time"],
                metadata={"response_time": avg_response_time}
            )
        
        # Cache hit rate detection
        cache_hit_rate = health_status.get('cache_hit_rate', 100)
        if cache_hit_rate < 50:
            await self.create_incident(
                title="Low Cache Hit Rate",
                description=f"Cache hit rate: {cache_hit_rate}%",
                severity=IncidentSeverity.LOW,
                tags=["cache", "performance"],
                metadata={"hit_rate": cache_hit_rate}
            )
        
        # Memory usage detection
        memory_usage = health_status.get('memory_usage_percent', 0)
        if memory_usage > 90:
            await self.create_incident(
                title="High Memory Usage",
                description=f"Memory usage: {memory_usage}%",
                severity=IncidentSeverity.CRITICAL,
                tags=["memory", "resources"],
                metadata={"memory_usage": memory_usage}
            )
    
    async def create_incident(self, title: str, description: str, 
                            severity: IncidentSeverity, tags: List[str] = None,
                            metadata: Dict = None) -> str:
        """Create a new incident."""
        
        # Check if similar incident already exists
        existing_incident = self._find_similar_incident(title, tags or [])
        if existing_incident:
            self.logger.info(f"Similar incident already exists: {existing_incident.id}")
            return existing_incident.id
        
        # Create new incident
        self.incident_counter += 1
        incident_id = f"INC-{self.incident_counter:06d}"
        
        incident = Incident(
            id=incident_id,
            title=title,
            description=description,
            severity=severity,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.incidents[incident_id] = incident
        
        self.logger.warning(f"Created incident {incident_id}: {title}")
        
        # Send notifications
        await self._send_notifications(incident)
        
        # Trigger automated response
        await self._trigger_automated_response(incident)
        
        return incident_id
    
    def _find_similar_incident(self, title: str, tags: List[str]) -> Optional[Incident]:
        """Find similar open incidents."""
        for incident in self.incidents.values():
            if (incident.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING] and
                incident.title == title and
                set(incident.tags) == set(tags)):
                return incident
        return None
    
    async def _process_incidents(self):
        """Process existing incidents."""
        for incident in list(self.incidents.values()):
            if incident.status == IncidentStatus.OPEN:
                # Move to investigating
                await self.update_incident_status(incident.id, IncidentStatus.INVESTIGATING)
            
            elif incident.status == IncidentStatus.INVESTIGATING:
                # Check if incident should be auto-resolved
                if self._should_auto_resolve(incident):
                    await self.resolve_incident(incident.id, "Auto-resolved: conditions normalized")
    
    def _should_auto_resolve(self, incident: Incident) -> bool:
        """Check if incident should be auto-resolved."""
        # Auto-resolve after timeout if no manual intervention
        age = datetime.now() - incident.created_at
        if age.total_seconds() > self.auto_resolve_timeout:
            return True
        
        # Check if underlying issue is resolved
        # This would need specific logic based on incident type
        return False
    
    async def _trigger_automated_response(self, incident: Incident):
        """Trigger automated response actions for an incident."""
        applicable_actions = [
            action for action in self.response_actions
            if self._should_execute_action(action, incident)
        ]
        
        for action in applicable_actions:
            try:
                await self._execute_action(action, incident)
            except Exception as e:
                self.logger.error(f"Failed to execute action {action.name}: {e}")
    
    def _should_execute_action(self, action: ResponseAction, incident: Incident) -> bool:
        """Check if action should be executed for incident."""
        # Check severity threshold
        severity_levels = {
            IncidentSeverity.LOW: 1,
            IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.HIGH: 3,
            IncidentSeverity.CRITICAL: 4
        }
        
        if severity_levels[incident.severity] < severity_levels[action.severity_threshold]:
            return False
        
        # Check cooldown
        recent_executions = [
            dt for dt in self.action_history[action.name]
            if datetime.now() - dt < timedelta(seconds=action.cooldown)
        ]
        
        if recent_executions:
            return False
        
        return True
    
    async def _execute_action(self, action: ResponseAction, incident: Incident):
        """Execute a response action."""
        self.logger.info(f"Executing action {action.name} for incident {incident.id}")
        
        start_time = time.time()
        
        try:
            # Execute action with timeout
            await asyncio.wait_for(
                action.action_func(incident),
                timeout=action.timeout
            )
            
            # Record successful execution
            self.action_history[action.name].append(datetime.now())
            incident.actions_taken.append(f"{action.name}: SUCCESS")
            
            execution_time = time.time() - start_time
            self.logger.info(f"Action {action.name} completed in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            incident.actions_taken.append(f"{action.name}: TIMEOUT")
            self.logger.error(f"Action {action.name} timed out after {action.timeout}s")
            
        except Exception as e:
            incident.actions_taken.append(f"{action.name}: ERROR - {str(e)}")
            self.logger.error(f"Action {action.name} failed: {e}")
    
    # Response action implementations
    async def _clear_cache_action(self, incident: Incident):
        """Clear system cache."""
        await self.cache_manager.clear_all()
        self.logger.info("Cache cleared as incident response")
    
    async def _restart_trends_service(self, incident: Incident):
        """Restart trends service."""
        await self.recovery.restart_service()
        self.logger.info("Trends service restarted as incident response")
    
    async def _activate_fallback(self, incident: Incident):
        """Activate fallback data sources."""
        await self.recovery.activate_fallback_mode()
        self.logger.info("Fallback mode activated as incident response")
    
    async def _adjust_rate_limits(self, incident: Incident):
        """Adjust API rate limits."""
        # Reduce rate limits by 50%
        current_limits = self.config.get('rate_limits', {})
        for key, limit in current_limits.items():
            current_limits[key] = max(1, int(limit * 0.5))
        
        self.logger.info("Rate limits adjusted as incident response")
    
    async def update_incident_status(self, incident_id: str, status: IncidentStatus):
        """Update incident status."""
        if incident_id not in self.incidents:
            raise ValueError(f"Incident {incident_id} not found")
        
        incident = self.incidents[incident_id]
        old_status = incident.status
        incident.status = status
        incident.updated_at = datetime.now()
        
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now()
        
        self.logger.info(f"Incident {incident_id} status changed: {old_status} -> {status}")
    
    async def resolve_incident(self, incident_id: str, resolution_note: str):
        """Resolve an incident."""
        await self.update_incident_status(incident_id, IncidentStatus.RESOLVED)
        
        incident = self.incidents[incident_id]
        incident.metadata['resolution_note'] = resolution_note
        
        self.logger.info(f"Incident {incident_id} resolved: {resolution_note}")
    
    async def _send_notifications(self, incident: Incident):
        """Send incident notifications."""
        if not self.notification_config.get('enabled', False):
            return
        
        # Email notifications
        if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            await self._send_email_notification(incident)
        
        # Webhook notifications
        if self.notification_config.get('webhook_url'):
            await self._send_webhook_notification(incident)
    
    async def _send_email_notification(self, incident: Incident):
        """Send email notification for incident."""
        try:
            smtp_config = self.notification_config.get('smtp', {})
            if not smtp_config:
                return
            
            msg = MIMEMultipart()
            msg['From'] = smtp_config['from']
            msg['To'] = ', '.join(smtp_config['to'])
            msg['Subject'] = f"[{incident.severity.value.upper()}] {incident.title}"
            
            body = f"""
            Incident ID: {incident.id}
            Severity: {incident.severity.value}
            Status: {incident.status.value}
            Created: {incident.created_at}
            
            Description:
            {incident.description}
            
            Tags: {', '.join(incident.tags)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            if smtp_config.get('use_tls'):
                server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email notification sent for incident {incident.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    async def _send_webhook_notification(self, incident: Incident):
        """Send webhook notification for incident."""
        # Implementation would depend on webhook service
        pass
    
    async def _incident_aging_loop(self):
        """Background task to age and clean up old incidents."""
        while self.is_running:
            try:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                # Archive old resolved incidents
                to_remove = []
                for incident_id, incident in self.incidents.items():
                    if (incident.status == IncidentStatus.RESOLVED and
                        incident.resolved_at and
                        incident.resolved_at < cutoff_date):
                        to_remove.append(incident_id)
                
                for incident_id in to_remove:
                    del self.incidents[incident_id]
                    self.logger.info(f"Archived old incident {incident_id}")
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in incident aging loop: {e}")
                await asyncio.sleep(3600)
    
    def get_incident_summary(self) -> Dict:
        """Get summary of current incidents."""
        summary = {
            'total': len(self.incidents),
            'by_status': {},
            'by_severity': {},
            'recent': [],
            'escalated': [],
            'auto_resolved': 0,
            'manual_resolved': 0,
            'avg_resolution_time': 0
        }
        
        resolution_times = []
        
        for incident in self.incidents.values():
            # Count by status
            status = incident.status.value
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            # Count by severity
            severity = incident.severity.value
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Track resolution types
            if incident.status == IncidentStatus.RESOLVED:
                resolution_note = incident.metadata.get('resolution_note', '')
                if 'auto-resolved' in resolution_note.lower():
                    summary['auto_resolved'] += 1
                else:
                    summary['manual_resolved'] += 1
                
                # Calculate resolution time
                if incident.resolved_at:
                    resolution_time = (incident.resolved_at - incident.created_at).total_seconds()
                    resolution_times.append(resolution_time)
            
            # Recent incidents (last 24 hours)
            if datetime.now() - incident.created_at < timedelta(hours=24):
                summary['recent'].append({
                    'id': incident.id,
                    'title': incident.title,
                    'severity': incident.severity.value,
                    'status': incident.status.value,
                    'created_at': incident.created_at.isoformat(),
                    'actions_taken': len(incident.actions_taken)
                })
            
            # Escalated incidents (high/critical severity)
            if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
                summary['escalated'].append({
                    'id': incident.id,
                    'title': incident.title,
                    'severity': incident.severity.value,
                    'status': incident.status.value,
                    'age_minutes': int((datetime.now() - incident.created_at).total_seconds() / 60)
                })
        
        # Calculate average resolution time
        if resolution_times:
            summary['avg_resolution_time'] = int(sum(resolution_times) / len(resolution_times) / 60)  # in minutes
        
        return summary
    
    async def escalate_incident(self, incident_id: str, escalation_level: int = 1) -> bool:
        """Escalate an incident to higher severity or notification level."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        
        # Increase severity if possible
        severity_levels = [IncidentSeverity.LOW, IncidentSeverity.MEDIUM, IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]
        current_index = severity_levels.index(incident.severity)
        
        if current_index < len(severity_levels) - 1:
            new_severity = severity_levels[min(current_index + escalation_level, len(severity_levels) - 1)]
            incident.severity = new_severity
            incident.updated_at = datetime.now()
            incident.actions_taken.append(f"Escalated to {new_severity.value}")
            
            self.logger.warning(f"Incident {incident_id} escalated to {new_severity.value}")
            
            # Send escalation notifications
            await self._send_escalation_notification(incident, escalation_level)
            
            return True
        
        return False
    
    async def _send_escalation_notification(self, incident: Incident, escalation_level: int):
        """Send escalation notifications."""
        try:
            escalation_config = self.escalation_config.get('levels', [])
            
            for config in escalation_config:
                if config.get('severity') == incident.severity.value:
                    recipients = config.get('recipients', [])
                    
                    # Send email to escalation recipients
                    if recipients and self.notification_config.get('smtp'):
                        await self._send_escalation_email(incident, recipients, escalation_level)
                    
                    break
        
        except Exception as e:
            self.logger.error(f"Failed to send escalation notification: {e}")
    
    async def _send_escalation_email(self, incident: Incident, recipients: List[str], escalation_level: int):
        """Send escalation email notification."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            smtp_config = self.notification_config.get('smtp', {})
            if not smtp_config:
                return
            
            msg = MIMEMultipart()
            msg['From'] = smtp_config['from']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[ESCALATED - {incident.severity.value.upper()}] {incident.title}"
            
            body = f"""
            INCIDENT ESCALATED (Level {escalation_level})
            
            Incident ID: {incident.id}
            Title: {incident.title}
            Severity: {incident.severity.value} (ESCALATED)
            Status: {incident.status.value}
            Created: {incident.created_at}
            Age: {datetime.now() - incident.created_at}
            
            Description:
            {incident.description}
            
            Actions Taken:
            {chr(10).join(f"- {action}" for action in incident.actions_taken)}
            
            This incident has been escalated and requires immediate attention.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            if smtp_config.get('use_tls'):
                server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Escalation email sent for incident {incident.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send escalation email: {e}")
    
    async def bulk_resolve_incidents(self, incident_ids: List[str], resolution_note: str) -> Dict[str, bool]:
        """Resolve multiple incidents at once."""
        results = {}
        
        for incident_id in incident_ids:
            try:
                await self.resolve_incident(incident_id, resolution_note)
                results[incident_id] = True
            except Exception as e:
                self.logger.error(f"Failed to resolve incident {incident_id}: {e}")
                results[incident_id] = False
        
        return results
    
    async def create_incident_from_logs(self, log_pattern: str, severity: IncidentSeverity) -> Optional[str]:
        """Create incident based on log pattern detection."""
        try:
            # This would integrate with the log aggregation system
            incident_id = await self.create_incident(
                title=f"Log Pattern Alert: {log_pattern}",
                description=f"Detected concerning pattern in logs: {log_pattern}",
                severity=severity,
                tags=["logs", "pattern", "automated"],
                metadata={"log_pattern": log_pattern, "source": "log_analysis"}
            )
            
            return incident_id
            
        except Exception as e:
            self.logger.error(f"Failed to create incident from log pattern: {e}")
            return None
    
    def get_incident_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get incident metrics for the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        period_incidents = [
            incident for incident in self.incidents.values()
            if incident.created_at > cutoff_date
        ]
        
        if not period_incidents:
            return {"error": "No incidents in the specified period"}
        
        # Calculate metrics
        total_incidents = len(period_incidents)
        resolved_incidents = [i for i in period_incidents if i.status == IncidentStatus.RESOLVED]
        
        resolution_times = []
        for incident in resolved_incidents:
            if incident.resolved_at:
                resolution_time = (incident.resolved_at - incident.created_at).total_seconds() / 60  # minutes
                resolution_times.append(resolution_time)
        
        # MTTR (Mean Time To Resolution)
        mttr = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Incident frequency by day
        daily_counts = defaultdict(int)
        for incident in period_incidents:
            day_key = incident.created_at.date()
            daily_counts[day_key] += 1
        
        # Top components with incidents
        component_counts = defaultdict(int)
        for incident in period_incidents:
            for tag in incident.tags:
                if tag in ["api", "cache", "database", "performance", "memory"]:
                    component_counts[tag] += 1
        
        return {
            "period_days": days,
            "total_incidents": total_incidents,
            "resolved_incidents": len(resolved_incidents),
            "resolution_rate": (len(resolved_incidents) / total_incidents * 100) if total_incidents > 0 else 0,
            "mttr_minutes": mttr,
            "daily_incident_counts": dict(daily_counts),
            "top_incident_components": dict(Counter(component_counts).most_common(5)),
            "severity_distribution": {
                severity.value: len([i for i in period_incidents if i.severity == severity])
                for severity in IncidentSeverity
            },
            "avg_incidents_per_day": total_incidents / days if days > 0 else 0
        }
    
    async def create_incident_runbook(self, incident_type: str) -> Dict[str, Any]:
        """Create automated runbook for incident type."""
        runbooks = {
            "high_error_rate": {
                "title": "High Error Rate Response",
                "steps": [
                    "Check error logs for patterns",
                    "Verify external API connectivity",
                    "Check system resources (CPU, memory)",
                    "Consider enabling circuit breakers",
                    "Scale up resources if needed",
                    "Activate fallback mechanisms"
                ],
                "automated_actions": ["clear_cache", "activate_fallback"],
                "escalation_threshold": "10 minutes",
                "recovery_criteria": "Error rate below 5% for 10 minutes"
            },
            "slow_response_time": {
                "title": "Slow Response Time Response",
                "steps": [
                    "Check system load and resources",
                    "Analyze slow query logs",
                    "Verify cache hit rates",
                    "Check network connectivity",
                    "Consider horizontal scaling",
                    "Optimize database queries"
                ],
                "automated_actions": ["clear_cache", "adjust_rate_limits"],
                "escalation_threshold": "15 minutes",
                "recovery_criteria": "Response time below 2 seconds for 15 minutes"
            },
            "system_health_critical": {
                "title": "Critical System Health Response",
                "steps": [
                    "Immediate health check of all components",
                    "Check system resources and disk space",
                    "Verify database connectivity",
                    "Check external service dependencies",
                    "Consider service restart",
                    "Activate disaster recovery if needed"
                ],
                "automated_actions": ["restart_trends_service", "activate_fallback"],
                "escalation_threshold": "5 minutes",
                "recovery_criteria": "All health checks passing for 10 minutes"
            }
        }
        
        return runbooks.get(incident_type, {
            "title": f"Generic Response for {incident_type}",
            "steps": ["Investigate incident", "Apply appropriate fixes", "Monitor recovery"],
            "automated_actions": [],
            "escalation_threshold": "30 minutes",
            "recovery_criteria": "Manual verification required"
        })
    
    async def simulate_incident_response(self, incident_type: str) -> Dict[str, Any]:
        """Simulate incident response for testing."""
        simulation_results = {
            "incident_type": incident_type,
            "simulation_start": datetime.now().isoformat(),
            "steps_executed": [],
            "actions_taken": [],
            "estimated_resolution_time": 0,
            "success_probability": 0.0
        }
        
        # Get runbook for incident type
        runbook = await self.create_incident_runbook(incident_type)
        
        # Simulate each step
        total_time = 0
        for i, step in enumerate(runbook.get("steps", [])):
            step_time = 30 + (i * 15)  # Increasing time per step
            total_time += step_time
            
            simulation_results["steps_executed"].append({
                "step": step,
                "estimated_time_seconds": step_time,
                "success_probability": 0.8 - (i * 0.1)  # Decreasing success probability
            })
        
        # Simulate automated actions
        for action in runbook.get("automated_actions", []):
            action_time = 60  # 1 minute per action
            total_time += action_time
            
            simulation_results["actions_taken"].append({
                "action": action,
                "estimated_time_seconds": action_time,
                "success_probability": 0.9
            })
        
        simulation_results["estimated_resolution_time"] = total_time
        simulation_results["success_probability"] = 0.8  # Overall success probability
        simulation_results["simulation_end"] = datetime.now().isoformat()
        
        return simulation_results
    
    async def generate_incident_report(self, incident_id: str) -> Dict[str, Any]:
        """Generate detailed incident report."""
        if incident_id not in self.incidents:
            raise ValueError(f"Incident {incident_id} not found")
        
        incident = self.incidents[incident_id]
        
        # Calculate metrics
        duration = None
        if incident.resolved_at:
            duration = (incident.resolved_at - incident.created_at).total_seconds()
        
        # Get related incidents
        related_incidents = [
            i for i in self.incidents.values()
            if i.id != incident_id and
            set(i.tags) & set(incident.tags) and
            abs((i.created_at - incident.created_at).total_seconds()) < 3600  # Within 1 hour
        ]
        
        # Generate timeline
        timeline = [
            {
                "timestamp": incident.created_at.isoformat(),
                "event": "Incident created",
                "details": incident.description
            }
        ]
        
        for action in incident.actions_taken:
            timeline.append({
                "timestamp": incident.updated_at.isoformat(),
                "event": "Automated action",
                "details": action
            })
        
        if incident.resolved_at:
            timeline.append({
                "timestamp": incident.resolved_at.isoformat(),
                "event": "Incident resolved",
                "details": incident.metadata.get("resolution_note", "")
            })
        
        return {
            "incident_id": incident.id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "created_at": incident.created_at.isoformat(),
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "duration_seconds": duration,
            "duration_human": f"{int(duration // 60)} minutes" if duration else None,
            "tags": incident.tags,
            "actions_taken": incident.actions_taken,
            "related_incidents": [
                {
                    "id": ri.id,
                    "title": ri.title,
                    "severity": ri.severity.value,
                    "created_at": ri.created_at.isoformat()
                }
                for ri in related_incidents
            ],
            "timeline": timeline,
            "metadata": incident.metadata,
            "impact_assessment": await self._assess_incident_impact(incident),
            "lessons_learned": await self._generate_lessons_learned(incident),
            "recommendations": await self._generate_incident_recommendations(incident)
        }
    
    async def _assess_incident_impact(self, incident: Incident) -> Dict[str, Any]:
        """Assess the impact of an incident."""
        impact = {
            "severity_score": {
                IncidentSeverity.LOW: 1,
                IncidentSeverity.MEDIUM: 3,
                IncidentSeverity.HIGH: 7,
                IncidentSeverity.CRITICAL: 10
            }[incident.severity],
            "affected_components": incident.tags,
            "estimated_users_affected": 0,
            "estimated_revenue_impact": 0,
            "service_degradation": "none"
        }
        
        # Estimate impact based on severity and components
        if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            impact["estimated_users_affected"] = 100 if incident.severity == IncidentSeverity.HIGH else 500
            impact["service_degradation"] = "partial" if incident.severity == IncidentSeverity.HIGH else "major"
        
        # Component-specific impact
        if "api" in incident.tags:
            impact["estimated_users_affected"] *= 2
        if "database" in incident.tags:
            impact["service_degradation"] = "major"
        
        return impact
    
    async def _generate_lessons_learned(self, incident: Incident) -> List[str]:
        """Generate lessons learned from incident."""
        lessons = []
        
        # Duration-based lessons
        if incident.resolved_at:
            duration = (incident.resolved_at - incident.created_at).total_seconds()
            if duration > 1800:  # More than 30 minutes
                lessons.append("Consider improving automated detection and response times")
        
        # Action-based lessons
        if len(incident.actions_taken) > 5:
            lessons.append("Multiple actions were required - consider consolidating response procedures")
        
        # Severity-based lessons
        if incident.severity == IncidentSeverity.CRITICAL:
            lessons.append("Critical incident - review prevention measures and early warning systems")
        
        # Component-based lessons
        if "cache" in incident.tags:
            lessons.append("Cache-related incident - review cache configuration and monitoring")
        if "api" in incident.tags:
            lessons.append("API-related incident - consider improving API resilience and fallback mechanisms")
        
        return lessons
    
    async def _generate_incident_recommendations(self, incident: Incident) -> List[str]:
        """Generate recommendations based on incident."""
        recommendations = []
        
        # Severity-based recommendations
        if incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            recommendations.append("Implement additional monitoring and alerting for early detection")
            recommendations.append("Consider adding more automated response actions")
        
        # Pattern-based recommendations
        if "timeout" in incident.description.lower():
            recommendations.append("Review and optimize timeout configurations")
        if "memory" in incident.description.lower():
            recommendations.append("Implement memory usage monitoring and automatic scaling")
        if "database" in incident.tags:
            recommendations.append("Consider database performance optimization and connection pooling")
        
        # Recurrence recommendations
        similar_incidents = [
            i for i in self.incidents.values()
            if i.title == incident.title and i.id != incident.id
        ]
        
        if len(similar_incidents) > 2:
            recommendations.append("Recurring incident pattern detected - implement permanent fix")
        
        return recommendations
    
    async def setup_incident_webhooks(self, webhook_config: Dict[str, Any]):
        """Setup webhooks for incident notifications."""
        self.webhook_config = webhook_config
        
        # Validate webhook configuration
        required_fields = ["url", "events"]
        for field in required_fields:
            if field not in webhook_config:
                raise ValueError(f"Missing required webhook field: {field}")
        
        # Test webhook connectivity
        try:
            test_payload = {
                "event": "webhook_test",
                "timestamp": datetime.now().isoformat(),
                "message": "Webhook configuration test"
            }
            
            # Use unified HTTP client for webhook test
            response_data = self.http_client.post(
                webhook_config["url"],
                json=test_payload,
                headers=webhook_config.get("headers", {})
            )
            
            self.logger.info("Webhook configuration successful")
            return {"status": "success", "message": "Webhook configured and tested successfully"}
        
        except Exception as e:
            # Check if it's a rate limit or authentication error
            error_msg = str(e).lower()
            if '429' in error_msg or 'rate limit' in error_msg:
                self.logger.warning(f"Webhook test rate limited: {e}")
                return {"status": "warning", "message": f"Webhook configured but test rate limited: {e}"}
            elif '401' in error_msg or '403' in error_msg or 'auth' in error_msg:
                self.logger.warning(f"Webhook test authentication failed: {e}")
                return {"status": "warning", "message": f"Webhook configured but authentication failed: {e}"}
            else:
                self.logger.error(f"Webhook configuration failed: {e}")
                return {"status": "error", "message": f"Webhook configuration failed: {str(e)}"}
    
    async def send_webhook_notification(self, incident: Incident, event_type: str):
        """Send webhook notification for incident event."""
        if not hasattr(self, 'webhook_config') or not self.webhook_config:
            return
        
        if event_type not in self.webhook_config.get("events", []):
            return
        
        try:
            payload = {
                "event": event_type,
                "incident": {
                    "id": incident.id,
                    "title": incident.title,
                    "description": incident.description,
                    "severity": incident.severity.value,
                    "status": incident.status.value,
                    "created_at": incident.created_at.isoformat(),
                    "tags": incident.tags,
                    "metadata": incident.metadata
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Use unified HTTP client for webhook notification
            response_data = self.http_client.post(
                self.webhook_config["url"],
                json=payload,
                headers=self.webhook_config.get("headers", {})
            )
            
            self.logger.info(f"Webhook notification sent for incident {incident.id}")
        
        except Exception as e:
            # Handle various HTTP client exceptions
            error_msg = str(e).lower()
            if '429' in error_msg or 'rate limit' in error_msg:
                self.logger.warning(f"Webhook notification rate limited for incident {incident.id}: {e}")
            elif '401' in error_msg or '403' in error_msg or 'auth' in error_msg:
                self.logger.warning(f"Webhook notification authentication failed for incident {incident.id}: {e}")
            elif 'timeout' in error_msg:
                self.logger.warning(f"Webhook notification timeout for incident {incident.id}: {e}")
            elif 'connection' in error_msg:
                self.logger.warning(f"Webhook notification connection error for incident {incident.id}: {e}")
            else:
                self.logger.error(f"Failed to send webhook notification for incident {incident.id}: {e}")
    
    async def create_maintenance_window(self, start_time: datetime, end_time: datetime, description: str) -> str:
        """Create a maintenance window to suppress alerts."""
        maintenance_id = f"MAINT-{int(time.time())}"
        
        # Store maintenance window
        if not hasattr(self, 'maintenance_windows'):
            self.maintenance_windows = {}
        
        self.maintenance_windows[maintenance_id] = {
            "id": maintenance_id,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "created_at": datetime.now(),
            "active": True
        }
        
        self.logger.info(f"Created maintenance window {maintenance_id}: {description}")
        return maintenance_id
    
    def is_in_maintenance_window(self, timestamp: datetime = None) -> bool:
        """Check if current time is within a maintenance window."""
        if not hasattr(self, 'maintenance_windows'):
            return False
        
        check_time = timestamp or datetime.now()
        
        for window in self.maintenance_windows.values():
            if (window["active"] and 
                window["start_time"] <= check_time <= window["end_time"]):
                return True
        
        return False
    
    async def close_maintenance_window(self, maintenance_id: str):
        """Close a maintenance window."""
        if (hasattr(self, 'maintenance_windows') and 
            maintenance_id in self.maintenance_windows):
            self.maintenance_windows[maintenance_id]["active"] = False
            self.maintenance_windows[maintenance_id]["closed_at"] = datetime.now()
            self.logger.info(f"Closed maintenance window {maintenance_id}")
        else:
            raise ValueError(f"Maintenance window {maintenance_id} not found")
    
    async def run_health_check_incident_scan(self) -> List[str]:
        """Run health checks and create incidents for any issues found."""
        created_incidents = []
        
        try:
            # Get system health status
            health_status = await self.monitor.get_system_health()
            
            # Check for critical issues
            if health_status.get('memory_usage_percent', 0) > 90:
                incident_id = await self.create_incident(
                    title="Critical Memory Usage",
                    description=f"Memory usage is at {health_status['memory_usage_percent']}%",
                    severity=IncidentSeverity.CRITICAL,
                    tags=["memory", "resources", "automated"]
                )
                if incident_id:
                    created_incidents.append(incident_id)
            
            if health_status.get('disk_usage_percent', 0) > 90:
                incident_id = await self.create_incident(
                    title="Critical Disk Usage",
                    description=f"Disk usage is at {health_status['disk_usage_percent']}%",
                    severity=IncidentSeverity.CRITICAL,
                    tags=["disk", "resources", "automated"]
                )
                if incident_id:
                    created_incidents.append(incident_id)
            
            if health_status.get('api_failures', 0) > 10:
                incident_id = await self.create_incident(
                    title="High API Failure Rate",
                    description=f"API failure count: {health_status['api_failures']}",
                    severity=IncidentSeverity.HIGH,
                    tags=["api", "failures", "automated"]
                )
                if incident_id:
                    created_incidents.append(incident_id)
            
        except Exception as e:
            self.logger.error(f"Failed to run health check incident scan: {e}")
        
        return created_incidents
    
    def export_incident_report(self, days: int = 30, format_type: str = "json") -> str:
        """Export incident report in various formats."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        period_incidents = [
            incident for incident in self.incidents.values()
            if incident.created_at > cutoff_date
        ]
        
        if format_type.lower() == "json":
            import json
            
            report_data = {
                "report_period_days": days,
                "generated_at": datetime.now().isoformat(),
                "summary": self.get_incident_metrics(days),
                "incidents": [
                    {
                        "id": incident.id,
                        "title": incident.title,
                        "description": incident.description,
                        "severity": incident.severity.value,
                        "status": incident.status.value,
                        "created_at": incident.created_at.isoformat(),
                        "updated_at": incident.updated_at.isoformat(),
                        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                        "tags": incident.tags,
                        "actions_taken": incident.actions_taken,
                        "metadata": incident.metadata
                    }
                    for incident in period_incidents
                ]
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format_type.lower() == "csv":
            import csv
            import io
            
            output_buffer = io.StringIO()
            writer = csv.writer(output_buffer)
            
            # Write header
            writer.writerow([
                "ID", "Title", "Severity", "Status", "Created", "Resolved",
                "Resolution Time (min)", "Actions Count", "Tags"
            ])
            
            # Write data
            for incident in period_incidents:
                resolution_time = ""
                if incident.resolved_at:
                    resolution_time = int((incident.resolved_at - incident.created_at).total_seconds() / 60)
                
                writer.writerow([
                    incident.id,
                    incident.title,
                    incident.severity.value,
                    incident.status.value,
                    incident.created_at.isoformat(),
                    incident.resolved_at.isoformat() if incident.resolved_at else "",
                    resolution_time,
                    len(incident.actions_taken),
                    "; ".join(incident.tags)
                ])
            
            return output_buffer.getvalue()
        
        else:
            # Plain text format
            lines = [
                f"Incident Report - Last {days} Days",
                f"Generated: {datetime.now().isoformat()}",
                "=" * 50,
                ""
            ]
            
            metrics = self.get_incident_metrics(days)
            lines.extend([
                f"Total Incidents: {metrics.get('total_incidents', 0)}",
                f"Resolved: {metrics.get('resolved_incidents', 0)}",
                f"Resolution Rate: {metrics.get('resolution_rate', 0):.1%}",
                f"MTTR: {metrics.get('mttr_minutes', 0):.1f} minutes",
                "",
                "Incidents:",
                "-" * 20
            ])
            
            for incident in sorted(period_incidents, key=lambda x: x.created_at, reverse=True):
                lines.append(f"{incident.id}: {incident.title} [{incident.severity.value}] - {incident.status.value}")
            
            return "\n".join(lines)