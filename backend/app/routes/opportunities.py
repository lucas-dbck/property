from datetime import datetime
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analysis import calculate_roi
from ..auth import get_current_user
from ..database import get_db
from ..importers.immoweb import find_immoweb_listing_urls, import_immoweb_listing
from ..importers.listing_text import extract_listing_text_data
from ..models import ImportSource, InvestmentOpportunity, MonitoredSearch, User
from ..schemas import (
    ImmowebImportRequest,
    InvestmentOpportunityCreate,
    InvestmentOpportunityRead,
    InvestmentOpportunityUpdate,
    OpportunityAnalysisRead,
    OpportunityComparisonItem,
    OpportunityComparisonRead,
    OpportunityInputField,
    OpportunityInputTemplateRead,
    OpportunityQuickAnalysisRead,
    OpportunityQuickAnalysisRequest,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class ListingTextImportRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50000)
    source_url: str | None = None
    title: str | None = Field(default=None, min_length=3, max_length=180)
    user_overrides: dict = Field(default_factory=dict)
    notes: str | None = None


class MonitoredSearchCreate(BaseModel):
    search_url: HttpUrl
    name: str | None = Field(default=None, min_length=3, max_length=180)
    scan_now: bool = True


class MonitoredSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    search_url: str
    is_active: bool
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MonitoredSearchScanRead(BaseModel):
    monitored_search_id: int
    found_count: int
    created_count: int
    skipped_existing_count: int
    opportunity_ids: list[int]
    listing_urls: list[str]


def parse_json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value or "{}")
    return parsed if isinstance(parsed, dict) else {}


def merge_opportunity_data(opportunity: InvestmentOpportunity) -> dict[str, Any]:
    final_data = parse_json_object(opportunity.imported_data)
    final_data.update(parse_json_object(opportunity.user_overrides))
    return final_data


def serialize_opportunity(opportunity: InvestmentOpportunity) -> InvestmentOpportunityRead:
    imported_data = parse_json_object(opportunity.imported_data)
    user_overrides = parse_json_object(opportunity.user_overrides)
    return InvestmentOpportunityRead(
        id=opportunity.id,
        owner_id=opportunity.owner_id,
        source=opportunity.source,
        source_url=opportunity.source_url,
        title=opportunity.title,
        imported_data=imported_data,
        user_overrides=user_overrides,
        final_data={**imported_data, **user_overrides},
        extraction_confidence=opportunity.extraction_confidence,
        notes=opportunity.notes,
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at,
    )


def get_opportunity_or_404(db: Session, opportunity_id: int, owner_id: int) -> InvestmentOpportunity:
    opportunity = db.scalar(
        select(InvestmentOpportunity).where(
            InvestmentOpportunity.id == opportunity_id,
            InvestmentOpportunity.owner_id == owner_id,
        )
    )
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Investment opportunity not found")
    return opportunity


def create_opportunity_from_immoweb_url(
    db: Session,
    owner_id: int,
    source_url: str,
    notes: str | None = None,
) -> InvestmentOpportunity:
    imported_data = import_immoweb_listing(source_url)
    opportunity = InvestmentOpportunity(
        owner_id=owner_id,
        source=ImportSource.immoweb,
        source_url=source_url,
        title=imported_data.get("title") or imported_data.get("address") or "Imported Immoweb opportunity",
        imported_data=json.dumps(imported_data),
        user_overrides="{}",
        extraction_confidence=imported_data.get("extraction_confidence", 0.0),
        notes=notes,
    )
    db.add(opportunity)
    db.flush()
    return opportunity


