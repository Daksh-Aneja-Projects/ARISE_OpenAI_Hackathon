"""
Solution Architect Agent â€” Designs technical architecture with AMS ticket analysis mode.
Supports both Implementation Mode and AMS Mode based on contract type.
All outputs grounded in RFP â€” no hardcoded vendor names.
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgent


def analyze_ticket_data(tickets: List[Dict]) -> Dict[str, Any]:
    """
    Programmatic AMS ticket analysis â€” classifies and scores tickets for
    Eliminate / Shift-Left / Automate / Retain optimization.
    """
    categories = {}
    tier_counts = {"L1": 0, "L2": 0, "L3": 0}
    module_counts = {}
    priority_counts = {}
    total = len(tickets)

    for t in tickets:
        module = t.get("module", t.get("category", "Unknown"))
        tier = t.get("tier", t.get("level", "L2"))
        priority = t.get("priority", "Medium")

        module_counts[module] = module_counts.get(module, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

        key = f"{module}_{tier}"
        if key not in categories:
            categories[key] = {
                "module": module,
                "tier": tier,
                "count": 0,
                "examples": [],
            }
        categories[key]["count"] += 1
        if len(categories[key]["examples"]) < 3:
            categories[key]["examples"].append(
                t.get("description", t.get("summary", ""))[:100]
            )

    # Automation scoring heuristic
    scored = []
    for key, cat in categories.items():
        score = {"category": key, **cat, "action": "Retain"}
        if cat["tier"] == "L1" and cat["count"] > total * 0.05:
            score["action"] = "Eliminate"
            score["rationale"] = (
                "High-volume L1 tickets â€” deflect via knowledge base and self-service"
            )
        elif cat["tier"] == "L1":
            score["action"] = "Shift-Left"
            score["rationale"] = (
                "Low-complexity L1 work â€” automate with KB articles and guided flows"
            )
        elif cat["tier"] == "L2" and cat["count"] > total * 0.03:
            score["action"] = "Automate"
            score["rationale"] = (
                "Repetitive L2 tasks â€” candidate for RPA/workflow automation"
            )
        elif cat["tier"] == "L2":
            score["action"] = "Shift-Left"
            score["rationale"] = "L2 tasks that can be documented for L1 handling"
        else:
            score["action"] = "Retain"
            score["rationale"] = "Complex L3 work requiring specialist expertise"
        scored.append(score)

    tier_counts.get("L1", 0) / max(total, 1)
    eliminate_pct = sum(1 for s in scored if s["action"] == "Eliminate") / max(
        len(scored), 1
    )

    yoy_model = []
    baseline_fte = max(total / 2000, 3)
    for year in range(1, 4):
        reduction = 1.0 - (eliminate_pct * 0.3 * year)
        fte = round(baseline_fte * max(reduction, 0.5), 1)
        savings_pct = round((1 - reduction) * 100, 1)
        yoy_model.append(
            {
                "year": year,
                "fte": fte,
                "reduction_from_baseline": f"{savings_pct}%",
                "automation_maturity": ["Foundation", "Optimized", "Autonomous"][
                    min(year - 1, 2)
                ],
            }
        )

    return {
        "total_tickets": total,
        "tier_distribution": tier_counts,
        "module_distribution": module_counts,
        "priority_distribution": priority_counts,
        "automation_scoring": scored,
        "yoy_optimization": yoy_model,
        "summary": {
            "eliminate": sum(1 for s in scored if s["action"] == "Eliminate"),
            "shift_left": sum(1 for s in scored if s["action"] == "Shift-Left"),
            "automate": sum(1 for s in scored if s["action"] == "Automate"),
            "retain": sum(1 for s in scored if s["action"] == "Retain"),
        },
    }


class SolutionArchitectAgent(BaseAgent):
    name = "Solution Architect Agent"
    agent_tier = (
        "critical"  # AMS/Impl architecture design, complex domain, needs best model
    )

    def _get_rfp_context(self) -> str:
        intake = self.manifest.get("intake_output", {})
        scope = self.manifest.get("scope_output", {})
        context = self.get_rfp_sections("solution_architect") + "\n\n"
        if intake:
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
                context += "\n"
            # Platform and integration details from upgraded intake
            platforms = (
                intake.get("platform_details", []) if isinstance(intake, dict) else []
            )
            if platforms:
                context += "=== PLATFORM DETAILS ===\n"
                for p in platforms[:5]:
                    context += f"- {p.get('product_name', '?')}: {p.get('environments', '?')} environments, {p.get('modules_in_scope', [])}\n"
            integrations = (
                intake.get("integration_inventory", [])
                if isinstance(intake, dict)
                else []
            )
            if integrations:
                context += f"\n=== INTEGRATION INVENTORY ({len(integrations)} integrations) ===\n"
                for i in integrations[:8]:
                    context += f"- {i.get('source', '?')} â†’ {i.get('target', '?')} via {i.get('middleware', '?')}\n"
        if scope and isinstance(scope, dict):
            context += f"\n=== SCOPE PACKAGE ===\n{str(scope.get('scope_package', ''))[:2000]}\n"
        return context

    def _is_ams_mode(self) -> bool:
        contract_type = self.manifest.get("rfp", {}).get("contract_type", "")
        intake = self.manifest.get("intake_output", {})
        if isinstance(intake, dict):
            extracted_type = intake.get("extracted_fields", {}).get("contract_type", {})
            if isinstance(extracted_type, dict):
                contract_type = extracted_type.get("value", contract_type)
        return contract_type.lower() in (
            "ams",
            "managed_services",
            "managed services",
            "support",
        )

    def _get_ticket_data(self) -> list:
        tickets = self.manifest.get("ticket_data", [])
        if tickets:
            return tickets
        rfp_text = self.manifest.get("rfp_text", "")
        if "ticket" in rfp_text.lower() and (
            "category" in rfp_text.lower() or "module" in rfp_text.lower()
        ):
            lines = rfp_text.split("\n")
            parsed = []
            headers = None
            for line in lines:
                cols = [c.strip() for c in line.split(",")]
                if len(cols) >= 3:
                    if not headers and any(
                        h.lower()
                        in ("ticket", "id", "category", "module", "description")
                        for h in cols
                    ):
                        headers = [h.lower().strip() for h in cols]
                        continue
                    if headers:
                        row = {}
                        for i, h in enumerate(headers):
                            if i < len(cols):
                                row[h] = cols[i]
                        if row:
                            parsed.append(row)
            return parsed[:10000]
        return []

    async def observe(self) -> Dict[str, Any]:
        rfp_context = self._get_rfp_context()
        is_ams = self._is_ams_mode()
        products = ", ".join(self.manifest.get("rfp", {}).get("products", []))
        mode = "AMS managed services" if is_ams else "implementation"
        kb_context = await self.get_kb_context(
            f"solution architecture {mode} {products}",
            collections=["solution_templates", "sows"],
        )
        obs = {
            "rfp_context": rfp_context,
            "kb_context": kb_context,
            "client": self.manifest.get("client", {}),
            "rfp": self.manifest.get("rfp", {}),
            "is_ams": is_ams,
        }
        if is_ams:
            ticket_data = self._get_ticket_data()
            if ticket_data:
                obs["ticket_analysis"] = analyze_ticket_data(ticket_data)
                obs["has_tickets"] = True
            else:
                obs["has_tickets"] = False
        return obs

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\n"

        if obs.get("is_ams") and obs.get("has_tickets"):
            ta = obs["ticket_analysis"]
            return await self._orient_ams(obs, ta, kb_section)
        else:
            return await self._orient_standard(obs, kb_section)

    async def _orient_ams(self, obs, ticket_analysis, kb_section):
        summary = ticket_analysis["summary"]
        prompt = f"""Design an AMS operating model for this managed services engagement based on the RFP.

