import re
from html import unescape
from typing import Any
from urllib.parse import unquote, urlparse

KNOWN_BELGIAN_CITIES = [
    "Brussels", "Antwerp", "Ghent", "Leuven", "Mechelen", "Bruges", "Hasselt", "Namur",
    "Liege", "Charleroi", "Mons", "Aalst", "Kortrijk", "Ostend", "Genk", "Roeselare",
    "Duffel", "Zemst", "Etterbeek", "Ixelles", "Schaerbeek", "Uccle", "Anderlecht",
    "Jette", "Forest", "Molenbeek", "Woluwe", "Waterloo", "Vilvoorde", "Tervuren",
]

PROPERTY_TYPES = ["apartment", "house", "studio", "villa", "duplex", "penthouse", "land", "commercial"]
CONDITIONS = ["new", "renovated", "good", "average", "to renovate", "poor"]
AMENITIES = ["terrace", "garden", "balcony", "parking", "garage", "lift", "elevator", "furnished", "cellar"]

LABELS = {
    "price": ["price", "asking price", "sale price", "prijs", "vraagprijs", "prix", "prix demande"],
    "city": ["city", "gemeente", "ville", "locality", "location", "locatie", "adresse", "address"],
    "bedrooms": ["bedroom", "bedrooms", "slaapkamer", "slaapkamers", "chambre", "chambres"],
    "bathrooms": ["bathroom", "bathrooms", "badkamer", "badkamers", "salle de bain", "salles de bain"],
    "area_sqm": ["living area", "habitable surface", "surface habitable", "woonoppervlakte", "bewoonbare oppervlakte", "oppervlakte", "surface", "area"],
    "energy_score": ["epc", "peb", "energy score", "energy label", "energie score", "energielabel"],
    "property_type": ["property type", "type", "vastgoedtype", "type de bien"],
}


def extract_listing_text_data(text: str, source_url: str | None = None) -> dict[str, Any]:
    normalized = normalize_text(text)
    lines = normalized.splitlines()
    extracted: dict[str, Any] = {
        "source_url": source_url,
        "extraction_status": "partial",
        "extraction_method": "pasted_text",
        "extracted_fields": [],
        "missing_fields": [],
    }

    merge_url_fields(extracted, source_url)

    title = first_nonempty_line(text)
    if title:
        extracted["title"] = title[:180]

    extracted["price"] = find_price(normalized, lines)
    extracted["city"] = extracted.get("city") or find_city(normalized, lines)
    extracted["postcode"] = extracted.get("postcode") or find_postcode(normalized)
    extracted["property_type"] = extracted.get("property_type") or find_property_type(normalized, lines)
    extracted["bedrooms"] = find_labeled_number(lines, LABELS["bedrooms"]) or find_number(normalized, [
        r"(?:bedrooms?|slaapkamers?|chambres?)\s*[:\-]?\s*([0-9]+)",
        r"([0-9]+)\s*(?:bedrooms?|slaapkamers?|chambres?)",
    ])
    extracted["bathrooms"] = find_labeled_number(lines, LABELS["bathrooms"]) or find_number(normalized, [
        r"(?:bathrooms?|badkamers?|salles? de bains?)\s*[:\-]?\s*([0-9]+)",
        r"([0-9]+)\s*(?:bathrooms?|badkamers?|salles? de bains?)",
    ])
    extracted["area_sqm"] = find_labeled_number(lines, LABELS["area_sqm"]) or find_number(normalized, [
        r"(?:living area|habitable surface|surface habitable|woonoppervlakte|oppervlakte|surface|area)\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:m2|m²|sqm|sq m)?",
        r"([0-9]+(?:[.,][0-9]+)?)\s*(?:m2|m²|sqm|sq m)\b",
    ])
    extracted["energy_score"] = find_energy_score(normalized, lines)
    extracted["condition"] = find_condition(normalized)
    amenities = find_amenities(normalized)
    if amenities:
        extracted["amenities"] = amenities

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