def scan_monitored_search(
    db: Session,
    search: MonitoredSearch,
    max_listings: int = 20,
) -> MonitoredSearchScanRead:
    listing_urls = find_immoweb_listing_urls(search.search_url, limit=max_listings)
    created_ids: list[int] = []
    skipped_existing = 0

    for listing_url in listing_urls:
        existing = db.scalar(
            select(InvestmentOpportunity).where(
                InvestmentOpportunity.owner_id == search.owner_id,
                InvestmentOpportunity.source_url == listing_url,
            )
        )
        if existing:
            skipped_existing += 1
            continue

        opportunity = create_opportunity_from_immoweb_url(
            db,
            owner_id=search.owner_id,
            source_url=listing_url,
            notes=f"Loaded automatically from monitored search: {search.name}",
        )
        created_ids.append(opportunity.id)

    search.last_checked_at = datetime.utcnow()
    db.add(search)
    db.commit()

    return MonitoredSearchScanRead(
        monitored_search_id=search.id,
        found_count=len(listing_urls),
        created_count=len(created_ids),
        skipped_existing_count=skipped_existing,
        opportunity_ids=created_ids,
        listing_urls=listing_urls,
    )


@router.get("", response_model=list[InvestmentOpportunityRead])
def list_opportunities(
    source: ImportSource | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvestmentOpportunityRead]:
    query = select(InvestmentOpportunity).where(InvestmentOpportunity.owner_id == current_user.id)
    if source is not None:
        query = query.where(InvestmentOpportunity.source == source)
    query = query.order_by(InvestmentOpportunity.created_at.desc()).limit(limit).offset(offset)
    return [serialize_opportunity(item) for item in db.scalars(query)]


@router.get("/monitored-searches", response_model=list[MonitoredSearchRead])
def list_monitored_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MonitoredSearchRead]:
    searches = db.scalars(
        select(MonitoredSearch)
        .where(MonitoredSearch.owner_id == current_user.id)
        .order_by(MonitoredSearch.created_at.desc())
    )
    return list(searches)


