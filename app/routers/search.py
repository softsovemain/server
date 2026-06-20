from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Project, Server, User
from app.schemas import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    term = f"%{q}%"
    results: list[SearchResult] = []

    for server in db.query(Server).filter(or_(Server.name.ilike(term), Server.notes.ilike(term), Server.server_ip.ilike(term))).limit(10):
        results.append(SearchResult(id=server.id, name=server.name, type="server", subtitle=server.server_type.value))

    for project in db.query(Project).filter(
        or_(Project.name.ilike(term), Project.notes.ilike(term), Project.domain_name.ilike(term))
    ).limit(10):
        results.append(
            SearchResult(
                id=project.id,
                name=project.name,
                type="project",
                subtitle=project.domain_name or project.environment.value,
            )
        )

    return results[:20]