{obs["rfp_context"]}
{kb_section}

=== TICKET ANALYSIS ===
Total: {ticket_analysis["total_tickets"]} | Tiers: {ticket_analysis["tier_distribution"]} | Modules: {ticket_analysis["module_distribution"]}
Actions: Eliminate {summary["eliminate"]}, Shift-Left {summary["shift_left"]}, Automate {summary["automate"]}, Retain {summary["retain"]}
YoY Model: {ticket_analysis["yoy_optimization"]}

RULES: Do NOT hardcode any vendor name not in the RFP.

Return JSON:
{{
  "operating_model": {{
    "coverage_hours": "from RFP", "shift_structure": "proposed", "escalation_matrix": "L1â†’L2â†’L3â†’SME",
    "governance_cadence": "review structure"
  }},
  "staffing_pyramid": {{
    "l1_support": {{"count": 0, "location": "offshore", "shift": ""}},
    "l2_support": {{"count": 0, "location": "offshore", "shift": ""}},
    "l3_specialist": {{"count": 0, "location": "nearshore", "shift": ""}},
    "sdm": {{"count": 1, "location": "onshore"}},
    "tech_lead": {{"count": 1, "location": "nearshore"}}
  }},
  "sla_feasibility": {{
    "proposed_slas": ["from RFP"], "feasibility": "feasible|at_risk|infeasible", "risks": ["SLA risks"]
  }},
  "automation_roadmap": [{{"quarter": "Q1", "initiative": "", "expected_reduction": ""}}],
  "technology_stack": ["from RFP"],
  "technical_risks": ["specific risks"],
  "architecture_complexity": "standard|complex|enterprise",
  "mode": "ams"
}}"""
        result = await self.llm_json(prompt, max_tokens=5000)
        result["ticket_analysis"] = ticket_analysis
        return result

    async def _orient_standard(self, obs, kb_section):
        prompt = f"""Design the technical solution architecture for this engagement based on the RFP.

{obs["rfp_context"]}
{kb_section}

RULES: Do NOT hardcode any vendor or product name not in the RFP.

