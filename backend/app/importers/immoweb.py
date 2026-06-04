import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

from app.analysis import estimate_monthly_rent, rent_rate_for_location


class JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_json_ld = False
        self._buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attr_map = {name.lower(): value for name, value in attrs}
        if attr_map.get("type") == "application/ld+json":
            self._inside_json_ld = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside_json_ld:
            self.blocks.append("".join(self._buffer))
            self._inside_json_ld = False
            self._buffer = []


def import_immoweb_listing(url: str) -> dict[str, Any]:
    try:
        html = fetch_listing_html(url)
        extracted = extract_immoweb_listing(html, url)
    except Exception as exc:
        extracted = extract_immoweb_listing("", url)
        extracted["direct_fetch_error"] = str(exc)[:300]
    if needs_search_fallback(extracted):
        try:
            fallback_html = fetch_search_fallback_html(url, extracted)
            fallback = extract_immoweb_listing(fallback_html, url)
            fallback["extraction_method"] = "immoweb_search_fallback"
            merge_missing_fields(extracted, fallback)
        except Exception as exc:
            extracted["search_fallback_error"] = str(exc)[:300]
    return finalize_extraction(extracted)


def fetch_listing_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,nl;q=0.8,fr;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Referer": "https://www.immoweb.be/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def extract_immoweb_listing(html: str, source_url: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {
        "source_url": source_url,
        "extraction_status": "partial",
        "extracted_fields": [],
        "missing_fields": [],
    }

    merge_url_fields(extracted, source_url)

    json_objects = extract_json_ld(html)
    for item in json_objects:
        merge_json_ld_fields(extracted, item)

    listing_objects = extract_embedded_listing_objects(html)
    for item in listing_objects:
        merge_listing_object_fields(extracted, item)

    merge_raw_json_patterns(extracted, html)
    merge_regex_fields(extracted, html)

    return finalize_extraction(extracted)


EXPECTED_FIELDS = ["price", "city", "postcode", "property_type", "bedrooms", "bathrooms", "area_sqm", "energy_score"]
PRICE_NUMBER = r"([1-9][0-9]{4,8}|[1-9][0-9]{0,2}(?:[. ,\u00a0][0-9]{3})+)"


def finalize_extraction(extracted: dict[str, Any]) -> dict[str, Any]:
    if extracted.get("price") and not extracted.get("purchase_price"):
        extracted["purchase_price"] = extracted["price"]
    add_default_assumptions(extracted)
    add_estimated_rent(extracted)
    extracted_fields = [field for field in EXPECTED_FIELDS if extracted.get(field) not in (None, "", [])]
    missing_fields = [field for field in EXPECTED_FIELDS if field not in extracted_fields]
    extracted["extracted_fields"] = extracted_fields
    extracted["missing_fields"] = missing_fields
    extracted["extraction_confidence"] = round(len(extracted_fields) / len(EXPECTED_FIELDS), 2)
    extracted["extraction_status"] = "success" if not missing_fields else "partial"
    return {key: value for key, value in extracted.items() if value not in (None, "", [])}


def add_default_assumptions(extracted: dict[str, Any]) -> None:
    purchase_price = as_number(extracted.get("purchase_price") or extracted.get("price")) or 0
    area_sqm = as_number(extracted.get("area_sqm")) or 0
    condition = str(extracted.get("condition") or "").strip().lower()

    if purchase_price > 0 and not extracted.get("purchase_costs"):
        extracted["purchase_costs"] = round(purchase_price * 0.12, 2)
    if area_sqm > 0 and not extracted.get("renovation_cost"):
        cost_per_sqm = {
            "poor": 900,
            "to renovate": 900,
            "average": 350,
            "good": 200,
            "renovated": 75,
            "new": 0,
        }.get(condition, 250)
        extracted["renovation_cost"] = round(area_sqm * cost_per_sqm, 2)
    if area_sqm > 0 and not extracted.get("annual_operating_costs"):
        rent_per_sqm, _ = rent_rate_for_location(extracted.get("city"), extracted.get("postcode"))
        estimated_annual_rent = area_sqm * rent_per_sqm * 12
        extracted["annual_operating_costs"] = round(max(estimated_annual_rent * 0.15, 1200), 2)
    if purchase_price > 0 and not extracted.get("down_payment"):
        extracted["down_payment"] = round(purchase_price * 0.2, 2)
    extracted.setdefault("interest_rate", 3.5)
    extracted.setdefault("loan_years", 25)
    extracted.setdefault("vacancy_rate", 0.05)


