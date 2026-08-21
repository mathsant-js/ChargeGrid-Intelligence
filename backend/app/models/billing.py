import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvoiceStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = (
        CheckConstraint("price_per_kwh >= 0", name="ck_tariffs_price_nonnegative"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="ck_tariffs_valid_period"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("energy_kwh >= 0", name="ck_invoices_energy_nonnegative"),
        CheckConstraint("tariff_per_kwh >= 0", name="ck_invoices_tariff_nonnegative"),
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonnegative"),
        CheckConstraint("total >= 0", name="ck_invoices_total_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_sessions.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    tariff_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", native_enum=False), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
