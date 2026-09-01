from collections.abc import Mapping
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import get_db
from app.schemas.common import ErrorResponse

DbSession = Annotated[Session, Depends(get_db)]

OpenAPIResponses = dict[int | str, dict[str, Any]]

UNAUTHORIZED_RESPONSE: OpenAPIResponses = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are missing or invalid",
    }
}
FORBIDDEN_RESPONSE: OpenAPIResponses = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "The authenticated user does not have permission",
    }
}
NOT_FOUND_RESPONSE: OpenAPIResponses = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "The requested resource does not exist or is not visible to the user",
    }
}
CONFLICT_RESPONSE: OpenAPIResponses = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "The request conflicts with the current resource state",
    }
}


def get_or_404[ModelT: Base](db: Session, model: type[ModelT], resource_id: UUID) -> ModelT:
    instance = db.get(model, resource_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return instance


def commit_or_conflict(
    db: Session, constraint_details: Mapping[str, str] | None = None
) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        error_text = str(exc.orig)
        detail = next(
            (
                message
                for constraint, message in (constraint_details or {}).items()
                if constraint == constraint_name or constraint in error_text
            ),
            None,
        )
        if detail is None:
            raise
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
