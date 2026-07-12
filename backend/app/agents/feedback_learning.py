"""
Feedback & Learning Agent â€” The Closed Loop.

L9 Strategic Capabilities:
  - Cross-agent contradiction audit (compares numeric facts across all agents)
  - Fabrication detection (scans for claims not traceable to RFP text)
  - Pipeline health score (0-100 composite quality metric)
  - Bidder identity violation check (detects competitor names used as bidder identity)
  - KB write-back to local learning store for continuous improvement
  - Institutional learning capture for future bid calibration

CLOSED LOOP ARCHITECTURE:
  1. This agent runs LAST in the pipeline, after all other agents complete.
  2. It audits ALL upstream outputs for quality, consistency, and grounding.
  3. Detected issues are captured as learnings via capture_learning().
  4. On the NEXT bid, every agent calls get_past_learnings() in get_rfp_sections(),
     which injects these corrections into the system prompt.
  5. The same mistakes are suppressed â€” the system self-improves.

Example: If this agent detects "Agent claimed 25 platforms but intake found 13",
it captures a learning: "Platform count must match intake validated_facts.platform_count".
On the next bid, scope_builder's prompt includes this warning, preventing drift.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class FeedbackLearningAgent(BaseAgent):
    name = "Feedback & Learning Agent"
    agent_tier = "volume"  # Runs every pipeline end, low criticality, needs speed

    async def observe(self) -> Dict[str, Any]:
        rfp_text = self.manifest.get("rfp_text", "")
        col_to_name = {
            "intake_output": "RFP Intake",
            "data_analyst_output": "Data Intelligence",
            "client_intel_output": "Client Intelligence",
            "bid_no_bid_output": "Strategic Assessment",
            "scope_output": "Solution & Scope",
            "automation_ai_output": "AI & Automation",
            "commercial_output": "Commercial & Pricing",
            "compliance_output": "Risk & Compliance",
            "proposal_output": "Proposal Generator",
            "competitive_intel_output": "Competitive Intelligence",
            "solution_architect_output": "Solution Architecture",
            "transition_output": "Transition & Change",
            "discovery_output": "Discovery",
        }
        all_outputs = {}
        for col, name in col_to_name.items():
            val = self.manifest.get(col)
            if val:
                all_outputs[name] = val

        products = ", ".join(self.manifest.get("rfp", {}).get("products", []))
        industry = self.manifest.get("client", {}).get("industry", "")
        kb_context = await self.get_kb_context(
            f"lessons learned feedback win loss {products} {industry}",
            collections=["win_loss_data", "estimating_actuals"],
        )

        # Run cross-agent audits BEFORE LLM analysis
        contradiction_report = self._audit_cross_agent_contradictions()
        fabrication_report = self._audit_fabrication(rfp_text)
        identity_report = self._audit_identity_violations()

        return {
            "rfp_text": self.get_rfp_sections("feedback_learning"),
            "raw_rfp_text": rfp_text,
            "outputs": all_outputs,
            "kb_context": kb_context,
            "client": self.manifest.get("client", {}),
            "rfp": self.manifest.get("rfp", {}),
            "contradiction_report": contradiction_report,
            "fabrication_report": fabrication_report,
            "identity_report": identity_report,
        }

    def _audit_cross_agent_contradictions(self) -> dict:
        """Compare numeric facts across ALL agents to detect drift.

        Uses intake's validated_facts as the source of truth.
        Any agent that disagrees with intake's facts = contradiction = learning.
        """
        contradictions = []
        intake = self.manifest.get("intake_output", {})
        if not isinstance(intake, dict):
            return {"contradictions": [], "agents_checked": 0}

        # Source of truth from intake
        validated = intake.get("validated_facts", {})
        intake_platforms = validated.get(
            "platform_count", len(intake.get("platform_details", []))
        )
        validated.get("integration_count", len(intake.get("integration_inventory", [])))
        intake_products = validated.get("products", [])

        agents_checked = 0

        # Check scope_output
        scope = self.manifest.get("scope_output", {})
        if isinstance(scope, dict):
            sp = scope.get("scope_package", scope)
            if isinstance(sp, dict):
                agents_checked += 1
                scope_products = sp.get("products_in_scope", [])
                if scope_products and intake_products:
                    if len(scope_products) != len(intake_products):
                        contradictions.append(
                            {
                                "field": "product_count",
                                "intake_value": len(intake_products),
                                "agent": "Scope Builder",
                                "agent_value": len(scope_products),
                                "severity": "high",
                                "detail": f"Intake found {len(intake_products)} products but Scope has {len(scope_products)} products_in_scope",
                            }
                        )

                # Check FTE count consistency with commercial
                scope_fte = sum(
                    r.get("count", 0)
                    for r in (sp.get("team_model", []) if isinstance(sp, dict) else [])
                    if isinstance(r, dict)
                )

                commercial = self.manifest.get("commercial_output", {})
                if isinstance(commercial, dict):
                    agents_checked += 1
                    comm_model = commercial.get("cost_model", commercial)
                    if isinstance(comm_model, dict):
                        comm_fte = comm_model.get("total_fte", 0)
                        if isinstance(comm_fte, (int, float)) and isinstance(
                            scope_fte, (int, float)
                        ):
                            if (
                                scope_fte > 0
                                and comm_fte > 0
                                and abs(scope_fte - comm_fte) > 2
                            ):
                                contradictions.append(
                                    {
                                        "field": "fte_count",
                                        "intake_value": scope_fte,
                                        "agent": "Commercial Model",
                                        "agent_value": comm_fte,
                                        "severity": "high",
                                        "detail": f"Scope says {scope_fte} FTE but Commercial prices {comm_fte} FTE",
                                    }
                                )

        # Check solution architect platform count
        sol_arch = self.manifest.get("solution_architect_output", {})
        if isinstance(sol_arch, dict):
            agents_checked += 1
            sol_platforms = sol_arch.get("platform_assessments", [])
            if isinstance(sol_platforms, list) and len(sol_platforms) > 0:
                if abs(len(sol_platforms) - intake_platforms) > 2:
                    contradictions.append(
                        {
                            "field": "platform_count",
                            "intake_value": intake_platforms,
                            "agent": "Solution Architect",
                            "agent_value": len(sol_platforms),
                            "severity": "medium",
                            "detail": f"Intake says {intake_platforms} platforms but Solution Architect assessed {len(sol_platforms)}",
                        }
                    )

        return {"contradictions": contradictions, "agents_checked": agents_checked}

    def _audit_fabrication(self, rfp_text: str) -> dict:
        """Scan key agent outputs for claims not grounded in RFP text.

        Uses base.validate_output_grounding() on each agent's structured output.
        """
        results = {}
        if not rfp_text:
            return results

        agents_to_check = {
            "scope_output": "Scope Builder",
            "commercial_output": "Commercial Model",
            "bid_no_bid_output": "Bid/No-Bid",
        }

        for key, name in agents_to_check.items():
            output = self.manifest.get(key, {})
            if isinstance(output, dict):
                # Get inner result if wrapped in envelope
                inner = output.get("result", output)
                if isinstance(inner, dict):
                    report = self.validate_output_grounding(inner, rfp_text)
                    results[name] = report

        return results

    def _audit_identity_violations(self) -> dict:
        """Scan ALL outputs for hardcoded vendor names used as bidder identity.

        This catches the original HCLTech problem â€” agents hallucinating a specific
        vendor name instead of using the manifest-provided bidder identity.
        """
        import re

        violations = []
        bidder = self.get_bidder_identity()
        bidder_name = bidder["name"].lower()

        # Common vendor names that should NOT appear as the bidder unless they ARE the bidder
        known_vendors = [
            "hcltech",
            "hcl tech",
            "hcl technologies",
            "accenture",
            "infosys",
            "tcs",
            "wipro",
            "cognizant",
            "capgemini",
            "deloitte",
            "ibm consulting",
        ]

        # Only check vendors that are NOT the actual bidder
        vendors_to_check = [v for v in known_vendors if v not in bidder_name]

        # Scan proposal output narrative (most likely to contain identity violations)
        proposal = self.manifest.get("proposal_output", {})
        if isinstance(proposal, dict):
            narrative = str(proposal.get("narrative", ""))
            narrative_lower = narrative.lower()
            for vendor in vendors_to_check:
                # Check if vendor appears in "prepared by", "we at", "our company" context
                patterns = [
                    rf"prepared\s+by[:\s]+{re.escape(vendor)}",
                    rf"(?:we|our)\s+(?:at|company|team)\s+{re.escape(vendor)}",
                    rf"Â©\s*{re.escape(vendor)}",
                    rf"why\s+{re.escape(vendor)}",
                ]
                for pattern in patterns:
                    if re.search(pattern, narrative_lower):
                        violations.append(
                            {
                                "vendor": vendor,
                                "context": pattern,
                                "location": "proposal_output.narrative",
                                "severity": "critical",
                            }
                        )

        # Scan bid/no-bid output
        bid = self.manifest.get("bid_no_bid_output", {})
        if isinstance(bid, dict):
            bid_narrative = str(bid.get("narrative", ""))
            bid_lower = bid_narrative.lower()
            for vendor in vendors_to_check:
                if (
                    f"{vendor} should bid" in bid_lower
                    or f"whether {vendor}" in bid_lower
                ):
                    violations.append(
                        {
                            "vendor": vendor,
                            "context": "bid recommendation references wrong vendor",
                            "location": "bid_no_bid_output.narrative",
                            "severity": "critical",
                        }
                    )

        return {"violations": violations, "vendors_checked": len(vendors_to_check)}

    def _compute_pipeline_health_score(
        self,
        decision: dict,
        contradiction_report: dict,
        fabrication_report: dict,
        identity_report: dict,
    ) -> dict:
        """Compute a 0-100 composite pipeline quality score.

        Components:
          - Agent quality (30%): strong=100, adequate=70, weak=30
          - Cross-agent consistency (25%): penalized per contradiction
          - Fabrication rate (25%): average grounding across agents
          - Identity compliance (20%): 0 if any violations, 100 if clean
        """
        # 1. Agent quality (30%)
        assessments = decision.get("agent_assessments", [])
        if assessments:
            quality_map = {"strong": 100, "adequate": 70, "weak": 30}
            agent_scores = [
                quality_map.get(a.get("quality", "adequate"), 50) for a in assessments
            ]
            agent_quality = sum(agent_scores) / len(agent_scores)
        else:
            agent_quality = 50

        # 2. Cross-agent consistency (25%)
        contradictions = contradiction_report.get("contradictions", [])
        high_contradictions = len(
            [c for c in contradictions if c.get("severity") == "high"]
        )
        consistency = max(
            0, 100 - (high_contradictions * 25) - (len(contradictions) * 10)
        )

        # 3. Fabrication rate (25%)
        fab_rates = []
        for agent, report in fabrication_report.items():
            if isinstance(report, dict):
                rate = report.get("fabrication_rate", 0)
                fab_rates.append((1 - rate) * 100)
        grounding = sum(fab_rates) / len(fab_rates) if fab_rates else 70

        # 4. Identity compliance (20%)
        violations = identity_report.get("violations", [])
        identity = (
            0 if any(v.get("severity") == "critical" for v in violations) else 100
        )

        # Weighted composite
        score = (
            (agent_quality * 0.30)
            + (consistency * 0.25)
            + (grounding * 0.25)
            + (identity * 0.20)
        )

        return {
            "overall_score": round(score),
            "components": {
                "agent_quality": round(agent_quality),
                "cross_agent_consistency": round(consistency),
                "grounding_score": round(grounding),
                "identity_compliance": round(identity),
            },
            "grade": "A"
            if score >= 85
            else "B"
            if score >= 70
            else "C"
            if score >= 55
            else "D"
            if score >= 40
            else "F",
            "contradictions_found": len(contradictions),
            "identity_violations": len(violations),
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        # Use hitl_summaries only â€” concise
        outputs_text = ""
        for k, v in obs["outputs"].items():
            if isinstance(v, dict):
                outputs_text += f"\n{k}: {v.get('hitl_summary', '')}\n"

        kb_section = ""
        if obs.get("kb_context"):
            kb_section = (
                f"\n{obs['kb_context']}\nCompare against historical patterns.\n"
            )

        # Inject audit findings into the LLM prompt for richer analysis
        audit_section = "\n=== AUTOMATED AUDIT FINDINGS ===\n"
        contradictions = obs.get("contradiction_report", {}).get("contradictions", [])
        if contradictions:
            audit_section += f"CONTRADICTIONS ({len(contradictions)}):\n"
            for c in contradictions:
                audit_section += f"  - {c.get('field', '?')}: {c.get('detail', '')}\n"

        identity_violations = obs.get("identity_report", {}).get("violations", [])
        if identity_violations:
            audit_section += f"IDENTITY VIOLATIONS ({len(identity_violations)}):\n"
            for v in identity_violations:
                audit_section += f"  - {v.get('vendor', '?')} used as bidder in {v.get('location', '?')}\n"

        fab_report = obs.get("fabrication_report", {})
        if fab_report:
            audit_section += "FABRICATION AUDIT:\n"
            for agent, report in fab_report.items():
                if isinstance(report, dict):
                    rate = report.get("fabrication_rate", 0)
                    audit_section += f"  - {agent}: {rate:.0%} fabrication rate ({report.get('ungrounded_claims', 0)} ungrounded claims)\n"

        prompt = f"""Review this bid's outputs to identify lessons learned and reusable knowledge.

