import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urlparse

import httpx


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
    html = fetch_listing_html(url)
    return extract_immoweb_listing(html, url)


def fetch_listing_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,nl;q=0.8,fr;q=0.8",
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

    expected_fields = ["price", "city", "postcode", "property_type", "bedrooms", "bathrooms", "area_sqm", "energy_score"]
    extracted_fields = [field for field in expected_fields if extracted.get(field) not in (None, "", [])]
    missing_fields = [field for field in expected_fields if field not in extracted_fields]
    extracted["extracted_fields"] = extracted_fields
    extracted["missing_fields"] = missing_fields
    extracted["extraction_confidence"] = round(len(extracted_fields) / len(expected_fields), 2)
    extracted["extraction_status"] = "success" if not missing_fields else "partial"
    if looks_blocked_or_empty(html) and not extracted_fields:
        extracted["extraction_status"] = "blocked"
        extracted["error"] = "Immoweb did not expose listing details to the backend request."
    return extracted


def merge_url_fields(extracted: dict[str, Any], source_url: str) -> None:
    path_parts = [unquote(part) for part in urlparse(source_url).path.split("/") if part]
    if not path_parts:
        return
    lowered = [part.lower() for part in path_parts]
    for kind in ["apartment", "house", "studio", "land", "commercial"]:
        if kind in lowered and not extracted.get("property_type"):
            extracted["property_type"] = kind
    if "for-sale" in lowered:
        extracted.setdefault("listing_type", "sale")
    elif "for-rent" in lowered:
        extracted.setdefault("listing_type", "rent")

    if len(path_parts) >= 2 and path_parts[-1].isdigit():
        extracted.setdefault("listing_id", path_parts[-1])
    if len(path_parts) >= 3 and path_parts[-2].isdigit():
        extracted.setdefault("postcode", path_parts[-2])
        city = path_parts[-3].replace("-", " ").title()
        if city and city.lower() not in {"for sale", "for rent", "classified"}:
            extracted.setdefault("city", city)


def looks_blocked_or_empty(html: str) -> bool:
    lower = html.lower()
    return len(html) < 5000 or any(marker in lower for marker in ["captcha", "access denied", "enable javascript", "cloudflare"])


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
        for candidate in extract_json_objects_from_text(script):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            objects.extend(find_listing_like_objects(parsed))
    return objects


def extract_script_json_candidates(html: str) -> list[str]:
    candidates = []
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.I | re.S):
        script = unescape(match.group(1)).strip()
        if script and any(token in script.lower() for token in ["classified", "price", "bedroom", "surface", "__next_data__"]):
            candidates.append(script)
    return candidates


def extract_json_objects_from_text(text: str) -> list[str]:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return [stripped]

    objects: list[str] = []
    for keyword in ["classified", "property", "realEstate", "initialState", "__INITIAL_STATE__"]:
        for match in re.finditer(re.escape(keyword), text, re.I):
            start = text.find("{", match.end())
            if start == -1:
                continue
            obj = read_balanced_object(text, start)
            if obj:
                objects.append(obj)
    return objects


def read_balanced_object(text: str, start: int) -> str | None:
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
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : index + 1]
                return candidate.replace("'", '"') if "'" in candidate and '"' not in candidate else candidate
    return None


