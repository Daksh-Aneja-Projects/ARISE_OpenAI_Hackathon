"""
QA Agent â€” Cross-document validation, consistency checks, readability scoring.
Combines REAL programmatic checks with LLM quality review.
Checks completeness against actual RFP requirements, not generic criteria.
"""

import re
from typing import Any, Dict, List
from app.agents.base import BaseAgent


def flesch_reading_ease(text: str) -> float:
    """Calculate Flesch Reading Ease score for executive summary quality."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    words = text.split()
    if not sentences or not words:
        return 0.0
    syllable_count = 0
    for word in words:
        word = word.lower().strip(".,!?;:'\"()-")
        if not word:
            continue
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for i in range(1, len(word)):
            if word[i] in vowels and word[i - 1] not in vowels:
                count += 1
        if word.endswith("e") and count > 1:
            count -= 1
        syllable_count += max(count, 1)
    asl = len(words) / max(len(sentences), 1)
    asw = syllable_count / max(len(words), 1)
    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return round(max(0, min(100, score)), 1)


def check_cross_doc_consistency(manifest: dict) -> List[Dict[str, Any]]:
    """Programmatic cross-document checks â€” no LLM needed."""
    issues = []

    # Check 1: TCV consistency
    commercial = manifest.get("commercial_output", {})
    if isinstance(commercial, dict):
        pl = commercial.get("pl_model", {})
        if isinstance(pl, dict):
            tcv = pl.get("revenue", {}).get("total_contract_value")
            margin = pl.get("profitability", {}).get("margin_percent")
            if tcv and tcv < 10000:
                issues.append(
                    {
                        "check": "TCV Sanity",
                        "status": "fail",
                        "detail": f"TCV ${tcv:,.0f} seems unrealistically low",
                    }
                )
            elif tcv:
                issues.append(
                    {
                        "check": "TCV Sanity",
                        "status": "pass",
                        "detail": f"TCV ${tcv:,.0f} within reasonable range",
                    }
                )
            if margin and margin < 12:
                issues.append(
                    {
                        "check": "Margin Floor",
                        "status": "fail",
                        "detail": f"Margin {margin:.1f}% below 12% minimum",
                    }
                )
            elif margin and margin < 18:
                issues.append(
                    {
                        "check": "Margin Floor",
                        "status": "warn",
                        "detail": f"Margin {margin:.1f}% below 18% standard",
                    }
                )
            elif margin:
                issues.append(
                    {
                        "check": "Margin Floor",
                        "status": "pass",
                        "detail": f"Margin {margin:.1f}% within guidelines",
                    }
                )

    # Check 2: Scope effort vs commercial headcount
    scope = manifest.get("scope_output", {})
    if isinstance(scope, dict) and isinstance(commercial, dict):
        scope_pkg = scope.get("scope_package", scope)
        scope_team = (
            scope_pkg.get("team_model", []) if isinstance(scope_pkg, dict) else []
        )
        if isinstance(scope_team, dict):
            scope_team = scope_team.get("key_roles", [])
        comm_resources = commercial.get("resource_plan", [])
        scope_fte = sum(r.get("count", 0) for r in scope_team if isinstance(r, dict))
        comm_fte = sum(r.get("count", 0) for r in comm_resources if isinstance(r, dict))
        if scope_fte > 0 and comm_fte > 0:
            deviation = abs(scope_fte - comm_fte) / max(scope_fte, comm_fte) * 100
            if deviation > 30:
                issues.append(
                    {
                        "check": "Headcount Consistency",
                        "status": "fail",
                        "detail": f"Scope proposes {scope_fte:.0f} FTEs, Commercial models {comm_fte:.0f} FTEs â€” {deviation:.0f}% deviation",
                    }
                )
            else:
                issues.append(
                    {
                        "check": "Headcount Consistency",
                        "status": "pass",
                        "detail": f"Scope ({scope_fte:.0f}) and Commercial ({comm_fte:.0f}) aligned within {deviation:.0f}%",
                    }
                )

    # Check 3: All agents have outputs
    expected_agents = [
        "intake_output",
        "scope_output",
        "solution_output",
        "commercial_output",
        "compliance_output",
        "competitive_output",
    ]
    missing = [
        a.replace("_output", "").title() for a in expected_agents if not manifest.get(a)
    ]
    if missing:
        issues.append(
            {
                "check": "Pipeline Completeness",
                "status": "fail",
                "detail": f"Missing: {', '.join(missing)}",
            }
        )
    else:
        issues.append(
            {
                "check": "Pipeline Completeness",
                "status": "pass",
                "detail": "All core agent outputs present",
            }
        )

    # Check 4: Products consistency
    intake = manifest.get("intake_output", {})
    if isinstance(intake, dict):
        intake_products = intake.get("extracted_fields", {}).get("products", {})
        if isinstance(intake_products, dict):
            intake_products = intake_products.get("value", [])
        if intake_products:
            issues.append(
                {
                    "check": "Products Identified",
                    "status": "pass",
                    "detail": f"Products: {', '.join(intake_products[:5])}",
                }
            )

    return issues


class QAAgent(BaseAgent):
    name = "QA Agent"
    agent_tier = "analytical"  # Mostly programmatic checks, LLM portion is lightweight

    async def observe(self) -> Dict[str, Any]:
        self.manifest.get("rfp_text", "")
        all_outputs = {}
        for key in [
            "intake_output",
            "scope_output",
            "solution_output",
            "competitive_output",
            "commercial_output",
            "compliance_output",
            "automation_ai_output",
        ]:
            val = self.manifest.get(key)
            if val:
                all_outputs[key] = val

        structural_checks = check_cross_doc_consistency(self.manifest)
        readability_scores = {}
        for key, val in all_outputs.items():
            if isinstance(val, dict):
                narrative = val.get("narrative", "")
                if narrative and len(narrative) > 100:
                    readability_scores[key] = flesch_reading_ease(narrative)

        return {
            "rfp_text": self.get_rfp_sections("qa"),
            "agent_outputs": all_outputs,
            "structural_checks": structural_checks,
            "readability_scores": readability_scores,
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        # Use hitl_summaries (concise) not full narratives
        outputs_summary = ""
        for k, v in obs["agent_outputs"].items():
            if isinstance(v, dict):
                summary = v.get("hitl_summary", "")
                outputs_summary += f"\n{k}: {summary}\n"

        checks_text = "\n=== AUTOMATED CHECKS ===\n"
        for c in obs["structural_checks"]:
            icon = (
                "PASS"
                if c["status"] == "pass"
                else "WARN"
                if c["status"] == "warn"
                else "FAIL"
            )
            checks_text += f"[{icon}] {c['check']}: {c['detail']}\n"

        readability_text = "\n=== READABILITY ===\n"
        for k, score in obs.get("readability_scores", {}).items():
            status = (
                "OK" if score >= 65 else "NEEDS WORK" if score >= 50 else "TOO COMPLEX"
            )
            readability_text += f"{k}: {score}/100 ({status})\n"

        prompt = f"""QA review of bid response against RFP requirements.

