"""
Transition & Change Management Agent â€” Transition planning, knowledge transfer,
cutover strategy, stakeholder change management, governance (RACI), wave rollout,
and communication workflows.
Zero hardcoded values â€” everything from RFP and knowledge base.
"""

from typing import Any, Dict
from app.agents.base import BaseAgent


class TransitionChangeAgent(BaseAgent):
    name = "Transition & Change Management Agent"
    agent_tier = (
        "critical"  # 4 deep LLM calls, multi-phase planning, needs sustained quality
    )

    async def observe(self) -> Dict[str, Any]:
        intake = self.manifest.get("intake_output", {})

        # Pull KB data for transition topics
        kb_context = await self.get_kb_context(
            "transition change management knowledge transfer cutover parallel run RACI governance",
            collections=["knowledge_base", "rfps", "case_studies", "sows"],
        )

        # Extract key fields from intake
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

        scope_output = self.manifest.get("scope_output", {})
        solution_output = self.manifest.get("solution_output", {})

        return {
            "rfp_text": self.get_rfp_sections("transition_change"),
            "kb_context": kb_context,
            "intake": intake,
            "scope": scope_output,
            "solution": solution_output,
            "client": self.manifest.get("client", {}),
            "geographies": geographies,
            "contract_type": contract_type,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Split analysis into three focused LLM calls to avoid truncation."""
        kb_section = ""
        if obs.get("kb_context"):
            kb_section = f"\n{obs['kb_context']}\nUse best practices.\n"

        geo_context = (
            f"\nGeographies: {', '.join(obs.get('geographies', []))}\n"
            if obs.get("geographies")
            else ""
        )
        ct_context = f"\nContract Type: {obs.get('contract_type', 'Unknown')}\n"

        # Wire scope builder's transition timeline and team model
        scope_context = ""
        scope = obs.get("scope", {})
        if scope and isinstance(scope, dict):
            sp = scope.get("scope_package", scope)
            if isinstance(sp, dict):
                tw = sp.get("transition_weeks", 0)
                team = sp.get("team_model", [])
                products = sp.get("products_in_scope", [])
                total_fte = sum(r.get("count", 0) for r in team if isinstance(r, dict))
                scope_context = (
                    "\n=== SCOPE BUILDER CONTEXT (align transition with these) ===\n"
                )
                scope_context += f"Transition Duration from Scope: {tw} weeks\n"
                scope_context += f"Products in Scope: {', '.join(products)}\n"
                scope_context += f"Team Size: {total_fte} FTEs\n"
                if team:
                    scope_context += "Team Roles:\n"
                    for r in team[:10]:
                        if isinstance(r, dict):
                            scope_context += f"  - {r.get('role', '?')}: {r.get('count', 1)} FTEs ({r.get('location', 'offshore')})\n"
                scope_context += f"\nIMPORTANT: Your transition timeline should be AT LEAST {tw} weeks. "
                scope_context += "The scope builder already calculated this from the RFP. Build your phases around this duration.\n"

        rfp_text = obs["rfp_text"]

        # â”€â”€ CALL 1: Transition Plan â€” phases, KT, parallel run, cutover â”€â”€
        prompt_transition = f"""Analyze this RFP for transition and service takeover requirements.

RULES:
- Cite specific RFP sections where possible
- Phases must have clear start/end weeks and durations
- Knowledge transfer must include shadow periods and reverse KT
- All values must come from RFP context â€” do NOT hardcode
{ct_context}{geo_context}{scope_context}

=== RFP DOCUMENT ===
{rfp_text}
{kb_section}

Return JSON with EXACTLY this structure:
{{
  "transition_plan": {{
    "approach": "brief description of overall transition strategy",
    "total_duration_weeks": 0,
    "phases": [
      {{
        "phase_number": 1,
        "phase_name": "Phase Name",
        "start_week": 1,
        "end_week": 4,
        "duration_weeks": 4,
        "objectives": ["objective 1", "objective 2"],
        "deliverables": ["deliverable 1", "deliverable 2"],
        "exit_criteria": ["criterion 1"],
        "risks": ["risk 1"]
      }}
    ],
    "knowledge_transfer": {{
      "approach": "KT methodology",
      "kt_waves": 0,
      "shadow_period_weeks": 0,
      "reverse_kt_weeks": 0,
      "kt_topics": ["topic 1", "topic 2"]
    }},
    "parallel_run": {{
      "duration_weeks": 0,
      "sla_grace_period": "description",
      "go_live_criteria": ["criterion 1", "criterion 2"]
    }},
    "cutover_plan": {{
      "approach": "big-bang|phased|pilot",
      "rollback_plan": "description",
      "service_continuity_measures": ["measure 1"]
    }}
  }}
}}

Minimum 3 phases. Each objective and deliverable should be specific and measurable.
Align transition timeline with the scope builder's duration if provided above."""

        transition = await self.llm_json(prompt_transition, max_tokens=5000)
        self.log(
            "transition_plan_extracted",
            {
                "phases": len(transition.get("transition_plan", {}).get("phases", [])),
                "duration": transition.get("transition_plan", {}).get(
                    "total_duration_weeks", 0
                ),
            },
        )

        # â”€â”€ CALL 2: Change Management â€” stakeholders, training, communications â”€â”€
        prompt_change = f"""Analyze this RFP for change management requirements: stakeholder analysis,
training needs, communication planning, and success metrics.
{ct_context}{geo_context}

=== RFP DOCUMENT ===
{rfp_text}

Return JSON with EXACTLY this structure:
{{
  "change_management": {{
    "stakeholder_groups": [
      {{
        "group": "stakeholder group name",
        "impact_level": "high|medium|low",
        "change_readiness": "ready|needs_support|resistant",
        "key_concerns": ["concern 1"],
        "key_messages": ["message 1"],
        "engagement_approach": "approach description"
      }}
    ],
    "communication_plan": [
      {{
        "audience": "target audience",
        "channel": "email|meetings|portal|town-hall",
        "frequency": "weekly|bi-weekly|monthly|as-needed",
        "owner": "role responsible",
        "content_focus": "what is communicated"
      }}
    ],
    "training_plan": [
      {{
        "training_topic": "topic name",
        "target_audience": "who",
        "delivery_method": "virtual|in-person|self-paced|hybrid",
        "duration": "duration",
        "timing": "when in transition"
      }}
    ],
    "success_metrics": [
      {{
        "metric": "metric name",
        "target": "target value",
        "measurement_method": "how measured"
      }}
    ]
  }}
}}

Minimum 4 stakeholder groups, 4 communication channels, 4 training topics.
Training plans should include prerequisites and success criteria.
Success metrics must have specific numerical targets."""

        change = await self.llm_json(prompt_change, max_tokens=4500)
        self.log(
            "change_management_extracted",
            {
                "stakeholders": len(
                    change.get("change_management", {}).get("stakeholder_groups", [])
                ),
                "training": len(
                    change.get("change_management", {}).get("training_plan", [])
                ),
            },
        )

        # â”€â”€ CALL 3: Governance â€” RACI, milestones, escalation, wave rollout â”€â”€
        prompt_governance = f"""Analyze this RFP for governance structure, RACI matrix, milestone checkpoints,
escalation framework, and wave rollout strategy.
{ct_context}{geo_context}

=== RFP DOCUMENT ===
{rfp_text}

Return JSON with EXACTLY this structure:
{{
  "governance_model": {{
    "raci_matrix": [
      {{
        "activity": "activity description",
        "responsible": "role",
        "accountable": "role",
        "consulted": "role",
        "informed": "role"
      }}
    ],
    "milestone_checkpoints": [
      {{
        "milestone": "milestone name",
        "target_week": 0,
        "go_no_go": true,
        "criteria": ["criterion 1"]
      }}
    ],
    "escalation_matrix": [
      {{
        "level": "L1|L2|L3",
        "trigger": "escalation trigger",
        "owner": "role",
        "response_time": "SLA"
      }}
    ],
    "steering_committee": {{
      "frequency": "weekly|bi-weekly|monthly",
      "members": ["role 1", "role 2"],
      "charter": "brief charter description"
    }}
  }},
  "wave_rollout": [
    {{
      "wave": 1,
      "scope": "wave scope description",
      "start_week": 0,
      "end_week": 0,
      "geographies": ["geography"],
      "platforms": ["platform"]
    }}
  ],
  "transition_risks": [
    {{
      "risk": "risk description",
      "likelihood": "high|medium|low",
      "impact": "high|medium|low",
      "mitigation": "mitigation strategy",
      "owner": "role"
    }}
  ]
}}

Minimum 8 RACI activities, 4 milestones, 5 risks.
Risks must include specific mitigation strategies with owner roles and response timelines.
Wave rollout must align with scope builder's platforms and geographies."""

        governance = await self.llm_json(prompt_governance, max_tokens=4500)
        self.log(
            "governance_extracted",
            {
                "raci": len(
                    governance.get("governance_model", {}).get("raci_matrix", [])
                ),
                "milestones": len(
                    governance.get("governance_model", {}).get(
                        "milestone_checkpoints", []
                    )
                ),
                "risks": len(governance.get("transition_risks", [])),
            },
        )

        # Merge all three results
        merged = {**transition, **change, **governance}
        return merged

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        tp = decision.get("transition_plan", {})
        cm = decision.get("change_management", {})
        gov = decision.get("governance_model", {})
        waves = decision.get("wave_rollout", [])
        risks = decision.get("transition_risks", [])

        phases = tp.get("phases", [])
        kt = tp.get("knowledge_transfer", {})
        stakeholders = cm.get("stakeholder_groups", [])
        raci = gov.get("raci_matrix", [])
        milestones = gov.get("milestone_checkpoints", [])
        training = cm.get("training_plan", [])

        high_risks = len(
            [
                r
                for r in risks
                if r.get("likelihood") == "high" or r.get("impact") == "high"
            ]
        )

        prompt = f"""Write a concise transition and change management assessment (200-250 words max).

STYLE: Strategic consulting language. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive.

TRANSITION DATA:
Duration: {tp.get("total_duration_weeks", 0)} weeks across {len(phases)} phases
KT Waves: {kt.get("kt_waves", 0)} | Shadow: {kt.get("shadow_period_weeks", 0)}w | Reverse KT: {kt.get("reverse_kt_weeks", 0)}w
Parallel Run: {tp.get("parallel_run", {}).get("duration_weeks", 0)} weeks
Stakeholder Groups: {len(stakeholders)} | Training Programs: {len(training)}
RACI Activities: {len(raci)} | Milestones: {len(milestones)} ({len([m for m in milestones if m.get("go_no_go")])} Go/No-Go)
Rollout Waves: {len(waves)}
Risks: {len(risks)} identified ({high_risks} high-impact)

Write 4 tight paragraphs:
1. Transition strategy â€” overall approach, phasing, duration, key dependencies.
2. Knowledge transfer â€” KT methodology, shadow periods, parallel run strategy.
3. Change management â€” stakeholder analysis, communication approach, training plan, success metrics.
4. Governance â€” RACI highlights, milestone checkpoints, risk assessment, wave rollout strategy."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"{tp.get('total_duration_weeks', 0)}-week transition across {len(phases)} phases. "
        summary += f"{kt.get('kt_waves', 0)} KT waves, {tp.get('parallel_run', {}).get('duration_weeks', 0)}w parallel run. "
        summary += (
            f"{len(stakeholders)} stakeholder groups, {len(raci)} RACI activities. "
        )
        summary += f"{len(risks)} risks ({high_risks} high-impact)."

        # === CLOSED-LOOP: Capture learnings for institutional improvement ===
        if phases:
            self.capture_learning(
                learning_type="transition_pattern",
                insight=f"{tp.get('total_duration_weeks', 0)}-week transition, {len(phases)} phases, "
                f"{kt.get('kt_waves', 0)} KT waves, {len(stakeholders)} stakeholder groups. "
                f"{len(risks)} risks ({high_risks} high-impact). "
                f"Cutover: {tp.get('cutover_plan', {}).get('approach', 'phased')}.",
                confidence=0.7,
            )

        return {
            "transition_plan": tp,
            "change_management": cm,
            "governance_model": gov,
            "wave_rollout": waves,
            "transition_risks": risks,
            "narrative": narrative,
            "hitl_summary": summary,
        }
