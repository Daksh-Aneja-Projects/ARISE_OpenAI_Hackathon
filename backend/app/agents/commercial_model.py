"""
Commercial Model Agent â€” REAL calculations using rate cards, month-wise loading, P&L.
LLM determines WHAT roles are needed. Calculator does the MATH.
All prompts RFP-grounded â€” no hardcoded vendor names.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent
from app.config import settings


class CommercialModelAgent(BaseAgent):
    name = "Commercial Model Agent"
    agent_tier = (
        "critical"  # Financial precision matters — GPT-4o-mini best at arithmetic
    )

    async def observe(self) -> Dict[str, Any]:
        rfp_text = self.manifest.get("rfp_text", "")
        intake = self.get_upstream_result("intake_output")
        scope = self.get_upstream_result("scope_output")
        products = ", ".join(self.manifest.get("rfp", {}).get("products", []))
        contract_type = self.manifest.get("rfp", {}).get("contract_type", "")

        # Enforce Polystore Strictness (L3): Use Graph Cypher queries (L4 Reasoning Engine)
        # to determine rule contradictions before applying commercial logic.
        cypher_query = f"""
        MATCH (p:Product)-[:HAS_PRICING_RULE]->(r:Rule)
        WHERE p.name IN ['{products}'] AND r.contract_type = '{contract_type}'
        MATCH (r)-[:CONTRADICTS]-(c:Rule)
        RETURN r.statement AS rule, c.statement AS contradiction, r.confidence AS confidence
        ORDER BY r.confidence DESC
        """
        kb_context = await self.execute_cypher_query(
            query=cypher_query,
            fallback_rag_query=f"commercial model pricing {products} {contract_type}",
        )
        kb_rate_card = await self.get_kb_rate_card()

        # === RATE CARD ENGINE ===
        # Priority: 1. KB uploaded rate card  2. User-provided hourly rates  3. Config defaults
        user_ctx = self.manifest.get("user_context", {})
        if kb_rate_card:
            self._kb_rate_card = kb_rate_card
            self._rate_source = "kb_uploaded"
        elif any(
            user_ctx.get(k)
            for k in ["rate_onshore_usd", "rate_offshore_usd", "rate_nearshore_usd"]
        ):
            from app.services.commercial_calculator import build_rate_card_from_hourly

            onshore = user_ctx.get(
                "rate_onshore_usd", settings.DEFAULT_RATE_ONSHORE_USD
            )
            nearshore = user_ctx.get(
                "rate_nearshore_usd", settings.DEFAULT_RATE_NEARSHORE_USD
            )
            offshore = user_ctx.get(
                "rate_offshore_usd", settings.DEFAULT_RATE_OFFSHORE_USD
            )
            self._kb_rate_card = build_rate_card_from_hourly(
                onshore, nearshore, offshore
            )
            self._rate_source = (
                f"user_provided (${onshore}/${nearshore}/${offshore} per hr)"
            )
            self.log(
                "rate_card_from_user",
                {"onshore": onshore, "nearshore": nearshore, "offshore": offshore},
            )
        else:
            self._kb_rate_card = None
            self._rate_source = f"config_default (${settings.DEFAULT_RATE_ONSHORE_USD}/${settings.DEFAULT_RATE_NEARSHORE_USD}/${settings.DEFAULT_RATE_OFFSHORE_USD} per hr)"

        # === L23 Machine Economy (Agent Micro-transactions) ===
        # The commercial agent autonomously determines if it lacks critical external data
        # to price the contract accurately, and if so, purchases it.
        external_intel = None
        intel_prompt = f"""Analyze the RFP context. Are there specific macro-economic or regional risks (e.g., inflation, union strikes, currency volatility) that require external data to price accurately?
