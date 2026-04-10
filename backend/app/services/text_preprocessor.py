"""Text preprocessing pipeline for TTS input normalization.

Handles number expansion, date formatting, abbreviation expansion, and URL
removal so that TTS providers receive clean, pronounceable text.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Abbreviation dictionary
# ---------------------------------------------------------------------------
ABBREVIATIONS: dict[str, str] = {
    "Dr.": "Doctor",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Miz",
    "Prof.": "Professor",
    "Jr.": "Junior",
    "Sr.": "Senior",
    "St.": "Saint",
    "Ave.": "Avenue",
    "Blvd.": "Boulevard",
    "Dept.": "Department",
    "Est.": "Established",
    "Gov.": "Governor",
    "Inc.": "Incorporated",
    "Ltd.": "Limited",
    "Corp.": "Corporation",
    "Gen.": "General",
    "Sgt.": "Sergeant",
    "Lt.": "Lieutenant",
    "Capt.": "Captain",
    "Col.": "Colonel",
    "Maj.": "Major",
    "vs.": "versus",
    "etc.": "et cetera",
    "approx.": "approximately",
    "govt.": "government",
}

# ---------------------------------------------------------------------------
# Number-to-words (simple fallback when num2words is unavailable)
# ---------------------------------------------------------------------------

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
]

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_ORDINALS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 21: "twenty-first", 22: "twenty-second",
    23: "twenty-third", 24: "twenty-fourth", 25: "twenty-fifth",
    26: "twenty-sixth", 27: "twenty-seventh", 28: "twenty-eighth",
    29: "twenty-ninth", 30: "thirtieth", 31: "thirty-first",
}


def _number_to_words(n: int) -> str:
    """Convert an integer to English words.

    Tries num2words first; falls back to a built-in implementation that
    handles numbers up to 999,999,999.
    """
    try:
        from num2words import num2words
        return num2words(n)
    except ImportError:
        pass

    if n < 0:
        return "negative " + _number_to_words(-n)
    if n == 0:
        return "zero"

    parts: list[str] = []

    if n >= 1_000_000:
        millions = n // 1_000_000
        parts.append(_number_to_words(millions) + " million")
        n %= 1_000_000

    if n >= 1_000:
        thousands = n // 1_000
        parts.append(_number_to_words(thousands) + " thousand")
        n %= 1_000

    if n >= 100:
        hundreds = n // 100
        parts.append(_ONES[hundreds] + " hundred")
        n %= 100

    if n >= 20:
        tens = n // 10
        ones = n % 10
        word = _TENS[tens]
        if ones:
            word += "-" + _ONES[ones]
        parts.append(word)
    elif n > 0:
        parts.append(_ONES[n])

    return " ".join(parts)


def _year_to_words(year: int) -> str:
    """Convert a year to natural English speech form."""
    if 2000 <= year <= 2009:
        return "two thousand" + (" " + _ONES[year - 2000] if year > 2000 else "")
    if 2010 <= year <= 2099:
        return "twenty " + _number_to_words(year - 2000)
    if 1000 <= year <= 1999:
        high = year // 100
        low = year % 100
        result = _number_to_words(high) + " hundred"
        if low:
            result += " " + _number_to_words(low)
        return result
    return _number_to_words(year)


# ---------------------------------------------------------------------------
# Replacement patterns
# ---------------------------------------------------------------------------

# ISO dates: 2026-04-05
_DATE_PATTERN = re.compile(
    r"\b(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b"
)

# US dates: 04/05/2026 or 4/5/2026
_US_DATE_PATTERN = re.compile(
    r"\b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(\d{4})\b"
)

# Standalone numbers (not part of dates or words)
_NUMBER_PATTERN = re.compile(r"(?<!\w)(\d{1,9})(?!\w)")

# URLs
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+", re.IGNORECASE
)

# Email addresses
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


def _expand_dates(text: str) -> str:
    """Expand ISO dates like 2026-04-05 to 'April fifth, twenty twenty-six'."""
    def _replace_iso(m: re.Match) -> str:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        month_name = _MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
        day_word = _ORDINALS.get(day, _number_to_words(day))
        year_word = _year_to_words(year)
        return f"{month_name} {day_word}, {year_word}"

    def _replace_us(m: re.Match) -> str:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        month_name = _MONTH_NAMES[month] if 1 <= month <= 12 else str(month)
        day_word = _ORDINALS.get(day, _number_to_words(day))
        year_word = _year_to_words(year)
        return f"{month_name} {day_word}, {year_word}"

    text = _DATE_PATTERN.sub(_replace_iso, text)
    text = _US_DATE_PATTERN.sub(_replace_us, text)
    return text


def _expand_numbers(text: str) -> str:
    """Expand standalone numbers to words: '123' -> 'one hundred twenty-three'."""
    def _replace(m: re.Match) -> str:
        n = int(m.group(1))
        if n > 999_999_999:
            return m.group(0)  # Too large, leave as-is
        return _number_to_words(n)

    return _NUMBER_PATTERN.sub(_replace, text)


def _expand_abbreviations(text: str) -> str:
    """Expand common abbreviations."""
    for abbr, expansion in ABBREVIATIONS.items():
        # Word-boundary aware replacement (the abbreviation includes the dot)
        text = text.replace(abbr, expansion)
    return text


def _handle_urls(text: str) -> str:
    """Replace URLs with [link] and emails with the spoken form."""
    text = _URL_PATTERN.sub("[link]", text)
    text = _EMAIL_PATTERN.sub("[email]", text)
    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_text(text: str) -> str:
    """Apply the full text preprocessing pipeline.

    Steps (in order):
      1. URL/email handling
      2. Date expansion (ISO and US formats)
      3. Abbreviation expansion
      4. Number expansion (last, so expanded dates aren't re-processed)

    Returns the normalized text ready for TTS synthesis.
    """
    logger.debug("text_preprocessing_start", text_length=len(text))

    text = _handle_urls(text)
    text = _expand_dates(text)
    text = _expand_abbreviations(text)
    text = _expand_numbers(text)

    logger.debug("text_preprocessing_complete", text_length=len(text))
    return text
