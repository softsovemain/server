from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Database, User, UserRole
from app.schemas import DatabaseCreate, DatabaseResponse, DatabaseUpdate
from app.services.audit import log_audit
from app.services.encryption import encrypt_value
from app.services.serializers import database_to_response

router = APIRouter(prefix="/databases", tags=["databases"])


@router.get("", response_model=list[DatabaseResponse])
def list_databases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = db.query(Database).order_by(Database.name).all()
    return [database_to_response(r, user) for r in records]


@router.post("", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED)
def create_database(
    payload: DatabaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    data = payload.model_dump(exclude={"connection_string"})
    record = Database(**data)
    if payload.connection_string:
        record.connection_string_encrypted = encrypt_value(payload.connection_string)
    db.add(record)
    db.commit()
    db.refresh(record)
    log_audit(db, user, "create", "database", str(record.id), record.name)
    return database_to_response(record, user)


@router.get("/{database_id}", response_model=DatabaseResponse)
def get_database(
    database_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.query(Database).filter(Database.id == database_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Database not found")
    return database_to_response(record, user)


@router.patch("/{database_id}", response_model=DatabaseResponse)
def update_database(
    database_id: UUID,
    payload: DatabaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    record = db.query(Database).filter(Database.id == database_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Database not found")
    data = payload.model_dump(exclude_unset=True, exclude={"connection_string"})
    for key, value in data.items():
        setattr(record, key, value)
    if payload.connection_string is not None:
        record.connection_string_encrypted = encrypt_value(payload.connection_string) if payload.connection_string else None
    db.commit()
    db.refresh(record)
    log_audit(db, user, "update", "database", str(record.id), record.name)
    return database_to_response(record, user)


@router.delete("/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database(
    database_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    record = db.query(Database).filter(Database.id == database_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Database not found")
    log_audit(db, user, "delete", "database", str(record.id), record.name)
    db.delete(record)
    db.commit()
