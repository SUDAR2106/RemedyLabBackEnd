# remedylabs/backend/models/doctor_model.py

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from database.db_utils import DBManager # Import DBManager
# If DoctorRead needs to include UserRead details, you might import it like:
# from .user_model import UserRead

# --- Pydantic Schemas for Doctor ---
class DoctorBase(BaseModel):
    """
    Base Pydantic model for Doctor.
    doctor_id is a FK to user_id, so it's a string matching the user's UUID.
    """
    doctor_id: str = Field(..., example=str(uuid.uuid4())) # Matches user_id
    medical_license_number: Optional[str] = Field(None, max_length=50, example="LIC12345")
    specialization: Optional[str] = Field(None, max_length=100, example="Cardiology")
    contact_number: Optional[str] = Field(None, max_length=20, example="+919988776655")
    hospital_affiliation: Optional[str] = Field(None, max_length=100, example="City Hospital")
    is_available: bool = Field(True, example=True) # Boolean for 1/0 in SQLite
    last_assignment_date: Optional[datetime] = Field(None, example=datetime.now())

class DoctorCreate(DoctorBase):
    """
    Pydantic model for creating a new Doctor.
    Note: doctor_id is expected to be the user_id from the associated User.
    """
    pass # No additional fields beyond DoctorBase for direct doctor creation

class DoctorRead(DoctorBase):
    """
    Pydantic model for reading Doctor data.
    """
    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

# --- Database Interaction Class for Doctor ---
class Doctor:
    """
    Database model for Doctor, encapsulating CRUD operations.
    """
    def __init__(self, doctor_id: str, medical_license_number: Optional[str] = None,
                 specialization: Optional[str] = None, contact_number: Optional[str] = None,
                 hospital_affiliation: Optional[str] = None, is_available: int = 1, # Stored as int (0/1) in DB
                 last_assignment_date: Optional[str] = None): # Stored as string in DB
        self.doctor_id = doctor_id
        self.medical_license_number = medical_license_number
        self.specialization = specialization
        self.contact_number = contact_number
        self.hospital_affiliation = hospital_affiliation
        self.is_available = bool(is_available) # Convert 0/1 to bool for Python object
        self.last_assignment_date = last_assignment_date # Store as string

    def save(self) -> bool:
        """
        Saves or updates the doctor record in the database.
        Uses ON CONFLICT to handle both insert and update if record exists.
        """
        query = """
            INSERT INTO doctors (doctor_id, medical_license_number, specialization, contact_number, hospital_affiliation, is_available, last_assignment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doctor_id) DO UPDATE SET
                medical_license_number = EXCLUDED.medical_license_number,
                specialization = EXCLUDED.specialization,
                contact_number = EXCLUDED.contact_number,
                hospital_affiliation = EXCLUDED.hospital_affiliation,
                is_available = EXCLUDED.is_available,
                last_assignment_date = EXCLUDED.last_assignment_date;
        """
        params = (
            self.doctor_id,
            self.medical_license_number,
            self.specialization,
            self.contact_number,
            self.hospital_affiliation,
            int(self.is_available), # Convert bool to int (0/1) for SQLite
            self.last_assignment_date if isinstance(self.last_assignment_date, str) else (self.last_assignment_date.isoformat() if self.last_assignment_date else None)
        )
        return self.db_manager.execute_query(query, params) > 0

    @classmethod
    def get_by_id(cls, doctor_id: str) -> Optional['Doctor']:
        """
        Retrieves a doctor by their doctor_id.
        """
        query = "SELECT * FROM doctors WHERE doctor_id = ?"
        doctor_data = DBManager().fetch_one(query, (doctor_id,))
        if doctor_data:
            # Convert is_available back to boolean
            doctor_data['is_available'] = bool(doctor_data['is_available'])
            # Convert last_assignment_date string back to datetime object if it exists
            if 'last_assignment_date' in doctor_data and doctor_data['last_assignment_date']:
                try:
                    doctor_data['last_assignment_date'] = datetime.fromisoformat(doctor_data['last_assignment_date'])
                except ValueError:
                    pass # Keep as string if conversion fails
            return cls(**doctor_data)
        return None

    @classmethod
    def create(cls, doctor_id: str, medical_license_number: Optional[str] = None,
               specialization: Optional[str] = None, contact_number: Optional[str] = None,
               hospital_affiliation: Optional[str] = None, is_available: bool = True,
               last_assignment_date: Optional[datetime] = None) -> Optional['Doctor']:
        """
        Creates a new doctor record in the database.
        """
        new_doctor = cls(
            doctor_id, medical_license_number, specialization, contact_number,
            hospital_affiliation, is_available,
            last_assignment_date.isoformat() if last_assignment_date else None # Store as string
        )
        if new_doctor.save():
            return new_doctor
        return None

    @classmethod
    def find_available_doctor_by_specialization(cls, specialization: str) -> Optional['Doctor']:
        """
        Finds an available doctor with the specified specialization, prioritizing those with
        the oldest last_assignment_date to distribute load.
        """
        query = """
            SELECT * FROM doctors
            WHERE specialization = ? AND is_available = 1
            ORDER BY last_assignment_date ASC, RANDOM()
            LIMIT 1;
        """
        doctor_data = DBManager().fetch_one(query, (specialization,))
        if doctor_data:
            doctor_data['is_available'] = bool(doctor_data['is_available'])
            if 'last_assignment_date' in doctor_data and doctor_data['last_assignment_date']:
                try:
                    doctor_data['last_assignment_date'] = datetime.fromisoformat(doctor_data['last_assignment_date'])
                except ValueError:
                    pass
            return cls(**doctor_data)
        return None

    def update_last_assignment_date(self) -> bool:
        """
        Updates the last_assignment_date of the doctor to the current time.
        """
        self.last_assignment_date = datetime.now().isoformat() # Update internal object and convert to string
        query = "UPDATE doctors SET last_assignment_date = ? WHERE doctor_id = ?"
        params = (self.last_assignment_date, self.doctor_id)
        return self.db_manager.execute_query(query, params) > 0

    @classmethod
    def get_all(cls) -> List['Doctor']:
        """
        Retrieves all doctor records.
        """
        query = "SELECT * FROM doctors"
        doctors_data = DBManager().fetch_all(query)
        if doctors_data:
            results = []
            for data in doctors_data:
                data['is_available'] = bool(data['is_available'])
                if 'last_assignment_date' in data and data['last_assignment_date']:
                    try:
                        data['last_assignment_date'] = datetime.fromisoformat(data['last_assignment_date'])
                    except ValueError:
                        pass
                results.append(cls(**data))
            return results
        return []

    def to_read_model(self) -> DoctorRead:
        """Converts the database model instance to a Pydantic read model."""
        data = self.__dict__.copy()
        # Ensure datetime object is converted to string for Pydantic if it's a datetime object
        if isinstance(data.get('last_assignment_date'), datetime):
            data['last_assignment_date'] = data['last_assignment_date'].isoformat()
        return DoctorRead(**data)