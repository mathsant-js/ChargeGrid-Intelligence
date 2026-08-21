from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity, AlertType


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    station_id: UUID
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    created_at: datetime
    acknowledged_at: datetime | None
