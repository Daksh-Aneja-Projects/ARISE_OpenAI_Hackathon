"""
Intake Agent â€” First contact with client documents.
Parses, classifies, and structures raw RFP into BidManifest.

L9 Strategic Capabilities:
  - PDF noise filtering (strips IPs, page headers, watermarks before extraction)
  - Contradiction detection (flags conflicting values across RFP sections)
  - Validated facts repository (single source of truth for all downstream agents)
  - Evaluation criteria extraction (scoring weights for proposal section prioritization)
  - Mandatory vs. desirable requirement classification
  - Deal-type agnostic: works for AMS, Implementation, Transformation, Advisory, Hybrid

Extracts structured data that feeds ALL downstream agents:
  - Products/platforms with deployment matrix
  - Integration inventory with status tracking
  - SLA/KPI requirements with penalty exposure
  - Geographic scope with country-level detail
  - Incumbent signals for competitive positioning
  - Budget indicators for commercial calibration
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgent


class IntakeAgent(BaseAgent):
    name = "Intake Agent"
    agent_tier = "volume"  # 7 keys = max throughput for parallel RFP extraction

    def __init__(
        self, bid_id: str, manifest: Dict[str, Any], document_texts: List[str] = None
    ):
        super().__init__(bid_id, manifest)
        self.document_texts = document_texts or []

    async def observe(self) -> Dict[str, Any]:
        combined = (
            "\n\n---DOCUMENT BOUNDARY---\n\n".join(self.document_texts)
            if self.document_texts
            else ""
        )
        # Apply PDF noise filter BEFORE any LLM processing
        # This strips IP addresses, page headers/footers, watermarks that pollute extraction
        if combined:
            combined = self.clean_rfp_noise(combined)
            self.log(
                "pdf_noise_filtered",
                {
                    "original_chars": sum(len(d) for d in self.document_texts),
                    "cleaned_chars": len(combined),
                },
            )
        return {
            "document_content": combined[:80000],
            "existing_manifest": self.manifest,
            "document_count": len(self.document_texts),
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        if not obs["document_content"]:
            return {"has_content": False, "analysis": "No document content provided"}

        prompt = f"""Analyze this RFP document. Identify the document type, products, client, and structure.

CRITICAL: Extract product names EXACTLY as written. Do NOT substitute or assume products.

Document (first 25000 chars):
{obs["document_content"][:25000]}

Return JSON:
{{
  "document_type": "RFP|SOW|RFI|Qualification Questionnaire|Other",
  "contract_type_signals": ["signals indicating contract type"],
  "product_signals": ["EXACT product/platform names from document"],
  "client_name_signals": ["client name references"],
  "initial_risks": ["disqualifiers or red flags"],
  "geographic_signals": ["countries/regions mentioned"],
  "timeline_signals": ["duration/date references"],
  "complexity": "standard|complex|mega"
}}"""
        result = await self.llm_json(prompt, max_tokens=4000)
        result["has_content"] = True
        return result

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        if not orientation.get("has_content"):
            return {"action": "skip", "reason": "No document content"}
        return {
            "action": "full_extraction",
            "contract_type_signals": orientation.get("contract_type_signals", []),
            "product_signals": orientation.get("product_signals", []),
            "complexity": orientation.get("complexity", "standard"),
        }

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        if decision.get("action") == "skip":
            return {"status": "skipped", "reason": decision.get("reason")}

        combined = "\n\n".join(self.document_texts)[:60000]

        prompt = f"""You are an expert pre-sales Intake Analyst. Extract ALL key fields from this RFP.
This extraction feeds ALL downstream agents â€” scope, solution, automation, transition, commercial,
compliance, and competitive. Be THOROUGH. Missing data here = gaps in the final proposal.

CRITICAL RULES:
- Extract product names EXACTLY as written. Do NOT substitute or assume products.
- Extract EVERY integration mentioned, even if details are sparse
- Extract ALL SLAs/KPIs with their exact targets and measurement methods
- Identify incumbent/current provider signals for competitive positioning
- Flag any automation, AI, or innovation requirements explicitly
- Capture security, compliance, and data protection requirements

DOCUMENT:
{combined}

