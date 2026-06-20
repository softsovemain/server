from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Server, ServerType, User, UserRole
from app.schemas import ServerCreate, ServerResponse, ServerUpdate
from app.services.audit import log_audit
from app.services.serializers import apply_server_credentials, server_to_response

router = APIRouter(prefix="/servers", tags=["servers"])


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
    data = payload.model_dump(exclude={"username", "password", "ssh_key"})
    server = Server(**data)
    apply_server_credentials(server, payload.username, payload.password, payload.ssh_key)
    db.add(server)
    db.commit()
    db.refresh(server)
    log_audit(db, user, "create", "server", str(server.id), server.name)
    return server_to_response(server, user)


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
    data = payload.model_dump(exclude_unset=True, exclude={"username", "password", "ssh_key"})
    for key, value in data.items():
        setattr(server, key, value)
    if payload.username is not None or payload.password is not None or payload.ssh_key is not None:
        apply_server_credentials(server, payload.username, payload.password, payload.ssh_key)
    db.commit()
    db.refresh(server)
    log_audit(db, user, "update", "server", str(server.id), server.name)
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
    db.commit()
