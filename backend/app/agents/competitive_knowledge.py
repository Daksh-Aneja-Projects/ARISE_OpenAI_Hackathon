"""
Competitive Intelligence Knowledge Base — Application-agnostic competitive context.

Provides deal-specific competitive intelligence by combining:
  1. Bidder profile from manifest["bidder_profile"] (or generic fallback)
  2. Dynamic competitor discovery based on deal type, products, geography
  3. Industry-standard competitive frameworks (not vendor-specific)

The closed loop works here too: feedback_learning captures win/loss outcomes,
which are stored as learnings. On future bids, get_past_learnings() injects
"We lost to X because Y" insights into competitive analysis prompts.

MIGRATION NOTE: This file was originally named `hcltech_competitive.py` with 540 lines
of hardcoded HCLTech/HCM-specific data. It has been refactored to `competitive_knowledge.py`
and is now fully application-agnostic while maintaining the same public API
(`get_competitive_context`, `format_competitive_context_for_prompt`) so downstream agents don't break.
"""

from typing import Dict, Any


# ── Deal-Type Competitor Archetypes ────────────────────────────────────────────
# Instead of hardcoding specific vendors, we define the TYPES of competitors
# that typically appear for each deal type. The LLM uses these archetypes
# plus the specific products/geography to identify actual competitors.

DEAL_TYPE_ARCHETYPES = {
    "AMS": {
        "competitor_types": [
            "Tier-1 IT Services (Accenture, TCS, Infosys, Wipro, Cognizant, HCLTech, Capgemini)",
            "Tier-2 Specialists (DXC, LTIMindtree, Tech Mahindra, Mphasis)",
            "Product-native consulting arms (if product vendor offers managed services)",
            "Boutique/niche AMS providers in the client's industry vertical",
        ],
        "key_evaluation_factors": [
            "Delivery cost (offshore leverage)",
            "Platform-specific certified resources",
            "SLA track record and penalty management",
            "Automation and continuous improvement roadmap",
            "Transition risk — safe handover from incumbent",
        ],
        "pricing_dynamics": "Cost-competitive with demonstrable YOY efficiency gains",
    },
    "Implementation": {
        "competitor_types": [
            "Big 4 Advisory (Deloitte, EY, PwC, KPMG)",
            "Tier-1 System Integrators (Accenture, Infosys, TCS, Capgemini)",
            "Product-native implementation partners (vendor-certified SIs)",
            "Regional boutique SIs with deep vertical expertise",
        ],
        "key_evaluation_factors": [
            "Implementation methodology and accelerators",
            "Certified consultants on the specific platform",
            "Reference implementations in the client's industry",
            "Go-live success rate and defect density",
            "Post-go-live support and warranty terms",
        ],
        "pricing_dynamics": "Value-based with milestone payments and risk-sharing",
    },
    "Advisory": {
        "competitor_types": [
            "Big 4 Advisory (Deloitte, EY, PwC, KPMG)",
            "Strategy consultancies (McKinsey, BCG, Bain — for strategic scope)",
            "Product vendor professional services",
            "Independent advisory firms (Gartner consulting, ISG, Everest Group)",
        ],
        "key_evaluation_factors": [
            "Industry expertise and thought leadership",
            "Senior consultant experience and credentials",
            "Vendor-agnostic recommendations",
            "Quality of deliverables and frameworks",
        ],
        "pricing_dynamics": "Premium — daily rate driven, expertise-weighted",
    },
    "Transformation": {
        "competitor_types": [
            "Tier-1 IT Services with transformation practices",
            "Big 4 Advisory with implementation arms",
            "Cloud hyperscaler partners (AWS/Azure/GCP partner ecosystem)",
            "Digital-native consultancies (Thoughtworks, EPAM, Publicis Sapient)",
        ],
        "key_evaluation_factors": [
            "End-to-end transformation capability",
            "Change management and adoption expertise",
            "Technology modernization accelerators",
            "Business outcome commitment and risk-sharing",
        ],
        "pricing_dynamics": "Outcome-based with transformation incentives",
    },
}

# Default archetype for unknown deal types
DEFAULT_ARCHETYPE = DEAL_TYPE_ARCHETYPES["AMS"]


