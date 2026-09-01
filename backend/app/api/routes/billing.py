from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.billing import Invoice, InvoiceStatus, Tariff
from app.schemas.billing import InvoiceResponse, TariffCreate, TariffResponse, TariffUpdate

router = APIRouter(tags=["billing"])


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def deactivate_other_tariffs(db: DbSession, tariff_id: UUID | None = None) -> None:
    statement = update(Tariff).where(Tariff.is_active.is_(True))
    if tariff_id is not None:
        statement = statement.where(Tariff.id != tariff_id)
    db.execute(statement.values(is_active=False))


@router.get("/tariffs", response_model=list[TariffResponse])
async def list_tariffs(db: DbSession) -> list[Tariff]:
    return list(db.scalars(select(Tariff).order_by(Tariff.created_at, Tariff.id)).all())


@router.post("/tariffs", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
async def create_tariff(payload: TariffCreate, db: DbSession) -> Tariff:
    tariff = Tariff(**payload.model_dump())
    if tariff.is_active:
        deactivate_other_tariffs(db)
    db.add(tariff)
    commit_or_conflict(db)
    db.refresh(tariff)
    return tariff


@router.get("/tariffs/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: UUID, db: DbSession) -> Tariff:
    return get_or_404(db, Tariff, tariff_id)


@router.patch("/tariffs/{tariff_id}", response_model=TariffResponse)
async def update_tariff(payload: TariffUpdate, tariff_id: UUID, db: DbSession) -> Tariff:
    tariff = get_or_404(db, Tariff, tariff_id)
    changes = payload.model_dump(exclude_unset=True)
    valid_from = changes.get("valid_from", tariff.valid_from)
    valid_until = changes.get("valid_until", tariff.valid_until)
    if valid_until is not None and as_utc(valid_until) <= as_utc(valid_from):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid tariff validity period")
    if changes.get("is_active") is True:
        deactivate_other_tariffs(db, tariff.id)
    for field, value in changes.items():
        setattr(tariff, field, value)
    commit_or_conflict(db)
    db.refresh(tariff)
    return tariff


@router.get("/billing/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    db: DbSession,
    user_id: UUID | None = None,
    invoice_status: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
) -> list[Invoice]:
    statement = select(Invoice)
    if user_id is not None:
        statement = statement.where(Invoice.user_id == user_id)
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    return list(db.scalars(statement.order_by(Invoice.created_at, Invoice.id)).all())


@router.get("/billing/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID, db: DbSession) -> Invoice:
    return get_or_404(db, Invoice, invoice_id)
