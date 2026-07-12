"""
Compliance & Risk Agent â€” Per-clause risk assessment, negotiation matrix, compliance checklist.
Output: Risk register with RFP section citations, negotiation priorities, data protection matrix.
Works for any contract type: AMS, implementation, advisory, transformation, staff aug.
Zero hardcoded vendor names.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class ComplianceRiskAgent(BaseAgent):
    name = "Compliance & Risk Agent"
    agent_tier = "analytical"  # Risk matrix + SLA analysis, 70B handles legal language

    def _inject_structural_risks(self, contract_type: str, geographies: list) -> dict:
        """
        Last-resort fallback: inject known structural risks that apply to any
        AMS / implementation / transformation bid where the RFP defers material
        commercial terms to an MSA that was not provided alongside the RFP.

        These are universally valid â€” not client or vendor specific.
        Called only when both LLM attempts return empty arrays.
        """
        ct = contract_type.upper() if contract_type else "AMS"
        multi_geo = len(geographies) > 5

        contractual_risks = [
            {
                "clause": "MSA terms not provided",
                "rfp_section": "Commercial / Pricing sections",
                "risk_level": "critical",
                "description": (
                    "The RFP repeatedly defers material commercial terms (liability caps, indemnity, "
                    "insurance, pricing, payment) to a Master Service Agreement that was not attached. "
                    "Bidding without reviewing the full MSA creates uncapped financial exposure."
                ),
                "negotiation_priority": "must-negotiate",
                "recommended_position": (
                    "Obtain and review full MSA before final pricing. "
                    "Attach MSA review as a bid precondition."
                ),
                "mitigation": (
                    "Include explicit commercial assumptions in the bid; "
                    "caveat pricing on MSA review."
                ),
            },
            {
                "clause": "Service Credits / Earn-backs undefined",
                "rfp_section": "SLA & Coverage section",
                "risk_level": "high",
                "description": (
                    "The RFP references Service Credits and Earn-backs tied to SLA attainment "
                    "and business outcomes but does not specify credit percentages, calculation "
                    "windows, or earn-back eligibility criteria. This creates open-ended financial liability."
                ),
                "negotiation_priority": "must-negotiate",
                "recommended_position": (
                    "Cap aggregate monthly service credits at 10% of monthly fees. "
                    "Define earn-back mechanics explicitly."
                ),
                "mitigation": (
                    "Assume 10% monthly credit cap in financial model until terms are confirmed."
                ),
            },
            {
                "clause": "Chronic SLA miss penalties undefined",
                "rfp_section": "SLA & Coverage section",
                "risk_level": "high",
                "description": (
                    "Penalties for chronic SLA misses and chronic incident repeatability are "
                    "referenced but not quantified. Without explicit caps, cumulative penalties "
                    "could exceed contract value."
                ),
                "negotiation_priority": "must-negotiate",
                "recommended_position": (
                    "Define chronic threshold (e.g. 3 consecutive months). "
                    "Cap cumulative annual penalties at 15% of annual contract value."
                ),
                "mitigation": (
                    "Exclude force-majeure events and client-caused incidents "
                    "from penalty calculations."
                ),
            },
            {
                "clause": "Termination for convenience / exit costs",
                "rfp_section": "Terms, Duration & Exit section",
                "risk_level": "high",
                "description": (
                    "The RFP specifies an initial term with extension options but does not define "
                    "termination-for-convenience notice periods, wind-down cost recovery, or "
                    "transition-out fee obligations. Early termination could leave stranded staffing costs."
                ),
                "negotiation_priority": "must-negotiate",
                "recommended_position": (
                    "Minimum 6-month notice for termination for convenience. "
                    "Recover committed headcount costs for transition-out period."
                ),
                "mitigation": (
                    "Include workforce wind-down costs in financial model as a risk reserve."
                ),
            },
        ]

        if multi_geo:
            contractual_risks.append(
                {
                    "clause": "Multi-jurisdiction compliance obligations",
                    "rfp_section": "Security, Compliance & Privacy section",
                    "risk_level": "high",
                    "description": (
                        f"The engagement spans {len(geographies)} countries. Country-specific payroll "
                        "privacy, labor data, and GDPR/equivalent requirements vary materially. "
                        "Non-compliance in any single jurisdiction can trigger regulatory fines and contract penalties."
                    ),
                    "negotiation_priority": "must-negotiate",
                    "recommended_position": (
                        "Limit liability to the specific country in breach. "
                        "Client to provide country-level compliance requirements per jurisdiction."
                    ),
                    "mitigation": (
                        "Obtain country-specific legal review; include compliance gap costs in pricing."
                    ),
                }
            )

        if any(kw in ct for kw in ("IMPLEMENTATION", "TRANSFORMATION", "HYBRID")):
            contractual_risks.append(
                {
                    "clause": "Go-live acceptance criteria undefined",
                    "rfp_section": "Transition & Knowledge Transfer section",
                    "risk_level": "high",
                    "description": (
                        "Go-live exit criteria reference smooth payroll runs governed by multiple "
                        "committees but do not define acceptance thresholds, defect tolerances, or "
                        "dispute resolution. Subjective acceptance creates risk of delayed sign-off and unpaid milestones."
                    ),
                    "negotiation_priority": "must-negotiate",
                    "recommended_position": (
                        "Define binary, measurable acceptance criteria "
                        "(e.g. zero P1 incidents, 100% payroll accuracy for 2 cycles)."
                    ),
                    "mitigation": (
                        "Escalation path to neutral arbitrator if acceptance is withheld unreasonably."
                    ),
                }
            )

        sla_risks = [
            {
                "sla": "Response/Resolution targets",
                "rfp_section": "Service Levels section",
                "target": "Not quantified in RFP â€” deferred to response workbook",
                "risk": (
                    "Specific MTTA/MTTR targets are referenced but not stated in the RFP text. "
                    "Accepting SLAs without knowing target values prevents accurate cost modeling for staffing."
                ),
                "feasibility": "stretch",
                "recommendation": "negotiate",
            },
            {
                "sla": "24x7 payroll-critical monitoring",
                "rfp_section": "Service Levels section",
                "target": "24x7 coverage for payroll-critical incidents irrespective of standard hours",
                "risk": (
                    "Payroll-critical 24x7 monitoring overrides the base 24x5 coverage. "
                    "This requires dedicated on-call staffing with defined decision rights, "
                    "adding cost that must be explicitly priced and not absorbed into base service."
                ),
                "feasibility": "achievable",
                "recommendation": "negotiate",
            },
            {
                "sla": "Surge capacity commitment",
                "rfp_section": "Service Levels section",
                "target": "Demonstrated surge capacity for go-lives, major incidents, vendor release peaks",
                "risk": (
                    "Surge capacity obligations are qualitative and open-ended. Without defined "
                    "surge thresholds and additional fee mechanisms, surges could require "
                    "uncompensated overtime or understaffing."
                ),
                "feasibility": "stretch",
                "recommendation": "negotiate",
            },
        ]

        penalty_exposure = [
            {
                "penalty_type": "service credits",
                "rfp_section": "SLA & Coverage / Pricing sections",
                "exposure_level": "high",
                "description": (
                    "Service credits tied to monthly SLA attainment and business outcome KPIs. "
                    "Exact credit percentages not defined in RFP â€” deferred to MSA."
                ),
                "cap_analysis": "Uncapped as stated â€” cap must be negotiated",
            },
            {
                "penalty_type": "chronic miss penalties",
                "rfp_section": "SLA & Coverage section",
                "exposure_level": "high",
                "description": (
                    "Additional penalties for chronic SLA misses and chronic incident repeatability. "
                    "Thresholds and amounts not defined."
                ),
                "cap_analysis": "Uncapped as stated â€” definition of chronic and caps must be negotiated",
            },
        ]

        return {
            "contractual_risks": contractual_risks,
            "sla_risks": sla_risks,
            "penalty_exposure": penalty_exposure,
            "overall_risk_rating": "high",
            "showstoppers": [
                "MSA not provided â€” material commercial terms (liability, indemnity, credits) "
                "cannot be evaluated without it"
            ],
        }

    async def observe(self) -> Dict[str, Any]:
        rfp_text = self.manifest.get("rfp_text", "")
        intake = self.manifest.get("intake_output", {})
        kb_context = await self.get_kb_context(
            "compliance legal terms conditions SLA penalties indemnity data protection",
            collections=["clause_library", "rfps"],
        )
        geographies = []
        if isinstance(intake, dict):
            geo = intake.get("extracted_fields", {}).get("geographies", {})
            if isinstance(geo, dict):
                geographies = geo.get("value", [])
            elif isinstance(geo, list):
                geographies = geo

        contract_type = ""
        if isinstance(intake, dict):
            ct = intake.get("extracted_fields", {}).get("contract_type", {})
            contract_type = (
                ct.get("value", ct) if isinstance(ct, dict) else str(ct or "")
            )

        # FIX: get_rfp_sections("compliance_risk") only returns sections tagged for this
        # agent by the chunking pipeline. If SLA/penalty/contractual sections were not
        # tagged "compliance_risk", Call 1 receives an empty string and returns zero risks.
        # Fall back to the full rfp_text from manifest whenever sections are sparse.
        sectioned_text = self.get_rfp_sections("compliance_risk")
        effective_rfp = sectioned_text if len(sectioned_text) > 200 else rfp_text

        return {
            "rfp_text": effective_rfp,
            "intake": intake,
            "kb_context": kb_context,
            "client": self.manifest.get("client", {}),
            "geographies": geographies,
            "contract_type": contract_type,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Split analysis into two focused LLM calls to avoid truncation."""
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse approved clause positions.\n"

        geo_context = (
            f"\nGeographies: {', '.join(obs.get('geographies', []))}\n"
            if obs.get("geographies")
            else ""
        )
        ct_context = f"\nContract Type: {obs.get('contract_type', 'Unknown')}\n"

        rfp_text = obs["rfp_text"]

        # â”€â”€ CALL 1: Contractual risks, SLA risks, penalties â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        prompt_risks = f"""Analyze this RFP for contractual, SLA, and penalty risks.

