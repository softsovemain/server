from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Category, Project, Server, User
from app.schemas import DashboardStats, ExpiringItem

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
def get_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()
    horizon = today + timedelta(days=30)

    servers = db.query(Server).filter(Server.expiry_date.isnot(None)).all()
    domain_count = (
        db.query(Project.domain_name)
        .filter(Project.domain_name.isnot(None), Project.domain_name != "")
        .distinct()
        .count()
    )

    database_count = (
        db.query(Project.database_name)
        .filter(Project.database_name.isnot(None), Project.database_name != "")
        .distinct()
        .count()
    )

    return DashboardStats(
        total_categories=db.query(Category).count(),
        total_servers=db.query(Server).count(),
        total_projects=db.query(Project).count(),
        total_domains=domain_count,
        total_databases=database_count,
        expiring_servers=_expiring_servers(servers, today, horizon),
        expiring_domains=[],
    )