Extract and return JSON:
{{
  "contract_type": {{"value": "AMS|Implementation|Hybrid|Extend & Operate|Staff Aug|Advisory|Transformation", "confidence": "High|Medium|Low", "signals": ["RFP phrases that indicate this type"]}},
  "products": {{"value": ["EXACT product/platform names"], "confidence": "High|Medium|Low"}},
  "client_name": {{"value": "string", "confidence": "High|Medium|Low"}},
  "client_industry": {{"value": "string", "confidence": "High|Medium|Low"}},
  "employee_population": {{"value": "number or description", "confidence": "High|Medium|Low"}},
  "geographies": {{"value": ["countries/regions"], "confidence": "High|Medium|Low"}},
  "submission_deadline": {{"value": "YYYY-MM-DD or null", "confidence": "High|Medium|Low"}},
  "contract_duration": {{"value": "EXACT duration from RFP including extensions e.g. '2+1+1 years' or '36 months'. Include initial term AND optional extensions.", "confidence": "High|Medium|Low", "initial_months": 0, "extension_options": "e.g. 2x12 months", "total_max_months": 0}},
  "contract_start_date": {{"value": "YYYY-MM-DD or null", "confidence": "High|Medium|Low"}},
  "evaluation_criteria": {{"value": {{"technical": 0, "commercial": 0, "experience": 0, "other": 0}}, "confidence": "High|Medium|Low", "details": "any evaluation criteria text from RFP"}},
  "mandatory_sections": {{"value": ["required response sections"], "confidence": "High|Medium|Low"}},
  "disqualifiers": {{"value": ["potential disqualifiers â€” mandatory certs, minimum revenue, geography restrictions"], "confidence": "High|Medium|Low"}},
  "ambiguities": {{"value": [{{"description": "what is unclear", "severity": "High|Medium|Low", "impact": "which downstream agent this affects"}}], "confidence": "High|Medium|Low"}},
  "estimated_contract_value": {{"value": "number or null", "confidence": "High|Medium|Low"}},
  "key_requirements": {{"value": ["top 15-20 requirements â€” be exhaustive"], "confidence": "High|Medium|Low"}},
  "service_levels": {{"value": ["SLA requirements with targets"], "confidence": "High|Medium|Low"}},
  "certifications_required": {{"value": ["certifications/partnerships required"], "confidence": "High|Medium|Low"}},
  "incumbent_signals": {{"value": ["any mentions of current provider, handover, transition from existing vendor"], "confidence": "High|Medium|Low", "incumbent_name": "name if identified or null"}},
  "automation_references": {{"value": ["any RFP sections mentioning automation, AI, innovation, efficiency, continuous improvement"], "confidence": "High|Medium|Low"}},
  "security_requirements": {{"value": ["security certifications, data protection, GDPR, access controls, audit requirements"], "confidence": "High|Medium|Low"}},
  "budget_indicators": {{"value": "any budget range, cost expectations, pricing model preferences", "confidence": "High|Medium|Low"}},
  "stakeholder_groups": {{"value": ["key stakeholder groups mentioned â€” IT, HR, Finance, Operations, end users"], "confidence": "High|Medium|Low"}},
  "platform_details": [
    {{
      "product_name": "exact name from RFP",
      "vendor": "vendor name if mentioned",
      "version": "version if mentioned",
      "hosting_model": "cloud|on-premise|hybrid|SaaS",
      "countries_deployed": ["list or count"],
      "user_count": "number or description",
      "modules_in_scope": ["modules/features mentioned"],
      "key_config_volumes": [{{"type": "e.g. pay rules, integrations, reports", "count": "from RFP"}}],
      "environments": "count or list",
      "current_support_model": "how currently supported if mentioned",
      "customization_level": "standard|moderate|heavy â€” based on RFP signals",
      "criticality": "business-critical|important|standard"
    }}
  ],
  "integration_inventory": [
    {{
      "source": "system A",
      "target": "system B",
      "middleware": "if mentioned or null",
      "count": "number of integrations if stated",
      "type": "inbound|outbound|bidirectional",
      "frequency": "real-time|daily|weekly|on-demand if mentioned",
      "status": "active|planned|deprecated if mentioned"
    }}
  ],
  "kpi_sla_table": [
    {{
      "kpi_name": "from RFP â€” e.g. Incident Response Time, Resolution Time, Availability, Change Success Rate, Automation %",
      "target": "SLA target value if specified, otherwise 'TBD - referenced in [section]' or describe the SLA requirement as stated",
      "category": "availability|incident_management|change_management|service_request|reporting|automation",
      "measurement": "how measured, or 'Not specified' if RFP does not detail",
      "penalty": "penalty for breach if mentioned, or 'Referenced but not quantified'",
      "rfp_section": "section reference"
    }}
  ],
  "scope_sections": [
    {{
      "section_ref": "RFP section number",
      "title": "section title",
      "scope_summary": "2-3 sentence summary of what this section requires",
      "key_activities": ["main activities â€” be specific"],
      "response_requirements": ["what the RFP expects in the response for this section"]
    }}
  ]
}}"""

        result = await self.llm_json(prompt, max_tokens=8000)
        # Recovery: if llm_json failed to parse, attempt json.loads on the raw content
        if "error" in result and "raw" in result:
            import json as _json

            raw = result["raw"]
            # The raw may be truncated; try to find the JSON object
            try:
                s, e = raw.find("{"), raw.rfind("}") + 1
                if s >= 0 and e > s:
                    result = _json.loads(raw[s:e])
                    self.log("extraction_json_recovered", {"chars": len(raw)})
            except Exception:
                # Still failed — continue with empty result (agents will degrade gracefully)
                self.log(
                    "extraction_json_failed_permanently", {"raw_preview": raw[:200]}
                )
        self.log("extraction_complete", {"fields_extracted": len(result)})

        # Generate concise strategic narrative
        products = result.get("products", {}).get("value", [])
        platforms = result.get("platform_details", [])
        integrations = result.get("integration_inventory", [])
        slas = result.get("kpi_sla_table", [])
        scopes = result.get("scope_sections", [])
        client = result.get("client_name", {}).get("value", "Unknown")
        industry = result.get("client_industry", {}).get("value", "Unknown")
        contract_type = result.get("contract_type", {}).get("value", "Unknown")
        duration = result.get("contract_duration", {}).get("value", "Unknown")
        population = result.get("employee_population", {}).get("value", "Unknown")
        geographies = result.get("geographies", {}).get("value", [])

        narrative_prompt = f"""Write a strategic executive intake brief for this RFP opportunity.

