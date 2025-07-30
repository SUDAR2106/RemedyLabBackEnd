# remedylabs/backend/models/patient_doctor_mapping.py

import uuid
from datetime import datetime
from typing import Optional, Dict, Any,List

from database.db_utils import DBManager


class PatientDoctorMapping:
    def __init__(self, mapping_id=None, patient_id=None, doctor_id=None, assigned_date=None, is_active=1):
        self.mapping_id = mapping_id if mapping_id else str(uuid.uuid4())
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.assigned_date = assigned_date if assigned_date else datetime.now().isoformat()
        self.is_active = is_active # 1 for active, 0 for inactive/past assignments

    def save(self) -> bool:
        try:
            """Saves a new mapping or updates an existing one. Handles UNIQUE constraint for active mappings."""
            db_manager = DBManager()
            
            # Before inserting a new active mapping, ensure no active mapping already exists for this pair
            if self.is_active == 1:
                # Deactivate any existing active mapping for this patient-doctor pair
                deactivate_query = """
                    UPDATE patient_doctor_mapping
                    SET is_active = 0
                    WHERE patient_id = ? AND doctor_id = ? AND is_active = 1
                """
                db_manager.execute_query(deactivate_query, (self.patient_id, self.doctor_id))
            
            # Check if this specific mapping already exists
            existing_mapping = db_manager.fetch_one("SELECT mapping_id FROM patient_doctor_mapping WHERE mapping_id = ?", (self.mapping_id,))
            
            if existing_mapping:
                query = """
                    UPDATE patient_doctor_mapping
                    SET patient_id = ?, doctor_id = ?, assigned_date = ?, is_active = ?
                    WHERE mapping_id = ?
                """
                params = (self.patient_id, self.doctor_id, self.assigned_date, self.is_active, self.mapping_id)
            else:
                query = """
                    INSERT INTO patient_doctor_mapping (mapping_id, patient_id, doctor_id, assigned_date, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """
                params = (self.mapping_id, self.patient_id, self.doctor_id, self.assigned_date, self.is_active)
            
            print(f"Executing query: {query}")
            print(f"With params: {params}")
            result = db_manager.execute_query(query, params)
            print(f"Query execution result: {result}")
            return result
        except Exception as e:
            print(f"❌ Exception in PatientDoctorMapping.save(): {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def create(patient_id: str, doctor_id: str, is_active: bool = True) -> bool:
        """
        Create a new patient-doctor mapping safely (only one active mapping at a time).
        """
        existing = PatientDoctorMapping.find_active_mapping(patient_id, doctor_id)
        if existing:
            print("ℹ️ Patient is already assigned to this doctor.")
            return False

        mapping = PatientDoctorMapping(
            patient_id=patient_id,
            doctor_id=doctor_id,
            is_active=1 if is_active else 0
        )
        return mapping.save()

    @staticmethod
    def find_active_mapping(patient_id: str, doctor_id: str):
        """Finds an active mapping for a given patient-doctor pair."""
        db_manager = DBManager()
        mapping_data = db_manager.fetch_one("SELECT * FROM patient_doctor_mapping WHERE patient_id = ? AND doctor_id = ? AND is_active = 1", (patient_id, doctor_id))
        if mapping_data:
            return PatientDoctorMapping(**mapping_data)
        return None
    
    @staticmethod
    def find_patients_for_doctor(doctor_id: str, active_only: bool = True):
        """Finds all patients assigned to a specific doctor."""
        db_manager = DBManager()
        query = "SELECT * FROM patient_doctor_mapping WHERE doctor_id = ?"
        params = [doctor_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY assigned_date DESC"
        
        mappings_data = db_manager.fetch_all(query, params)
        if mappings_data:
            return [PatientDoctorMapping(**data) for data in mappings_data]
        return []

    @staticmethod
    def find_doctors_for_patient(patient_id: str, active_only: bool = True):
        """Finds all doctors assigned to a specific patient."""
        db_manager = DBManager()
        query = "SELECT * FROM patient_doctor_mapping WHERE patient_id = ?"
        params = [patient_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY assigned_date DESC"

        mappings_data = db_manager.fetch_all(query, params)
        if mappings_data:
            return [PatientDoctorMapping(**data) for data in mappings_data]
        return []

    def to_dict(self):
        return {
            "mapping_id": self.mapping_id,
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "assigned_date": self.assigned_date,
            "is_active": self.is_active
        }