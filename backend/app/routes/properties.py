from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..database import get_db
from ..models import Favorite, ListingStatus, Property, PropertyImage, PropertyType, User
from ..schemas import PropertyCreate, PropertyImageCreate, PropertyImageRead, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


def get_property_or_404(db: Session, property_id: int) -> Property:
    property_item = db.scalar(
        select(Property)
        .where(Property.id == property_id)
        .options(selectinload(Property.images))
    )
    if property_item is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return property_item


@router.get("", response_model=list[PropertyRead])
def list_properties(
    city: str | None = None,
    min_price: float | None = Query(default=None, gt=0),
    max_price: float | None = Query(default=None, gt=0),
    bedrooms: int | None = Query(default=None, ge=0),
    property_type: PropertyType | None = None,
    status_filter: ListingStatus = Query(default=ListingStatus.active, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Property]:
    query = select(Property).options(selectinload(Property.images)).where(Property.status == status_filter)

    if city:
        query = query.where(Property.city.ilike(f"%{city}%"))
    if min_price is not None:
        query = query.where(Property.price >= min_price)
    if max_price is not None:
        query = query.where(Property.price <= max_price)
    if bedrooms is not None:
        query = query.where(Property.bedrooms >= bedrooms)
    if property_type is not None:
        query = query.where(Property.property_type == property_type)

    query = query.order_by(Property.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query).unique())


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    property_item = Property(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        price=payload.price,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        area_sqm=payload.area_sqm,
        property_type=payload.property_type,
        status=payload.status,
    )
    property_item.images = [PropertyImage(**image.model_dump()) for image in payload.images]
    db.add(property_item)
    db.commit()
    db.refresh(property_item)
    return get_property_or_404(db, property_item.id)


@router.get("/{property_id}", response_model=PropertyRead)
def read_property(property_id: int, db: Session = Depends(get_db)) -> Property:
    return get_property_or_404(db, property_id)


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    property_item = get_property_or_404(db, property_id)
    if property_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can update this property")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(property_item, field, value)

    db.commit()
    db.refresh(property_item)
    return get_property_or_404(db, property_item.id)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    property_item = get_property_or_404(db, property_id)
    if property_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this property")

    db.delete(property_item)
    db.commit()


@router.post("/{property_id}/images", response_model=PropertyImageRead, status_code=status.HTTP_201_CREATED)
def add_property_image(
    property_id: int,
    payload: PropertyImageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PropertyImage:
    property_item = get_property_or_404(db, property_id)
    if property_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can add images")

    image = PropertyImage(property_id=property_id, **payload.model_dump())
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.post("/{property_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def favorite_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    get_property_or_404(db, property_id)
    existing = db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.property_id == property_id,
        )
    )
    if existing is None:
        db.add(Favorite(user_id=current_user.id, property_id=property_id))
        db.commit()


@router.delete("/{property_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    favorite = db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.property_id == property_id,
        )
    )
    if favorite is not None:
        db.delete(favorite)
        db.commit()
