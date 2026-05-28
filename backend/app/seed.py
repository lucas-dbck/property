from sqlalchemy import select

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import Property, PropertyImage, PropertyType, User


DEMO_EMAIL = "demo@property.local"


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        demo_user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if demo_user is None:
            demo_user = User(
                email=DEMO_EMAIL,
                full_name="Demo Owner",
                hashed_password=hash_password("password123"),
            )
            db.add(demo_user)
            db.flush()

        existing_properties = db.scalar(
            select(Property).where(Property.owner_id == demo_user.id, Property.title == "Bright Antwerp Apartment")
        )
        if existing_properties is not None:
            db.commit()
            return

        properties = [
            Property(
                owner_id=demo_user.id,
                title="Bright Antwerp Apartment",
                description="A warm two-bedroom apartment with natural light, a balcony, and easy access to the city center.",
                address="Kasteelpleinstraat 12",
                city="Antwerp",
                country="Belgium",
                price=385000,
                bedrooms=2,
                bathrooms=1,
                area_sqm=86,
                property_type=PropertyType.apartment,
                images=[
                    PropertyImage(
                        url="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267",
                        alt_text="Bright apartment living room",
                    )
                ],
            ),
            Property(
                owner_id=demo_user.id,
                title="Family House Near Ghent",
                description="A calm family home with a garden, renovated kitchen, and three comfortable bedrooms.",
                address="Lindenlaan 44",
                city="Ghent",
                country="Belgium",
                price=545000,
                bedrooms=3,
                bathrooms=2,
                area_sqm=142,
                property_type=PropertyType.house,
                images=[
                    PropertyImage(
                        url="https://images.unsplash.com/photo-1568605114967-8130f3a36994",
                        alt_text="Detached family house",
                    )
                ],
            ),
            Property(
                owner_id=demo_user.id,
                title="Compact Brussels Studio",
                description="A practical studio close to public transport, ideal as a first home or investment property.",
                address="Rue Haute 89",
                city="Brussels",
                country="Belgium",
                price=215000,
                bedrooms=0,
                bathrooms=1,
                area_sqm=38,
                property_type=PropertyType.studio,
                images=[
                    PropertyImage(
                        url="https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
                        alt_text="Compact studio interior",
                    )
                ],
            ),
        ]

        db.add_all(properties)
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seed data ready.")
