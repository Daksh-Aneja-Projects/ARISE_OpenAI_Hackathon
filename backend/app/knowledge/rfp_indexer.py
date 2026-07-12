"""
RFP Section Indexer — Splits a full RFP document into logical sections,
tags each with topic labels, and builds a queryable index that allows
agents to read the *actual* relevant portions of the RFP.

The Intake agent builds this index once; all downstream agents consume it
through BaseAgent.get_rfp_sections(tags).
"""

import re
from typing import List, Dict, Any, Tuple


# ─── Topic tags for agent routing ────────────────────────────────────────────
AGENT_TAG_MAP: Dict[str, List[str]] = {
    "intake": ["all"],
    "bid_no_bid": [
        "strategic",
        "evaluation",
        "qualification",
        "scope",
        "commercial",
        "experience",
    ],
    "competitive_intel": [
        "evaluation",
        "selection",
        "experience",
        "qualifications",
        "scope",
        "commercial",
    ],
    "scope_builder": [
        "scope",
        "requirements",
        "deliverables",
        "activities",
        "team",
        "timeline",
        "SLA",
    ],
    "solution_architect": [
        "technical",
        "integration",
        "platform",
        "architecture",
        "scope",
        "SLA",
        "infrastructure",
    ],
    "commercial_model": [
        "commercial",
        "pricing",
        "contract",
        "team",
        "duration",
        "scope",
        "SLA",
        "penalty",
    ],
    "compliance_risk": [
        "legal",
        "compliance",
        "SLA",
        "penalty",
        "liability",
        "data_protection",
        "governance",
        "insurance",
        "indemnity",
    ],
    "automation_ai": [
        "automation",
        "monitoring",
        "testing",
        "SLA",
        "continuous_improvement",
        "technical",
        "integration",
    ],
    "transition_change": [
        "transition",
        "handover",
        "exit",
        "governance",
        "timeline",
        "team",
        "scope",
        "SLA",
        "training",
    ],
    "discovery": [
        "scope",
        "commercial",
        "technical",
        "governance",
        "integration",
        "SLA",
    ],
    "output_generator": ["scope", "commercial", "team", "technical", "evaluation"],
    "qa": ["all"],
    "feedback_learning": ["scope", "commercial", "evaluation"],
}


# ─── Section splitting ───────────────────────────────────────────────────────


def _detect_section_breaks(text: str) -> List[Tuple[int, str, str]]:
    """
    Detect section boundaries using structural patterns common in RFPs.
    Returns list of (char_position, section_ref, section_title).
    """
    breaks = []

    # Pattern 1: Numbered headers like "2.1 Scope of Services" or "2.1. Scope"
    for m in re.finditer(
        r"^[\s]*(\d+(?:\.\d+)*\.?)\s+([A-Z][^\n]{3,80})", text, re.MULTILINE
    ):
        breaks.append((m.start(), m.group(1).rstrip("."), m.group(2).strip()))

    # Pattern 2: ALL-CAPS headers like "SCOPE OF SERVICES" (at least 3 words)
    for m in re.finditer(
        r"^[\s]*((?:[A-Z][A-Z\s&,/()-]{8,80}))\s*$", text, re.MULTILINE
    ):
        title = m.group(1).strip()
        # Skip if it's just a single short word or looks like data
        if len(title.split()) >= 2 and not re.match(r"^\d", title):
            breaks.append((m.start(), "", title))

    # Pattern 3: "Section X:" or "Part X:" headers
    for m in re.finditer(
        r"^[\s]*((?:Section|Part|Article|Appendix|Annex|Schedule)\s+[\dA-Z]+[:.]\s*([^\n]{3,80}))",
        text,
        re.MULTILINE | re.IGNORECASE,
    ):
        breaks.append((m.start(), "", m.group(1).strip()))

    # De-duplicate and sort by position
    breaks.sort(key=lambda x: x[0])

    # Remove breaks that are too close together (< 200 chars apart)
    filtered = []
    last_pos = -500
    for pos, ref, title in breaks:
        if pos - last_pos >= 200:
            filtered.append((pos, ref, title))
            last_pos = pos

    return filtered