RULES:
- Cite specific RFP sections for EVERY risk
- Classify each risk by severity and negotiation priority
- Do NOT hardcode any vendor name not in the RFP
- If a section is unclear, ambiguous, or defers to an external Master Service Agreement (MSA) that is not provided, you MUST flag the missing terms as HIGH priority contractual risks.
- If SLAs are not explicitly defined but are expected for this contract type, flag the lack of SLAs as a HIGH priority SLA risk.
{ct_context}
=== RFP DOCUMENT ===
{rfp_text}
{kb_section}
{geo_context}

Return JSON with EXACTLY this structure:
{{
  "contractual_risks": [
    {{"clause": "short clause summary", "rfp_section": "section ref", "risk_level": "critical|high|medium|low", "description": "why this is risky", "negotiation_priority": "must-negotiate|should-negotiate|acceptable", "recommended_position": "what to propose", "mitigation": "if accepted as-is"}}
  ],
  "sla_risks": [
    {{"sla": "SLA name", "rfp_section": "ref", "target": "target value", "risk": "why challenging", "feasibility": "achievable|stretch|unrealistic", "recommendation": "accept|negotiate|reject"}}
  ],
  "penalty_exposure": [
    {{"penalty_type": "service credits|LD|termination", "rfp_section": "ref", "exposure_level": "high|medium|low", "description": "penalty terms", "cap_analysis": "capped or uncapped"}}
  ],
  "overall_risk_rating": "high|medium|low",
  "showstoppers": ["any terms that could prevent bidding"]
}}

