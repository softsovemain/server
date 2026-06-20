from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Project, User
from app.services.permissions import filter_projects_query, get_accessible_server_ids
from pydantic import BaseModel

router = APIRouter(prefix="/domains", tags=["domains"])


class ProjectDomainItem(BaseModel):
    domain_name: str
    project_id: str
    project_name: str


@router.get("", response_model=list[ProjectDomainItem])
def list_domains_from_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server_ids = get_accessible_server_ids(db, user)
    query = filter_projects_query(
        db.query(Project).filter(Project.domain_name.isnot(None), Project.domain_name != ""),
        server_ids,
    )
    projects = query.order_by(Project.domain_name).all()
    return [
        ProjectDomainItem(
            domain_name=p.domain_name,
            project_id=str(p.id),
            project_name=p.name,
        )
        for p in projects
    ]
