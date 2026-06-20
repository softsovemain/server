from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Project, Server, User, UserRole, UserServerAccess


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def get_accessible_server_ids(db: Session, user: User) -> set[UUID] | None:
    """None means unrestricted access (admin). Empty set means no servers assigned."""
    if is_admin(user):
        return None
    rows = db.query(UserServerAccess.server_id).filter(UserServerAccess.user_id == user.id).all()
    return {row[0] for row in rows}


def filter_servers_query(query: Query, server_ids: set[UUID] | None) -> Query:
    if server_ids is None:
        return query
    if not server_ids:
        return query.filter(False)
    return query.filter(Server.id.in_(server_ids))


def filter_projects_query(query: Query, server_ids: set[UUID] | None) -> Query:
    if server_ids is None:
        return query
    if not server_ids:
        return query.filter(False)
    return query.filter(
        or_(
            Project.frontend_server_id.in_(server_ids),
            Project.backend_server_id.in_(server_ids),
        )
    )


def project_is_visible(project: Project, server_ids: set[UUID] | None) -> bool:
    if server_ids is None:
        return True
    if not server_ids:
        return False
    if project.frontend_server_id and project.frontend_server_id in server_ids:
        return True
    if project.backend_server_id and project.backend_server_id in server_ids:
        return True
    return False


def require_server_access(db: Session, user: User, server_id: UUID | None) -> None:
    if server_id is None:
        return
    server_ids = get_accessible_server_ids(db, user)
    if server_ids is None:
        return
    if server_id not in server_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this server")


def get_project_or_403(db: Session, user: User, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project_is_visible(project, get_accessible_server_ids(db, user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this project")
    return project


def get_server_or_403(db: Session, user: User, server_id: UUID) -> Server:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    require_server_access(db, user, server_id)
    return server


def validate_project_server_links(
    db: Session,
    user: User,
    frontend_server_id: UUID | None,
    backend_server_id: UUID | None,
) -> None:
    server_ids = get_accessible_server_ids(db, user)
    if server_ids is None:
        return
    if not frontend_server_id and not backend_server_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link at least one assigned server to this project",
        )
    if frontend_server_id and frontend_server_id not in server_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to frontend server")
    if backend_server_id and backend_server_id not in server_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to backend server")


def sync_user_server_access(db: Session, user: User, server_ids: list[UUID]) -> None:
    db.query(UserServerAccess).filter(UserServerAccess.user_id == user.id).delete()
    if is_admin(user):
        return
    for server_id in server_ids:
        if not db.query(Server).filter(Server.id == server_id).first():
            raise HTTPException(status_code=400, detail=f"Server not found: {server_id}")
        db.add(UserServerAccess(user_id=user.id, server_id=server_id))


def get_user_server_ids_list(db: Session, user: User) -> list[UUID]:
    server_ids = get_accessible_server_ids(db, user)
    if server_ids is None:
        return []
    return sorted(server_ids)
