from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import AdminUser
from app.api.routes.common import (
    FORBIDDEN_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    DbSession,
    commit_or_conflict,
    get_or_404,
)
from app.models.alert import Alert, AlertSeverity, AlertType
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])
AUTH_RESPONSES = UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE


@router.get("", response_model=list[AlertResponse], responses=AUTH_RESPONSES)
async def list_alerts(
    db: DbSession,
    _: AdminUser,
    station_id: UUID | None = None,
    alert_type: Annotated[AlertType | None, Query(alias="type")] = None,
    severity: AlertSeverity | None = None,
    acknowledged: bool | None = None,
) -> list[Alert]:
    statement = select(Alert)
    if station_id is not None:
        statement = statement.where(Alert.station_id == station_id)
    if alert_type is not None:
        statement = statement.where(Alert.type == alert_type)
    if severity is not None:
        statement = statement.where(Alert.severity == severity)
    if acknowledged is not None:
        condition = (
            Alert.acknowledged_at.is_not(None) if acknowledged else Alert.acknowledged_at.is_(None)
        )
        statement = statement.where(condition)
    return list(db.scalars(statement.order_by(Alert.created_at.desc(), Alert.id)).all())


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse, responses=AUTH_RESPONSES)
async def acknowledge_alert(alert_id: UUID, db: DbSession, _: AdminUser) -> Alert:
    alert = get_or_404(db, Alert, alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(UTC)
        commit_or_conflict(db)
        db.refresh(alert)
    return alert
