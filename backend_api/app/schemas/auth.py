from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


def _validate_password_strength(password: str) -> str:
    if not re.search(r"[a-zA-Z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("Password must contain at least one special character")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    return password


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str = Field(min_length=3, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserPayload(BaseModel):
    id: int
    username: str
    email: str = ""
    plan: str = "free"


class AuthResponse(BaseModel):
    ok: bool = True
    user: UserPayload
    message: str


class MessageResponse(BaseModel):
    ok: bool = True
    message: str