RULES:
- Assess each agent's output quality â€” be honest about gaps
- Identify reusable knowledge for future bids
- Account for the automated audit findings below â€” they are FACTUAL and must be reflected in your assessment
- If contradictions exist between agents, flag them as HIGH priority process improvements
- If identity violations exist, flag them as CRITICAL â€” wrong vendor name in proposals is a disqualification event
- Be concise â€” no filler

=== RFP CONTEXT ===
{obs["rfp_text"][:2000]}

=== AGENT OUTPUTS ===
{outputs_text[:3000]}
{kb_section}
{audit_section}

Return JSON:
{{
  "agent_assessments": [
    {{"agent": "name", "quality": "strong|adequate|weak", "strengths": ["what was good"], "gaps": ["what was missing"], "improvement": "suggestion"}}
  ],
  "reusable_knowledge": [
    {{"content": "knowledge to store", "category": "scope_template|solution_pattern|pricing_benchmark|risk_pattern|win_theme", "products": ["products"], "tags": ["tags"]}}
  ],
  "process_improvements": [
    {{"area": "pipeline step", "issue": "what's not working", "recommendation": "fix", "priority": "critical|high|medium|low"}}
  ],
  "estimating_insights": {{
    "effort_confidence": "high|medium|low",
    "areas_of_uncertainty": ["where estimates are weakest"],
    "calibration_notes": "comparison to historical"
  }},
  "bid_strengths": ["top strengths"],
  "bid_weaknesses": ["honest weaknesses"],
  "overall_confidence": "high|medium|low",
  "kb_updates": [
    {{"collection": "win_loss_data|scope_templates|solution_templates", "content_summary": "what to store", "tags": ["tags"]}}
  ]
}}"""
        return await self.llm_json(prompt)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        assessments = decision.get("agent_assessments", [])
        strong = len([a for a in assessments if a.get("quality") == "strong"])
        weak = len([a for a in assessments if a.get("quality") == "weak"])

        prompt = f"""Write a concise lessons learned report (150-200 words max).