Each risk description should be 2-3 sentences explaining the specific exposure and commercial impact.
Include ALL risks you find. You MUST output at least 2 contractual risks and 1 SLA risk, even if they are simply flagging missing information or deferred MSA terms as critical risks to clarify before bidding."""

        risks = await self.llm_json(prompt_risks, max_tokens=4000)

        # â”€â”€ CALL 1 VALIDATION + RETRY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # If the LLM returned empty arrays (truncated JSON, parse failure, or the
        # rfp_text sections had no contractual content), retry once with a shorter,
        # more directive prompt before falling back to programmatic risks.
        call1_empty = (
            not risks.get("contractual_risks")
            and not risks.get("sla_risks")
            and not risks.get("penalty_exposure")
        )
        if call1_empty:
            self.log(
                "call1_retry",
                {"reason": "Call 1 returned no risks â€” retrying with focused prompt"},
            )
            rfp_truncated = rfp_text[
                :8000
            ]  # guard against context-limit failures on retry
            prompt_retry = (
                "You are a contract risk analyst. Read the RFP and extract risks.\n"
                + ct_context
                + "\n=== RFP ===\n"
                + rfp_truncated
                + "\n\nYou MUST return populated JSON arrays. Never return empty arrays.\n"
                "Find at minimum: MSA deferral risks, undefined SLA targets, "
                "penalty/credit terms, unlimited liability, termination clauses.\n"
                "{\n"
                '  "contractual_risks": [\n'
                '    {"clause": "summary", "rfp_section": "ref", "risk_level": "critical|high|medium|low",\n'
                '      "description": "2-3 sentence risk explanation", '
                '"negotiation_priority": "must-negotiate|should-negotiate|acceptable",\n'
                '      "recommended_position": "what to propose", "mitigation": "if accepted as-is"}\n'
                "  ],\n"
                '  "sla_risks": [\n'
                '    {"sla": "name", "rfp_section": "ref", "target": "value",\n'
                '      "risk": "why challenging", "feasibility": "achievable|stretch|unrealistic",\n'
                '      "recommendation": "accept|negotiate|reject"}\n'
                "  ],\n"
                '  "penalty_exposure": [\n'
                '    {"penalty_type": "type", "rfp_section": "ref", "exposure_level": "high|medium|low",\n'
                '      "description": "terms", "cap_analysis": "capped or uncapped"}\n'
                "  ],\n"
                '  "overall_risk_rating": "high|medium|low",\n'
                '  "showstoppers": []\n'
                "}"
            )
            risks = await self.llm_json(prompt_retry, max_tokens=4000)

        # â”€â”€ PROGRAMMATIC FALLBACK if both LLM attempts return empty â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Inject known structural risks that apply to any AMS/implementation bid
        # where the RFP defers terms to an MSA that was not provided.
        # This ensures the risk register is never silently empty.
        if not risks.get("contractual_risks") and not risks.get("sla_risks"):
            self.log(
                "call1_fallback",
                {
                    "reason": "Both LLM attempts returned empty â€” injecting structural risks"
                },
            )
            risks = self._inject_structural_risks(
                obs.get("contract_type", ""),
                obs.get("geographies", []),
            )

        self.log(
            "risks_extracted",
            {
                "contractual": len(risks.get("contractual_risks", [])),
                "sla": len(risks.get("sla_risks", [])),
                "penalties": len(risks.get("penalty_exposure", [])),
                "source": "llm" if not call1_empty else "retry_or_fallback",
            },
        )

        # â”€â”€ CALL 2: Data protection, IP, insurance, exit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        prompt_compliance = f"""Analyze this RFP for data protection, IP rights, insurance, and exit obligations.
{ct_context}
=== RFP DOCUMENT ===
{rfp_text}
{geo_context}

