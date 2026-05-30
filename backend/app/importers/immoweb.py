import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any

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
        "User-Agent": "Mozilla/5.0 (compatible; PropertyROI/0.1; +https://github.com/lucas-dbck/property)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
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

    json_objects = extract_json_ld(html)
    for item in json_objects:
        merge_json_ld_fields(extracted, item)

    merge_regex_fields(extracted, html)

    expected_fields = ["price", "city", "postcode", "property_type", "bedrooms", "bathrooms", "area_sqm", "energy_score"]
    extracted_fields = [field for field in expected_fields if extracted.get(field) not in (None, "", [])]
    missing_fields = [field for field in expected_fields if field not in extracted_fields]
    extracted["extracted_fields"] = extracted_fields
    extracted["missing_fields"] = missing_fields
    extracted["extraction_confidence"] = round(len(extracted_fields) / len(expected_fields), 2)
    extracted["extraction_status"] = "success" if not missing_fields else "partial"
    return extracted


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


def merge_regex_fields(extracted: dict[str, Any], html: str) -> None:
    text = unescape(strip_html(html))
    compact = " ".join(text.split())

    extracted.setdefault("price", first_number_match(compact, [r"EUR\s*([0-9.\s]+)", r"([0-9.\s]+)\s*EUR"]))
    extracted.setdefault("bedrooms", first_number_match(compact, [r"([0-9]+)\s+bedroom", r"Bedrooms?\s*([0-9]+)"]))
    extracted.setdefault("bathrooms", first_number_match(compact, [r"([0-9]+)\s+bathroom", r"Bathrooms?\s*([0-9]+)"]))
    extracted.setdefault("area_sqm", first_number_match(compact, [r"([0-9]+)\s*m2"]))

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
        match = re.search(pattern, text, re.I)
        if match:
            return as_number(match.group(1))
    return None


def as_number(value: Any) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.,]", "", str(value)).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def strip_html(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", " ", str(value))
    return " ".join(unescape(text).split())
