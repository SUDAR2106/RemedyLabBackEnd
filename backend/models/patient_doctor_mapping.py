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
    def find_patients_for_doctor(doctor_id: str, skip: int = 0, limit: int = 100) -> list:
        """
        Find all patients assigned to a specific doctor with pagination support.
        
        Args:
            doctor_id (str): The doctor's ID
            skip (int): Number of records to skip for pagination
            limit (int): Maximum number of records to return
            
        Returns:
            list: List of patient records assigned to the doctor
        """
        db_manager = DBManager()
        query = """
            SELECT p.*, pdm.assigned_date
            FROM patient_doctor_mapping pdm
            JOIN patients p ON pdm.patient_id = p.patient_id
            WHERE pdm.doctor_id = ? AND pdm.is_active = 1
            ORDER BY pdm.assigned_date DESC
            LIMIT ? OFFSET ?
        """
        results = db_manager.fetch_all(query, (doctor_id, limit, skip))
        return results if results else []

# Alternative method without pagination (if you need backward compatibility)
    @staticmethod
    def find_patients_for_doctor_simple(doctor_id: str) -> list:
        """
        Find all patients assigned to a specific doctor without pagination.
        
        Args:
            doctor_id (str): The doctor's ID
            
        Returns:
            list: List of patient records assigned to the doctor
        """
        db_manager = DBManager()
        query = """
            SELECT p.*, pdm.assigned_date, pdm.status as assignment_status
            FROM patient_doctor_mapping pdm
            JOIN patients p ON pdm.patient_id = p.patient_id
            WHERE pdm.doctor_id = ? AND pdm.is_active = 1
            ORDER BY pdm.assigned_date DESC
        """
        results = db_manager.fetch_all(query, (doctor_id,))
        return results if results else []

    # @staticmethod
    # def find_doctors_for_patient(patient_id: str, active_only: bool = True):
    #     """Finds all doctors assigned to a specific patient."""
    #     db_manager = DBManager()
    #     query = "SELECT * FROM patient_doctor_mapping WHERE patient_id = ?"
    #     params = [patient_id]
    #     if active_only:
    #         query += " AND is_active = 1"
    #     query += " ORDER BY assigned_date DESC"

    #     mappings_data = db_manager.fetch_all(query, params)
    #     if mappings_data:
    #         return [PatientDoctorMapping(**data) for data in mappings_data]
    #     return []
    
   

    @staticmethod
    def get_assigned_patients_by_doctor_id(doctor_id: int, skip: int = 0, limit: int = 100) -> List['PatientDoctorMapping']:
        """
        Get assigned patients for a doctor with pagination
        """
        try:
            db_manager = DBManager()
            query = """
                SELECT * FROM patient_doctor_mapping 
                WHERE doctor_id = ? AND is_active = 1
                ORDER BY assigned_date DESC
                LIMIT ? OFFSET ?
            """
            mappings_data = db_manager.fetch_all(query, (doctor_id, limit, skip))
            
            if mappings_data:
                return [PatientDoctorMapping(**data) for data in mappings_data]
            return []
        except Exception as e:
            print(f"❌ Error in get_assigned_patients_by_doctor_id: {e}")
            return []

    @staticmethod
    def count_by_doctor_id(doctor_id: int) -> int:
        """
        Count total assigned patients for a doctor
        """
        try:
            db_manager = DBManager()
            result = db_manager.fetch_one(
                "SELECT COUNT(*) as count FROM patient_doctor_mapping WHERE doctor_id = ? AND is_active = 1",
                (doctor_id,)
            )
            return result['count'] if result else 0
        except Exception as e:
            print(f"❌ Error in count_by_doctor_id: {e}")
            return 0

    @staticmethod
    def get_by_doctor_and_patient_id(doctor_id: int, patient_id: int) -> Optional['PatientDoctorMapping']:
        """
        Get active mapping for a specific doctor-patient pair
        """
        try:
            db_manager = DBManager()
            mapping_data = db_manager.fetch_one(
                "SELECT * FROM patient_doctor_mapping WHERE doctor_id = ? AND patient_id = ? AND is_active = 1",
                (doctor_id, patient_id)
            )
            if mapping_data:
                return PatientDoctorMapping(**mapping_data)
            return None
        except Exception as e:
            print(f"❌ Error in get_by_doctor_and_patient_id: {e}")
            return None

    @staticmethod
    def get_all_active_mappings() -> List['PatientDoctorMapping']:
        """
        Get all active patient-doctor mappings
        """
        try:
            db_manager = DBManager()
            mappings_data = db_manager.fetch_all(
                "SELECT * FROM patient_doctor_mapping WHERE is_active = 1 ORDER BY assigned_date DESC"
            )
            if mappings_data:
                return [PatientDoctorMapping(**data) for data in mappings_data]
            return []
        except Exception as e:
            print(f"❌ Error in get_all_active_mappings: {e}")
            return []

    @staticmethod
    def deactivate_mapping(doctor_id: int, patient_id: int) -> bool:
        """
        Deactivate a patient-doctor mapping
        """
        try:
            db_manager = DBManager()
            result = db_manager.execute_query(
                "UPDATE patient_doctor_mapping SET is_active = 0 WHERE doctor_id = ? AND patient_id = ? AND is_active = 1",
                (doctor_id, patient_id)
            )
            return result
        except Exception as e:
            print(f"❌ Error in deactivate_mapping: {e}")
            return False

    @staticmethod
    def reactivate_mapping(doctor_id: int, patient_id: int) -> bool:
        """
        Reactivate a patient-doctor mapping (deactivates any other active mappings for the patient first)
        """
        try:
            db_manager = DBManager()
            
            # First, deactivate any existing active mappings for this patient
            db_manager.execute_query(
                "UPDATE patient_doctor_mapping SET is_active = 0 WHERE patient_id = ? AND is_active = 1",
                (patient_id,)
            )
            
            # Then reactivate the specific mapping
            result = db_manager.execute_query(
                "UPDATE patient_doctor_mapping SET is_active = 1 WHERE doctor_id = ? AND patient_id = ?",
                (doctor_id, patient_id)
            )
            return result
        except Exception as e:
            print(f"❌ Error in reactivate_mapping: {e}")
            return False

    @staticmethod
    def get_patient_history(patient_id: int) -> List['PatientDoctorMapping']:
        """
        Get complete assignment history for a patient (including inactive mappings)
        """
        try:
            db_manager = DBManager()
            mappings_data = db_manager.fetch_all(
                "SELECT * FROM patient_doctor_mapping WHERE patient_id = ? ORDER BY assigned_date DESC",
                (patient_id,)
            )
            if mappings_data:
                return [PatientDoctorMapping(**data) for data in mappings_data]
            return []
        except Exception as e:
            print(f"❌ Error in get_patient_history: {e}")
            return []

    @staticmethod
    def get_doctor_history(doctor_id: int) -> List['PatientDoctorMapping']:
        """
        Get complete assignment history for a doctor (including inactive mappings)
        """
        try:
            db_manager = DBManager()
            mappings_data = db_manager.fetch_all(
                "SELECT * FROM patient_doctor_mapping WHERE doctor_id = ? ORDER BY assigned_date DESC",
                (doctor_id,)
            )
            if mappings_data:
                return [PatientDoctorMapping(**data) for data in mappings_data]
            return []
        except Exception as e:
            print(f"❌ Error in get_doctor_history: {e}")
            return []

    @staticmethod
    def bulk_assign_patients(doctor_id: int, patient_ids: List[int]) -> Dict[str, Any]:
        """
        Bulk assign multiple patients to a doctor
        """
        try:
            db_manager = DBManager()
            success_count = 0
            failed_assignments = []
            
            for patient_id in patient_ids:
                try:
                    # Check if mapping already exists
                    existing = PatientDoctorMapping.get_by_doctor_and_patient_id(doctor_id, patient_id)
                    if existing:
                        continue
                    
                    # Create new mapping
                    mapping = PatientDoctorMapping(
                        patient_id=patient_id,
                        doctor_id=doctor_id,
                        is_active=1
                    )
                    if mapping.save():
                        success_count += 1
                    else:
                        failed_assignments.append(patient_id)
                        
                except Exception as e:
                    print(f"❌ Failed to assign patient {patient_id}: {e}")
                    failed_assignments.append(patient_id)
            
            return {
                "success_count": success_count,
                "total_requested": len(patient_ids),
                "failed_assignments": failed_assignments,
                "success": len(failed_assignments) == 0
            }
            
        except Exception as e:
            print(f"❌ Error in bulk_assign_patients: {e}")
            return {
                "success_count": 0,
                "total_requested": len(patient_ids),
                "failed_assignments": patient_ids,
                "success": False,
                "error": str(e)
            }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert mapping instance to dictionary
        """
        return {
            "mapping_id": self.mapping_id,
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "assigned_date": self.assigned_date.isoformat() if isinstance(self.assigned_date, datetime) else self.assigned_date,
            "is_active": self.is_active
        }

    def __repr__(self) -> str:
        """
        String representation of the mapping
        """
        return f"PatientDoctorMapping(mapping_id={self.mapping_id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, is_active={self.is_active})"

    def __eq__(self, other) -> bool:
        """
        Equality comparison
        """
        if not isinstance(other, PatientDoctorMapping):
            return False
        return self.mapping_id == other.mapping_id

    def __hash__(self) -> int:
        """
        Hash function for using in sets/dicts
        """
        return hash(self.mapping_id)