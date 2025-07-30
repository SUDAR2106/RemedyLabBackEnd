#remedylabs/backend/database/init_db.py

# RemedyLab/database/init_db.py
import sqlite3
from datetime import datetime
import os
import sys
import uuid # For generating UUIDs for dummy data

# --- START: Temporary sys.path adjustment for config import ---
# Ensure this path adjustment correctly points to the root of your backend project
# For D:\TheRemedyLab\RemedyLab\backend
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
# --- END: Temporary sys.path adjustment ---

# Import the global connection from db.py
from database.db import get_global_db_connection
from database.db_utils import DBManager # Ensure this is correctly importing DBManager

# Import the populate function from auto_allocator.py
from services.auto_allocator import populate_default_specialist_mappings # <--- UPDATED IMPORT


# --- Helper function to create tables ---
def _create_tables(conn: sqlite3.Connection):
    """
    Creates all necessary database tables if they don't already exist.
    """
    cursor = conn.cursor()

    # Create 'users' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL, -- e.g., 'patient', 'doctor', 'admin'
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("Table 'users' checked/created.")

    # Create 'patients' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            date_of_birth TEXT,
            gender TEXT,
            contact_number TEXT,
            address TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
    """)
    print("Table 'patients' checked/created.")

    # Create 'doctors' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            medical_license_number TEXT UNIQUE,
            specialization TEXT,
            contact_number TEXT,
            hospital_affiliation TEXT,
            is_available INTEGER DEFAULT 1, -- New: 1 for available, 0 for not available
            last_assignment_date TEXT,    -- New: To help with workload balancing
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
    """)
    print("Table 'doctors' checked/created.")

    # Create 'health_reports' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_reports (
            report_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            uploaded_by TEXT NOT NULL, -- user_id of the uploader (patient or admin)
            report_type TEXT,           -- e.g., 'Blood Test', 'X-Ray', 'Cardiology Report'
            file_type TEXT NOT NULL,    -- e.g., 'pdf', 'jpeg', 'png'
            upload_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,    -- Local path where the file is stored
            extracted_data_json TEXT,   -- JSON string of extracted patient info and metrics
            assigned_doctor_id TEXT,    -- Nullable, assigned later
            processing_status TEXT NOT NULL DEFAULT 'uploaded', -- e.g., 'uploaded', 'extracted', 'doctor_assigned', 'pending_ai_analysis', 'pending_doctor_review', 'approved_by_doctor'
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_doctor_id) REFERENCES doctors (doctor_id) ON DELETE SET NULL
        );
    """)
    print("Table 'health_reports' checked/created.")

    # Create 'recommendations' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            recommendation_id TEXT PRIMARY KEY,
            report_id TEXT UNIQUE NOT NULL, -- One-to-one with health_report
            patient_id TEXT NOT NULL,
            ai_generated_treatment TEXT,
            ai_generated_lifestyle TEXT,
            ai_generated_priority TEXT,
            doctor_id TEXT, -- NULL until reviewed
            doctor_notes TEXT,
            status TEXT NOT NULL, -- e.g., 'AI_generated', 'approved_by_doctor', 'modified_by_doctor', 'rejected_by_doctor'
            reviewed_date TEXT,
            approved_treatment TEXT,
            approved_lifestyle TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES health_reports (report_id) ON DELETE CASCADE,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id) ON DELETE SET NULL
        );
    """)
    print("Table 'recommendations' checked/created.")

    # Create 'patient_doctor_mapping' table (for explicit assignments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_doctor_mapping (
            mapping_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            assigned_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER NOT NULL DEFAULT 1, -- 1 for active, 0 for inactive
            UNIQUE (patient_id, doctor_id), -- Ensure a patient-doctor pair is unique
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id) ON DELETE CASCADE
        );
    """)
    print("Table 'patient_doctor_mapping' checked/created.")

    # Create table for Report Type to Specialist Mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_specialist_mapping (
            report_type TEXT PRIMARY KEY,
            specialization_required TEXT NOT NULL
        );
    """)
    print("Table 'report_specialist_mapping' checked/created.")

    conn.commit()
    print("All necessary tables checked/created.")


