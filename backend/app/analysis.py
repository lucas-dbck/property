from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CITY_RENT_PER_SQM = {
    "brussels": 18.0,
    "antwerp": 16.0,
    "ghent": 17.0,
    "leuven": 19.0,
    "mechelen": 15.5,
    "bruges": 15.0,
    "charleroi": 10.5,
    "liege": 12.0,
}

ENERGY_MULTIPLIERS = {
    "a+": 1.06,
    "a": 1.05,
    "b": 1.03,
    "c": 1.0,
    "d": 0.97,
    "e": 0.94,
    "f": 0.9,
}

AMENITY_MULTIPLIERS = {
    "balcony": 0.02,
    "terrace": 0.03,
    "garden": 0.04,
    "parking": 0.04,
    "garage": 0.04,
    "lift": 0.015,
    "elevator": 0.015,
    "furnished": 0.05,
    "renovated": 0.05,
    "near metro": 0.025,
    "public transport": 0.02,
}


@dataclass
class RentEstimate:
    monthly_rent: float
    explanation: list[str]


def as_float(data: dict[str, Any], key: str, default: float = 0) -> float:
    value = data.get(key, default)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_amenities(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    if isinstance(value, str):
        return [normalize_text(item) for item in value.split(",") if normalize_text(item)]
    return []


def estimate_monthly_rent(data: dict[str, Any]) -> RentEstimate:
    known_rent = as_float(data, "monthly_rent") or as_float(data, "expected_monthly_rent") or as_float(data, "estimated_rent")
    if known_rent > 0:
        return RentEstimate(
            monthly_rent=round(known_rent, 2),
            explanation=["Used rent provided by the user or imported listing data."],
        )

    city = normalize_text(data.get("city"))
    area_sqm = as_float(data, "area_sqm") or as_float(data, "living_area") or as_float(data, "size_sqm")
    bedrooms = as_float(data, "bedrooms")
    base_rent_per_sqm = CITY_RENT_PER_SQM.get(city, 14.0)
    explanation = [f"Base rent for {city or 'unknown city'}: EUR {base_rent_per_sqm:.2f}/m2."]

    if area_sqm > 0:
        monthly_rent = area_sqm * base_rent_per_sqm
        explanation.append(f"Area adjustment: {area_sqm:.0f} m2 used.")
    else:
        monthly_rent = 650 + bedrooms * 275
        explanation.append("Area missing, estimated from bedroom count.")

    energy_score = normalize_text(data.get("energy_score"))
    energy_multiplier = ENERGY_MULTIPLIERS.get(energy_score, 1.0)
    if energy_score:
        explanation.append(f"Energy score {energy_score.upper()} multiplier: {energy_multiplier:.2f}.")
    monthly_rent *= energy_multiplier

    amenities = normalize_amenities(data.get("amenities"))
    amenity_bonus = sum(AMENITY_MULTIPLIERS.get(item, 0) for item in amenities)
    if amenity_bonus:
        explanation.append(f"Amenity bonus: {amenity_bonus * 100:.1f}%.")
    monthly_rent *= 1 + min(amenity_bonus, 0.2)

    condition = normalize_text(data.get("condition") or data.get("renovation_level"))
    condition_multipliers = {"poor": 0.9, "average": 1.0, "renovated": 1.06, "new": 1.08}
    condition_multiplier = condition_multipliers.get(condition, 1.0)
    if condition:
        explanation.append(f"Condition multiplier: {condition_multiplier:.2f}.")
    monthly_rent *= condition_multiplier

    return RentEstimate(monthly_rent=round(monthly_rent, 2), explanation=explanation)


def calculate_roi(data: dict[str, Any]) -> dict[str, Any]:
    rent_estimate = estimate_monthly_rent(data)

    purchase_price = as_float(data, "purchase_price") or as_float(data, "price")
    renovation_cost = as_float(data, "renovation_cost")
    closing_costs = as_float(data, "closing_costs") or purchase_price * (as_float(data, "closing_cost_rate", 0.12))
    total_investment = purchase_price + renovation_cost + closing_costs

    vacancy_rate = as_float(data, "vacancy_rate", 0.05)
    annual_taxes = as_float(data, "annual_taxes") or as_float(data, "property_tax")
    annual_insurance = as_float(data, "annual_insurance", 600)
    monthly_maintenance = as_float(data, "monthly_maintenance", rent_estimate.monthly_rent * 0.08)
    management_fee_rate = as_float(data, "management_fee_rate", 0)

    annual_rent = rent_estimate.monthly_rent * 12
    vacancy_loss = annual_rent * vacancy_rate
    management_fees = annual_rent * management_fee_rate
    annual_operating_costs = annual_taxes + annual_insurance + monthly_maintenance * 12 + vacancy_loss + management_fees
    net_operating_income = annual_rent - annual_operating_costs

    down_payment = as_float(data, "down_payment")
    loan_amount = as_float(data, "loan_amount")
    if loan_amount == 0 and purchase_price > 0 and down_payment > 0:
        loan_amount = max(purchase_price - down_payment, 0)

    interest_rate = as_float(data, "interest_rate")
    loan_years = as_float(data, "loan_years", 25)
    monthly_debt_service = calculate_monthly_payment(loan_amount, interest_rate, loan_years)
    annual_debt_service = monthly_debt_service * 12

    annual_cash_flow = net_operating_income - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12
    cash_invested = down_payment + renovation_cost + closing_costs if down_payment > 0 else total_investment

    gross_yield = percentage(annual_rent, purchase_price)
    net_yield = percentage(net_operating_income, total_investment)
    cash_on_cash_return = percentage(annual_cash_flow, cash_invested)

    roi_score = score_opportunity(net_yield, cash_on_cash_return, monthly_cash_flow, vacancy_rate)

    return {
        "estimated_monthly_rent": rent_estimate.monthly_rent,
        "rent_estimation_explanation": rent_estimate.explanation,
        "annual_rent": round(annual_rent, 2),
        "purchase_price": round(purchase_price, 2),
        "renovation_cost": round(renovation_cost, 2),
        "closing_costs": round(closing_costs, 2),
        "total_investment": round(total_investment, 2),
        "annual_operating_costs": round(annual_operating_costs, 2),
        "net_operating_income": round(net_operating_income, 2),
        "monthly_debt_service": round(monthly_debt_service, 2),
        "monthly_cash_flow": round(monthly_cash_flow, 2),
        "annual_cash_flow": round(annual_cash_flow, 2),
        "gross_yield": round(gross_yield, 2),
        "net_yield": round(net_yield, 2),
        "cash_on_cash_return": round(cash_on_cash_return, 2),
        "roi_score": roi_score,
    }


def calculate_monthly_payment(loan_amount: float, annual_interest_rate: float, loan_years: float) -> float:
    if loan_amount <= 0 or loan_years <= 0:
        return 0
    monthly_rate = annual_interest_rate / 100 / 12
    number_of_payments = loan_years * 12
    if monthly_rate == 0:
        return loan_amount / number_of_payments
    return loan_amount * (monthly_rate * (1 + monthly_rate) ** number_of_payments) / (
        (1 + monthly_rate) ** number_of_payments - 1
    )


def percentage(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0
    return numerator / denominator * 100


def score_opportunity(net_yield: float, cash_on_cash_return: float, monthly_cash_flow: float, vacancy_rate: float) -> int:
    score = 50
    score += min(max(net_yield - 3, 0) * 5, 25)
    score += min(max(cash_on_cash_return, 0) * 2, 20)
    if monthly_cash_flow > 0:
        score += min(monthly_cash_flow / 100, 10)
    if vacancy_rate > 0.08:
        score -= min((vacancy_rate - 0.08) * 100, 10)
    return int(max(0, min(round(score), 100)))
