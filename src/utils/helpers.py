import unicodedata
import re
from datetime import datetime

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_header(header: str) -> str:
    if header is None:
        return ""
    normalized = unicodedata.normalize("NFD", header)
    ascii_only = "".join(c for c in normalized if not unicodedata.combining(c))
    return ascii_only.strip().lower().replace(" ", "_")


def normalize_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""

    candidates = [value]
    for separator in (" ", "T"):
        if separator in value:
            head = value.split(separator, 1)[0].strip()
            if head:
                candidates.append(head)

    for candidate in list(candidates):
        if len(candidate) >= 10:
            slice_ = candidate[:10]
            if len(slice_) == 10 and slice_[4] in ("-", "/", ".") and slice_ not in candidates:
                candidates.append(slice_)

    unique_candidates = []
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)

    for candidate in unique_candidates:
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            pass
        else:
            return dt.date().isoformat()

    patterns = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
    for candidate in unique_candidates:
        for pattern in patterns:
            try:
                dt = datetime.strptime(candidate, pattern)
            except ValueError:
                continue
            return dt.strftime("%Y-%m-%d")

    return value


def coerce_iso_date(value: str) -> str:
    if not value:
        return ""
    normalized = normalize_date(value)
    if normalized and ISO_DATE_PATTERN.match(normalized):
        return normalized
    return ""
