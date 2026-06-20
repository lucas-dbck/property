import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, get_db
from app.main import app
from app.routes import opportunities


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


client = TestClient(app)


def register_user(email: str = "owner@example.com", password: str = "password123") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Property Owner", "password": password},
    )
    assert response.status_code == 201
    return response.json()


def login_user(email: str = "owner@example.com", password: str = "password123") -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_property(token: str) -> dict:
    response = client.post(
        "/properties",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Sunny Antwerp Loft",
            "description": "A bright loft with generous windows and a calm central location.",
            "address": "Main Street 12",
            "city": "Antwerp",
            "country": "Belgium",
            "price": 425000,
            "bedrooms": 2,
            "bathrooms": 1,
            "area_sqm": 88,
            "property_type": "apartment",
            "listing_type": "sale",
            "latitude": 51.2194,
            "longitude": 4.4025,
            "amenities": ["balcony", "lift"],
            "energy_score": "B",
            "agent_name": "Local Agent",
            "agent_phone": "+32 3 555 0101",
            "agent_email": "agent@example.com",
            "images": [
                {
                    "url": "https://example.com/image.jpg",
                    "alt_text": "Sunny living room",
                    "sort_order": 0,
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_read_current_user():
    user = register_user()
    assert user["email"] == "owner@example.com"

    token = login_user()
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"


def test_create_and_filter_properties():
    register_user()
    token = login_user()
    property_item = create_property(token)

    assert property_item["title"] == "Sunny Antwerp Loft"
    assert property_item["slug"] == "sunny-antwerp-loft"
    assert property_item["listing_type"] == "sale"
    assert property_item["amenities"] == ["balcony", "lift"]
    assert property_item["images"][0]["url"] == "https://example.com/image.jpg"

    response = client.get("/properties", params={"city": "antwerp", "min_price": 300000, "listing_type": "sale"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["city"] == "Antwerp"


def test_favorite_and_unfavorite_property():
    register_user()
    token = login_user()
    property_item = create_property(token)

    favorite_response = client.post(
        f"/properties/{property_item['id']}/favorite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert favorite_response.status_code == 204

    unfavorite_response = client.delete(
        f"/properties/{property_item['id']}/favorite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unfavorite_response.status_code == 204


def test_create_public_inquiry():
    register_user()
    token = login_user()
    property_item = create_property(token)

    response = client.post(
        "/inquiries",
        json={
            "property_id": property_item["id"],
            "name": "Interested Buyer",
            "email": "buyer@example.com",
            "message": "I would like to schedule a viewing this week.",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "buyer@example.com"


def test_create_and_update_investment_opportunity():
    register_user()
    token = login_user()

    response = client.post(
        "/opportunities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Antwerp ROI candidate",
            "source": "manual",
            "imported_data": {
                "city": "Antwerp",
                "purchase_price": 300000,
                "estimated_rent": 1250,
            },
            "user_overrides": {
                "renovation_cost": 25000,
            },
            "extraction_confidence": 0.8,
        },
    )

    assert response.status_code == 201
    opportunity = response.json()
    assert opportunity["final_data"]["purchase_price"] == 300000
    assert opportunity["final_data"]["renovation_cost"] == 25000

    update_response = client.patch(
        f"/opportunities/{opportunity['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_overrides": {"estimated_rent": 1350, "renovation_cost": 20000}},
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["final_data"]["estimated_rent"] == 1350
    assert updated["final_data"]["renovation_cost"] == 20000


def test_create_immoweb_import(monkeypatch):
    register_user()
    token = login_user()

    def fake_import_immoweb_listing(url: str) -> dict:
        return {
            "source_url": url,
            "extraction_status": "success",
            "title": "Extracted apartment",
            "city": "Antwerp",
            "postcode": "2000",
            "price": 300000,
            "area_sqm": 80,
            "bedrooms": 2,
            "energy_score": "B",
            "extraction_confidence": 0.75,
            "extracted_fields": ["city", "postcode", "price", "area_sqm", "bedrooms", "energy_score"],
            "missing_fields": ["bathrooms", "property_type"],
        }

    monkeypatch.setattr(opportunities, "import_immoweb_listing", fake_import_immoweb_listing)

    response = client.post(
        "/opportunities/imports/immoweb",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://www.immoweb.be/en/classified/apartment/for-sale/antwerp/2000/123456",
            "title": "Immoweb candidate",
            "user_overrides": {"renovation_cost": 15000},
        },
    )

    assert response.status_code == 201
    opportunity = response.json()
    assert opportunity["source"] == "immoweb"
    assert opportunity["imported_data"]["extraction_status"] == "success"
    assert opportunity["imported_data"]["price"] == 300000
    assert opportunity["final_data"]["renovation_cost"] == 15000


def test_monitored_search_loads_new_immoweb_listings_once(monkeypatch):
    register_user()
    token = login_user()
    listing_urls = [
        "https://www.immoweb.be/en/classified/apartment/for-sale/duffel/2570/21603852",
        "https://www.immoweb.be/en/classified/house/for-sale/malderen/1840/21603899",
    ]

    def fake_find_immoweb_listing_urls(search_url: str, limit: int = 20) -> list[str]:
        assert search_url == "https://www.immoweb.be/en/search/apartment/for-sale/duffel/2570"
        return listing_urls[:limit]

    def fake_import_immoweb_listing(url: str) -> dict:
        city = "Duffel" if "duffel" in url else "Malderen"
        return {
            "source_url": url,
            "extraction_status": "partial",
            "city": city,
            "price": 300000,
            "purchase_price": 300000,
            "area_sqm": 80,
            "bedrooms": 2,
            "monthly_rent": 1200,
            "extraction_confidence": 0.5,
            "extracted_fields": ["city", "price", "area_sqm", "bedrooms"],
            "missing_fields": ["energy_score"],
        }

    monkeypatch.setattr(opportunities, "find_immoweb_listing_urls", fake_find_immoweb_listing_urls)
    monkeypatch.setattr(opportunities, "import_immoweb_listing", fake_import_immoweb_listing)

    create_response = client.post(
        "/opportunities/monitored-searches",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Duffel apartments",
            "search_url": "https://www.immoweb.be/en/search/apartment/for-sale/duffel/2570",
            "scan_now": True,
        },
    )

    assert create_response.status_code == 201
    search = create_response.json()
    assert search["name"] == "Duffel apartments"
    assert search["last_checked_at"] is not None

    list_response = client.get("/opportunities", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    scan_response = client.post(
        f"/opportunities/monitored-searches/{search['id']}/scan",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert scan_response.status_code == 200
    scan = scan_response.json()
    assert scan["found_count"] == 2
    assert scan["created_count"] == 0
    assert scan["skipped_existing_count"] == 2


def test_analyze_investment_opportunity():
    register_user()
    token = login_user()

    create_response = client.post(
        "/opportunities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "ROI analysis candidate",
            "imported_data": {
                "city": "Antwerp",
                "area_sqm": 80,
                "bedrooms": 2,
                "purchase_price": 300000,
                "energy_score": "B",
                "amenities": ["balcony", "parking"],
            },
            "user_overrides": {
                "renovation_cost": 25000,
                "down_payment": 75000,
                "interest_rate": 3.5,
                "loan_years": 25,
                "annual_taxes": 1200,
                "annual_insurance": 650,
                "vacancy_rate": 0.05,
            },
        },
    )
    assert create_response.status_code == 201
    opportunity_id = create_response.json()["id"]

    analysis_response = client.get(
        f"/opportunities/{opportunity_id}/analysis",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert analysis_response.status_code == 200
    body = analysis_response.json()
    assert body["opportunity_id"] == opportunity_id
    assert body["analysis"]["estimated_monthly_rent"] > 0
    assert body["analysis"]["gross_yield"] > 0
    assert "roi_score" in body["analysis"]


def test_read_opportunity_input_template():
    response = client.get("/opportunities/input-template")

    assert response.status_code == 200
    body = response.json()
    field_keys = {field["key"] for field in body["fields"]}
    assert "purchase_price" in field_keys
    assert "monthly_rent" in field_keys
    assert "energy_score" in field_keys
    assert "renovation_cost" in field_keys
    assert "vacancy_rate" in field_keys
    purchase_price = next(field for field in body["fields"] if field["key"] == "purchase_price")
    assert purchase_price["imported"] is True
    assert purchase_price["required_for_roi"] is True


def test_quick_analyze_opportunity_inputs():
    response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Antwerp",
                "area_sqm": 80,
                "purchase_price": 300000,
                "energy_score": "B",
                "amenities": ["balcony", "parking"],
                "renovation_cost": 20000,
                "down_payment": 75000,
                "interest_rate": 3.5,
                "loan_years": 25,
                "vacancy_rate": 0.05,
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["final_data"]["purchase_price"] == 300000
    assert body["analysis"]["estimated_monthly_rent"] > 0
    assert body["analysis"]["total_investment"] > 300000
    assert "roi_score" in body["analysis"]


def test_quick_analyze_estimates_missing_cost_assumptions():
    response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Antwerp",
                "area_sqm": 100,
                "purchase_price": 385000,
                "energy_score": "C",
            }
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["purchase_price"] == 385000
    assert analysis["renovation_cost"] == 25000
    assert analysis["purchase_costs"] == 46200
    assert analysis["annual_operating_costs"] > 0
    assert analysis["total_investment"] > 385000


def test_city_and_postcode_influence_estimated_rent():
    leuven_response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Leuven",
                "postcode": "3000",
                "area_sqm": 80,
                "purchase_price": 300000,
            }
        },
    )
    charleroi_response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Charleroi",
                "postcode": "6000",
                "area_sqm": 80,
                "purchase_price": 300000,
            }
        },
    )
    duffel_response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Duffel",
                "postcode": "2570",
                "area_sqm": 80,
                "purchase_price": 300000,
            }
        },
    )

    assert leuven_response.status_code == 200
    assert charleroi_response.status_code == 200
    assert duffel_response.status_code == 200
    leuven_rent = leuven_response.json()["analysis"]["estimated_monthly_rent"]
    charleroi_rent = charleroi_response.json()["analysis"]["estimated_monthly_rent"]
    duffel_rent = duffel_response.json()["analysis"]["estimated_monthly_rent"]

    assert leuven_rent > duffel_rent > charleroi_rent


