"""
Rate Card & Commercial Calculator — Real calculations, not LLM-generated numbers.
Provides configurable rate cards and performs actual month-wise resource loading math.

Default hourly rates (when no rate card uploaded):
  Onshore:   $120/hr  →  $19,200/month
  Nearshore: $90/hr   →  $14,400/month
  Offshore:  $30/hr   →  $4,800/month
"""

from typing import Any, Dict, List, Optional
from app.config import settings

HOURS_PER_MONTH = 160  # Standard billable hours


def _build_default_rate_card() -> Dict:
    """Build the default rate card from config settings.
    Uses DEFAULT_RATE_ONSHORE/NEARSHORE/OFFSHORE_USD from .env.
    Junior roles get a 0.83x discount; test engineers get 0.67x.
    """
    on = settings.DEFAULT_RATE_ONSHORE_USD * HOURS_PER_MONTH
    ne = settings.DEFAULT_RATE_NEARSHORE_USD * HOURS_PER_MONTH
    off = settings.DEFAULT_RATE_OFFSHORE_USD * HOURS_PER_MONTH
    # Junior discount multipliers
    on_jr = round(on * 0.83)
    ne_jr = round(ne * 0.83)
    off_jr = round(off * 0.83)
    roles = [
        "Service Delivery Manager",
        "Program Manager",
        "Solution Architect",
        "Technical Lead",
        "Senior Consultant",
        "Consultant",
        "Test Lead",
        "DevOps Engineer",
        "Integration Specialist",
        "Business Analyst",
        "Change Manager",
        "Service Owner",
    ]
    junior_roles = {"Associate Consultant", "Test Engineer"}
    card = {"onshore": {}, "nearshore": {}, "offshore": {}}
    for role in roles:
        card["onshore"][role] = on
        card["nearshore"][role] = ne
        card["offshore"][role] = off
    for role in junior_roles:
        card["onshore"][role] = on_jr
        card["nearshore"][role] = ne_jr
        card["offshore"][role] = off_jr
    return card


# Lazily-built default rate card — reads from settings at startup
DEFAULT_RATE_CARD = _build_default_rate_card()

# In-memory store for user-configured rate cards
_rate_cards: Dict[str, Dict] = {"default": DEFAULT_RATE_CARD}
_active_card: str = "default"


def get_rate_card(name: str = None) -> Dict:
    return _rate_cards.get(name or _active_card, DEFAULT_RATE_CARD)


def set_rate_card(name: str, card: Dict):
    _rate_cards[name] = card


def set_active_rate_card(name: str):
    global _active_card
    _active_card = name


def build_rate_card_from_hourly(
    onshore_hr: float = 120, nearshore_hr: float = 90, offshore_hr: float = 30
) -> Dict:
    """Build a full rate card from simple hourly rates (user-provided in bid creation form)."""
    roles = list(DEFAULT_RATE_CARD["onshore"].keys())
    card = {"onshore": {}, "nearshore": {}, "offshore": {}}
    for role in roles:
        # Senior roles get a 10% premium, juniors get 15% discount
        if "Associate" in role or "Test Engineer" in role:
            mult = 0.85
        elif (
            "Manager" in role
            or "Architect" in role
            or "Owner" in role
            or "Lead" in role
        ):
            mult = 1.10
        else:
            mult = 1.0
        card["onshore"][role] = round(onshore_hr * HOURS_PER_MONTH * mult)
        card["nearshore"][role] = round(nearshore_hr * HOURS_PER_MONTH * mult)
        card["offshore"][role] = round(offshore_hr * HOURS_PER_MONTH * mult)
    return card


def get_rate(role: str, location: str, rate_card: Dict = None) -> float:
    """Get monthly rate for a role at a location. Fuzzy matches role names."""
    card = rate_card or get_rate_card()
    loc_rates = card.get(location, card.get("offshore", {}))

    # Exact match
    if role in loc_rates:
        return loc_rates[role]

    # Fuzzy match
    role_lower = role.lower()
    for k, v in loc_rates.items():
        if k.lower() in role_lower or role_lower in k.lower():
            return v

    # Default to Consultant rate
    return loc_rates.get("Consultant", 4800)