STYLE: Senior consulting language. No markdown. No bullets. No asterisks. Professional flowing paragraphs that embed specific data points throughout. This is a client-ready brief that will be read by bid leadership.

DATA POINTS TO WEAVE IN:
- Client: {client} | Industry: {industry} | Contract Type: {contract_type}
- Products: {", ".join(products) if products else "Not identified"}
- Geographies: {", ".join(geographies[:8]) if geographies else "Not specified"} ({len(geographies)} total)
- Duration: {duration} | Population: {population}
- Platforms: {len(platforms)} | Integrations: {len(integrations)} | SLAs: {len(slas)}
- Disqualifiers: {len(result.get("disqualifiers", {}).get("value", []))}
- Ambiguities: {len(result.get("ambiguities", {}).get("value", []))}

You MUST write exactly 3 full paragraphs (each paragraph must be 3-5 sentences):

Paragraph 1 â€” ENGAGEMENT OVERVIEW: Who is the client, what industry, what is being procured (contract type), at what scale (employee population, geographies). Set the strategic context for why this engagement matters.

Paragraph 2 â€” PLATFORM AND TECHNICAL LANDSCAPE: What platforms are in scope, their deployment model, integration complexity ({len(integrations)} integrations across what systems), environment count, and the operational demands. Highlight what makes this technically challenging.

Paragraph 3 â€” RISKS, GAPS AND ATTENTION AREAS: What are the disqualification risks, key ambiguities that need clarification, areas where the RFP is vague or contradictory, and what must be resolved before the bid team can proceed with confidence.

