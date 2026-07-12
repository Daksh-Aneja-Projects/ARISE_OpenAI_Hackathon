"""
Discovery Agent â€” Generates structured client discovery questions based on RFP gaps.
Output: Questions organized by category, each mapped to the specific RFP gap that triggered it.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class DiscoveryAgent(BaseAgent):
    name = "Discovery Agent"
    agent_tier = "lightweight"

    async def observe(self) -> Dict[str, Any]:
        self.manifest.get("rfp_text", "")
        intake = self.manifest.get("intake_output", {})
        products = ", ".join(self.manifest.get("rfp", {}).get("products", []))
        industry = self.manifest.get("client", {}).get("industry", "")
        kb_context = await self.get_kb_context(
            f"discovery questions clarifications {products} {industry}",
            collections=["rfps", "sows"],
        )
        ambiguities = []
        if isinstance(intake, dict):
            ambiguities = intake.get(
                "ambiguities",
                intake.get("extracted_fields", {})
                .get("ambiguities", {})
                .get("value", []),
            )
        return {
            "rfp_text": self.get_rfp_sections("discovery"),
            "intake": intake,
            "kb_context": kb_context,
            "ambiguities": ambiguities,
            "products": products,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse past discovery patterns.\n"

        amb_text = ""
        if obs.get("ambiguities"):
            amb_text = f"\n=== AMBIGUITIES FROM INTAKE ===\n{obs['ambiguities']}\n"

        prompt = f"""Analyze this RFP to identify information gaps and generate discovery questions.

RULES:
- Map every question to the specific RFP section
- Organize by: Scope, Technical, Commercial, Governance, Transition
- Prioritize: must-ask vs nice-to-have
- Focus on: {obs.get("products", "")}

=== RFP DOCUMENT ===
{obs["rfp_text"]}
{kb_section}
{amb_text}

Return JSON:
{{
  "discovery_categories": [
    {{
      "category": "Scope|Technical|Commercial|Governance|Transition|Integration",
      "questions": [
        {{
          "question": "the question",
          "rfp_trigger": "RFP section that created this gap",
          "why_important": "impact on bid if not clarified",
          "priority": "must-ask|should-ask|nice-to-have",
          "expected_format": "data|document|confirmation"
        }}
      ]
    }}
  ],
  "pre_meeting_requests": [
    {{"document": "what to request", "reason": "why needed", "rfp_ref": "section"}}
  ],
  "assumptions_to_validate": [
    {{"assumption": "what assumed", "rfp_basis": "why", "risk_if_wrong": "impact"}}
  ],
  "total_questions": 0,
  "must_ask_count": 0
}}"""
        return await self.llm_json(prompt, max_tokens=6000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        categories = decision.get("discovery_categories", [])
        total_q = sum(len(c.get("questions", [])) for c in categories)
        must_ask = sum(
            len([q for q in c.get("questions", []) if q.get("priority") == "must-ask"])
            for c in categories
        )
        pre_meeting = len(decision.get("pre_meeting_requests", []))
        assumptions = len(decision.get("assumptions_to_validate", []))

        prompt = f"""Write a concise discovery session brief (150-200 words max).

STYLE: Formal pre-meeting briefing language. No markdown. No bullets. No asterisks. Flowing paragraphs.

DISCOVERY DATA:
Categories: {len(categories)} | Total Questions: {total_q} ({must_ask} must-ask)
Pre-meeting Requests: {pre_meeting} | Assumptions to Validate: {assumptions}

Write 3 tight paragraphs:
1. Session purpose â€” objective, question count, key uncertainty areas needing resolution.
2. Critical questions â€” the must-ask items that could materially change scope or pricing.
3. Pre-meeting requests and assumptions â€” documents to request in advance, assumptions to validate."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"{total_q} discovery questions across {len(categories)} categories. "
        summary += f"{must_ask} must-ask. "
        summary += f"{pre_meeting} pre-meeting document requests."

        # === CLOSED-LOOP: Capture learnings for institutional improvement ===
        if must_ask > 0:
            top_cats = ", ".join(c.get("category", "?") for c in categories[:3])
            self.capture_learning(
                learning_type="discovery_pattern",
                insight=f"Generated {total_q} questions ({must_ask} must-ask) across categories: {top_cats}. "
                f"{assumptions} assumptions need validation. {pre_meeting} pre-meeting doc requests.",
                confidence=0.6,
            )

        return {
            "discovery_analysis": decision,
            "narrative": narrative,
            "hitl_summary": summary,
        }
