from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.billing import router as billing_router
from app.api.routes.chargers import router as chargers_router
from app.api.routes.energy import router as energy_router
from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.solar import router as solar_router
from app.api.routes.stations import router as stations_router
from app.api.routes.users import router as users_router
from app.api.routes.vehicles import router as vehicles_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(vehicles_router)
api_router.include_router(stations_router)
api_router.include_router(chargers_router)
api_router.include_router(sessions_router)
api_router.include_router(energy_router)
api_router.include_router(solar_router)
api_router.include_router(billing_router)
api_router.include_router(alerts_router)