RFP Snippet: {rfp_text[:1000]}
Return JSON strictly in this format: {{"needs_data": true/false, "asset_ref": "description of data needed", "estimated_price": 0.05, "seller_agent": "bloomberg_macro_agent"}}"""

        try:
            intel_decision = await self.llm_json(intel_prompt)
            if intel_decision.get("needs_data") and intel_decision.get("asset_ref"):
                asset = intel_decision["asset_ref"]
                # Use local KB to find relevant market data
                intel_result = await self.get_kb_context(query=f"market data {asset}")
                if intel_result and len(intel_result) > 10:
                    external_intel = f"Market Intelligence ({asset}): {intel_result}"
                    self.log("external_intel_found", {"asset": asset})
                else:
                    external_intel = (
                        f"No historical intelligence found for asset: {asset}"
                    )
                    self.log("external_intel_not_found", {"asset": asset})
        except Exception as e:
            self.log("intel_lookup_failed", {"error": str(e)})

        # === PRICING OPTIMIZER (from past learnings) ===
        pricing_learnings = self.get_past_learnings("commercial_model")

        # === TRANSITION PLAN (from transition agent) ===
        transition = self.get_upstream_result("transition_change_output")

        # === DATA INTELLIGENCE (from data analyst) ===
        data_intel_raw = self.get_upstream_result("data_analyst_output")

        # === AUTOMATION SAVINGS (from automation_ai agent) ===
        automation_output = self.get_upstream_result("automation_ai_output")

        return {
            "rfp_text": self.get_rfp_sections("commercial_model"),
            "intake": intake,
            "scope": scope,
            "client": self.manifest.get("client", {}),
            "kb_context": kb_context,
            "kb_rate_card": self._kb_rate_card,
            "pricing_learnings": pricing_learnings,
            "rate_source": self._rate_source,
            "external_intel": external_intel,
            "transition_plan": transition,
            "data_analyst": data_intel_raw,
            "automation_output": automation_output,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """LLM analyzes the RFP to determine team composition and commercial parameters."""
        scope_info = ""
        if obs["scope"] and isinstance(obs["scope"], dict):
            sp = obs["scope"].get("scope_package", obs["scope"])
            scope_info = (
                "\n=== SCOPE BUILDER OUTPUT (AUTHORITATIVE â€” USE THIS TEAM) ===\n"
            )
            scope_info += f"Total Effort: {sp.get('total_effort_days', 0)} days\n"
            scope_info += f"Timeline: {sp.get('timeline_months', 0)} months\n"
            scope_info += f"Products: {', '.join(sp.get('products_in_scope', []))}\n"

            # Format team model explicitly so the LLM can see each role
            team_model = sp.get("team_model", [])
            if team_model and isinstance(team_model, list):
                total_fte = sum(
                    r.get("count", 0) for r in team_model if isinstance(r, dict)
                )
                scope_info += f"\nTEAM MODEL ({total_fte} total FTEs â€” you MUST use these roles and counts):\n"
                for r in team_model:
                    if isinstance(r, dict):
                        scope_info += f"  - {r.get('role', 'Unknown')}: {r.get('count', 1)} FTEs, {r.get('location', 'offshore')}"
                        if r.get("platform"):
                            scope_info += f" (for {r['platform']})"
                        scope_info += "\n"
                scope_info += f"\nCRITICAL: Your resources array MUST include ALL {total_fte} FTEs from the team model above.\n"
                scope_info += "Map each scope role to the nearest standard role name from the list below.\n"
                scope_info += "Do NOT invent your own team â€” use the scope builder's team model as the source of truth.\n"

        data_intel_info = ""
        data_intel = obs.get("data_analyst", {})
        if data_intel:
            data_intel_info = "\n=== DATA INTELLIGENCE (L3 Constraint) ===\n"
            data_intel_info += f"Volumes: {data_intel.get('volume_summary', 'N/A')}\n"
            data_intel_info += (
                f"Staffing Indicators: {data_intel.get('staffing_indicators', 'N/A')}\n"
            )

        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\n"

        external_intel_section = ""
        if obs.get("external_intel"):
            external_intel_section = f"\n=== EXTERNAL INTEL (L23 Quantum Smart Contract) ===\n{obs['external_intel']}\n"

        # Extract contract duration from intake if available
        intake_duration = ""
        intake = obs.get("intake", {})
        ef = intake.get("extracted_fields", intake)
        dur = ef.get("contract_duration", {})
        if isinstance(dur, dict):
            dur_val = dur.get("value", "")
            init_months = dur.get("initial_months", 0)
            total_max = dur.get("total_max_months", 0)
            if dur_val and dur_val.lower() not in (
                "not specified",
                "not specified in document",
                "unknown",
                "null",
                "",
            ):
                intake_duration = (
                    f"\n=== CONTRACT DURATION (from RFP) ===\nDuration: {dur_val}"
                )
                if init_months:
                    intake_duration += f"\nInitial period: {init_months} months"
                if total_max:
                    intake_duration += (
                        f"\nTotal max (with extensions): {total_max} months"
                    )
                intake_duration += "\nIMPORTANT: Use this EXACT duration for contract_months. Do NOT default to 12.\n"

        # Inject transition plan from transition_change agent
        transition_section = ""
        tp = obs.get("transition_plan", {})
        if tp and isinstance(tp, dict):
            tp_plan = tp.get("transition_plan", tp)
            tw = (
                tp_plan.get("total_duration_weeks", 0)
                if isinstance(tp_plan, dict)
                else 0
            )
            phases = tp_plan.get("phases", []) if isinstance(tp_plan, dict) else []
            if tw:
                transition_section = "\n=== TRANSITION PLAN (from Transition Agent â€” use as ground truth) ===\n"
                transition_section += f"Total Transition Duration: {tw} weeks ({round(tw / 4.3, 1)} months)\n"
                transition_section += f"Phases: {len(phases)}\n"
                transition_section += "IMPORTANT: Use this duration for transition_months. Do NOT guess.\n"

        prompt = f"""Analyze this RFP and determine the commercial model â€” team, contract params, costs.

