# remedylab/backend/api/routes/recommendation_routes.py
# Import authentication dependencies
from utils.auth_dependencies import get_current_user, get_current_doctor, CurrentUser
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import sqlite3
from database.db import get_db
from sqlalchemy.orm import Session
from models.recommendation import Recommendation
from api.schemas.recommendation_schemas import (
    RecommendationResponse,
    RecommendationCreate,
    RecommendationUpdate,
    DoctorReviewRequest,
    RecommendationListResponse,
    ApprovedRecommendationResponse
)

router = APIRouter()

@router.post("/create", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
async def create_recommendation(
    recommendation_data: RecommendationCreate,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Create a new AI-generated recommendation for a health report.
    """
    try:
        # Verify that the report exists
        cursor = db.cursor()
        cursor.execute("SELECT report_id FROM health_reports WHERE report_id = ?", (recommendation_data.report_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health report not found.")
        
        # Create the recommendation
        recommendation = Recommendation.create(
            report_id=recommendation_data.report_id,
            patient_id=recommendation_data.patient_id,
            doctor_id=recommendation_data.doctor_id,
            ai_generated_treatment=recommendation_data.ai_generated_treatment,
            ai_generated_lifestyle=recommendation_data.ai_generated_lifestyle,
            ai_generated_priority=recommendation_data.ai_generated_priority,
            status=recommendation_data.status or 'AI_generated'
        )
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create recommendation."
            )
        
        return RecommendationResponse(**recommendation.to_dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating recommendation: {str(e)}"
        )


@router.get("/report/{report_id}", response_model=RecommendationResponse)
async def get_recommendation_by_report(
    report_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get recommendation by health report ID.
    """
    recommendation = Recommendation.find_by_report_id(report_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recommendation found for this report."
        )
    
    return RecommendationResponse(**recommendation.to_dict())


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation_by_id(
    recommendation_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get a specific recommendation by its ID.
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    return RecommendationResponse(**recommendation.to_dict())


@router.get("/patient/{patient_id}", response_model=List[RecommendationResponse])
async def get_patient_recommendations(
    patient_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all recommendations for a specific patient.
    """
    recommendations = Recommendation.get_by_patient_id(patient_id)
    
    if not recommendations:
        return []
    
    return [RecommendationResponse(**rec.to_dict()) for rec in recommendations]


@router.get("/patient/{patient_id}/approved", response_model=List[ApprovedRecommendationResponse])
async def get_approved_recommendations_for_patient(
    patient_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all approved recommendations for a patient with additional details.
    """
    approved_recommendations = Recommendation.get_approved_for_patient(patient_id)
    
    if not approved_recommendations:
        return []
    
    return [ApprovedRecommendationResponse(**rec) for rec in approved_recommendations]


@router.get("/doctor/{doctor_id}/pending", response_model=List[RecommendationResponse])
async def get_pending_recommendations_for_doctor(
    doctor_id: str,
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get all pending recommendations assigned to a doctor for review.
    """
     # Verify the current user is the requested doctor (security check)
    if current_user.user_id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own pending recommendations."
        )

    pending_recommendations = Recommendation.get_pending_for_doctor(doctor_id)

    if not pending_recommendations:
        return []
    
    return [RecommendationResponse(**rec.to_dict()) for rec in pending_recommendations]


@router.get("/doctor/{doctor_id}/reviewed", response_model=List[RecommendationResponse])
async def get_reviewed_recommendations_by_doctor(
    doctor_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Get all recommendations that have been reviewed by a specific doctor.
    """
    reviewed_recommendations = Recommendation.get_reviewed_by_doctor(doctor_id)
    
    if not reviewed_recommendations:
        return []
    
    return [RecommendationResponse(**rec.to_dict()) for rec in reviewed_recommendations]


@router.put("/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str,
    review_request: DoctorReviewRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Approve an AI-generated recommendation as-is.
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    success = recommendation.approve(
        doctor_id=review_request.doctor_id,
        doctor_notes=review_request.doctor_notes or ""
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve recommendation."
        )
    
    return {
        "message": "Recommendation approved successfully",
        "recommendation_id": recommendation_id,
        "status": "approved_by_doctor"
    }


@router.put("/{recommendation_id}/modify-approve")
async def modify_and_approve_recommendation(
    recommendation_id: str,
    review_request: DoctorReviewRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Modify and approve a recommendation with updated treatment and lifestyle plans.
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    if not review_request.approved_treatment or not review_request.approved_lifestyle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both approved_treatment and approved_lifestyle are required for modification."
        )
    
    success = recommendation.modify_and_approve(
        doctor_id=review_request.doctor_id,
        approved_treatment=review_request.approved_treatment,
        approved_lifestyle=review_request.approved_lifestyle,
        doctor_notes=review_request.doctor_notes or ""
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to modify and approve recommendation."
        )
    
    return {
        "message": "Recommendation modified and approved successfully",
        "recommendation_id": recommendation_id,
        "status": "modified_and_approved_by_doctor"
    }


@router.put("/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    review_request: DoctorReviewRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Reject an AI-generated recommendation.
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    if not review_request.doctor_notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor notes are required when rejecting a recommendation."
        )
    
    success = recommendation.reject(
        doctor_id=review_request.doctor_id,
        doctor_notes=review_request.doctor_notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject recommendation."
        )
    
    return {
        "message": "Recommendation rejected successfully",
        "recommendation_id": recommendation_id,
        "status": "rejected_by_doctor"
    }


@router.put("/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: str,
    update_data: RecommendationUpdate,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Update recommendation status and other fields.
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    success = recommendation.update_status(
        new_status=update_data.status,
        doctor_id=update_data.doctor_id,
        doctor_notes=update_data.doctor_notes,
        approved_treatment=update_data.approved_treatment,
        approved_lifestyle=update_data.approved_lifestyle
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update recommendation."
        )
    
    # Return updated recommendation
    updated_recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    return RecommendationResponse(**updated_recommendation.to_dict())


@router.delete("/{recommendation_id}")
async def delete_recommendation(
    recommendation_id: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Delete a recommendation (soft delete by updating status).
    """
    recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found."
        )
    
    # Instead of hard delete, we can mark as deleted
    success = recommendation.update_status(new_status="deleted")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete recommendation."
        )
    
    return {
        "message": "Recommendation deleted successfully",
        "recommendation_id": recommendation_id
    }