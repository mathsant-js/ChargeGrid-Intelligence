from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser
from app.api.routes.common import NOT_FOUND_RESPONSE, UNAUTHORIZED_RESPONSE, DbSession
from app.core.config import get_settings
from app.models.user import UserRole
from app.schemas.analytics import DashboardResponse, SustainabilityResponse
from app.services.analytics import AnalyticsFilters, dashboard, sustainability

router = APIRouter(prefix="/analytics", tags=["analytics"])
DateFrom = Annotated[datetime | None, Query(alias="from")]
DateTo = Annotated[datetime | None, Query(alias="to")]


def filters_for_user(
    current_user_id: UUID,
    role: UserRole,
    station_id: UUID | None,
    user_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> AnalyticsFilters:
    if role != UserRole.ADMIN:
        if user_id is not None and user_id != current_user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found")
        user_id = current_user_id
    if date_from is not None and date_from.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "from must include a timezone")
    if date_to is not None and date_to.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "to must include a timezone")
    if date_from is not None:
        date_from = date_from.astimezone(UTC)
    if date_to is not None:
        date_to = date_to.astimezone(UTC)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "from must not exceed to")
    return AnalyticsFilters(station_id, user_id, date_from, date_to)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_dashboard(
    db: DbSession,
    current_user: CurrentUser,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    station_id: UUID | None = None,
    user_id: UUID | None = None,
) -> DashboardResponse:
    return dashboard(
        db,
        filters_for_user(
            current_user.id, current_user.role, station_id, user_id, date_from, date_to
        ),
    )


@router.get(
    "/sustainability",
    response_model=SustainabilityResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_sustainability(
    db: DbSession,
    current_user: CurrentUser,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    station_id: UUID | None = None,
    user_id: UUID | None = None,
) -> SustainabilityResponse:
    return sustainability(
        db,
        filters_for_user(
            current_user.id, current_user.role, station_id, user_id, date_from, date_to
        ),
        get_settings().grid_emission_factor_kg_per_kwh,
    )
