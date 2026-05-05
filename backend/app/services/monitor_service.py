from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Alert, ContractTask


def sweep_deadlines(db: Session) -> int:
    """Create alerts for upcoming and overdue open tasks. Returns number of new alerts."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=settings.alert_upcoming_days)
    tasks = (
        db.query(ContractTask)
        .filter(ContractTask.status == "open", ContractTask.due_date.isnot(None))
        .all()
    )
    created = 0
    for task in tasks:
        due = task.due_date
        if due is None:
            continue
        if due < now:
            atype = "overdue"
            msg = f"Overdue: {task.task_name} (was due {due.date().isoformat()})"
        elif due <= horizon:
            atype = "upcoming"
            msg = f"Upcoming deadline: {task.task_name} on {due.date().isoformat()}"
        else:
            continue
        recent = (
            db.query(Alert)
            .filter(
                Alert.task_id == task.id,
                Alert.alert_type == atype,
                Alert.resolved.is_(False),
            )
            .first()
        )
        if recent:
            continue
        db.add(
            Alert(
                contract_id=task.contract_id,
                task_id=task.id,
                alert_type=atype,
                message=msg,
                resolved=False,
            )
        )
        created += 1
    if created:
        db.commit()
    return created
