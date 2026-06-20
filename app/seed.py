from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import Category, CategoryType, User, UserRole


def run_seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.admin,
            )
            db.add(admin)

        defaults = [
            ("Client Projects", CategoryType.client, "#8b5cf6"),
            ("My Personal", CategoryType.personal, "#fafafa"),
            ("Company Project", CategoryType.company, "#a78bfa"),
        ]
        for name, cat_type, color in defaults:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(name=name, type=cat_type, color=color))

        db.commit()
    finally:
        db.close()
