"""
Client Intelligence Agent â€” Web-powered client research, market position & win strategy.

L9 Strategic Capabilities:
  - Web research enrichment (real-time public data on client)
  - Procurement maturity classification (first-time outsourcing, rebid, consolidation)
  - Technology maturity scoring (cloud-native, legacy, hybrid)
  - Decision-maker mapping inference from RFP language patterns
  - Financial health indicators from public signals
  - Deal-type agnostic: works for AMS, Implementation, Transformation, Advisory, Hybrid

Output: Company profile, technology landscape, procurement signals, win strategy inputs, risk factors.
100% RFP-driven â€” zero hardcoded vendor/product/client references.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class ClientIntelligenceAgent(BaseAgent):
    name = "Client Intelligence Agent"
    agent_tier = (
        "critical"  # Nuanced buyer psychology, market synthesis needs top reasoning
    )

    async def observe(self) -> Dict[str, Any]:
        intake = self.manifest.get("intake_output", {})
        client = self.manifest.get("client", {})
        rfp = self.manifest.get("rfp", {})

        products = ", ".join(rfp.get("products", []))
        industry = client.get("industry", "")
        client_name = client.get("name", "")

        # Extract geographies if available
        geographies = []
        if isinstance(intake, dict):
            geo = intake.get("extracted_fields", {}).get("geographies", {})
            if isinstance(geo, dict):
                geographies = geo.get("value", [])
            elif isinstance(geo, list):
                geographies = geo

        kb_context = await self.get_kb_context(
            f"client intelligence {client_name} {industry} {products} market position",
            collections=["rfps", "win_loss_data", "case_studies"],
        )

        # User-provided competitive context
        user_ctx = self.manifest.get("user_context", {})
        incumbent = user_ctx.get("incumbent_vendor", "")
        past_rel = user_ctx.get("past_relationship", "")
        competitors = user_ctx.get("known_competitors", [])

        # Web research for client enrichment
        web_intel = ""
        if client_name and client_name != "Unknown":
            web_intel = await self.web_lookup(
                f"{client_name} company", context=f"{industry} technology strategy"
            )

        return {
            "rfp_text": self.get_rfp_sections("client_intelligence"),
            "intake": intake,
            "kb_context": kb_context,
            "client": client,
            "rfp": rfp,
            "products": products,
            "industry": industry,
            "client_name": client_name,
            "geographies": geographies,
            "incumbent_vendor": incumbent,
            "past_relationship": past_rel,
            "known_competitors": competitors,
            "web_intel": web_intel,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Two-call strategy: company profile + win strategy inputs."""
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse past engagement patterns.\n"

        geo_context = (
            f"\nGeographies: {', '.join(obs.get('geographies', []))}\n"
            if obs.get("geographies")
            else ""
        )
        incumbent_ctx = (
            f"\nIncumbent Vendor: {obs['incumbent_vendor']}\n"
            if obs.get("incumbent_vendor")
            else ""
        )
        relationship_ctx = (
            f"\nPast Relationship: {obs['past_relationship']}\n"
            if obs.get("past_relationship")
            else ""
        )
        competitor_ctx = ""
        if obs.get("known_competitors"):
            competitor_ctx = (
                f"\nKnown Competitors: {', '.join(obs['known_competitors'])}\n"
            )

        rfp_text = obs["rfp_text"]

        web_section = ""
        if obs.get("web_intel"):
            web_section = (
                f"\n=== WEB RESEARCH (real-time public data) ===\n{obs['web_intel']}\n"
            )

        # â”€â”€ CALL 1: Company Profile, Technology Landscape, Procurement Signals â”€â”€
        prompt_profile = f"""Analyze this RFP and any available context to build a comprehensive client intelligence profile.

RULES:
- Extract all factual client information from the RFP document
- Infer technology maturity and procurement behavior from RFP language and requirements
- Do NOT invent information not supported by the RFP
- If information is unavailable, state "Not specified in RFP"
- Classify procurement maturity: Is this a first-time outsourcing, a rebid/re-tender, a vendor consolidation, or a new capability build?
- Infer decision-maker orientation from RFP language: CIO-led (technical depth), CFO-led (cost focus), CPO-led (compliance), COO-led (operational efficiency)

Client: {obs.get("client_name", "Unknown")}
Industry: {obs.get("industry", "Unknown")}
Products: {obs.get("products", "")}
{geo_context}{incumbent_ctx}{relationship_ctx}{competitor_ctx}
{web_section}

=== RFP DOCUMENT ===
{rfp_text}
{kb_section}

Return JSON with EXACTLY this structure:
{{
  "company_profile": {{
    "name": "client name from RFP",
    "industry": "industry vertical",
    "estimated_size": "enterprise|large|mid-market|SMB",
    "headquarters": "location if mentioned",
    "employee_count": "if mentioned or inferred",
    "revenue_range": "if mentioned or inferred",
    "technology_maturity": "advanced|moderate|traditional",
    "key_priorities": ["top 3 business priorities from RFP"],
    "regulatory_environment": "regulated|moderate|minimal"
  }},
  "technology_landscape": {{
    "current_platforms": ["platforms mentioned in RFP"],
    "integration_complexity": "very-high|high|medium|low",
    "digital_maturity": "leader|developing|traditional",
    "cloud_adoption": "cloud-native|hybrid|on-premise|migrating",
    "pain_points": ["technology challenges evident from RFP"],
    "modernization_signals": ["indicators of transformation intent"],
    "data_sensitivity": "high|medium|low"
  }},
  "procurement_signals": {{
    "buying_style": "relationship|value|price|technical-fit",
    "procurement_maturity": "first-time-outsourcing|rebid|consolidation|new-capability|expansion",
    "risk_appetite": "conservative|moderate|progressive",
    "decision_maker_orientation": "CIO-led|CFO-led|CPO-led|COO-led|committee",
    "decision_factors": ["key decision factors from RFP language"],
    "evaluation_criteria": ["explicit or implied evaluation factors"],
    "timeline_pressure": "urgent|standard|relaxed",
    "budget_signals": "constrained|flexible|not-specified"
  }}
}}

Each assessment should be backed by specific RFP evidence. Explain reasoning in 2-3 sentences per field."""

        profile = await self.llm_json(prompt_profile, max_tokens=4500)
        self.log(
            "profile_extracted",
            {
                "industry": profile.get("company_profile", {}).get("industry", ""),
                "tech_maturity": profile.get("technology_landscape", {}).get(
                    "digital_maturity", ""
                ),
            },
        )

        # â”€â”€ CALL 2: Relationship Context, Win Strategy Inputs, Risk Factors â”€â”€
        prompt_strategy = f"""Based on this RFP, develop win strategy inputs and identify client-specific risk factors.

Client: {obs.get("client_name", "Unknown")}
Industry: {obs.get("industry", "Unknown")}
Products: {obs.get("products", "")}
{incumbent_ctx}{relationship_ctx}{competitor_ctx}

=== RFP DOCUMENT ===
{rfp_text}

Return JSON with EXACTLY this structure:
{{
  "relationship_context": {{
    "relationship_status": "new|existing|renewal|competitive-displacement",
    "engagement_history": "brief description of relationship signals from RFP",
    "trust_indicators": ["signals of trust or distrust in RFP language"],
    "switching_cost_assessment": "high|medium|low"
  }},
  "win_strategy_inputs": {{
    "client_hot_buttons": ["top 3-5 things the client cares most about"],
    "differentiators_needed": ["capabilities needed to win"],
    "pricing_sensitivity": "premium-tolerant|value-focused|cost-driven",
    "relationship_leverage": "strong|moderate|limited|none",
    "competitive_positioning": "leader|challenger|niche|cost-play",
    "key_proof_points": ["case studies or references that would resonate"]
  }},
  "risk_factors": [
    {{"risk": "description", "impact": "high|medium|low", "mitigation": "recommended action"}}
  ]
}}

Focus on actionable intelligence. Maximum 7 risk factors. Each risk must have a specific mitigation strategy."""

        strategy = await self.llm_json(prompt_strategy, max_tokens=4000)
        self.log(
            "strategy_extracted",
            {
                "hot_buttons": len(
                    strategy.get("win_strategy_inputs", {}).get(
                        "client_hot_buttons", []
                    )
                ),
                "risks": len(strategy.get("risk_factors", [])),
            },
        )

        # Merge both results
        merged = {**profile, **strategy}
        return merged

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        profile = decision.get("company_profile", {})
        tech = decision.get("technology_landscape", {})
        procurement = decision.get("procurement_signals", {})
        relationship = decision.get("relationship_context", {})
        win_inputs = decision.get("win_strategy_inputs", {})
        risks = decision.get("risk_factors", [])

        hot_buttons = win_inputs.get("client_hot_buttons", [])[:3]
        differentiators = win_inputs.get("differentiators_needed", [])[:3]
        pain_points = tech.get("pain_points", [])[:3]

        prompt = f"""Write a concise client intelligence brief (200-250 words max).

STYLE: Strategic consulting language. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive.

CLIENT DATA:
Company: {profile.get("name", "Unknown")} | Industry: {profile.get("industry", "Unknown")}
Size: {profile.get("estimated_size", "Unknown")} | Tech Maturity: {profile.get("technology_maturity", "Unknown")}
Relationship: {relationship.get("relationship_status", "Unknown")}
Integration Complexity: {tech.get("integration_complexity", "Unknown")}
Buying Style: {procurement.get("buying_style", "Unknown")} | Risk Appetite: {procurement.get("risk_appetite", "Unknown")}
Hot Buttons: {"; ".join(hot_buttons) if hot_buttons else "Not identified"}
Differentiators Needed: {"; ".join(differentiators) if differentiators else "Not identified"}
Pain Points: {"; ".join(pain_points) if pain_points else "Not identified"}
Risks: {len(risks)} identified

Write 3 tight paragraphs:
1. Client profile â€” industry position, technology maturity, key business priorities, regulatory context.
2. Procurement intelligence â€” buying behavior, decision factors, pricing sensitivity, timeline pressure.
3. Win strategy â€” hot buttons, required differentiators, competitive positioning, key risks to mitigate."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"Client: {profile.get('name', 'Unknown')} ({profile.get('industry', '')}). "
        summary += f"Tech maturity: {profile.get('technology_maturity', 'unknown')}. "
        summary += f"Buying style: {procurement.get('buying_style', 'unknown')}. "
        summary += f"{len(hot_buttons)} hot buttons, {len(risks)} risks. "
        summary += (
            f"Positioning: {win_inputs.get('competitive_positioning', 'unknown')}."
        )

        return {
            "company_profile": profile,
            "technology_landscape": tech,
            "procurement_signals": procurement,
            "relationship_context": relationship,
            "win_strategy_inputs": win_inputs,
            "risk_factors": risks,
            "narrative": narrative,
            "hitl_summary": summary,
        }