def find_listing_like_objects(value: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(value, dict):
        keys = {normalize_key(key) for key in value}
        if keys & {"price", "mainvalue", "bedroomcount", "bedrooms", "roomcount", "surface", "livablesurface", "nethabitablesurface"}:
            found.append(value)
        for child in value.values():
            found.extend(find_listing_like_objects(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_listing_like_objects(child))
    return found


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
    set_first(extracted, field_map, "price", ["price", "mainprice", "saleprice", "transactionprice", "mainvalue"])
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
        ["livablesurface", "nethabitablesurface", "habitablesurface", "surface", "area", "size"],
    )
    set_first(extracted, field_map, "energy_score", ["epcscore", "energyscore", "energyclass", "peb"])
    set_first(extracted, field_map, "condition", ["condition", "buildingcondition", "renovationlevel"])

    if not extracted.get("images"):
        images = collect_image_urls(item)
        if images:
            extracted["images"] = images


def flatten_mapping(value: Any) -> dict[str, Any]:
    flattened = {}
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = normalize_key(key)
            if child not in (None, "", []):
                flattened.setdefault(normalized, child)
            if isinstance(child, (dict, list)):
                flattened.update(flatten_mapping(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                flattened.update(flatten_mapping(child))
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


def merge_raw_json_patterns(extracted: dict[str, Any], html: str) -> None:
    raw = unescape(html)
    if not extracted.get("price"):
        extracted["price"] = first_number_match(
            raw,
            [
                r'"price"\s*:\s*\{[^{}]{0,300}"mainValue"\s*:\s*([0-9]{5,8})',
                r'"mainValue"\s*:\s*([0-9]{5,8})',
                r'"salePrice"\s*:\s*([0-9]{5,8})',
                r'"transactionPrice"\s*:\s*([0-9]{5,8})',
            ],
        )
    if not extracted.get("city"):
        extracted["city"] = first_text_match(raw, [r'"locality"\s*:\s*"([^"]+)"', r'"city"\s*:\s*"([^"]+)"'])
    if not extracted.get("postcode"):
        extracted["postcode"] = first_text_match(raw, [r'"postalCode"\s*:\s*"?([0-9]{4})"?', r'"postcode"\s*:\s*"?([0-9]{4})"?'])
    if not extracted.get("bedrooms"):
        extracted["bedrooms"] = first_number_match(raw, [r'"bedroomCount"\s*:\s*([0-9]+)', r'"bedrooms"\s*:\s*([0-9]+)'])
    if not extracted.get("bathrooms"):
        extracted["bathrooms"] = first_number_match(raw, [r'"bathroomCount"\s*:\s*([0-9]+)', r'"bathrooms"\s*:\s*([0-9]+)'])
    if not extracted.get("area_sqm"):
        extracted["area_sqm"] = first_number_match(raw, [r'"netHabitableSurface"\s*:\s*([0-9]+)', r'"livableSurface"\s*:\s*([0-9]+)', r'"surface"\s*:\s*([0-9]+)'])
    if not extracted.get("energy_score"):
        extracted["energy_score"] = first_text_match(raw, [r'"epcScore"\s*:\s*"([A-G][+]?)"', r'"energyClass"\s*:\s*"([A-G][+]?)"'])
    if not extracted.get("property_type"):
        extracted["property_type"] = first_text_match(raw, [r'"subtype"\s*:\s*"([^"]+)"', r'"propertyType"\s*:\s*"([^"]+)"'])


def merge_regex_fields(extracted: dict[str, Any], html: str) -> None:
    text = unescape(strip_html(html))
    compact = " ".join(text.split())

    if not extracted.get("price"):
        extracted["price"] = first_number_match(
            compact,
            [
                r"(?:Price|Asking price|Sale price)\s*(?:EUR|€)?\s*([0-9][0-9.\s,]*)",
                r"(?:EUR|€)\s*([0-9][0-9.\s,]*)\s*(?:asking|sale|price)",
            ],
        )
    if not extracted.get("bedrooms"):
        extracted["bedrooms"] = first_number_match(compact, [r"(?:Bedrooms?|Bedroom\(s\))\s*([0-9]+)"])
    if not extracted.get("bathrooms"):
        extracted["bathrooms"] = first_number_match(compact, [r"(?:Bathrooms?|Bathroom\(s\))\s*([0-9]+)"])
    if not extracted.get("area_sqm"):
        extracted["area_sqm"] = first_number_match(
            compact,
            [r"(?:Living area|Habitable surface|Surface|Area)\s*([0-9]+)\s*(?:m2|m²|sqm)"],
        )

    energy_match = re.search(r"\bEPC\b[^A-F+]*([A-F][+]?)\b|\bEnergy score\b[^A-F+]*([A-F][+]?)\b", compact, re.I)
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
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return as_number(match.group(1))
    return None


def first_text_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            value = unescape(match.group(1)).strip()
            return value if value else None
    return None


def as_number(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.,]", "", str(value)).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def strip_html(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return " ".join(unescape(text).split())