def _get_bidder_profile(bidder_profile: dict = None) -> dict:
    """Extract or build a bidder profile for competitive positioning.

    If manifest provides a bidder_profile, use it. Otherwise return
    a generic template that the LLM can work with.
    """
    if (
        bidder_profile
        and isinstance(bidder_profile, dict)
        and bidder_profile.get("name")
    ):
        return {
            "name": bidder_profile["name"],
            "type": bidder_profile.get("type", "IT Services & Consulting"),
            "key_strengths": bidder_profile.get(
                "strengths",
                [
                    "Global delivery capability",
                    "Competitive cost structure",
                    "Platform-certified resources",
                    "Proven AMS/implementation track record",
                ],
            ),
            "key_weaknesses": bidder_profile.get(
                "weaknesses",
                [
                    "Assess based on specific deal requirements",
                ],
            ),
            "certifications": bidder_profile.get("certifications", []),
            "employees": bidder_profile.get("employees", ""),
            "revenue": bidder_profile.get("revenue", ""),
        }
    # Generic fallback — forces the agent to be honest about what it knows
    return {
        "name": "[Bidder]",
        "type": "Enterprise IT Services Provider",
        "key_strengths": [
            "Global delivery capability with onshore/offshore model",
            "Platform-certified technical resources",
            "Automation and AI-driven service optimization",
            "Compliance frameworks (ISO 27001, SOC 2, GDPR)",
            "Follow-the-sun support capability",
        ],
        "key_weaknesses": [
            "Specific weaknesses should be assessed against deal requirements",
        ],
        "certifications": [],
        "employees": "",
        "revenue": "",
    }


def _get_deal_archetype(deal_type: str) -> dict:
    """Get the competitor archetype for this deal type."""
    dt = deal_type.upper().strip() if deal_type else "AMS"
    for key in DEAL_TYPE_ARCHETYPES:
        if key in dt or dt in key:
            return DEAL_TYPE_ARCHETYPES[key]
    # Check for hybrid/combined
    if any(kw in dt for kw in ("HYBRID", "MANAGED", "SUPPORT")):
        return DEAL_TYPE_ARCHETYPES["AMS"]
    if any(kw in dt for kw in ("IMPLEMENT", "DEPLOY", "ROLLOUT")):
        return DEAL_TYPE_ARCHETYPES["Implementation"]
    if any(kw in dt for kw in ("ADVISORY", "CONSULTING", "STRATEGY")):
        return DEAL_TYPE_ARCHETYPES["Advisory"]
    if any(kw in dt for kw in ("TRANSFORM", "MODERNIZ", "DIGITAL")):
        return DEAL_TYPE_ARCHETYPES["Transformation"]
    return DEFAULT_ARCHETYPE


def _estimate_deal_tier(estimated_tcv: float = None, products: list = None) -> str:
    """Classify deal size for competitive positioning."""
    if estimated_tcv:
        if estimated_tcv > 20_000_000:
            return "enterprise"
        elif estimated_tcv > 5_000_000:
            return "mid-market"
        else:
            return "emerging"
    # Infer from product count if TCV not available
    if products and len(products) >= 8:
        return "enterprise"
    elif products and len(products) >= 4:
        return "mid-market"
    return "emerging"


def get_competitive_context(
    deal_type: str = "AMS",
    products: list = None,
    industry: str = "",
    geography: list = None,
    estimated_tcv: float = None,
    is_incumbent: bool = False,
    bidder_profile: dict = None,
) -> Dict[str, Any]:
    """Build competitive context for a specific deal.

    This is the main API — called by CompetitiveIntelAgent.
    Returns a structured dict with bidder profile, deal archetype,
    and competitive positioning guidance.
    """
    products = products or []
    geography = geography or []

    bidder = _get_bidder_profile(bidder_profile)
    archetype = _get_deal_archetype(deal_type)
    deal_tier = _estimate_deal_tier(estimated_tcv, products)

    # Build product-specific competitive signals
    product_signals = []
    for p in products:
        p_lower = p.lower()
        if any(
            kw in p_lower
            for kw in ("workday", "successfactors", "oracle hcm", "ukg", "ceridian")
        ):
            product_signals.append(
                f"{p}: HCM/WFM platform — evaluate vendor partnership tier and certified consultant count"
            )
        elif any(kw in p_lower for kw in ("sap", "s/4hana", "ecc")):
            product_signals.append(
                f"{p}: SAP ecosystem — evaluate SAP partnership level and implementation credentials"
            )
        elif any(kw in p_lower for kw in ("salesforce", "dynamics")):
            product_signals.append(
                f"{p}: CRM platform — evaluate CRM practice size and implementation track record"
            )
        elif any(kw in p_lower for kw in ("azure", "aws", "gcp", "cloud")):
            product_signals.append(
                f"{p}: Cloud platform — evaluate cloud partnership tier and migration credentials"
            )
        elif any(kw in p_lower for kw in ("servicenow", "jira", "itsm")):
            product_signals.append(
                f"{p}: ITSM platform — evaluate ITSM practice and automation capabilities"
            )
        elif any(
            kw in p_lower for kw in ("power bi", "tableau", "databricks", "snowflake")
        ):
            product_signals.append(
                f"{p}: Data/Analytics platform — evaluate data engineering and analytics capabilities"
            )
        else:
            product_signals.append(
                f"{p}: Evaluate certified resource pool and implementation experience"
            )

    # Geographic competitive factors
    geo_factors = []
    if geography:
        if len(geography) > 10:
            geo_factors.append(
                "Large multi-geography deal — favors Tier-1 providers with global delivery presence"
            )
        if any(
            g.lower() in ("netherlands", "germany", "france", "uk") for g in geography
        ):
            geo_factors.append(
                "European presence — GDPR compliance and EU data residency requirements favor providers with EU delivery centers"
            )
        if any(
            g.lower() in ("us", "usa", "united states", "canada") for g in geography
        ):
            geo_factors.append(
                "North American presence — requires onshore delivery capability and potentially ITAR/FedRAMP compliance"
            )

    return {
        "bidder_profile": bidder,
        "deal_type": deal_type,
        "deal_tier": deal_tier,
        "archetype": archetype,
        "product_signals": product_signals,
        "geo_factors": geo_factors,
        "is_incumbent": is_incumbent,
        "products": products,
        "industry": industry,
        "geography": geography,
    }


