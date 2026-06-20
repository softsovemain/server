import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.strip() if settings.ENCRYPTION_KEY else ""
    if key:
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError):
            pass
    derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        return _get_fernet().encrypt(value.encode()).decode()
    except Exception as exc:
        raise ValueError("Could not encrypt credential. Check ENCRYPTION_KEY or leave it empty.") from exc


def decrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except Exception:
        return None
