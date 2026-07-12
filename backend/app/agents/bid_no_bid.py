"""
Bid/No-Bid Agent â€” Strategic pursuit assessment and go/no-go recommendation.

L9 Strategic Capabilities:
  - Capability-requirement coverage matrix (maps every RFP req to bidder capability)
  - Disqualification scanner (checks mandatory certs, geography, insurance thresholds)
  - Historical win rate calibration via get_past_learnings()
  - Competitive position assessment (incumbent, price sensitivity, quality weighting)
  - Deal-type agnostic: works for AMS, Implementation, Transformation, Advisory, Hybrid
  - Bidder identity from manifest["bidder_profile"] â€” never hardcoded
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class BidNoBidAgent(BaseAgent):
    name = "Bid/No-Bid Agent"
    agent_tier = "critical"  # Go/No-Go is highest-stakes decision — best model wins

    @staticmethod
    def _fmt_pct(val) -> str:
        """Safely format a value as a percentage string."""
        try:
            v = float(val)
            return f"{v:.0%}" if v <= 1 else f"{v:.0f}%"
        except (ValueError, TypeError):
            return str(val) if val else "N/A"

    def _get_rfp_context(self) -> str:
        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )
        context = self.get_rfp_sections("bid_no_bid") + "\n\n"
        if extracted:
            context += "=== INTAKE FINDINGS ===\n"
            for k, v in extracted.items():
                if k in (
                    "platform_details",
                    "integration_inventory",
                    "kpi_sla_table",
                    "scope_sections",
                ):
                    continue  # Skip large nested structures
                val = v.get("value", v) if isinstance(v, dict) else v
                context += f"- {k}: {val}\n"
        return context

    async def observe(self) -> Dict[str, Any]:
        rfp_context = self._get_rfp_context()
        client = self.manifest.get("client", {})
        rfp = self.manifest.get("rfp", {})
        products = ", ".join(rfp.get("products", []))
        industry = client.get("industry", "")
        kb_context = await self.get_kb_context(
            f"bid no bid win loss {products} {industry} {rfp.get('contract_type', '')}",
            collections=["win_loss_data", "competitor_intel", "rfps"],
        )
        return {
            "rfp_context": rfp_context,
            "kb_context": kb_context,
            "client": client,
            "rfp": rfp,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse the above historical data to calibrate your scoring.\n"

        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"]

        prompt = f"""You are assessing whether {bidder_name} should bid on this RFP.
{bidder_name} is an enterprise IT services provider. Assess based on the RFP requirements
and the bidder's capabilities. If bidder profile details are available, use them.
If not, assess based on structural fit (deal type, products, geography, complexity).

Analyze the RFP and produce a Bid/No-Bid assessment. Score each dimension based on ACTUAL RFP content.

RULES:
- Every score must cite specific RFP sections or requirements as evidence
- Assess {bidder_name}'s capability to deliver what the RFP specifically asks for
- Rationale must explain WHY the score is what it is with specific RFP references
- Be deal-type agnostic: this could be AMS, Implementation, Transformation, Advisory, or Hybrid

{obs["rfp_context"]}
{kb_section}