Return JSON:
{{
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
  "security_compliance": ["from RFP"],
  "tooling_strategy": ["tools needed"],
  "technical_risks": ["risks with mitigations"],
  "architecture_complexity": "standard|complex|enterprise",
  "mode": "implementation"
}}"""
        return await self.llm_json(prompt, max_tokens=5000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        mode = decision.get("mode", "implementation")

        if mode == "ams":
            return await self._act_ams(decision)
        else:
            return await self._act_standard(decision)

    async def _act_ams(self, decision):
        ticket_analysis = decision.get("ticket_analysis", {})
        staffing = decision.get("staffing_pyramid", {})
        total_staff = sum(
            v.get("count", 0) for v in staffing.values() if isinstance(v, dict)
        )

        prompt = f"""Write a professional AMS solution narrative (300-400 words).

STYLE: Data-dense consulting language. Every sentence must contain a specific number or fact. No markdown. No bullets. No asterisks. Flowing paragraphs. Client-ready.

AMS DATA:
Tickets: {ticket_analysis.get("total_tickets", 0)} | Tiers: {ticket_analysis.get("tier_distribution", {})}
Optimization: Eliminate {ticket_analysis.get("summary", {}).get("eliminate", 0)}, Automate {ticket_analysis.get("summary", {}).get("automate", 0)}, Shift-Left {ticket_analysis.get("summary", {}).get("shift_left", 0)}, Retain {ticket_analysis.get("summary", {}).get("retain", 0)}
Staff: {total_staff} FTEs | SLA feasibility: {decision.get("sla_feasibility", {}).get("feasibility", "N/A")}
YoY: {ticket_analysis.get("yoy_optimization", [])}

Write 4 impactful paragraphs:
1. Operating model â€” coverage model, staffing pyramid with FTE counts per tier and location, escalation structure.
2. Ticket analysis â€” volume insights, tier distribution, top modules, optimization potential.
3. Optimization strategy â€” Eliminate/Shift-Left/Automate actions with quantified FTE impact per category.
4. YoY roadmap â€” automation maturity phases, FTE reduction trajectory, ROI timeline."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)
        summary = (
            f"AMS solution for {ticket_analysis.get('total_tickets', 0)} tickets. "
        )
        summary += f"Automation: {ticket_analysis.get('summary', {}).get('eliminate', 0)} eliminate, "
        summary += f"{ticket_analysis.get('summary', {}).get('automate', 0)} automate. "
        summary += (
            f"Complexity: {decision.get('architecture_complexity', 'standard')}. "
        )
        summary += f"{len(decision.get('technical_risks', []))} risks identified."

        return {
            "solution_design": decision,
            "ticket_analysis": ticket_analysis,
            "narrative": narrative,
            "mode": "ams",
            "hitl_summary": summary,
        }

    async def _act_standard(self, decision):
        platforms = decision.get("platform_architectures", [])
        plat_text = " | ".join(
            [
                f"{p['platform']}: {p.get('technical_approach', '')[:60]}"
                for p in platforms
            ]
        )
        risks = decision.get("technical_risks", [])
        integrations = decision.get("integration_architecture", {})
        env = decision.get("environment_strategy", {})
        op_model = decision.get("operating_model", {})

        security = decision.get("security_compliance", [])
        decision.get("tooling_strategy", [])

        prompt = f"""Write a professional technical solution narrative (300-400 words).

STYLE: Data-dense consulting language. Every sentence must contain a specific number or fact. No markdown. No bullets. No asterisks. Client-ready.

SOLUTION DATA:
Platforms: {plat_text}
Integrations: {len(integrations.get("data_flows", []))} data flows via {integrations.get("middleware", [])}
Environments: {env.get("total_environments", 0)} ({env.get("promotion_path", "N/A")})
Operating Model: Coverage {op_model.get("coverage", "N/A")}, Distribution {op_model.get("team_distribution", "N/A")}
Risks: {len(risks)} identified | Complexity: {decision.get("architecture_complexity", "standard")}
Security: {security[:3] if security else "Standard"}

Write 4 impactful paragraphs:
1. Platform architecture â€” per-platform technical approach, modules, deployment model.
2. Operating model â€” team distribution, governance cadence, escalation with response times.
3. Integration and environment strategy â€” middleware, data flows, promotion path, monitoring.
4. Risk and security â€” key risks with mitigations, security posture, compliance readiness."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)
        summary = f"Solution for {len(platforms)} platforms. "
        summary += (
            f"Complexity: {decision.get('architecture_complexity', 'standard')}. "
        )
        summary += f"{len(risks)} risks identified."

        return {
            "platform_architectures": platforms,
            "integration_architecture": integrations,
            "environment_strategy": env,
            "operating_model": op_model,
            "security_compliance": decision.get("security_compliance", []),
            "tooling_strategy": decision.get("tooling_strategy", []),
            "technical_risks": risks,
            "architecture_complexity": decision.get(
                "architecture_complexity", "standard"
            ),
            "narrative": narrative,
            "mode": "implementation",
            "hitl_summary": summary,
        }