def split_into_sections(text: str) -> List[Dict[str, Any]]:
    """
    Split RFP text into logical sections based on detected headers.
    Each section includes the raw text, char range, and detected header info.
    """
    breaks = _detect_section_breaks(text)

    if not breaks:
        # No structure detected — split into ~3000 char chunks
        sections = []
        chunk_size = 3000
        for i in range(0, len(text), chunk_size):
            sections.append(
                {
                    "section_ref": f"chunk-{i // chunk_size + 1}",
                    "title": f"Document Section {i // chunk_size + 1}",
                    "char_start": i,
                    "char_end": min(i + chunk_size, len(text)),
                    "text": text[i : i + chunk_size],
                }
            )
        return sections

    sections = []
    for i, (pos, ref, title) in enumerate(breaks):
        end = breaks[i + 1][0] if i + 1 < len(breaks) else len(text)
        section_text = text[pos:end].strip()

        # Skip very short sections (< 100 chars) — likely sub-headers without content
        if len(section_text) < 100:
            continue

        sections.append(
            {
                "section_ref": ref or f"section-{i + 1}",
                "title": title,
                "char_start": pos,
                "char_end": end,
                "text": section_text,
            }
        )

    # Add preamble if first section doesn't start at the beginning
    if breaks and breaks[0][0] > 200:
        preamble = text[: breaks[0][0]].strip()
        if len(preamble) > 100:
            sections.insert(
                0,
                {
                    "section_ref": "0",
                    "title": "Preamble / Cover",
                    "char_start": 0,
                    "char_end": breaks[0][0],
                    "text": preamble,
                },
            )

    return sections


# ─── LLM-based section tagging ───────────────────────────────────────────────


async def tag_sections(
    sections: List[Dict[str, Any]], llm_service
) -> List[Dict[str, Any]]:
    """
    Use LLM to tag each section with topic labels.
    Processes sections in batches to reduce LLM calls.
    """
    # Build a batch summary for the LLM — section refs + first 300 chars
    batch_items = []
    for s in sections:
        preview = s["text"][:300].replace("\n", " ").strip()
        batch_items.append(
            {
                "ref": s["section_ref"],
                "title": s["title"],
                "preview": preview,
                "char_count": len(s["text"]),
            }
        )

    # Process in batches of 15 sections
    all_tags = {}
    batch_size = 15

    for batch_start in range(0, len(batch_items), batch_size):
        batch = batch_items[batch_start : batch_start + batch_size]

        sections_text = ""
        for item in batch:
            sections_text += f"\n--- {item['ref']}: {item['title']} ({item['char_count']} chars) ---\n{item['preview']}\n"

        prompt = f"""Tag each RFP section with relevant topic labels.

AVAILABLE TAGS (use 2-5 per section):
scope, requirements, deliverables, activities, team, timeline,
technical, integration, platform, architecture, infrastructure,
commercial, pricing, contract, duration, penalty,
legal, compliance, SLA, liability, data_protection, governance, insurance, indemnity,
evaluation, selection, experience, qualifications,
automation, monitoring, testing, continuous_improvement,
strategic, executive, overview,
transition, handover, exit

SECTIONS:
{sections_text}

Return JSON — a dict mapping section ref to tag list:
{{
  "{batch[0]["ref"]}": ["tag1", "tag2", "tag3"],
  "{batch[-1]["ref"]}": ["tag1", "tag2"]
}}"""

        try:
            result = await llm_service.generate_structured(
                prompt,
                system_prompt="You are a document analyst. Tag each section with relevant topic labels. Respond with valid JSON only.",
                max_tokens=2000,
            )
            if isinstance(result, dict) and "error" not in result:
                all_tags.update(result)
        except Exception as e:
            print(f"[RFP Indexer] Tagging batch failed: {e}")

    # Apply tags to sections
    for section in sections:
        ref = section["section_ref"]
        tags = all_tags.get(ref, [])
        if not tags:
            # Fallback: rule-based tagging from title keywords
            tags = _rule_based_tags(section["title"], section["text"][:500])
        section["tags"] = tags

    return sections