RULES:
- Derive EVERY parameter from the RFP content
- contract_months: MUST match the RFP contract duration. Look for patterns like "2+1+1 years", "initial term X years with Y optional extensions", "36 months". Convert to total initial months (excluding optional extensions). If RFP says "2+1+1 years", contract_months = 24 (the initial 2 years).
- TEAM SIZING: If a SCOPE BUILDER team model is provided above, you MUST use those EXACT roles and FTE counts. Copy the count values directly. Do NOT reduce to 1 FTE per role.
- If no scope builder team model, size team based on product count, integrations, countries, SLAs. STRICTLY anchor resource loading numbers to the DATA INTELLIGENCE volume metrics to prevent hallucinations.
- Use these EXACT role names: Service Delivery Manager, Program Manager, Solution Architect, Technical Lead, Senior Consultant, Consultant, Associate Consultant, Test Lead, Test Engineer, DevOps Engineer, Integration Specialist, Business Analyst, Change Manager, Service Owner

=== RFP DOCUMENT ===
{obs["rfp_text"]}
{scope_info}
{data_intel_info}
{kb_section}
{external_intel_section}
{intake_duration}
{transition_section}

Return JSON:
{{
  "resources": [
    {{"role": "exact role name from list above", "count": 3, "location": "onshore|nearshore|offshore", "start_month": 1, "justification": "RFP requirement driving this"}}
  ],
  "contract_months": 24,
  "extension_options": "e.g. 2x12 months optional",
  "transition_months": 2,
  "pricing_model": "managed_services|time_material|outcome_based",
  "currency": "USD",
  "target_margin_percent": 22,
  "transition_cost_estimate": 0,
  "tools_monthly_cost": 0,
  "travel_annual_cost": 0,
  "contingency_percent": 3,
  "cost_derivation": {{
    "travel_calculation": "N countries x N trips x $N = $total",
    "tools_calculation": "N platforms x $N/month = $total",
    "transition_calculation": "N platforms x N weeks x team cost = $total"
  }},
  "pricing_notes": "RFP pricing signals",
  "efficiency_targets": ["automation opportunities"],
  "commercial_risks": ["commercial risks with RFP refs"]
}}

