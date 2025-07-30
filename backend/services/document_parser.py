#remedylabs/services/document_parser.py
import os
import json
from datetime import datetime
from typing import Dict, Any,Optional, Tuple
import logging
# Import the specific extractors from your new 'extraction' sub-package
from services.extraction.text_extractor import RawTextExtractor
from services.extraction.patient_info_extractor import PatientInfoExtractor
from services.extraction.metric_extractor import MetricExtractor
import sqlite3
# Import the HealthReport DB interaction class
from models.health_report_model import HealthReport

# Import the auto-allocator
from services.auto_allocator import auto_assign_doctor

logger = logging.getLogger(__name__)


class DocumentParserService:

    @staticmethod
    def parse_report(file_path: str) -> Dict[str, Any]:
        """
        Parses a given health report file, extracts patient information and metrics.

        Args:
            file_path (str): The full path to the uploaded report file.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'patient_info': Dict with meta data
                - 'metrics': Dict with health metrics
                - 'raw_text': str, extracted raw text
                - 'errors': Optional list of error messages
        """
        raw_text = None
        patient_info: Dict[str, Optional[str]] = {}
        metrics: Dict[str, Tuple[str, str]] = {}
        errors = []

        # 1. Extract raw text
        try:
            ext = os.path.splitext(file_path.lower())[1]
            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                raw_text = RawTextExtractor.get_text_from_image(file_path)
            else:
                raw_text = RawTextExtractor.extract_text(file_path)

            if not raw_text or len(raw_text.strip()) < 20:
                msg = f"Insufficient text extracted from file '{os.path.basename(file_path)}'."
                logger.warning(msg)
                errors.append(msg)
                raw_text = ""
        except ValueError as e:
            msg = f"Unsupported file type for text extraction: {ext}. Error: {e}"
            logger.error(msg)
            return {
                "patient_info": {},
                "metrics": {},
                "raw_text": "",
                "errors": [msg]
            }
        except Exception as e:
            msg = f"Unexpected error during text extraction from {os.path.basename(file_path)}: {e}"
            logger.error(msg)
            return {
                "patient_info": {},
                "metrics": {},
                "raw_text": "",
                "errors": [msg]
            }

        # 2. Extract patient info (if raw text exists)
        if raw_text:
            try:
                patient_info = PatientInfoExtractor.extract_patient_info(raw_text)
            except Exception as e:
                msg = f"Failed to extract patient info: {e}"
                logger.warning(msg)
                patient_info = {}
                errors.append(msg)

            # 3. Extract health metrics
            try:
                metrics = MetricExtractor.extract_metrics(raw_text, is_path=False)
            except Exception as e:
                msg = f"Failed to extract health metrics: {e}"
                logger.warning(msg)
                metrics = {}
                errors.append(msg)
        else:
            errors.append("No valid raw text extracted. Skipping info and metric parsing.")

        return {
            "patient_info": patient_info,
            "metrics": metrics,
            "raw_text": raw_text,
            "errors": errors if errors else None
        }
    """
    Orchestrates the extraction of raw text, patient meta-info, and health metrics
    from various types of health report files for the FastAPI backend.
    """

    @classmethod
    def process_report_pipeline(cls, report_id: str, db: sqlite3.Connection) -> dict:
        """
        Full pipeline for processing a health report:
        1. Load report
        2. Extract data
        3. Save to DB
        4. Generate AI recommendations
        5. Save/update recommendations
        6. Trigger doctor auto-allocation

        Args:
            report_id: The ID of the report to process
            db: The database connection to use

        Returns:
            dict: Summary of processing outcome.
        """
        try:
            report = HealthReport.get_by_report_id(report_id)
            if not report:
                msg = f"Report {report_id} not found."
                logger.error(msg)
                return {"success": False, "step": "load_report", "error": msg}

            logger.info(f"🔍 Processing report: {report.file_name} ({report.report_id})")

            # --- Step 1: Extract content
            extracted = cls.parse_report(report.file_path)

            if not extracted or not extracted.get("raw_text"):
                report.processing_status = "failed_extraction"
                report.extracted_data_json = json.dumps({"error": "Extraction failed or empty content"})
            else:
                report.processing_status = "extracted"
                report.extracted_data_json = json.dumps(extracted)

            if not report.save():
                msg = f"❌ Failed to update report {report_id} with extracted data."
                logger.error(msg)
                return {"success": False, "step": "save_extracted_data", "error": msg}

            # --- Step 2: Auto-assign doctor
            if report.processing_status == "extracted":
                logger.info(f"🔄 Auto-assigning doctor for report {report_id}...")
                doctor_assigned  = auto_assign_doctor(report_id,db)

                if not doctor_assigned:
                    logger.warning(f"No doctor could be assigned to report {report_id}.")
                    return {
                        "success": False,
                        "step": "doctor_auto_assignment",
                        "error": "No suitable doctor could be assigned."
                    }
                # Refresh report after doctor assignment
                
                report = HealthReport.get_by_report_id(report_id)  # Refresh after update
                if not report or not report.assigned_doctor_id:
                    logger.error(f"Doctor assignment did not persist for report {report_id}.")
                    return {
                        "success": False,
                        "step": "doctor_verification",
                        "error": "Doctor assignment did not persist."
                    }
                logger.info(f"✅ Doctor {report.assigned_doctor_id} assigned to report {report_id}.")

            # --- Step 3: Generate AI recommendation
            from services.ai_recommendation_engine import generate_ai_recommendations
            from models.recommendation import Recommendation
            if report.processing_status == "doctor_assigned":
                logger.info(f"⚙️ Generating AI recommendations for report {report_id}...")
                
                try:
                    # Fixed import path - correct way to import from services directory
                    from services.ai_recommendation_engine import generate_ai_recommendations
                    from models.recommendation import Recommendation
                    
                    ai_data = generate_ai_recommendations(extracted)

                    if ai_data:
                        rec = Recommendation.find_by_report_id(report_id)
                        if rec:
                            # Update existing recommendation
                            updated = rec.update_status(
                                new_status="pending_doctor_review",
                                doctor_id=report.assigned_doctor_id,
                                approved_treatment=ai_data.get("treatment_suggestions", ""),
                                approved_lifestyle=ai_data.get("lifestyle_recommendations", ""),
                                doctor_notes=""
                            )
                            if updated:
                                logger.info(f"📌 Recommendation updated for report {report_id}.")
                            else:
                                logger.error(f"Failed to update recommendation for report {report_id}.")
                        else:
                            # Create new recommendation
                            created = Recommendation.create(
                                report_id=report.report_id,
                                patient_id=report.patient_id,
                                doctor_id=report.assigned_doctor_id,
                                ai_generated_treatment=ai_data.get("treatment_suggestions", ""),
                                ai_generated_lifestyle=ai_data.get("lifestyle_recommendations", ""),
                                ai_generated_priority=ai_data.get("priority", "Medium"),
                                status="pending_doctor_review"
                            )
                            if created:
                                logger.info(f"🆕 Recommendation created for report {report_id}.")
                            else:
                                logger.error(f"❌ Failed to create recommendation for report {report_id}.")

                        report.processing_status = "pending_doctor_review"
                    else:
                        logger.warning(f"AI engine returned no data for report {report_id}.")
                        report.processing_status = "pending_ai_analysis"

                    report.save()

                except ImportError as e:
                    logger.error(f"Failed to import AI recommendation engine: {e}")
                    logger.info("Skipping AI recommendation generation due to import error.")
                    # Continue with the pipeline but mark status appropriately
                    report.processing_status = "doctor_assigned_no_ai"
                    report.save()
                except Exception as e:
                    logger.error(f"Error during AI recommendation generation: {e}")
                    report.processing_status = "ai_generation_failed"
                    report.save()

            else:
                logger.info(f"Skipping AI generation for report {report_id} due to current status: {report.processing_status}")

            return {
                "success": True,
                "report_id": report_id,
                "status": report.processing_status,
                "assigned_doctor_id": report.assigned_doctor_id,
                "extracted": bool(extracted.get("raw_text")),
                "recommendation_attempted": report.processing_status in ["pending_doctor_review", "pending_ai_analysis", "ai_generation_failed"]
            }
        except Exception as e:
            logger.error(f"Pipeline error for report {report_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "step": "pipeline_execution",
                "error": f"Pipeline execution failed: {str(e)}"
            }