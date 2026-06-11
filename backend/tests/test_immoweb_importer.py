import json

from app.importers import immoweb
from app.importers.immoweb import extract_immoweb_listing, extract_listing_urls_from_search_html


def test_extracts_embedded_listing_data_before_page_text_numbers():
    payload = {
        "props": {
            "pageProps": {
                "classified": {
                    "title": "Renovated apartment near park",
                    "price": {"mainValue": 325000, "currency": "EUR"},
                    "property": {
                        "type": "APARTMENT",
                        "bedroomCount": 2,
                        "bathroomCount": 1,
                        "netHabitableSurface": 91,
                        "buildingCondition": "RENOVATED",
                    },
                    "address": {
                        "locality": "Antwerp",
                        "postalCode": "2000",
                        "street": "Example Street",
                    },
                    "energy": {"epcScore": "B"},
                    "media": {
                        "pictures": [
                            {"largeUrl": "https://images.example/listing-1.jpg"},
                            {"largeUrl": "https://images.example/listing-2.jpg"},
                        ]
                    },
                }
            }
        }
    }
    html = f"""
    <html>
      <body>
        Similar homes from EUR 999999 and 6 bedrooms nearby.
        <script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>
      </body>
    </html>
    """

    result = extract_immoweb_listing(html, "https://www.immoweb.be/listing")

    assert result["title"] == "Renovated apartment near park"
    assert result["price"] == 325000
    assert result["city"] == "Antwerp"
    assert result["postcode"] == "2000"
    assert result["property_type"] == "APARTMENT"
    assert result["bedrooms"] == 2
    assert result["bathrooms"] == 1
    assert result["area_sqm"] == 91
    assert result["energy_score"] == "B"
    assert result["condition"] == "RENOVATED"
    assert result["images"] == [
        "https://images.example/listing-1.jpg",
        "https://images.example/listing-2.jpg",
    ]


def test_regex_fallback_requires_specific_labels():
    html = """
    <html>
      <body>
        Nearby homes EUR 999999.
        Price EUR 275000.
        Bedrooms 1.
        Living area 64 m2.
        Energy score C.
      </body>
    </html>
    """

    result = extract_immoweb_listing(html, "https://www.immoweb.be/listing")

    assert result["price"] == 275000
    assert result["bedrooms"] == 1
    assert result["area_sqm"] == 64
    assert result["energy_score"] == "C"


def test_extracts_city_from_url_and_plain_euro_price_text():
    html = """
    <html>
      <body>
        Javascript required.
        Appartement te koop
        425000€
        2 slaapkamers | 119 m²
        EPC B
      </body>
    </html>
    """

    result = extract_immoweb_listing(
        html,
        "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852",
    )

    assert result["price"] == 425000
    assert result["city"] == "Duffel"
    assert result["postcode"] == "2570"
    assert result["property_type"] == "apartment"
    assert result["listing_id"] == "21603852"
    assert result["bedrooms"] == 2
    assert result["area_sqm"] == 119
    assert result["energy_score"] == "B"


def test_extracts_raw_immoweb_json_fields_when_scripts_are_not_valid_json():
    html = """
    <html>
      <body>
        <script>
          self.__next_f.push(["classified", "{\\"mainValue\\":425000,\\"bedroomCount\\":2,\\"netHabitableSurface\\":119,\\"epcScore\\":\\"B\\",\\"locality\\":\\"Duffel\\",\\"postalCode\\":\\"2570\\"}"])
        </script>
      </body>
    </html>
    """

    result = extract_immoweb_listing(
        html,
        "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852",
    )

    assert result["price"] == 425000
    assert result["purchase_price"] == 425000
    assert result["city"] == "Duffel"
    assert result["postcode"] == "2570"
    assert result["bedrooms"] == 2
    assert result["area_sqm"] == 119
    assert result["energy_score"] == "B"


