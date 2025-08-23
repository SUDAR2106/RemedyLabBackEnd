# remedylab/backend/api/routes/health_report_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, List
import uuid
import shutil
import os
from datetime import datetime
import json
from models.health_report_model import HealthReportCreate, HealthReportRead
from api.schemas.health_report_schemas import (
    HealthReportResponse, HealthReportListResponse, HealthReportStatusUpdate,
    FileUploadResponse, ErrorResponse, PatientDashboardResponse, UserProfileResponse
)
from database.db import get_db
import sqlite3
from fastapi.staticfiles import StaticFiles
from services.document_parser import DocumentParserService
from utils.auth_dependencies import (
    get_current_user, get_current_patient, get_current_doctor, 
    get_current_doctor_or_admin, CurrentUser
)

# Define the directory where uploaded files will be stored
UPLOAD_DIRECTORY = "uploaded_files"

# Create the router instance with prefix and tags
router = APIRouter()

# ==============================================================================
# Patient Dashboard and Profile Routes
# ==============================================================================
# Mount static files for uploaded reports
router.mount("/files", StaticFiles(directory=UPLOAD_DIRECTORY), name="uploaded_files")

@router.get("/patient/dashboard", response_model=PatientDashboardResponse)
async def patient_dashboard(current_user: CurrentUser = Depends(get_current_patient)):
    """
    Patient dashboard - only accessible by patients
    Shows recent reports and health summary
    """
    return PatientDashboardResponse(
        message=f"Welcome to patient dashboard, {current_user.first_name}!",
        user_type=current_user.user_type,
        user_id=current_user.user_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name
    )

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get user profile for any authenticated user
    """
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        user_type=current_user.user_type,
        full_name=f"{current_user.first_name} {current_user.last_name}",
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email
    )

# ==============================================================================
# Health Report CRUD Operations
# ==============================================================================

@router.post("/upload", response_model=HealthReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_health_report(
    report_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_patient),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Upload a health report file - only accessible by patients
    The patient_id and uploaded_by are automatically set from the current user
    """
    cursor = db.cursor()

    # Automatically use current user's ID as both patient_id and uploaded_by
    patient_id = current_user.user_id
    uploaded_by = current_user.user_id

    # 1. Save uploaded file
    new_report_id = str(uuid.uuid4())
    current_time = datetime.now()

    # Ensure the upload directory exists
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    # Sanitize filename to prevent directory traversal attacks
    file_name = os.path.basename(file.filename)

    # Validate file type (optional - add your allowed extensions)
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
    file_extension = os.path.splitext(file_name)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Append UUID to filename to ensure uniqueness and prevent overwrites
    unique_file_name = f"{uuid.uuid4()}_{file_name}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_file_name)

    # Save the file to the server
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved to {file_path} by user {current_user.username}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Could not save file: {e}"
        )

    # 2. Insert initial report metadata
    try:
        cursor.execute(
            """
            INSERT INTO health_reports (
                report_id, patient_id, uploaded_by, report_type, file_type,
                upload_date, file_name, file_path, extracted_data_json, processing_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_report_id,
                patient_id,
                uploaded_by,
                report_type or file_extension,
                file_extension,
                current_time,
                file.filename,
                file_path,
                None,  # No extracted data yet
                "uploaded"
            )
        )
        db.commit()
        print(f"Report {new_report_id} uploaded by patient {current_user.username}")
    except sqlite3.IntegrityError as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Database integrity error: {e}"
        )
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {e}"
        )

    # 3. Run document parsing and pipeline
    try:
        result = DocumentParserService.process_report_pipeline(new_report_id, db)
        if not result.get("success"):
            print(f"Pipeline processing failed for report {new_report_id}: {result.get('error')}")
    except Exception as e:
        print(f"Pipeline error for report {new_report_id}: {e}")

    # 4. Fetch updated report from DB to return
    cursor.execute("SELECT * FROM health_reports WHERE report_id = ?", (new_report_id,))
    created_report = cursor.fetchone()
    if not created_report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Could not retrieve saved report."
        )

    return HealthReportResponse(**created_report)

@router.get("/my-reports", response_model=List[HealthReportResponse])
async def get_my_reports(
    current_user: CurrentUser = Depends(get_current_patient),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all health reports for the current patient
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM health_reports WHERE patient_id = ? ORDER BY upload_date DESC", (current_user.user_id,))
    reports = cursor.fetchall()
    
    return [HealthReportResponse(**report) for report in reports]

@router.get("/reports/{patient_id}", response_model=List[HealthReportResponse])
async def get_patient_reports(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_doctor_or_admin),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all health reports for a specific patient - accessible by doctors and admins
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM health_reports WHERE patient_id = ? ORDER BY upload_date DESC", (patient_id,))
    reports = cursor.fetchall()
    
    return [HealthReportResponse(**report) for report in reports]

@router.get("/report/{report_id}/file")
async def get_report_file(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get the file path for a report to enable direct file access
    """
    cursor = db.cursor()
    cursor.execute("SELECT file_path, patient_id FROM health_reports WHERE report_id = ?", (report_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    file_path, report_patient_id = result
    
    # Check permissions
    if current_user.is_patient() and report_patient_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return the relative file path that can be accessed via static files
    import os
    filename = os.path.basename(file_path)
    return {"file_url": f"/api/health/files/{filename}"}

@router.get("/report/{report_id}", response_model=HealthReportResponse)
async def get_report_by_id(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get a specific health report by its ID
    Patients can only access their own reports, doctors/admins can access any
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM health_reports WHERE report_id = ?", (report_id,))
    report = cursor.fetchone()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Health report not found."
        )
    
    # Check access permissions
    report_dict = dict(report) if hasattr(report, 'keys') else report
    report_patient_id = report_dict.get('patient_id') if isinstance(report_dict, dict) else report[1]  # Assuming patient_id is second column
    
    # Patients can only access their own reports
    if current_user.is_patient() and report_patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own reports."
        )
    
    return HealthReportResponse(**report)

@router.put("/report/{report_id}/status", response_model=dict)
async def update_report_status(
    report_id: str,
    status_update: HealthReportStatusUpdate,
    current_user: CurrentUser = Depends(get_current_doctor_or_admin),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Update the processing status of a health report - accessible by doctors and admins
    """
    cursor = db.cursor()
    
    # Check if report exists
    cursor.execute("SELECT report_id FROM health_reports WHERE report_id = ?", (report_id,))
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Health report not found."
        )
    
    # Update status
    try:
        cursor.execute(
            "UPDATE health_reports SET processing_status = ? WHERE report_id = ?",
            (status_update.processing_status, report_id)
        )
        db.commit()
        print(f"Report {report_id} status updated to {status_update.processing_status} by {current_user.username}")
        return {
            "message": "Report status updated successfully", 
            "report_id": report_id, 
            "new_status": status_update.processing_status,
            "updated_by": current_user.username
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to update status: {e}"
        )

@router.delete("/report/{report_id}")
async def delete_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Delete a health report and its associated file
    Patients can only delete their own reports, doctors/admins can delete any
    """
    cursor = db.cursor()
    
    # Get report details before deletion
    cursor.execute("SELECT file_path, patient_id FROM health_reports WHERE report_id = ?", (report_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Health report not found."
        )
    
    file_path = result[0]
    report_patient_id = result[1]
    
    # Check access permissions
    if current_user.is_patient() and report_patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only delete your own reports."
        )
    
    try:
        # Delete from database
        cursor.execute("DELETE FROM health_reports WHERE report_id = ?", (report_id,))
        db.commit()
        
        # Delete physical file if it exists
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"Report {report_id} deleted by {current_user.username}")
        return {
            "message": "Report deleted successfully", 
            "report_id": report_id,
            "deleted_by": current_user.username
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to delete report: {e}"
        )

# ==============================================================================
# Statistics and Analytics (for doctors/admins)
# ==============================================================================

@router.get("/stats/patient/{patient_id}")
async def get_patient_report_stats(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_doctor_or_admin),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get statistics for a patient's reports - accessible by doctors and admins
    """
    cursor = db.cursor()
    
    # Get total reports count
    cursor.execute("SELECT COUNT(*) FROM health_reports WHERE patient_id = ?", (patient_id,))
    total_reports = cursor.fetchone()[0]
    
    # Get reports by status
    cursor.execute(
        """
        SELECT processing_status, COUNT(*) 
        FROM health_reports 
        WHERE patient_id = ? 
        GROUP BY processing_status
        """, 
        (patient_id,)
    )
    status_counts = dict(cursor.fetchall())
    
    # Get recent reports
    cursor.execute(
        "SELECT * FROM health_reports WHERE patient_id = ? ORDER BY upload_date DESC LIMIT 5", 
        (patient_id,)
    )
    recent_reports = [HealthReportResponse(**report) for report in cursor.fetchall()]
    
    return {
        "patient_id": patient_id,
        "total_reports": total_reports,
        "status_distribution": status_counts,
        "recent_reports": recent_reports,
        "requested_by": current_user.username
    }

@router.get("/my-stats")
async def get_my_report_stats(
    current_user: CurrentUser = Depends(get_current_patient),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get statistics for current patient's own reports
    """
    cursor = db.cursor()
    
    # Get total reports count
    cursor.execute("SELECT COUNT(*) FROM health_reports WHERE patient_id = ?", (current_user.user_id,))
    total_reports = cursor.fetchone()[0]
    
    # Get reports by status
    cursor.execute(
        """
        SELECT processing_status, COUNT(*) 
        FROM health_reports 
        WHERE patient_id = ? 
        GROUP BY processing_status
        """, 
        (current_user.user_id,)
    )
    status_counts = dict(cursor.fetchall())
    
    return {
        "patient_id": current_user.user_id,
        "patient_name": f"{current_user.first_name} {current_user.last_name}",
        "total_reports": total_reports,
        "status_distribution": status_counts
    }
