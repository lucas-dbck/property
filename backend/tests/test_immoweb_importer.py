import json

from app.importers.immoweb import extract_immoweb_listing


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
