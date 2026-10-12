"""Durable simulator clock checkpoint."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SimulationState(Base):
    """Singleton checkpoint committed atomically with the simulator tick."""

    __tablename__ = "simulation_state"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    singleton_key: Mapped[bool] = mapped_column(Boolean, unique=True, nullable=False, default=True)
    current_instant: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_tick: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
