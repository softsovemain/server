from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Project, ProjectCommand, User, UserRole
from app.schemas import ProjectCommandCreate, ProjectCommandResponse, ProjectCommandUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/commands", tags=["commands"])


def _ensure_backend_project(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.backend_server_id:
        raise HTTPException(
            status_code=400,
            detail="Commands can only be linked to projects with a backend server",
        )
    return project


def command_to_response(cmd: ProjectCommand) -> ProjectCommandResponse:
    return ProjectCommandResponse(
        id=cmd.id,
        project_id=cmd.project_id,
        label=cmd.label,
        command=cmd.command,
        created_at=cmd.created_at,
        updated_at=cmd.updated_at,
        project_name=cmd.project.name if cmd.project else None,
    )


@router.get("", response_model=list[ProjectCommandResponse])
def list_commands(
    project_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(ProjectCommand).join(Project).filter(Project.backend_server_id.isnot(None))
    if project_id:
        query = query.filter(ProjectCommand.project_id == project_id)
    commands = query.order_by(Project.name, ProjectCommand.label).all()
    return [command_to_response(c) for c in commands]


@router.post("", response_model=ProjectCommandResponse, status_code=status.HTTP_201_CREATED)
def create_command(
    payload: ProjectCommandCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    project = _ensure_backend_project(db, payload.project_id)
    cmd = ProjectCommand(**payload.model_dump())
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    log_audit(db, user, "create", "command", str(cmd.id), f"{project.name}: {cmd.label}")
    return command_to_response(cmd)


@router.patch("/{command_id}", response_model=ProjectCommandResponse)
def update_command(
    command_id: UUID,
    payload: ProjectCommandUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    cmd = db.query(ProjectCommand).filter(ProjectCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")

    data = payload.model_dump(exclude_unset=True)
    if "project_id" in data:
        _ensure_backend_project(db, data["project_id"])

    for key, value in data.items():
        setattr(cmd, key, value)

    db.commit()
    db.refresh(cmd)
    log_audit(db, user, "update", "command", str(cmd.id), cmd.label)
    return command_to_response(cmd)


@router.delete("/{command_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_command(
    command_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    cmd = db.query(ProjectCommand).filter(ProjectCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    log_audit(db, user, "delete", "command", str(cmd.id), cmd.label)
    db.delete(cmd)
    db.commit()
