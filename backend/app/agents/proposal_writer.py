"""
Proposal Writer Agent â€” L9-grade executive proposal generator.
Consumes ALL upstream agent structured data (team models, cost breakdowns,
automation savings, transition plans, work packages) and produces a complete,
copy-paste ready, client-facing RFP response document.

Uses multiple focused LLM calls to ensure each section gets full depth.
Zero hardcoded values â€” everything derived from the pipeline.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


def _fmt_usd(val) -> str:
    """Format a number as USD currency."""
    try:
        n = float(val)
        if n >= 1_000_000:
            return f"${n / 1_000_000:,.2f}M"
        elif n >= 1_000:
            return f"${n:,.0f}"
        else:
            return f"${n:,.0f}"
    except (TypeError, ValueError):
        return str(val) if val else "$0"


def _deep_text(obj, depth=0) -> str:
    """Recursively extract text from nested LLM output (dicts, lists, strings).

    Handles cases where the LLM returns structured JSON like:
    {"content": {"products_in_scope": "...", "work_breakdown_structure": {"table": "..."}}}
    and flattens it into clean markdown text.
    """
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, list):
        parts = []
        for item in obj:
            text = _deep_text(item, depth)
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    if isinstance(obj, dict):
        # If dict has a single 'content' key, unwrap it
        if len(obj) == 1 and "content" in obj:
            return _deep_text(obj["content"], depth)
        # If dict has a 'table' key, extract it
        if "table" in obj:
            parts = []
            for k, v in obj.items():
                parts.append(_deep_text(v, depth))
            return "\n\n".join(p for p in parts if p)
        # Otherwise assemble each key as a subsection
        parts = []
        for key, val in obj.items():
            text = _deep_text(val, depth + 1)
            if text:
                # Convert snake_case keys to Title Case headers
                header = key.replace("_", " ").title()
                # Only add header if the text doesn't already start with a markdown header
                if text.lstrip().startswith("#") or text.lstrip().startswith("|"):
                    parts.append(text)
                else:
                    hashes = "#" * min(depth + 3, 5)
                    parts.append(f"{hashes} {header}\n\n{text}")
        return "\n\n".join(parts)
    return str(obj)


def _extract_structured_data(manifest: dict) -> dict:
    """Extract all structured data from upstream agents into a clean dict."""
    data = {}

    # Client
    data["client"] = manifest.get("client", {})
    data["rfp"] = manifest.get("rfp", {})

    # Intake
    intake = manifest.get("intake_output", {})
    if isinstance(intake, dict):
        data["platforms"] = intake.get("platform_details", [])
        data["integrations"] = intake.get("integration_inventory", [])
        data["slas"] = intake.get("kpi_sla_table", [])
        ef = intake.get("extracted_fields", {})
        if isinstance(ef, dict):
            data["contract_type"] = (
                ef.get("contract_type", {}).get("value", "")
                if isinstance(ef.get("contract_type"), dict)
                else str(ef.get("contract_type", ""))
            )
            emp = ef.get("employee_population", {})
            data["employee_count"] = (
                emp.get("value", 0) if isinstance(emp, dict) else emp
            )

    # Scope
    scope = manifest.get("scope_output", {})
    if isinstance(scope, dict):
        sp = scope.get("scope_package", scope)
        if isinstance(sp, dict):
            data["products"] = sp.get("products_in_scope", [])
            data["contract_months"] = sp.get("contract_months", 0)
            data["transition_weeks"] = sp.get("transition_weeks", 0)
            data["team_model"] = sp.get("team_model", [])
            data["work_packages"] = sp.get("work_packages", [])
            data["total_effort_days"] = sp.get("total_effort_days", 0)
            # Scope boundaries for detailed scope section
            data["in_scope"] = sp.get("in_scope", [])
            data["out_of_scope"] = sp.get("out_of_scope", [])
            data["assumptions"] = sp.get("assumptions", [])
            data["dependencies"] = sp.get("dependencies", [])
            data["scope_by_platform"] = sp.get("scope_by_platform", [])

    # Solution â€” including security/compliance and tooling strategy
    solution = manifest.get("solution_output", {})
    if isinstance(solution, dict):
        data["platform_architectures"] = solution.get("platform_architectures", [])
        data["integration_architecture"] = solution.get("integration_architecture", {})
        data["environment_strategy"] = solution.get("environment_strategy", {})
        data["operating_model"] = solution.get("operating_model", {})
        data["solution_narrative"] = solution.get("narrative", "")
        data["security_compliance"] = solution.get("security_compliance", [])
        data["tooling_strategy"] = solution.get("tooling_strategy", [])
        data["architecture_complexity"] = solution.get(
            "architecture_complexity", "standard"
        )

    # Automation â€” including architecture-level outputs
    automation = manifest.get("automation_ai_output", {})
    if isinstance(automation, dict):
        data["automation_sections"] = automation.get("platform_sections", [])
        data["cross_platform_automations"] = automation.get("cross_platform", [])
        data["total_automation_opportunities"] = automation.get(
            "total_opportunities", 0
        )
        data["priority_breakdown"] = automation.get("priority_breakdown", {})
        # Client context from automation agent
        auto_ctx = automation.get("client_context", {})
        if isinstance(auto_ctx, dict):
            data["rfp_automation_refs"] = auto_ctx.get("rfp_automation_refs", [])

    # Transition â€” including wave rollout and full governance with milestones
    transition = manifest.get("transition_change_output", {})
    if isinstance(transition, dict):
        data["transition_plan"] = transition.get("transition_plan", {})
        data["change_management"] = transition.get("change_management", {})
        data["governance_model"] = transition.get("governance_model", {})
        data["transition_risks"] = transition.get("transition_risks", [])
        data["wave_rollout"] = transition.get("wave_rollout", [])

    # Commercial â€” including scenarios, margin guardrails, resource loading
    commercial = manifest.get("commercial_output", {})
    if isinstance(commercial, dict):
        data["pl_model"] = commercial.get("pl_model", {})
        data["cost_breakdown"] = commercial.get("cost_breakdown_detail", {})
        data["automation_yoy"] = commercial.get("automation_yoy", [])
        data["automation_breakdown"] = commercial.get(
            "automation_opportunity_breakdown", []
        )
        data["resources"] = commercial.get("resources", [])
        data["scenarios"] = commercial.get("scenarios", {})
        data["margin_guardrail"] = commercial.get("margin_guardrail", {})
        data["resource_loading"] = commercial.get("resource_loading", {})
        data["contract_params"] = commercial.get("contract_params", {})
        data["commercial_risks"] = commercial.get("commercial_risks", [])
        data["efficiency_targets"] = commercial.get("efficiency_targets", [])

    # Compliance â€” FULL extraction including SLA risks, penalties, data protection, IP, exit
    compliance = manifest.get("compliance_output", {})
    if isinstance(compliance, dict):
        data["compliance_narrative"] = compliance.get("narrative", "")
        # The risk_register from compliance is a nested dict containing multiple risk categories
        rr = compliance.get("risk_register", {})
        if isinstance(rr, dict):
            data["risk_register"] = rr
            data["contractual_risks"] = rr.get("contractual_risks", [])
            data["sla_risks"] = rr.get("sla_risks", [])
            data["penalty_exposure"] = rr.get("penalty_exposure", [])
            data["overall_risk_rating"] = rr.get("overall_risk_rating", "medium")
            data["showstoppers"] = rr.get("showstoppers", [])
            data["negotiation_summary"] = rr.get("negotiation_summary", {})
            data["data_protection"] = rr.get("data_protection", [])
            data["insurance_indemnity"] = rr.get("insurance_indemnity", {})
            data["ip_data_rights"] = rr.get("ip_data_rights", {})
            data["exit_transition"] = rr.get("exit_transition", {})
        elif isinstance(rr, list):
            data["risk_register"] = rr

    # Competitive Intelligence â€” competitors, win themes, differentiators
    competitive = manifest.get("competitive_output", {})
    if isinstance(competitive, dict):
        cl = competitive.get("competitive_landscape", competitive)
        if isinstance(cl, dict):
            data["competitors"] = cl.get("competitors", [])
            data["win_themes"] = cl.get("win_themes", [])
            data["differentiators"] = cl.get("differentiators", [])
            data["vulnerabilities"] = cl.get("vulnerabilities", [])
            data["incumbent"] = cl.get("incumbent", {})
            data["pricing_strategy"] = cl.get("pricing_strategy", {})
        data["competitive_narrative"] = competitive.get("narrative", "")

    # Client Intelligence (if available)
    client_intel = manifest.get("client_intelligence_output", {})
    if isinstance(client_intel, dict):
        data["client_intelligence"] = client_intel

    # â”€â”€ Contract months floor guard â”€â”€
    # Ensure contract_months is never 0 â€” pull from commercial if scope is missing
    cm = data.get("contract_months", 0)
    if not cm or (isinstance(cm, (int, float)) and cm < 6):
        # Try commercial model
        pl = data.get("pl_model", {})
        if isinstance(pl, dict):
            rev = pl.get("revenue", {})
            if isinstance(rev, dict):
                cm = rev.get("contract_months", 0) or rev.get("contract_term_months", 0)
        # If still 0, default to 24 for enterprise deals
        if not cm or (isinstance(cm, (int, float)) and cm < 6):
            cm = 24
        data["contract_months"] = cm

    return data


def _build_data_summary(data: dict) -> str:
    """Build a concise but comprehensive summary of all structured data for LLM consumption."""
    lines = []

    client = data.get("client", {})
    lines.append(
        f"CLIENT: {client.get('name', 'Unknown')} | Industry: {client.get('industry', 'Unknown')}"
    )
    lines.append(f"CONTRACT TYPE: {data.get('contract_type', 'Unknown')}")
    lines.append(f"EMPLOYEE POPULATION: {data.get('employee_count', 'Unknown')}")

    products = data.get("products", [])
    if products:
        lines.append(f"PRODUCTS IN SCOPE: {', '.join(products)}")

    lines.append(f"CONTRACT DURATION: {data.get('contract_months', '?')} months")
    lines.append(f"TRANSITION: {data.get('transition_weeks', '?')} weeks")
    lines.append(f"TOTAL EFFORT: {data.get('total_effort_days', '?')} days")

    # Team
    team = data.get("team_model", [])
    if team:
        total_fte = sum(r.get("count", 0) for r in team if isinstance(r, dict))
        lines.append(f"\nTEAM MODEL ({total_fte} FTEs):")
        for r in team[:15]:
            if isinstance(r, dict):
                lines.append(
                    f"  {r.get('role', '?')}: {r.get('count', 1)} FTEs ({r.get('location', 'offshore')})"
                )

    # Work packages
    wps = data.get("work_packages", [])
    if wps:
        lines.append(f"\nWORK PACKAGES ({len(wps)}):")
        for wp in wps[:20]:
            if isinstance(wp, dict):
                lines.append(
                    f"  {wp.get('name', '?')}: {wp.get('effort_days', '?')} days"
                )

    # Scope boundaries
    in_scope = data.get("in_scope", [])
    out_of_scope = data.get("out_of_scope", [])
    if in_scope or out_of_scope:
        lines.append("\nSCOPE BOUNDARIES:")
        if in_scope:
            lines.append(f"  IN SCOPE: {'; '.join(str(s) for s in in_scope[:10])}")
        if out_of_scope:
            lines.append(
                f"  OUT OF SCOPE: {'; '.join(str(s) for s in out_of_scope[:10])}"
            )
    assumptions = data.get("assumptions", [])
    if assumptions:
        lines.append(f"  ASSUMPTIONS: {'; '.join(str(a) for a in assumptions[:8])}")
    dependencies = data.get("dependencies", [])
    if dependencies:
        lines.append(f"  DEPENDENCIES: {'; '.join(str(d) for d in dependencies[:8])}")

    # Platforms
    platforms = data.get("platforms", [])
    if platforms:
        lines.append(f"\nPLATFORMS ({len(platforms)}):")
        for p in platforms[:8]:
            if isinstance(p, dict):
                lines.append(
                    f"  {p.get('product_name', '?')}: {p.get('description', '')}"
                )

    # Integrations
    integrations = data.get("integrations", [])
    if integrations:
        lines.append(f"\nINTEGRATIONS ({len(integrations)}):")
        for i in integrations[:10]:
            if isinstance(i, dict):
                lines.append(
                    f"  {i.get('source', '?')} â†’ {i.get('target', '?')} ({i.get('middleware', '')})"
                )

    # Transition phases
    tp = data.get("transition_plan", {})
    if isinstance(tp, dict) and tp.get("phases"):
        lines.append(
            f"\nTRANSITION ({tp.get('total_duration_weeks', '?')} weeks, {len(tp['phases'])} phases):"
        )
        for phase in tp["phases"][:6]:
            if isinstance(phase, dict):
                lines.append(
                    f"  Phase {phase.get('phase_number', '?')}: {phase.get('phase_name', '?')} (Wk {phase.get('start_week', '?')}-{phase.get('end_week', '?')})"
                )
        kt = tp.get("knowledge_transfer", {})
        if isinstance(kt, dict):
            lines.append(
                f"  KT: {kt.get('kt_waves', '?')} waves, {kt.get('shadow_period_weeks', '?')}w shadow"
            )
        pr = tp.get("parallel_run", {})
        if isinstance(pr, dict):
            lines.append(f"  Parallel Run: {pr.get('duration_weeks', '?')} weeks")
            go_live = pr.get("go_live_criteria", [])
            if go_live:
                lines.append(
                    f"  Go-Live Criteria: {'; '.join(str(c) for c in go_live[:5])}"
                )
        cutover = tp.get("cutover_plan", {})
        if isinstance(cutover, dict) and cutover.get("approach"):
            lines.append(
                f"  Cutover: {cutover.get('approach', '?')} | Rollback: {cutover.get('rollback_plan', 'N/A')}"
            )

    # Wave rollout
    waves = data.get("wave_rollout", [])
    if waves:
        lines.append(f"\nWAVE ROLLOUT ({len(waves)} waves):")
        for w in waves[:6]:
            if isinstance(w, dict):
                lines.append(
                    f"  Wave {w.get('wave', '?')}: {w.get('scope', '?')} (Wk {w.get('start_week', '?')}-{w.get('end_week', '?')})"
                )

    # Governance milestones
    gov = data.get("governance_model", {})
    if isinstance(gov, dict):
        milestones = gov.get("milestone_checkpoints", [])
        if milestones:
            lines.append(f"\nMILESTONE CHECKPOINTS ({len(milestones)}):")
            for m in milestones[:6]:
                if isinstance(m, dict):
                    lines.append(
                        f"  {m.get('milestone', '?')} (Wk {m.get('target_week', '?')}) {'[GO/NO-GO]' if m.get('go_no_go') else ''}"
                    )
        raci = gov.get("raci_matrix", [])
        if raci:
            lines.append(f"  RACI: {len(raci)} activities defined")
        esc = gov.get("escalation_matrix", [])
        if esc:
            lines.append(f"  Escalation Levels: {len(esc)}")
        sc = gov.get("steering_committee", {})
        if isinstance(sc, dict) and sc.get("frequency"):
            lines.append(f"  Steering Committee: {sc.get('frequency', '?')}")

    # Change management â€” enriched with details
    cm = data.get("change_management", {})
    if isinstance(cm, dict):
        lines.append("\nCHANGE MANAGEMENT:")
        stakeholders = cm.get("stakeholder_groups", [])
        lines.append(f"  Stakeholder Groups: {len(stakeholders)}")
        for sg in stakeholders[:5]:
            if isinstance(sg, dict):
                lines.append(
                    f"    - {sg.get('group', '?')}: impact={sg.get('impact_level', '?')}, readiness={sg.get('change_readiness', '?')}"
                )
        training = cm.get("training_plan", [])
        lines.append(f"  Training Programs: {len(training)}")
        for t in training[:5]:
            if isinstance(t, dict):
                lines.append(
                    f"    - {t.get('training_topic', '?')}: {t.get('target_audience', '?')} ({t.get('delivery_method', '?')}, {t.get('duration', '?')})"
                )
        comms = cm.get("communication_plan", [])
        lines.append(f"  Communication Channels: {len(comms)}")
        success = cm.get("success_metrics", [])
        if success:
            lines.append(f"  Success Metrics: {len(success)}")
            for s in success[:4]:
                if isinstance(s, dict):
                    lines.append(
                        f"    - {s.get('metric', '?')}: target={s.get('target', '?')}"
                    )

    # Automation
    auto_sections = data.get("automation_sections", [])
    if auto_sections:
        total_opps = sum(
            len(s.get("opportunities", []))
            for s in auto_sections
            if isinstance(s, dict)
        )
        lines.append(f"\nAUTOMATION ({total_opps} opportunities):")
        for section in auto_sections[:5]:
            if isinstance(section, dict):
                lines.append(f"  Platform: {section.get('platform', '?')}")
                for opp in section.get("opportunities", [])[:5]:
                    if isinstance(opp, dict):
                        lines.append(
                            f"    [{opp.get('priority', 'MED')}] {opp.get('title', '?')}: FTE={opp.get('estimated_fte_reduction', '?')}, effort={opp.get('effort', '?')}, horizon={opp.get('horizon', '?')}"
                        )

    # Cross-platform automations
    cross_auto = data.get("cross_platform_automations", [])
    if cross_auto:
        lines.append(f"\nCROSS-PLATFORM AUTOMATIONS ({len(cross_auto)}):")
        for ca in cross_auto[:5]:
            if isinstance(ca, dict):
                lines.append(
                    f"  [{ca.get('priority', 'MED')}] {ca.get('title', '?')}: FTE={ca.get('estimated_fte_reduction', '?')}, platforms={ca.get('platforms', [])}"
                )

    # Commercial
    pl = data.get("pl_model", {})
    if isinstance(pl, dict):
        rev = pl.get("revenue", {})
        costs = pl.get("costs", {})
        profit = pl.get("profitability", {})
        lines.append("\nCOMMERCIAL:")
        if isinstance(rev, dict):
            lines.append(f"  TCV: {_fmt_usd(rev.get('total_contract_value', 0))}")
            lines.append(f"  Annual: {_fmt_usd(rev.get('annual_revenue', 0))}")
            lines.append(f"  Monthly: {_fmt_usd(rev.get('monthly_price', 0))}")
        if isinstance(costs, dict):
            lines.append(f"  COGS: {_fmt_usd(costs.get('total_cogs', 0))}")
            lines.append(
                f"  Direct Delivery: {_fmt_usd(costs.get('direct_delivery', 0))}"
            )
            lines.append(f"  Transition: {_fmt_usd(costs.get('transition', 0))}")
        if isinstance(profit, dict):
            lines.append(f"  Margin: {profit.get('margin_percent', 0)}%")

    cbd = data.get("cost_breakdown", {})
    if isinstance(cbd, dict) and any(cbd.values()):
        lines.append(f"  Transition Cost: {_fmt_usd(cbd.get('transition_cost', 0))}")
        lines.append(f"  Change Mgmt: {_fmt_usd(cbd.get('change_management_cost', 0))}")
        lines.append(f"  Tools/Infra: {_fmt_usd(cbd.get('tools_monthly', 0))}/mo")
        lines.append(f"  Travel: {_fmt_usd(cbd.get('travel_annual', 0))}/yr")

    # Commercial scenarios
    scenarios = data.get("scenarios", {})
    if isinstance(scenarios, dict) and scenarios:
        comp = scenarios.get("comparison", scenarios)
        if isinstance(comp, dict) and comp:
            lines.append("\nCOMMERCIAL SCENARIOS:")
            if comp.get("base_tcv"):
                lines.append(
                    f"  Base: TCV={_fmt_usd(comp.get('base_tcv', 0))}, Margin={comp.get('base_margin', 0)}%"
                )
            if comp.get("aggressive_tcv"):
                lines.append(
                    f"  Aggressive: TCV={_fmt_usd(comp.get('aggressive_tcv', 0))}, Margin={comp.get('aggressive_margin', 0)}%"
                )
            if comp.get("conservative_tcv"):
                lines.append(
                    f"  Conservative: TCV={_fmt_usd(comp.get('conservative_tcv', 0))}, Margin={comp.get('conservative_margin', 0)}%"
                )

    # Margin guardrail
    guardrail = data.get("margin_guardrail", {})
    if isinstance(guardrail, dict) and guardrail.get("status"):
        lines.append(
            f"  Margin Status: {guardrail.get('status', '?')} â€” {guardrail.get('message', '')}"
        )

    auto_yoy = data.get("automation_yoy", [])
    if auto_yoy:
        lines.append("\nYOY SAVINGS:")
        for y in auto_yoy:
            if isinstance(y, dict):
                lines.append(
                    f"  Y{y.get('year')}: {_fmt_usd(y.get('automation_savings', 0))} ({y.get('realization_pct', 0)}%)"
                )

    auto_bd = data.get("automation_breakdown", [])
    if auto_bd:
        lines.append(f"\nPER-AUTOMATION SAVINGS ({len(auto_bd)}):")
        for item in auto_bd[:15]:
            if isinstance(item, dict):
                lines.append(
                    f"  {item.get('title', '?')}: {_fmt_usd(item.get('annual_saving_usd', 0))}/yr ({item.get('estimated_fte_reduction', 0)} FTE)"
                )

    # â”€â”€ COMPETITIVE INTELLIGENCE (from competitive agent) â”€â”€
    competitors = data.get("competitors", [])
    if competitors:
        lines.append(f"\nCOMPETITIVE LANDSCAPE ({len(competitors)} competitors):")
        for c in competitors[:6]:
            if isinstance(c, dict):
                lines.append(
                    f"  {c.get('name', '?')}: threat={c.get('threat', '?')}, strength={c.get('strength', '')}, counter={c.get('counter', '')}"
                )
    incumbent = data.get("incumbent", {})
    if isinstance(incumbent, dict) and incumbent.get("name"):
        lines.append(
            f"  Incumbent: {incumbent.get('name', 'Unknown')} (switching cost: {incumbent.get('switching_cost', '?')})"
        )
    win_themes = data.get("win_themes", [])
    if win_themes:
        lines.append(f"\nWIN THEMES ({len(win_themes)}):")
        for wt in win_themes[:5]:
            if isinstance(wt, dict):
                lines.append(
                    f"  - {wt.get('theme', '?')} â†’ differentiator: {wt.get('differentiator', '')}"
                )
    differentiators = data.get("differentiators", [])
    if differentiators:
        lines.append(f"\nBIDDER DIFFERENTIATORS ({len(differentiators)}):")
        for d in differentiators[:5]:
            if isinstance(d, dict):
                lines.append(
                    f"  - {d.get('what', '?')}: addresses {d.get('rfp_req', '?')}, unique because {d.get('why_unique', '')}"
                )
    pricing_strategy = data.get("pricing_strategy", {})
    if isinstance(pricing_strategy, dict) and pricing_strategy.get("positioning"):
        lines.append(
            f"  Pricing Position: {pricing_strategy.get('positioning', '?')} â€” {pricing_strategy.get('approach', '')}"
        )

    # â”€â”€ COMPLIANCE & RISK (from compliance agent) â”€â”€
    contractual_risks = data.get("contractual_risks", [])
    if contractual_risks:
        lines.append(f"\nCONTRACTUAL RISKS ({len(contractual_risks)}):")
        for cr in contractual_risks[:6]:
            if isinstance(cr, dict):
                lines.append(
                    f"  [{cr.get('risk_level', '?')}] {cr.get('clause', '?')}: {cr.get('description', '')} | negotiate={cr.get('negotiation_priority', '?')}"
                )
    sla_risks = data.get("sla_risks", [])
    if sla_risks:
        lines.append(f"\nSLA RISKS ({len(sla_risks)}):")
        for sr in sla_risks[:5]:
            if isinstance(sr, dict):
                lines.append(
                    f"  {sr.get('sla', '?')}: target={sr.get('target', '?')}, feasibility={sr.get('feasibility', '?')}, action={sr.get('recommendation', '?')}"
                )
    penalty_exposure = data.get("penalty_exposure", [])
    if penalty_exposure:
        lines.append(f"\nPENALTY EXPOSURE ({len(penalty_exposure)}):")
        for pe in penalty_exposure[:5]:
            if isinstance(pe, dict):
                lines.append(
                    f"  {pe.get('penalty_type', '?')}: exposure={pe.get('exposure_level', '?')}, cap={pe.get('cap_analysis', '?')}"
                )
    neg_summary = data.get("negotiation_summary", {})
    if isinstance(neg_summary, dict) and neg_summary.get("total_clauses_reviewed"):
        lines.append(
            f"\nNEGOTIATION SUMMARY: {neg_summary.get('must_negotiate', 0)} must-negotiate, {neg_summary.get('should_negotiate', 0)} should-negotiate, {neg_summary.get('acceptable', 0)} acceptable"
        )
    data_prot = data.get("data_protection", [])
    if data_prot:
        lines.append(f"\nDATA PROTECTION ({len(data_prot)} jurisdictions):")
        for dp in data_prot[:5]:
            if isinstance(dp, dict):
                lines.append(
                    f"  {dp.get('jurisdiction', '?')}: {dp.get('regulation', '?')}, status={dp.get('compliance_status', '?')}"
                )
    ip_rights = data.get("ip_data_rights", {})
    if isinstance(ip_rights, dict) and ip_rights.get("ip_ownership"):
        lines.append(
            f"\nIP & DATA RIGHTS: ownership={ip_rights.get('ip_ownership', '?')}, handling={ip_rights.get('data_handling', '?')}"
        )
    exit_trans = data.get("exit_transition", {})
    if isinstance(exit_trans, dict) and exit_trans.get("exit_obligations"):
        lines.append(
            f"EXIT: assistance={exit_trans.get('transition_assistance_period', '?')}"
        )
    overall_risk = data.get("overall_risk_rating", "")
    if overall_risk:
        lines.append(f"OVERALL RISK RATING: {overall_risk.upper()}")
    showstoppers = data.get("showstoppers", [])
    if showstoppers:
        lines.append(f"SHOWSTOPPERS: {'; '.join(str(s) for s in showstoppers[:3])}")

    # Transition risks
    transition_risks = data.get("transition_risks", [])
    if transition_risks:
        lines.append(f"\nTRANSITION RISKS ({len(transition_risks)}):")
        for tr in transition_risks[:6]:
            if isinstance(tr, dict):
                lines.append(
                    f"  [{tr.get('likelihood', '?')}/{tr.get('impact', '?')}] {tr.get('risk', '?')}: mitigation={tr.get('mitigation', '?')}"
                )

    # Security & compliance from solution agent
    sec = data.get("security_compliance", [])
    if sec:
        lines.append(f"\nSECURITY & COMPLIANCE: {'; '.join(str(s) for s in sec[:6])}")

    return "\n".join(lines)


class ProposalWriterAgent(BaseAgent):
    name = "Proposal Writer Agent"
    agent_tier = (
        "critical"  # Client reads this — best writing quality = higher win probability
    )

    async def observe(self) -> Dict[str, Any]:
        client = self.manifest.get("client", {})
        rfp = self.manifest.get("rfp", {})
        user_ctx = self.manifest.get("user_context", {})

        # Extract ALL structured data from upstream agents
        structured = _extract_structured_data(self.manifest)
        data_summary = _build_data_summary(structured)

        products = ", ".join(rfp.get("products", []))
        industry = client.get("industry", "")

        kb_context = await self.get_kb_context(
            f"proposal writing executive summary methodology {products} {industry}",
            collections=["sows", "rfps", "win_loss_data"],
        )

        return {
            "client": client,
            "rfp": rfp,
            "user_ctx": user_ctx,
            "structured": structured,
            "data_summary": data_summary,
            "products": products,
            "industry": industry,
            "kb_context": kb_context,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate proposal via 3 focused LLM calls for maximum quality per section."""
        user_notes = ""
        uc = obs.get("user_ctx", {})
        if uc.get("additional_context"):
            user_notes = f"\nUSER STRATEGIC NOTES: {uc['additional_context']}\n"

        client_name = obs["client"].get("name", "the Client")
        data_summary = obs["data_summary"]

        preamble = f"""You are a Tier-1 Executive Proposal Architect producing an L9-grade RFP response for {client_name}.
This is a multi-million dollar engagement. Every section must be deeply detailed, data-rich, and client-ready.

ENGAGEMENT TYPE DETECTION: Analyze the CONTRACT TYPE, scope, team model, and transition data below
to determine the engagement type (AMS, Implementation, Advisory, Transformation, Hybrid, or other).
Adapt your language, section depth, and terminology to match. For AMS: emphasize steady-state operations,
SLAs, and continuous improvement. For Implementation: emphasize delivery phases, go-live criteria, and
cutover planning. For Advisory: emphasize strategic recommendations and roadmaps. For Hybrid: blend
both operational and project delivery language. NEVER assume a specific engagement type â€” infer it.

CRITICAL RULES:
1. USE THE EXACT numbers from the data below. NEVER invent figures.
2. USE RICH MARKDOWN: ## headers, ### sub-headers, **bold**, bullet points (- ), markdown tables (| col | col |).
3. Each section MUST be 500-800 words. Short sections = FAILURE. If a subsection is only 1-2 sentences, EXPAND it.
4. ALL monetary amounts in US Dollars ($).
5. Include specific role names, FTE counts, platform names, phase durations from the data.
6. Tables MUST use proper markdown: | Header | Header |\\n|---|---|\\n| data | data |
7. Write in formal consulting language. No fluff. Every sentence adds value.
8. EVERY subsection (### heading) must have AT LEAST one full paragraph (3+ sentences) of narrative PLUS supporting details.
9. Never write a one-sentence subsection. If a subsection has only 1 sentence, you FAILED.
10. NEVER hardcode domain names, technology products, or industry terms beyond what appears in the data.
    Reference "the client's platforms" or use the exact names from the PRODUCTS IN SCOPE and PLATFORMS data.
11. This proposal must work for ANY industry, ANY technology stack, ANY engagement model. Be adaptive.
{user_notes}

=== STRUCTURED DATA FROM ALL UPSTREAM AGENTS ===
{data_summary}
"""

        # â”€â”€ CALL 1: Executive Summary + Scope + Solution Design â”€â”€
        prompt1 = (
            preamble
            + """

Generate these 3 sections as JSON:
{
  "executive_summary": "5 commanding paragraphs with rich detail. Para 1 (Client Context & Engagement Vision): Deep understanding of the client's business context, industry challenges, workforce scale, and why this engagement matters strategically. Reference the employee population, number of platforms, and operational complexity. Para 2 (Proposed Solution Approach): Name EVERY platform in scope, describe the unified operating model, integration strategy (which interfaces are active vs. planned), and architecture approach. Mention environment strategy and monitoring approach. Para 3 (Team Model & Delivery Structure): Exact FTE count, onshore/offshore/nearshore split with numbers, follow-the-sun coverage model, key roles (name them). Include a markdown summary table: | Role | FTE Count | Location |. Para 4 (Commercial Overview): TCV, annual run rate, monthly cost, contract term, transition cost, COGS, margin percentage. Reference automation savings potential. Para 5 (Why Us): Use the WIN THEMES and DIFFERENTIATORS from the competitive intelligence data. Reference specific bidder strengths that counter competitor threats. Mention partnership model, automation-first approach, and proven expertise with the specific platforms in scope.",

  "scope_of_services": "Comprehensive scope section: ### Products in Scope (for EACH platform, write a FULL paragraph â€” at least 5 sentences â€” describing: what modules are in scope, what daily operational activities we will perform, configuration management approach, user access governance, compliance obligations, reporting and analytics responsibilities, and incident resolution approach for that platform). ### Work Breakdown Structure (markdown table: | # | Work Package | Effort (Days) | Description | â€” use the EXACT work packages and effort days from the data, with 1-2 sentence description per WP explaining what it covers). ### Service Scope Boundaries (INCLUDED: full paragraph listing all included activities from the IN SCOPE data â€” operational support, technical support, functional support, incident resolution, change management, release coordination, reporting, integration monitoring, user support, compliance, automation, knowledge management, continuous improvement. EXCLUDED: separate full paragraph listing all EXCLUDED items from the OUT OF SCOPE data with rationale for each exclusion â€” why it's excluded and how it prevents scope creep while allowing flexibility). ### Key Assumptions & Dependencies (bullet list with 5+ items from the ASSUMPTIONS and DEPENDENCIES data, each a full sentence explaining the assumption and its impact if violated). ### Service Level Framework (paragraph on SLA targets per tier with specific response/resolution times, measurement methodology using service management platform, automated ticketing, monthly SLA reports, reporting cadence including weekly operational reviews and quarterly business reviews).",

  "solution_design": "Deeply detailed technical section â€” architects will scrutinize this. ### Platform Architecture (for EACH platform: 1 full paragraph covering hosting model, access patterns with authentication method, configuration management with promotion path, backup strategy with retention periods, disaster recovery approach, and monitoring tools. If security compliance data exists, weave in RBAC, MFA, audit logging, and certification requirements). ### Integration Landscape (opening paragraph on integration strategy emphasizing reliability, traceability, and reconciliation. THEN markdown table: | Source | Target | Pattern | Frequency | â€” for ALL integrations from the data including those marked as 'None'. THEN paragraph on integration risks including data inconsistency from manual workarounds, and enhancement roadmap for activating future integrations). ### Environment Strategy (full paragraph: number of environments with naming conventions, purpose of each, step-by-step promotion workflow from developer commit through production release, data refresh schedule with anonymization/tokenization approach, PII masking, access governance with quarterly reviews). ### Target Operating Model (full paragraph: 24/7 coverage model with specific engineer counts per shift, peak vs. off-peak staffing, shift handover protocol with duration and checklist, time zone windows, escalation path L1â†’L2â†’L3 with named roles and response times for each level, on-call rotation schedule). ### Technical Risk Considerations (AT LEAST 5 risks as bullet points, each with: risk title, full sentence description of the risk and its potential impact, and specific mitigation approach. Cover: integration failure, configuration drift, data privacy in lower environments, model degradation, single points of failure)."
}"""
        )

        self.log("proposal_call_1", {"sections": "exec_summary, scope, solution"})
        result1 = await self.llm_json(prompt1, max_tokens=8000)

        # â”€â”€ CALL 2: Team + Transition + Commercial â”€â”€
        prompt2 = (
            preamble
            + """

Generate these 3 sections as JSON:
{
  "team_and_governance": "### Proposed Team Model (opening paragraph summarizing the delivery team: total FTE count, location distribution rationale, follow-the-sun coverage model, and how the team structure maps to the client's operational needs. THEN markdown table: | Role | FTEs | Location | Key Responsibilities | â€” for EVERY role from the data, with 2-3 sentence description of key responsibilities per role explaining WHAT they do and WHY this role is critical to the engagement). ### Governance Framework (3 subsections each with a full paragraph: **Steering Committee** monthly â€” chaired by whom, what it reviews including TCV utilization, automation savings, risk exposure. **Operational Review** weekly â€” led by whom, tracks SLA compliance, incident trends, backlog, resource utilization, focus areas. **SLA Governance** monthly â€” dedicated review of availability, incident resolution, change success, benchmarked against contractual obligations with root cause analysis for breaches). ### RACI Matrix (markdown table: | Key Activity | Service Owner | Program Manager | Functional Consultant | Support Engineer | Solution Architect | â€” with R/A/C/I for at least 6 activities: Service Delivery, Incident Management, Change Implementation, Integration Maintenance, Release Deployment, Knowledge Management). ### Escalation Matrix (markdown table: | Level | Description | Response Time | Resolution Target | â€” 3 levels with specific times). ### Communication Cadence (paragraph describing daily stand-ups, weekly reviews, monthly governance, quarterly business reviews, and the collaboration portal).",

  "transition_plan": "### Transition Overview (paragraph describing the phased approach, total duration in weeks, total transition cost, and how it ensures minimal disruption. Reference the three distinct phases by name). ### Phase Plan (markdown table: | Phase | Week | Duration | Key Activities | Exit Criteria | â€” for EACH phase from the transition data, with specific activities and measurable exit criteria). ### Knowledge Transfer Methodology (full paragraph: number of KT waves, duration of each wave, shadow period length, what each wave covers â€” Wave 1 architecture/integration, Wave 2 functional configurations, Wave 3 support operations. Reverse KT sessions, documentation and recording in centralized repository). ### Parallel Run & Cutover (full paragraph: parallel run duration, go-live criteria from the data, rollback plan with specific triggers). ### Change Management Strategy (### Stakeholder Analysis: for each stakeholder group from the data, describe impact level, readiness, key concerns, and engagement approach. ### Training Plan: markdown table: | Program | Audience | Method | Duration | â€” from the training programs data. ### Communication Plan: describe channels and frequency. ### Success Metrics: list each success metric with its target value from the data). ### Transition Risks & Mitigations (markdown table: | Risk | Likelihood | Impact | Mitigation | Owner | â€” from the transition risks data, at least 3 risks).",

  "commercial_proposition": "### Pricing Summary (markdown table: | Metric | Value | â€” with TCV, Annual Revenue, Monthly Price, Contract Term, Transition Cost). ### Cost Structure Breakdown (markdown table: | Cost Category | Amount | Notes | â€” with Direct Delivery, Transition, Change Management, Tools & Licensing, Travel & Expenses, COGS Total â€” use EXACT amounts from the data with explanatory notes). ### Commercial Scenarios (if scenario data is available, include markdown table: | Scenario | TCV | Margin | â€” for Base, Aggressive, and Conservative scenarios. Add a paragraph explaining the pricing model rationale and how each scenario balances investment with value). ### YOY Cost Optimization (markdown table: | Year | Automation Savings | Realization % | Cumulative | â€” from the automation YOY data). ### Automation Savings Detail (markdown table: | Automation | Platform | FTE Reduction | Annual Saving | â€” for EVERY automation opportunity from the data). ### Pricing Model & Value Engineering (full paragraph: pricing model type â€” fixed-fee for cost predictability, gross margin percentage, how cumulative automation savings enhance operational efficiency, each automation mapped to platforms and validated through ROI analysis, commercial structure aligned with client's strategic goals of scalability, resilience, and continuous improvement)."
}"""
        )

        self.log("proposal_call_2", {"sections": "team, transition, commercial"})
        result2 = await self.llm_json(prompt2, max_tokens=7000)

        # â”€â”€ CALL 3: Automation + Risk (deep compliance) â”€â”€
        prompt3 = (
            preamble
            + """

Generate these 2 sections as JSON:
{
  "automation_roadmap": "### Automation & AI Innovation Strategy (opening paragraph: strategic vision for automation as a transformative capability â€” not just cost savings but operational intelligence. State the total number of automation opportunities identified, total FTE reduction potential, total annual cost avoidance figure, and the philosophy of building a self-optimizing workforce management ecosystem). ### Per-Platform Opportunities (for EACH platform from the automation data: write a subheading with the platform name, then for EACH automation opportunity on that platform write a FULL detailed entry with: **[PRIORITY] Title** followed by a 3-4 sentence paragraph explaining: (1) WHAT the automation does and what business problem it solves, (2) HOW it works technically â€” the mechanism, triggers, and data flows, (3) the expected BENEFIT with quantified impact â€” FTE reduction number, effort level, and implementation horizon. Do NOT just list bullet points â€” each automation must have a substantive paragraph that a client can evaluate). ### Cross-Platform Synergies (full paragraph explaining how automations across platforms create compounding value â€” e.g., anomaly detection in one platform triggering actions in another, shared CI/CD infrastructure, unified monitoring reducing end-to-end process latency and manual handoffs. Reference specific cross-platform automations from the data). ### Implementation Roadmap (Year 1: list specific automations to deploy with individual FTE reductions and cumulative total. Year 2: list next wave of automations with cumulative FTE reduction. Year 3: optimization and scaling focus â€” sustaining gains and exploring new AI use cases). ### ROI Summary (markdown table: | Metric | Value | â€” total FTE reduction, total annual savings, payback period, 3-year cumulative savings).",

  "risk_management": "### Risk Register (opening paragraph: describe the risk management methodology â€” proactive identification, continuous monitoring, structured mitigation through governance. Mention bi-weekly assessment using 5x5 matrix, escalation protocols, centralized register reviewed in Service Review Meetings with accountable owners. THEN markdown table: | # | Risk | Likelihood | Impact | Mitigation | Owner | â€” include AT LEAST 5 risks combining transition risks and contractual risks from the data, with specific mitigation strategies and named owner roles). ### SLA Risk Assessment (if SLA risks data is available: full paragraph analyzing each SLA target's feasibility â€” which are achievable, which are stretch, which need negotiation. Include a markdown table: | SLA | Target | Feasibility | Recommendation | â€” from the SLA risks data). ### Penalty Exposure Analysis (if penalty data is available: full paragraph analyzing penalty types â€” service credits, liquidated damages, termination triggers. Assess whether penalties are capped or uncapped and the financial exposure level). ### Compliance Considerations (full paragraph: cover ALL data privacy standards from the data protection matrix â€” GDPR, CCPA, or other regulations by jurisdiction. Describe RBAC enforcement across all platforms, quarterly access reviews, segregation of duties, audit log retention period, mandatory compliance training, SOC 2 Type II certification maintenance). ### Contractual Risk Management (full paragraph: MSA structure with defined SLAs and financial remedies for breaches including service credits, exit clauses ensuring seamless knowledge transfer and data portability, IP ownership â€” custom assets to client while reusable accelerators retained, force majeure provisions with communication protocols and recovery timelines). ### Business Continuity & Disaster Recovery (full paragraph: DR plan with specific RPO and RTO targets, redundant infrastructure in geographically dispersed regions, backup frequency and retention period, quarterly failover testing, communication protocols during incidents â€” automated alerts, hourly status updates during major outages, post-mortem reports within 72 hours, annual DR plan review)."
}"""
        )

        self.log("proposal_call_3", {"sections": "automation, risk"})
        result3 = await self.llm_json(prompt3, max_tokens=6000)

        # â”€â”€ CALL 4: Methodology + Value Prop + Case Studies â”€â”€
        prompt4 = (
            preamble
            + """

Generate these 3 sections as JSON:
{
  "methodology": "### Delivery Methodology (opening paragraph: describe the hybrid ITIL + Agile operating model â€” ITIL for service management stability, Agile for execution adaptability. Explain how this phased approach enables structured transition, rapid stabilization, and continuous value delivery with clear governance, measurable outcomes, and client collaboration). Then for EACH of the 5 phases below, write a FULL detailed subsection with: **Objective** (1 sentence stating the goal), **Approach** (2-3 sentences describing HOW this phase is executed â€” methodology, tools, collaboration model), **Key Activities** (4-5 bullet points with specific actionable items), **Deliverables** (3-4 specific documents/artifacts by name), **Duration** (specific timeframe from the data), **Success Criteria** (2-3 measurable criteria with specific thresholds). The 5 phases: (1) Mobilization & Planning (Weeks 1-3 of transition), (2) Transition & Knowledge Transfer (use KT waves and shadow periods from data), (3) Stabilization & Early Life Support (hypercare period from data), (4) Steady State Operations (main contract period), (5) Continuous Improvement & Innovation (from Month 6 onward â€” quarterly innovation cycles, automation deployment cadence, minimum automations per quarter target).",

  "value_proposition": "### Strategic Value Proposition (2 compelling paragraphs: Para 1 â€” how this partnership transforms the client's operations from a cost center into a strategic asset driving operational agility, cost efficiency, and stakeholder satisfaction. Reference the client's scale and how platform reliability directly impacts operations, compliance, and business outcomes. Para 2 â€” how integrating all platforms into a cohesive automated operating model eliminates silos, reduces manual intervention, enables data-driven decision-making at scale, with specific automation count and savings figures). ### Quantitative Benefits (markdown table: | Benefit Area | Year 1 | Year 2 | Year 3 | â€” covering: FTE Reduction with specific numbers per year, Cost Savings in dollars, Uptime Improvement percentages trending upward, Incident Resolution Time improving year over year. Use realistic progression â€” Year 3 should show sustained/improved metrics, NOT zero). ### Qualitative Benefits (full paragraph: data integrity through automated validation and reconciliation, proactive monitoring with AI-driven anomaly detection for early issue identification, improved end-user experience through self-service tools and streamlined workflows, institutional knowledge preservation through living documentation and structured KT, scalable architecture for future geographic and platform expansion). ### Partnership Model & Long-term Vision (paragraph: quarterly innovation cycles for joint performance assessment and enhancement prioritization, embedded security ensuring compliance at every layer, long-term AI-driven operations vision including predictive analytics, intelligent process optimization, and advanced analytics for demand forecasting with 95%+ accuracy). ### Why Us (5 bullet points, each a FULL sentence using WIN THEMES and DIFFERENTIATORS from the competitive data: proven expertise managing large-scale multi-platform environments in the client's industry, dedicated team with certified specialists in the specific platforms, follow-the-sun support model with specific FTE count, automation-first approach with proven efficiency gains percentage, robust security and compliance framework with certifications).",

  "case_studies": "Generate 3-5 detailed case studies based on RFP complexity. Each case study MUST be a JSON object with these fields: title (compelling headline with quantified result â€” e.g., 'Global Retailer Achieves 40% Reduction in Support Costs'), client_type (industry / employee count / geography â€” match the current client's industry and scale), challenge (3-4 sentences: business context, specific pain points with technical details, what was failing and WHY it mattered commercially â€” cost overruns, compliance risks, operational disruption), solution (4-5 sentences: what was deployed â€” exact team size, specific platforms matching the RFP, number of automations implemented, methodology used, transition timeline, key innovations), outcome (4 bullet-point quantified results: cost savings with $ amount, FTE reduction number, uptime percentage, time-to-resolve improvement, ROI timeline), technologies (array of platform and tool names matching those in scope), team_size (string like '25 FTEs'), duration (string like '36 months'), relevance (2-3 sentences explaining why THIS case study directly applies to the current client â€” similar industry, comparable scale, identical platforms, shared challenges). IMPORTANT: Each case study must feature different platforms from the scope to demonstrate breadth. Mark all as 'Pending Validation' with verified: false. Do NOT invent specific client names."
}"""
        )

        self.log(
            "proposal_call_4", {"sections": "methodology, value_prop, case_studies"}
        )
        result4 = await self.llm_json(prompt4, max_tokens=7000)

        # â”€â”€ CALL 5: Delivery Approach (dynamic per RFP type) + Competitive Positioning â”€â”€
        # This call dynamically adapts based on the RFP context â€” the LLM infers the
        # engagement type (AMS, Implementation, Advisory, Transformation, Hybrid) from
        # the data and generates the appropriate layered delivery model.
        prompt5 = (
            preamble
            + """

IMPORTANT: Analyze the CONTRACT TYPE, scope of work, team model, and transition plan data above
to INFER the engagement type. This could be: AMS (Application Managed Services), Implementation
(greenfield/brownfield), Advisory/Consulting, Digital Transformation, or a Hybrid model.
Adapt your response to match whatever the RFP demands â€” DO NOT assume any specific type.

Generate these 2 sections as JSON:
{
  "delivery_approach": "### Engagement Model (opening paragraph: based on the contract type and scope data, describe the engagement model â€” is this a managed services engagement with steady-state operations, a transformation program with implementation phases, an advisory engagement, or a hybrid? Explain WHY this model was chosen based on the client's needs, platform complexity, and objectives. This paragraph MUST be specific to the RFP context, not generic). ### Layered Delivery Architecture (describe 4-5 delivery layers as detailed subsections. For EACH layer write a FULL paragraph with specific details: **Layer 1 â€” Strategic Advisory & Program Governance**: engagement leadership, client stakeholder alignment, program management office, quarterly business reviews, continuous improvement charter, innovation pipeline management. **Layer 2 â€” Solution Architecture & Design Authority**: platform architecture governance, integration design authority, change advisory board, environment strategy, security architecture oversight, technology roadmap ownership. **Layer 3 â€” Functional & Technical Operations**: day-to-day operations for each platform â€” incident management, problem management, change execution, configuration management, release management, user support, reporting and analytics, scheduled jobs monitoring. Detail what activities happen at L1/L2/L3 support tiers. **Layer 4 â€” Automation & Innovation Engine**: automation opportunity identification and implementation, RPA/scripting/API development, AI/ML model deployment for predictive operations, CI/CD pipeline management, self-healing infrastructure, proactive monitoring and alerting. **Layer 5 â€” Quality Assurance & Compliance**: SLA monitoring and reporting, CSAT measurement, audit readiness, regulatory compliance, security assessments, knowledge management, documentation governance). ### Operating Model (full paragraph: describe the steady-state operating rhythm â€” daily stand-ups, weekly operational reviews, monthly governance, quarterly business reviews. Cover shift structure if 24/7, or business-hours if not, with specifics from the team model data. Describe how tickets flow from intake through resolution with average resolution times per priority). ### Delivery Tooling & Ecosystem (full paragraph: describe the service management platform â€” ITSM tool for incident/change/problem management, collaboration platform, documentation repository, monitoring and alerting stack, CI/CD pipeline tools, automation platform, reporting and dashboards. Do NOT name specific vendor tools unless they appear in the data â€” instead describe capabilities). ### Continuous Improvement Framework (paragraph: describe the structured approach to continuous improvement â€” quarterly automation reviews, monthly efficiency assessments, annual roadmap refresh, innovation budget allocation, automation deployment targets per quarter, KPI-driven improvement with specific metrics like mean-time-to-resolve reduction targets).",

  "competitive_positioning": "### Why Us for This Engagement (opening paragraph: synthesize ALL win themes and differentiators from the competitive intelligence data into a compelling narrative about why we are uniquely positioned for this specific engagement. Reference the client's industry, scale, platforms, and challenges). ### Competitive Advantages (for EACH differentiator from the data, write a bullet point with a bold title and 2-sentence explanation of how it directly addresses the client's needs and why competitors cannot match it). ### Incumbent Transition Strategy (if incumbent data is available: paragraph on how we will ensure smooth transition from the incumbent â€” knowledge capture, parallel operations, risk mitigation, client communication, timeline for full operational ownership). ### Strategic Partnership Vision (paragraph: long-term vision beyond the initial contract â€” how we will evolve the engagement through innovation cycles, automation maturity advancement, expanding scope as trust is built, joint IP development, and becoming a strategic technology partner rather than just a service provider)."
}"""
        )

        self.log(
            "proposal_call_5",
            {"sections": "delivery_approach, competitive_positioning"},
        )
        result5 = await self.llm_json(prompt5, max_tokens=5000)

        # Merge all results
        merged = {**result1, **result2, **result3, **result4, **result5}
        return merged

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        obs = await self.observe()
        client_name = obs.get("client", {}).get("name", "Client")
        products = obs.get("products", "")

        # Build ordered sections â€” comprehensive proposal structure
        section_order = [
            ("executive_summary", "Executive Summary"),
            ("scope_of_services", "Scope of Services"),
            ("solution_design", "Solution Design & Architecture"),
            ("delivery_approach", "Delivery Approach & Operating Model"),
            ("team_and_governance", "Team Model & Governance"),
            ("transition_plan", "Transition & Change Management"),
            ("automation_roadmap", "AI & Automation Roadmap"),
            ("commercial_proposition", "Commercial Proposition"),
            ("methodology", "Delivery Methodology"),
            ("risk_management", "Risk Management & Compliance"),
            ("value_proposition", "Value Proposition & Business Case"),
            ("competitive_positioning", "Why Us"),
        ]

        sections = []
        for key, title in section_order:
            content = decision.get(key)
            if content:
                sections.append(
                    {"id": key, "title": title, "content": _deep_text(content)}
                )

        case_studies = decision.get("case_studies", [])
        # The LLM may return case_studies as a string (prompt leak) or a single dict
        if isinstance(case_studies, str):
            case_studies = []
        elif isinstance(case_studies, dict):
            case_studies = [case_studies]
        elif not isinstance(case_studies, list):
            case_studies = []

        # Count
        sections_written = len(sections)
        word_count = sum(len(str(s["content"]).split()) for s in sections)

        summary = f"Full proposal with {sections_written} sections, {len(case_studies)} case stud{'y' if len(case_studies) == 1 else 'ies'} ({word_count:,} words)."

        # Compile full narrative â€” professional, copy-paste ready document
        full_narrative = "# Proposal Response\n"
        full_narrative += f"## {client_name} â€” {products}\n\n"
        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"]
        full_narrative += f"**Prepared by:** {bidder_name} | **Confidential**\n\n---\n"

        # Table of Contents
        full_narrative += "\n## Table of Contents\n\n"
        for i, s in enumerate(sections, 1):
            full_narrative += f"{i}. {s['title']}\n"
        if case_studies:
            full_narrative += f"{len(sections) + 1}. Case Studies\n"
        full_narrative += "\n---\n"

        # Sections
        for i, s in enumerate(sections, 1):
            full_narrative += f"\n\n## {i}. {s['title']}\n\n{s['content']}"

        # Case Studies
        if case_studies:
            full_narrative += f"\n\n## {len(sections) + 1}. Case Studies\n"
            for cs in case_studies:
                if isinstance(cs, dict):
                    full_narrative += f"\n### {cs.get('title', 'Case Study')}\n\n"
                    full_narrative += (
                        f"**Client Profile:** {cs.get('client_type', '')}\n\n"
                    )
                    full_narrative += f"**Challenge:** {cs.get('challenge', '')}\n\n"
                    full_narrative += (
                        f"**Solution Delivered:** {cs.get('solution', '')}\n\n"
                    )
                    full_narrative += (
                        f"**Business Outcome:** {cs.get('outcome', '')}\n\n"
                    )
                    full_narrative += f"**Relevance to {client_name}:** {cs.get('relevance', '')}\n\n---\n"

        full_narrative += f"\n\n---\n\n*This document is confidential and proprietary. Â© {bidder_name}.*\n"

        # === CLOSED-LOOP: Capture learnings for institutional improvement ===
        self.capture_learning(
            learning_type="proposal_pattern",
            insight=f"Proposal generated with {sections_written} sections, "
            f"{len(case_studies)} case studies, {word_count:,} words. "
            f"Client: {client_name}. Products: {products}.",
            confidence=0.7,
        )
        if word_count < 2000:
            self.capture_learning(
                learning_type="quality_flag",
                insight="Proposal word count below 2000 â€” likely truncated or insufficient depth. "
                "Consider increasing max_tokens or adding more upstream agent data.",
                confidence=0.8,
            )

        return {
            "sections": sections,
            "case_studies": case_studies,
            "sections_written": sections_written,
            "total_word_count": word_count,
            "narrative": full_narrative.strip(),
            "hitl_summary": summary,
        }
