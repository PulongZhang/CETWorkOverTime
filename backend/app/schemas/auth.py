from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class SessionResponse(BaseModel):
    authenticated: bool
