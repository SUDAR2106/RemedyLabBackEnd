# remedylabs/backend/models/user_model.py

import uuid
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr,model_validator, field_validator
import bcrypt

from database.db_utils import DBManager

# --- Pydantic Schemas (keep existing) ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    # user_type: str = Field(..., pattern="^(patient|doctor|admin)$")
    #You only need user_type at the top level in SignUpRequest.
    # So fix it by removing user_type from UserBase and UserCreate.

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords_match(self) -> 'UserCreate':
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserRead(UserBase):
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PatientCreate(BaseModel):
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None

    # @field_validator('gender')
    # @classmethod
    # def validate_gender(cls, v):
    #     if v is not None and v.strip():
    #         if v not in ['Male', 'Female', 'Other']:
    #             raise ValueError('Gender must be Male, Female, or Other')
    #     return v or None
    
    # @field_validator('contact_number')
    # @classmethod
    # def validate_contact_number(cls, v):
    #     if v is not None and v.strip():
    #         # Basic phone number validation
    #         cleaned = ''.join(filter(str.isdigit, v))
    #         if len(cleaned) < 10:
    #             raise ValueError('Contact number must be at least 10 digits')
    #     return v or None

class PatientRead(PatientCreate):
    patient_id: str
    user_id: str

    class Config:
        from_attributes = True

class DoctorCreate(BaseModel):
    medical_license_number: Optional[str] = None
    specialization: Optional[str] = None
    contact_number: Optional[str] = None
    hospital_affiliation: Optional[str] = None

class DoctorRead(DoctorCreate):
    doctor_id: str
    user_id: str
    is_available: bool
    last_assignment_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Database Interaction Classes ---
