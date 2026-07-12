"""
Intelligent Solutioning Engine â€” The IP agent of the platform.
Combines automation/AI opportunity analysis with full solution architecture:
platform architecture, integration landscape, environment strategy, TOM,
and automation roadmap â€” all in one cohesive view.

100% RFP-driven â€” zero hardcoded vendor/product/client references.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class AutomationAIAgent(BaseAgent):
    name = "Intelligent Solutioning Engine"
    agent_tier = (
        "volume"  # ROI calc + automation mapping, analytical but high frequency
    )

    def _get_rfp_context(self) -> str:
        intake = self.manifest.get("intake_output", {})
        scope = self.manifest.get("scope_output", {})
        context = self.get_rfp_sections("automation_ai") + "\n\n"
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )
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
        # Add platform + integration details for architecture
        platforms = (
            intake.get("platform_details", []) if isinstance(intake, dict) else []
        )
        if platforms:
            context += "\n=== PLATFORM DETAILS ===\n"
            for p in platforms[:5]:
                context += f"- {p.get('product_name', '?')}: {p.get('environments', '?')} environments, {p.get('modules_in_scope', [])}\n"
        integrations = (
            intake.get("integration_inventory", []) if isinstance(intake, dict) else []
        )
        if integrations:
            context += (
                f"\n=== INTEGRATION INVENTORY ({len(integrations)} integrations) ===\n"
            )
            for i in integrations[:8]:
                context += f"- {i.get('source', '?')} â†’ {i.get('target', '?')} via {i.get('middleware', '?')}\n"
        if scope and isinstance(scope, dict):
            context += f"\n=== SCOPE PACKAGE ===\n{str(scope.get('scope_package', ''))[:2000]}\n"
        return context

    async def observe(self) -> Dict[str, Any]:
        rfp_context = self._get_rfp_context()
        client = self.manifest.get("client", {})
        rfp = self.manifest.get("rfp", {})
        products = ", ".join(rfp.get("products", []))
        industry = client.get("industry", "")
        kb_context = await self.get_kb_context(
            f"automation solution architecture integration {products} {industry}",
            collections=["solutions", "solution_templates", "case_studies", "sows"],
        )
        return {
            "rfp_context": rfp_context,
            "kb_context": kb_context,
            "client": client,
            "rfp": rfp,
            "products": products,
            "industry": industry,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\n"

        prompt = f"""Analyze this RFP and produce TWO outputs:
1. SOLUTION ARCHITECTURE (platform architecture, integration landscape, environments, target operating model)
2. AUTOMATION & AI OPPORTUNITIES (grouped by platform)

RULES:
- Group by product/platform from the RFP
- Each automation opportunity must cite a specific RFP requirement or operational pain point
- 3-6 automation opportunities per platform, 2-4 cross-platform
- Architecture must cover ALL platforms, integrations, environments from RFP
- For each automation: explain WHAT it does, HOW it works technically, and WHY it matters to the business
- Include implementation complexity, prerequisites, and expected timeline
- Do NOT hardcode vendor/product names not in the RFP

{obs["rfp_context"]}
{kb_section}

