from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import ListingStatus, PropertyType


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class PropertyImageCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    alt_text: str | None = Field(default=None, max_length=180)
    sort_order: int = 0


class PropertyImageRead(PropertyImageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PropertyBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10)
    address: str = Field(min_length=3, max_length=240)
    city: str = Field(min_length=2, max_length=120)
    country: str = Field(default="Belgium", min_length=2, max_length=80)
    price: float = Field(gt=0)
    bedrooms: int = Field(default=0, ge=0)
    bathrooms: int = Field(default=0, ge=0)
    area_sqm: float | None = Field(default=None, gt=0)
    property_type: PropertyType
    status: ListingStatus = ListingStatus.active


class PropertyCreate(PropertyBase):
    images: list[PropertyImageCreate] = Field(default_factory=list)


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, min_length=10)
    address: str | None = Field(default=None, min_length=3, max_length=240)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=80)
    price: float | None = Field(default=None, gt=0)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    area_sqm: float | None = Field(default=None, gt=0)
    property_type: PropertyType | None = None
    status: ListingStatus | None = None


class PropertyRead(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    images: list[PropertyImageRead] = Field(default_factory=list)


class InquiryCreate(BaseModel):
    property_id: int
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    message: str = Field(min_length=10, max_length=2000)


class InquiryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    property_id: int
    name: str
    email: EmailStr
    message: str
    created_at: datetime
