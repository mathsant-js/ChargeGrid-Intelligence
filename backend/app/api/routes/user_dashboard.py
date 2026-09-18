from fastapi import APIRouter

from app.api.dependencies import RegularUser
from app.api.routes.common import FORBIDDEN_RESPONSE, UNAUTHORIZED_RESPONSE, DbSession
from app.schemas.user_dashboard import UserDashboardResponse
from app.services.user_dashboard import get_user_dashboard

router = APIRouter(prefix="/user", tags=["user dashboard"])


@router.get(
    "/dashboard",
    response_model=UserDashboardResponse,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE,
)
async def user_dashboard(db: DbSession, current_user: RegularUser) -> UserDashboardResponse:
    return get_user_dashboard(db, current_user.id)
