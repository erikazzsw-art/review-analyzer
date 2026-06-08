from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)


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
