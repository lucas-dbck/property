from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_optional_current_user
from ..database import get_db
from ..models import Inquiry, Property, User
from ..schemas import InquiryCreate, InquiryRead

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=InquiryRead, status_code=status.HTTP_201_CREATED)
def create_inquiry(
    payload: InquiryCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> Inquiry:
    property_item = db.scalar(select(Property).where(Property.id == payload.property_id))
    if property_item is None:
        raise HTTPException(status_code=404, detail="Property not found")

    inquiry = Inquiry(
        user_id=current_user.id if current_user else None,
        property_id=payload.property_id,
        name=payload.name,
        email=payload.email.lower(),
        message=payload.message,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.get("/mine", response_model=list[InquiryRead])
def list_my_inquiries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Inquiry]:
    return list(
        db.scalars(
            select(Inquiry)
            .where(Inquiry.user_id == current_user.id)
            .order_by(Inquiry.created_at.desc())
        )
    )
