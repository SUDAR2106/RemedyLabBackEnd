"""
Metric‑parsing logic from your original extractor.py – **almost unchanged**.
Only difference: instead of calling the private PDF/DOCX helpers directly we
now import `extract_text` from text_extractor.py.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Tuple, Union

from .text_extractor import RawTextExtractor   # ⬅️ new
from utils.metrics import METRIC_ALIASES, ALIAS_LOOKUP, REF_RANGES
from utils.flagging import flag_metrics, FlaggedMetric  # ✅ import here

# --------------------------- helpers from original file --------------------
class MetricExtractor:
    @staticmethod
    def _clean_number(token: str) -> Union[float, None]:
        token = token.replace(",", "")
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", token)
        if m:
            try:
                return float(m.group())
            except ValueError:
                pass
        return None

   
    @staticmethod
    def extract_metrics(
        input_: Union[str, os.PathLike],
        is_path: bool = True
    ) -> Dict[str, FlaggedMetric]:
        """
    Exactly the same public API as before.
    Only difference: text is obtained via `extract_text()` helper if you pass a path.
    """
        if is_path:
            text = RawTextExtractor.extract_text(str(input_))
        else:
            text = str(input_)    # raw text directly

    # ------------------- remainder identical to your code -------------------
        values: Dict[str, Union[float, None]] = {m: None for m in METRIC_ALIASES}
        lines = text.splitlines()

        # Pass 1 – free‑form lines
        for raw in lines:
            line_lc = raw.lower()
            line = re.sub(r"[\-–=|]+", ":", line_lc)
            for alias_raw, canonical in ALIAS_LOOKUP.items():
                if re.search(rf"\b{re.escape(alias_raw)}\b", line):
                    segment = line.split(alias_raw, 1)[1]
                    val = MetricExtractor._clean_number(segment)
                    if val is not None and values[canonical] is None:
                        values[canonical] = val

        # Pass 2 – table lines (pipe‑delimited)
        for line in lines:
            if "|" not in line or len(line) < 10:
                continue
            cols = [c.strip().lower() for c in line.strip().strip("|").split("|")]
            if len(cols) < 2:
                continue
            metric_text, value_text = cols[0], cols[1]
            for alias, canonical in ALIAS_LOOKUP.items():
                if alias in metric_text and values[canonical] is None:
                    val = MetricExtractor._clean_number(value_text)
                    if val is not None:
                        values[canonical] = val

    # Derive ratios (same helpers as before)
        def _derive(key: str, func):
            if values.get(key) is None:
                try:
                    result = func()
                    if result is not None and not (result != result):  # exclude NaN
                        values[key] = round(result, 2)
                except ZeroDivisionError:
                    pass

        _derive("LDL/HDL Ratio",
                lambda: values["LDL"] / values["HDL"]
                if values["LDL"] and values["HDL"] else None)
        _derive("Total Cholesterol/HDL Ratio",
                lambda: values["Total Cholesterol"] / values["HDL"]
                if values["Total Cholesterol"] and values["HDL"] else None)
        _derive("TG/HDL Ratio",
                lambda: values["Triglycerides"] / values["HDL"]
                if values["Triglycerides"] and values["HDL"] else None)
        _derive("Non-HDL Cholesterol",
                lambda: values["Total Cholesterol"] - values["HDL"]
                if values["Total Cholesterol"] and values["HDL"] else None)
        
         # ✅ Use shared flagging logic
        return flag_metrics(values)
