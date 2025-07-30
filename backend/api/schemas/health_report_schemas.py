# remedylab/backend/api/schemas/health_report_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class HealthReportUploadRequest(BaseModel):
    """
    Schema for health report upload request (used with Form data)
    """
    patient_id: str = Field(..., description="ID of the patient")
    uploaded_by: str = Field(..., description="ID of the user uploading the report")
    report_type: Optional[str] = Field(None, description="Type of the health report")

class HealthReportBase(BaseModel):
    """
    Base schema for health reports with common fields
    """
    patient_id: str = Field(..., example=str(uuid.uuid4()))
    uploaded_by: str = Field(..., example=str(uuid.uuid4()))
    report_type: Optional[str] = Field(None, max_length=100, example="Blood Test")
    file_type: Optional[str] = Field(None, max_length=20, example=".pdf")
    file_name: Optional[str] = Field(None, max_length=255, example="blood_test_report.pdf")
    assigned_doctor_id: Optional[str] = Field(None, example=str(uuid.uuid4()))
    processing_status: str = Field("uploaded", example="uploaded")

class HealthReportCreate(HealthReportBase):
    """
    Schema for creating a new health report
    """
    pass

class HealthReportResponse(HealthReportBase):
    """
    Schema for health report responses
    """
    report_id: str = Field(..., example=str(uuid.uuid4()))
    upload_date: datetime = Field(..., example=datetime.now())
    file_path: str = Field(..., example="/app/uploaded_files/unique_file_name.pdf")
    extracted_data_json: Optional[str] = Field(None, example='{"symptoms": "fever", "diagnosis": "flu"}')

    class Config:
        from_attributes = True

class HealthReportUpdate(BaseModel):
    """
    Schema for updating health report fields
    """
    report_type: Optional[str] = Field(None, max_length=100)
    assigned_doctor_id: Optional[str] = Field(None)
    processing_status: Optional[str] = Field(None)
    extracted_data_json: Optional[str] = Field(None)

class HealthReportStatusUpdate(BaseModel):
    """
    Schema for updating just the processing status
    """
    processing_status: str = Field(..., example="processing")

class HealthReportListResponse(BaseModel):
    """
    Schema for listing multiple health reports
    """
    reports: List[HealthReportResponse]
    total_count: int
    page: int = 1
    page_size: int = 10

class ExtractedDataResponse(BaseModel):
    """
    Schema for extracted data from health reports
    """
    report_id: str
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_status: str = "pending"
    extraction_date: Optional[datetime] = None

class FileUploadResponse(BaseModel):
    """
    Schema for file upload confirmation
    """
    message: str
    report_id: str
    file_name: str
    upload_status: str = "success"

class ErrorResponse(BaseModel):
    """
    Schema for error responses
    """
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)