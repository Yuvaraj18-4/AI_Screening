import re


def normalise_notice_period(notice_raw: str | int | None, full_text: str = "") -> int:
    """Normalises notice period into integer days."""
    text_to_check = str(notice_raw or "").lower().strip()
    if not text_to_check and full_text:
        text_to_check = full_text.lower()

    if not text_to_check:
        return 30

    if "immediate" in text_to_check:
        return 0

    if "serving notice" in text_to_check:
        return 15

    # Check for days: e.g. "30 days", "60 days", "90 days"
    day_match = re.search(r"(\d+)\s*days?", text_to_check)
    if day_match:
        return int(day_match.group(1))

    # Check for months: e.g. "1 month", "2 months", "3 months"
    month_match = re.search(r"(\d+)\s*(?:months?|mon\b)", text_to_check)
    if month_match:
        return int(month_match.group(1)) * 30

    word_months = {
        "one": 30,
        "two": 60,
        "three": 90,
    }
    for word, days in word_months.items():
        if f"{word} month" in text_to_check:
            return days

    # Check pure number
    if text_to_check.isdigit():
        val = int(text_to_check)
        if val <= 6:
            return val * 30  # Assume months if small number like 1, 2, 3
        return val

    # Default fallback
    return 30