Return JSON:
{{
  "products_in_scope": ["from RFP"],
  "key_volumes": [{{"metric": "e.g. integration count", "value": "from RFP", "risk": "why it matters"}}],
  "rfp_automation_refs": ["RFP sections mandating automation"],

  "platform_architectures": [
    {{
      "platform": "product name from RFP",
      "environments": ["from RFP"],
      "modules_in_scope": ["from RFP"],
      "technical_approach": "brief approach",
      "key_considerations": ["technical considerations"]
    }}
  ],
  "integration_architecture": {{
    "middleware": ["from RFP"],
    "integration_patterns": ["API|Event|Batch"],
    "data_flows": [{{"source": "", "target": "", "pattern": "", "frequency": ""}}],
    "monitoring_approach": "how monitored"
  }},
  "environment_strategy": {{
    "total_environments": 0,
    "promotion_path": "Devâ†’TSTâ†’UATâ†’Prod",
    "refresh_strategy": "approach",
    "data_masking": "GDPR approach if applicable"
  }},
  "operating_model": {{
    "coverage": "from RFP", "team_distribution": "onshore/offshore split",
    "escalation": "matrix", "governance": "cadence"
  }},
  "technical_risks": ["risks with mitigations"],
  "architecture_complexity": "standard|complex|enterprise",

  "platform_sections": [
    {{
      "platform": "product from RFP",
      "summary": "1 sentence scope",
      "opportunities": [
        {{
          "id": "PREFIX-N",
          "title": "descriptive title",
          "rfp_trigger": "Section X â€” brief quote or operational pain point",
          "what": "What business problem this solves and what gets automated â€” 2-3 sentences",
          "how": "Technical approach â€” mechanism, triggers, data flows, tools involved â€” 2-3 sentences",
          "business_justification": "Why this matters commercially â€” cost impact, risk reduction, compliance â€” 1-2 sentences",
          "sub_items": ["Specific automation step #1", "Specific automation step #2", "Specific automation step #3"],
          "prerequisites": ["What must be in place before implementation"],
          "effort": "Low|Medium|High (N-N weeks)",
          "benefit": "Quantified benefit â€” FTE hours saved, error reduction %, cycle time improvement",
          "estimated_fte_reduction": 0.5,
          "horizon": "Month N-N (Phase)",
          "risk_rating": 1-5,
          "priority": "CRITICAL|HIGH|MEDIUM|LOWER"
        }}
      ]
    }}
  ],
  "cross_platform": [
    {{
      "id": "CROSS-N",
      "title": "descriptive title",
      "description": "What this cross-platform automation does and how it creates compounding value â€” 2-3 sentences",
      "how": "Technical approach â€” what connects the platforms, data flow, orchestration mechanism â€” 2-3 sentences",
      "platforms": ["Platform A", "Platform B"],
      "effort": "Low|Medium|High (N-N weeks)",
      "benefit": "Quantified cross-platform benefit â€” reduced handoffs, faster processing, error elimination",
      "estimated_fte_reduction": 0.25,
      "priority": "CRITICAL|HIGH|MEDIUM|LOWER"
    }}
  ]
}}"""
        return await self.llm_json(prompt, max_tokens=6000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        all_opps = []
        for section in orientation.get("platform_sections", []):
            for opp in section.get("opportunities", []):
                all_opps.append(
                    {
                        "id": opp.get("id", ""),
                        "title": opp.get("title", ""),
                        "platform": section.get("platform", ""),
                        "risk_rating": opp.get("risk_rating", 1),
                        "effort": opp.get("effort", ""),
                        "horizon": opp.get("horizon", ""),
                        "priority": opp.get("priority", "MEDIUM"),
                        "benefit": opp.get("benefit", ""),
                    }
                )
        for cross in orientation.get("cross_platform", []):
            all_opps.append(
                {
                    "id": cross.get("id", ""),
                    "title": cross.get("title", ""),
                    "platform": "Cross-Platform",
                    "risk_rating": 3,
                    "effort": cross.get("effort", ""),
                    "horizon": "",
                    "priority": cross.get("priority", "MEDIUM"),
                    "benefit": cross.get("benefit", ""),
                }
            )

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOWER": 3}
        all_opps.sort(
            key=lambda x: (priority_order.get(x["priority"], 2), -x["risk_rating"])
        )

        return {
            "analysis": orientation,
            "prioritised": all_opps,
            "total": len(all_opps),
        }

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        analysis = decision["analysis"]
        prioritised = decision["prioritised"]
        total = decision["total"]

        products = ", ".join(analysis.get("products_in_scope", []))
        critical = len([o for o in prioritised if o["priority"] == "CRITICAL"])
        high = len([o for o in prioritised if o["priority"] == "HIGH"])
        platforms = analysis.get("platform_architectures", [])
        plat_text = " | ".join(
            [
                f"{p['platform']}: {p.get('technical_approach', '')[:50]}"
                for p in platforms
            ]
        )
        risks = analysis.get("technical_risks", [])
        integration = analysis.get("integration_architecture", {})
        op_model = analysis.get("operating_model", {})
        env = analysis.get("environment_strategy", {})
        top_opps = " | ".join(
            [f"{o['id']} {o['title']} [{o['priority']}]" for o in prioritised[:5]]
        )

        prompt = f"""Write an informative AI + Solutioning narrative (300-350 words).

STYLE: Data-dense consulting language. No markdown. No bullets. No asterisks. Embed specific numbers. Client-ready.

SOLUTION + AUTOMATION DATA:
Platforms: {plat_text}
Architecture Complexity: {analysis.get("architecture_complexity", "standard")}
Integrations: {len(integration.get("data_flows", []))} data flows via {integration.get("middleware", [])}
Environments: {env.get("total_environments", 0)} ({env.get("promotion_path", "N/A")})
Operating Model: Coverage {op_model.get("coverage", "N/A")}, Distribution {op_model.get("team_distribution", "N/A")}
Risks: {len(risks)} identified
Products: {products}
Automation: {total} opportunities ({critical} CRITICAL, {high} HIGH)
Top Automation: {top_opps}

Write 4 data-dense paragraphs (no fluff â€” every sentence must contain a number or specific fact):
1. Platform architecture â€” per-platform approach, modules, complexity assessment.
2. Automation highlights â€” top 3-5 opportunities with specific FTE savings and mechanisms.
3. Cross-platform synergies and implementation roadmap â€” phased deployment with YoY impact.
4. Risk profile and operational readiness â€” key risks, mitigations, tooling strategy."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"{total} automation opportunities across {products}. "
        summary += f"Solution for {len(platforms)} platforms ({analysis.get('architecture_complexity', 'standard')}). "
        summary += (
            f"{critical} CRITICAL, {high} HIGH priority. {len(risks)} tech risks."
        )

        # === CLOSED-LOOP: Capture learnings for institutional improvement ===
        if total > 0:
            self.capture_learning(
                learning_type="automation_pattern",
                insight=f"{total} automation opportunities identified ({critical} critical, {high} high). "
                f"Architecture complexity: {analysis.get('architecture_complexity', 'standard')}. "
                f"{len(risks)} technical risks across {len(platforms)} platforms.",
                confidence=0.7,
            )

        return {
            # Architecture outputs
            "platform_architectures": platforms,
            "integration_architecture": integration,
            "environment_strategy": env,
            "operating_model": op_model,
            "technical_risks": risks,
            "architecture_complexity": analysis.get(
                "architecture_complexity", "standard"
            ),
            # Automation outputs
            "client_context": {
                "products_in_scope": analysis.get("products_in_scope", []),
                "key_volumes": analysis.get("key_volumes", []),
                "rfp_automation_refs": analysis.get("rfp_automation_refs", []),
            },
            "platform_sections": analysis.get("platform_sections", []),
            "cross_platform": analysis.get("cross_platform", []),
            "prioritisation_table": prioritised,
            "total_opportunities": total,
            "priority_breakdown": {
                "critical": critical,
                "high": high,
                "medium": len([o for o in prioritised if o["priority"] == "MEDIUM"]),
                "lower": len([o for o in prioritised if o["priority"] == "LOWER"]),
            },
            "narrative": narrative,
            "hitl_summary": summary,
            "executive_summary": summary,
        }
