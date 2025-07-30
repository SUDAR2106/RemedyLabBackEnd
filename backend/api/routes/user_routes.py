#remedylab/backend/api/routes/user_routes.py
# User Routes for FastAPI
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import bcrypt # For password hashing
import uuid # For generating user_ids
from datetime import datetime

# Import your Pydantic models AND the new User, Patient, Doctor DB models
from models.user_model import UserCreate, UserRead, User, PatientCreate, PatientRead, Patient, DoctorCreate, DoctorRead, Doctor
from database.db import get_db # Import the database context manager
import sqlite3

user_router = APIRouter()

# Helper function to hash passwords
def hash_password(password: str) -> str:
    # bcrypt generates a salt automatically and includes it in the hash
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return hashed_password

# Helper function to verify passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@user_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Registers a new user in the system and creates a corresponding patient/doctor profile if applicable.
    """
    # Check if username or email already exists using the User model's method
    if User.get_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    hashed_pwd = hash_password(user_data.password)

    # Create the user using the User model's create method
    # Remove user_id parameter since it's generated internally
    new_user_db_instance = User.create(
        username=user_data.username,
        password_hash=hashed_pwd,
        user_type=user_data.user_type,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    if not new_user_db_instance:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user due to a database error."
        )

    # Note: Patient and Doctor profiles are already created automatically 
    # in the User.create() method based on user_type

    return UserRead(**new_user_db_instance.to_dict())


@user_router.post("/login", response_model=UserRead)
async def login_user(username: str, password: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Authenticates a user and returns their details if successful.
    """
    user = User.get_by_username(username)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Return the user data, excluding the password hash
    return UserRead(**user.to_dict())

@user_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves a user's details by user_id.
    """
    user = User.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead(**user.to_dict())

@user_router.get("/", response_model=List[UserRead])
async def get_all_users(db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves all users in the system.
    """
    users = User.get_all()
    return [UserRead(**user.to_dict()) for user in users]

# --- NEW ENDPOINTS for creating/updating Patient and Doctor profiles ---

@user_router.post("/patients/{user_id}", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient_profile(user_id: str, patient_data: PatientCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Creates or updates a patient profile for an existing user.
    """
    user = User.get_by_user_id(user_id)
    if not user or user.user_type != "patient":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found or not a patient type.")

    existing_patient = Patient.get_by_patient_id(user_id)
    if existing_patient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient profile already exists for this user. Use PUT to update.")

    new_patient = Patient.create(
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        contact_number=patient_data.contact_number,
        address=patient_data.address
    )

    if not new_patient:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create patient profile.")

    return PatientRead(**new_patient.to_dict())

@user_router.get("/patients/{patient_id}", response_model=PatientRead)
async def get_patient_profile(patient_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves a patient's profile details.
    """
    patient = Patient.get_by_patient_id(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found.")
    return PatientRead(**patient.to_dict())

@user_router.post("/doctors/{user_id}", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
async def create_doctor_profile(user_id: str, doctor_data: DoctorCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Creates or updates a doctor profile for an existing user.
    """
    user = User.get_by_user_id(user_id)
    if not user or user.user_type != "doctor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found or not a doctor type.")

    existing_doctor = Doctor.get_by_doctor_id(user_id)
    if existing_doctor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile already exists for this user. Use PUT to update.")

    new_doctor = Doctor.create(
        user_id=user_id,
        medical_license_number=doctor_data.medical_license_number,
        specialization=doctor_data.specialization,
        contact_number=doctor_data.contact_number,
        hospital_affiliation=doctor_data.hospital_affiliation,
        is_available=True
    )

    if not new_doctor:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create doctor profile.")

    return DoctorRead(**new_doctor.to_dict())

@user_router.get("/doctors/{doctor_id}", response_model=DoctorRead)
async def get_doctor_profile(doctor_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves a doctor's profile details.
    """
    doctor = Doctor.get_by_doctor_id(doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found.")
    return DoctorRead(**doctor.to_dict())