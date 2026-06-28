from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.assessment import Assessment
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.models.worker import Worker
from app.schemas.analytics import (
    DailyExposureRow,
    ExposureOverview,
    RiskSessionRow,
    RiskWorkerRow,
    WorstEventRow,
)
from app.schemas.session_summary import ScoreAggregate


def build_exposure_overview(
    db: DbSession,
    owner_user_id: str,
    period_days: int,
) -> ExposureOverview:
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=period_days)
    sessions = list(
        db.scalars(
            select(Session).where(
                Session.owner_user_id == owner_user_id,
                Session.created_at >= cutoff,
            )
        )
    )
    if not sessions:
        return _empty_overview(period_days)

    session_ids = [session.id for session in sessions]
    session_map = {session.id: session for session in sessions}
    worker_rows = db.execute(
        select(SessionWorker, Worker)
        .outerjoin(Worker, SessionWorker.worker_id == Worker.id)
        .where(SessionWorker.session_id.in_(session_ids))
    ).all()
    session_worker_map = {session_worker.id: session_worker for session_worker, _ in worker_rows}
    worker_record_map = {
        session_worker.id: worker for session_worker, worker in worker_rows if worker is not None
    }
    events = list(
        db.scalars(
            select(ErgonomicEvent).where(ErgonomicEvent.session_id.in_(session_ids))
        )
    )
    assessments = list(
        db.scalars(
            select(Assessment).where(
                Assessment.session_id.in_(session_ids),
                Assessment.assessment_status == "reviewed",
            )
        )
    )
    reviewed_event_ids = {
        assessment.ergonomic_event_id
        for assessment in assessments
        if assessment.ergonomic_event_id
    }

    worker_states: dict[str, dict[str, Any]] = {}
    session_states = {
        session.id: _session_state(session)
        for session in sessions
    }
    daily_states: dict[date, dict[str, Any]] = {}
    global_scores = _new_score_state()
    worst_events: list[WorstEventRow] = []

    for session in sessions:
        day = _event_day(session.started_at or session.created_at)
        daily = daily_states.setdefault(day, _daily_state())
        daily["sessions"].add(session.id)

    for event in events:
        session = session_map[event.session_id]
        session_worker = session_worker_map.get(event.session_worker_id)
        if session_worker is None:
            continue
        worker = worker_record_map.get(session_worker.id)
        worker_key = f"worker:{worker.id}" if worker else f"unassigned:{session_worker.id}"
        worker_state = worker_states.setdefault(
            worker_key,
            _worker_state(worker_key, session_worker, worker),
        )
        worker_state["sessions"].add(session.id)
        session_state = session_states[session.id]
        session_state["workers"].add(worker_key)
        daily = daily_states.setdefault(_event_day(event.started_at), _daily_state())
        daily["workers"].add(worker_key)

        if event.event_type == "worker_observed":
            score_stats = (event.metadata_json or {}).get("score_stats")
            _merge_score_stats(worker_state["scores"], score_stats)
            _merge_score_stats(session_state["scores"], score_stats)
            _merge_score_stats(daily["scores"], score_stats)
            _merge_score_stats(global_scores, score_stats)
        elif event.event_type == "high_risk_posture":
            duration_ms = _event_duration(event, session.stopped_at or now)
            for state in (worker_state, session_state, daily):
                state["high_risk_event_count"] += 1
                state["high_risk_duration_ms"] += duration_ms
            worst_events.append(
                WorstEventRow(
                    event_id=event.id,
                    session_id=session.id,
                    session_code=session.session_code,
                    session_worker_id=session_worker.id,
                    worker_name=worker.name if worker else session_worker.edge_worker_id,
                    event_type=event.event_type,
                    started_at=event.started_at,
                    duration_ms=duration_ms,
                    score_type=event.score_type,
                    score=event.score,
                    risk_level=event.risk_level,
                    severity=event.severity,
                    reviewed=event.id in reviewed_event_ids,
                )
            )
        elif event.event_type == "sustained_high_risk":
            worker_state["sustained_event_count"] += 1
            session_state["sustained_event_count"] += 1
            daily["sustained_event_count"] += 1

    top_workers = sorted(
        (_worker_row(state) for state in worker_states.values()),
        key=lambda row: (
            row.high_risk_duration_ms,
            row.high_risk_event_count,
            max(row.rula.peak or 0, row.reba.peak or 0),
        ),
        reverse=True,
    )[:8]
    top_sessions = sorted(
        (_session_row(state) for state in session_states.values()),
        key=lambda row: (
            row.high_risk_duration_ms,
            row.high_risk_event_count,
            max(row.peak_rula or 0, row.peak_reba or 0),
        ),
        reverse=True,
    )[:8]
    trends = [_daily_row(day, daily_states[day]) for day in sorted(daily_states)]
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    worst_events.sort(
        key=lambda event: (
            severity_rank.get(event.severity, 0),
            event.score or 0,
            event.duration_ms,
        ),
        reverse=True,
    )

    return ExposureOverview(
        period_days=period_days,
        session_count=len(sessions),
        completed_session_count=sum(session.status == "completed" for session in sessions),
        worker_count=len(worker_states),
        high_risk_event_count=sum(
            state["high_risk_event_count"] for state in session_states.values()
        ),
        sustained_event_count=sum(
            state["sustained_event_count"] for state in session_states.values()
        ),
        high_risk_duration_ms=sum(
            state["high_risk_duration_ms"] for state in session_states.values()
        ),
        reviewed_assessment_count=len(assessments),
        rula=_score_row(global_scores, "rula"),
        reba=_score_row(global_scores, "reba"),
        top_workers=top_workers,
        top_sessions=top_sessions,
        daily_trend=trends,
        worst_events=worst_events[:8],
    )


