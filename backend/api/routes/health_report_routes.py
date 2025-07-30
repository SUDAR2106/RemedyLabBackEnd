# remedylab/backend/api/routes/health_report_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import uuid
import shutil
import os
from datetime import datetime
import json
from models.health_report_model import HealthReportCreate, HealthReportRead
from database.db import get_db
import sqlite3
from services.document_parser import DocumentParserService

# Define the directory where uploaded files will be stored
UPLOAD_DIRECTORY = "uploaded_files"

# Create the router instance
router = APIRouter()

@router.post("/upload", response_model=HealthReportRead, status_code=status.HTTP_201_CREATED)
async def upload_health_report(
    patient_id: str = Form(...),
    uploaded_by: str = Form(...),
    report_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Uploads a health report file and stores its metadata in the database.
    """
    cursor = db.cursor()

    # 1. Validate uploader
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uploaded_by,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploader (User) not found.")

    # 2. Save uploaded file
    new_report_id = str(uuid.uuid4())
    current_time = datetime.now()

    # Ensure the upload directory exists
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    # Sanitize filename to prevent directory traversal attacks
    file_name = os.path.basename(file.filename)

    # Append UUID to filename to ensure uniqueness and prevent overwrites
    unique_file_name = f"{uuid.uuid4()}_{file_name}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_file_name)
    file_extension = os.path.splitext(file_name)[1].lower()

    # Save the file to the server
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File saved to {file_path}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save file: {e}")

    # 3. Insert initial report metadata
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
    except sqlite3.IntegrityError as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

    # 4. Run document parsing and pipeline
    try:
        result = DocumentParserService.process_report_pipeline(new_report_id, db)
        if not result.get("success"):
            pass  # Optionally log or include result["error"]
    except Exception as e:
        print(f"Pipeline error: {e}")

    # 5. Fetch updated report from DB to return
    cursor.execute("SELECT * FROM health_reports WHERE report_id = ?", (new_report_id,))
    created_report = cursor.fetchone()
    if not created_report:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve saved report.")

    return HealthReportRead(**created_report)


@router.get("/reports/{patient_id}", response_model=list[HealthReportRead])
async def get_patient_reports(
    patient_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all health reports for a specific patient.
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM health_reports WHERE patient_id = ?", (patient_id,))
    reports = cursor.fetchall()
    
    if not reports:
        return []
    
    return [HealthReportRead(**report) for report in reports]


@router.get("/report/{report_id}", response_model=HealthReportRead)
async def get_report_by_id(
    report_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get a specific health report by its ID.
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM health_reports WHERE report_id = ?", (report_id,))
    report = cursor.fetchone()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found.")
    
    return HealthReportRead(**report)


@router.put("/report/{report_id}/status")
async def update_report_status(
    report_id: str,
    new_status: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Update the processing status of a health report.
    """
    cursor = db.cursor()
    
    # Check if report exists
    cursor.execute("SELECT report_id FROM health_reports WHERE report_id = ?", (report_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found.")
    
    # Update status
    try:
        cursor.execute(
            "UPDATE health_reports SET processing_status = ? WHERE report_id = ?",
            (new_status, report_id)
        )
        db.commit()
        return {"message": "Report status updated successfully", "report_id": report_id, "new_status": new_status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update status: {e}")


@router.delete("/report/{report_id}")
async def delete_report(
    report_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Delete a health report and its associated file.
    """
    cursor = db.cursor()
    
    # Get file path before deletion
    cursor.execute("SELECT file_path FROM health_reports WHERE report_id = ?", (report_id,))
    result = cursor.fetchone()
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found.")
    
    file_path = result[0] if isinstance(result, tuple) else result['file_path']
    
    try:
        # Delete from database
        cursor.execute("DELETE FROM health_reports WHERE report_id = ?", (report_id,))
        db.commit()
        
        # Delete physical file if it exists
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        return {"message": "Report deleted successfully", "report_id": report_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete report: {e}")