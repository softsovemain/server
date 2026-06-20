from uuid import UUID

from app.core.deps import can_view_secrets
from app.models import Database, Server, User
from app.schemas import DatabaseResponse, ServerResponse
from app.services.encryption import decrypt_value, encrypt_value


def server_to_response(server: Server, user: User) -> ServerResponse:
    show_secrets = can_view_secrets(user)
    has_creds = bool(server.username_encrypted or server.password_encrypted or server.ssh_key_encrypted)
    return ServerResponse(
        id=server.id,
        name=server.name,
        category_id=server.category_id,
        provider=server.provider,
        server_type=server.server_type,
        server_os=server.server_os,
        server_ip=server.server_ip,
        panel_url=server.panel_url,
        expiry_date=server.expiry_date,
        notes=server.notes,
        status=server.status,
        has_credentials=has_creds,
        username=decrypt_value(server.username_encrypted) if show_secrets else None,
        password=decrypt_value(server.password_encrypted) if show_secrets else None,
        ssh_key=decrypt_value(server.ssh_key_encrypted) if show_secrets else None,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


def apply_server_credentials(server: Server, username: str | None, password: str | None, ssh_key: str | None) -> None:
    if username is not None:
        server.username_encrypted = encrypt_value(username) if username else None
    if password is not None:
        server.password_encrypted = encrypt_value(password) if password else None
    if ssh_key is not None:
        server.ssh_key_encrypted = encrypt_value(ssh_key) if ssh_key else None


def database_to_response(db_record: Database, user: User) -> DatabaseResponse:
    show_secrets = can_view_secrets(user)
    has_conn = bool(db_record.connection_string_encrypted)
    return DatabaseResponse(
        id=db_record.id,
        name=db_record.name,
        server_id=db_record.server_id,
        db_type=db_record.db_type,
        notes=db_record.notes,
        has_connection_string=has_conn,
        connection_string=decrypt_value(db_record.connection_string_encrypted) if show_secrets else None,
        created_at=db_record.created_at,
        updated_at=db_record.updated_at,
    )