def _worker_state(worker_key: str, session_worker: SessionWorker, worker: Worker | None) -> dict:
    return {
        "worker_key": worker_key,
        "worker_id": worker.id if worker else None,
        "worker_name": worker.name if worker else session_worker.edge_worker_id,
        "employee_number": worker.employee_number if worker else None,
        "sessions": set(),
        "high_risk_event_count": 0,
        "high_risk_duration_ms": 0,
        "sustained_event_count": 0,
        "scores": _new_score_state(),
    }


def _session_state(session: Session) -> dict:
    return {
        "session": session,
        "workers": set(),
        "high_risk_event_count": 0,
        "high_risk_duration_ms": 0,
        "sustained_event_count": 0,
        "scores": _new_score_state(),
    }


def _daily_state() -> dict:
    return {
        "sessions": set(),
        "workers": set(),
        "high_risk_event_count": 0,
        "high_risk_duration_ms": 0,
        "sustained_event_count": 0,
        "scores": _new_score_state(),
    }


def _new_score_state() -> dict[str, dict[str, int]]:
    return {
        "rula": {"sum": 0, "count": 0, "peak": 0},
        "reba": {"sum": 0, "count": 0, "peak": 0},
    }


def _merge_score_stats(target: dict, source: object) -> None:
    if not isinstance(source, dict):
        return
    for score_type in ("rula", "reba"):
        values = source.get(score_type)
        if not isinstance(values, dict):
            continue
        target[score_type]["sum"] += int(values.get("sum") or 0)
        target[score_type]["count"] += int(values.get("count") or 0)
        target[score_type]["peak"] = max(
            target[score_type]["peak"], int(values.get("peak") or 0)
        )


def _score_row(scores: dict, score_type: str) -> ScoreAggregate:
    values = scores[score_type]
    count = values["count"]
    return ScoreAggregate(
        average=round(values["sum"] / count, 2) if count else None,
        peak=values["peak"] or None,
        samples=count,
    )


def _worker_row(state: dict) -> RiskWorkerRow:
    return RiskWorkerRow(
        worker_key=state["worker_key"],
        worker_id=state["worker_id"],
        worker_name=state["worker_name"],
        employee_number=state["employee_number"],
        session_count=len(state["sessions"]),
        high_risk_event_count=state["high_risk_event_count"],
        high_risk_duration_ms=state["high_risk_duration_ms"],
        sustained_event_count=state["sustained_event_count"],
        rula=_score_row(state["scores"], "rula"),
        reba=_score_row(state["scores"], "reba"),
    )


def _session_row(state: dict) -> RiskSessionRow:
    session = state["session"]
    return RiskSessionRow(
        session_id=session.id,
        session_code=session.session_code,
        notes=session.notes,
        status=session.status,
        started_at=session.started_at,
        worker_count=len(state["workers"]),
        high_risk_event_count=state["high_risk_event_count"],
        high_risk_duration_ms=state["high_risk_duration_ms"],
        peak_rula=state["scores"]["rula"]["peak"] or None,
        peak_reba=state["scores"]["reba"]["peak"] or None,
    )


def _daily_row(day: date, state: dict) -> DailyExposureRow:
    return DailyExposureRow(
        day=day,
        session_count=len(state["sessions"]),
        worker_count=len(state["workers"]),
        high_risk_event_count=state["high_risk_event_count"],
        high_risk_duration_ms=state["high_risk_duration_ms"],
        peak_rula=state["scores"]["rula"]["peak"] or None,
        peak_reba=state["scores"]["reba"]["peak"] or None,
    )


def _event_duration(event: ErgonomicEvent, ended_at: datetime) -> int:
    if event.duration_ms is not None:
        return event.duration_ms
    start = event.started_at if event.started_at.tzinfo else event.started_at.replace(tzinfo=UTC)
    end = ended_at if ended_at.tzinfo else ended_at.replace(tzinfo=UTC)
    return max(0, int((end - start).total_seconds() * 1000))


def _event_day(value: datetime) -> date:
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).date()


def _empty_overview(period_days: int) -> ExposureOverview:
    empty_score = ScoreAggregate(average=None, peak=None, samples=0)
    return ExposureOverview(
        period_days=period_days,
        session_count=0,
        completed_session_count=0,
        worker_count=0,
        high_risk_event_count=0,
        sustained_event_count=0,
        high_risk_duration_ms=0,
        reviewed_assessment_count=0,
        rula=empty_score,
        reba=empty_score,
        top_workers=[],
        top_sessions=[],
        daily_trend=[],
        worst_events=[],
    )