def format_competitive_context_for_prompt(ctx: Dict[str, Any]) -> str:
    """Format competitive context into a prompt-ready string.

    This is the second public API — called by CompetitiveIntelAgent
    to inject competitive intelligence into the LLM prompt.
    """
    bidder = ctx.get("bidder_profile", {})
    archetype = ctx.get("archetype", DEFAULT_ARCHETYPE)
    bidder_name = bidder.get("name", "[Bidder]")

    lines = [
        "=== COMPETITIVE INTELLIGENCE CONTEXT ===",
        "",
        "--- BIDDER PROFILE ---",
        f"Name: {bidder_name}",
        f"Type: {bidder.get('type', 'IT Services')}",
    ]

    if bidder.get("employees"):
        lines.append(f"Scale: {bidder['employees']} employees")
    if bidder.get("revenue"):
        lines.append(f"Revenue: {bidder['revenue']}")

    strengths = bidder.get("key_strengths", [])
    if strengths:
        lines.append("Key Strengths:")
        for s in strengths:
            lines.append(f"  - {s}")

    weaknesses = bidder.get("key_weaknesses", [])
    if weaknesses:
        lines.append("Known Gaps (self-assess):")
        for w in weaknesses:
            lines.append(f"  - {w}")

    lines.append("")
    lines.append("--- DEAL CONTEXT ---")
    lines.append(f"Deal Type: {ctx.get('deal_type', 'AMS')}")
    lines.append(f"Deal Tier: {ctx.get('deal_tier', 'mid-market')}")
    lines.append(f"Industry: {ctx.get('industry', 'Not specified')}")
    lines.append(f"Products: {', '.join(ctx.get('products', []))}")
    lines.append(f"Geography: {', '.join(ctx.get('geography', []))}")
    lines.append(
        f"Incumbent: {'Yes — defending' if ctx.get('is_incumbent') else 'No — challenging'}"
    )

    lines.append("")
    lines.append(
        f"--- LIKELY COMPETITOR TYPES (for {ctx.get('deal_type', 'this deal type')}) ---"
    )
    for ct in archetype.get("competitor_types", []):
        lines.append(f"  - {ct}")

    lines.append("")
    lines.append("--- EVALUATION FACTORS (what clients score on) ---")
    for ef in archetype.get("key_evaluation_factors", []):
        lines.append(f"  - {ef}")

    lines.append("")
    lines.append("--- PRICING DYNAMICS ---")
    lines.append(f"  {archetype.get('pricing_dynamics', 'Competitive')}")

    product_signals = ctx.get("product_signals", [])
    if product_signals:
        lines.append("")
        lines.append("--- PRODUCT-SPECIFIC COMPETITIVE SIGNALS ---")
        for ps in product_signals:
            lines.append(f"  - {ps}")

    geo_factors = ctx.get("geo_factors", [])
    if geo_factors:
        lines.append("")
        lines.append("--- GEOGRAPHIC COMPETITIVE FACTORS ---")
        for gf in geo_factors:
            lines.append(f"  - {gf}")

    lines.append("")
    lines.append(
        f"IMPORTANT: Use this context to identify REAL competitors likely to bid on this deal. "
        f"Generate win themes specific to {bidder_name}'s strengths vs. those competitors. "
        f"Do NOT invent capabilities — if {bidder_name}'s profile doesn't list a strength, don't claim it."
    )

    return "\n".join(lines)
