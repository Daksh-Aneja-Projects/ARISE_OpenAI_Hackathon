"""
Scope Builder Agent â€” Generates WBS, scope matrix, effort estimation, team model.
Token-efficient: uses compact JSON with minimal nesting to prevent truncation.
Each work package maps to specific RFP sections and deliverables.
"""

import math
from typing import Any, Dict
from app.agents.base import BaseAgent


class ScopeBuilderAgent(BaseAgent):
    name = "Scope Builder Agent"
    agent_tier = "volume"

    # â”€â”€ PRODUCT TAXONOMY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # These keyword sets are intentionally broad so they match across any RFP,
    # not just INGKA. The classification drives FTE benchmarking:
    #   PRIMARY   â†’ full fte_per_platform multiplier (config, support, release)
    #   MIDDLEWARE â†’ lighter fte_per_middleware multiplier (shared integration team)
    #   ENDPOINT   â†’ zero platform FTEs (integrated WITH, not managed BY us)
    _MIDDLEWARE_KEYWORDS = {
        "boomi",
        "workato",
        "mulesoft",
        "tibco",
        "jitterbit",
        "dell boomi",
        "azure integration",
        "aws glue",
        "informatica",
        "snaplogic",
        "talend",
        "apigee",
        "kong",
        "azure api",
        "aws api gateway",
        "ibm mq",
        "kafka",
        "rabbitmq",
        "nifi",
        "celigo",
        "tray.io",
        "make",
        "zapier",
    }
    _ENDPOINT_KEYWORDS = {
        # Payroll & HR adjacent systems â€” integrated with, not managed by AMS
        "sap hcm",
        "sap",
        "adp",
        "workday",
        "successfactors",
        "sf",
        "peoplesoft",
        "oracle hcm",
        "bamboohr",
        "ceridian",
        "dayforce",
        "kronos hcm",
        "isolved",
        # Data platforms / cloud infra
        "gcp",
        "google cloud",
        "aws",
        "azure",
        "snowflake",
        "databricks",
        "power bi",
        "tableau",
        "looker",
        "dbt",
        # Downstream payroll/finance hubs (data handoff targets)
        "ppdh",
        "pymw",
        "gv",
        "emd",
        "emd-12",
        "payroll vendor",
        # Generic integration patterns that aren't platforms
        "sftp",
        "api",
        "file",
        "batch",
        "real-time",
        # Identity / security infra
        "okta",
        "azure ad",
        "active directory",
        "ping identity",
        # ITSM tooling (governance tooling, not an AMS platform)
        "servicenow",
        "jira",
        "confluence",
        # Specific module/component names that aren't standalone platforms
        "timekeeping",
        "scheduling",
        "absence",
        "opp workload import",
        "opp bs import",
        "activiti",
        "workload import",
        "bs import",
    }

    @staticmethod
    def _classify_products(products: list) -> tuple:
        """
        Split a raw product list into (primary_platforms, middleware_tools, endpoints).

        Applies to any RFP â€” keywords are domain-general, not client-specific.
        Returns three lists; callers use len() for FTE benchmarking.
        """
        primary, middleware, endpoints = [], [], []
        for p in products:
            p_lower = p.lower().strip()
            # Middleware check first (Boomi / Workato could also match "integration")
            if any(kw in p_lower for kw in ScopeBuilderAgent._MIDDLEWARE_KEYWORDS):
                middleware.append(p)
            elif any(kw in p_lower for kw in ScopeBuilderAgent._ENDPOINT_KEYWORDS):
                endpoints.append(p)
            else:
                primary.append(p)
        return primary, middleware, endpoints

    def _get_rfp_context(self) -> str:
        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )
        context = self.get_rfp_sections("scope_builder") + "\n\n"

        # FIX 1: scope_sections and kpi_sla_table are CRITICAL for scope accuracy.
        # They were previously excluded â€” now only raw sub-objects that are
        # rendered separately below are skipped to avoid duplication.
        if extracted:
            context += "=== INTAKE FINDINGS ===\n"
            for k, v in extracted.items():
                if k in ("platform_details", "integration_inventory"):
                    continue  # rendered in dedicated sections below
                val = v.get("value", v) if isinstance(v, dict) else v
                context += f"- {k}: {val}\n"

        # FIX 2: Inject kpi_sla_table explicitly â€” drives SLA-specific work packages
        kpi_sla = extracted.get("kpi_sla_table", {})
        if kpi_sla:
            context += "\n=== KPI / SLA REQUIREMENTS ===\n"
            if isinstance(kpi_sla, dict):
                for metric, detail in kpi_sla.items():
                    context += f"- {metric}: {detail}\n"
            elif isinstance(kpi_sla, list):
                for row in kpi_sla:
                    context += f"- {row}\n"

        # FIX 3: Inject scope_sections explicitly â€” defines in/out-of-scope boundaries
        scope_sections = extracted.get("scope_sections", {})
        if scope_sections:
            context += "\n=== SCOPE SECTIONS FROM RFP ===\n"
            if isinstance(scope_sections, dict):
                for section, detail in scope_sections.items():
                    context += f"- {section}: {detail}\n"
            elif isinstance(scope_sections, list):
                for s in scope_sections:
                    context += f"- {s}\n"

        # FIX 4: Raise platform cap from 5 â†’ 10 and log truncation warnings
        MAX_PLATFORMS = 10
        platforms = (
            intake.get("platform_details", []) if isinstance(intake, dict) else []
        )
        if platforms:
            context += "\n=== PLATFORM DETAILS ===\n"
            for p in platforms[:MAX_PLATFORMS]:
                context += (
                    f"- {p.get('product_name', '?')}: {p.get('user_count', '?')} users, "
                    f"{p.get('countries_deployed', '?')} countries\n"
                )
            if len(platforms) > MAX_PLATFORMS:
                self.log(
                    "platform_truncation_warning",
                    {
                        "total": len(platforms),
                        "shown": MAX_PLATFORMS,
                        "note": "Increase MAX_PLATFORMS if more platforms must reach the LLM",
                    },
                )
                context += (
                    f"[WARNING: {len(platforms) - MAX_PLATFORMS} additional platforms "
                    f"truncated from context â€” review MAX_PLATFORMS]\n"
                )

        # FIX 5: Raise integration cap from 6 â†’ 15 and log truncation warnings
        MAX_INTEGRATIONS = 15
        integrations = (
            intake.get("integration_inventory", []) if isinstance(intake, dict) else []
        )
        if integrations:
            context += f"\n=== INTEGRATIONS: {len(integrations)} identified ===\n"
            for i in integrations[:MAX_INTEGRATIONS]:
                context += f"- {i.get('source', '?')} â†’ {i.get('target', '?')} ({i.get('type', '?')})\n"
            if len(integrations) > MAX_INTEGRATIONS:
                self.log(
                    "integration_truncation_warning",
                    {"total": len(integrations), "shown": MAX_INTEGRATIONS},
                )
                context += (
                    f"[WARNING: {len(integrations) - MAX_INTEGRATIONS} additional integrations "
                    f"truncated from context]\n"
                )

        # FIX 6: Raise app analysis cap from 10 â†’ 20 and log truncation warnings
        MAX_APPS = 20
        data_analysis = self.manifest.get("data_analysis", {})
        if data_analysis:
            app_analysis = data_analysis.get("application_analysis", [])
            vol = data_analysis.get("volume_summary", {})
            staff = data_analysis.get("staffing_indicators", {})
            if app_analysis or vol:
                context += (
                    "\n=== OPERATIONAL DATA ANALYSIS (from ticket/volume dumps) ===\n"
                )
                if vol:
                    context += (
                        f"Total Tickets: {vol.get('total_tickets', '?')} | "
                        f"Monthly Avg: {vol.get('monthly_average', '?')} | "
                        f"Trend: {vol.get('trend', '?')}\n"
                    )
                    by_type = vol.get("by_type", {})
                    if by_type:
                        context += (
                            f"By Type: Incidents={by_type.get('incident', 0)}, "
                            f"SRs={by_type.get('service_request', 0)}, "
                            f"CRs={by_type.get('change_request', 0)}, "
                            f"Enhancements={by_type.get('enhancement', 0)}\n"
                        )
                for app in app_analysis[:MAX_APPS]:
                    context += (
                        f"- {app.get('application', '?')}: {app.get('ticket_count', 0)} tickets, "
                        f"complexity={app.get('complexity_rating', '?')}, "
                        f"automation_potential={app.get('automation_potential', '?')}\n"
                    )
                if len(app_analysis) > MAX_APPS:
                    self.log(
                        "app_analysis_truncation_warning",
                        {"total": len(app_analysis), "shown": MAX_APPS},
                    )
                    context += f"[WARNING: {len(app_analysis) - MAX_APPS} additional apps truncated]\n"
                if staff:
                    context += f"Estimated FTEs from data: {staff.get('estimated_fte_needed', '?')}\n"

        return context

    async def observe(self) -> Dict[str, Any]:
        rfp_context = self._get_rfp_context()
        client = self.manifest.get("client", {})
        rfp = self.manifest.get("rfp", {})
        products = ", ".join(rfp.get("products", []))
        contract_type = rfp.get("contract_type", "")
        kb_context = await self.get_kb_context(
            f"{contract_type} scope WBS {products} {client.get('industry', '')}",
            collections=["sows", "scope_templates", "rfps"],
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
            kb_section = (
                f"\n{obs['kb_context']}\nUse past scope templates to inform sizing.\n"
            )

        prompt = f"""Analyze this RFP and build a comprehensive scope package.

RULES:
- Structure by platform/product from the RFP
- Size effort based on actual RFP volumes (countries, integrations, users, configurations)
- Include detailed scope descriptions per platform
- For each work package: include deliverables and RFP section references
- Team model must include key responsibilities per role
- CRITICAL: You MUST estimate realistic non-zero values for effort_days, team counts, timeline_months, and transition_weeks based on the RFP complexity. NEVER return 0 for these fields. Use industry benchmarks:
  * AMS per platform: 3-8 FTEs depending on complexity
  * Per 5 integrations: +1 integration specialist
  * Per 10 countries: +1 FTE for localization
  * Governance overhead: SDM (1) + PM (1) + Architect (1)
  * Transition: typically 8-16 weeks for global AMS deals
  * Effort: FTE count x 20 days/month x contract months
- Do NOT hardcode any vendor/product name not in the RFP
- CRITICAL â€” products_in_scope must list ONLY platforms that require a dedicated AM&S team (i.e. platforms the client owns/operates that we will configure, support, and maintain). Do NOT include: integration endpoints or upstream/downstream systems we merely connect to (e.g. SAP, ADP, Workday, Successfactors, GCP, PPDH, PYMW, GV, EMD-12, payroll vendors); SFTP/API/file transport mechanisms; individual module names that are sub-components of a listed platform; or ITSM/governance tooling. Middleware orchestration tools (e.g. Boomi, Workato, MuleSoft) are in scope ONLY if the RFP explicitly assigns their maintenance to the AM&S partner â€” if so, list them but keep them separate from primary platforms in scope_by_platform.
- scope_by_platform must have one entry per distinct platform team required, not one entry per mentioned product name

{obs["rfp_context"]}
{kb_section}

Return JSON:
{{
  "products_in_scope": ["names from RFP"],
  "contract_type": "AMS|Implementation|Hybrid|Advisory|Transformation",
  "contract_months": 0,
  "scope_by_platform": [
    {{
      "platform": "product name",
      "scope_summary": "3-4 sentence description of what is in scope for this platform",
      "work_packages": [
        {{"id": "WP-01", "name": "name", "rfp_ref": "section", "effort_days": 0, "roles": ["role1"], "deliverables": ["deliverable1"], "description": "2-3 sentence description"}}
      ],
      "platform_effort_days": 0,
      "support_activities": ["specific daily/weekly support activities"],
      "compliance_obligations": ["compliance requirements"]
    }}
  ],
  "cross_platform_scope": [
    {{"id": "CP-01", "name": "name", "effort_days": 0, "roles": ["role1"], "deliverables": ["deliverable1"], "description": "what this covers"}}
  ],
  "in_scope": ["specific included items traceable to RFP sections"],
  "out_of_scope": ["explicit exclusions with rationale"],
  "assumptions": [{{"assumption": "what we assume", "impact_if_violated": "what happens if wrong"}}],
  "dependencies": [{{"dependency": "what client must provide", "timing": "when", "impact_if_delayed": "impact"}}],
  "total_effort_days": 0,
  "effort_confidence": "High|Medium|Low",
  "team_model": [
    {{"role": "string", "count": 0, "location": "onshore|offshore|nearshore", "platform": "which product", "key_responsibilities": "what this role does"}}
  ],
  "transition_weeks": 0,
  "transition_phases": ["phase descriptions"],
  "timeline_months": 0
}}"""
        return await self.llm_json(prompt, max_tokens=6000)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and adjust LLM estimates using programmatic guardrails."""
        try:
            return await self._apply_guardrails(orientation)
        except Exception as e:
            self.log("guardrail_error", {"error": str(e)})
            return orientation  # Gracefully fall back to raw LLM output

    async def _apply_guardrails(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Benchmark-driven guardrails.  Fires for ANY under-estimation, not just
        the zero-team edge case.  Benchmarks are contract-type aware:

        AMS       â€” 3 FTEs/platform, 1 per 5 integrations, 1 per 10 countries
        Implementation â€” 6 FTEs/platform, 1 per 3 integrations, 1 per 8 countries
        Hybrid    â€” 5 FTEs/platform, 1 per 4 integrations, 1 per 10 countries
        Advisory / Transformation â€” 2 FTEs/platform, lighter integration load

        Governance roles (SDM, PM, Architect) are billed at 0.5 utilisation
        when computing effort-days, preventing linear inflation.

        Transition duration is sized from actual complexity signals (platforms,
        countries, integrations) rather than a fixed fallback.
        """

        team = orientation.get("team_model", [])
        total_fte = sum(r.get("count", 0) for r in team if isinstance(r, dict))

        intake = self.manifest.get("intake_output", {})
        if not isinstance(intake, dict):
            # Nothing to validate against â€” just run safety floor on timeline/transition
            if (
                not orientation.get("timeline_months")
                or orientation["timeline_months"] == 0
            ):
                orientation["timeline_months"] = (
                    orientation.get("contract_months", 24) or 24
                )
            if (
                not orientation.get("transition_weeks")
                or orientation["transition_weeks"] == 0
            ):
                orientation["transition_weeks"] = 12
            return orientation

        # â”€â”€ 1. EXTRACT COMPLEXITY SIGNALS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ef = intake.get("extracted_fields", intake)
        platforms_data = intake.get("platform_details", [])
        integrations_data = intake.get("integration_inventory", [])
        core_products = self.manifest.get("rfp", {}).get("products", [])

        # â”€â”€ PLATFORM COUNT: three-tier resolution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Tier 1 â€” Trust the LLM's scope_by_platform: it has already read the RFP
        #          and excluded integration endpoints and adjacent systems.
        llm_scoped_platforms = orientation.get("scope_by_platform", [])
        orientation.get("products_in_scope", [])

        # Tier 2 â€” Intake platform_details (populated by the intake agent)
        # Tier 3 â€” Classify raw core_products to strip endpoints/adjacent systems
        if llm_scoped_platforms:
            # LLM produced a platform breakdown â€” use it directly.
            # Split into primary vs middleware for differentiated FTE floors.
            llm_primary, llm_middleware, _ = self._classify_products(
                [
                    p.get("platform", "")
                    for p in llm_scoped_platforms
                    if isinstance(p, dict)
                ]
            )
            num_platforms = max(len(llm_primary), 1)
            num_middleware = len(llm_middleware)
        elif platforms_data:
            # Intake agent already did discovery â€” use that list.
            intake_names = [
                p.get("product_name", "") for p in platforms_data if isinstance(p, dict)
            ]
            pri, mid, _ = self._classify_products(intake_names)
            num_platforms = max(len(pri), 1)
            num_middleware = len(mid)
        else:
            # Last resort: classify the raw product list from the RFP manifest.
            # This is where the old code went wrong â€” applying fte_per_platform
            # to every mentioned product name (incl. endpoints & adjacent systems).
            pri, mid, _ = self._classify_products(core_products)
            num_platforms = max(len(pri), 1)
            num_middleware = len(mid)

        self.log(
            "platform_classification",
            {
                "source": (
                    "llm_scope_by_platform"
                    if llm_scoped_platforms
                    else (
                        "intake_platform_details"
                        if platforms_data
                        else "core_products_classified"
                    )
                ),
                "num_primary_platforms": num_platforms,
                "num_middleware_platforms": num_middleware,
                "raw_product_count": len(core_products),
            },
        )

        num_integrations = (
            len(integrations_data) if isinstance(integrations_data, list) else 0
        )

        num_countries = 0
        total_users = 0
        if isinstance(ef, dict):
            geo = ef.get("geographies", ef.get("client_geography", {}))
            if isinstance(geo, dict):
                geo_val = geo.get("value", [])
            elif isinstance(geo, list):
                geo_val = geo
            else:
                geo_val = []
            num_countries = len(geo_val) if isinstance(geo_val, list) else 0

            # FIX 7: Actually parse and use employee_population for sizing
            emp_raw = ef.get("employee_population", {})
            if isinstance(emp_raw, dict):
                emp_val = emp_raw.get("value", 0)
            elif isinstance(emp_raw, (int, float)):
                emp_val = emp_raw
            else:
                emp_val = 0
            try:
                total_users = (
                    int(str(emp_val).replace(",", "").replace("+", "").strip())
                    if emp_val
                    else 0
                )
            except (ValueError, TypeError):
                total_users = 0

        # â”€â”€ 2. CONTRACT-TYPE-AWARE BENCHMARKS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # FIX 8: Benchmarks are now actually applied per contract type
        contract_type = (
            orientation.get("contract_type")
            or self.manifest.get("rfp", {}).get("contract_type", "AMS")
        ).upper()

        contract_months = (
            orientation.get("contract_months")
            or orientation.get("timeline_months")
            or 24
        )

        if "IMPLEMENTATION" in contract_type:
            fte_per_platform = 6  # design, build, test, cutover, hypercare
            fte_per_middleware = 3  # impl-phase integration build is heavy
            integration_batch = 3  # denser integration work in impl projects
            geo_batch = 8  # regional rollout overhead is higher
            governance_fte = 4  # SDM, PM, Architect, Test Lead all full-time
        elif "HYBRID" in contract_type:
            fte_per_platform = 5  # impl team + ongoing AMS residual
            fte_per_middleware = 2
            integration_batch = 4
            geo_batch = 10
            governance_fte = 4
        elif "ADVISORY" in contract_type or "TRANSFORMATION" in contract_type:
            fte_per_platform = 2  # advisory is lighter on execution FTEs
            fte_per_middleware = 1
            integration_batch = 6
            geo_batch = 12
            governance_fte = 3
        else:  # AMS (default)
            fte_per_platform = 3  # config, L2/L3 support, release management
            fte_per_middleware = 2  # shared integration team per middleware tool
            integration_batch = 5
            geo_batch = 10
            governance_fte = 3

        min_platform_fte = num_platforms * fte_per_platform
        min_middleware_fte = (
            num_middleware * fte_per_middleware
        )  # lighter floor for orchestration tools
        min_integration_fte = (
            math.ceil(num_integrations / integration_batch) if num_integrations else 0
        )
        min_geo_fte = math.ceil(num_countries / geo_batch) if num_countries else 0
        # Volume-driven support: 100K+ = +2, 50Kâ€“99K = +1
        min_user_fte = (
            2 if total_users >= 100_000 else (1 if total_users >= 50_000 else 0)
        )
        min_total_fte = (
            min_platform_fte
            + min_middleware_fte
            + min_integration_fte
            + min_geo_fte
            + min_user_fte
            + governance_fte
        )

        self.log(
            "fte_benchmark_calc",
            {
                "contract_type": contract_type,
                "num_platforms": num_platforms,
                "num_middleware": num_middleware,
                "num_integrations": num_integrations,
                "num_countries": num_countries,
                "total_users": total_users,
                "min_platform_fte": min_platform_fte,
                "min_middleware_fte": min_middleware_fte,
                "min_integration_fte": min_integration_fte,
                "min_geo_fte": min_geo_fte,
                "min_user_fte": min_user_fte,
                "governance_fte": governance_fte,
                "min_total_fte": min_total_fte,
                "llm_total_fte": total_fte,
            },
        )

        # â”€â”€ 3. TEAM CORRECTION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # FIX 9: Guardrail now fires whenever LLM is below benchmark minimum,
        # not only on the zero-team edge case.
        if total_fte < min_total_fte:
            if total_fte == 0:
                # Full rebuild â€” LLM returned nothing usable
                self.log("team_rebuild", {"reason": "LLM returned empty team"})
                # Use LLM's scoped products first; fall back to classified primary platforms
                raw_rebuild_products = (
                    [
                        p.get("platform", "")
                        for p in llm_scoped_platforms
                        if isinstance(p, dict)
                    ]
                    or orientation.get("products_in_scope", [])
                    or core_products
                )
                primary_rebuild, middleware_rebuild, _ = self._classify_products(
                    raw_rebuild_products
                )
                products = (primary_rebuild or raw_rebuild_products)[:10]
                team = []
                for prod in products[:10]:
                    team.append(
                        {
                            "role": f"{prod} - Platform Lead",
                            "count": 1,
                            "location": "offshore",
                            "platform": prod,
                            "key_responsibilities": f"Lead platform delivery and operations for {prod}",
                        }
                    )
                    if "IMPLEMENTATION" in contract_type:
                        team.append(
                            {
                                "role": f"{prod} - Senior Consultant",
                                "count": 2,
                                "location": "offshore",
                                "platform": prod,
                                "key_responsibilities": f"Design, configure, and build {prod} modules",
                            }
                        )
                        team.append(
                            {
                                "role": f"{prod} - Test Engineer",
                                "count": 1,
                                "location": "offshore",
                                "platform": prod,
                                "key_responsibilities": f"Unit, integration, and UAT testing for {prod}",
                            }
                        )
                    else:
                        team.append(
                            {
                                "role": f"{prod} - Functional Consultant",
                                "count": 2,
                                "location": "offshore",
                                "platform": prod,
                                "key_responsibilities": f"Configuration, support, and enhancements for {prod}",
                            }
                        )
                if num_integrations > 0:
                    team.append(
                        {
                            "role": "Integration Specialist",
                            "count": max(1, min_integration_fte),
                            "location": "offshore",
                            "platform": "All",
                            "key_responsibilities": (
                                "API / middleware integration development, monitoring, and L2/L3 support"
                            ),
                        }
                    )
                if min_geo_fte > 0:
                    team.append(
                        {
                            "role": "Regional Support Lead",
                            "count": min_geo_fte,
                            "location": "nearshore",
                            "platform": "All",
                            "key_responsibilities": (
                                "Localization, regional compliance, and multi-timezone support coverage"
                            ),
                        }
                    )
                if min_user_fte > 0:
                    team.append(
                        {
                            "role": "Volume Support Analyst",
                            "count": min_user_fte,
                            "location": "offshore",
                            "platform": "All",
                            "key_responsibilities": (
                                "High-volume ticket triage, L1/L2 support at scale, queue management"
                            ),
                        }
                    )
            else:
                # Selective scale-up â€” LLM produced something but it's too lean.
                # Only scale delivery (offshore/nearshore) roles; governance stays fixed.
                self.log(
                    "team_scale_up",
                    {
                        "from_fte": total_fte,
                        "to_min_fte": min_total_fte,
                        "reason": "LLM estimate below benchmark minimum",
                    },
                )
                scale_factor = min_total_fte / total_fte
                for r in team:
                    if isinstance(r, dict) and r.get("location") != "onshore":
                        r["count"] = max(1, round(r.get("count", 1) * scale_factor))

        # â”€â”€ 4. MANDATORY GOVERNANCE ROLES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        existing_roles = {
            r.get("role", "").lower() for r in team if isinstance(r, dict)
        }
        if not any(
            "delivery manager" in role or "sdm" in role for role in existing_roles
        ):
            team.append(
                {
                    "role": "Service Delivery Manager",
                    "count": 1,
                    "location": "onshore",
                    "platform": "All",
                    "key_responsibilities": (
                        "Overall service delivery, client relationship, SLA governance, escalation management"
                    ),
                }
            )
        if not any("program manager" in role for role in existing_roles):
            team.append(
                {
                    "role": "Program Manager",
                    "count": 1,
                    "location": "nearshore",
                    "platform": "All",
                    "key_responsibilities": (
                        "Program governance, sprint/phase reporting, risk and change management"
                    ),
                }
            )
        if not any(
            "solution architect" in role or "architect" in role
            for role in existing_roles
        ):
            team.append(
                {
                    "role": "Solution Architect",
                    "count": 1,
                    "location": "onshore",
                    "platform": "All",
                    "key_responsibilities": (
                        "Technical design authority, architecture governance, integration oversight"
                    ),
                }
            )
        if not any("test lead" in role or "qa lead" in role for role in existing_roles):
            team.append(
                {
                    "role": "Test Lead",
                    "count": 1,
                    "location": "offshore",
                    "platform": "All",
                    "key_responsibilities": (
                        "Test strategy, regression suite management, UAT coordination"
                    ),
                }
            )

        orientation["team_model"] = team

        # â”€â”€ 5. EFFORT RECALCULATION WITH PARTIAL GOVERNANCE UTILISATION â”€â”€â”€â”€â”€â”€
        # FIX 10: Governance roles are partially billable (0.5 utilisation).
        # This prevents linear inflation when governance roles are injected.
        GOVERNANCE_KEYWORDS = {
            "delivery manager",
            "sdm",
            "program manager",
            "solution architect",
            "architect",
        }
        GOVERNANCE_UTIL_RATE = 0.5  # governance roles average 50% chargeable time

        delivery_fte_sum = 0
        governance_fte_sum = 0.0
        for r in team:
            if not isinstance(r, dict):
                continue
            role_lower = r.get("role", "").lower()
            count = r.get("count", 0)
            if any(kw in role_lower for kw in GOVERNANCE_KEYWORDS):
                governance_fte_sum += count * GOVERNANCE_UTIL_RATE
            else:
                delivery_fte_sum += count

        billable_fte = delivery_fte_sum + governance_fte_sum
        orientation["total_effort_days"] = round(billable_fte * 20 * contract_months)

        # â”€â”€ 6. TRANSITION DURATION â€” COMPLEXITY-SIZED â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # FIX 11: Transition is sized from actual deal complexity,
        # not a single fallback value of 12.
        if (
            not orientation.get("transition_weeks")
            or orientation["transition_weeks"] == 0
        ):
            is_large = (
                num_platforms >= 5 or num_countries >= 10 or num_integrations >= 10
            )
            is_medium = (
                num_platforms >= 3 or num_countries >= 5 or num_integrations >= 5
            )
            if "IMPLEMENTATION" in contract_type:
                orientation["transition_weeks"] = (
                    20 if is_large else (16 if is_medium else 12)
                )
            elif "HYBRID" in contract_type:
                orientation["transition_weeks"] = (
                    16 if is_large else (12 if is_medium else 10)
                )
            else:  # AMS / Advisory
                orientation["transition_weeks"] = (
                    16 if is_large else (12 if is_medium else 8)
                )

        # â”€â”€ 7. TIMELINE SAFETY FLOOR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if (
            not orientation.get("timeline_months")
            or orientation["timeline_months"] == 0
        ):
            orientation["timeline_months"] = contract_months

        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        platforms = decision.get("scope_by_platform", [])
        team = decision.get("team_model", [])
        total_fte = sum(r.get("count", 0) for r in team if isinstance(r, dict))
        total_effort = decision.get("total_effort_days", 0)
        products = decision.get("products_in_scope", [])
        wp_count = sum(len(p.get("work_packages", [])) for p in platforms)
        onshore = sum(
            r.get("count", 0)
            for r in team
            if isinstance(r, dict) and r.get("location") == "onshore"
        )
        offshore = sum(
            r.get("count", 0)
            for r in team
            if isinstance(r, dict) and r.get("location") == "offshore"
        )

        plat_summary = " | ".join(
            [
                f"{p.get('platform', '?')}: {p.get('platform_effort_days', 0)}d, {len(p.get('work_packages', []))} WPs"
                for p in platforms
            ]
        )

        prompt = f"""Write a scope of services narrative for a SOW document.

STYLE: No markdown. No bullets. No asterisks. Professional flowing paragraphs. Client-ready.

DATA:
Products: {", ".join(products)} | Contract: {decision.get("contract_type", "Unknown")}
Platforms: {plat_summary}
Effort: {total_effort} days | {wp_count} work packages
Team: {total_fte} FTEs ({onshore} onshore, {offshore} offshore)
Timeline: {decision.get("timeline_months", 0)} months | Transition: {decision.get("transition_weeks", 0)} weeks

Write exactly 3 paragraphs (3-4 sentences each). Complete every sentence:
1. What will be delivered â€” products, effort, contract timeline, scale.
2. Team model â€” FTE counts by location, key roles, transition approach.
3. Scope boundaries â€” in-scope vs out-of-scope, assumptions, dependencies.

Do NOT stop mid-sentence. Complete all 3 paragraphs."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"Scope: {', '.join(products)}. "
        summary += (
            f"{wp_count} work packages, {total_effort} effort-days, {total_fte} FTEs. "
        )
        summary += f"Timeline: {decision.get('timeline_months', 0)} months. "
        summary += f"Confidence: {decision.get('effort_confidence', 'Medium')}."

        return {
            "scope_package": decision,
            "narrative": narrative,
            "hitl_summary": summary,
        }
