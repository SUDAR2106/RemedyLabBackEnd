# remedylabs/backend/services/auto_allocator.py

import datetime
import json # To parse extracted_data_json if needed for report type inference
from typing import Optional, List # Added List
import sqlite3 # For database operations
# --- Imports for Models ---
from models.health_report_model import HealthReport # The DB interaction class for HealthReport
from models.user_model import Doctor # <--- UPDATED: Import Doctor from its new file

from models.patient_doctor_mapping import PatientDoctorMapping # New mapping model
from models.report_specialist_mapping import ReportSpecialistMapping # New mapping model
# Assuming DBManager is used for database operations
from database.db_utils import DBManager

def get_report_type_from_extracted_data(extracted_data_json: str) -> Optional[str]:
   
    """
    Attempts to derive a structured report type from the extracted data JSON.
    This is a simplified example; a real-world scenario might involve more complex NLP.
    """
    if not extracted_data_json:
        return None
    try:
        data = json.loads(extracted_data_json)
        metrics = data.get('metrics', {})
        # Simple heuristic: if 'Total Cholesterol' is present, it's likely a lipid profile
        if 'Total Cholesterol' in metrics or 'LDL' in metrics:
            return "Lipid Profile" # Match case with your seeded mappings
        if 'TSH' in metrics or 'T3' in metrics:
            return "Thyroid Function Test" # Match case
        # Add more heuristics based on your common report types and extracted metrics
        # For now, default to a generic type if specific metrics aren't found
        return "General Checkup" # Fallback if no specific type can be inferred
    except json.JSONDecodeError:
        print("Warning: Could not decode extracted_data_json for report type inference.")
        return None

def auto_assign_doctor(report_id: str, db: Optional[sqlite3.Connection] = None) -> bool:
    """
    Automates the assignment of a doctor to a health report based on its type and doctor availability/specialization.
    This function should be called after a report's data has been extracted.
    It updates the HealthReport with the assigned doctor and creates a PatientDoctorMapping.
    Returns True if a doctor was successfully assigned or already assigned, False otherwise.
    """
    print(f"Auto-assigning doctor for report {report_id}...")
    try:
        report = HealthReport.get_by_report_id(report_id)

        if not report:
            print(f"Auto-allocation: Report with ID {report_id} not found.")
            return False

        if report.assigned_doctor_id:
            print(f"Auto-allocation: Report {report_id} already has an assigned doctor ({report.assigned_doctor_id}).")
            return True # Already assigned, nothing to do

        print(f"Auto-allocation: Starting for report '{report.file_name}' (ID: {report.report_id})")

        # 1. Determine required specialization based on report type
        specialization_required = None
        if report.report_type:
            # Check if a direct mapping exists for the provided report_type
            try:
                specialization_required = ReportSpecialistMapping.get_specialization_by_report_type(report.report_type)
                print(f"Auto-allocation: Found specialization mapping for '{report.report_type}': {specialization_required}")
            except Exception as e:
                print(f"Auto-allocation: Error getting specialization mapping: {e}")
                specialization_required = None

        if not specialization_required and report.extracted_data_json:
            # If no direct mapping for report.report_type, try to infer from extracted data
            inferred_report_type = get_report_type_from_extracted_data(report.extracted_data_json)
            if inferred_report_type:
                try:
                    specialization_required = ReportSpecialistMapping.get_specialization_by_report_type(inferred_report_type)
                    print(f"Auto-allocation: Found specialization mapping for inferred type '{inferred_report_type}': {specialization_required}")
                except Exception as e:
                    print(f"Auto-allocation: Error getting inferred specialization mapping: {e}")
                    specialization_required = None

        if not specialization_required:
            # Fallback to a default if no specific specialization can be determined
            print(f"Auto-allocation: No specific specialization found for report type '{report.report_type}'. Defaulting to 'General Physician'.")
            specialization_required = "General Physician" # Ensure a fallback

        print(f"Auto-allocation: Required specialization: {specialization_required}")

        # 2. Find an available doctor with the required specialization
        assigned_doctor = None
        try:
            # assigned_doctor = Doctor.get_available_doctors_by_specialization(specialization_required)
            # Note: This method name suggests it returns a single doctor, not a list
            # If it returns a list, use [0] to get the first one
            available_doctors = Doctor.get_available_doctors_by_specialization(specialization_required)
            if available_doctors:
                # If it returns a list, take the first one
                if isinstance(available_doctors, list):
                    assigned_doctor = available_doctors[0]
                else:
                    # If it returns a single doctor object
                    assigned_doctor = available_doctors
                print(f"Auto-allocation: Found available doctor with required specialization: {assigned_doctor.doctor_id}")
        except Exception as e:
            print(f"Auto-allocation: Error finding doctor by specialization: {e}")
            assigned_doctor = None

        if not assigned_doctor:
            print(f"Auto-allocation: No available doctor found for specialization: {specialization_required}. Checking for any available doctor.")
            # Fallback: if no specialist, try any available doctor
            try:
                available_doctors = Doctor.get_all_available_doctors()
                # if available_doctors:
                if available_doctors and len(available_doctors) > 0:
                    assigned_doctor = available_doctors[0] # Pick the first one
                    print(f"Auto-allocation: Found available doctor: {assigned_doctor.doctor_id}")
                else:
                    print(f"Auto-allocation: No suitable doctor found. Report {report_id} remains unassigned.")
                    report.processing_status = 'pending_manual_assignment' # Update status
                    if not report.save():
                        print(f"Auto-allocation: Failed to update report status to pending_manual_assignment.")
                    return False
            except Exception as e:
                print(f"Auto-allocation: Error finding any available doctor: {e}")
                return False

        print(f"Auto-allocation: Assigned doctor: {assigned_doctor.doctor_id} ({getattr(assigned_doctor, 'specialization', 'Unknown')})")

        # 3. Update the health report with the assigned doctor
        try:
            report.assigned_doctor_id = assigned_doctor.doctor_id
            report.processing_status = 'doctor_assigned' # Update status
            if not report.save():
                print(f"Auto-allocation: Failed to save assigned doctor for report {report_id}.")
                return False
            print(f"Auto-allocation: Successfully updated report with assigned doctor.")
        except Exception as e:
            print(f"Auto-allocation: Error updating report with assigned doctor: {e}")
            return False

        # 4. Create a PatientDoctorMapping entry
        try:
            mapping_created = PatientDoctorMapping.create(report.patient_id, assigned_doctor.doctor_id, True)
            if mapping_created:
                print(f"Auto-allocation: Created patient-doctor mapping successfully.")
            else:
                print(f"Auto-allocation: Patient-doctor mapping may already exist or creation failed.")
        except Exception as e:
            print(f"Auto-allocation: Error creating patient-doctor mapping: {e}")
            # Continue, as this is not critical for report processing
            
        # 5. Update the doctor's last assignment date
        try:
            if hasattr(assigned_doctor, 'update_last_assignment_date'):
                if assigned_doctor.update_last_assignment_date():
                    print(f"Auto-allocation: Updated last assignment date for doctor {assigned_doctor.doctor_id}.")
                else:
                    print(f"Auto-allocation: Failed to update last assignment date for doctor {assigned_doctor.doctor_id}.")
            else:
                print(f"Auto-allocation: Doctor model doesn't have update_last_assignment_date method.")
        except Exception as e:
            print(f"Auto-allocation: Error updating doctor's last assignment date: {e}")
            # Continue, as this is not critical

        print(f"Auto-allocation: Successfully assigned doctor {assigned_doctor.doctor_id} to report {report_id}.")
        return True
        
    except Exception as e:
        print(f"Auto-allocation: Unexpected error occurred while assigning doctor to report {report_id}: {str(e)}")
        import traceback
        traceback.print_exc()  # This will help debug the issue
        return False
        # 6. Update the recommendation if it exists (assuming AI runs before this, or after)
        # This part would typically happen AFTER AI recommendation generation,
        # and the recommendation would be created by the AI service, then updated here.
        # For now, let's assume if a recommendation exists, we update its doctor_id.
        # from models.recommendation import Recommendation # Local import to avoid circular dependency if needed
        # recommendation = Recommendation.get_by_report_id(report_id)
        # if recommendation:
        #     recommendation.doctor_id = assigned_doctor.doctor_id
        #     recommendation.status = 'pending_doctor_review'
        #     recommendation.save()


    #     print(f"Auto-allocation: Successfully assigned doctor {assigned_doctor.doctor_id} to report {report_id}.")
    #     return True
    # except Exception as e:
    #     print(f"Auto-allocation: Error while assigning doctor for report {report_id}: {e}")
    #     return False
