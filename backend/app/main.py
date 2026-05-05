"""FastAPI application — Agentic Contract Intelligence.

Routes and lifecycle management. Uses Microsoft Agent Framework agents
(via pipeline.py) for all LLM-powered operations.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.models import Alert, Contract, ContractRisk, ContractTask
from app.schemas import AlertOut, ContractDetail, ContractSummary, DashboardOut, QueryRequest, QueryResponse, RiskOut, TaskOut
from app.services import document_service, monitor_service, pipeline


def run_sweep():
    db = SessionLocal()
    try:
        monitor_service.sweep_deadlines(db)
    finally:
        db.close()


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    init_db()
    scheduler.add_job(run_sweep, "interval", minutes=settings.scheduler_interval_minutes, id="deadline_sweep")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Agentic Contract Intelligence", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "groq_configured": bool(settings.groq_api_key)}


@app.post("/upload")
async def upload_contract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "No filename")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    try:
        text = document_service.extract_text_from_bytes(file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    path = document_service.save_upload(file.filename, content)
    contract = Contract(filename=file.filename, stored_path=path, raw_text=text)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    try:
        # Agentic pipeline — orchestrator agent coordinates everything
        result = await pipeline.process_contract_full(db, contract)
    except Exception as e:
        raise HTTPException(502, f"LLM processing failed: {e!s}") from e
    return {
        "id": contract.id,
        "filename": contract.filename,
        "message": "Contract processed",
        **result,
    }


def _risk_histogram(db: Session) -> dict[str, int]:
    rows = db.query(Contract.overall_risk_score).all()
    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for (score,) in rows:
        s = float(score or 0)
        if s <= 20:
            buckets["0-20"] += 1
        elif s <= 40:
            buckets["21-40"] += 1
        elif s <= 60:
            buckets["41-60"] += 1
        elif s <= 80:
            buckets["61-80"] += 1
        else:
            buckets["81-100"] += 1
    return buckets


@app.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    horizon = now + timedelta(days=settings.alert_upcoming_days)
    total = db.query(func.count(Contract.id)).scalar() or 0
    open_tasks = (
        db.query(func.count(ContractTask.id)).filter(ContractTask.status == "open").scalar() or 0
    )
    upcoming = (
        db.query(func.count(ContractTask.id))
        .filter(
            ContractTask.status == "open",
            ContractTask.due_date.isnot(None),
            ContractTask.due_date >= now,
            ContractTask.due_date <= horizon,
        )
        .scalar()
        or 0
    )
    overdue = (
        db.query(func.count(ContractTask.id))
        .filter(
            ContractTask.status == "open",
            ContractTask.due_date.isnot(None),
            ContractTask.due_date < now,
        )
        .scalar()
        or 0
    )
    open_alerts = db.query(func.count(Alert.id)).filter(Alert.resolved.is_(False)).scalar() or 0
    avg_risk = db.query(func.avg(Contract.overall_risk_score)).scalar()
    avg_risk_f = float(avg_risk or 0)
    recent_alerts = (
        db.query(Alert).filter(Alert.resolved.is_(False)).order_by(Alert.created_at.desc()).limit(15).all()
    )
    contracts_db = db.query(Contract).order_by(Contract.created_at.desc()).all()
    summaries: list[ContractSummary] = []
    for c in contracts_db:
        tc = db.query(func.count(ContractTask.id)).filter(ContractTask.contract_id == c.id).scalar() or 0
        ac = (
            db.query(func.count(Alert.id))
            .filter(Alert.contract_id == c.id, Alert.resolved.is_(False))
            .scalar()
            or 0
        )
        summaries.append(
            ContractSummary(
                id=c.id,
                filename=c.filename,
                overall_risk_score=c.overall_risk_score,
                created_at=c.created_at,
                task_count=int(tc),
                open_alert_count=int(ac),
            )
        )
    return DashboardOut(
        total_contracts=int(total),
        open_tasks=int(open_tasks),
        upcoming_deadlines=int(upcoming),
        overdue_tasks=int(overdue),
        open_alerts=int(open_alerts),
        avg_risk_score=round(avg_risk_f, 2),
        risk_histogram=_risk_histogram(db),
        recent_alerts=[AlertOut.model_validate(a) for a in recent_alerts],
        contracts=summaries,
    )


@app.get("/contracts/{contract_id}", response_model=ContractDetail)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(404, "Contract not found")
    try:
        parsed = json.loads(c.parsed_json) if c.parsed_json else {}
    except json.JSONDecodeError:
        parsed = {}
    tasks = db.query(ContractTask).filter(ContractTask.contract_id == c.id).all()
    risks = db.query(ContractRisk).filter(ContractRisk.contract_id == c.id).all()
    alerts = (
        db.query(Alert)
        .filter(Alert.contract_id == c.id, Alert.resolved.is_(False))
        .order_by(Alert.created_at.desc())
        .limit(20)
        .all()
    )
    return ContractDetail(
        id=c.id,
        filename=c.filename,
        parsed_summary=parsed if isinstance(parsed, dict) else {},
        overall_risk_score=c.overall_risk_score,
        created_at=c.created_at,
        tasks=[TaskOut.model_validate(t) for t in tasks],
        risks=[RiskOut.model_validate(r) for r in risks],
        alerts=[AlertOut.model_validate(a) for a in alerts],
    )


@app.post("/contracts/{contract_id}/query", response_model=QueryResponse)
async def query_contract(contract_id: int, body: QueryRequest, db: Session = Depends(get_db)):
    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(404, "Contract not found")
    try:
        # Agentic RAG query
        answer, sources = await pipeline.rag_answer(db, c.id, body.question, c.raw_text)
    except Exception as e:
        raise HTTPException(502, f"Query failed: {e!s}") from e
    return QueryResponse(answer=answer, sources=sources)


@app.post("/alerts/{alert_id}/draft-email")
async def draft_email_for_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    contract = db.get(Contract, alert.contract_id)
    name = contract.filename if contract else "contract"
    try:
        # Agentic email draft
        draft = await pipeline.draft_action_message(alert.message, name)
    except Exception as e:
        raise HTTPException(502, f"Draft failed: {e!s}") from e
    return {"alert_id": alert_id, **draft}


@app.post("/monitor/run")
def run_monitor_once(db: Session = Depends(get_db)):
    n = monitor_service.sweep_deadlines(db)
    return {"new_alerts": n}


@app.post("/tasks/{task_id}/resolve")
def resolve_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(ContractTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.status = "done"
    for a in db.query(Alert).filter(Alert.task_id == task_id, Alert.resolved.is_(False)).all():
        a.resolved = True
    db.commit()
    return {"ok": True, "task_id": task_id}


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.resolved = True
    db.commit()
    return {"ok": True}
