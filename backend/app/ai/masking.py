import re


def mask_personal_data(
    raw_text: str,
    candidate_name: str = "",
    candidate_email: str = "",
    candidate_phone: str = "",
) -> str:
    """Masks personal identifiers from CV text prior to AI scoring.

    Removes/replaces:
    - Name tokens
    - Email addresses
    - Phone numbers
    - Personal titles (Mr/Mrs/Ms/Dr)
    - Gendered pronouns (he/she/him/her/his/hers -> they/them/their)
    - Date of birth and age lines
    - Marital status lines
    - Father's/spouse name lines

    Preserves:
    - Employment history, company names, dates, skills, education, notice, location.
    """
    masked = raw_text

    # 1. Mask specific email if provided, then all email patterns
    if candidate_email:
        masked = re.sub(re.escape(candidate_email), "[EMAIL_REDACTED]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]", masked)

    # 2. Mask specific phone if provided, then phone patterns
    if candidate_phone:
        masked = re.sub(re.escape(candidate_phone), "[PHONE_REDACTED]", masked, flags=re.IGNORECASE)
    masked = re.sub(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", masked
    )

    # 3. Mask candidate name tokens (first name, last name) if length >= 3
    if candidate_name:
        for token in candidate_name.split():
            clean_token = re.sub(r"[^\w]", "", token)
            if len(clean_token) >= 3 and clean_token.lower() not in (
                "curriculum",
                "vitae",
                "resume",
            ):
                masked = re.sub(
                    rf"\b{re.escape(clean_token)}\b", "[NAME_REDACTED]", masked, flags=re.IGNORECASE
                )

    # 4. Remove personal honorifics / titles
    masked = re.sub(r"\b(Mr\.|Mrs\.|Ms\.|Miss\b|Dr\.)\s*", "", masked, flags=re.IGNORECASE)

    # 5. Mask DOB and Age lines
    masked = re.sub(
        r"(?i)\b(?:dob|date\s+of\s+birth|d\.o\.b)\s*[:=-]\s*[^\n]+", "[DOB_REDACTED]", masked
    )
    masked = re.sub(r"(?i)\bage\s*[:=-]\s*\d+\s*(?:years?|yrs?)?", "[AGE_REDACTED]", masked)

    # 6. Mask Marital status
    masked = re.sub(r"(?i)\bmarital\s+status\s*[:=-]\s*[^\n]+", "[MARITAL_STATUS_REDACTED]", masked)

    # 7. Mask Father's / Mother's / Spouse's name
    masked = re.sub(
        r"(?i)\b(?:father'?s|mother'?s|spouse'?s)\s+name\s*[:=-]\s*[^\n]+",
        "[RELATION_NAME_REDACTED]",
        masked,
    )

    # 8. Replace gendered pronouns with gender-neutral counterparts
    pronoun_map = [
        (r"\bhe\b", "they"),
        (r"\bshe\b", "they"),
        (r"\bhim\b", "them"),
        (r"\bher\b", "them"),
        (r"\bhis\b", "their"),
        (r"\bhers\b", "theirs"),
        (r"\bhimself\b", "themselves"),
        (r"\bherself\b", "themselves"),
    ]
    for pat, rep in pronoun_map:
        masked = re.sub(pat, rep, masked, flags=re.IGNORECASE)

    return masked
