from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Server, ServerType, User, UserRole
from app.schemas import ServerCreate, ServerResponse, ServerUpdate
from app.services.audit import log_audit
from app.services.serializers import apply_server_credentials, server_to_response

router = APIRouter(prefix="/servers", tags=["servers"])


def _normalize_server_data(data: dict) -> dict:
    normalized = {}
    for key, value in data.items():
        if value == "":
            normalized[key] = None
        else:
            normalized[key] = value
    return normalized


def _save_server(
    db: Session,
    user: User,
    server: Server,
    *,
    username: str | None,
    password: str | None,
    ssh_key: str | None,
    audit_action: str,
) -> ServerResponse:
    try:
        apply_server_credentials(
            server,
            username if username != "" else None,
            password if password != "" else None,
            ssh_key if ssh_key != "" else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.add(server)
    db.flush()
    log_audit(db, user, audit_action, "server", str(server.id), server.name)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        detail = str(getattr(exc, "orig", exc))
        raise HTTPException(status_code=400, detail=f"Could not save server: {detail}") from exc
    db.refresh(server)
    return server_to_response(server, user)


@router.get("", response_model=list[ServerResponse])
def list_servers(
    server_type: ServerType | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Server)
    if server_type is not None:
        query = query.filter(Server.server_type == server_type)
    servers = query.order_by(Server.name).all()
    return [server_to_response(s, user) for s in servers]


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    data = _normalize_server_data(payload.model_dump(exclude={"username", "password", "ssh_key"}))
    server = Server(**data)
    return _save_server(
        db,
        user,
        server,
        username=payload.username,
        password=payload.password,
        ssh_key=payload.ssh_key,
        audit_action="create",
    )


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(
    server_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server_to_response(server, user)


@router.patch("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: UUID,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    data = _normalize_server_data(
        payload.model_dump(exclude_unset=True, exclude={"username", "password", "ssh_key"})
    )
    for key, value in data.items():
        setattr(server, key, value)

    username = payload.username if payload.username is not None else None
    password = payload.password if payload.password is not None else None
    ssh_key = payload.ssh_key if payload.ssh_key is not None else None
    if username is not None or password is not None or ssh_key is not None:
        return _save_server(
            db,
            user,
            server,
            username=username,
            password=password,
            ssh_key=ssh_key,
            audit_action="update",
        )

    log_audit(db, user, "update", "server", str(server.id), server.name)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        detail = str(getattr(exc, "orig", exc))
        raise HTTPException(status_code=400, detail=f"Could not save server: {detail}") from exc
    db.refresh(server)
    return server_to_response(server, user)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    log_audit(db, user, "delete", "server", str(server.id), server.name)
    db.delete(server)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        detail = str(getattr(exc, "orig", exc))
        raise HTTPException(status_code=400, detail=f"Could not delete server: {detail}") from exc
