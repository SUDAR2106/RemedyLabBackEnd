#remedylabs\backend\utils\jwt_handler.py

# utils/jwt_handler.py
import jwt
from datetime import datetime, timedelta,timezone
from fastapi import HTTPException, status
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_DELTA_SECONDS

def create_jwt_token(data: dict) -> str:
    """Create a JWT token with the provided data"""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    payload["iat"] = datetime.now(timezone.utc)  # Issued at time
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_jwt_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
