from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class ActionSpec(BaseModel):
    action: str = Field(..., description="Name of the action, e.g., 'create_followup_task'")
    params: dict = Field(default_factory=dict, description="Parameters for the action")

class TaskRequest(BaseModel):
    description: str = Field(..., description="Human readable description of the workflow")
    filters: dict = Field(default_factory=dict, description="Filters for searching opportunities")
    actions: List[ActionSpec] = Field(..., description="List of actions to perform on each matched record")
    preview_only: bool = Field(default=True, description="If true, only return a preview without side‑effects")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    preview: Optional[dict] = None
    message: Optional[str] = None

# Simple in‑memory store for demo purposes
_tasks = {}

@router.post("/", response_model=TaskResponse)
def submit_task(request: TaskRequest):
    # In a real implementation this would invoke the LangGraph agent.
    task_id = f"task-{len(_tasks) + 1}"
    _tasks[task_id] = {"request": request, "status": "received"}
    return TaskResponse(
        task_id=task_id,
        status="received",
        preview={"filters": request.filters, "actions": [a.action for a in request.actions]},
        message="Preview generated – execution not yet implemented.",
    )

@router.get("/{task_id}", response_model=TaskResponse)
def get_status(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    entry = _tasks[task_id]
    return TaskResponse(
        task_id=task_id,
        status=entry["status"],
        message="Status placeholder",
    )
