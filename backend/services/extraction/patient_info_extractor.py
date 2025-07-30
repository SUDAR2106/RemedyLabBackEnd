"""
Patient‑meta parsing logic copied verbatim.
"""
from __future__ import annotations
import re
from typing import Dict, Optional

class PatientInfoExtractor:
    @staticmethod
    def extract_patient_info(text: str) -> Dict[str, Optional[str]]:
        info = {
            "Patient Name": None,
            "Patient ID": None,
            "Age": None,
            "Sex": None,
            "Report Date": None,
            "UHID": None,
            "Lab ID": None,
        }

        patterns = {
            "Patient Name": [
                r"Name\s*[:\-]?\s*(Baby\.?|Master\.?)?\s*([A-Z][a-zA-Z .'-]+)",
                r"Patient Name\s*[:\-]?\s*([A-Z][a-zA-Z .'-]+)",
            ],
            "Patient ID": [
                r"(?:Patient ID|PID|Reg\.?\s*No\.?)\s*[:\-]?\s*(\S+)"
            ],
            "Age": [
                r"Age\s*/\s*Sex\s*[:\-]?\s*(\d+\s*(?:YRS|Years|Mon|Months)?)",
                r"Age\s*[:\-]?\s*(\d+\s*(?:YRS|Years|Mon|Months)?)"
            ],
            "Sex": [
                r"Age\s*/\s*Sex\s*[:\-]?\s*\d+\s*(?:YRS|Mon|Months)?\s*/\s*(M|F)",
                r"Sex\s*[:\-]?\s*(Male|Female|M|F|Other)"
            ],
            "Report Date": [
                r"(?:Report(?:ed)? on|Date|Generated on|Registered on|Collected on)"
                r"\s*[:\-]?\s*([0-3]?\d[/\-\.][01]?\d[/\-\.]\d{4})"
            ],
            "UHID": [r"UHID\s*No\s*[:\-]?\s*(\S+)"],
            "Lab ID": [r"LAB\s*ID\s*No\s*[:\-]?\s*(\S+)"],
        }

        for key, regex_list in patterns.items():
            for pattern in regex_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if key == "Patient Name":
                        parts = match.groups()
                        value = " ".join(p for p in parts if p).strip()
                    else:
                        value = match.group(1).strip()

                    if key == "Sex":
                        if value.upper() in ["M", "MALE"]:
                            info[key] = "Male"
                        elif value.upper() in ["F", "FEMALE"]:
                            info[key] = "Female"
                        else:
                            info[key] = value.capitalize()
                    else:
                        info[key] = value
                    break
        return info