def test_rent_estimate_uses_bedrooms_when_area_is_missing():
    response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Leuven",
                "property_type": "apartment",
                "bedrooms": 2,
                "purchase_price": 300000,
            }
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["estimated_monthly_rent"] > 1000
    assert "estimated" in " ".join(analysis["rent_estimation_explanation"]).lower()


def test_analysis_exposes_loan_calculation_parts():
    response = client.post(
        "/opportunities/analyze",
        json={
            "data": {
                "city": "Leuven",
                "area_sqm": 80,
                "purchase_price": 300000,
                "down_payment": 60000,
                "interest_rate": 3.5,
                "loan_years": 25,
            }
        },
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["down_payment"] == 60000
    assert analysis["total_investment"] == 356000
    assert analysis["total_cash_invested"] == 60000
    assert analysis["loan_amount"] == 296000
    assert analysis["monthly_debt_service"] > 0


def test_compare_investment_opportunities():
    register_user()
    token = login_user()

    for title, price, rent in [
        ("Better Antwerp deal", 250000, 1450),
        ("Weaker Brussels deal", 420000, 1500),
    ]:
        response = client.post(
            "/opportunities",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "imported_data": {
                    "city": "Antwerp",
                    "area_sqm": 80,
                    "purchase_price": price,
                    "monthly_rent": rent,
                    "energy_score": "B",
                },
                "user_overrides": {
                    "renovation_cost": 10000,
                    "annual_taxes": 1000,
                    "annual_insurance": 600,
                    "vacancy_rate": 0.04,
                },
            },
        )
        assert response.status_code == 201

    compare_response = client.get(
        "/opportunities/compare",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert compare_response.status_code == 200
    body = compare_response.json()
    assert body["count"] == 2
    assert body["items"][0]["rank"] == 1
    assert body["items"][0]["title"] == "Better Antwerp deal"
    assert body["items"][0]["roi_score"] >= body["items"][1]["roi_score"]