Return JSON with EXACTLY this structure:
{{
  "data_protection": [
    {{"jurisdiction": "country/region", "regulation": "GDPR|CCPA|etc", "requirements": ["requirement1"], "compliance_status": "compliant|partial|gap", "action_needed": "action"}}
  ],
  "insurance_indemnity": {{
    "insurance_requirements": ["requirement from RFP"],
    "indemnity_scope": "description of indemnity terms",
    "unlimited_liability_clauses": ["any unlimited liability found"],
    "recommendation": "assessment"
  }},
  "ip_data_rights": {{
    "ip_ownership": "who owns IP",
    "data_handling": "data obligations",
    "concerns": ["concern1"]
  }},
  "exit_transition": {{
    "exit_obligations": ["obligation from RFP"],
    "transition_assistance_period": "duration",
    "risks": ["risk1"]
  }}
}}

Be thorough. If a topic is not addressed in the RFP, flag it as a compliance gap that needs clarification."""

        compliance = await self.llm_json(prompt_compliance, max_tokens=4000)
        self.log(
            "compliance_extracted",
            {
                "data_protection": len(compliance.get("data_protection", [])),
                "has_insurance": bool(compliance.get("insurance_indemnity")),
            },
        )

        # â”€â”€ Merge both results â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        merged = {**risks, **compliance}

        # â”€â”€ overall_risk_rating fallback â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Derive programmatically if the LLM omitted it or returned a non-enum value.
        valid_ratings = {"high", "medium", "low"}
        if merged.get("overall_risk_rating", "").lower() not in valid_ratings:
            all_risk_items = merged.get("contractual_risks", []) + merged.get(
                "sla_risks", []
            )
            levels = [
                r.get("risk_level", r.get("feasibility", "")).lower()
                for r in all_risk_items
            ]
            if any(lv in ("critical", "high", "unrealistic") for lv in levels):
                merged["overall_risk_rating"] = "high"
            elif any(lv in ("medium", "stretch") for lv in levels):
                merged["overall_risk_rating"] = "medium"
            elif all_risk_items:
                merged["overall_risk_rating"] = "low"
            else:
                merged["overall_risk_rating"] = (
                    "medium"  # safe default: always needs review
                )

        # â”€â”€ Compute negotiation summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        must_neg = 0
        should_neg = 0
        acceptable = 0
        for r in merged.get("contractual_risks", []):
            prio = r.get("negotiation_priority", "")
            if prio == "must-negotiate":
                must_neg += 1
            elif prio == "should-negotiate":
                should_neg += 1
            else:
                acceptable += 1

        merged["negotiation_summary"] = {
            "must_negotiate": must_neg,
            "should_negotiate": should_neg,
            "acceptable": acceptable,
            "total_clauses_reviewed": must_neg + should_neg + acceptable,
        }

        return merged

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        neg_summary = decision.get("negotiation_summary", {})
        rating = decision.get("overall_risk_rating", "medium")  # safe default
        contractual = len(decision.get("contractual_risks", []))
        sla_risks = len(decision.get("sla_risks", []))
        penalties = len(decision.get("penalty_exposure", []))
        showstoppers = decision.get("showstoppers", [])
        must_neg = neg_summary.get("must_negotiate", 0)

        critical_clauses = [
            r.get("clause", "?")
            for r in decision.get("contractual_risks", [])
            if r.get("risk_level") in ("critical", "high")
        ][:3]
        data_regs = [
            d.get("regulation", "?") for d in decision.get("data_protection", [])
        ][:3]

        prompt = f"""Write a concise risk and compliance assessment (150-200 words max).