RULES:
- Check completeness against RFP mandatory sections
- Verify consistency between agent outputs
- Ensure no internal content exposed

=== RFP (abbreviated) ===
{obs["rfp_text"][:4000]}

=== AGENT OUTPUTS ===
{outputs_summary[:2500]}
{checks_text}
{readability_text}

Return JSON:
{{
  "rfp_requirements_coverage": [
    {{"requirement": "RFP req", "rfp_section": "ref", "status": "covered|partial|missing", "covered_by": "agent"}}
  ],
  "consistency_checks": [
    {{"check": "what compared", "status": "pass|fail|warn", "detail": "finding"}}
  ],
  "quality_scores": {{
    "completeness": 0-100,
    "consistency": 0-100,
    "accuracy": 0-100,
    "compliance": 0-100,
    "quality": 0-100,
    "overall": 0-100
  }},
  "critical_fixes": ["must-fix items"],
  "improvements": ["recommended improvements"],
  "brand_check": {{"pass": true, "issues": ["any internal content exposed"]}},
  "overall_readiness": "Ready|Needs Work|Not Ready"
}}"""
        return await self.llm_json(prompt)

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        return orientation

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        scores = decision.get("quality_scores", {})
        coverage = decision.get("rfp_requirements_coverage", [])
        covered = len([r for r in coverage if r.get("status") == "covered"])
        partial = len([r for r in coverage if r.get("status") == "partial"])
        missing = len([r for r in coverage if r.get("status") == "missing"])
        overall = scores.get("overall", 0)
        readiness = decision.get("overall_readiness", "Unknown")
        critical = decision.get("critical_fixes", [])

        prompt = f"""Write a concise quality assessment (150-200 words max).

STYLE: Formal QA assessment language. No markdown. No bullets. No asterisks. Flowing paragraphs. Decisive.

QA DATA:
Readiness: {readiness} | Score: {overall}/100
Scores: Completeness {scores.get("completeness", 0)} | Consistency {scores.get("consistency", 0)} | Accuracy {scores.get("accuracy", 0)} | Compliance {scores.get("compliance", 0)} | Quality {scores.get("quality", 0)}
Coverage: {covered} covered, {partial} partial, {missing} missing out of {covered + partial + missing}
Critical Fixes: {len(critical)} â€” {critical[:3]}

Write 3 tight paragraphs:
1. Readiness verdict â€” score, primary quality drivers, dimension breakdown.
2. Coverage gaps â€” what's missing, which agent outputs need strengthening.
3. Critical fixes â€” must-do items before submission, in priority order."""

        narrative = await self.llm_generate(prompt, max_tokens=1500)

        summary = f"QA: {readiness} ({overall}/100). "
        summary += (
            f"RFP coverage: {covered} covered, {partial} partial, {missing} missing. "
        )
        if critical:
            summary += f"{len(critical)} critical fixes."

        # Use structural checks from observe phase stored in manifest context
        structural_checks = check_cross_doc_consistency(self.manifest)
        readability_scores = {}
        for key in [
            "intake_output",
            "scope_output",
            "solution_output",
            "competitive_output",
            "commercial_output",
            "compliance_output",
        ]:
            val = self.manifest.get(key)
            if isinstance(val, dict):
                narr = val.get("narrative", "")
                if narr and len(narr) > 100:
                    readability_scores[key] = flesch_reading_ease(narr)

        # === CLOSED-LOOP: Capture learnings for institutional improvement ===
        self.capture_learning(
            learning_type="qa_pattern",
            insight=f"QA verdict: {readiness} ({overall}/100). "
            f"Coverage: {covered} covered, {partial} partial, {missing} missing. "
            f"{len(critical)} critical fixes required.",
            confidence=0.8,
        )
        if missing > 0:
            missing_items = [
                r.get("requirement", "?")
                for r in coverage
                if r.get("status") == "missing"
            ][:3]
            self.capture_learning(
                learning_type="coverage_gap",
                insight=f"{missing} RFP requirements not covered: {', '.join(missing_items)}. "
                "Ensure upstream agents address these requirements in future bids.",
                confidence=0.9,
            )

        return {
            "qa_scores": decision,
            "structural_checks": structural_checks,
            "readability_scores": readability_scores,
            "narrative": narrative,
            "hitl_summary": summary,
        }
