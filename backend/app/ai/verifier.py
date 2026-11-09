import re


def normalise_for_verification(text: str) -> str:
    """Normalises text for quote verification: lowercases, strips punctuation, collapses whitespace."""
    if not text:
        return ""
    # Replace non-alphanumeric with spaces, collapse whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def verify_quote(quote: str | None, masked_text: str) -> bool:
    """Verifies that the provided quote actually exists in the masked CV text.

    Uses normalized substring matching to be tolerant of line breaks, tabs,
    and slight spacing differences while ensuring the text was not hallucinated.
    """
    if not quote or not quote.strip():
        return False

    norm_quote = normalise_for_verification(quote)
    if not norm_quote:
        return False

    norm_masked = normalise_for_verification(masked_text)
    return norm_quote in norm_masked
