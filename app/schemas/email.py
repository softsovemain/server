from typing import Annotated

from pydantic import BeforeValidator, Field


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or len(email) < 3:
        raise ValueError("Invalid email address")
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("Invalid email address")
    return email


# Allows internal domains like admin@opshub.local (Pydantic EmailStr blocks .local TLDs)
Email = Annotated[str, BeforeValidator(_normalize_email), Field(max_length=255)]