CRITICAL: The total FTE count across all resources MUST be realistic for the scope. A multi-platform enterprise deal typically needs 10-25+ FTEs, NOT 1 per role. Match the scope builder's team model if provided."""
        return await self.llm_json(prompt)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """Use the REAL calculator to compute actual financials with 3 scenarios + guardrails."""
        from app.services.commercial_calculator import (
            calculate_resource_loading,
            calculate_pl,
            calculate_scenarios,
            check_margin_guardrails,
            get_rate_card,
            set_rate_card,
            set_active_rate_card,
        )

        if getattr(self, "_kb_rate_card", None):
            set_rate_card("kb_uploaded", self._kb_rate_card)
            set_active_rate_card("kb_uploaded")
            self.log(
                "using_kb_rate_card",
                {
                    "roles": sum(
                        len(v)
                        for v in self._kb_rate_card.values()
                        if isinstance(v, dict)
                    )
                },
            )

        def safe_num(val, fallback=0):
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                import re

                nums = re.findall(r"[\d,]+\.?\d*", val.replace(",", ""))
                if nums:
                    try:
                        return float(nums[0])
                    except ValueError:
                        pass
            return fallback

        resources = orientation.get("resources", [])
        contract_months = int(safe_num(orientation.get("contract_months"), 12))
        transition_months = int(safe_num(orientation.get("transition_months"), 1))
        target_margin = safe_num(orientation.get("target_margin_percent"), 22)
        transition_cost = safe_num(orientation.get("transition_cost_estimate"), 0)
        tools_monthly = safe_num(orientation.get("tools_monthly_cost"), 0)
        travel_annual = safe_num(orientation.get("travel_annual_cost"), 0)
        contingency_pct = safe_num(orientation.get("contingency_percent"), 3)

        # =================================================================
        # UPSTREAM AGENT WIRING â€” Ground truth from pipeline, not LLM guesses
        # =================================================================
        # The downstream agents already analyzed the RFP. Commercial should
        # consume their structured output directly for numerical accuracy.

        # --- 1. TEAM MODEL from Scope Builder (authoritative for resource plan) ---
        scope_output = self.manifest.get("scope_output", {})
        if scope_output and isinstance(scope_output, dict):
            sp = scope_output.get("scope_package", scope_output)
            if isinstance(sp, dict):
                team_model = sp.get("team_model", [])
                if team_model and isinstance(team_model, list):
                    # Map scope roles to standard calculator role names
                    ROLE_MAP = {
                        "functional analyst": "Senior Consultant",
                        "functional consultant": "Senior Consultant",
                        "developer": "Consultant",
                        "release manager": "Technical Lead",
                        "integration specialist": "Integration Specialist",
                        "support analyst": "Consultant",
                        "test analyst": "Test Engineer",
                        "test lead": "Test Lead",
                        "devops engineer": "DevOps Engineer",
                        "business analyst": "Business Analyst",
                        "change manager": "Change Manager",
                        "service delivery manager": "Service Delivery Manager",
                        "program manager": "Program Manager",
                        "solution architect": "Solution Architect",
                        "technical lead": "Technical Lead",
                        "senior consultant": "Senior Consultant",
                        "consultant": "Consultant",
                        "associate consultant": "Associate Consultant",
                        "service owner": "Service Owner",
                    }
                    scope_resources = []
                    for r in team_model:
                        if not isinstance(r, dict):
                            continue
                        role_raw = r.get("role", "Consultant")
                        count = safe_num(r.get("count", r.get("fte", 1)), 1)
                        location = r.get("location", "offshore").lower()
                        # Normalize location
                        if location not in ("onshore", "nearshore", "offshore"):
                            location = "offshore"
                        # Map role name to standard calculator role
                        role_mapped = ROLE_MAP.get(role_raw.lower(), role_raw)
                        # If role_mapped not in standard set, try partial match
                        standard_roles = set(ROLE_MAP.values())
                        if role_mapped not in standard_roles:
                            for std in standard_roles:
                                if (
                                    role_raw.lower() in std.lower()
                                    or std.lower() in role_raw.lower()
                                ):
                                    role_mapped = std
                                    break
                            else:
                                role_mapped = "Consultant"  # Safe default
                        scope_resources.append(
                            {
                                "role": role_mapped,
                                "count": count,
                                "location": location,
                                "start_month": 1,
                                "justification": f"From scope builder: {role_raw}",
                            }
                        )
                    if scope_resources:
                        scope_fte = sum(r["count"] for r in scope_resources)
                        llm_fte = sum(safe_num(r.get("count", 0), 0) for r in resources)
                        self.log(
                            "team_model_wired_from_scope",
                            {
                                "scope_fte": scope_fte,
                                "llm_fte": llm_fte,
                                "scope_roles": len(scope_resources),
                                "override": True,
                            },
                        )
                        resources = scope_resources

                # Also pull contract timeline from scope if available
                scope_months = safe_num(sp.get("timeline_months"), 0)
                if scope_months > 0 and scope_months != contract_months:
                    self.log(
                        "contract_months_from_scope",
                        {
                            "llm_value": contract_months,
                            "scope_value": int(scope_months),
                        },
                    )
                    contract_months = int(scope_months)

        # --- 2. CONTRACT DURATION from Intake (authoritative for contract_months) ---
        intake_output = self.manifest.get("intake_output", {})
        if intake_output and isinstance(intake_output, dict):
            ef = intake_output.get("extracted_fields", intake_output)
            if isinstance(ef, dict):
                dur = ef.get("contract_duration", {})
                if isinstance(dur, dict):
                    init_months = safe_num(dur.get("initial_months"), 0)
                    safe_num(dur.get("total_max_months"), 0)
                    if init_months > 0:
                        if init_months != contract_months:
                            self.log(
                                "contract_months_from_intake",
                                {
                                    "current": contract_months,
                                    "intake_initial_months": int(init_months),
                                },
                            )
                        contract_months = int(init_months)

        # --- 3. TRANSITION TIMELINE from Transition Agent (authoritative) ---

        # === DYNAMIC TRANSITION TIMELINE FROM UPSTREAM AGENT ===
        # Pull the REAL transition duration from the transition agent output.
        # Do NOT rely on the LLM's guess â€” the transition agent already analyzed the RFP.
        transition_output = self.get_upstream_result("transition_change_output")
        if transition_output and isinstance(transition_output, dict):
            tp = transition_output.get("transition_plan", transition_output)
            if isinstance(tp, dict):
                total_weeks = safe_num(tp.get("total_duration_weeks"), 0)
                if total_weeks > 0:
                    derived_months = max(round(total_weeks / 4.3), 1)
                    if derived_months != transition_months:
                        self.log(
                            "transition_months_override",
                            {
                                "llm_value": transition_months,
                                "transition_agent_weeks": total_weeks,
                                "derived_months": derived_months,
                            },
                        )
                        transition_months = derived_months

        # === FINAL FLOOR GUARD â€” contract_months must be reasonable ===
        # An enterprise AMS deal can never be 0 months. If LLM returned 0 or
        # upstream didn't provide a value, default to 24 months (standard AMS).
        if contract_months < 6:
            self.log(
                "contract_months_floor_applied",
                {
                    "raw_value": contract_months,
                    "corrected_to": 24,
                    "reason": "Enterprise AMS deals require minimum 6-month term; defaulting to 24",
                },
            )
            contract_months = 24

        # === PROGRAMMATIC COST GUARDRAILS ===
        # When LLM returns $0 for these critical cost lines, derive them from real data.
        # An enterprise AMS deal should NEVER have $0 transition/tools/travel.
        from app.services.commercial_calculator import get_rate

        rate_card = get_rate_card()

        if resources:
            # -- Transition Cost: If $0, calculate from team Ã— transition_months Ã— ramp factor --
            if transition_cost == 0 and transition_months > 0:
                monthly_team_cost = sum(
                    get_rate(
                        r.get("role", "Consultant"),
                        r.get("location", "offshore"),
                        rate_card,
                    )
                    * r.get("count", 1)
                    for r in resources
                )
                # During transition, team runs at ~50% utilization (KT, shadow, parallel run)
                transition_cost = round(monthly_team_cost * transition_months * 0.5)
                self.log(
                    "transition_cost_derived",
                    {
                        "monthly_team_cost": monthly_team_cost,
                        "transition_months": transition_months,
                        "calculated": transition_cost,
                    },
                )

            # -- Tools & Infra: If $0, estimate from platform count --
            if tools_monthly == 0:
                # Derive platform count from upstream intake/scope data
                intake = self.get_upstream_result("intake_output") or {}
                platforms = (
                    intake.get("platform_details", [])
                    if isinstance(intake, dict)
                    else []
                )
                num_platforms = max(len(platforms), 1)
                scope = self.get_upstream_result("scope_output") or {}
                if isinstance(scope, dict):
                    sp = scope.get("scope_package", scope)
                    scope_products = (
                        sp.get("products_in_scope", []) if isinstance(sp, dict) else []
                    )
                    num_platforms = max(num_platforms, len(scope_products), 1)
                # $500/month per platform for monitoring, ITSM, CI/CD, test tooling
                tools_monthly = round(num_platforms * 500)
                self.log(
                    "tools_monthly_derived",
                    {"platforms": num_platforms, "calculated": tools_monthly},
                )

            # -- Travel: If $0, estimate from onshore FTE count --
            if travel_annual == 0:
                onshore_fte = sum(
                    r.get("count", 0)
                    for r in resources
                    if r.get("location", "").lower() == "onshore"
                )
                # Each onshore FTE: ~4 client-site visits/year Ã— $3,750 avg per trip
                if onshore_fte > 0:
                    travel_annual = round(onshore_fte * 4 * 3750)
                else:
                    # Even offshore-heavy deals need SDM/PM travel: $15K base
                    travel_annual = 15000
                self.log(
                    "travel_annual_derived",
                    {"onshore_fte": onshore_fte, "calculated": travel_annual},
                )

        # --- 4. CHANGE MANAGEMENT COST from Transition Agent ---
        change_management_cost = 0
        transition_output = self.manifest.get("transition_change_output", {})
        if transition_output and isinstance(transition_output, dict):
            cm = transition_output.get("change_management", {})
            if isinstance(cm, dict):
                training_count = len(cm.get("training_plan", []))
                stakeholder_count = len(cm.get("stakeholder_groups", []))
                comms_count = len(cm.get("communication_plan", []))
                # Derive cost: training programs Ã— $5K + stakeholder workshops Ã— $3K + comms setup Ã— $2K
                change_management_cost = (
                    (training_count * 5000)
                    + (stakeholder_count * 3000)
                    + (comms_count * 2000)
                )
                if change_management_cost > 0:
                    self.log(
                        "change_management_cost_derived",
                        {
                            "training_programs": training_count,
                            "stakeholder_groups": stakeholder_count,
                            "comm_channels": comms_count,
                            "total": change_management_cost,
                        },
                    )

        # --- 5. AUTOMATION YOY SAVINGS from Automation Agent ---
        automation_yoy = []
        automation_opportunity_breakdown = []
        total_automation_savings_annual = 0
        automation_data = self.manifest.get("automation_ai_output", {})
        if automation_data and isinstance(automation_data, dict):
            platform_sections = automation_data.get("platform_sections", [])
            cross_platform = automation_data.get("cross_platform", [])
            all_opps = []
            for section in platform_sections:
                if isinstance(section, dict):
                    for opp in section.get("opportunities", []):
                        if isinstance(opp, dict):
                            all_opps.append(opp)
            for cp in cross_platform:
                if isinstance(cp, dict):
                    all_opps.append(cp)

            # Use estimated_fte_reduction from automation agent (dynamic per-opportunity)
            # Only fall back to priority-based estimate when agent didn't provide a number
            monthly_team_cost = 0
            if resources:
                monthly_team_cost = sum(
                    get_rate(
                        r.get("role", "Consultant"),
                        r.get("location", "offshore"),
                        rate_card,
                    )
                    * r.get("count", 1)
                    for r in resources
                )
            total_fte = (
                max(sum(r.get("count", 1) for r in resources), 1) if resources else 1
            )
            cost_per_fte_annual = (
                (monthly_team_cost / total_fte) * 12 if resources else 36000
            )

            automation_opportunity_breakdown = []
            for opp in all_opps:
                # Dynamic: use agent-provided FTE reduction if available
                fte_saved = safe_num(opp.get("estimated_fte_reduction"), 0)
                if fte_saved == 0:
                    # Fallback: estimate from priority when agent didn't provide
                    priority = (opp.get("priority", "MEDIUM") or "MEDIUM").upper()
                    if priority in ("CRITICAL", "HIGH"):
                        fte_saved = 0.5
                    elif priority == "MEDIUM":
                        fte_saved = 0.25
                    else:
                        fte_saved = 0.1
                annual_saving = round(fte_saved * cost_per_fte_annual)
                total_automation_savings_annual += annual_saving
                automation_opportunity_breakdown.append(
                    {
                        "id": opp.get("id", ""),
                        "title": opp.get("title", ""),
                        "platform": opp.get("platform", "Cross-Platform"),
                        "priority": opp.get("priority", "MEDIUM"),
                        "estimated_fte_reduction": fte_saved,
                        "annual_saving_usd": annual_saving,
                        "benefit": opp.get("benefit", ""),
                        "effort": opp.get("effort", ""),
                        "horizon": opp.get("horizon", ""),
                    }
                )

            # Build YOY optimization curve
            contract_years = max(contract_months // 12, 1)
            for year in range(1, contract_years + 1):
                # Realization ramps: Y1 20% (building), Y2 60% (stabilizing), Y3+ 100% (mature)
                if year == 1:
                    realization = 0.2
                elif year == 2:
                    realization = 0.6
                else:
                    realization = 1.0
                realized_saving = round(total_automation_savings_annual * realization)
                automation_yoy.append(
                    {
                        "year": year,
                        "automation_savings": realized_saving,
                        "realization_pct": round(realization * 100),
                        "cumulative_savings": round(
                            total_automation_savings_annual
                            * sum(
                                0.2 if y == 1 else 0.6 if y == 2 else 1.0
                                for y in range(1, year + 1)
                            )
                        ),
                    }
                )

            if total_automation_savings_annual > 0:
                self.log(
                    "automation_yoy_calculated",
                    {
                        "opportunities_count": len(all_opps),
                        "annual_savings_potential": total_automation_savings_annual,
                        "contract_years": contract_years,
                    },
                )

        import asyncio

        loop = asyncio.get_event_loop()

        loading = await loop.run_in_executor(
            None,
            lambda: calculate_resource_loading(
                resources=resources,
                contract_months=contract_months,
                transition_months=transition_months,
            ),
        )
        pl = await loop.run_in_executor(
            None,
            lambda: calculate_pl(
                resource_loading=loading,
                target_margin_percent=target_margin,
                transition_cost=transition_cost + change_management_cost,
                tools_monthly=tools_monthly,
                travel_annual=travel_annual,
                contingency_percent=contingency_pct,
            ),
        )
        scenarios = await loop.run_in_executor(
            None,
            lambda: calculate_scenarios(
                resources=resources,
                contract_months=contract_months,
                transition_months=transition_months,
                transition_cost=transition_cost + change_management_cost,
                tools_monthly=tools_monthly,
                travel_annual=travel_annual,
                contingency_percent=contingency_pct,
                target_margin_percent=target_margin,
            ),
        )

        margin = pl["profitability"]["margin_percent"]
        guardrail = check_margin_guardrails(margin)
        rate_card = get_rate_card()

        return {
            "resources": resources,
            "resource_loading": loading,
            "pl_model": pl,
            "scenarios": scenarios,
            "margin_guardrail": guardrail,
            "rate_card_used": rate_card,
            "contract_params": {
                "months": contract_months,
                "transition_months": transition_months,
                "pricing_model": orientation.get("pricing_model"),
                "currency": orientation.get("currency", "USD"),
            },
            "cost_breakdown_detail": {
                "transition_cost": transition_cost,
                "change_management_cost": change_management_cost,
                "tools_monthly": tools_monthly,
                "travel_annual": travel_annual,
            },
            "automation_yoy": automation_yoy,
            "automation_savings_annual": total_automation_savings_annual,
            "automation_opportunity_breakdown": automation_opportunity_breakdown,
            "efficiency_targets": orientation.get("efficiency_targets", []),
            "commercial_risks": orientation.get("commercial_risks", []),
        }

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the narrative around the REAL numbers."""
        pl = decision["pl_model"]
        loading = decision["resource_loading"]
        resources = decision["resources"]
        params = decision["contract_params"]

        revenue = pl["revenue"]
        costs = pl["costs"]
        profit = pl["profitability"]
        loc_split = loading["cost_by_location"]
        total_loc = sum(loc_split.values()) or 1
        total_fte = sum(r.get("count", 0) for r in resources)
        onshore_fte = sum(
            r.get("count", 0) for r in resources if r.get("location") == "onshore"
        )
        offshore_fte = sum(
            r.get("count", 0) for r in resources if r.get("location") == "offshore"
        )

        prompt = f"""Write a concise commercial proposition narrative (180-250 words max).

STYLE: Strategic consulting language for a commercial proposal. Use rich Markdown (### sub-headers, bullet points). No bullets. No asterisks. Flowing paragraphs with EXACT financial figures. Client-ready.

FINANCIALS (USE THESE EXACT NUMBERS):
TCV: ${revenue["total_contract_value"]:,.0f} ({params["months"]} months)
Annual: ${revenue["annual_revenue"]:,.0f} | Monthly: ${revenue["monthly_price"]:,.0f}
Team: {total_fte:.0f} FTEs ({onshore_fte:.0f} onshore, {offshore_fte:.0f} offshore)
COGS: ${costs["total_cogs"]:,.0f} | Margin: {profit["margin_percent"]:.1f}%
Location split: Onshore ${loc_split["onshore"]:,.0f} ({loc_split["onshore"] / total_loc * 100:.0f}%), Offshore ${loc_split["offshore"]:,.0f} ({loc_split["offshore"] / total_loc * 100:.0f}%)

Write 3 tight paragraphs:
1. Team and delivery model â€” role composition, FTE counts, onshore/offshore ratio. Link each role to RFP requirements.
2. Commercial proposition â€” TCV, annual run rate, monthly pricing. Cost structure breakdown. Pricing model rationale.
3. Value and efficiency â€” YoY optimization targets, margin health, commercial risks and how they're mitigated."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"TCV: ${revenue['total_contract_value']:,.0f} over {params['months']} months. "
        summary += f"Team: {total_fte:.0f} FTEs ({onshore_fte:.0f} onshore, {offshore_fte:.0f} offshore). "
        summary += f"Monthly: ${revenue['monthly_price']:,.0f}. Margin: {profit['margin_percent']:.1f}%."

        monthly_summary = []
        breakdown = loading.get("monthly_breakdown", [])
        for m in breakdown[:6]:
            monthly_summary.append(
                {"month": m["month"], "fte": m["total_fte"], "cost": m["total_cost"]}
            )
        if len(breakdown) > 6:
            last = breakdown[-1]
            monthly_summary.append(
                {
                    "month": last["month"],
                    "fte": last["total_fte"],
                    "cost": last["total_cost"],
                }
            )

        scenarios = decision.get("scenarios", {})
        guardrail = decision.get("margin_guardrail", {})
        comparison = scenarios.get("comparison", {})

        if guardrail.get("status") == "flag":
            summary += f" âš ï¸ MARGIN ALERT: {guardrail['message']}"
        elif guardrail.get("status") == "block":
            summary += f" ðŸ›‘ MARGIN BLOCK: {guardrail['message']}"
        if comparison:
            summary += f" Scenario range: {comparison.get('tcv_range', 'N/A')}."

        return {
            "narrative": narrative,
            "resource_plan": resources,
            "resource_loading": {
                "monthly_summary": monthly_summary,
                "total_fte_months": loading["total_fte_months"],
                "average_monthly_cost": loading["average_monthly_cost"],
                "cost_by_location": loading["cost_by_location"],
            },
            "pl_model": pl,
            "scenarios": {
                "comparison": comparison,
                "base": {
                    "tcv": comparison.get("base_tcv"),
                    "margin": comparison.get("base_margin"),
                },
                "aggressive": {
                    "tcv": comparison.get("aggressive_tcv"),
                    "margin": comparison.get("aggressive_margin"),
                },
                "conservative": {
                    "tcv": comparison.get("conservative_tcv"),
                    "margin": comparison.get("conservative_margin"),
                },
            },
            "margin_guardrail": guardrail,
            "contract_params": params,
            "efficiency_targets": decision.get("efficiency_targets", []),
            "commercial_risks": decision.get("commercial_risks", []),
            "hitl_summary": summary,
        }
