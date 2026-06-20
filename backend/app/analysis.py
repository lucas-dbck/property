from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import unicodedata


CITY_RENT_PER_SQM = {
    "brussels": 18.0,
    "bruxelles": 18.0,
    "etterbeek": 19.0,
    "ixelles": 20.0,
    "elsene": 20.0,
    "uccle": 19.0,
    "ukkel": 19.0,
    "schaerbeek": 17.0,
    "schaarbeek": 17.0,
    "anderlecht": 15.5,
    "saint-gilles": 18.0,
    "sint-gillis": 18.0,
    "woluwe-saint-pierre": 19.0,
    "sint-pieters-woluwe": 19.0,
    "woluwe-saint-lambert": 18.5,
    "sint-lambrechts-woluwe": 18.5,
    "antwerp": 16.0,
    "antwerpen": 16.0,
    "ghent": 17.0,
    "gent": 17.0,
    "leuven": 19.0,
    "mechelen": 15.5,
    "duffel": 14.0,
    "zemst": 14.5,
    "malderen": 13.5,
    "londerzeel": 13.5,
    "vilvoorde": 15.0,
    "grimbergen": 15.0,
    "zaventem": 16.0,
    "waterloo": 17.0,
    "aalst": 13.5,
    "bruges": 15.0,
    "brugge": 15.0,
    "kortrijk": 13.5,
    "ostend": 14.0,
    "oostende": 14.0,
    "sint-niklaas": 13.5,
    "turnhout": 13.0,
    "hasselt": 13.5,
    "genk": 12.0,
    "namur": 12.0,
    "namen": 12.0,
    "mons": 11.0,
    "bergen": 11.0,
    "charleroi": 10.5,
    "liege": 12.0,
    "luik": 12.0,
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


def normalize_location(value: Any) -> str:
    text = normalize_text(value).replace("_", "-")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re_collapse_non_words(text)
    return text


def re_collapse_non_words(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def rent_rate_for_location(city: Any, postcode: Any = None) -> tuple[float, str]:
    city_key = normalize_location(city)
    if city_key in CITY_RENT_PER_SQM:
        return CITY_RENT_PER_SQM[city_key], city_key

    raw_postcode = str(postcode or "").strip()
    if raw_postcode.isdigit():
        code = int(raw_postcode)
        if 1000 <= code <= 1299:
            return 18.0, f"postcode {raw_postcode}"
        if 2000 <= code <= 2999:
            return 15.0, f"postcode {raw_postcode}"
        if 3000 <= code <= 3499:
            return 16.5, f"postcode {raw_postcode}"
        if 1500 <= code <= 1999:
            return 15.0, f"postcode {raw_postcode}"
        if 9000 <= code <= 9999:
            return 14.5, f"postcode {raw_postcode}"
        if 8000 <= code <= 8999:
            return 14.0, f"postcode {raw_postcode}"
        if 3500 <= code <= 3999:
            return 13.0, f"postcode {raw_postcode}"
        if 4000 <= code <= 7999:
            return 11.5, f"postcode {raw_postcode}"

    return 14.0, city_key or "unknown city"


def estimate_monthly_rent(data: dict[str, Any]) -> RentEstimate:
    known_rent = as_float(data, "monthly_rent") or as_float(data, "expected_monthly_rent") or as_float(data, "estimated_rent")
    if known_rent > 0:
        return RentEstimate(
            monthly_rent=round(known_rent, 2),
            explanation=["Used rent provided by the user or imported listing data."],
        )

    city = data.get("city")
    postcode = data.get("postcode") or data.get("postal_code")
    area_sqm = as_float(data, "area_sqm") or as_float(data, "living_area") or as_float(data, "size_sqm")
    bedrooms = as_float(data, "bedrooms")
    base_rent_per_sqm, location_label = rent_rate_for_location(city, postcode)
    explanation = [f"Base rent for {location_label}: EUR {base_rent_per_sqm:.2f}/m2."]

    if area_sqm <= 0:
        area_sqm = estimate_area_from_basics(data, bedrooms)
        if area_sqm > 0:
            explanation.append(f"Living area missing, estimated {area_sqm:.0f} m2 from bedrooms/property type.")

    if area_sqm > 0:
        monthly_rent = area_sqm * base_rent_per_sqm
        explanation.append(f"Area adjustment: {area_sqm:.0f} m2 used.")
    else:
        monthly_rent = 650
        explanation.append("Area and bedrooms missing, used minimum fallback rent.")

    energy_score = normalize_text(data.get("energy_score"))
    energy_multiplier = ENERGY_MULTIPLIERS.get(energy_score, 1.0)
    if energy_score:
        explanation.append(f"Energy score {energy_score.upper()} multiplier: {energy_multiplier:.2f}.")
    monthly_rent *= energy_multiplier

    condition = normalize_text(data.get("condition") or data.get("renovation_level"))
    condition_multipliers = {"poor": 0.9, "average": 1.0, "renovated": 1.06, "new": 1.08}
    condition_multiplier = condition_multipliers.get(condition, 1.0)
    if condition:
        explanation.append(f"Condition multiplier: {condition_multiplier:.2f}.")
    monthly_rent *= condition_multiplier

    return RentEstimate(monthly_rent=round(monthly_rent, 2), explanation=explanation)


def estimate_area_from_basics(data: dict[str, Any], bedrooms: float) -> float:
    property_type = normalize_text(data.get("property_type"))
    if bedrooms > 0:
        area = 42 + bedrooms * 18
        if "house" in property_type or "villa" in property_type:
            area += 20
        return area
    if "studio" in property_type:
        return 38
    if "house" in property_type or "villa" in property_type:
        return 115
    if "apartment" in property_type or "flat" in property_type:
        return 65
    return 0


def enrich_default_assumptions(data: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(data)
    purchase_price = as_float(enriched, "purchase_price") or as_float(enriched, "price")
    area_sqm = as_float(enriched, "area_sqm") or as_float(enriched, "living_area") or as_float(enriched, "size_sqm")
    condition = normalize_text(enriched.get("condition") or enriched.get("renovation_level"))

    if purchase_price > 0 and as_float(enriched, "purchase_costs") == 0 and as_float(enriched, "closing_costs") == 0:
        # Belgian buyer costs are high; use a conservative default the user can edit.
        enriched["purchase_costs"] = round(purchase_price * 0.12, 2)

    if area_sqm > 0 and as_float(enriched, "renovation_cost") == 0:
        cost_per_sqm = {
            "poor": 900,
            "to renovate": 900,
            "average": 350,
            "good": 200,
            "renovated": 75,
            "new": 0,
        }.get(condition, 250)
        enriched["renovation_cost"] = round(area_sqm * cost_per_sqm, 2)

    if as_float(enriched, "annual_operating_costs") == 0 and as_float(enriched, "operating_costs") == 0:
        rent_estimate = estimate_monthly_rent(enriched)
        annual_rent = rent_estimate.monthly_rent * 12
        enriched["annual_operating_costs"] = round(max(annual_rent * 0.15, 1200), 2)

    project_cost = (
        purchase_price
        + as_float(enriched, "renovation_cost")
        + (as_float(enriched, "purchase_costs") or as_float(enriched, "closing_costs"))
    )
    if project_cost > 0 and as_float(enriched, "down_payment") == 0:
        enriched["down_payment"] = round(project_cost * 0.2, 2)

    if as_float(enriched, "interest_rate") == 0:
        enriched["interest_rate"] = 3.5

    if as_float(enriched, "loan_years") == 0:
        enriched["loan_years"] = 25

    if "vacancy_rate" not in enriched or enriched.get("vacancy_rate") in (None, ""):
        enriched["vacancy_rate"] = 0.05

    return enriched


def calculate_roi(data: dict[str, Any]) -> dict[str, Any]:
    data = enrich_default_assumptions(data)
    rent_estimate = estimate_monthly_rent(data)

    purchase_price = as_float(data, "purchase_price") or as_float(data, "price")
    renovation_cost = as_float(data, "renovation_cost")
    purchase_costs = as_float(data, "purchase_costs") or as_float(data, "closing_costs")
    total_investment = purchase_price + renovation_cost + purchase_costs

    annual_rent = rent_estimate.monthly_rent * 12
    annual_operating_costs = get_annual_operating_costs(data, annual_rent, rent_estimate.monthly_rent)
    net_operating_income = annual_rent - annual_operating_costs

    down_payment = as_float(data, "down_payment")
    loan_amount = as_float(data, "loan_amount")
    if loan_amount == 0 and total_investment > 0 and down_payment > 0:
        loan_amount = max(total_investment - down_payment, 0)

    interest_rate = as_float(data, "interest_rate")
    loan_years = as_float(data, "loan_years", 25)
    manual_monthly_debt_service = as_float(data, "monthly_debt_service") or as_float(data, "monthly_loan_payment")
    monthly_debt_service = manual_monthly_debt_service or calculate_monthly_payment(
        loan_amount,
        interest_rate,
        loan_years,
    )
    annual_debt_service = monthly_debt_service * 12

    annual_cash_flow = net_operating_income - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12
    cash_invested = down_payment if down_payment > 0 else total_investment

    # Standard property investment formulas:
    # gross yield = annual rent / purchase price
    # net yield = net operating income / total investment
    # ROI = annual net profit / total cash invested
    gross_yield = percentage(annual_rent, purchase_price)
    net_yield = percentage(net_operating_income, total_investment)
    cash_on_cash_return = percentage(annual_cash_flow, cash_invested)

    vacancy_rate = as_float(data, "vacancy_rate", 0)
    roi_score = score_opportunity(net_yield, cash_on_cash_return, monthly_cash_flow, vacancy_rate)

    return {
        "estimated_monthly_rent": rent_estimate.monthly_rent,
        "rent_estimation_explanation": rent_estimate.explanation,
        "annual_rent": round(annual_rent, 2),
        "purchase_price": round(purchase_price, 2),
        "renovation_cost": round(renovation_cost, 2),
        "purchase_costs": round(purchase_costs, 2),
        "closing_costs": round(purchase_costs, 2),
        "total_investment": round(total_investment, 2),
        "total_cash_invested": round(cash_invested, 2),
        "annual_operating_costs": round(annual_operating_costs, 2),
        "net_operating_income": round(net_operating_income, 2),
        "monthly_debt_service": round(monthly_debt_service, 2),
        "monthly_loan_payment": round(monthly_debt_service, 2),
        "loan_amount": round(loan_amount, 2),
        "down_payment": round(down_payment, 2),
        "interest_rate": round(interest_rate, 2),
        "loan_years": round(loan_years, 2),
        "monthly_cash_flow": round(monthly_cash_flow, 2),
        "annual_cash_flow": round(annual_cash_flow, 2),
        "gross_yield": round(gross_yield, 2),
        "net_yield": round(net_yield, 2),
        "cash_on_cash_return": round(cash_on_cash_return, 2),
        "roi_score": roi_score,
        "gross_yield_formula": "annual_rent / purchase_price",
        "net_yield_formula": "net_operating_income / total_investment",
        "cash_on_cash_formula": "annual_net_profit / total_cash_invested",
    }


def get_annual_operating_costs(data: dict[str, Any], annual_rent: float, monthly_rent: float) -> float:
    bucket = as_float(data, "annual_operating_costs") or as_float(data, "operating_costs")
    if bucket > 0:
        return bucket

    vacancy_rate = as_float(data, "vacancy_rate", 0.05)
    annual_taxes = as_float(data, "annual_taxes") or as_float(data, "property_tax")
    annual_insurance = as_float(data, "annual_insurance", 600)
    monthly_maintenance = as_float(data, "monthly_maintenance", monthly_rent * 0.08)
    management_fee_rate = as_float(data, "management_fee_rate", 0)

    vacancy_loss = annual_rent * vacancy_rate
    management_fees = annual_rent * management_fee_rate
    return annual_taxes + annual_insurance + monthly_maintenance * 12 + vacancy_loss + management_fees


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
