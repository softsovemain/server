from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserResponse
from app.services.permissions import get_user_server_ids_list, is_admin


def user_to_response(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        server_ids=get_user_server_ids_list(db, user),
        has_full_access=is_admin(user),
    )
