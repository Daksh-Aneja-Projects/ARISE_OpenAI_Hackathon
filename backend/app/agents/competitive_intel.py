"""
Competitive Intelligence Agent â€” Competitive landscape, win themes, differentiators.
Uses application-agnostic competitive knowledge base to identify real competitors
for the specific deal type, products, and geography.

L9 Strategic Capabilities:
  - Dynamic competitor discovery (not a static list)
  - Bidder-agnostic win themes from manifest["bidder_profile"]
  - Incumbent detection from RFP language signals (not hardcoded vendor name checks)
  - Ghost competitor strategy (counter-positioning per likely bidder)
  - Closed loop: past win/loss learnings injected via get_past_learnings()
"""

from typing import Any, Dict
from app.agents.base import BaseAgent
from app.agents.competitive_knowledge import (
    get_competitive_context,
    format_competitive_context_for_prompt,
)


class CompetitiveIntelAgent(BaseAgent):
    name = "Competitive Intelligence Agent"
    agent_tier = (
        "analytical"  # Market synthesis, 70B handles sparse-signal analysis well
    )

    def _get_rfp_context(self) -> str:
        self.manifest.get("rfp_text", "")
        intake = self.manifest.get("intake_output", {})
        context = self.get_rfp_sections("competitive_intel") + "\n\n"
        if intake and isinstance(intake, dict):
            extracted = intake.get("extracted_fields", {})
            if extracted:
                context += "=== INTAKE FINDINGS ===\n"
                for k, v in extracted.items():
                    if k in (
                        "platform_details",
                        "integration_inventory",
                        "kpi_sla_table",
                        "scope_sections",
                    ):
                        continue
                    val = v.get("value", v) if isinstance(v, dict) else v
                    context += f"- {k}: {val}\n"
        return context

    def _detect_incumbent_signals(self) -> dict:
        """Parse RFP for incumbent signals generically â€” no hardcoded vendor names.

        Looks for language patterns that indicate an incumbent relationship:
        - "current service provider", "existing vendor", "handover"
        - "transition from", "incumbent", "re-tendering"
        - Named vendors in transition/handover context

        Returns: {is_incumbent: bool, signals: list, detected_vendor: str or None}
        """
        import re

        rfp_text = (self.manifest.get("rfp_text", "") or "").lower()
        user_ctx = self.manifest.get("user_context", {})

        signals = []
        detected_vendor = None

        # Check user-provided incumbent info first (highest priority)
        if user_ctx.get("incumbent_vendor"):
            return {
                "is_incumbent": False,  # If user specifies incumbent, WE are not the incumbent
                "signals": [
                    f"User identified incumbent: {user_ctx['incumbent_vendor']}"
                ],
                "detected_vendor": user_ctx["incumbent_vendor"],
            }

        # Generic incumbent language patterns
        incumbent_patterns = [
            r"(?:current|existing|incumbent)\s+(?:service\s+)?(?:provider|vendor|partner|supplier)",
            r"(?:transition|handover|takeover)\s+from",
            r"re-?(?:tender|bid|compete|procurement)",
            r"(?:outgoing|departing)\s+(?:provider|vendor|partner)",
            r"service\s+(?:transfer|migration)\s+from",
        ]
        for pattern in incumbent_patterns:
            matches = re.findall(pattern, rfp_text)
            if matches:
                signals.extend(matches[:2])

        # Check if bidder name appears in incumbent context
        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"].lower()
        if bidder_name != "[bidder]":
            bidder_in_rfp = bidder_name in rfp_text
            if bidder_in_rfp and any(
                kw in rfp_text
                for kw in ["incumbent", "current", "handover", "transition from"]
            ):
                return {
                    "is_incumbent": True,
                    "signals": [
                        f"Bidder ({bidder['name']}) referenced in incumbent context"
                    ],
                    "detected_vendor": bidder["name"],
                }

        return {
            "is_incumbent": False,
            "signals": signals,
            "detected_vendor": detected_vendor,
        }

    def _get_competitive_context(self) -> str:
        """Build bidder-agnostic competitive intel for this specific deal."""
        rfp = self.manifest.get("rfp", {})
        client = self.manifest.get("client", {})
        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )

        products = rfp.get("products", [])
        if extracted and isinstance(extracted, dict):
            ip = extracted.get("products", {})
            if isinstance(ip, dict) and ip.get("value"):
                products = ip["value"]

        deal_type = rfp.get("contract_type", "AMS")
        if extracted and isinstance(extracted, dict):
            ct = extracted.get("contract_type", {})
            if isinstance(ct, dict) and ct.get("value"):
                deal_type = ct["value"]

        # Use generic incumbent detection (no hardcoded vendor check)
        incumbent_info = self._detect_incumbent_signals()

        ctx = get_competitive_context(
            deal_type=deal_type,
            products=products,
            industry=client.get("industry", ""),
            geography=client.get("geography", []),
            estimated_tcv=self.manifest.get("estimated_tcv"),
            is_incumbent=incumbent_info["is_incumbent"],
            bidder_profile=self.manifest.get("bidder_profile"),
        )
        return format_competitive_context_for_prompt(ctx)

    async def observe(self) -> Dict[str, Any]:
        rfp_context = self._get_rfp_context()
        products = ", ".join(self.manifest.get("rfp", {}).get("products", []))
        industry = self.manifest.get("client", {}).get("industry", "")
        kb_context = await self.get_kb_context(
            f"competitive intelligence {products} {industry} win themes",
            collections=["competitor_intel", "win_loss_data"],
        )
        competitive_context = self._get_competitive_context()
        incumbent_info = self._detect_incumbent_signals()

        # Web research for competitive intelligence enrichment
        web_intel = ""
        if products and industry:
            web_intel = await self.web_lookup(
                f"{industry} IT outsourcing competitive landscape {products.split(',')[0]}",
                context="market share competitors",
            )

        return {
            "rfp_context": rfp_context,
            "kb_context": kb_context,
            "competitive_context": competitive_context,
            "incumbent_info": incumbent_info,
            "web_intel": web_intel,
            "client": self.manifest.get("client", {}),
            "rfp": self.manifest.get("rfp", {}),
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse past competitive data.\n"

        web_section = ""
        if obs.get("web_intel"):
            web_section = (
                f"\n=== WEB RESEARCH (real-time market intel) ===\n{obs['web_intel']}\n"
            )

        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"]

        incumbent_section = ""
        inc_info = obs.get("incumbent_info", {})
        if inc_info.get("detected_vendor"):
            incumbent_section = f"\n=== INCUMBENT INTELLIGENCE ===\nDetected incumbent: {inc_info['detected_vendor']}\nSignals: {', '.join(inc_info.get('signals', []))}\n"

        prompt = f"""Analyze the competitive landscape for this RFP from {bidder_name}'s perspective.
Use the competitive intelligence context below to identify REAL competitors relevant to this deal type and product set.

RULES:
- Identify competitors who are LIKELY to bid based on the deal type, products, and geography
- For each win theme: provide evidence from {bidder_name} capabilities AND explain the impact on evaluation
- For each differentiator: explain WHY competitors cannot match it with proof points
- Be specific â€” generic statements like "industry expertise" are worthless without specifics
- If {bidder_name} is "[Bidder]", focus on structural advantages (cost model, delivery model, automation) not named capabilities
- NEVER claim capabilities not listed in the bidder profile

{obs["rfp_context"]}
{kb_section}
{web_section}
{obs["competitive_context"]}
{incumbent_section}

Return JSON:
{{
  "competitors": [
    {{"name": "real competitor name", "threat": "high|medium|low", "strength": "their key strength for THIS specific deal â€” 2 sentences", "weakness": "exploitable weakness with specific context â€” 2 sentences", "counter": "{bidder_name} positioning strategy to neutralize this competitor â€” 2 sentences"}}
  ],
  "incumbent": {{"name": "name or Unknown", "evidence": "RFP signals suggesting incumbent", "switching_cost": "high|medium|low", "displacement": "specific displacement strategy â€” what we offer that incumbent cannot"}},
  "win_themes": [
    {{"theme": "compelling theme statement", "rfp_criteria": "which evaluation criteria this addresses", "differentiator": "specific {bidder_name} capability or credential backing this theme", "evidence": "proof point â€” past deal, certification, or metric", "impact": "how this shifts evaluation in our favor â€” 1-2 sentences"}}
  ],
  "differentiators": [
    {{"what": "specific {bidder_name} differentiator", "rfp_req": "exact RFP requirement it addresses", "why_unique": "why competitors cannot replicate this â€” specific gap analysis â€” 2-3 sentences", "proof_point": "quantified evidence or credential"}}
  ],
  "vulnerabilities": [
    {{"gap": "{bidder_name} weakness for this deal", "rfp_req": "which requirement exposes it", "severity": "high|medium|low", "mitigation": "specific mitigation strategy â€” partnership, hiring, accelerator"}}
  ],
  "ghost_strategies": [
    {{"competitor": "competitor name", "if_they_bid": "their likely positioning â€” 1-2 sentences", "our_counter": "how to neutralize their pitch â€” 1-2 sentences"}}
  ],
  "pricing_strategy": {{"positioning": "premium|competitive|aggressive", "signals": "RFP signals informing this â€” evaluation weightage, budget hints, incumbent pricing", "approach": "specific pricing strategy â€” 2-3 sentences on how to structure the commercial to win"}},
  "deal_strategy": {{"overall_approach": "displacement|retention|new_entry", "key_message": "the ONE message that wins this deal â€” 1-2 sentences", "risk_to_win": "what could cause us to lose â€” 1-2 sentences"}}
}}"""
        return await self.llm_json(prompt, max_tokens=5000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        competitors = decision.get("competitors", [])
        themes = decision.get("win_themes", [])
        diffs = decision.get("differentiators", [])
        vulns = decision.get("vulnerabilities", [])
        ghosts = decision.get("ghost_strategies", [])
        inc = decision.get("incumbent", {})
        pricing = decision.get("pricing_strategy", {})

        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"]

        comp_text = " | ".join(
            [f"{c.get('name', '?')} ({c.get('threat', '?')})" for c in competitors[:5]]
        )
        theme_text = " | ".join([t.get("theme", "") for t in themes[:4]])

        prompt = f"""Write a concise competitive strategy narrative for {bidder_name} (120-150 words max).

STYLE: Strategic consulting language. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive.

COMPETITIVE DATA:
Competitors: {comp_text}
Incumbent: {inc.get("name", "Unknown")} (switching cost: {inc.get("switching_cost", "unknown")})
Win Themes: {theme_text}
Differentiators: {len(diffs)} | Vulnerabilities: {len(vulns)} | Ghost Strategies: {len(ghosts)}
Pricing: {pricing.get("positioning", "N/A")} â€” {pricing.get("approach", "N/A")}

Write 3 tight paragraphs:
1. Competitive landscape â€” who is bidding, threat levels, incumbent dynamics.
2. {bidder_name} win themes and differentiators â€” key proposal messages.
3. Vulnerabilities and pricing â€” gaps to address, commercial positioning."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        theme_names = [t.get("theme", "") for t in themes[:3]]
        summary = f"{len(competitors)} competitors. "
        summary += f"Win themes: {'; '.join(theme_names)}. "
        summary += f"Incumbent: {inc.get('name', 'Unknown')}. "
        summary += f"Pricing: {pricing.get('positioning', 'N/A')}."

        return {
            "competitive_landscape": decision,
            "narrative": narrative,
            "hitl_summary": summary,
        }
