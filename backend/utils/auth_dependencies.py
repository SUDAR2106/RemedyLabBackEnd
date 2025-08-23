#remedylabs\backend\utils\auth_dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from models.user_model import User
from utils.jwt_handler import decode_jwt_token

# Security scheme for extracting Bearer tokens
security = HTTPBearer()

class CurrentUser:
    """Current user context"""
    def __init__(self, user_id: str, username: str, user_type: str, 
                 first_name: str, last_name: str, email: Optional[str] = None):
        self.user_id = user_id
        self.username = username
        self.user_type = user_type
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
    
    def is_admin(self) -> bool:
        return self.user_type == "admin"
    
    def is_doctor(self) -> bool:
        return self.user_type == "doctor"
    
    def is_patient(self) -> bool:
        return self.user_type == "patient"

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT token
    """
    try:
        # Decode the JWT token
        payload = decode_jwt_token(credentials.credentials)
        
        # Extract user info from token
        username = payload.get("sub")
        user_id = payload.get("user_id")
        user_type = payload.get("user_type")
        
        if not username or not user_id or not user_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Optionally verify user still exists in database
        user = User.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Return current user context
        return CurrentUser(
            user_id=user.user_id,
            username=user.username,
            user_type=user.user_type,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Role-based dependencies
async def get_current_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency for admin-only routes"""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_doctor(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency for doctor-only routes"""
    if not current_user.is_doctor():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required"
        )
    return current_user

async def get_current_patient(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency for patient-only routes"""
    if not current_user.is_patient():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required"
        )
    return current_user

async def get_current_doctor_or_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency for routes accessible by doctors or admins"""
    if not (current_user.is_doctor() or current_user.is_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor or Admin access required"
        )
    return current_user