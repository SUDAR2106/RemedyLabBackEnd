#remedylab/backend/api/routes/doctor_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

# Import authentication dependencies
from utils.auth_dependencies import get_current_user, get_current_doctor, CurrentUser
# Import database session dependency
from database.db import get_db
# Import models
from models.user_model import User, Patient, Doctor
from models.health_report_model import HealthReport
from models.recommendation import Recommendation
from models.patient_doctor_mapping import PatientDoctorMapping
# Import schemas
from api.schemas.doctor_schemas import (
    DoctorResponse, 
    DoctorDashboardOverview,
    AssignedPatientsResponse,
    AssignedPatient,
    PendingRecommendationsResponse,
    PendingRecommendation,
    ReviewedRecommendationsResponse,
    ReviewedRecommendation,
    RecommendationDetailsResponse,
    ReviewAction,
    PatientProfileForDoctor,
    PatientBasicInfo,
    PatientReportsResponse,
    HealthReportSummary
)

# Utility function for safe date formatting
def format_date_safe(date_obj):
    """Safely format a date object, handling both datetime and string types"""
    if date_obj is None:
        return None
    if isinstance(date_obj, str):
        return date_obj  # Already a string, return as-is
    if hasattr(date_obj, 'strftime'):
        return date_obj.strftime("%Y-%m-%d")
    return str(date_obj) if date_obj else None

