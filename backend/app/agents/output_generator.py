"""
Output Generator Agent â€” Coordinates generation of client-ready documents.
Assembles all agent narratives and structured data into a cohesive executive
summary and SOW outline. Consumes full upstream agent outputs.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class OutputGeneratorAgent(BaseAgent):
    name = "Output Generator Agent"
    agent_tier = "lightweight"

    async def observe(self) -> Dict[str, Any]:
        return {
            "rfp_text": self.get_rfp_sections("output_generator"),
            "intake": self.manifest.get("intake_output", {}),
            "scope": self.manifest.get("scope_output", {}),
            "solution": self.manifest.get("solution_output", {}),
            "commercial": self.manifest.get("commercial_output", {}),
            "compliance": self.manifest.get("compliance_output", {}),
            "competitive": self.manifest.get("competitive_output", {}),
            "automation_ai": self.manifest.get("automation_ai_output", {}),
            "transition": self.manifest.get("transition_change_output", {}),
            "client": self.manifest.get("client", {}),
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        sections = []
        for key in [
            "intake",
            "scope",
            "solution",
            "commercial",
            "compliance",
            "competitive",
            "automation_ai",
            "transition",
        ]:
            val = obs.get(key)
            if val and isinstance(val, dict):
                sections.append(
                    {
                        "agent": key,
                        "has_narrative": bool(val.get("narrative")),
                        "has_data": True,
                    }
                )
            else:
                sections.append(
                    {"agent": key, "has_narrative": False, "has_data": False}
                )
        ready = [s for s in sections if s["has_data"]]
        missing = [s["agent"] for s in sections if not s["has_data"]]
        return {
            "ready_sections": ready,
            "missing_sections": missing,
            "total_ready": len(ready),
        }

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "generate": True,
            "sections_available": orientation["total_ready"],
            "missing": orientation["missing_sections"],
        }

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        rfp_text = self.get_rfp_sections("output_generator")
        intake = self.manifest.get("intake_output", {})
        scope = self.manifest.get("scope_output", {})
        solution = self.manifest.get("solution_output", {})
        commercial = self.manifest.get("commercial_output", {})
        competitive = self.manifest.get("competitive_output", {})
        transition = self.manifest.get("transition_change_output", {})
        automation = self.manifest.get("automation_ai_output", {})

        # Build rich context from upstream structured data
        summaries = {}
        for name, data in [
            ("intake", intake),
            ("scope", scope),
            ("solution", solution),
            ("commercial", commercial),
            ("competitive", competitive),
            ("transition", transition),
            ("automation", automation),
        ]:
            if isinstance(data, dict):
                narrative = data.get("narrative", "")
                summary = data.get("hitl_summary", "")
                # Use full narrative (up to 1500 chars) + summary for richer context
                combined = (
                    f"{summary}\n{str(narrative)[:1500]}" if narrative else summary
                )
                if combined.strip():
                    summaries[name] = combined

        # Add key commercial figures
        commercial_context = ""
        if isinstance(commercial, dict):
            pl = commercial.get("pl_model", {})
            if isinstance(pl, dict):
                rev = pl.get("revenue", {})
                if isinstance(rev, dict):
                    commercial_context = f"\nFINANCIALS: TCV=${rev.get('total_contract_value', 0):,.0f}, Monthly=${rev.get('monthly_price', 0):,.0f}, Margin={pl.get('profitability', {}).get('margin_percent', 0)}%"
            # Add automation YOY savings
            auto_yoy = commercial.get("automation_yoy", [])
            if auto_yoy:
                total_savings = sum(
                    y.get("automation_savings", 0)
                    for y in auto_yoy
                    if isinstance(y, dict)
                )
                commercial_context += f"\nAUTOMATION SAVINGS: ${total_savings:,.0f} cumulative over {len(auto_yoy)} years"

        # Add team model context
        team_context = ""
        if isinstance(scope, dict):
            sp = scope.get("scope_package", scope)
            if isinstance(sp, dict):
                team = sp.get("team_model", [])
                if team:
                    total_fte = sum(
                        r.get("count", r.get("fte", 0))
                        for r in team
                        if isinstance(r, dict)
                    )
                    team_context = f"\nTEAM: {total_fte} FTEs across {len(team)} roles"

        # Add transition timeline context
        transition_context = ""
        if isinstance(transition, dict):
            tp = transition.get("transition_plan", {})
            if isinstance(tp, dict):
                phases = tp.get("phases", [])
                duration = tp.get("total_duration_weeks", 0)
                transition_context = (
                    f"\nTRANSITION: {len(phases)} phases over {duration} weeks"
                )

        prompt = f"""Generate two outputs from the comprehensive agent data below.

STYLE: Formal proposal language. No markdown. No bullets. No asterisks. Flowing paragraphs. Client-ready.
ALL monetary amounts MUST be in US Dollars ($). Every claim must be backed by specific data.

=== RFP CONTEXT ===
{rfp_text[:12000]}

=== AGENT INTELLIGENCE ===
{chr(10).join(f"{k.upper()}: {v}" for k, v in summaries.items() if v)}
{commercial_context}
{team_context}
{transition_context}

Return JSON with two fields:
{{
  "executive_summary": "400-500 word executive summary. 5 paragraphs: (1) Client understanding â€” their business context, challenges, strategic imperatives. (2) Proposed solution â€” specific platforms, architecture approach, team model with exact FTE count and delivery model. (3) Transition and delivery â€” phased approach, timeline, risk mitigation. (4) Commercial proposition â€” exact TCV, monthly pricing, contract term, value drivers, automation ROI projections. (5) Why Us â€” differentiators, relevant experience, partnership commitment. USE THE EXACT NUMBERS from the data.",
  "sow_outline": "300-400 word SOW outline. 12 sections each with 2-3 sentences: 1. Background & Context, 2. Scope of Services, 3. Service Level Framework, 4. Governance & Reporting, 5. Team Structure & Staffing, 6. Transition Plan, 7. Knowledge Transfer, 8. Automation & Continuous Improvement, 9. Pricing & Payment Terms, 10. Dependencies & Assumptions, 11. Term & Termination, 12. Change Management."
}}"""

        result = await self.llm_json(prompt, max_tokens=6000)

        executive_summary = result.get(
            "executive_summary", "Executive summary generation failed."
        )
        sow_outline = result.get("sow_outline", "SOW outline generation failed.")

        missing = decision.get("missing", [])
        available = decision.get("sections_available", 0)
        summary = f"Proposal assembled from {available} agent outputs."
        if missing:
            summary += f" Missing: {', '.join(missing)}."

        return {
            "executive_summary": executive_summary,
            "sow_outline": sow_outline,
            "sections_available": available,
            "missing_sections": missing,
            "narrative": executive_summary,
            "hitl_summary": summary,
        }
