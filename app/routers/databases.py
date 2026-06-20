from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Project, User
from app.services.permissions import filter_projects_query, get_accessible_server_ids

router = APIRouter(prefix="/databases", tags=["databases"])


class ProjectDatabaseItem(BaseModel):
    database_name: str
    project_id: str
    project_name: str


@router.get("", response_model=list[ProjectDatabaseItem])
def list_databases_from_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server_ids = get_accessible_server_ids(db, user)
    query = filter_projects_query(
        db.query(Project).filter(Project.database_name.isnot(None), Project.database_name != ""),
        server_ids,
    )
    projects = query.order_by(Project.database_name).all()
    return [
        ProjectDatabaseItem(
            database_name=p.database_name,
            project_id=str(p.id),
            project_name=p.name,
        )
        for p in projects
    ]
