from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Project, Server, User
from app.schemas import SearchResult
from app.services.permissions import filter_projects_query, filter_servers_query, get_accessible_server_ids

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    term = f"%{q}%"
    results: list[SearchResult] = []
    server_ids = get_accessible_server_ids(db, user)

    server_query = filter_servers_query(
        db.query(Server).filter(
            or_(Server.name.ilike(term), Server.notes.ilike(term), Server.server_ip.ilike(term))
        ),
        server_ids,
    ).limit(10)
    for server in server_query:
        results.append(SearchResult(id=server.id, name=server.name, type="server", subtitle=server.server_type.value))

    project_query = filter_projects_query(
        db.query(Project).filter(
            or_(
                Project.name.ilike(term),
                Project.notes.ilike(term),
                Project.domain_name.ilike(term),
                Project.database_name.ilike(term),
            )
        ),
        server_ids,
    ).limit(10)
    for project in project_query:
        results.append(
            SearchResult(
                id=project.id,
                name=project.name,
                type="project",
                subtitle=project.domain_name or project.environment.value,
            )
        )

    return results[:20]
