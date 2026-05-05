from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskOut(BaseModel):
    id: int
    task_name: str
    due_date: datetime | None
    priority: str
    status: str

    model_config = {"from_attributes": True}


class RiskOut(BaseModel):
    id: int
    title: str
    description: str
    category: str
    score: float

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: int
    contract_id: int
    task_id: int | None
    alert_type: str
    message: str
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractSummary(BaseModel):
    id: int
    filename: str
    overall_risk_score: float
    created_at: datetime
    task_count: int = 0
    open_alert_count: int = 0

    model_config = {"from_attributes": True}


class ContractDetail(BaseModel):
    id: int
    filename: str
    parsed_summary: dict[str, Any] = Field(default_factory=dict)
    overall_risk_score: float
    created_at: datetime
    tasks: list[TaskOut] = []
    risks: list[RiskOut] = []
    alerts: list[AlertOut] = []


class DashboardOut(BaseModel):
    total_contracts: int
    open_tasks: int
    upcoming_deadlines: int
    overdue_tasks: int
    open_alerts: int
    avg_risk_score: float
    risk_histogram: dict[str, int]
    recent_alerts: list[AlertOut]
    contracts: list[ContractSummary]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