# Example of how you might populate report_specialist_mapping (run once or from admin interface)
# This function is called from database/init_db.py
def populate_default_specialist_mappings():
    # from models.report_specialist_mapping import ReportSpecialistMapping
    mappings = {
        "Blood Test": "General Physician",
        "X-Ray": "Radiologist",
        "MRI Scan": "Radiologist",
        "Cardiology Report": "Cardiologist",
        "Neurology Report": "Neurologist",
        "General Checkup": "General Physician",
        "Diabetes Report": "Endocrinologist",
        "Liver Function Test": "Hepatologist",
        "Kidney Function Test": "Nephrologist",
        "Lipid Profile": "General Physician", # Corrected case from 'lipid_profile'
        "Thyroid Function Test": "Endocrinologist", # Corrected case from 'thyroid_function_test'
        "Eye Test": "Ophthalmologist", # Corrected case from 'eye_test'
        "Hearing Test": "ENT Specialist", # Corrected case from 'hearing_test'
        "Others Test": "General Physician",  # Fallback for unclassified tests, corrected case
        "Urine Test": "Nephrologist", # Corrected case
        "Stool Test": "Gastroenterologist", # Corrected case
    }
    for report_type, specialization in mappings.items():
        try:
            existing_specialization = ReportSpecialistMapping.get_specialization_by_report_type(report_type)
            if not existing_specialization:
                result = ReportSpecialistMapping.create(report_type, specialization)
                if result:
                    print(f"Added mapping: {report_type} -> {specialization}")
                else:
                    print(f"Failed to add mapping: {report_type} -> {specialization}")
            else:
                print(f"Mapping already exists: {report_type} -> {existing_specialization}")
        except Exception as e:
            print(f"Error processing mapping {report_type} -> {specialization}: {e}")