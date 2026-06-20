from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Category, Project, Server, User
from app.schemas import DashboardStats, ExpiringItem
from app.services.permissions import filter_projects_query, filter_servers_query, get_accessible_server_ids

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _expiring_servers(servers: list[Server], today: date, horizon: date) -> list[ExpiringItem]:
    result = []
    for server in servers:
        if server.expiry_date and today <= server.expiry_date <= horizon:
            result.append(
                ExpiringItem(
                    id=server.id,
                    name=server.name,
                    type="server",
                    expiry_date=server.expiry_date,
                    days_remaining=(server.expiry_date - today).days,
                )
            )
    return sorted(result, key=lambda x: x.days_remaining)


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    horizon = today + timedelta(days=30)
    server_ids = get_accessible_server_ids(db, user)

    servers = filter_servers_query(
        db.query(Server).filter(Server.expiry_date.isnot(None)),
        server_ids,
    ).all()

    projects_query = filter_projects_query(db.query(Project), server_ids)
    domain_count = (
        projects_query.filter(Project.domain_name.isnot(None), Project.domain_name != "")
        .with_entities(Project.domain_name)
        .distinct()
        .count()
    )
    database_count = (
        filter_projects_query(db.query(Project), server_ids)
        .filter(Project.database_name.isnot(None), Project.database_name != "")
        .with_entities(Project.database_name)
        .distinct()
        .count()
    )

    return DashboardStats(
        total_categories=(
            filter_projects_query(db.query(Project.category_id), server_ids)
            .filter(Project.category_id.isnot(None))
            .distinct()
            .count()
        ),
        total_servers=filter_servers_query(db.query(Server), server_ids).count(),
        total_projects=filter_projects_query(db.query(Project), server_ids).count(),
        total_domains=domain_count,
        total_databases=database_count,
        expiring_servers=_expiring_servers(servers, today, horizon),
        expiring_domains=[],
    )