def calculate_resource_loading(
    resources: List[Dict],
    contract_months: int = 24,
    transition_months: int = 2,
    ramp_schedule: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate month-wise resource loading with real math.

    resources: [{"role": str, "count": float, "location": "onshore|offshore|nearshore", "start_month": int}]
    contract_months: total contract duration
    transition_months: months of transition/ramp-up at start
    ramp_schedule: list of utilization % per month during ramp (e.g. [0.25, 0.5, 0.75, 1.0])
    """
    if not ramp_schedule:
        ramp_schedule = [0.25, 0.50, 0.75, 1.0]

    rate_card = get_rate_card()
    monthly_breakdown = []
    total_cost = 0
    total_fte_months = 0

    for month in range(1, contract_months + 1):
        month_data = {"month": month, "resources": [], "total_fte": 0, "total_cost": 0}

        for res in resources:
            role = res["role"]
            base_count = res.get("count", 1)
            location = res.get("location", "offshore")
            start_month = res.get("start_month", 1)

            if month < start_month:
                continue

            # Apply ramp-up during transition
            months_since_start = month - start_month
            if months_since_start < len(ramp_schedule):
                fte = base_count * ramp_schedule[months_since_start]
            else:
                fte = base_count

            monthly_rate = get_rate(role, location, rate_card)
            cost = fte * monthly_rate

            month_data["resources"].append(
                {
                    "role": role,
                    "location": location,
                    "fte": round(fte, 2),
                    "monthly_rate": monthly_rate,
                    "cost": round(cost, 2),
                }
            )
            month_data["total_fte"] += fte
            month_data["total_cost"] += cost

        month_data["total_fte"] = round(month_data["total_fte"], 2)
        month_data["total_cost"] = round(month_data["total_cost"], 2)
        monthly_breakdown.append(month_data)
        total_cost += month_data["total_cost"]
        total_fte_months += month_data["total_fte"]

    # Summary by location
    onshore_cost = sum(
        r["cost"]
        for m in monthly_breakdown
        for r in m["resources"]
        if r["location"] == "onshore"
    )
    nearshore_cost = sum(
        r["cost"]
        for m in monthly_breakdown
        for r in m["resources"]
        if r["location"] == "nearshore"
    )
    offshore_cost = sum(
        r["cost"]
        for m in monthly_breakdown
        for r in m["resources"]
        if r["location"] == "offshore"
    )

    # Summary by role
    role_summary = {}
    for m in monthly_breakdown:
        for r in m["resources"]:
            key = f"{r['role']} ({r['location']})"
            if key not in role_summary:
                role_summary[key] = {
                    "total_cost": 0,
                    "total_fte_months": 0,
                    "monthly_rate": r["monthly_rate"],
                }
            role_summary[key]["total_cost"] += r["cost"]
            role_summary[key]["total_fte_months"] += r["fte"]

    # Steady-state monthly cost (after ramp)
    steady_months = [
        m
        for m in monthly_breakdown
        if m["month"] > transition_months + len(ramp_schedule)
    ]
    avg_monthly = (
        sum(m["total_cost"] for m in steady_months) / len(steady_months)
        if steady_months
        else 0
    )

    return {
        "monthly_breakdown": monthly_breakdown,
        "total_contract_cost": round(total_cost, 2),
        "total_fte_months": round(total_fte_months, 2),
        "average_monthly_cost": round(avg_monthly, 2),
        "cost_by_location": {
            "onshore": round(onshore_cost, 2),
            "nearshore": round(nearshore_cost, 2),
            "offshore": round(offshore_cost, 2),
        },
        "role_summary": role_summary,
        "contract_months": contract_months,
    }


def calculate_pl(
    resource_loading: Dict[str, Any],
    target_margin_percent: float = 25.0,
    sga_percent: float = 8.0,
    transition_cost: float = 0,
    tools_monthly: float = 0,
    travel_annual: float = 0,
    contingency_percent: float = 5.0,
) -> Dict[str, Any]:
    """Calculate real P&L from resource loading."""
    total_cost = resource_loading["total_contract_cost"]
    contract_months = resource_loading["contract_months"]
    contract_years = contract_months / 12

    # Direct costs
    direct_delivery = total_cost
    transition = transition_cost
    tools = tools_monthly * contract_months
    travel = travel_annual * contract_years
    contingency = direct_delivery * (contingency_percent / 100)

    total_direct = direct_delivery + transition + tools + travel + contingency

    # SG&A
    sga = total_direct * (sga_percent / 100)
    total_cogs = total_direct + sga

    # Revenue (to hit target margin)
    revenue = total_cogs / (1 - target_margin_percent / 100)
    gross_profit = revenue - total_cogs
    actual_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

    # Monthly pricing
    monthly_price = revenue / contract_months
    annual_revenue = revenue / contract_years

    return {
        "revenue": {
            "total_contract_value": round(revenue, 2),
            "annual_revenue": round(annual_revenue, 2),
            "monthly_price": round(monthly_price, 2),
        },
        "costs": {
            "direct_delivery": round(direct_delivery, 2),
            "transition": round(transition, 2),
            "tools_infra": round(tools, 2),
            "travel": round(travel, 2),
            "contingency": round(contingency, 2),
            "total_direct": round(total_direct, 2),
            "sga": round(sga, 2),
            "total_cogs": round(total_cogs, 2),
        },
        "profitability": {
            "gross_profit": round(gross_profit, 2),
            "margin_percent": round(actual_margin, 2),
            "target_margin": target_margin_percent,
        },
        "per_month": {
            "avg_delivery_cost": round(direct_delivery / contract_months, 2),
            "price_to_client": round(monthly_price, 2),
            "monthly_margin": round(gross_profit / contract_months, 2),
        },
    }


def calculate_scenarios(
    resources: list,
    contract_months: int = 24,
    transition_months: int = 2,
    transition_cost: float = 0,
    tools_monthly: float = 0,
    travel_annual: float = 0,
    contingency_percent: float = 5.0,
    target_margin_percent: float = 25.0,
) -> Dict[str, Any]:
    """
    Generate 3 commercial scenarios: Base, Aggressive, Conservative.
    All margins derived from the target_margin_percent (set by LLM from RFP analysis):
    - Base: target margin as-is
    - Aggressive: target margin - 7% with 10% fewer resources
    - Conservative: target margin + 5% with 15% buffer on resources
    """
    scenarios = {}
    aggressive_margin = max(target_margin_percent - 7, 10)
    conservative_margin = target_margin_percent + 5

    # --- BASE SCENARIO ---
    base_loading = calculate_resource_loading(
        resources, contract_months, transition_months
    )
    base_pl = calculate_pl(
        base_loading,
        target_margin_percent=target_margin_percent,
        transition_cost=transition_cost,
        tools_monthly=tools_monthly,
        travel_annual=travel_annual,
        contingency_percent=contingency_percent,
    )
    scenarios["base"] = {
        "label": "Base Case",
        "description": f"Standard pricing with {target_margin_percent:.0f}% target margin (derived from RFP analysis)",
        "margin_target": target_margin_percent,
        "resource_loading": base_loading,
        "pl_model": base_pl,
    }

    # --- AGGRESSIVE SCENARIO ---
    aggressive_resources = []
    for r in resources:
        ar = dict(r)
        ar["count"] = round(r.get("count", 1) * 0.9, 2)  # 10% fewer FTEs
        aggressive_resources.append(ar)
    agg_loading = calculate_resource_loading(
        aggressive_resources, contract_months, transition_months
    )
    agg_pl = calculate_pl(
        agg_loading,
        target_margin_percent=aggressive_margin,
        transition_cost=transition_cost,
        tools_monthly=tools_monthly,
        travel_annual=travel_annual,
        contingency_percent=max(contingency_percent - 2, 1),
    )
    scenarios["aggressive"] = {
        "label": "Aggressive",
        "description": f"Competitive pricing with leaner team ({aggressive_margin:.0f}% margin, 10% fewer FTEs)",
        "margin_target": aggressive_margin,
        "resource_loading": agg_loading,
        "pl_model": agg_pl,
    }

    # --- CONSERVATIVE SCENARIO ---
    cons_resources = []
    for r in resources:
        cr = dict(r)
        cr["count"] = round(r.get("count", 1) * 1.15, 2)  # 15% more FTEs
        cons_resources.append(cr)
    cons_loading = calculate_resource_loading(
        cons_resources, contract_months, transition_months
    )
    cons_pl = calculate_pl(
        cons_loading,
        target_margin_percent=conservative_margin,
        transition_cost=transition_cost * 1.2,
        tools_monthly=tools_monthly,
        travel_annual=travel_annual * 1.2,
        contingency_percent=contingency_percent + 3,
    )
    scenarios["conservative"] = {
        "label": "Conservative",
        "description": f"Risk-adjusted pricing with buffer team ({conservative_margin:.0f}% margin, 15% more FTEs)",
        "margin_target": conservative_margin,
        "resource_loading": cons_loading,
        "pl_model": cons_pl,
    }

    # Comparison summary
    comparison = {
        "base_tcv": base_pl["revenue"]["total_contract_value"],
        "aggressive_tcv": agg_pl["revenue"]["total_contract_value"],
        "conservative_tcv": cons_pl["revenue"]["total_contract_value"],
        "base_margin": base_pl["profitability"]["margin_percent"],
        "aggressive_margin": agg_pl["profitability"]["margin_percent"],
        "conservative_margin": cons_pl["profitability"]["margin_percent"],
        "tcv_range": f"${agg_pl['revenue']['total_contract_value']:,.0f} — ${cons_pl['revenue']['total_contract_value']:,.0f}",
    }

    return {"scenarios": scenarios, "comparison": comparison}


def check_margin_guardrails(margin_percent: float) -> Dict[str, Any]:
    """
    Enforce PRD margin guardrails:
    - >= 18%: PASS — no action needed
    - 12-18%: FLAG — requires named Practice Director approval
    - < 12%: BLOCK — bid paused, escalation to Practice Head
    """
    if margin_percent >= 18:
        return {
            "status": "pass",
            "level": "green",
            "message": f"Margin {margin_percent:.1f}% meets threshold (≥18%)",
            "action_required": None,
            "approver_required": None,
        }
    elif margin_percent >= 12:
        return {
            "status": "flag",
            "level": "amber",
            "message": f"Margin {margin_percent:.1f}% below standard threshold (18%). Requires Practice Director approval.",
            "action_required": "Named approval required before pipeline progression",
            "approver_required": "Practice Director",
        }
    else:
        return {
            "status": "block",
            "level": "red",
            "message": f"Margin {margin_percent:.1f}% critically below minimum (12%). Bid paused — escalation required.",
            "action_required": "Bid paused. Practice Head / EVP must review and explicitly approve continuation.",
            "approver_required": "Practice Head / EVP",
        }


def check_discount_authority(discount_percent: float) -> Dict[str, Any]:
    """
    PRD discount authority matrix:
    - 0-5%: Bid Manager authority
    - 5-15%: Practice Director authority
    - 15%+: EVP / Commercial Head authority
    """
    if discount_percent <= 5:
        return {
            "level": "standard",
            "approver": "Bid Manager",
            "message": f"{discount_percent:.1f}% discount within Bid Manager authority",
        }
    elif discount_percent <= 15:
        return {
            "level": "elevated",
            "approver": "Practice Director",
            "message": f"{discount_percent:.1f}% discount requires Practice Director approval",
        }
    else:
        return {
            "level": "executive",
            "approver": "EVP / Commercial Head",
            "message": f"{discount_percent:.1f}% discount requires EVP/Commercial Head approval",
        }
