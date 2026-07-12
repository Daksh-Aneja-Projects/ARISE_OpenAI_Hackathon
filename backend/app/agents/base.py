"""
Base Agent class — all agents inherit from this.
Implements the OODA (Observe-Orient-Decide-Act) loop pattern.

Application-agnostic: bidder identity is injected via manifest["bidder_profile"],
not hardcoded. The closed-loop learning cycle works as follows:
  1. Each agent calls get_past_learnings() in get_rfp_sections() to inject
     historical corrections into its system prompt.
  2. FeedbackLearningAgent runs post-pipeline, audits all outputs, detects
     fabrications and cross-agent contradictions, and writes learnings via
     capture_learning().
  3. On the NEXT bid, step 1 retrieves these learnings — suppressing known
     failure modes (identity hallucination, metric fabrication, etc).
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.services.llm import llm_service


class BaseAgent(ABC):
    """Abstract base for all bid pipeline agents."""

    name: str = "BaseAgent"
    max_retries: int = 3
    agent_tier: Optional[str] = (
        None  # Routing tier: critical | analytical | volume | lightweight
    )

    def __init__(self, bid_id: str, manifest: Dict[str, Any]):
        self.bid_id = bid_id
        self.manifest = manifest
        self.run_id = str(uuid.uuid4())[:8]
        self.logs: list = []
        self.errors: list = []

    def get_upstream_result(self, key: str) -> Dict[str, Any]:
        """Safely retrieve an upstream agent's output from the manifest.

        Agent outputs in the manifest may be stored as either:
          - A raw dict (the result itself)
          - An envelope dict: {status, agent, result, timestamp}
        This method normalises both forms and returns the inner result dict,
        or an empty dict if the key is missing / malformed.
        """
        val = self.manifest.get(key)
        if not val or not isinstance(val, dict):
            return {}
        # If it looks like an envelope, unwrap the inner 'result'
        if "result" in val and "status" in val:
            inner = val.get("result")
            return inner if isinstance(inner, dict) else {}
        return val

    def log(self, event: str, data: Any = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.name,
            "event": event,
            "data": data,
        }
        self.logs.append(entry)

    async def run(self) -> Dict[str, Any]:
        """Execute the OODA loop with retry logic."""
        self.log("agent_started")
        for attempt in range(1, self.max_retries + 1):
            try:
                # OBSERVE — gather inputs and context
                self.log("observe_phase")
                observations = await self.observe()

                # ORIENT — analyze and frame the situation
                self.log("orient_phase")
                orientation = await self.orient(observations)

                # DECIDE — determine the course of action
                self.log("decide_phase")
                decision = await self.decide(orientation)

                # ACT — produce outputs
                self.log("act_phase")
                result = await self.act(decision)

                self.log("agent_completed", {"attempt": attempt})

                # Record agent telemetry
                try:
                    from app.telemetry import telemetry as _tel

                    _tel.record_agent_call(self.name, bid_id=self.bid_id, success=True)
                except Exception:
                    pass

                # Auto-audit successful completion
                try:
                    from app.api.audit import log_event

                    log_event(
                        event_type="agent_completed",
                        event_detail=f"Agent '{self.name}' completed successfully",
                        bid_id=self.bid_id,
                        agent_name=self.name,
                        user_name="System",
                    )
                except Exception as e:
                    print(f"Audit log failed: {e}")

                return {
                    "status": "success",
                    "agent": self.name,
                    "run_id": self.run_id,
                    "result": result,
                    "logs": self.logs,
                }
            except Exception as e:
                self.log("agent_error", {"attempt": attempt, "error": str(e)})
                self.errors.append(str(e))
                if attempt == self.max_retries:
                    # Record agent failure telemetry
                    try:
                        from app.telemetry import telemetry as _tel

                        _tel.record_agent_call(
                            self.name, bid_id=self.bid_id, success=False
                        )
                    except Exception:
                        pass
                    # Auto-audit failure
                    try:
                        from app.api.audit import log_event

                        log_event(
                            event_type="agent_failed",
                            event_detail=f"Agent '{self.name}' failed: {str(e)}",
                            bid_id=self.bid_id,
                            agent_name=self.name,
                            user_name="System",
                        )
                    except Exception as err:
                        print(f"Audit log failed: {err}")

                    return {
                        "status": "failed",
                        "agent": self.name,
                        "run_id": self.run_id,
                        "errors": self.errors,
                        "logs": self.logs,
                    }

    @abstractmethod
    async def observe(self) -> Dict[str, Any]:
        """OBSERVE: Gather all inputs, context, and KB data needed."""
        pass

    @abstractmethod
    async def orient(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """ORIENT: Analyze observations, identify patterns, frame the problem."""
        pass

    @abstractmethod
    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Determine the course of action based on orientation."""
        pass

    @abstractmethod
    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """ACT: Execute the decision and produce outputs."""
        pass

    @staticmethod
    def clean_narrative(text: str) -> str:
        """Strip markdown formatting and thinking blocks from LLM output."""
        import re

        # Strip Qwen-3 / DeepSeek thinking blocks that consume token budget
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Remove markdown headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Remove bold/italic markers
        text = text.replace("**", "").replace("__", "")
        text = re.sub(r"(?<!\w)\*(?!\s)", "", text)
        text = re.sub(r"(?<!\s)\*(?!\w)", "", text)
        # Remove markdown bullet markers, keep the text
        text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
        # Remove numbered list markdown
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
        # Clean up multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def clean_rfp_noise(text: str) -> str:
        """Strip PDF-parsing artifacts from RFP text before indexing.

        Removes: IP addresses, repeated page headers/footers, watermarks,
        control characters, and other noise that pollutes the knowledge index.
        """
        import re

        # Strip IPv4 addresses (e.g. "192.168.1.1" or "10.0.0.1")
        text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "", text)
        # Strip page number markers ("Page 1 of 50", "Page 12", "- 3 -")
        text = re.sub(r"\bPage\s+\d+\s*(of\s*\d+)?\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*-\s*\d+\s*-\s*$", "", text, flags=re.MULTILINE)
        # Strip common watermark patterns ("CONFIDENTIAL", "DRAFT", "DO NOT COPY")
        text = re.sub(
            r"^\s*(CONFIDENTIAL|DRAFT|DO NOT COPY|INTERNAL USE ONLY)\s*$",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        # Strip repeated header/footer lines (lines appearing 3+ times across the doc)
        lines = text.split("\n")
        if len(lines) > 20:
            from collections import Counter

            line_counts = Counter(
                line.strip() for line in lines if len(line.strip()) > 5
            )
            repeat_threshold = max(3, len(lines) // 30)  # ~3% of doc or min 3
            repeats = {
                line for line, count in line_counts.items() if count >= repeat_threshold
            }
            if repeats:
                lines = [line for line in lines if line.strip() not in repeats]
                text = "\n".join(lines)
        # Strip control characters and null bytes
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        # Clean up excessive whitespace from removals
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_bidder_identity(self) -> dict:
        """Retrieve bidder identity from manifest — never hardcoded.

        Returns a dict with keys: name, tagline, domain.
        Falls back to a generic "Enterprise IT Services Provider" identity
        so agents never hallucinate a specific vendor name.
        """
        profile = self.manifest.get("bidder_profile", {})
        if isinstance(profile, dict) and profile.get("name"):
            return {
                "name": profile["name"],
                "tagline": profile.get("tagline", "Enterprise Technology Services"),
                "domain": profile.get("domain", "IT Services"),
            }
        # Generic fallback — agnostic identity
        return {
            "name": "[Bidder]",
            "tagline": "Enterprise Technology Services Provider",
            "domain": "IT Services",
        }

    def get_validated_facts(self) -> dict:
        """Extract cross-agent consensus facts from the manifest.

        These are the single source of truth that ALL agents must use.
        Intake populates them; downstream agents consume them.
        If agents disagree, the feedback loop captures the discrepancy.
        """
        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )
        scope = self.manifest.get("scope_output", {})
        sp = scope.get("scope_package", scope) if isinstance(scope, dict) else {}

        def _extract_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("value", field_data)
            return field_data

        # Build consensus facts with source tracking
        facts = {
            "platform_count": len(intake.get("platform_details", []))
            if isinstance(intake, dict)
            else 0,
            "integration_count": len(intake.get("integration_inventory", []))
            if isinstance(intake, dict)
            else 0,
            "products": _extract_val(extracted.get("products", [])),
            "employee_count": _extract_val(extracted.get("employee_population", 0)),
            "contract_type": _extract_val(extracted.get("contract_type", "")),
            "geographies": _extract_val(extracted.get("geographies", [])),
            "scope_products": sp.get("products_in_scope", [])
            if isinstance(sp, dict)
            else [],
            "scope_fte_total": sum(
                r.get("count", 0)
                for r in (sp.get("team_model", []) if isinstance(sp, dict) else [])
                if isinstance(r, dict)
            ),
        }
        return facts

    def validate_output_grounding(self, output: dict, rfp_text: str) -> dict:
        """Check if LLM output claims are grounded in the RFP text.

        Returns a report with: grounded_claims, ungrounded_claims, fabrication_rate.
        Ungrounded claims are logged as learnings for the feedback loop.
        """
        import re

        grounded = []
        ungrounded = []
        rfp_lower = rfp_text.lower() if rfp_text else ""

        def _check_value(key, value):
            if isinstance(value, str) and len(value) > 20:
                # Check if key terms from the value appear in RFP
                words = [
                    w
                    for w in re.findall(r"\b[a-zA-Z]{4,}\b", value.lower())
                    if w
                    not in {
                        "this",
                        "that",
                        "with",
                        "from",
                        "will",
                        "have",
                        "been",
                        "their",
                        "they",
                        "would",
                        "should",
                        "could",
                        "which",
                        "these",
                        "those",
                        "more",
                        "also",
                        "each",
                        "both",
                        "such",
                        "when",
                        "than",
                        "into",
                    }
                ]
                if words:
                    matches = sum(1 for w in words[:8] if w in rfp_lower)
                    if matches / max(len(words[:8]), 1) >= 0.3:
                        grounded.append(key)
                    else:
                        ungrounded.append(key)
            elif isinstance(value, (int, float)) and value > 0:
                if str(int(value)) in rfp_text or f"{value}" in rfp_text:
                    grounded.append(key)

        for key, value in output.items():
            if isinstance(value, dict):
                for k2, v2 in value.items():
                    _check_value(f"{key}.{k2}", v2)
            elif isinstance(value, list):
                for i, item in enumerate(value[:5]):
                    if isinstance(item, dict):
                        for k2, v2 in item.items():
                            _check_value(f"{key}[{i}].{k2}", v2)
            else:
                _check_value(key, value)

        total = len(grounded) + len(ungrounded)
        fabrication_rate = len(ungrounded) / max(total, 1)

        report = {
            "grounded_claims": len(grounded),
            "ungrounded_claims": len(ungrounded),
            "ungrounded_keys": ungrounded[:10],
            "fabrication_rate": round(fabrication_rate, 2),
            "total_checked": total,
        }

        if fabrication_rate > 0.5:
            self.log("high_fabrication_rate", report)

        return report

    def _default_system_prompt(self, json_mode: bool = False) -> str:
        """Build application-agnostic system prompt using bidder identity from manifest."""
        bidder = self.get_bidder_identity()
        if json_mode:
            return f"You are {self.name} for {bidder['name']}. Respond with valid JSON only."
        return (
            f"You are {self.name}, an expert agent for {bidder['name']}'s "
            f"{bidder['tagline']} bid management system. "
            f"You MUST ground all claims in the RFP document provided. "
            f"If a fact cannot be verified from the RFP, mark it as [ESTIMATED] or [PLACEHOLDER]. "
            f"NEVER fabricate metrics, vendor names, or capabilities not present in the source data."
        )

    async def llm_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
        max_tokens: int = 1500,
    ) -> str:
        """Generate narrative text via the LLM service using this agent's tier + provider.

        Passes both `tier` (preferred) and `provider` (legacy) so the LLM service
        can route correctly regardless of which var is set on the subclass.
        """
        effective_prompt = prompt
        if not json_mode:
            # /no_think suppresses internal reasoning chains (Qwen-3, DeepSeek)
            # so all max_tokens go to actual output, not internal monologue.
            effective_prompt = prompt.rstrip() + "\n/no_think"
        result = await llm_service.generate(
            effective_prompt,
            system_prompt=system_prompt or self._default_system_prompt(),
            max_tokens=max_tokens,
            agent_tier=self.agent_tier,
            require_json=json_mode,
        )
        return self.clean_narrative(result)

    async def llm_json(
        self, prompt: str, system_prompt: str = "", max_tokens: int = 6000
    ) -> Dict[str, Any]:
        """Generate structured JSON via the LLM service using this agent's tier + provider."""
        return await llm_service.generate_structured(
            prompt,
            system_prompt=system_prompt or self._default_system_prompt(json_mode=True),
            max_tokens=max_tokens,
            tier=self.agent_tier,
        )

    async def web_lookup(self, term: str, context: str = "") -> str:
        """Search the web for an unknown term/product/technology.
        Guardrails: 10s timeout, single query, 1000 char result cap, relevance filter.
        Use this when agents encounter unknown apps, acronyms, or technologies in an RFP.
        """
        import httpx
        import re

        query = f"{term} {context}" if context else term
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http:
                resp = await http.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                if resp.status_code != 200:
                    return ""
                snippets = []
                for s in re.findall(
                    r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL
                )[:4]:
                    clean = re.sub(r"<[^>]+>", "", s).strip()
                    if (
                        clean
                        and len(clean) > 20
                        and term.lower().split()[0] in clean.lower()
                    ):
                        snippets.append(clean)
                result = " ".join(snippets)[:1000]
                if result:
                    self.log("web_lookup", {"term": term, "chars": len(result)})
                return result
        except Exception:
            return ""

    async def rag_query(
        self, query: str, collection: Optional[str] = None, top_k: int = 5
    ) -> Dict[str, Any]:
        """Query the Knowledge Base via RAG for relevant past content."""
        try:
            from app.knowledge.embeddings import embedding_service
            from app.knowledge.rag import rag_pipeline

            if len(rag_pipeline.embeddings_store) == 0:
                return {"context": "", "sources": [], "result_count": 0}
            query_embedding = embedding_service.embed(query)
            result = await rag_pipeline.search_with_context(
                query_embedding=query_embedding,
                top_k=top_k,
                collection_filter=collection,
            )
            self.log(
                "rag_query",
                {
                    "query": query[:100],
                    "collection": collection,
                    "results": result.get("result_count", 0),
                },
            )
            return result
        except Exception as e:
            self.log("rag_query_failed", {"error": str(e)})
            return {"context": "", "sources": [], "result_count": 0}

    async def get_kb_context(self, query: str, collections: list = None) -> str:
        """Get formatted KB context from multiple collections for injection into prompts."""
        if not collections:
            collections = [None]  # Search all
        all_context = []
        all_sources = []
        for coll in collections:
            result = await self.rag_query(query, collection=coll, top_k=3)
            if result.get("context"):
                all_context.append(result["context"])
                all_sources.extend(result.get("sources", []))
        if not all_context:
            return ""
        header = "=== KNOWLEDGE BASE CONTEXT (from past bids & templates) ===\n"
        source_list = ", ".join(set(s.get("filename", "?") for s in all_sources[:5]))
        header += f"Sources: {source_list}\n\n"
        return header + "\n\n---\n\n".join(all_context)

    async def execute_cypher_query(
        self, query: str, fallback_rag_query: Optional[str] = None
    ) -> str:
        """Execute a graph-style query against the knowledge base.

        Uses RAG-based KB retrieval as the primary mechanism.
        """
        self.log("cypher_query_executed", {"query": query[:100]})

        # Use KB context retrieval
        rag_query = fallback_rag_query or query
        try:
            context = await self.get_kb_context(rag_query)
            if context:
                return f"=== KNOWLEDGE BASE CONTEXT (GRAPH QUERY) ===\nQuery: {query.strip()}\n\n{context}"
            return ""
        except Exception as e:
            self.log("cypher_query_failed", {"error": str(e)})
            return ""

    async def get_kb_rate_card(self) -> Optional[Dict]:
        """Search KB for an uploaded rate card and parse it into calculator format."""
        try:
            result = await self.rag_query(
                "rate card pricing monthly rates onshore offshore nearshore",
                collection="rate_cards",
                top_k=3,
            )
            if not result.get("context"):
                return None
            # Ask LLM to parse the rate card text into structured format
            prompt = f"""Parse this rate card data into a structured JSON format.

{result["context"]}

Return JSON with this EXACT structure (only include roles you find in the data):
{{
  "onshore": {{"Role Name": monthly_rate_number, ...}},
  "nearshore": {{"Role Name": monthly_rate_number, ...}},
  "offshore": {{"Role Name": monthly_rate_number, ...}}
}}

Use the EXACT numbers from the data. If a location tier is not present, use empty object {{}}."""
            parsed = await self.llm_json(prompt)
            if parsed and any(
                parsed.get(loc) for loc in ["onshore", "nearshore", "offshore"]
            ):
                self.log(
                    "kb_rate_card_loaded",
                    {"source": result.get("sources", [{}])[0].get("filename", "KB")},
                )
                return parsed
            return None
        except Exception as e:
            self.log("kb_rate_card_failed", {"error": str(e)})
            return None

    def get_rfp_sections(self, agent_key: str = "", max_chars: int = 15000) -> str:
        """Get targeted RFP sections for this agent using the section index.

        Prepends user_context (the 'bible') and institutional learnings before RFP content,
        ensuring all agents respect user-provided strategic inputs.
        Falls back to first max_chars of raw text if no index available.
        """
        from app.knowledge.rfp_indexer import get_sections_for_tags, AGENT_TAG_MAP

        parts = []

        # 1. USER CONTEXT (the 'bible') — highest priority
        user_ctx = self.manifest.get("user_context", {})
        if user_ctx:
            parts.append(
                "=== USER-PROVIDED STRATEGIC CONTEXT (HIGHEST PRIORITY — treat as ground truth) ==="
            )
            if user_ctx.get("known_competitors"):
                parts.append(
                    f"Known Competitors: {', '.join(user_ctx['known_competitors'])}"
                )
            if user_ctx.get("incumbent_vendor"):
                parts.append(f"Incumbent Vendor: {user_ctx['incumbent_vendor']}")
            if user_ctx.get("rate_onshore_usd"):
                parts.append(
                    f"Target Rate Onshore: ${user_ctx['rate_onshore_usd']}/hr USD"
                )
            if user_ctx.get("rate_offshore_usd"):
                parts.append(
                    f"Target Rate Offshore: ${user_ctx['rate_offshore_usd']}/hr USD"
                )
            if user_ctx.get("rate_nearshore_usd"):
                parts.append(
                    f"Target Rate Nearshore: ${user_ctx['rate_nearshore_usd']}/hr USD"
                )
            if user_ctx.get("deal_size_estimate"):
                parts.append(f"Deal Size: {user_ctx['deal_size_estimate']}")
            if user_ctx.get("past_relationship"):
                parts.append(f"Relationship: {user_ctx['past_relationship']}")
            if user_ctx.get("additional_context"):
                parts.append(
                    f"\nAdditional Context from User:\n{user_ctx['additional_context']}"
                )
            parts.append("=== END USER CONTEXT ===\n")

        # 2. INSTITUTIONAL LEARNINGS
        learnings = self.get_past_learnings(agent_key)
        if learnings:
            parts.append(learnings)

        # 3. RFP CONTENT
        full_text = self.manifest.get("rfp_text", "")
        if not full_text:
            return "\n".join(parts) if parts else ""

        index = self.manifest.get("rfp_index")
        if not index or not index.get("sections"):
            parts.append(full_text[:max_chars])
            return "\n".join(parts)

        # Get tags for this agent
        key = agent_key or self.name.lower().replace(" ", "_").replace("&", "").replace(
            "__", "_"
        )
        tags = AGENT_TAG_MAP.get(key, ["scope", "requirements", "commercial"])

        result = get_sections_for_tags(index, full_text, tags, max_chars=max_chars)

        primary = result.get("primary", "")
        overview = result.get("overview", "")
        sections_used = result.get("sections_used", "")

        self.log(
            "rfp_sections_loaded",
            {"agent_key": key, "sections": sections_used, "chars": len(primary)},
        )

        # Build the context with overview as secondary
        parts.append(f"=== RFP SECTIONS (relevant to {self.name}) ===")
        parts.append(f"Sections referenced: {sections_used}\n")
        parts.append(primary)

        if overview:
            parts.append(
                f"\n=== FULL DOCUMENT STRUCTURE (for reference) ===\n{overview}"
            )

        return "\n".join(parts)

    def get_past_learnings(self, agent_key: str = "", limit: int = 5) -> str:
        """Query the institutional learning store for relevant past insights.

        Returns formatted string ready for injection into LLM prompts.
        Makes the agent smarter with each RFP the system processes.
        """
        from app.knowledge.learning_store import (
            query_learnings,
            format_learnings_for_prompt,
            mark_learning_used,
        )

        # Extract context from manifest
        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )

        industry = ""
        contract_type = ""
        products = []

        if extracted:
            ind = extracted.get("client_industry", "")
            if isinstance(ind, dict):
                industry = str(ind.get("value", "") or "")
            else:
                industry = str(ind or "")
            ct = extracted.get("contract_type", "")
            if isinstance(ct, dict):
                contract_type = str(ct.get("value", "") or "")
            else:
                contract_type = str(ct or "")
            prods = extracted.get("products", [])
            if isinstance(prods, dict):
                products_val = prods.get("value", [])
            else:
                products_val = prods
            if isinstance(products_val, list):
                products = [str(p) for p in products_val]
            elif isinstance(products_val, str):
                products = [p.strip() for p in products_val.split(",")]
            else:
                products = []

        key = agent_key or self.name.lower().replace(" ", "_").replace("&", "").replace(
            "__", "_"
        )

        learnings = query_learnings(
            agent_name=key,
            industry=industry,
            contract_type=contract_type,
            products=products,
            limit=limit,
        )

        if learnings:
            self.log("learnings_retrieved", {"count": len(learnings), "agent": key})
            for l in learnings:
                mark_learning_used(l["id"])

        return format_learnings_for_prompt(learnings)

    def capture_learning(
        self,
        learning_type: str,
        insight: str,
        confidence: float = 0.5,
        metadata: dict = None,
    ):
        """Capture a learning from this agent's run into the institutional store."""
        from app.knowledge.learning_store import add_learning

        intake = self.manifest.get("intake_output", {})
        extracted = (
            intake.get("extracted_fields", {}) if isinstance(intake, dict) else {}
        )

        industry = ""
        contract_type = ""
        products = []

        if extracted:
            ind = extracted.get("client_industry", "")
            if isinstance(ind, dict):
                industry = str(ind.get("value", "") or "")
            else:
                industry = str(ind or "")
            ct = extracted.get("contract_type", "")
            if isinstance(ct, dict):
                contract_type = str(ct.get("value", "") or "")
            else:
                contract_type = str(ct or "")
            prods = extracted.get("products", [])
            if isinstance(prods, dict):
                products_val = prods.get("value", [])
            else:
                products_val = prods
            if isinstance(products_val, list):
                products = [str(p) for p in products_val]
            elif isinstance(products_val, str):
                products = [p.strip() for p in products_val.split(",")]
            else:
                products = []

        key = self.name.lower().replace(" ", "_").replace("&", "").replace("__", "_")

        result = add_learning(
            bid_id=self.bid_id,
            agent_name=key,
            learning_type=learning_type,
            insight=insight,
            industry=industry,
            contract_type=contract_type,
            products=products,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.log("learning_captured", {"type": learning_type, "id": result["id"]})
        return result
