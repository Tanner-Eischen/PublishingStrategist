"""
Incident management API endpoints.

This module provides REST API endpoints for managing incidents
in the KDP Strategist system.
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.kdp_strategist.data.automated_incident_response import (
    AutomatedIncidentResponse, IncidentSeverity, IncidentStatus
)


# Pydantic models for API
class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str
    tags: List[str] = []
    metadata: Dict = {}


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    tags: List[str]
    metadata: Dict
    actions_taken: List[str]


class IncidentSummaryResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    recent: List[Dict]


router = APIRouter(prefix="/incidents", tags=["incidents"])

# Global incident response system instance
incident_response = None


def get_incident_response():
    """Get or create incident response system instance."""
    global incident_response
    if incident_response is None:
        # Load configuration
        try:
            import json
            with open("config/incident_response.json", 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {}
        
        incident_response = AutomatedIncidentResponse(config)
    
    return incident_response


@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, description="Maximum number of incidents to return")
):
    """List incidents with optional filtering."""
    response_system = get_incident_response()
    incidents = list(response_system.incidents.values())
    
    # Apply filters
    if status:
        incidents = [i for i in incidents if i.status.value == status]
    
    if severity:
        incidents = [i for i in incidents if i.severity.value == severity]
    
    # Sort by creation time (newest first) and limit
    incidents = sorted(incidents, key=lambda x: x.created_at, reverse=True)[:limit]
    
    # Convert to response format
    return [
        IncidentResponse(
            id=incident.id,
            title=incident.title,
            description=incident.description,
            severity=incident.severity.value,
            status=incident.status.value,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            resolved_at=incident.resolved_at,
            tags=incident.tags,
            metadata=incident.metadata,
            actions_taken=incident.actions_taken
        )
        for incident in incidents
    ]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str):
    """Get detailed information about a specific incident."""
    response_system = get_incident_response()
    
    if incident_id not in response_system.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = response_system.incidents[incident_id]
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        tags=incident.tags,
        metadata=incident.metadata,
        actions_taken=incident.actions_taken
    )


@router.post("/", response_model=Dict[str, str])
async def create_incident(incident_data: IncidentCreate):
    """Create a new incident."""
    response_system = get_incident_response()
    
    try:
        severity = IncidentSeverity(incident_data.severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Valid options: {[s.value for s in IncidentSeverity]}"
        )
    
    incident_id = await response_system.create_incident(
        title=incident_data.title,
        description=incident_data.description,
        severity=severity,
        tags=incident_data.tags,
        metadata=incident_data.metadata
    )
    
    return {"incident_id": incident_id, "message": "Incident created successfully"}


@router.put("/{incident_id}", response_model=Dict[str, str])
async def update_incident(incident_id: str, update_data: IncidentUpdate):
    """Update an existing incident."""
    response_system = get_incident_response()
    
    if incident_id not in response_system.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = response_system.incidents[incident_id]
    
    # Update status if provided
    if update_data.status:
        try:
            status = IncidentStatus(update_data.status)
            await response_system.update_incident_status(incident_id, status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid options: {[s.value for s in IncidentStatus]}"
            )
    
    # Update other fields
    if update_data.description is not None:
        incident.description = update_data.description
        incident.updated_at = datetime.now()
    
    if update_data.tags is not None:
        incident.tags = update_data.tags
        incident.updated_at = datetime.now()
    
    if update_data.metadata is not None:
        incident.metadata.update(update_data.metadata)
        incident.updated_at = datetime.now()
    
    return {"message": "Incident updated successfully"}


@router.post("/{incident_id}/resolve", response_model=Dict[str, str])
async def resolve_incident(incident_id: str, resolution_note: str):
    """Resolve an incident."""
    response_system = get_incident_response()
    
    try:
        await response_system.resolve_incident(incident_id, resolution_note)
        return {"message": "Incident resolved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary/overview", response_model=IncidentSummaryResponse)
async def get_incident_summary():
    """Get incident summary statistics."""
    response_system = get_incident_response()
    summary = response_system.get_incident_summary()
    
    return IncidentSummaryResponse(**summary)


@router.post("/monitoring/start", response_model=Dict[str, str])
async def start_monitoring():
    """Start the incident monitoring system."""
    response_system = get_incident_response()
    
    if response_system.is_running:
        return {"message": "Monitoring system is already running"}
    
    await response_system.start_monitoring()
    return {"message": "Incident monitoring started successfully"}


@router.post("/monitoring/stop", response_model=Dict[str, str])
async def stop_monitoring():
    """Stop the incident monitoring system."""
    response_system = get_incident_response()
    
    if not response_system.is_running:
        return {"message": "Monitoring system is not running"}
    
    await response_system.stop_monitoring()
    return {"message": "Incident monitoring stopped successfully"}


@router.get("/monitoring/status", response_model=Dict[str, bool])
async def get_monitoring_status():
    """Get monitoring system status."""
    response_system = get_incident_response()
    return {"is_running": response_system.is_running}


@router.post("/test/notification", response_model=Dict[str, str])
async def test_notification(severity: str = "medium"):
    """Test the notification system by creating a test incident."""
    response_system = get_incident_response()
    
    try:
        severity_enum = IncidentSeverity(severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Valid options: {[s.value for s in IncidentSeverity]}"
        )
    
    incident_id = await response_system.create_incident(
        title="Test Notification",
        description="This is a test incident to verify the notification system",
        severity=severity_enum,
        tags=["test", "notification"]
    )
    
    # Auto-resolve the test incident
    import asyncio
    await asyncio.sleep(1)
    await response_system.resolve_incident(incident_id, "Test notification completed")
    
    return {
        "incident_id": incident_id,
        "message": "Test notification sent and incident auto-resolved"
    }