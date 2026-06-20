from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Domain, User, UserRole
from app.schemas import DomainCreate, DomainResponse, DomainUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainResponse])
def list_domains(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Domain).order_by(Domain.domain_name).all()


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def create_domain(
    payload: DomainCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    domain = Domain(**payload.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    log_audit(db, user, "create", "domain", str(domain.id), domain.domain_name)
    return domain


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.patch("/{domain_id}", response_model=DomainResponse)
def update_domain(
    domain_id: UUID,
    payload: DomainUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(domain, key, value)
    db.commit()
    db.refresh(domain)
    log_audit(db, user, "update", "domain", str(domain.id), domain.domain_name)
    return domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(
    domain_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.devops)),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    log_audit(db, user, "delete", "domain", str(domain.id), domain.domain_name)
    db.delete(domain)
    db.commit()
