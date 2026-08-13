from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import Report


def crime_hotspots(db: Session, limit: int = 5) -> list[dict]:
    rows = (
        db.query(Report.location, func.count(Report.id).label("count"))
        .filter(Report.location.isnot(None), Report.location != "")
        .group_by(Report.location)
        .order_by(func.count(Report.id).desc())
        .limit(limit)
        .all()
    )
    return [{"location": location, "count": count} for location, count in rows]


def category_trends(db: Session) -> list[dict]:
    now = datetime.now(timezone.utc)
    last_week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    current_counts = dict(
        db.query(Report.category, func.count(Report.id))
        .filter(Report.created_at >= last_week_start)
        .group_by(Report.category)
        .all()
    )
    previous_counts = dict(
        db.query(Report.category, func.count(Report.id))
        .filter(Report.created_at >= prev_week_start, Report.created_at < last_week_start)
        .group_by(Report.category)
        .all()
    )

    categories = set(current_counts) | set(previous_counts)
    trends = []
    for category in categories:
        current = current_counts.get(category, 0)
        previous = previous_counts.get(category, 0)
        if previous == 0:
            change_pct = 100.0 if current > 0 else 0.0
        else:
            change_pct = round((current - previous) / previous * 100, 1)
        trends.append({
            "category": category,
            "current_count": current,
            "previous_count": previous,
            "change_pct": change_pct,
        })
    trends.sort(key=lambda t: t["current_count"], reverse=True)
    return trends


def priority_breakdown(db: Session) -> list[dict]:
    rows = (
        db.query(Report.priority, func.count(Report.id))
        .group_by(Report.priority)
        .all()
    )
    return [{"priority": priority, "count": count} for priority, count in rows]
