"""
Central place to store metric → alias mapping and reference ranges.
Add or edit entries here – extractor.py will pick them up automatically.
"""
from typing import Dict, List, Tuple

# ------------------------------------------------------------------
# Metric aliases grouped by category – extend as needed
# ------------------------------------------------------------------
METRIC_ALIASES: Dict[str, List[str]] = {
    # CBC (Complete Blood Count)
    "Hemoglobin": [
        "hemoglobin", "haemoglobin", "hb", "hemoglobin (hb)", "hemoglobin hb"
    ],
    "WBC": [
        "wbc", "white blood cells", "white blood", "total wbc", "total wbc count"
    ],
    "RBC": [
        "rbc", "red blood cells", "red blood", "rbc count"
    ],
    "Platelet Count": [
        "platelet", "platelets", "plts", "platelet count"
    ],

    # Lipid Profile
    "Total Cholesterol": ["cholesterol", "total cholesterol"],
    "HDL": ["hdl", "hdl cholesterol"],
    "LDL": ["ldl", "ldl cholesterol"],
    "Triglycerides": ["triglycerides", "tg"],
    "VLDL": ["vldl", "vldl cholesterol"],
    "LDL/HDL Ratio": ["ldl/hdl", "ldl / hdl", "ldl to hdl ratio"],
    "Total Cholesterol/HDL Ratio": [
        "total cholesterol/hdl", "total cholesterol / hdl", "tc/hdl", "chol/hdl"
    ],
    "TG/HDL Ratio": ["tg/hdl", "tg / hdl", "triglyceride/hdl"],
    "Non-HDL Cholesterol": ["non-hdl", "non-hdl cholesterol", "non hdl"],

    # Glucose
    "Fasting Glucose": [
        "fbs", "fasting glucose", "fasting blood sugar", "fasting blood sugar"
    ],
    "Random Glucose": [
        "random glucose", "ppbs", "postprandial glucose", "postprandial blood sugar"
    ],
    "Glucose": ["glucose", "blood glucose"],

    # Diabetes monitoring
    "HbA1c": ["hba1c", "glycated hemoglobin"],

    # LFT (Liver Function Test)
    "ALT (SGPT)": ["alt", "sgpt", "sgpt (alt)"],
    "AST (SGOT)": ["ast", "sgot", "sgot (ast)"],
    "Total Bilirubin": ["bilirubin", "total bilirubin"],
    "Alkaline Phosphatase": ["alkaline phosphatase", "alk phos", "alp"],

    # KFT (Kidney Function Test)
    "Serum Creatinine": ["creatinine", "serum creatinine"],
    "Blood Urea": ["urea", "blood urea"],

    # Urinalysis
    "Urine pH": ["urine ph"],
    "Specific Gravity": ["specific gravity", "urine sg"],
}

# ------------------------------------------------------------------
# Flat alias → canonical lookup
# ------------------------------------------------------------------
ALIAS_LOOKUP: Dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in METRIC_ALIASES.items()
    for alias in aliases
}

# ------------------------------------------------------------------
# Reference (adult) ranges – edit as required
# Values: (lower_limit, upper_limit)
# ------------------------------------------------------------------
REF_RANGES: Dict[str, Tuple[float, float]] = {
    # CBC (Complete Blood Count)
    "Hemoglobin": (12, 17),
    "WBC": (4000, 11000),
    "RBC": (4.0, 6.0),
    "Platelet Count": (150000, 450000),

    # Lipid Profile
    "Total Cholesterol": (120, 200),
    "HDL": (40, 60),
    "LDL": (0, 100),
    "Triglycerides": (0, 150),
    "VLDL": (5, 40),
    "LDL/HDL Ratio": (1.0, 3.5),
    "Total Cholesterol/HDL Ratio": (3.5, 5.0),
    "TG/HDL Ratio": (0.5, 3.0),
    "Non-HDL Cholesterol": (0, 130),

    # Glucose
    "Fasting Glucose": (70, 100),
    "Random Glucose": (70, 140),
    "Glucose": (70, 140),

    # Diabetes monitoring
    "HbA1c": (4.0, 5.6),

    # LFT (Liver Function Test)
    "ALT (SGPT)": (7, 56),
    "AST (SGOT)": (5, 40),
    "Total Bilirubin": (0.3, 1.2),
    "Alkaline Phosphatase": (44, 147),

    # KFT (Kidney Function Test)
    "Serum Creatinine": (0.6, 1.3),
    "Blood Urea": (10, 50),

    # Urinalysis
    "Urine pH": (4.5, 8.0),
    "Specific Gravity": (1.005, 1.030),
}
