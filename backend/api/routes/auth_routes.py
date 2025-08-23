#remedylab/backend/api/routes/auth_routes.py

from fastapi import APIRouter, HTTPException, status , Depends
from datetime import datetime , timedelta,timezone # Import datetime for updating updated_at
import bcrypt # Import bcrypt for password verification
from utils.jwt_handler import create_jwt_token
from utils.auth_dependencies import get_current_user, CurrentUser
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_DELTA_SECONDS # Import your JWT configuration

from api.schemas.auth_schemas import LoginRequest, LoginSuccessResponse , UserProfileResponse # Import your schemas
from models.user_model import User # Import your User model

router = APIRouter()

@router.post("/login", response_model=LoginSuccessResponse, summary="User login")
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    
    # Validate input
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter both username and password."
        )

    # Get user from database
    user = User.get_by_username(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    # Verify password
    try:
        if not bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error occurred."
        )

    # Create JWT token payload
    token_data = {
        "sub": user.username,
        "user_id": user.user_id,
        "user_type": user.user_type,
    }
    
    # Generate JWT token
    access_token = create_jwt_token(token_data)
    
    # Update last login timestamp (if you have this method)
    # user.update_last_login()

    return LoginSuccessResponse(
        message="Login successful",
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        user_type=user.user_type,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email
    )

@router.get("/me", response_model=UserProfileResponse, summary="Get current user profile")
async def get_my_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        user_type=current_user.user_type,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email
    )

@router.post("/logout", summary="User logout")
async def logout(current_user: CurrentUser = Depends(get_current_user)):
    """Logout current user"""
    # With JWT, logout is mainly handled client-side by removing the token
    # You could implement token blacklisting here if needed
    return {"message": "Logout successful"}