# --- Function to populate default specialist mappings ---
def populate_default_specialist_mappings():
    """
    Populates default report-specialist mappings if they don't already exist.
    This uses DBManager for consistency.
    """
    db_manager = DBManager()
    mappings = [
        ("General Health Checkup", "General Medicine"),
        ("Cardiology Report", "Cardiologist"),
        ("Pathology Lab Report", "Pathologist"),
        ("Dermatology Consultation", "Dermatologist"),
        ("Neurology Scan", "Neurologist"),
        ("Blood Test", "General Physician"),
        ("Urine Test", "General Physician"),
        ("X-Ray Report", "Radiologist"),
        ("MRI Scan", "Radiologist"),
        ("Diabetes Report", "Endocrinologist"),
        ("Liver Function Test", "Hepatologist"),
        ("Kidney Function Test", "Nephrologist"),
        ("Lipid Profile", "General Physician"),
        ("Thyroid Function Test", "Endocrinologist"),
        ("Eye Test", "Ophthalmologist"),
        ("Hearing Test", "ENT Specialist"),
        ("Others Test", "General Physician"), # Fallback for unclassified tests
        ("Stool Test", "Gastroenterologist")
    ]

    print("Checking and populating default specialist mappings...")
    for report_type, specialization in mappings:
        try:
            existing_mapping = db_manager.fetch_one(
                "SELECT report_type FROM report_specialist_mapping WHERE report_type = ?",
                (report_type,)
            )
            if not existing_mapping:
                db_manager.execute_query(
                    "INSERT INTO report_specialist_mapping (report_type, specialization_required) VALUES (?, ?)",
                    (report_type, specialization)
                )
                print(f"  Added mapping: '{report_type}' -> '{specialization}'")
            # else: # Uncomment if you want to see messages for existing mappings
            #     print(f"  Mapping already exists: '{report_type}'")
        except Exception as e:
            print(f"Error adding mapping '{report_type}': {e}")

    # Seed a dummy doctor user if none exists, to ensure auto-allocation has a target
    dummy_doctor_user_id = "doctor_uuid_for_initial_seed"
    # Consider using a more robust way to check if a doctor exists beyond just user_id,
    # e.g., check username or email in case the UUID changes.
    existing_doctor_user = db_manager.fetch_one(
        "SELECT user_id FROM users WHERE username = ?", ("dr.seed",)
    )
    if not existing_doctor_user:
        print("Seeding dummy doctor user and profile for initial setup...")
        # A simple password hash for a dummy user (in a real app, use bcrypt)
        dummy_password_hash = "dummy_hashed_password" # In production, use bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            # Create the user entry for the dummy doctor
            db_manager.execute_query(
                "INSERT INTO users (user_id, username, password_hash, user_type, email, first_name, last_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (dummy_doctor_user_id, "dr.seed", dummy_password_hash, "doctor", "dr.seed@example.com", "Doctor", "Seed")
            )
            # Create the doctor profile entry linked to the user_id
            db_manager.execute_query(
                "INSERT INTO doctors (doctor_id, user_id, medical_license_number, specialization, contact_number, hospital_affiliation, is_available, last_assignment_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (dummy_doctor_user_id, dummy_doctor_user_id, "ML-SEED-001", "General Medicine", "1112223333", "Seed Hospital", 1, datetime.now().isoformat())
            )
            print(f"  Dummy doctor '{dummy_doctor_user_id}' seeded successfully.")
        except sqlite3.IntegrityError as e:
            print(f"  Dummy doctor seeding skipped (already exists or integrity error): {e}")
        except Exception as e:
            print(f"  Error seeding dummy doctor: {e}")


# --- Main initialization function to be called on app startup ---
def initialize_database_and_data():
    """
    Orchestrates the full database initialization:
    1. Establishes global connection.
    2. Creates all tables.
    3. Populates default data (e.g., specialist mappings, dummy doctors).
    """
    print("Starting full database and data initialization...")
    conn = get_global_db_connection()
    _create_tables(conn) # Call the local _create_tables function
    populate_default_specialist_mappings()
    print("Full database and data initialization complete.")

# This part is for standalone execution of init_db.py (e.g., python init_db.py)
# It's not used when run via FastAPI's lifespan in main.py
if __name__ == "__main__":
    # Ensure DATABASE_FILE is accessible for standalone run
    # You might need to adjust sys.path or pass DATABASE_FILE explicitly if config is not directly importable
    from database.db import init_db_connection, close_db_connection # Import for standalone use

    print("Running init_db.py in standalone mode...")
    try:
        init_db_connection() # Initialize connection
        initialize_database_and_data() # Run the full initialization sequence
    finally:
        close_db_connection() # Ensure connection is closed
    print("Standalone database initialization completed.")