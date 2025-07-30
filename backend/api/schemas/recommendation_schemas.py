# remedylab/backend/api/schemas/recommendation_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class RecommendationBase(BaseModel):
    """
    Base schema for recommendations with common fields
    """
    report_id: str = Field(..., description="ID of the health report")
    patient_id: str = Field(..., description="ID of the patient")
    ai_generated_treatment: str = Field(..., description="AI-generated treatment plan")
    ai_generated_lifestyle: str = Field(..., description="AI-generated lifestyle recommendations")
    ai_generated_priority: str = Field(..., description="AI-generated priority level")
    doctor_id: Optional[str] = Field(None, description="ID of the assigned doctor")
    status: str = Field("AI_generated", description="Current status of the recommendation")

class RecommendationCreate(RecommendationBase):
    """
    Schema for creating a new recommendation
    """
    pass

class RecommendationResponse(RecommendationBase):
    """
    Schema for recommendation responses
    """
    recommendation_id: str = Field(..., description="Unique identifier for the recommendation")
    doctor_notes: Optional[str] = Field(None, description="Doctor's notes on the recommendation")
    reviewed_date: Optional[str] = Field(None, description="Date when the recommendation was reviewed")
    approved_treatment: Optional[str] = Field(None, description="Doctor-approved treatment plan")
    approved_lifestyle: Optional[str] = Field(None, description="Doctor-approved lifestyle recommendations")
    created_at: str = Field(..., description="Creation timestamp")
    last_updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class RecommendationUpdate(BaseModel):
    """
    Schema for updating recommendation fields
    """
    status: str = Field(..., description="New status for the recommendation")
    doctor_id: Optional[str] = Field(None, description="Doctor ID")
    doctor_notes: Optional[str] = Field(None, description="Doctor's notes")
    approved_treatment: Optional[str] = Field(None, description="Approved treatment plan")
    approved_lifestyle: Optional[str] = Field(None, description="Approved lifestyle recommendations")

class DoctorReviewRequest(BaseModel):
    """
    Schema for doctor review actions (approve, modify, reject)
    """
    doctor_id: str = Field(..., description="ID of the reviewing doctor")
    doctor_notes: Optional[str] = Field(None, description="Doctor's notes on the review")
    approved_treatment: Optional[str] = Field(None, description="Modified treatment plan (for modify-approve)")
    approved_lifestyle: Optional[str] = Field(None, description="Modified lifestyle plan (for modify-approve)")

class ApprovalRequest(BaseModel):
    """
    Schema for simple approval without modifications
    """
    doctor_id: str = Field(..., description="ID of the approving doctor")
    doctor_notes: Optional[str] = Field("", description="Optional notes from the doctor")

class ModifyApprovalRequest(BaseModel):
    """
    Schema for modifying and approving recommendations
    """
    doctor_id: str = Field(..., description="ID of the reviewing doctor")
    approved_treatment: str = Field(..., description="Modified treatment plan")
    approved_lifestyle: str = Field(..., description="Modified lifestyle recommendations")
    doctor_notes: Optional[str] = Field("", description="Doctor's notes on modifications")

class RejectionRequest(BaseModel):
    """
    Schema for rejecting recommendations
    """
    doctor_id: str = Field(..., description="ID of the rejecting doctor")
    doctor_notes: str = Field(..., description="Required notes explaining rejection")

class RecommendationListResponse(BaseModel):
    """
    Schema for listing multiple recommendations
    """
    recommendations: List[RecommendationResponse]
    total_count: int
    page: int = 1
    page_size: int = 10

class ApprovedRecommendationResponse(BaseModel):
    """
    Schema for approved recommendations with additional details (from joined query)
    """
    recommendation_id: str
    report_id: str
    patient_id: str
    ai_generated_treatment: str
    ai_generated_lifestyle: str
    ai_generated_priority: str
    doctor_id: Optional[str]
    doctor_notes: Optional[str]
    status: str
    reviewed_date: Optional[str]
    approved_treatment: Optional[str]
    approved_lifestyle: Optional[str]
    created_at: str
    last_updated_at: str
    report_name: Optional[str] = Field(None, alias="Report Name")
    doctor_first_name: Optional[str]
    doctor_last_name: Optional[str]
    doctor_name: Optional[str] = Field(None, alias="Doctor Name")

    class Config:
        allow_population_by_field_name = True

class RecommendationStatusUpdate(BaseModel):
    """
    Schema for updating just the recommendation status
    """
    status: str = Field(..., description="New status for the recommendation")

class RecommendationSummary(BaseModel):
    """
    Schema for recommendation summary (minimal info)
    """
    recommendation_id: str
    patient_id: str
    status: str
    created_at: str
    reviewed_date: Optional[str]
    doctor_name: Optional[str]

class DoctorWorkloadResponse(BaseModel):
    """
    Schema for doctor workload statistics
    """
    doctor_id: str
    pending_count: int
    reviewed_count: int
    approved_count: int
    rejected_count: int
    modified_count: int

class RecommendationStats(BaseModel):
    """
    Schema for recommendation statistics
    """
    total_recommendations: int
    ai_generated: int
    pending_review: int
    approved: int
    modified_approved: int
    rejected: int

class ActionResponse(BaseModel):
    """
    Schema for action confirmation responses
    """
    message: str
    recommendation_id: str
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """
    Schema for error responses
    """
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Status enumeration for validation
class RecommendationStatus:
    AI_GENERATED = "AI_generated"
    PENDING_DOCTOR_REVIEW = "pending_doctor_review"
    APPROVED_BY_DOCTOR = "approved_by_doctor"
    MODIFIED_AND_APPROVED = "modified_and_approved_by_doctor"
    REJECTED_BY_DOCTOR = "rejected_by_doctor"
    DELETED = "deleted"
    
    @classmethod
    def get_all_statuses(cls):
        return [
            cls.AI_GENERATED,
            cls.PENDING_DOCTOR_REVIEW,
            cls.APPROVED_BY_DOCTOR,
            cls.MODIFIED_AND_APPROVED,
            cls.REJECTED_BY_DOCTOR,
            cls.DELETED
        ]

class PaginationParams(BaseModel):
    """
    Schema for pagination parameters
    """
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")
    
class FilterParams(BaseModel):
    """
    Schema for filtering recommendations
    """
    status: Optional[str] = Field(None, description="Filter by status")
    doctor_id: Optional[str] = Field(None, description="Filter by doctor ID")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")