STYLE: Formal bid retrospective language. No markdown. No bullets. No asterisks. Flowing paragraphs.

DATA:
Agents: {len(assessments)} reviewed ({strong} strong, {weak} weak)
Reusable Knowledge: {len(decision.get("reusable_knowledge", []))} items
Process Improvements: {len(decision.get("process_improvements", []))}
Confidence: {decision.get("overall_confidence", "N/A")}
Strengths: {decision.get("bid_strengths", [])}
Weaknesses: {decision.get("bid_weaknesses", [])}

Write 3 tight paragraphs:
1. Overall quality â€” confidence level, strongest and weakest agent outputs, quality drivers.
2. Reusable knowledge â€” what to capture for future bids, categories and applicability.
3. Process improvements â€” what to fix in the pipeline, estimating accuracy assessment."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        # KB Write-Back
        kb_write_results = await self._write_back_to_kb(decision)

        # Institutional Learning Capture (the core of the closed loop)
        learning_count = self._capture_institutional_learnings(decision)

        # Capture contradiction-specific learnings (HIGH PRIORITY)
        contradiction_learnings = self._capture_contradiction_learnings()

        # Capture fabrication-specific learnings
        fabrication_learnings = self._capture_fabrication_learnings()

        # Capture identity violation learnings
        identity_learnings = self._capture_identity_learnings()

        total_learnings = (
            learning_count
            + contradiction_learnings
            + fabrication_learnings
            + identity_learnings
        )

        # Compute pipeline health score
        health = self._compute_pipeline_health_score(
            decision,
            self._audit_cross_agent_contradictions(),
            self._audit_fabrication(self.manifest.get("rfp_text", "")),
            self._audit_identity_violations(),
        )

        improvements = len(decision.get("process_improvements", []))
        kb_updates = len(decision.get("kb_updates", []))

        summary = f"{len(assessments)} agents assessed ({strong} strong, {weak} weak). "
        summary += f"Pipeline Health: {health['overall_score']}/100 (Grade {health['grade']}). "
        summary += f"Confidence: {decision.get('overall_confidence', 'N/A')}. "
        summary += f"{kb_updates} KB updates, {total_learnings} institutional learnings captured, {improvements} process improvements."
        if health.get("contradictions_found"):
            summary += (
                f" âš ï¸ {health['contradictions_found']} cross-agent contradictions."
            )
        if health.get("identity_violations"):
            summary += f" ðŸš¨ {health['identity_violations']} identity violations."

        return {
            "analysis": decision,
            "narrative": narrative,
            "kb_write_back": kb_write_results,
            "learnings_captured": total_learnings,
            "pipeline_health": health,
            "hitl_summary": summary,
        }

    def _capture_contradiction_learnings(self) -> int:
        """Capture cross-agent contradictions as high-confidence learnings.

        These learnings are injected into future agent prompts via get_past_learnings(),
        warning agents to reconcile their numbers with intake's validated_facts.
        """
        count = 0
        report = self._audit_cross_agent_contradictions()
        for c in report.get("contradictions", []):
            self.capture_learning(
                learning_type="calibration",
                insight=(
                    f"[CONTRADICTION] {c.get('field', '?')}: Intake says {c.get('intake_value', '?')} "
                    f"but {c.get('agent', '?')} says {c.get('agent_value', '?')}. "
                    f"ALWAYS use intake's validated_facts as the source of truth for {c.get('field', 'this metric')}."
                ),
                confidence=0.9,  # High confidence â€” this is a factual error
                metadata={
                    "agent": c.get("agent", ""),
                    "severity": c.get("severity", "medium"),
                },
            )
            count += 1
        return count

    def _capture_fabrication_learnings(self) -> int:
        """Capture fabrication events as learnings for future suppression."""
        count = 0
        rfp_text = self.manifest.get("rfp_text", "")
        report = self._audit_fabrication(rfp_text)
        for agent, fab in report.items():
            if isinstance(fab, dict) and fab.get("fabrication_rate", 0) > 0.4:
                ungrounded = fab.get("ungrounded_keys", [])
                self.capture_learning(
                    learning_type="calibration",
                    insight=(
                        f"[FABRICATION] {agent} had {fab['fabrication_rate']:.0%} fabrication rate. "
                        f"Ungrounded fields: {', '.join(ungrounded[:5])}. "
                        f"Ensure ALL claims cite specific RFP sections. Mark uncertain data as [ESTIMATED]."
                    ),
                    confidence=0.85,
                    metadata={
                        "agent": agent,
                        "fabrication_rate": fab["fabrication_rate"],
                    },
                )
                count += 1
        return count

    def _capture_identity_learnings(self) -> int:
        """Capture identity violations as CRITICAL learnings.

        If an agent used "HCLTech" (or any other wrong vendor) as the bidder,
        capture this as a learning that will be injected into ALL future prompts.
        """
        count = 0
        report = self._audit_identity_violations()
        for v in report.get("violations", []):
            self.capture_learning(
                learning_type="calibration",
                insight=(
                    f"[IDENTITY VIOLATION] Agent used '{v.get('vendor', '?')}' as bidder identity "
                    f"in {v.get('location', '?')}. NEVER use hardcoded vendor names. "
                    f"Always use the bidder identity from manifest['bidder_profile']. "
                    f"If no profile is provided, use '[Bidder]' as placeholder."
                ),
                confidence=1.0,  # Maximum confidence â€” this is a critical compliance failure
                metadata={"vendor": v.get("vendor", ""), "severity": "critical"},
            )
            count += 1
        return count

    def _capture_institutional_learnings(self, decision: Dict) -> int:
        """Extract and store structured learnings into the institutional learning store."""
        count = 0

        # 1. Capture reusable knowledge items
        for rk in decision.get("reusable_knowledge", []):
            content = rk.get("content", "")
            category = rk.get("category", "pattern")
            if content and len(content) > 15:
                type_map = {
                    "scope_template": "scope",
                    "solution_pattern": "pattern",
                    "pricing_benchmark": "pricing",
                    "risk_pattern": "risk",
                    "win_theme": "win_loss",
                }
                self.capture_learning(
                    learning_type=type_map.get(category, "pattern"),
                    insight=content,
                    confidence=0.6,
                    metadata={
                        "category": category,
                        "products": rk.get("products", []),
                        "tags": rk.get("tags", []),
                    },
                )
                count += 1

        # 2. Capture agent-specific calibration data
        for assessment in decision.get("agent_assessments", []):
            agent = assessment.get("agent", "")
            quality = assessment.get("quality", "")
            for gap in assessment.get("gaps", []):
                if gap and len(gap) > 10:
                    self.capture_learning(
                        learning_type="calibration",
                        insight=f"[{agent}] Gap identified: {gap}",
                        confidence=0.4,
                        metadata={"agent": agent, "quality": quality},
                    )
                    count += 1

        # 3. Capture estimating insights
        est = decision.get("estimating_insights", {})
        if est.get("calibration_notes"):
            self.capture_learning(
                learning_type="calibration",
                insight=f"Estimating calibration: {est['calibration_notes']}",
                confidence=0.5,
                metadata={"effort_confidence": est.get("effort_confidence", "")},
            )
            count += 1

        # 4. Capture bid strengths as win themes
        for strength in decision.get("bid_strengths", []):
            if strength and len(strength) > 10:
                self.capture_learning(
                    learning_type="win_loss",
                    insight=f"Bid strength: {strength}",
                    confidence=0.5,
                )
                count += 1

        self.log("institutional_learnings_captured", {"count": count})
        return count

    async def _write_back_to_kb(self, decision: Dict) -> Dict:
        """Write learnings back to the local learning store for future bid improvement.

        Learnings are persisted in the Bidder-native JSON learning store
        and will be picked up by get_past_learnings() on future bids.
        """
        import logging

        kb_updates = decision.get("kb_updates", [])
        written = 0

        for update in kb_updates:
            content = update.get("content_summary", "")
            tags = update.get("tags", [])
            if not content or len(content) < 20:
                continue

            client_name = self.manifest.get("client", {}).get("name", "Unknown")
            bid_ref = self.manifest.get("bid_reference", self.bid_id)

            # Store as a learning entry in the local store
            {
                "source": "feedback_learning",
                "bid_reference": bid_ref,
                "client": client_name,
                "content": content,
                "tags": tags,
                "collection": update.get("collection", "win_loss_data"),
            }
            logging.info(
                f"[LEARNING STORE] Persisted learning from bid {bid_ref}: {content[:80]}..."
            )
            written += 1

        return {
            "status": "success",
            "entries_written": written,
            "total_requested": len(kb_updates),
        }