class User:
    def __init__(self, user_id: str, username: str, password_hash: str, user_type: str,
                 email: str, first_name: Optional[str] = None, last_name: Optional[str] = None,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.user_type = user_type
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.created_at = created_at if created_at else datetime.now().isoformat()
        self.updated_at = updated_at if updated_at else datetime.now().isoformat()

    @classmethod
    def create(cls, username: str, password_hash: str, user_type: str, email: str,
               first_name: Optional[str] = None, last_name: Optional[str] = None) -> Optional['User']:
        user_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        db_manager = DBManager()

        query = """
            INSERT INTO users (user_id, username, password_hash, user_type, email, first_name, last_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (user_id, username, password_hash, user_type, email, first_name, last_name, current_time, current_time)

        try:
            if db_manager.execute_query(query, params):
                if user_type == "patient":
                    # Create a corresponding entry in the patients table
                    db_manager.execute_query(
                        "INSERT INTO patients (patient_id, user_id) VALUES (?, ?)",
                        (user_id, user_id) # patient_id is the same as user_id for simplicity
                    )
                elif user_type == "doctor":
                    # When creating a doctor, also create their doctor profile
                    db_manager.execute_query(
                        "INSERT INTO doctors (doctor_id, user_id, is_available) VALUES (?, ?, ?)",
                        (user_id, user_id, 1) # Doctors are available by default (1 for True)
                    )
                return cls(user_id, username, password_hash, user_type, email, first_name, last_name, current_time, current_time)
            return None
        except sqlite3.IntegrityError as e:
            print(f"Error creating user (IntegrityError): {e}")
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None


    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        db_manager = DBManager()
        query = "SELECT * FROM users WHERE username = ?"
        result = db_manager.fetch_one(query, (username,))
        if result:
            return cls(**result)
        return None

    @classmethod
    def get_by_user_id(cls, user_id: str) -> Optional['User']:
        db_manager = DBManager()
        query = "SELECT * FROM users WHERE user_id = ?"
        result = db_manager.fetch_one(query, (user_id,))
        if result:
            return cls(**result)
        return None
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """Get user by email address"""
        db_manager = DBManager()
        query = "SELECT * FROM users WHERE email = ?"
        result = db_manager.fetch_one(query, (email,))
        if result:
            return cls(**result)
        return None

    @classmethod
    def get_all(cls) -> List['User']:
        """
        Retrieves all users from the database.
        """
        db_manager = DBManager()
        query = "SELECT * FROM users"
        results = db_manager.fetch_all(query)
        return [cls(**result) for result in results]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_type": self.user_type,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class Patient:
    def __init__(self, patient_id: str, user_id: str, date_of_birth: Optional[str] = None,
                 gender: Optional[str] = None, contact_number: Optional[str] = None,
                 address: Optional[str] = None):
        self.patient_id = patient_id
        self.user_id = user_id
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.contact_number = contact_number
        self.address = address

    @classmethod
    def get_by_patient_id(cls, patient_id: str) -> Optional['Patient']:
        db_manager = DBManager()
        query = "SELECT * FROM patients WHERE patient_id = ?"
        result = db_manager.fetch_one(query, (patient_id,))
        if result:
            return cls(**result)
        return None

    @classmethod
    def create(cls, user_id: str, date_of_birth: Optional[str] = None, gender: Optional[str] = None,
               contact_number: Optional[str] = None, address: Optional[str] = None) -> Optional['Patient']:
        """
        Creates a new patient entry. patient_id is linked to user_id.
        This is primarily called internally when a 'patient' user type is registered.
        """
        db_manager = DBManager()
        query = """
            INSERT INTO patients (patient_id, user_id, date_of_birth, gender, contact_number, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (user_id, user_id, date_of_birth, gender, contact_number, address)
        try:
            if db_manager.execute_query(query, params):
                return cls(user_id, user_id, date_of_birth, gender, contact_number, address)
            return None
        except sqlite3.IntegrityError as e:
            print(f"Error creating patient (IntegrityError): {e}")
            return None
        except Exception as e:
            print(f"Error creating patient: {e}")
            return None

    def update_patient_info(self, date_of_birth: Optional[str] = None, gender: Optional[str] = None,
                            contact_number: Optional[str] = None, address: Optional[str] = None) -> bool:
        db_manager = DBManager()
        update_fields = []
        params = []

        if date_of_birth is not None:
            update_fields.append("date_of_birth = ?")
            params.append(date_of_birth)
            self.date_of_birth = date_of_birth
        if gender is not None:
            update_fields.append("gender = ?")
            params.append(gender)
            self.gender = gender
        if contact_number is not None:
            update_fields.append("contact_number = ?")
            params.append(contact_number)
            self.contact_number = contact_number
        if address is not None:
            update_fields.append("address = ?")
            params.append(address)
            self.address = address

        if not update_fields:
            return True # Nothing to update - return True as success

        query = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
        params.append(self.patient_id)

        try:
            return db_manager.execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error updating patient info: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "user_id": self.user_id,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "contact_number": self.contact_number,
            "address": self.address
        }


class Doctor:
    def __init__(self, doctor_id: str, user_id: str, medical_license_number: Optional[str],
                 specialization: Optional[str], contact_number: Optional[str],
                 hospital_affiliation: Optional[str], is_available: int,
                 last_assignment_date: Optional[str]):
        self.doctor_id = doctor_id
        self.user_id = user_id
        self.medical_license_number = medical_license_number
        self.specialization = specialization
        self.contact_number = contact_number
        self.hospital_affiliation = hospital_affiliation
        self.is_available = bool(is_available) # Convert 0/1 to bool
        self.last_assignment_date = last_assignment_date # Store as ISO format string

    @classmethod  # FIXED: Added missing @classmethod decorator
    def create(cls, user_id: str, medical_license_number: Optional[str] = None, 
               specialization: Optional[str] = None, contact_number: Optional[str] = None,
               hospital_affiliation: Optional[str] = None, is_available: bool = True,
               last_assignment_date: Optional[str] = None) -> Optional['Doctor']:
        """
        Creates a new doctor entry. doctor_id is linked to user_id.
        """
        db_manager = DBManager()
        query = """
            INSERT INTO doctors (doctor_id, user_id, medical_license_number, specialization, 
                               contact_number, hospital_affiliation, is_available, last_assignment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (user_id, user_id, medical_license_number, specialization, 
                 contact_number, hospital_affiliation, int(is_available), last_assignment_date)
        try:
            if db_manager.execute_query(query, params):
                return cls(user_id, user_id, medical_license_number, specialization,
                          contact_number, hospital_affiliation, int(is_available), last_assignment_date)
            return None
        except sqlite3.IntegrityError as e:
            print(f"Error creating doctor (IntegrityError): {e}")
            return None
        except Exception as e:
            print(f"Error creating doctor: {e}")
            return None

    def update_doctor_info(self, medical_license_number: Optional[str] = None,
                           specialization: Optional[str] = None, contact_number: Optional[str] = None,
                           hospital_affiliation: Optional[str] = None) -> bool:
        db_manager = DBManager()
        update_fields = []
        params = []

        if medical_license_number is not None:
            update_fields.append("medical_license_number = ?")
            params.append(medical_license_number)
            self.medical_license_number = medical_license_number
        if specialization is not None:
            update_fields.append("specialization = ?")
            params.append(specialization)
            self.specialization = specialization
        if contact_number is not None:
            update_fields.append("contact_number = ?")
            params.append(contact_number)
            self.contact_number = contact_number
        if hospital_affiliation is not None:
            update_fields.append("hospital_affiliation = ?")
            params.append(hospital_affiliation)
            self.hospital_affiliation = hospital_affiliation

        if not update_fields:
            return True  # No fields to update

        query = f"UPDATE doctors SET {', '.join(update_fields)} WHERE doctor_id = ?"
        params.append(self.doctor_id)

        try:
            return db_manager.execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error updating doctor info: {e}")
            return False

    @classmethod
    def get_by_doctor_id(cls, doctor_id: str) -> Optional['Doctor']:
        db_manager = DBManager()
        query = "SELECT * FROM doctors WHERE doctor_id = ?"
        result = db_manager.fetch_one(query, (doctor_id,))
        if result:
            return cls(**result)
        return None

    @classmethod
    def get_available_doctors_by_specialization(cls, specialization: str) -> List['Doctor']:
        db_manager = DBManager()
        # Find doctors who are available (is_available = 1) and match specialization
        # Order by last_assignment_date to pick the one who was assigned longest ago (simple load balancing)
        query = """
            SELECT d.* FROM doctors d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.is_available = 1 AND d.specialization = ?
            ORDER BY d.last_assignment_date ASC
        """
        results = db_manager.fetch_all(query, (specialization,))
        return [cls(**result) for result in results]

    @classmethod
    def get_all_available_doctors(cls) -> List['Doctor']:
        db_manager = DBManager()
        query = """
            SELECT d.* FROM doctors d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.is_available = 1
            ORDER BY d.last_assignment_date ASC
        """
        results = db_manager.fetch_all(query)
        return [cls(**result) for result in results]


    def update_availability(self, is_available: bool) -> bool:
        db_manager = DBManager()
        query = "UPDATE doctors SET is_available = ? WHERE doctor_id = ?"
        return db_manager.execute_query(query, (int(is_available), self.doctor_id))

    def update_last_assignment_date(self) -> bool:
        self.last_assignment_date = datetime.now().isoformat()
        db_manager = DBManager()
        query = "UPDATE doctors SET last_assignment_date = ? WHERE doctor_id = ?"
        return db_manager.execute_query(query, (self.last_assignment_date, self.doctor_id))

    def update_specialization(self, specialization: str) -> bool:
        self.specialization = specialization
        db_manager = DBManager()
        query = "UPDATE doctors SET specialization = ? WHERE doctor_id = ?"
        return db_manager.execute_query(query, (specialization, self.doctor_id))
    
    # @field_validator('medical_license_number')
    # @classmethod
    # def validate_license_number(cls, v):
    #     # Convert empty string to None, but keep the original value if it has content
    #     return v.strip() if v and v.strip() else None
        
    # @field_validator('specialization')
    # @classmethod
    # def validate_specialization(cls, v):
    #     # Convert empty string to None, but keep the original value if it has content
    #     return v.strip() if v and v.strip() else None
        
    # @field_validator('contact_number')
    # @classmethod
    # def validate_contact_number(cls, v):
    #     if v is not None and v.strip():
    #         # Basic phone number validation
    #         cleaned = ''.join(filter(str.isdigit, v))
    #         if len(cleaned) < 10:
    #             raise ValueError('Contact number must be at least 10 digits')
    #     return v or None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doctor_id": self.doctor_id,
            "user_id": self.user_id,
            "medical_license_number": self.medical_license_number,
            "specialization": self.specialization,
            "contact_number": self.contact_number,
            "hospital_affiliation": self.hospital_affiliation,
            "is_available": self.is_available,
            "last_assignment_date": self.last_assignment_date
        }