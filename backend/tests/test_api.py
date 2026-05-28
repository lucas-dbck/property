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
    assert property_item["images"][0]["url"] == "https://example.com/image.jpg"

    response = client.get("/properties", params={"city": "antwerp", "min_price": 300000})

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
