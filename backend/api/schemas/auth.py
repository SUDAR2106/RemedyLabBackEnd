#remedylab/backend/api/schemas/auth.py

from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginSuccessResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user_id: str # Or int, depending on your user_id type
    username: str
    user_type: str # "patient" | "doctor" | "admin",
    first_name: str
    last_name: str
    email: Optional[str] = None # email: str | None = None