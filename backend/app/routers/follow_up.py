"""
Proactive Follow-Up API Router.
Endpoints:
- POST /api/follow-up/schedule: Queue a follow-up task
- GET /api/follow-up/tasks: List follow-up tasks
- GET /api/follow-up/task/{task_id}: Get specific task details
- POST /api/follow-up/trigger-due: Batch scheduler worker run
- POST /api/follow-up/trigger/{task_id}: Simulate immediate Day 2 trigger
- POST /api/follow-up/respond/{task_id}: Submit patient recovery feedback
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.models.follow_up import (
    FollowUpTask,
    FollowUpCreateRequest,
    FollowUpResponseRequest,
)
from app.services.follow_up_service import follow_up_service

router = APIRouter(prefix="/api/follow-up", tags=["Proactive Follow-Up Agent"])


@router.post("/schedule", response_model=FollowUpTask)
async def schedule_follow_up_task(request: FollowUpCreateRequest) -> FollowUpTask:
    """
    Schedules an asynchronous post-consultation / medication recovery check-in.
    Default delay: 48 hours.
    """
    try:
        return follow_up_service.schedule_follow_up(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule follow-up: {str(e)}")


@router.get("/tasks", response_model=List[FollowUpTask])
async def list_follow_up_tasks(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, DISPATCHED, COMPLETED)"),
    limit: int = Query(50, ge=1, le=200)
) -> List[FollowUpTask]:
    """Lists scheduled and executed follow-up tasks."""
    return follow_up_service.list_tasks(patient_id=patient_id, status=status, limit=limit)


@router.get("/task/{task_id}", response_model=FollowUpTask)
async def get_follow_up_task(task_id: str) -> FollowUpTask:
    """Retrieves single follow-up task with its multi-channel notification history."""
    task = follow_up_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Follow-up task {task_id} not found")
    return task


@router.post("/trigger-due", response_model=List[FollowUpTask])
async def trigger_due_tasks() -> List[FollowUpTask]:
    """
    Batch scheduler worker execution.
    Inspects Redis / DB for tasks past their 48-hour trigger time and dispatches notifications.
    """
    return follow_up_service.trigger_due_followups()


@router.post("/trigger/{task_id}", response_model=FollowUpTask)
async def trigger_task_immediately(task_id: str) -> FollowUpTask:
    """
    Simulates immediate execution of Day 2 follow-up for demonstrations and testing.
    Executes Follow-Up Agent and dispatches WhatsApp, SMS, and App notifications.
    """
    task = follow_up_service.trigger_task_now(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Follow-up task {task_id} not found")
    return task


@router.post("/respond/{task_id}", response_model=FollowUpTask)
async def submit_patient_response(task_id: str, request: FollowUpResponseRequest) -> FollowUpTask:
    """
    Records patient's response to recovery check-in ('Feeling much better', 'Fever is persisting').
    Analyzes recovery status and re-escalates to triage if needed.
    """
    request.task_id = task_id
    task = follow_up_service.record_patient_response(request)
    if not task:
        raise HTTPException(status_code=404, detail=f"Follow-up task {task_id} not found")
    return task
