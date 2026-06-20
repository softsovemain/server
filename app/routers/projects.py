from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Project, User, UserRole
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/projects", tags=["projects"])


def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        category_id=project.category_id,
        server_id=project.server_id,
        domain_id=project.domain_id,
        database_id=project.database_id,
        environment=project.environment,
        main_url=project.main_url,
        frontend_url=project.frontend_url,
        backend_url=project.backend_url,
        tech_stack=project.tech_stack or [],
        status=project.status,
        notes=project.notes,
        created_at=project.created_at,
        updated_at=project.updated_at,
        category_name=project.category.name if project.category else None,
        server_name=project.server.name if project.server else None,
        domain_name=project.domain.domain_name if project.domain else None,
        database_name=project.database.name if project.database else None,
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    projects = db.query(Project).order_by(Project.name).all()
    return [project_to_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    log_audit(db, user, "create", "project", str(project.id), project.name)
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    log_audit(db, user, "update", "project", str(project.id), project.name)
    return project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    log_audit(db, user, "delete", "project", str(project.id), project.name)
    db.delete(project)
    db.commit()