Do NOT truncate. Write ALL three paragraphs in full."""

        narrative = await self.llm_generate(narrative_prompt, max_tokens=1500)

        # Build HITL summary â€” strategic, data-driven
        low_confidence = [
            k
            for k, v in result.items()
            if isinstance(v, dict) and v.get("confidence") == "Low"
        ]
        disqualifiers = result.get("disqualifiers", {}).get("value", [])
        ambiguities = result.get("ambiguities", {}).get("value", [])

        summary = f"Intake processed {len(self.document_texts)} document(s). "
        summary += f"Contract type: {contract_type}. "
        summary += (
            f"Products: {', '.join(products[:5]) if products else 'None identified'}. "
        )
        summary += f"{len(platforms)} platforms detailed, {len(integrations)} integrations mapped, {len(slas)} SLAs extracted. "
        if ambiguities:
            high_amb = len(
                [
                    a
                    for a in ambiguities
                    if isinstance(a, dict) and a.get("severity") == "High"
                ]
            )
            summary += f"{len(ambiguities)} ambiguities ({high_amb} high). "
        if disqualifiers:
            summary += f"{len(disqualifiers)} potential disqualifiers. "
        if low_confidence:
            summary += f"{len(low_confidence)} low-confidence fields."

        # Build RFP section index for downstream agents
        rfp_index = None
        try:
            from app.knowledge.rfp_indexer import build_rfp_index
            from app.services.llm import llm_service

            full_text = "\n\n".join(self.document_texts)
            if len(full_text) > 1000:
                rfp_index = await build_rfp_index(full_text, llm_service)
                self.log(
                    "rfp_index_built", {"sections": rfp_index.get("section_count", 0)}
                )
                summary += f" Indexed {rfp_index.get('section_count', 0)} sections."
        except Exception as e:
            self.log("rfp_index_failed", {"error": str(e)})

        # â”€â”€ Contradiction Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Scan for conflicting values within the extraction itself
        contradictions = []
        emp = result.get("employee_population", {})
        emp_val = emp.get("value", "") if isinstance(emp, dict) else emp
        if isinstance(emp_val, str) and any(
            c in emp_val for c in ["-", "~", "to", "approximately"]
        ):
            contradictions.append(
                {
                    "field": "employee_population",
                    "values_found": emp_val,
                    "severity": "Medium",
                    "recommendation": "Clarify exact headcount with client â€” affects team sizing",
                }
            )

        # Check product count consistency
        if platforms and products:
            if len(platforms) != len(products):
                contradictions.append(
                    {
                        "field": "products_vs_platforms",
                        "values_found": f"{len(products)} products extracted but {len(platforms)} platform details found",
                        "severity": "High",
                        "recommendation": "Reconcile product list with platform details â€” affects scope and commercial",
                    }
                )

        if contradictions:
            summary += f" {len(contradictions)} contradictions detected."
            self.log(
                "contradictions_detected",
                {
                    "count": len(contradictions),
                    "fields": [c["field"] for c in contradictions],
                },
            )

        # â”€â”€ Validated Facts Repository â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Single source of truth consumed by ALL downstream agents via get_validated_facts()
        validated_facts = {
            "platform_count": len(platforms),
            "integration_count": len(integrations),
            "sla_count": len(slas),
            "products": products,
            "employee_count": emp_val,
            "contract_type": contract_type,
            "geographies": geographies,
            "geo_count": len(geographies),
            "evaluation_criteria": result.get("evaluation_criteria", {}).get(
                "value", {}
            ),
            "mandatory_certs": result.get("certifications_required", {}).get(
                "value", []
            ),
            "budget_indicators": result.get("budget_indicators", {}).get("value", ""),
            "incumbent_name": result.get("incumbent_signals", {}).get("incumbent_name"),
        }
        self.log("validated_facts_built", validated_facts)

        return {
            "extracted_fields": result,
            "narrative": narrative,
            "platform_details": platforms,
            "integration_inventory": integrations,
            "kpi_sla_table": slas,
            "scope_sections": scopes,
            "low_confidence_fields": low_confidence,
            "disqualifiers": disqualifiers,
            "ambiguities": ambiguities,
            "contradictions": contradictions,
            "validated_facts": validated_facts,
            "hitl_summary": summary,
            "rfp_index": rfp_index,
        }