def _rule_based_tags(title: str, preview: str) -> List[str]:
    """Fallback rule-based tagging when LLM tagging fails."""
    combined = (title + " " + preview).lower()
    tags = []

    tag_keywords = {
        "scope": ["scope", "services", "requirements", "work packages", "deliverables"],
        "requirements": ["requirement", "mandatory", "shall", "must", "expected"],
        "technical": [
            "technical",
            "architecture",
            "infrastructure",
            "server",
            "cloud",
            "api",
        ],
        "integration": [
            "integration",
            "interface",
            "api",
            "connector",
            "middleware",
            "data flow",
        ],
        "platform": [
            "platform",
            "module",
            "product",
            "application",
            "system",
            "software",
        ],
        "commercial": [
            "commercial",
            "pricing",
            "price",
            "cost",
            "fee",
            "financial",
            "bid price",
        ],
        "contract": [
            "contract",
            "agreement",
            "term",
            "duration",
            "period",
            "renewal",
            "extension",
        ],
        "legal": [
            "legal",
            "liability",
            "indemnity",
            "warranty",
            "termination",
            "dispute",
        ],
        "compliance": [
            "compliance",
            "regulatory",
            "gdpr",
            "data protection",
            "privacy",
            "audit",
        ],
        "SLA": [
            "sla",
            "service level",
            "kpi",
            "availability",
            "uptime",
            "response time",
            "resolution",
        ],
        "penalty": ["penalty", "service credit", "liquidated damages", "deduction"],
        "evaluation": [
            "evaluation",
            "criteria",
            "scoring",
            "selection",
            "assessment",
            "weighting",
        ],
        "team": [
            "team",
            "resource",
            "personnel",
            "staffing",
            "role",
            "fte",
            "headcount",
        ],
        "timeline": [
            "timeline",
            "schedule",
            "milestone",
            "phase",
            "deadline",
            "go-live",
        ],
        "transition": [
            "transition",
            "handover",
            "migration",
            "onboarding",
            "exit",
            "knowledge transfer",
        ],
        "governance": [
            "governance",
            "steering",
            "committee",
            "escalation",
            "reporting",
            "review",
        ],
        "automation": [
            "automation",
            "automate",
            "self-healing",
            "monitoring",
            "bot",
            "rpa",
        ],
        "experience": [
            "experience",
            "case study",
            "reference",
            "track record",
            "similar",
            "past performance",
        ],
        "insurance": ["insurance", "policy", "cover", "professional indemnity"],
        "data_protection": [
            "data protection",
            "gdpr",
            "privacy",
            "personal data",
            "data handling",
        ],
        "strategic": ["strategic", "objective", "vision", "transformation", "value"],
        "overview": ["introduction", "overview", "background", "context", "about"],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in combined for kw in keywords):
            tags.append(tag)

    return tags or ["general"]


# ─── Index builder ────────────────────────────────────────────────────────────


async def build_rfp_index(full_text: str, llm_service) -> Dict[str, Any]:
    """
    Build a complete section index for the RFP document.
    Returns a serializable dict stored in the bid manifest.
    """
    print(f"[RFP Indexer] Building index for {len(full_text)} chars of RFP text...")

    # Step 1: Split into structural sections
    sections = split_into_sections(full_text)
    print(f"[RFP Indexer] Detected {len(sections)} sections")

    # Step 2: Tag each section with topics
    sections = await tag_sections(sections, llm_service)
    print("[RFP Indexer] Tagged all sections")

    # Step 3: Build the index (without raw text — that stays in rfp_text)
    index_entries = []
    for s in sections:
        index_entries.append(
            {
                "section_ref": s["section_ref"],
                "title": s["title"],
                "char_start": s["char_start"],
                "char_end": s["char_end"],
                "char_count": len(s["text"]),
                "tags": s["tags"],
            }
        )

    # Step 4: Build overview (compact 2K summary of section structure)
    overview_lines = []
    for entry in index_entries:
        tags_str = ", ".join(entry["tags"][:4])
        overview_lines.append(
            f"  [{entry['section_ref']}] {entry['title']} "
            f"({entry['char_count']} chars) — {tags_str}"
        )

    index = {
        "total_chars": len(full_text),
        "section_count": len(index_entries),
        "sections": index_entries,
        "overview": "\n".join(overview_lines),
    }

    print(
        f"[RFP Indexer] Index complete: {len(index_entries)} sections, {len(full_text)} chars total"
    )
    return index