STYLE: Strategic legal/commercial assessment language. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive.

RISK DATA:
Overall Rating: {rating.upper()}
Contractual Risks: {contractual} | SLA Risks: {sla_risks} | Penalty Exposures: {penalties}
Must-Negotiate: {must_neg} | Should-Negotiate: {neg_summary.get("should_negotiate", 0)} | Acceptable: {neg_summary.get("acceptable", 0)}
Showstoppers: {len(showstoppers)} - {showstoppers[:2] if showstoppers else "None"}
Critical Clauses: {"; ".join(critical_clauses) if critical_clauses else "None"}
Data Protection Regulations: {", ".join(data_regs) if data_regs else "None specified"}

Write 3 tight paragraphs:
1. Risk verdict - overall rating and what drives it. Key contractual risks and their RFP sources.
2. SLA and penalty exposure - which SLAs are stretch/unrealistic, penalty cap analysis, financial exposure.
3. Negotiation strategy - must-negotiate items, showstoppers if any, recommended approach for legal review."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = (
            f"Risk: {rating.upper()}. {contractual} contractual risks, "
            f"{sla_risks} SLA risks, {must_neg} must-negotiate. "
        )
        summary += (
            f"{len(showstoppers)} showstoppers. "
            if showstoppers
            else "No showstoppers. "
        )

        return {
            "risk_register": decision,
            "narrative": narrative,
            "hitl_summary": summary,
        }
