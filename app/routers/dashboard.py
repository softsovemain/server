from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Category, Database, Domain, Project, Server, User
from app.schemas import DashboardStats, ExpiringItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _expiring_items(items: list, name_attr: str, type_label: str, today: date, horizon: date) -> list[ExpiringItem]:
    result = []
    for item in items:
        expiry = getattr(item, "expiry_date", None)
        if expiry and today <= expiry <= horizon:
            result.append(
                ExpiringItem(
                    id=item.id,
                    name=getattr(item, name_attr),
                    type=type_label,
                    expiry_date=expiry,
                    days_remaining=(expiry - today).days,
                )
            )
    return sorted(result, key=lambda x: x.days_remaining)


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()
    horizon = today + timedelta(days=30)

    servers = db.query(Server).filter(Server.expiry_date.isnot(None)).all()
    domains = db.query(Domain).filter(Domain.expiry_date.isnot(None)).all()

    return DashboardStats(
        total_categories=db.query(Category).count(),
        total_servers=db.query(Server).count(),
        total_projects=db.query(Project).count(),
        total_domains=db.query(Domain).count(),
        total_databases=db.query(Database).count(),
        expiring_servers=_expiring_items(servers, "name", "server", today, horizon),
        expiring_domains=_expiring_items(domains, "domain_name", "domain", today, horizon),
    )