# Create router with explicit tags and prefix
router = APIRouter(
    tags=["Doctor Dashboard"],
    responses={
        401: {"description": "Unauthorized - JWT token required"},
        403: {"description": "Forbidden - Doctor role required"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get("/test")
async def test_doctor_route():
    return {"message": "doctor router is active"}

print("✓ doctor_routes.py loaded. Routes:", [route.path for route in router.routes])

@router.get("/dashboard/overview", response_model=DoctorDashboardOverview)
async def get_dashboard_overview(
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get dashboard overview with doctor info and summary statistics
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get assigned patients count
        assigned_patients_count = PatientDoctorMapping.count_by_doctor_id(doctor.doctor_id)

        # Get pending recommendations count
        pending_reviews_count = Recommendation.count_pending_by_doctor_id(doctor.doctor_id)
        
        # Get reviewed recommendations count
        reviewed_recommendations_count = Recommendation.count_reviewed_by_doctor_id(doctor.doctor_id)

        # Get total reports assigned to this doctor
        total_reports_assigned = Recommendation.count_total_reports_assigned_to_doctor(doctor.doctor_id)
        
        return DoctorDashboardOverview(
            doctor_info=DoctorResponse(
                doctor_id=doctor.doctor_id,
                user_id=current_user.user_id,
                first_name=current_user.first_name,
                last_name=current_user.last_name,
                username=current_user.username,
                email=current_user.email,
                specialization=doctor.specialization,
                medical_license_number=doctor.medical_license_number,
                hospital_affiliation=doctor.hospital_affiliation,
                contact_number=doctor.contact_number
            ),
            total_assigned_patients=assigned_patients_count,
            pending_reviews_count=pending_reviews_count,
            reviewed_recommendations_count=reviewed_recommendations_count,
            total_reports_assigned=total_reports_assigned
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )

@router.get("/patients/assigned", response_model=AssignedPatientsResponse)
async def get_assigned_patients(
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get list of patients assigned to the current doctor
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get assigned patients with pagination
        assigned_patients = PatientDoctorMapping.find_patients_for_doctor(
            doctor.doctor_id,skip=skip, limit=limit
        )
        
        patients_list = []
        total_report_count = 0  # Initialize total report count

        for mapping in assigned_patients:
            patient_id = mapping["patient_id"]
            user = User.get_by_user_id(mapping["user_id"])

            # Count reports for this patient
            report_count = HealthReport.count_by_patient_id(patient_id)
            has_reports = report_count > 0

            # ✅ Add this patient's reports to total
            total_report_count += report_count

            #patient = Patient.get_by_patient_id(patient_id)
             # Parse assigned_date safely
            # Format assigned_date safely
            assigned_date_str = format_date_safe(mapping.get("assigned_date"))
                                                      
                
            patients_list.append(AssignedPatient(
                patient_id=patient_id,
                patient_name=f"{user.first_name} {user.last_name}",
                username=user.username,
                assigned_date=assigned_date_str,
                has_reports=has_reports
            ))
        
        #total_count = PatientDoctorMapping.count_by_doctor_id(doctor.doctor_id)
        
        return AssignedPatientsResponse(
            patients=patients_list,
            total_count=total_report_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assigned patients: {str(e)}"
        )

@router.get("/patient/{patient_id}/profile", response_model=PatientProfileForDoctor)
async def get_patient_profile(
    patient_id: str = Path(..., description="Patient ID"),
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get patient profile information for doctor view
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Verify patient is assigned to this doctor
        mapping = PatientDoctorMapping.get_by_doctor_and_patient_id(
            doctor.doctor_id, patient_id
        )
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient not assigned to this doctor"
            )
        
        # Get patient information
        patient = Patient.get_by_patient_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        user = User.get_by_user_id(patient.user_id)
        
        # Get patient reports statistics
        total_reports = HealthReport.count_by_patient_id(patient_id)
        latest_report = HealthReport.get_latest_by_patient_id(patient_id)

            
        return PatientProfileForDoctor(
            patient_id=patient_id,
            basic_info=PatientBasicInfo(
                patient_id=patient_id,
                user_id=patient.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                date_of_birth=format_date_safe(patient.date_of_birth),
                gender=patient.gender,
                contact_number=patient.contact_number,
                address=patient.address,
                email=user.email
            ),
            total_reports=total_reports,
            latest_report_date=format_date_safe(latest_report.upload_date if latest_report else None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient profile: {str(e)}"
        )

@router.get("/patient/{patient_id}/reports", response_model=PatientReportsResponse)
async def get_patient_reports(
    patient_id: str = Path(..., description="Patient ID"),
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get patient's health reports list for doctor view
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Verify patient is assigned to this doctor
        mapping = PatientDoctorMapping.get_by_doctor_and_patient_id(
            doctor.doctor_id, patient_id
        )
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient not assigned to this doctor"
            )
        
        # Get patient information
        patient = Patient.get_by_patient_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        user = User.get_by_user_id(patient.user_id)
        
        # Get patient reports with pagination
        reports = HealthReport.get_by_patient_id_paginated(
            patient_id, skip=skip, limit=limit
        )
        
        reports_list = []
        for report in reports:
            # Check if report has AI recommendation
            recommendation = Recommendation.get_by_report_id(report.report_id)
            has_ai_recommendation = recommendation is not None
            recommendation_status = recommendation.status if recommendation else None
            
            reports_list.append(HealthReportSummary(
                report_id=report.report_id,
                file_name=report.file_name,
                report_type=report.report_type,
                upload_date=format_date_safe(report.upload_date),
                processing_status=report.processing_status,
                has_ai_recommendation=has_ai_recommendation,
                recommendation_status=recommendation_status
            ))
        
        total_count = HealthReport.count_by_patient_id(patient_id)
        
        return PatientReportsResponse(
            patient_info=PatientBasicInfo(
                patient_id=patient_id,
                user_id=patient.user_id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                date_of_birth=format_date_safe(patient.date_of_birth),
                gender=patient.gender,
                contact_number=patient.contact_number,
                address=patient.address,
                email=user.email
            ),
            reports=reports_list,
            total_count=total_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient reports: {str(e)}"
        )

@router.get("/recommendations/pending", response_model=PendingRecommendationsResponse)
async def get_pending_recommendations(
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get list of pending recommendations for doctor review
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get pending recommendations for this doctor's patients
        pending_recommendations = Recommendation.get_pending_by_doctor_id(
            doctor.doctor_id, skip=skip, limit=limit
        )
        
        recommendations_list = []
        for recommendation in pending_recommendations:
            # Get patient and report information
            report = HealthReport.get_by_report_id(recommendation.report_id)
            patient = Patient.get_by_patient_id(recommendation.patient_id)
            user = User.get_by_user_id(patient.user_id)
            
            recommendations_list.append(PendingRecommendation(
                recommendation_id=recommendation.recommendation_id,
                patient_id=recommendation.patient_id,
                report_id=recommendation.report_id,
                patient_name=f"{user.first_name} {user.last_name}",
                report_name=report.file_name,
                ai_recommendation_date=format_date_safe(recommendation.created_at),
                ai_priority=recommendation.ai_generated_priority,
                ai_generated_treatment=recommendation.ai_generated_treatment,
                ai_generated_lifestyle=recommendation.ai_generated_lifestyle
            ))
        
        total_count = Recommendation.count_pending_by_doctor_id(doctor.doctor_id)
        
        return PendingRecommendationsResponse(
            recommendations=recommendations_list,
            total_count=total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending recommendations: {str(e)}"
        )

@router.get("/recommendation/{recommendation_id}/details", response_model=RecommendationDetailsResponse)
async def get_recommendation_details(
    recommendation_id: str = Path(..., description="Recommendation ID"),
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get detailed recommendation information for review interface
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get recommendation
        recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        
        # Verify patient is assigned to this doctor
        mapping = PatientDoctorMapping.get_by_doctor_and_patient_id(
            doctor.doctor_id, recommendation.patient_id
        )
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient not assigned to this doctor"
            )
        
        # Get related information
        report = HealthReport.get_by_report_id(recommendation.report_id)
        patient = Patient.get_by_patient_id(recommendation.patient_id)
        user = User.get_by_user_id(patient.user_id)
        
        # Get reviewer information if reviewed
        reviewed_by_doctor_name = None
        if recommendation.reviewed_by_doctor_id:
            reviewer_doctor = Doctor.get_by_doctor_id(recommendation.reviewed_by_doctor_id)
            if reviewer_doctor:
                reviewer_user = User.get_by_user_id(reviewer_doctor.user_id)
                reviewed_by_doctor_name = f"Dr. {reviewer_user.first_name} {reviewer_user.last_name}"
        
        return RecommendationDetailsResponse(
            recommendation_id=recommendation.recommendation_id,
            patient_id=recommendation.patient_id,
            report_id=recommendation.report_id,
            patient_name=f"{user.first_name} {user.last_name}",
            report_name=report.file_name,
            report_upload_date=format_date_safe(report.upload_date),
            ai_generated_priority=recommendation.ai_generated_priority,
            ai_generated_treatment=recommendation.ai_generated_treatment,
            ai_generated_lifestyle=recommendation.ai_generated_lifestyle,
            status=recommendation.status,
            doctor_notes=recommendation.doctor_notes,
            approved_treatment=recommendation.approved_treatment,
            approved_lifestyle=recommendation.approved_lifestyle,
            created_at=format_date_safe(recommendation.created_at),
            reviewed_date=format_date_safe(recommendation.reviewed_date),
            reviewed_by_doctor_name=reviewed_by_doctor_name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendation details: {str(e)}"
        )

@router.post("/recommendation/{recommendation_id}/review")
async def review_recommendation(
    review_action: ReviewAction,
    recommendation_id: str = Path(..., description="Recommendation ID"),
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """    Submit review action for a recommendation
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get recommendation
        recommendation = Recommendation.get_by_recommendation_id(recommendation_id)
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        
        # Verify patient is assigned to this doctor
        mapping = PatientDoctorMapping.find_patients_for_doctor(
            doctor.doctor_id, recommendation.patient_id
        )
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient not assigned to this doctor"
            )
        
        # Validate recommendation status
        if recommendation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recommendation has already been reviewed"
            )
        
        # Update recommendation based on action
        update_data = {
            "reviewed_by_doctor_id": doctor.doctor_id,
            "reviewed_date": datetime.now(),
            "doctor_notes": review_action.doctor_notes
        }
        
        if review_action.action == "approve":
            update_data.update({
                "status": "approved",
                "approved_treatment": recommendation.ai_generated_treatment,
                "approved_lifestyle": recommendation.ai_generated_lifestyle
            })
        elif review_action.action == "modify_approve":
            update_data.update({
                "status": "approved",
                "approved_treatment": review_action.modified_treatment or recommendation.ai_generated_treatment,
                "approved_lifestyle": review_action.modified_lifestyle or recommendation.ai_generated_lifestyle
            })
        elif review_action.action == "reject":
            update_data["status"] = "rejected"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid review action. Must be 'approve', 'modify_approve', or 'reject'"
            )
        
        # Update recommendation in database
        success = Recommendation.update_recommendation(recommendation_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update recommendation"
            )
        
        return {
            "message": "Recommendation reviewed successfully",
            "recommendation_id": recommendation_id,
            "action": review_action.action,
            "status": update_data["status"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review recommendation: {str(e)}"
        )

@router.get("/recommendations/reviewed", response_model=ReviewedRecommendationsResponse)
async def get_reviewed_recommendations(
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get list of reviewed recommendations by the current doctor
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        # Get reviewed recommendations by this doctor
        reviewed_recommendations = Recommendation.get_reviewed_by_doctor_id(
            doctor.doctor_id, skip=skip, limit=limit
        )
        
        recommendations_list = []
        for recommendation in reviewed_recommendations:
            # Get patient and report information
            report = HealthReport.get_by_report_id(recommendation.report_id)
            patient = Patient.get_by_patient_id(recommendation.patient_id)
            user = User.get_by_user_id(patient.user_id)
            
            recommendations_list.append(ReviewedRecommendation(
                recommendation_id=recommendation.recommendation_id,
                patient_id=recommendation.patient_id,
                report_id=recommendation.report_id,
                patient_name=f"{user.first_name} {user.last_name}",
                report_name=report.file_name,
                review_date=format_date_safe(recommendation.reviewed_date),
                status=recommendation.status,
                doctor_notes=recommendation.doctor_notes,
                approved_treatment=recommendation.approved_treatment,
                approved_lifestyle=recommendation.approved_lifestyle
            ))
        
        total_count = Recommendation.count_reviewed_by_doctor_id(doctor.doctor_id)
        
        return ReviewedRecommendationsResponse(
            recommendations=recommendations_list,
            total_count=total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviewed recommendations: {str(e)}"
        )

@router.get("/profile", response_model=DoctorResponse)
async def get_doctor_profile(
    current_user: CurrentUser = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get current doctor's profile information
    """
    try:
        # Get doctor profile
        doctor = Doctor.get_by_doctor_id(current_user.user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        return DoctorResponse(
            doctor_id=doctor.doctor_id,
            user_id=current_user.user_id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            username=current_user.username,
            email=current_user.email,
            specialization=doctor.specialization,
            medical_license_number=doctor.medical_license_number,
            hospital_affiliation=doctor.hospital_affiliation,
            contact_number=doctor.contact_number
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get doctor profile: {str(e)}"
        )