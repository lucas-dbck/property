from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PropertyType(str, Enum):
    apartment = "apartment"
    house = "house"
    studio = "studio"
    land = "land"
    commercial = "commercial"


class ListingStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class ListingType(str, Enum):
    sale = "sale"
    rent = "rent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    properties: Mapped[list["Property"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str] = mapped_column(String(240), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(80), default="Belgium", nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    area_sqm: Mapped[float | None] = mapped_column(Float)
    property_type: Mapped[PropertyType] = mapped_column(SqlEnum(PropertyType), nullable=False, index=True)
    listing_type: Mapped[ListingType] = mapped_column(SqlEnum(ListingType), default=ListingType.sale, nullable=False, index=True)
    status: Mapped[ListingStatus] = mapped_column(SqlEnum(ListingStatus), default=ListingStatus.active, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    amenities: Mapped[str | None] = mapped_column(Text)
    available_from: Mapped[datetime | None] = mapped_column(Date)
    energy_score: Mapped[str | None] = mapped_column(String(40))
    agent_name: Mapped[str | None] = mapped_column(String(120))
    agent_phone: Mapped[str | None] = mapped_column(String(50))
    agent_email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="properties")
    images: Mapped[list["PropertyImage"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(180))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    property: Mapped["Property"] = relationship(back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "property_id", name="uq_user_property_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="favorites")
    property: Mapped["Property"] = relationship(back_populates="favorites")


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="inquiries")
    property: Mapped["Property"] = relationship(back_populates="inquiries")