def add_estimated_rent(extracted: dict[str, Any]) -> None:
    if extracted.get("monthly_rent") or extracted.get("estimated_rent"):
        return
    rent_estimate = estimate_monthly_rent(extracted)
    if rent_estimate.monthly_rent > 0:
        extracted["monthly_rent"] = rent_estimate.monthly_rent
        extracted["estimated_rent"] = rent_estimate.monthly_rent
        extracted["rent_estimation_explanation"] = rent_estimate.explanation


def needs_search_fallback(extracted: dict[str, Any]) -> bool:
    return any(extracted.get(field) in (None, "", []) for field in ["price", "bedrooms", "area_sqm"])


def merge_missing_fields(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key in {"source_url", "extracted_fields", "missing_fields", "extraction_confidence", "extraction_status"}:
            continue
        if target.get(key) in (None, "", []) and value not in (None, "", []):
            target[key] = value


def fetch_search_fallback_html(source_url: str, extracted: dict[str, Any]) -> str:
    parts = [unquote(part) for part in urlparse(source_url).path.split("/") if part]
    language = parts[0] if parts and parts[0] in {"en", "nl", "fr"} else "en"
    property_type = str(extracted.get("property_type") or "apartment").lower()
    if property_type == "huis":
        property_type = "house"
    city = str(extracted.get("city") or "").lower().replace(" ", "-")
    postcode = str(extracted.get("postcode") or "")
    location = f"{quote(city)}/{postcode}" if city and postcode else quote(city or postcode)
    if not location:
        raise ValueError("Not enough listing location data for search fallback.")
    search_url = f"https://www.immoweb.be/{language}/search/{property_type}/for-sale/{location}"
    return fetch_listing_html(search_url)


def merge_url_fields(extracted: dict[str, Any], source_url: str) -> None:
    path_parts = [unquote(part) for part in urlparse(source_url).path.split("/") if part]
    if not path_parts:
        return

    lowered = [part.lower() for part in path_parts]
    type_aliases = {
        "apartment": "apartment",
        "appartement": "apartment",
        "flat": "apartment",
        "house": "house",
        "huis": "house",
        "maison": "house",
        "villa": "house",
        "studio": "studio",
        "duplex": "duplex",
        "penthouse": "penthouse",
        "land": "land",
        "terrain": "land",
    }
    for slug, property_type in type_aliases.items():
        if slug in lowered and not extracted.get("property_type"):
            extracted["property_type"] = property_type

    if any(part in lowered for part in ["for-sale", "te-koop", "a-vendre", "à-vendre"]):
        extracted.setdefault("listing_type", "sale")
    elif any(part in lowered for part in ["for-rent", "te-huur", "a-louer", "à-louer"]):
        extracted.setdefault("listing_type", "rent")

    for index, part in enumerate(path_parts):
        if re.fullmatch(r"[1-9][0-9]{3}", part):
            extracted.setdefault("postcode", part)
            if index > 0:
                city = path_parts[index - 1].replace("-", " ").title()
                if city.lower() not in {"for sale", "for rent", "te koop", "te huur", "a vendre", "a louer", "classified"}:
                    extracted.setdefault("city", city)

    if path_parts and path_parts[-1].isdigit():
        extracted.setdefault("listing_id", path_parts[-1])


def extract_json_ld(html: str) -> list[dict[str, Any]]:
    parser = JsonLdParser()
    parser.feed(html)
    objects: list[dict[str, Any]] = []
    for block in parser.blocks:
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        objects.extend(flatten_json_ld(parsed))
    return objects


def flatten_json_ld(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        result: list[dict[str, Any]] = []
        for item in value:
            result.extend(flatten_json_ld(item))
        return result
    if isinstance(value, dict):
        graph = value.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [value]
    return []


def extract_embedded_listing_objects(html: str) -> list[dict[str, Any]]:
    objects = []
    for script in extract_script_json_candidates(html):
        for candidate in extract_json_candidates_from_text(script):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            objects.extend(find_listing_like_objects(parsed))
    return objects


def extract_script_json_candidates(html: str) -> list[str]:
    candidates = []
    next_data_match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    )
    if next_data_match:
        candidates.append(unescape(next_data_match.group(1)).strip())

    for match in re.finditer(r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>", html, re.I | re.S):
        candidates.append(match.group(1).strip())

    for match in re.finditer(r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.I | re.S):
        value = unescape(match.group(1)).strip()
        if value.startswith(("{", "[")):
            candidates.append(value)

    for match in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.I | re.S):
        script = unescape(match.group(1)).strip()
        if script and any(token in script.lower() for token in ["classified", "price", "mainvalue", "bedroom", "surface"]):
            candidates.append(script)

    return candidates


def extract_json_candidates_from_text(text: str) -> list[str]:
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        return [stripped]

    candidates: list[str] = []
    normalized = normalize_raw_page_text(text)
    for keyword in ["classified", "property", "realEstate", "initialState", "mainValue", "transaction"]:
        for match in re.finditer(re.escape(keyword), normalized, re.I):
            for opener in ["{", "["]:
                start = normalized.find(opener, match.end())
                if start == -1:
                    continue
                candidate = read_balanced_json(normalized, start)
                if candidate:
                    candidates.append(candidate)
    return candidates


def read_balanced_json(text: str, start: int) -> str | None:
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    quote = ""
    escape = False
    for index in range(start, min(len(text), start + 2_000_000)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                in_string = False
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                candidate = text[start : index + 1]
                return candidate.replace("'", '"') if '"' not in candidate and "'" in candidate else candidate
    return None


def find_listing_like_objects(value: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(value, dict):
        keys = {normalize_key(key) for key in value}
        if keys & {"price", "bedroomcount", "bedrooms", "roomcount", "surface", "livablesurface", "nethabitablesurface"}:
            found.append(value)
        for child in value.values():
            found.extend(find_listing_like_objects(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_listing_like_objects(child))
    return found


def merge_raw_json_patterns(extracted: dict[str, Any], html: str) -> None:
    # Immoweb changes its client-side framework often. These patterns catch the
    # stable field names when the page exposes data inside escaped JSON strings.
    raw = normalize_raw_page_text(html)
    raw_patterns = {
        "price": [
            r'(?:window\.)?classified\s*=\s*\{[\s\S]{0,2000}(?:["\']?price["\']?\s*:\s*\{[\s\S]{0,500}["\']?mainValue["\']?\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?)',
            r'["\']?price["\']?\s*:\s*\{[^{}]{0,800}["\']?(?:mainValue|value|amount)["\']?\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?',
            r'"price"\s*:\s*\{[^{}]{0,800}"(?:mainValue|value|amount)"\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?',
            r'["\']?(?:mainValue|salePrice|transactionPrice|askingPrice)["\']?\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?',
            r'"(?:mainValue|salePrice|transactionPrice|askingPrice|amount)"\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?[^{}]{0,120}"(?:EUR|€)"',
            r'"(?:mainValue|salePrice|transactionPrice|askingPrice)"\s*:\s*"?([0-9][0-9. ,\u00a0]{4,})"?',
            r'"(?:formattedPrice|priceFormatted|priceLabel|displayPrice)"\s*:\s*"[^"]*(?:EUR|€)\s*([0-9][0-9. ,\u00a0]{4,})',
            r'"(?:price|prix|prijs)"\s*:\s*"[^"]*(?:EUR|€)\s*([0-9][0-9. ,\u00a0]{4,})',
        ],
        "bedrooms": [
            r'["\']?(?:bedroomCount|numberOfBedrooms|bedrooms)["\']?\s*:\s*([0-9]+)',
            r'"(?:bedroomCount|numberOfBedrooms|bedrooms)"\s*:\s*([0-9]+)',
        ],
        "bathrooms": [
            r'["\']?(?:bathroomCount|numberOfBathrooms|bathrooms)["\']?\s*:\s*([0-9]+)',
            r'"(?:bathroomCount|numberOfBathrooms|bathrooms)"\s*:\s*([0-9]+)',
        ],
        "area_sqm": [
            r'["\']?(?:netHabitableSurface|habitableSurface|livingArea|surface)["\']?\s*:\s*(?:\{["\']?value["\']?\s*:\s*)?([0-9]{2,4})',
            r'"(?:netHabitableSurface|habitableSurface|livingArea|surface)"\s*:\s*(?:\{"value"\s*:\s*)?([0-9]{2,4})',
        ],
    }
    for field, patterns in raw_patterns.items():
        if extracted.get(field) not in (None, "", []):
            continue
        value = first_number_match(raw, patterns)
        if value not in (None, "", []):
            extracted[field] = value

    text_patterns = {
        "city": [
            r'["\']?(?:locality|city|municipality)["\']?\s*:\s*["\']([^"\']{2,80})["\']',
            r'"(?:locality|city|municipality)"\s*:\s*"([^"]{2,80})"',
        ],
        "postcode": [
            r'["\']?(?:postalCode|postcode|zip)["\']?\s*:\s*["\']?(1[0-9]{3}|[2-9][0-9]{3})["\']?',
            r'"(?:postalCode|postcode|zip)"\s*:\s*"?(1[0-9]{3}|[2-9][0-9]{3})"?',
        ],
        "energy_score": [
            r'["\']?(?:epcScore|energyScore|energyClass|peb)["\']?\s*:\s*["\']?([A-G]\+?)["\']?',
            r'"(?:epcScore|energyScore|energyClass|peb)"\s*:\s*"?([A-G]\+?)"?',
        ],
    }
    for field, patterns in text_patterns.items():
        if extracted.get(field) not in (None, "", []):
            continue
        for pattern in patterns:
            match = re.search(pattern, raw, re.I)
            if match:
                extracted[field] = unescape(match.group(1)).strip()
                break


def normalize_raw_page_text(html: str) -> str:
    variants = [unescape(html)]
    variants.append(variants[0].replace('\\"', '"').replace("\\u0022", '"').replace("\\u20ac", "€"))

    for match in re.finditer(r'"((?:\\.|[^"\\]){20,})"', html, re.S):
        chunk = match.group(1)
        if not any(token in chunk.lower() for token in ["price", "mainvalue", "bedroom", "surface", "classified"]):
            continue
        try:
            decoded = json.loads(f'"{chunk}"')
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, str):
            variants.append(unescape(decoded).replace('\\"', '"').replace("\\u0022", '"').replace("\\u20ac", "€"))

    unique = list(dict.fromkeys(variants))
    return "\n".join(unique)


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def merge_json_ld_fields(extracted: dict[str, Any], item: dict[str, Any]) -> None:
    address = item.get("address")
    offers = item.get("offers")

    if not extracted.get("title"):
        extracted["title"] = item.get("name") or item.get("headline")
    if not extracted.get("description"):
        extracted["description"] = strip_html(item.get("description"))
    if isinstance(address, dict):
        extracted.setdefault("city", address.get("addressLocality"))
        extracted.setdefault("postcode", address.get("postalCode"))
        extracted.setdefault("address", address.get("streetAddress"))
        extracted.setdefault("country", address.get("addressCountry"))
    if isinstance(offers, dict):
        extracted.setdefault("price", as_number(offers.get("price")))
        extracted.setdefault("currency", offers.get("priceCurrency"))

    image = item.get("image")
    if image and not extracted.get("images"):
        extracted["images"] = normalize_images(image)


def merge_listing_object_fields(extracted: dict[str, Any], item: dict[str, Any]) -> None:
    field_map = flatten_mapping(item)

    set_first(extracted, field_map, "title", ["title", "name"])
    set_first(extracted, field_map, "price", ["price", "mainprice", "saleprice", "transactionprice"])
    set_first(extracted, field_map, "currency", ["currency", "pricecurrency"])
    set_first(extracted, field_map, "city", ["locality", "city", "municipality", "addresslocality"])
    set_first(extracted, field_map, "postcode", ["postalcode", "postcode", "zip"])
    set_first(extracted, field_map, "address", ["street", "streetaddress", "address"])
    set_first(extracted, field_map, "property_type", ["propertytype", "type", "subtype"])
    set_first(extracted, field_map, "bedrooms", ["bedroomcount", "bedrooms", "numberofbedrooms"])
    set_first(extracted, field_map, "bathrooms", ["bathroomcount", "bathrooms", "numberofbathrooms"])
    set_first(
        extracted,
        field_map,
        "area_sqm",
        ["livablesurface", "netHabitablesurface", "habitableSurface", "surface", "area", "size"],
    )
    set_first(extracted, field_map, "energy_score", ["epcscore", "energyscore", "energyclass", "peb"])
    set_first(extracted, field_map, "condition", ["condition", "buildingcondition", "renovationlevel"])

    if not extracted.get("images"):
        images = collect_image_urls(item)
        if images:
            extracted["images"] = images


def flatten_mapping(value: Any, prefix: str = "") -> dict[str, Any]:
    flattened = {}
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = normalize_key(key)
            if child not in (None, "", []):
                flattened.setdefault(normalized, child)
            if isinstance(child, (dict, list)):
                flattened.update(flatten_mapping(child, normalized))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                flattened.update(flatten_mapping(child, prefix))
    return flattened


def set_first(extracted: dict[str, Any], field_map: dict[str, Any], target: str, keys: list[str]) -> None:
    if extracted.get(target) not in (None, "", []):
        return
    for key in keys:
        value = field_map.get(normalize_key(key))
        normalized_value = normalize_value(target, value)
        if normalized_value not in (None, "", []):
            extracted[target] = normalized_value
            return


def normalize_value(target: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ["value", "amount", "mainValue", "label", "name"]:
            if key in value:
                return normalize_value(target, value[key])
        return None
    if isinstance(value, list):
        return None
    if target in {"price", "bedrooms", "bathrooms", "area_sqm"}:
        return as_number(value)
    if target == "energy_score":
        match = re.search(r"\b(A\+|A|B|C|D|E|F|G)\b", str(value), re.I)
        return match.group(1).upper() if match else None
    return str(value).strip()


def collect_image_urls(value: Any) -> list[str]:
    urls = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = normalize_key(key)
            if normalized_key in {"url", "src", "smallurl", "mediumurl", "largeurl"} and isinstance(child, str):
                if child.startswith("http") and child not in urls:
                    urls.append(child)
            elif isinstance(child, (dict, list)):
                urls.extend(url for url in collect_image_urls(child) if url not in urls)
    elif isinstance(value, list):
        for child in value:
            urls.extend(url for url in collect_image_urls(child) if url not in urls)
    return urls[:12]


def merge_regex_fields(extracted: dict[str, Any], html: str) -> None:
    text = unescape(strip_html(html))
    compact = " ".join(text.split())

    if not extracted.get("price"):
        extracted["price"] = first_number_match(
            compact,
            [
                r"(?:Price|Asking price|Sale price|Prijs|Vraagprijs|Prix|Prix demandé)\s*(?:EUR|\u20ac)?\s*([0-9][0-9. ,\u00a0]*)",
                r"(?:EUR|\u20ac)\s*([0-9][0-9. ,\u00a0]*)\s*(?:asking|sale|price)",
                r"\b([1-9][0-9. ,\u00a0]{4,})\s*(?:EUR|\u20ac)",
                r"(?:EUR|\u20ac)\s*([1-9][0-9. ,\u00a0]{4,})\b",
            ],
        )
    if not extracted.get("bedrooms"):
        extracted["bedrooms"] = first_number_match(
            compact,
            [
                r"(?:Bedrooms?|Bedroom\(s\)|Slaapkamers?|Chambres?)\s*[:\-]?\s*([0-9]+)\b(?!\s*(?:m2|m\u00b2|sqm))",
                r"([0-9]+)\s*(?:bedrooms?|slaapkamers?|chambres?)\b",
            ],
        )
    if not extracted.get("bathrooms"):
        extracted["bathrooms"] = first_number_match(
            compact,
            [
                r"(?:Bathrooms?|Bathroom\(s\)|Badkamers?|Salles? de bains?)\s*[:\-]?\s*([0-9]+)\b(?!\s*(?:m2|m\u00b2|sqm))",
                r"([0-9]+)\s*(?:bathrooms?|badkamers?|salles? de bains?)\b",
            ],
        )
    if not extracted.get("area_sqm"):
        extracted["area_sqm"] = first_number_match(
            compact,
            [
                r"(?:Living area|Habitable surface|Surface habitable|Woonoppervlakte|Bewoonbare oppervlakte|Surface|Area|Oppervlakte)\s*([0-9]+)\s*(?:m2|m\u00b2|sqm)",
                r"\b([1-9][0-9]{1,3})\s*(?:m2|m\u00b2|sqm)\b",
            ],
        )

    energy_match = re.search(
        r"\bEPC\b[^A-G+]*([A-G][+]?)\b|\bPEB\b[^A-G+]*([A-G][+]?)\b|\bEnergy score\b[^A-G+]*([A-G][+]?)\b",
        compact,
        re.I,
    )
    if energy_match and not extracted.get("energy_score"):
        extracted["energy_score"] = next(group for group in energy_match.groups() if group).upper()

    if not extracted.get("property_type"):
        for property_type in ["apartment", "house", "studio", "land", "commercial"]:
            if re.search(rf"\b{property_type}\b", compact, re.I):
                extracted["property_type"] = property_type
                break


def normalize_images(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, dict):
        url = value.get("url")
        return [url] if isinstance(url, str) else []
    return []


def first_number_match(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return as_number(match.group(1))
    return None


def as_number(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    leading_money = re.match(PRICE_NUMBER, raw)
    if leading_money:
        raw = leading_money.group(1)
    cleaned = re.sub(r"[^0-9.,]", "", raw)
    if "," in cleaned and "." not in cleaned and len(cleaned.split(",")[-1]) == 3:
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def strip_html(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", " ", str(value))
    return " ".join(unescape(text).split())
