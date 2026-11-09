import re
from datetime import date
from typing import Any

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def parse_date_token(token: str | None, is_end_date: bool = False) -> date | None:
    if not token:
        return None

    clean = token.strip().lower()
    if any(k in clean for k in ["present", "current", "till date", "now", "today"]):
        return date.today()

    # Pattern: Month YYYY (e.g. "March 2018", "Mar 2018")
    m_match = re.search(r"([a-z]+)\.?\s+(\d{4})", clean)
    if m_match:
        m_str = m_match.group(1)
        year = int(m_match.group(2))
        month = MONTH_MAP.get(m_str, 1)
        return date(year, month, 28 if is_end_date and month == 2 else 1)

    # Pattern: Month 'YY or Month YY (e.g. "June '19", "Jun 19")
    m_short_match = re.search(r"([a-z]+)\.?\s+['\u2019]?(\d{2})\b", clean)
    if m_short_match:
        m_str = m_short_match.group(1)
        yy = int(m_short_match.group(2))
        year = 2000 + yy if yy < 70 else 1900 + yy
        month = MONTH_MAP.get(m_str, 1)
        return date(year, month, 28 if is_end_date and month == 2 else 1)

    # Pattern: MM/YYYY or MM-YYYY
    slash_match = re.search(r"(\d{1,2})[/-](\d{4})", clean)
    if slash_match:
        month = max(1, min(12, int(slash_match.group(1))))
        year = int(slash_match.group(2))
        return date(year, month, 1)

    # Pattern: YYYY-MM
    iso_match = re.search(r"(\d{4})[/-](\d{1,2})", clean)
    if iso_match:
        year = int(iso_match.group(1))
        month = max(1, min(12, int(iso_match.group(2))))
        return date(year, month, 1)

    # Pattern: Just YYYY (e.g. "2018")
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", clean)
    if year_match:
        year = int(year_match.group(1))
        return date(year, 12 if is_end_date else 1, 1)

    return None


def merge_date_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Merge overlapping or contiguous date intervals."""
    if not intervals:
        return []

    # Filter invalid and sort by start date
    valid = [(s, e) for s, e in intervals if s <= e]
    if not valid:
        return []

    sorted_intervals = sorted(valid, key=lambda x: x[0])
    merged: list[tuple[date, date]] = [sorted_intervals[0]]

    for current_start, current_end in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if current_start <= prev_end:
            # Overlapping or contiguous interval: merge
            merged[-1] = (prev_start, max(prev_end, current_end))
        else:
            merged.append((current_start, current_end))

    return merged


def calculate_experience_from_intervals(intervals: list[tuple[date, date]]) -> float:
    merged = merge_date_intervals(intervals)
    total_days = sum((end - start).days for start, end in merged)
    years = round(total_days / 365.25, 1)
    return max(0.0, years)


def extract_explicit_experience_years(text: str) -> float | None:
    text_lower = text.lower()
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience",
        r"experience\s*[:=-]\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        r"total\s+experience\s*[:=-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
    ]
    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def compute_experience_years(
    employment_entries: list[dict[str, Any]],
    raw_text: str,
) -> tuple[float, float]:
    """Computes total experience in years and a parse quality score (0.0 to 1.0).

    Returns: (experience_years, parse_quality)
    """
    intervals: list[tuple[date, date]] = []

    for entry in employment_entries:
        start_str = entry.get("start")
        end_str = entry.get("end") or entry.get("to")
        start_dt = parse_date_token(start_str, is_end_date=False)
        end_dt = parse_date_token(end_str, is_end_date=True)

        if start_dt and end_dt:
            if start_dt <= end_dt:
                intervals.append((start_dt, end_dt))
            else:
                intervals.append((end_dt, start_dt))

    if intervals:
        exp_years = calculate_experience_from_intervals(intervals)
        return exp_years, 1.0

    # Fallback to explicit statement in text
    explicit = extract_explicit_experience_years(raw_text)
    if explicit is not None:
        return explicit, 0.85

    # Could not parse experience
    return 0.0, 0.5