# ─── Section retrieval for agents ─────────────────────────────────────────────


def get_sections_for_tags(
    index: Dict[str, Any],
    full_text: str,
    primary_tags: List[str],
    max_chars: int = 15000,
    secondary_overview: bool = True,
) -> Dict[str, str]:
    """
    Retrieve relevant RFP sections for a given set of topic tags.

    Returns:
        {
            "primary": "... actual RFP text from relevant sections ...",
            "overview": "... 2K char structural overview of full document ...",
            "sections_used": "2.1 Scope, 4.0 Commercial Terms, ..."
        }
    """
    if not index or not index.get("sections"):
        # No index available — return truncated text as fallback
        return {
            "primary": full_text[:max_chars] if full_text else "",
            "overview": "",
            "sections_used": "no index — using first 15K chars",
        }

    sections = index["sections"]

    # "all" tag means return everything up to max_chars
    if "all" in primary_tags:
        return {
            "primary": full_text[:max_chars],
            "overview": index.get("overview", ""),
            "sections_used": "all sections",
        }

    # Score each section by tag overlap
    scored = []
    for sec in sections:
        sec_tags = set(t.lower() for t in sec.get("tags", []))
        primary_set = set(t.lower() for t in primary_tags)

        # Count matching tags
        overlap = len(sec_tags & primary_set)
        if overlap > 0:
            scored.append((overlap, sec))

    # Sort by relevance (most matching tags first)
    scored.sort(key=lambda x: -x[0])

    # Collect sections up to max_chars
    primary_parts = []
    sections_used = []
    total_chars = 0

    for _score, sec in scored:
        section_text = full_text[sec["char_start"] : sec["char_end"]]
        if total_chars + len(section_text) > max_chars:
            # Add partial if we have room for at least 500 chars
            remaining = max_chars - total_chars
            if remaining >= 500:
                primary_parts.append(
                    f"\n=== [{sec['section_ref']}] {sec['title']} (truncated) ===\n"
                    + section_text[:remaining]
                )
                sections_used.append(f"{sec['section_ref']} {sec['title']} (partial)")
            break
        primary_parts.append(
            f"\n=== [{sec['section_ref']}] {sec['title']} ===\n" + section_text
        )
        sections_used.append(f"{sec['section_ref']} {sec['title']}")
        total_chars += len(section_text)

    # If we got less than 3000 chars of primary, add remaining sections as secondary
    if total_chars < 3000:
        used_refs = {sec["section_ref"] for _, sec in scored[: len(primary_parts)]}
        for sec in sections:
            if sec["section_ref"] not in used_refs and total_chars < max_chars:
                section_text = full_text[sec["char_start"] : sec["char_end"]]
                remaining = max_chars - total_chars
                if remaining < 500:
                    break
                primary_parts.append(
                    f"\n=== [{sec['section_ref']}] {sec['title']} (secondary) ===\n"
                    + section_text[:remaining]
                )
                sections_used.append(f"{sec['section_ref']} {sec['title']} (secondary)")
                total_chars += min(len(section_text), remaining)

    result = {
        "primary": "\n".join(primary_parts),
        "overview": index.get("overview", "") if secondary_overview else "",
        "sections_used": ", ".join(sections_used),
    }

    return result
