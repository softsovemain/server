import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return _get_fernet().decrypt(value.encode()).decode()
