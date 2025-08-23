#remedylab/backend/api/routes/signup.py

# Enhanced signup.py route
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from api.schemas.signup import SignUpRequest, SignUpSuccessResponse
from models.user_model import User, Patient, Doctor
from database.db_utils import DBManager
import bcrypt
import logging
from pydantic import ValidationError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", response_model=SignUpSuccessResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(request: SignUpRequest):
    """
    Registers a new user (either patient or doctor) and their associated profile.
    """
    
    logger.info("=== SIGNUP ENDPOINT CALLED ===")
     # COMPREHENSIVE REQUEST DEBUGGING
    logger.info("=== RAW REQUEST DEBUGGING ===")
    logger.info(f"Request object type: {type(request)}")
    logger.info(f"Request dict: {request.model_dump()}")
    logger.info(f"Request JSON: {request.model_dump_json(indent=2)}")
    
    logger.info("=== USER TYPE & DATA ===")
    logger.info(f"User type: '{request.user_type}'")
    logger.info(f"User data: {request.user_data}")
    logger.info(f"Patient details: {request.patient_details}")
    logger.info(f"Doctor details: {request.doctor_details}")
    
    if request.doctor_details:
        logger.info("=== DOCTOR DETAILS BREAKDOWN ===")
        logger.info(f"Medical license: '{request.doctor_details.medical_license_number}'")
        logger.info(f"Specialization: '{request.doctor_details.specialization}'")
        logger.info(f"Contact number: '{request.doctor_details.contact_number}'")
        logger.info(f"Hospital affiliation: '{request.doctor_details.hospital_affiliation}'")
        
        # Check for None vs empty string
        logger.info(f"Contact number is None: {request.doctor_details.contact_number is None}")
        logger.info(f"Contact number is empty string: {request.doctor_details.contact_number == ''}")
        logger.info(f"Contact number length: {len(request.doctor_details.contact_number or '')}")
        logger.info(f"Contact number type: {type(request.doctor_details.contact_number)}")
    
    try:
        # Log the incoming request for debugging
        logger.info(f"Received signup request for user_type: {request.user_type}")
        logger.info(f"Username: {request.user_data.username}")
        logger.info(f"Email: {request.user_data.email}")
        
        # Log doctor details if present
        if request.doctor_details:
            logger.info(f"Doctor specialization: {request.doctor_details.specialization}")
            logger.info(f"Doctor license: {request.doctor_details.medical_license_number}")
        
        # Additional validation for doctor
        if request.user_type == "doctor":
            logger.info("Validating doctor-specific fields...")
            if not request.doctor_details:
                logger.error("Doctor details missing")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Doctor details are required for doctor registration"
                )
            if not request.doctor_details.medical_license_number:
                logger.error("Medical license number missing")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Medical license number is required for doctors"
                )
            if not request.doctor_details.specialization:
                logger.error("Specialization missing")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Specialization is required for doctors"
                )

        logger.info("Checking username uniqueness...")
        # Check username uniqueness
        if User.get_by_username(request.user_data.username): 
            logger.warning(f"Username already exists: {request.user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken. Please choose a different one."
            )

        logger.info("Checking email uniqueness...")
        # Check email uniqueness
        if User.get_by_email(request.user_data.email):
            logger.warning(f"Email already exists: {request.user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered. Please use a different one or login."
            )

        # Check medical license uniqueness for doctors
        if (request.user_type == "doctor" and 
            request.doctor_details and 
            request.doctor_details.medical_license_number):
            logger.info("Checking medical license uniqueness...")
            db_manager = DBManager()
            if db_manager.fetch_one("SELECT 1 FROM doctors WHERE medical_license_number = ?", 
                                (request.doctor_details.medical_license_number,)):
                logger.warning(f"Medical license already exists: {request.doctor_details.medical_license_number}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Medical License ID already exists. Please use a different one."
                )

        logger.info("Hashing password...")
        # Hash password
        hashed_password = bcrypt.hashpw(
            request.user_data.password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')

        logger.info("Creating user...")
        # Create user
        user = User.create(
            username=request.user_data.username,
            password_hash=hashed_password,
            user_type=request.user_type,
            email=request.user_data.email,
            first_name=request.user_data.first_name,
            last_name=request.user_data.last_name
        )

        if not user:
            logger.error("Failed to create user in database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account. Please try again."
            )

        logger.info(f"User created successfully with ID: {user.user_id}")

        # Update patient profile with additional details
        if request.user_type == "patient" and request.patient_details:
            logger.info("Updating patient profile...")
            patient_profile = Patient.get_by_patient_id(user.user_id)
            if patient_profile:
                success = patient_profile.update_patient_info(
                    date_of_birth=request.patient_details.date_of_birth,
                    gender=request.patient_details.gender,
                    contact_number=request.patient_details.contact_number,
                    address=request.patient_details.address
                )
                if not success:
                    logger.warning(f"Failed to update patient details for user {user.user_id}")

        # Update doctor profile with additional details
        elif request.user_type == "doctor" and request.doctor_details:
            logger.info("Updating doctor profile...")
            doctor_profile = Doctor.get_by_doctor_id(user.user_id)
            if doctor_profile:
                logger.info(f"Found doctor profile: {doctor_profile.to_dict()}")
                
                # Log what we're about to update
                logger.info("=== VALUES BEING PASSED TO UPDATE ===")
                logger.info(f"medical_license_number: '{request.doctor_details.medical_license_number}'")
                logger.info(f"specialization: '{request.doctor_details.specialization}'")
                logger.info(f"contact_number: '{request.doctor_details.contact_number}'")
                logger.info(f"hospital_affiliation: '{request.doctor_details.hospital_affiliation}'")

                success = doctor_profile.update_doctor_info(
                    medical_license_number=request.doctor_details.medical_license_number,
                    specialization=request.doctor_details.specialization,
                    contact_number=request.doctor_details.contact_number,
                    hospital_affiliation=request.doctor_details.hospital_affiliation
                )
                logger.info(f"Doctor profile update success: {success}")

                if success:
                    # Verify the update by fetching the record again
                    updated_doctor = Doctor.get_by_doctor_id(user.user_id)
                    if updated_doctor:
                        logger.info("=== VERIFICATION OF UPDATED DOCTOR RECORD ===")
                        logger.info(f"Updated doctor record: {updated_doctor.to_dict()}")
                        logger.info(f"Contact number in DB after update: '{updated_doctor.contact_number}'")
                else:
                    logger.error(f"Failed to update doctor details for user {user.user_id}")
            else:
                logger.error(f"Doctor profile not found for user {user.user_id}")


        logger.info("Preparing response...")
        response_data = SignUpSuccessResponse(
            message="Account created successfully! Please log in.",
            user_id=user.user_id,
            username=user.username,
            user_type=user.user_type
        )
        
        logger.info(f"Returning success response: {response_data.model_dump()}")
        return response_data

    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        raise he
    except ValidationError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(ve)}"
        )
    except ValueError as ve:
        logger.error(f"Value error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. An unexpected error occurred."
        )