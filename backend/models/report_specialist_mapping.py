# models/report_specialist_mapping.py
import uuid
from database.db_utils import DBManager

class ReportSpecialistMapping:
    def __init__(self, report_type: str, specialization_required: str):
        self.report_type = report_type
        self.specialization_required = specialization_required

    @classmethod
    def create(cls, report_type: str, specialization_required: str) -> 'ReportSpecialistMapping':
        """Creates a new report specialist mapping entry."""
        db_manager = DBManager()
        query = "INSERT INTO report_specialist_mapping (report_type, specialization_required) VALUES (?, ?)"
        if db_manager.execute_query(query, (report_type, specialization_required)):
            return cls(report_type, specialization_required)
        return None

    @classmethod
    def get_specialization_by_report_type(cls, report_type: str) -> str:
        """Retrieves the required specialization for a given report type."""
        db_manager = DBManager()
        query = "SELECT specialization_required FROM report_specialist_mapping WHERE report_type = ?"
        result = db_manager.fetch_one(query, (report_type,))
        if result:
            return result['specialization_required']
        return None # No specific specialization found

    @classmethod
    def update(cls, report_type: str, new_specialization_required: str) -> bool:
        """Updates the specialization for an existing report type mapping."""
        db_manager = DBManager()
        query = "UPDATE report_specialist_mapping SET specialization_required = ? WHERE report_type = ?"
        return db_manager.execute_query(query, (new_specialization_required, report_type))

    @classmethod
    def delete(cls, report_type: str) -> bool:
        """Deletes a report specialist mapping entry."""
        db_manager = DBManager()
        query = "DELETE FROM report_specialist_mapping WHERE report_type = ?"
        return db_manager.execute_query(query, (report_type,))
    
    @staticmethod
    def has_any_mappings() -> bool:
        """
        Checks if any report-specialist mappings already exist in the table.
        """
        db_manager = DBManager()
        result = db_manager.fetch_one("SELECT 1 FROM report_specialist_mapping LIMIT 1")
        return result is not None