#!/usr/bin/env python3
"""
Incident Management CLI Tool

This script provides command-line interface for managing incidents
in the KDP Strategist system.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kdp_strategist.data.automated_incident_response import (
    AutomatedIncidentResponse, IncidentSeverity, IncidentStatus
)


class IncidentManager:
    """CLI interface for incident management."""
    
    def __init__(self, config_path: str = None):
        config_path = config_path or "config/incident_response.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_path} not found, using defaults")
            config = {}
        
        self.response_system = AutomatedIncidentResponse(config)
    
    async def list_incidents(self, status: str = None, severity: str = None):
        """List incidents with optional filtering."""
        incidents = self.response_system.incidents
        
        # Apply filters
        if status:
            incidents = {
                k: v for k, v in incidents.items()
                if v.status.value == status
            }
        
        if severity:
            incidents = {
                k: v for k, v in incidents.items()
                if v.severity.value == severity
            }
        
        if not incidents:
            print("No incidents found matching criteria")
            return
        
        # Display incidents
        print(f"{'ID':<12} {'Title':<30} {'Severity':<10} {'Status':<12} {'Created':<20}")
        print("-" * 84)
        
        for incident in sorted(incidents.values(), key=lambda x: x.created_at, reverse=True):
            created_str = incident.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{incident.id:<12} {incident.title[:29]:<30} {incident.severity.value:<10} "
                  f"{incident.status.value:<12} {created_str:<20}")
    
    async def show_incident(self, incident_id: str):
        """Show detailed information about an incident."""
        if incident_id not in self.response_system.incidents:
            print(f"Incident {incident_id} not found")
            return
        
        incident = self.response_system.incidents[incident_id]
        
        print(f"Incident ID: {incident.id}")
        print(f"Title: {incident.title}")
        print(f"Description: {incident.description}")
        print(f"Severity: {incident.severity.value}")
        print(f"Status: {incident.status.value}")
        print(f"Created: {incident.created_at}")
        print(f"Updated: {incident.updated_at}")
        
        if incident.resolved_at:
            print(f"Resolved: {incident.resolved_at}")
        
        if incident.tags:
            print(f"Tags: {', '.join(incident.tags)}")
        
        if incident.actions_taken:
            print("\nActions Taken:")
            for action in incident.actions_taken:
                print(f"  - {action}")
        
        if incident.metadata:
            print("\nMetadata:")
            for key, value in incident.metadata.items():
                print(f"  {key}: {value}")
    
    async def create_incident(self, title: str, description: str, severity: str, tags: List[str] = None):
        """Create a new incident."""
        try:
            severity_enum = IncidentSeverity(severity)
        except ValueError:
            print(f"Invalid severity: {severity}")
            print(f"Valid options: {[s.value for s in IncidentSeverity]}")
            return
        
        incident_id = await self.response_system.create_incident(
            title=title,
            description=description,
            severity=severity_enum,
            tags=tags or []
        )
        
        print(f"Created incident: {incident_id}")
    
    async def update_status(self, incident_id: str, status: str):
        """Update incident status."""
        try:
            status_enum = IncidentStatus(status)
        except ValueError:
            print(f"Invalid status: {status}")
            print(f"Valid options: {[s.value for s in IncidentStatus]}")
            return
        
        try:
            await self.response_system.update_incident_status(incident_id, status_enum)
            print(f"Updated incident {incident_id} status to {status}")
        except ValueError as e:
            print(f"Error: {e}")
    
    async def resolve_incident(self, incident_id: str, note: str):
        """Resolve an incident."""
        try:
            await self.response_system.resolve_incident(incident_id, note)
            print(f"Resolved incident {incident_id}")
        except ValueError as e:
            print(f"Error: {e}")
    
    async def show_summary(self):
        """Show incident summary."""
        summary = self.response_system.get_incident_summary()
        
        print("Incident Summary")
        print("=" * 40)
        print(f"Total Incidents: {summary['total']}")
        
        print("\nBy Status:")
        for status, count in summary['by_status'].items():
            print(f"  {status}: {count}")
        
        print("\nBy Severity:")
        for severity, count in summary['by_severity'].items():
            print(f"  {severity}: {count}")
        
        if summary['recent']:
            print(f"\nRecent Incidents (last 24h): {len(summary['recent'])}")
            for incident in summary['recent'][:5]:  # Show top 5
                print(f"  {incident['id']}: {incident['title']} ({incident['severity']})")
    
    async def start_monitoring(self):
        """Start the incident monitoring system."""
        print("Starting incident monitoring system...")
        await self.response_system.start_monitoring()
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping incident monitoring system...")
            await self.response_system.stop_monitoring()
    
    async def test_notification(self, severity: str = "medium"):
        """Test notification system."""
        try:
            severity_enum = IncidentSeverity(severity)
        except ValueError:
            print(f"Invalid severity: {severity}")
            return
        
        incident_id = await self.response_system.create_incident(
            title="Test Notification",
            description="This is a test incident to verify notification system",
            severity=severity_enum,
            tags=["test"]
        )
        
        print(f"Created test incident: {incident_id}")
        
        # Auto-resolve after a moment
        await asyncio.sleep(2)
        await self.response_system.resolve_incident(incident_id, "Test completed")
        print(f"Resolved test incident: {incident_id}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="KDP Strategist Incident Manager")
    parser.add_argument("--config", help="Path to incident response config file")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List incidents")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--severity", help="Filter by severity")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show incident details")
    show_parser.add_argument("incident_id", help="Incident ID")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create new incident")
    create_parser.add_argument("title", help="Incident title")
    create_parser.add_argument("description", help="Incident description")
    create_parser.add_argument("severity", choices=["low", "medium", "high", "critical"])
    create_parser.add_argument("--tags", nargs="*", help="Incident tags")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update incident status")
    update_parser.add_argument("incident_id", help="Incident ID")
    update_parser.add_argument("status", choices=["open", "investigating", "resolving", "resolved", "closed"])
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve incident")
    resolve_parser.add_argument("incident_id", help="Incident ID")
    resolve_parser.add_argument("note", help="Resolution note")
    
    # Summary command
    subparsers.add_parser("summary", help="Show incident summary")
    
    # Monitor command
    subparsers.add_parser("monitor", help="Start incident monitoring")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test notification system")
    test_parser.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = IncidentManager(args.config)
    
    try:
        if args.command == "list":
            await manager.list_incidents(args.status, args.severity)
        elif args.command == "show":
            await manager.show_incident(args.incident_id)
        elif args.command == "create":
            await manager.create_incident(args.title, args.description, args.severity, args.tags)
        elif args.command == "update":
            await manager.update_status(args.incident_id, args.status)
        elif args.command == "resolve":
            await manager.resolve_incident(args.incident_id, args.note)
        elif args.command == "summary":
            await manager.show_summary()
        elif args.command == "monitor":
            await manager.start_monitoring()
        elif args.command == "test":
            await manager.test_notification(args.severity)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())