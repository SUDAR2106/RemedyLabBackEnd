#remedylab/backend/api/schemas/signup.py

#Pydantic models for the request and response bodies.
# This file defines the schemas for user registration in the API.
# It includes models for user details, patient and doctor specifics, and the overall sign-up request structure.
# api/schemas/signup.py
from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional, Literal
from models.user_model import UserCreate, PatientCreate, DoctorCreate

class SignUpRequest(BaseModel):
    user_type: Literal["patient", "doctor"]
    user_data: UserCreate
    patient_details: Optional[PatientCreate] = None
    doctor_details: Optional[DoctorCreate] = None
    
    @model_validator(mode="after")
    def validate_user_type_details(self) -> 'SignUpRequest':
        if self.user_type == "patient":
            # Patient details are optional
            if self.doctor_details is not None:
                raise ValueError("Doctor details should not be provided for patient registration")
                
        elif self.user_type == "doctor":
            # Doctor must have doctor_details with required fields
            if not self.doctor_details:
                raise ValueError("Doctor details are required for doctor registration")
            if not self.doctor_details.medical_license_number:
                raise ValueError("Medical license number is required for doctors")
            if not self.doctor_details.specialization:
                raise ValueError("Specialization is required for doctors")
            if self.patient_details is not None:
                raise ValueError("Patient details should not be provided for doctor registration")
        return self

class SignUpSuccessResponse(BaseModel):
    message: str
    user_id: str
    username: str
    user_type: str