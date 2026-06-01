import re
from html import unescape
from typing import Any

KNOWN_BELGIAN_CITIES = [
    "Brussels", "Antwerp", "Ghent", "Leuven", "Mechelen", "Bruges", "Hasselt", "Namur",
    "Liege", "Charleroi", "Mons", "Aalst", "Kortrijk", "Ostend", "Genk", "Roeselare",
    "Duffel", "Zemst", "Etterbeek", "Ixelles", "Schaerbeek", "Uccle", "Anderlecht",
]

PROPERTY_TYPES = ["apartment", "house", "studio", "villa", "duplex", "penthouse", "land", "commercial"]
CONDITIONS = ["new", "renovated", "good", "average", "to renovate", "poor"]
AMENITIES = ["terrace", "garden", "balcony", "parking", "garage", "lift", "elevator", "furnished", "cellar"]


def extract_listing_text_data(text: str, source_url: str | None = None) -> dict[str, Any]:
    normalized = normalize_text(text)
    extracted: dict[str, Any] = {
        "source_url": source_url,
        "extraction_status": "partial",
        "extraction_method": "pasted_text",
        "extracted_fields": [],
        "missing_fields": [],
    }

    title = first_nonempty_line(text)
    if title:
        extracted["title"] = title[:180]

    extracted["price"] = find_price(normalized)
    extracted["city"] = find_city(normalized)
    extracted["postcode"] = find_postcode(normalized)
    extracted["property_type"] = find_property_type(normalized)
    extracted["bedrooms"] = find_number(normalized, [
        r"(?:bedrooms?|slaapkamers?|chambres?)\s*[:\-]?\s*([0-9]+)",
        r"([0-9]+)\s*(?:bedrooms?|slaapkamers?|chambres?)",
    ])
    extracted["bathrooms"] = find_number(normalized, [
        r"(?:bathrooms?|badkamers?|salles? de bains?)\s*[:\-]?\s*([0-9]+)",
        r"([0-9]+)\s*(?:bathrooms?|badkamers?|salles? de bains?)",
    ])
    extracted["area_sqm"] = find_number(normalized, [
        r"(?:living area|habitable surface|surface habitable|woonoppervlakte|oppervlakte|surface|area)\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:m2|m²|sqm|sq m)?",
        r"([0-9]+(?:[.,][0-9]+)?)\s*(?:m2|m²|sqm|sq m)\b",
    ])
    extracted["energy_score"] = find_energy_score(normalized)
    extracted["condition"] = find_condition(normalized)
    amenities = find_amenities(normalized)
    if amenities:
        extracted["amenities"] = amenities

    # Mirror backend ROI field names so the frontend form can use the same keys directly.
    if extracted.get("price"):
        extracted["purchase_price"] = extracted["price"]

    expected_fields = ["price", "city", "postcode", "property_type", "bedrooms", "bathrooms", "area_sqm", "energy_score"]
    extracted_fields = [field for field in expected_fields if extracted.get(field) not in (None, "", [])]
    missing_fields = [field for field in expected_fields if field not in extracted_fields]
    extracted["extracted_fields"] = extracted_fields
    extracted["missing_fields"] = missing_fields
    extracted["extraction_confidence"] = round(len(extracted_fields) / len(expected_fields), 2)
    extracted["extraction_status"] = "success" if not missing_fields else "partial"
    return {key: value for key, value in extracted.items() if value not in (None, "", [])}


def normalize_text(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\u00a0", " ")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def first_nonempty_line(text: str) -> str | None:
    for line in normalize_text(text).splitlines():
        clean = line.strip()
        if len(clean) >= 8 and not re.search(r"^(price|prijs|prix|€|eur)\b", clean, re.I):
            return clean
    return None


def find_price(text: str) -> float | None:
    patterns = [
        r"(?:price|asking price|sale price|prijs|prix)\s*[:\-]?\s*(?:€|eur)?\s*([0-9][0-9.\s,]{4,})",
        r"(?:€|eur)\s*([0-9][0-9.\s,]{4,})",
        r"([0-9][0-9.\s,]{4,})\s*(?:€|eur)",
    ]
    return find_number(text, patterns)


def find_city(text: str) -> str | None:
    postcode = find_postcode(text)
    if postcode:
        match = re.search(rf"\b{postcode}\b\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ'\- ]{{2,40}})", text)
        if match:
            return clean_label(match.group(1))
    for city in KNOWN_BELGIAN_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", text, re.I):
            return city
    match = re.search(r"(?:city|gemeente|ville|locality)\s*[:\-]?\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ'\- ]{2,40})", text, re.I)
    return clean_label(match.group(1)) if match else None


def find_postcode(text: str) -> str | None:
    match = re.search(r"\b([1-9][0-9]{3})\b", text)
    return match.group(1) if match else None


def find_property_type(text: str) -> str | None:
    for property_type in PROPERTY_TYPES:
        if re.search(rf"\b{property_type}\b", text, re.I):
            return "house" if property_type == "villa" else property_type
    return None


def find_energy_score(text: str) -> str | None:
    patterns = [
        r"(?:epc|peb|energy score|energy label|energie score|energielabel)\s*[:\-]?\s*([A-G][+]?)\b",
        r"\b([A-G][+]?)\s*(?:epc|peb|energy label|energielabel)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).upper()
    return None


def find_condition(text: str) -> str | None:
    for condition in CONDITIONS:
        if re.search(rf"\b{re.escape(condition)}\b", text, re.I):
            return "renovated" if condition == "good" else condition
    return None


def find_amenities(text: str) -> list[str]:
    found = []
    for amenity in AMENITIES:
        if re.search(rf"\b{re.escape(amenity)}\b", text, re.I):
            found.append("lift" if amenity == "elevator" else amenity)
    return sorted(set(found))


def find_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return as_number(match.group(1))
    return None


def as_number(value: str) -> float | None:
    cleaned = re.sub(r"[^0-9.,]", "", str(value))
    if not cleaned:
        return None
    if cleaned.count(",") == 1 and cleaned.rfind(",") > cleaned.rfind("."):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "").replace(".", "") if len(cleaned.split(".")[-1]) == 3 else cleaned.replace(",", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def clean_label(value: str) -> str:
    value = re.split(r"\s{2,}|\n|,|\|", value.strip())[0]
    return value.strip(" -:;.")
