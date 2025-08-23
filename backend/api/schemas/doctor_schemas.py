# remedylab/backend/api/schemas/doctor_schemas.py
# This file contains Pydantic schemas for doctor-related data structures
# including doctor profiles, patient information, recommendations, and dashboard overviews.
# It is used to validate and serialize data in the API.

from pydantic import BaseModel, validator,Field
from typing import Optional, List
from datetime import datetime

# Base schemas for doctor-related data
class DoctorBase(BaseModel):
    specialization: Optional[str] = None
    medical_license_number: Optional[str] = None
    hospital_affiliation: Optional[str] = None
    contact_number: Optional[str] = None

class DoctorCreate(DoctorBase):
    user_id: str

class DoctorResponse(DoctorBase):
    doctor_id: str
    user_id: str
    first_name: str
    last_name: str
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True

# Patient-related schemas for doctor dashboard
class PatientBasicInfo(BaseModel):
    patient_id: str
    user_id: str
    first_name: str
    last_name: str
    username: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

class AssignedPatient(BaseModel):
    patient_id: str
    patient_name: str
    username: str
    assigned_date: str
    has_reports: bool = False

    class Config:
        from_attributes = True

# Recommendation-related schemas
class PendingRecommendation(BaseModel):
    recommendation_id: str
    patient_id: str
    report_id: str
    patient_name: str
    report_name: str
    ai_recommendation_date: str
    ai_priority: Optional[str] = None
    ai_generated_treatment: Optional[str] = None
    ai_generated_lifestyle: Optional[str] = None

    class Config:
        from_attributes = True

class ReviewedRecommendation(BaseModel):
    recommendation_id: str
    patient_id: str
    report_id: str
    patient_name: str
    report_name: str
    review_date: Optional[str] = None
    status: str
    doctor_notes: Optional[str] = None
    approved_treatment: Optional[str] = None
    approved_lifestyle: Optional[str] = None

    class Config:
        from_attributes = True

# Review action schemas
class ReviewAction(BaseModel):
    action: str  # "approve", "modify_approve", "reject"
    doctor_notes: Optional[str] = None
    modified_treatment: Optional[str] = None
    modified_lifestyle: Optional[str] = None

    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ["approve", "modify_approve", "reject"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v

    @validator('modified_treatment', 'modified_lifestyle')
    def validate_modifications(cls, v, values):
        if values.get('action') == 'modify_approve' and v is None:
            raise ValueError("Modified content required when action is 'modify_approve'")
        return v

# Dashboard overview schema
class DoctorDashboardOverview(BaseModel):
    doctor_info: DoctorResponse
    total_assigned_patients: int
    pending_reviews_count: int
    reviewed_recommendations_count: int
    total_reports_assigned: int

    class Config:
        from_attributes = True

# API Response schemas
class AssignedPatientsResponse(BaseModel):
    patients: List[AssignedPatient]
    total_count: int

    class Config:
        from_attributes = True

class PendingRecommendationsResponse(BaseModel):
    recommendations: List[PendingRecommendation]
    total_count: int

    class Config:
        from_attributes = True

class ReviewedRecommendationsResponse(BaseModel):
    recommendations: List[ReviewedRecommendation]
    total_count: int

    class Config:
        from_attributes = True

class RecommendationDetailsResponse(BaseModel):
    recommendation_id: str
    patient_id: str
    report_id: str
    patient_name: str
    report_name: str
    report_upload_date: str
    ai_generated_priority: Optional[str] = None
    ai_generated_treatment: Optional[str] = None
    ai_generated_lifestyle: Optional[str] = None
    status: str
    doctor_notes: Optional[str] = None
    approved_treatment: Optional[str] = None
    approved_lifestyle: Optional[str] = None
    created_at: str
    reviewed_date: Optional[str] = None
    reviewed_by_doctor_name: Optional[str] = None

    class Config:
        from_attributes = True

# Patient profile response for doctor view
class PatientProfileForDoctor(BaseModel):
    patient_id: str
    basic_info: PatientBasicInfo
    total_reports: int
    latest_report_date: Optional[str] = None

    class Config:
        from_attributes = True

# Health report summary for doctor view
class HealthReportSummary(BaseModel):
    report_id: str
    file_name: str
    report_type: str
    upload_date: str
    processing_status: str
    has_ai_recommendation: bool = False
    recommendation_status: Optional[str] = None

    class Config:
        from_attributes = True

class PatientReportsResponse(BaseModel):
    patient_info: PatientBasicInfo
    reports: List[HealthReportSummary]
    total_count: int

    class Config:
        from_attributes = True

# Additional schemas for error handling and responses
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None

# Authentication-related schemas
class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    user_type: Optional[str] = None

# Statistics and analytics schemas
class DoctorStatistics(BaseModel):
    total_patients: int
    active_patients: int
    pending_reviews: int
    completed_reviews: int
    approval_rate: float
    average_review_time: Optional[float] = None  # in hours

class PatientStatistics(BaseModel):
    patient_id: str
    total_reports: int
    pending_recommendations: int
    approved_recommendations: int
    rejected_recommendations: int
    last_report_date: Optional[str] = None

# Pagination schemas
class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100

    @validator('skip')
    def validate_skip(cls, v):
        if v < 0:
            raise ValueError("Skip must be non-negative")
        return v

    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v

# Filter schemas for advanced querying
class RecommendationFilter(BaseModel):
    status: Optional[str] = None
    patient_id: Optional[int] = None
    priority: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v and v not in ["pending", "approved", "rejected", "under_review"]:
            raise ValueError("Invalid status")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in ["high", "medium", "low", "urgent"]:
            raise ValueError("Invalid priority level")
        return v

class PatientFilter(BaseModel):
    gender: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    has_reports: Optional[bool] = None

# Bulk operation schemas
class BulkReviewAction(BaseModel):
    recommendation_ids: List[int]
    action: str
    doctor_notes: Optional[str] = None

    @validator('recommendation_ids')
    def validate_recommendation_ids(cls, v):
        if not v:
            raise ValueError("At least one recommendation ID is required")
        if len(v) > 100:
            raise ValueError("Cannot process more than 100 recommendations at once")
        return v

    @validator('action')
    def validate_bulk_action(cls, v):
        allowed_actions = ["approve", "reject"]
        if v not in allowed_actions:
            raise ValueError(f"Bulk action must be one of: {allowed_actions}")
        return v