def merge_url_fields(extracted: dict[str, Any], source_url: str | None) -> None:
    if not source_url:
        return
    path_parts = [unquote(part) for part in urlparse(source_url).path.split("/") if part]
    lowered = [part.lower() for part in path_parts]
    for kind in PROPERTY_TYPES:
        if kind in lowered and not extracted.get("property_type"):
            extracted["property_type"] = "house" if kind == "villa" else kind
    for index, part in enumerate(path_parts):
        if re.fullmatch(r"[1-9][0-9]{3}", part):
            extracted.setdefault("postcode", part)
            if index > 0:
                city = path_parts[index - 1].replace("-", " ").title()
                if city.lower() not in {"for sale", "for rent", "classified"}:
                    extracted.setdefault("city", city)
    if path_parts and path_parts[-1].isdigit():
        extracted.setdefault("listing_id", path_parts[-1])


def normalize_text(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def first_nonempty_line(text: str) -> str | None:
    for line in normalize_text(text).splitlines():
        clean = line.strip()
        if len(clean) >= 8 and not re.search(r"^(price|prijs|prix|€|eur|overview|details)\b", clean, re.I):
            return clean
    return None


def find_price(text: str, lines: list[str]) -> float | None:
    labeled = find_labeled_number(lines, LABELS["price"])
    if labeled and labeled >= 10000:
        return labeled
    patterns = [
        r"(?:price|asking price|sale price|prijs|prix)\s*[:\-]?\s*(?:€|eur)?\s*([0-9][0-9.\s,]{4,})",
        r"(?:€|eur)\s*([0-9][0-9.\s,]{4,})",
        r"([0-9][0-9.\s,]{4,})\s*(?:€|eur)",
    ]
    return find_number(text, patterns)


def find_city(text: str, lines: list[str]) -> str | None:
    for line in lines:
        location = parse_postcode_city(line)
        if location:
            return location[1]
    labeled = find_labeled_text(lines, LABELS["city"])
    if labeled:
        location = parse_postcode_city(labeled)
        if location:
            return location[1]
        return clean_label(labeled)
    for city in KNOWN_BELGIAN_CITIES:
        if re.search(rf"\b{re.escape(city)}\b", text, re.I):
            return city
    return None


def find_postcode(text: str) -> str | None:
    match = re.search(r"\b([1-9][0-9]{3})\b", text)
    return match.group(1) if match else None


def parse_postcode_city(value: str) -> tuple[str, str] | None:
    match = re.search(r"\b([1-9][0-9]{3})\b\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ'\- ]{2,40})", value)
    if not match:
        return None
    return match.group(1), clean_label(match.group(2))


def find_property_type(text: str, lines: list[str]) -> str | None:
    labeled = find_labeled_text(lines, LABELS["property_type"])
    haystack = f"{labeled or ''}\n{text}"
    for property_type in PROPERTY_TYPES:
        if re.search(rf"\b{property_type}\b", haystack, re.I):
            return "house" if property_type == "villa" else property_type
    return None


def find_energy_score(text: str, lines: list[str]) -> str | None:
    labeled = find_labeled_text(lines, LABELS["energy_score"])
    for value in [labeled, text]:
        if not value:
            continue
        match = re.search(r"\b(A\+|A|B|C|D|E|F|G)\b", value, re.I)
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


def find_labeled_number(lines: list[str], labels: list[str]) -> float | None:
    value = find_labeled_text(lines, labels)
    return as_number(value) if value else None


def find_labeled_text(lines: list[str], labels: list[str]) -> str | None:
    normalized_labels = [normalize_label(label) for label in labels]
    for index, line in enumerate(lines):
        compact = normalize_label(line)
        for label in normalized_labels:
            if compact == label or compact.startswith(label + ":") or compact.startswith(label + " "):
                inline = re.sub(rf"^{re.escape(line.split(':', 1)[0])}:?", "", line, flags=re.I).strip()
                if inline and normalize_label(inline) != label:
                    return inline
                for next_line in lines[index + 1 : index + 4]:
                    if next_line and not is_label_only(next_line):
                        return next_line
    return None


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def is_label_only(value: str) -> bool:
    compact = normalize_label(value)
    return any(compact == normalize_label(label) for group in LABELS.values() for label in group)


def find_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return as_number(match.group(1))
    return None


def as_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9.,]", "", str(value))
    if not cleaned:
        return None
    if "," in cleaned and cleaned.rfind(",") > cleaned.rfind("."):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1 or ("." in cleaned and len(cleaned.split(".")[-1]) == 3):
        cleaned = cleaned.replace(".", "").replace(",", "")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def clean_label(value: str) -> str:
    value = re.split(r"\s{2,}|\n|,|\|", value.strip())[0]
    return value.strip(" -:;.")