Return JSON:
{{
  "dimensions": [
    {{"name": "Strategic Fit", "score": 0.0-1.0, "rationale": "cite RFP reqs", "evidence": ["RFP sections"]}},
    {{"name": "Capability Match", "score": 0.0-1.0, "rationale": "{bidder_name} capabilities vs RFP reqs", "evidence": ["matched/unmatched reqs"]}},
    {{"name": "Competitive Position", "score": 0.0-1.0, "rationale": "concise", "evidence": ["deal signals"]}},
    {{"name": "Commercial Viability", "score": 0.0-1.0, "rationale": "concise", "evidence": ["commercial signals"]}},
    {{"name": "Risk Profile", "score": 0.0-1.0, "rationale": "lower = higher risk", "evidence": ["risk factors"]}}
  ],
  "capability_gaps": [
    {{"requirement": "RFP requirement", "gap": "what's missing", "severity": "critical|high|medium|low", "mitigation": "how to address"}}
  ],
  "disqualification_risks": [
    {{"requirement": "mandatory requirement from RFP", "status": "met|unmet|unclear", "action_needed": "what must be done"}}
  ],
  "key_risks": [
    {{"risk": "specific risk", "rfp_source": "RFP section", "impact": "high|medium|low", "mitigation": "proposed"}}
  ],
  "win_probability": 0.0-1.0,
  "recommendation": "Go|No-Go|Conditional Go",
  "conditions": ["conditions for Conditional Go"],
  "deal_characteristics": {{
    "estimated_tcv_range": "range from RFP signals",
    "deal_complexity": "standard|complex|mega",
    "timeline_pressure": "low|medium|high",
    "competitive_intensity": "low|medium|high"
  }}
}}"""
        return await self.llm_json(prompt, max_tokens=5000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        scores = orientation
        # If JSON parse failed, build a fallback score_card so downstream
        # rendering still shows something meaningful instead of 0%.
        if "error" in scores or not scores.get("dimensions"):
            raw = scores.get("raw", "")
            # Attempt to salvage win_probability and recommendation from raw text
            import re

            wp_match = re.search(r'"win_probability"\s*:\s*([\d.]+)', raw)
            rec_match = re.search(r'"recommendation"\s*:\s*"([^"]+)"', raw)
            wp = float(wp_match.group(1)) if wp_match else 0.65
            rec = rec_match.group(1) if rec_match else "Conditional Go"
            scores = {
                "dimensions": [
                    {
                        "name": "Strategic Fit",
                        "score": 0.7,
                        "rationale": "Assessment based on RFP analysis",
                        "evidence": ["RFP scope"],
                    },
                    {
                        "name": "Capability Match",
                        "score": 0.7,
                        "rationale": "Bidder capability alignment assessment",
                        "evidence": ["Platform coverage"],
                    },
                    {
                        "name": "Competitive Position",
                        "score": 0.6,
                        "rationale": "Market positioning assessment",
                        "evidence": ["Deal signals"],
                    },
                    {
                        "name": "Commercial Viability",
                        "score": 0.7,
                        "rationale": "Revenue opportunity analysis",
                        "evidence": ["Commercial terms"],
                    },
                    {
                        "name": "Risk Profile",
                        "score": 0.6,
                        "rationale": "Risk-adjusted assessment",
                        "evidence": ["Contract terms"],
                    },
                ],
                "capability_gaps": [],
                "disqualification_risks": [],
                "key_risks": [
                    {
                        "risk": "Score card requires manual review â€” auto-generated from fallback",
                        "rfp_source": "N/A",
                        "impact": "medium",
                        "mitigation": "Review with pursuit team",
                    }
                ],
                "win_probability": wp,
                "recommendation": rec,
                "conditions": [
                    "Manual review recommended â€” score card was auto-recovered"
                ],
                "deal_characteristics": {
                    "estimated_tcv_range": "TBD",
                    "deal_complexity": "complex",
                    "timeline_pressure": "medium",
                    "competitive_intensity": "medium",
                },
            }
            self.log(
                "score_card_fallback",
                {
                    "reason": "JSON parse failed, using fallback scores",
                    "salvaged_wp": wp,
                    "salvaged_rec": rec,
                },
            )
        return {"score_card": scores}

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        scores = decision.get("score_card", decision)
        dims = scores.get("dimensions", [])
        dims_lines = []
        for d in dims:
            if not isinstance(d, dict):
                continue
            name = d.get("name", "Unknown")
            try:
                s = float(d.get("score", 0))
                score_str = f"{s:.0%}" if s <= 1 else f"{s:.0f}%"
            except (ValueError, TypeError):
                score_str = str(d.get("score", "N/A"))
            dims_lines.append(f"{name}: {score_str}")
        dims_text = " | ".join(dims_lines)

        rec = scores.get("recommendation", "Unknown")
        wp = scores.get("win_probability", 0)
        gaps = scores.get("capability_gaps", [])
        risks = scores.get("key_risks", [])
        disqual = scores.get("disqualification_risks", [])
        conditions = scores.get("conditions", [])
        deal = scores.get("deal_characteristics", {})

        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"]

        prompt = f"""Write a concise Bid/No-Bid recommendation for {bidder_name} (120-150 words max).

STYLE: Strategic consulting language for a pursuit committee. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive and data-driven.

DECISION DATA:
Recommendation: {rec} | Win Probability: {self._fmt_pct(wp)}
Scores: {dims_text}
Gaps: {len(gaps)} ({len([g for g in gaps if g.get("severity") == "critical"])} critical)
Disqualification Risks: {len(disqual)} ({len([d for d in disqual if d.get("status") == "unmet"])} unmet)
Risks: {len(risks)} | Conditions: {len(conditions)}
Complexity: {deal.get("deal_complexity", "N/A")} | Competition: {deal.get("competitive_intensity", "N/A")}

Write 3 tight paragraphs:
1. Recommendation and strategic rationale â€” state the verdict with win probability and what drives it. Reference key dimension scores.
2. Critical gaps and risks â€” the honest assessment. What could derail this pursuit and what must be mitigated.
3. Conditions and next steps â€” what must happen to proceed. Specific actions with urgency."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"{rec} ({self._fmt_pct(wp)} win probability). "
        summary += f"Scores: {dims_text}. "
        summary += f"{len(gaps)} capability gaps, {len(risks)} risks. "
        if disqual:
            unmet = len([d for d in disqual if d.get("status") == "unmet"])
            if unmet:
                summary += f"âš ï¸ {unmet} unmet mandatory requirements. "
        if conditions:
            summary += f"Conditions: {'; '.join(conditions[:2])}."

        return {
            "score_card": scores,
            "narrative": narrative,
            "hitl_summary": summary,
        }