def test_extracts_price_from_messy_next_flight_page_script():
    html = """
    <html>
      <body>
        <script>
          self.__next_f.push([1, "classified", "{\\"classified\\":{\\"price\\":{\\"mainValue\\":385000,\\"currency\\":\\"EUR\\"},\\"property\\":{\\"bedroomCount\\":3,\\"netHabitableSurface\\":140},\\"address\\":{\\"locality\\":\\"Malderen\\",\\"postalCode\\":\\"1840\\"}}}"])
        </script>
      </body>
    </html>
    """

    result = extract_immoweb_listing(
        html,
        "https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899",
    )

    assert result["price"] == 385000
    assert result["purchase_price"] == 385000
    assert result["monthly_rent"] > 0
    assert result["city"] == "Malderen"
    assert result["postcode"] == "1840"
    assert result["bedrooms"] == 3
    assert result["area_sqm"] == 140


def test_extracts_price_from_window_classified_script():
    html = """
    <html>
      <body>
        <script>
          window.classified = {
            price: { mainValue: 385000, currency: "EUR" },
            property: { bedroomCount: 3, netHabitableSurface: 140 },
            address: { locality: "Malderen", postalCode: "1840" }
          };
        </script>
      </body>
    </html>
    """

    result = extract_immoweb_listing(
        html,
        "https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899",
    )

    assert result["price"] == 385000
    assert result["purchase_price"] == 385000
    assert result["monthly_rent"] == 1890
    assert result["city"] == "Malderen"
    assert result["postcode"] == "1840"
    assert result["bedrooms"] == 3
    assert result["area_sqm"] == 140


def test_extracts_formatted_price_from_webpage_json():
    html = """
    <html>
      <body>
        <script>
          window.__DATA__ = {
            "classified": {
              "formattedPrice": "€ 425.000",
              "property": {"bedroomCount": 2, "netHabitableSurface": 119},
              "address": {"locality": "Duffel", "postalCode": "2570"}
            }
          }
        </script>
      </body>
    </html>
    """

    result = extract_immoweb_listing(
        html,
        "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852",
    )

    assert result["price"] == 425000
    assert result["monthly_rent"] == 1666
    assert result["city"] == "Duffel"
    assert result["bedrooms"] == 2
    assert result["area_sqm"] == 119


def test_import_uses_search_fallback_when_direct_listing_is_incomplete(monkeypatch):
    listing_url = "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852"
    direct_html = "<html><body>Javascript required</body></html>"
    search_html = """
    <html>
      <body>
        <a href="/en/classified/apartment/for-sale/duffel/2570/21603852">
          Apartment for sale in Duffel
          Price € 425,000
          2 bedrooms
          119 m²
          EPC B
        </a>
      </body>
    </html>
    """
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return direct_html if url == listing_url else search_html

    monkeypatch.setattr(immoweb, "fetch_listing_html", fake_fetch)

    result = immoweb.import_immoweb_listing(listing_url)

    assert len(fetched_urls) == 2
    assert "/en/search/apartment/for-sale/duffel/2570" in fetched_urls[1]
    assert result["price"] == 425000
    assert result["purchase_price"] == 425000
    assert result["city"] == "Duffel"
    assert result["bedrooms"] == 2
    assert result["area_sqm"] == 119
    assert result["energy_score"] == "B"


def test_import_keeps_url_fields_when_direct_fetch_fails(monkeypatch):
    listing_url = "https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899"

    def fake_fetch(url):
        raise RuntimeError("blocked")

    monkeypatch.setattr(immoweb, "fetch_listing_html", fake_fetch)

    result = immoweb.import_immoweb_listing(listing_url)

    assert result["city"] == "Malderen"
    assert result["postcode"] == "1840"
    assert result["property_type"] == "house"
    assert result["listing_id"] == "21603899"
    assert result["direct_fetch_error"] == "blocked"


def test_extracts_listing_urls_from_search_html():
    html = """
    <html>
      <body>
        <a href="/en/classified/apartment/for-sale/duffel/2570/21603852?searchId=abc">Listing</a>
        <a href="https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899">Listing</a>
        <a href="/en/classified/apartment/for-sale/duffel/2570/21603852?searchId=duplicate">Duplicate</a>
      </body>
    </html>
    """

    urls = extract_listing_urls_from_search_html(html, "https://www.immoweb.be/en/search/apartment/for-sale/duffel")

    assert urls == [
        "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852",
        "https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899",
    ]
