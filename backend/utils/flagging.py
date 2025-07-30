# utils/flagging.py
from __future__ import annotations
from typing import Dict, Union, Tuple
from utils.metrics import REF_RANGES # Import reference ranges

# Define the FlaggedMetric type for clarity
FlaggedMetric = Tuple[str, str] # (value-string, colour)

def flag_metrics(values: Dict[str, Union[float, None]]) -> Dict[str, FlaggedMetric]:
    """
    Flags extracted metric values as 'normal', 'abnormal', or 'missing'
    based on predefined reference ranges.
    """
    flagged: Dict[str, FlaggedMetric] = {}
    for metric, val in values.items():
        if val is None:
            flagged[metric] = ("❌ Missing", "red") # Indicate missing value in red
            continue
        if metric not in REF_RANGES:
            flagged[metric] = (f"{val} (no ref)", "gray") # Gray for metrics without reference ranges
            continue
        
        lo, hi = REF_RANGES[metric]
        
        # Determine the color and suffix based on the value's relation to the reference range
        if lo <= val <= hi:
            colour = "green" # Normal range
            suffix = ""
        else:
            colour = "orange" # Outside normal range
            suffix = " ⚠️" # Warning flag
            
        flagged[metric] = (f"{val}{suffix}", colour)
    return flagged