@router.post("/monitored-searches", response_model=MonitoredSearchRead, status_code=status.HTTP_201_CREATED)
def create_monitored_search(
    payload: MonitoredSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoredSearchRead:
    search_url = str(payload.search_url)
    existing = db.scalar(
        select(MonitoredSearch).where(
            MonitoredSearch.owner_id == current_user.id,
            MonitoredSearch.search_url == search_url,
        )
    )
    if existing:
        if payload.scan_now:
            scan_monitored_search(db, existing)
            db.refresh(existing)
        return existing

    search = MonitoredSearch(
        owner_id=current_user.id,
        search_url=search_url,
        name=payload.name or "Immoweb monitored search",
    )
    db.add(search)
    db.commit()
    db.refresh(search)
    if payload.scan_now:
        scan_monitored_search(db, search)
        db.refresh(search)
    return search


@router.post("/monitored-searches/{search_id}/scan", response_model=MonitoredSearchScanRead)
def scan_monitored_search_endpoint(
    search_id: int,
    max_listings: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoredSearchScanRead:
    search = db.scalar(
        select(MonitoredSearch).where(
            MonitoredSearch.id == search_id,
            MonitoredSearch.owner_id == current_user.id,
        )
    )
    if search is None:
        raise HTTPException(status_code=404, detail="Monitored search not found")
    return scan_monitored_search(db, search, max_listings=max_listings)


@router.post("", response_model=InvestmentOpportunityRead, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: InvestmentOpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentOpportunityRead:
    opportunity = InvestmentOpportunity(
        owner_id=current_user.id,
        source=payload.source,
        source_url=str(payload.source_url) if payload.source_url else None,
        title=payload.title,
        imported_data=json.dumps(payload.imported_data),
        user_overrides=json.dumps(payload.user_overrides),
        extraction_confidence=payload.extraction_confidence,
        notes=payload.notes,
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return serialize_opportunity(opportunity)


@router.post("/imports/immoweb", response_model=InvestmentOpportunityRead, status_code=status.HTTP_201_CREATED)
def import_immoweb_opportunity(
    payload: ImmowebImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentOpportunityRead:
    source_url = str(payload.url)
    try:
        opportunity = create_opportunity_from_immoweb_url(
            db,
            owner_id=current_user.id,
            source_url=source_url,
            notes=payload.notes,
        )
        if payload.title:
            opportunity.title = payload.title
        opportunity.user_overrides = json.dumps(payload.user_overrides)
    except Exception as exc:
        imported_data = {
            "source_url": source_url,
            "extraction_status": "failed",
            "error": str(exc),
            "extracted_fields": [],
            "missing_fields": [],
        }
        opportunity = InvestmentOpportunity(
            owner_id=current_user.id,
            source=ImportSource.immoweb,
            source_url=source_url,
            title=payload.title or "Imported Immoweb opportunity",
            imported_data=json.dumps(imported_data),
            user_overrides=json.dumps(payload.user_overrides),
            extraction_confidence=0.0,
            notes=payload.notes,
        )
        db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return serialize_opportunity(opportunity)


@router.post("/imports/text", response_model=InvestmentOpportunityRead, status_code=status.HTTP_201_CREATED)
def import_listing_text_opportunity(
    payload: ListingTextImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentOpportunityRead:
    imported_data = extract_listing_text_data(payload.text, payload.source_url)
    extraction_confidence = imported_data.get("extraction_confidence", 0.0)
    source_url = payload.source_url or imported_data.get("source_url")
    opportunity = InvestmentOpportunity(
        owner_id=current_user.id,
        source=ImportSource.other,
        source_url=source_url,
        title=payload.title or imported_data.get("title") or "Imported listing text opportunity",
        imported_data=json.dumps(imported_data),
        user_overrides=json.dumps(payload.user_overrides),
        extraction_confidence=extraction_confidence,
        notes=payload.notes,
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return serialize_opportunity(opportunity)


@router.get("/input-template", response_model=OpportunityInputTemplateRead)
def read_opportunity_input_template() -> OpportunityInputTemplateRead:
    return OpportunityInputTemplateRead(
        fields=[
            OpportunityInputField(
                key="source_url",
                label="Listing URL",
                group="listing",
                value_type="url",
                imported=True,
                description="Original property listing URL, for example an Immoweb page.",
                example="https://www.immoweb.be/en/classified/apartment/for-sale/antwerp/2000/123456",
            ),
            OpportunityInputField(
                key="purchase_price",
                label="Purchase price",
                group="purchase",
                value_type="number",
                imported=True,
                required_for_roi=True,
                description="Asking or purchase price of the property.",
                example=300000,
            ),
            OpportunityInputField(
                key="city",
                label="City",
                group="property",
                value_type="text",
                imported=True,
                description="City used for local rent estimation when rent is missing.",
                example="Antwerp",
            ),
            OpportunityInputField(
                key="area_sqm",
                label="Living area",
                group="property",
                value_type="number",
                imported=True,
                description="Interior living area in square meters.",
                example=80,
            ),
            OpportunityInputField(
                key="bedrooms",
                label="Bedrooms",
                group="property",
                value_type="number",
                imported=True,
                description="Bedroom count, used as a fallback when area is missing.",
                example=2,
            ),
            OpportunityInputField(
                key="energy_score",
                label="Energy score",
                group="property",
                value_type="select",
                imported=True,
                description="Energy label. Better scores can increase estimated rent.",
                example="B",
            ),
            OpportunityInputField(
                key="condition",
                label="Condition",
                group="property",
                value_type="select",
                description="Condition of the property: poor, average, renovated, or new.",
                example="renovated",
                default="average",
            ),
            OpportunityInputField(
                key="monthly_rent",
                label="Expected monthly rent",
                group="rent",
                value_type="number",
                description="Manual rent estimate. If empty, the backend estimates rent from city, area, and energy score.",
                example=1350,
            ),
            OpportunityInputField(
                key="renovation_cost",
                label="Renovation cost",
                group="purchase",
                value_type="number",
                required_for_roi=True,
                description="Expected renovation budget before renting or reselling.",
                example=25000,
                default=0,
            ),
            OpportunityInputField(
                key="purchase_costs",
                label="Purchase costs",
                group="purchase",
                value_type="number",
                description="One-time purchase costs such as registration, notary, and deed fees.",
                example=36000,
                default=0,
            ),
            OpportunityInputField(
                key="annual_operating_costs",
                label="Annual operating costs",
                group="purchase",
                value_type="number",
                description="One yearly bucket for maintenance, tax, insurance, and management costs.",
                example=3000,
                default=0,
            ),
            OpportunityInputField(
                key="vacancy_rate",
                label="Vacancy rate",
                group="risk",
                value_type="percent",
                description="Expected percentage of rent lost to vacancy. Default is 5%.",
                example=0.05,
                default=0.05,
            ),
            OpportunityInputField(
                key="down_payment",
                label="Down payment",
                group="financing",
                value_type="number",
                description="Cash paid upfront. Used for cash-on-cash return.",
                example=75000,
            ),
            OpportunityInputField(
                key="interest_rate",
                label="Interest rate",
                group="financing",
                value_type="percent",
                description="Annual mortgage interest rate.",
                example=3.5,
                default=0,
            ),
            OpportunityInputField(
                key="loan_years",
                label="Loan years",
                group="financing",
                value_type="number",
                description="Mortgage duration in years.",
                example=25,
                default=25,
            ),
        ]
    )


@router.post("/analyze", response_model=OpportunityQuickAnalysisRead)
def analyze_opportunity_inputs(payload: OpportunityQuickAnalysisRequest) -> OpportunityQuickAnalysisRead:
    final_data = payload.data
    return OpportunityQuickAnalysisRead(final_data=final_data, analysis=calculate_roi(final_data))


@router.get("/compare", response_model=OpportunityComparisonRead)
def compare_opportunities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityComparisonRead:
    opportunities = list(
        db.scalars(
            select(InvestmentOpportunity)
            .where(InvestmentOpportunity.owner_id == current_user.id)
            .order_by(InvestmentOpportunity.created_at.desc())
        )
    )
    analyzed_items = []
    for opportunity in opportunities:
        analysis = calculate_roi(merge_opportunity_data(opportunity))
        analyzed_items.append((opportunity, analysis))

    analyzed_items.sort(
        key=lambda item: (
            item[1]["roi_score"],
            item[1]["monthly_cash_flow"],
            item[1]["net_yield"],
            item[1]["cash_on_cash_return"],
        ),
        reverse=True,
    )

    items = [
        OpportunityComparisonItem(
            rank=index + 1,
            opportunity_id=opportunity.id,
            title=opportunity.title,
            roi_score=analysis["roi_score"],
            estimated_monthly_rent=analysis["estimated_monthly_rent"],
            gross_yield=analysis["gross_yield"],
            net_yield=analysis["net_yield"],
            monthly_cash_flow=analysis["monthly_cash_flow"],
            cash_on_cash_return=analysis["cash_on_cash_return"],
            total_investment=analysis["total_investment"],
        )
        for index, (opportunity, analysis) in enumerate(analyzed_items)
    ]

    return OpportunityComparisonRead(count=len(items), items=items)


@router.get("/{opportunity_id}", response_model=InvestmentOpportunityRead)
def read_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentOpportunityRead:
    return serialize_opportunity(get_opportunity_or_404(db, opportunity_id, current_user.id))


@router.get("/{opportunity_id}/analysis", response_model=OpportunityAnalysisRead)
def analyze_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityAnalysisRead:
    opportunity = get_opportunity_or_404(db, opportunity_id, current_user.id)
    final_data = merge_opportunity_data(opportunity)
    return OpportunityAnalysisRead(
        opportunity_id=opportunity.id,
        final_data=final_data,
        analysis=calculate_roi(final_data),
    )


@router.patch("/{opportunity_id}", response_model=InvestmentOpportunityRead)
def update_opportunity(
    opportunity_id: int,
    payload: InvestmentOpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentOpportunityRead:
    opportunity = get_opportunity_or_404(db, opportunity_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    if "source_url" in updates and updates["source_url"] is not None:
        updates["source_url"] = str(updates["source_url"])
    if "imported_data" in updates and updates["imported_data"] is not None:
        updates["imported_data"] = json.dumps(updates["imported_data"])
    if "user_overrides" in updates and updates["user_overrides"] is not None:
        updates["user_overrides"] = json.dumps(updates["user_overrides"])

    for field, value in updates.items():
        setattr(opportunity, field, value)

    db.commit()
    db.refresh(opportunity)
    return serialize_opportunity(opportunity)


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    opportunity = get_opportunity_or_404(db, opportunity_id, current_user.id)
    db.delete(opportunity)
    db.commit()
