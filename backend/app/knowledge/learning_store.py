"""
Institutional Learning Store — Persistent knowledge accumulator.
Captures structured learnings from each completed bid and makes them
available to all agents on future bids. The system gets smarter with
each RFP it processes.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

LEARNING_STORE_PATH = Path("data/learnings.json")


def _load_store() -> List[Dict[str, Any]]:
    """Load the learning store from disk."""
    if not LEARNING_STORE_PATH.exists():
        LEARNING_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return []
    try:
        with open(LEARNING_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_store(learnings: List[Dict[str, Any]]):
    """Persist the learning store to disk."""
    LEARNING_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(learnings, f, indent=2, default=str)


def add_learning(
    bid_id: str,
    agent_name: str,
    learning_type: str,
    insight: str,
    industry: str = "",
    contract_type: str = "",
    products: Optional[List[str]] = None,
    deal_size: str = "mid",
    confidence: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add a new learning to the store.
    If a similar insight already exists (same agent + type + similar text),
    boost its confidence instead of duplicating.
    """
    store = _load_store()
    products = products or []

    # Check for duplicates — boost confidence if similar exists
    for existing in store:
        if (
            existing["agent_name"] == agent_name
            and existing["learning_type"] == learning_type
            and _similarity(existing["insight"], insight) > 0.7
        ):
            existing["confidence"] = min(existing["confidence"] + 0.1, 1.0)
            existing["usage_count"] = existing.get("usage_count", 0) + 1
            existing["last_reinforced"] = datetime.utcnow().isoformat()
            existing["reinforced_by_bids"] = list(
                set(existing.get("reinforced_by_bids", []) + [bid_id])
            )
            _save_store(store)
            return existing

    learning = {
        "id": str(uuid.uuid4()),
        "bid_id": bid_id,
        "agent_name": agent_name,
        "industry": industry.lower(),
        "contract_type": contract_type.lower(),
        "products": [p.lower() for p in products],
        "deal_size": deal_size,
        "learning_type": learning_type,
        "insight": insight,
        "confidence": confidence,
        "usage_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None,
        "last_reinforced": None,
        "reinforced_by_bids": [bid_id],
        "metadata": metadata or {},
    }
    store.append(learning)
    _save_store(store)
    return learning


def query_learnings(
    agent_name: Optional[str] = None,
    industry: str = "",
    contract_type: str = "",
    products: Optional[List[str]] = None,
    learning_type: Optional[str] = None,
    min_confidence: float = 0.3,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Query the learning store for relevant past insights.
    Returns learnings ranked by relevance score (industry match + product match + confidence).
    """
    store = _load_store()
    products = [p.lower() for p in (products or [])]
    industry = industry.lower()
    contract_type = contract_type.lower()

    scored = []
    for learning in store:
        if learning["confidence"] < min_confidence:
            continue
        if agent_name and learning["agent_name"] != agent_name:
            continue
        if learning_type and learning["learning_type"] != learning_type:
            continue

        # Relevance scoring
        score = learning["confidence"] * 0.3  # Base: confidence

        # Industry match
        if industry and learning["industry"] == industry:
            score += 0.3
        elif industry and learning["industry"]:
            score += 0.05  # Partial credit for cross-industry patterns

        # Contract type match
        if contract_type and learning["contract_type"] == contract_type:
            score += 0.2

        # Product overlap
        if products and learning["products"]:
            overlap = len(set(products) & set(learning["products"]))
            total = max(len(set(products) | set(learning["products"])), 1)
            score += 0.2 * (overlap / total)

        # Usage boost — more used = more proven
        score += min(learning.get("usage_count", 0) * 0.02, 0.1)

        # Time-based decay — learnings older than 180 days lose relevance
        created = learning.get("created_at", "")
        last_used = (
            learning.get("last_used") or learning.get("last_reinforced") or created
        )
        try:
            ts = datetime.fromisoformat(last_used) if last_used else datetime.utcnow()
            age_days = (datetime.utcnow() - ts).days
            if age_days > 180:
                decay = min(age_days / 600, 0.3)  # Max 30% penalty at ~1.5 years
                score *= 1.0 - decay
        except (ValueError, TypeError):
            pass  # Malformed timestamp — skip decay

        scored.append((score, learning))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Update last_used timestamp for returned learnings
    result = [item[1] for item in scored[:limit]]
    if result:
        store = _load_store()
        returned_ids = {l["id"] for l in result}
        for learning in store:
            if learning["id"] in returned_ids:
                learning["last_used"] = datetime.utcnow().isoformat()
        _save_store(store)

    return result


def format_learnings_for_prompt(learnings: List[Dict[str, Any]]) -> str:
    """Format learnings into a string that can be injected into agent prompts."""
    if not learnings:
        return ""

    lines = ["=== INSTITUTIONAL KNOWLEDGE (from past bids) ==="]
    for i, l in enumerate(learnings, 1):
        conf = f"{l['confidence']:.0%}"
        uses = l.get("usage_count", 0)
        reinforced = len(l.get("reinforced_by_bids", []))
        lines.append(
            f"[{i}] ({l['learning_type'].upper()} | {conf} confidence | seen in {reinforced} bids) "
            f"{l['insight']}"
        )
    lines.append("=== END INSTITUTIONAL KNOWLEDGE ===\n")
    return "\n".join(lines)


def mark_learning_used(learning_id: str):
    """Increment usage count when a learning is consumed by an agent."""
    store = _load_store()
    for learning in store:
        if learning["id"] == learning_id:
            learning["usage_count"] = learning.get("usage_count", 0) + 1
            break
    _save_store(store)


def get_all_learnings() -> List[Dict[str, Any]]:
    """Get all learnings for dashboard display."""
    return _load_store()


def get_learning_stats() -> Dict[str, Any]:
    """Get aggregate stats about the learning store."""
    store = _load_store()
    if not store:
        return {
            "total_learnings": 0,
            "total_bids_learned": 0,
            "by_agent": {},
            "by_type": {},
            "avg_confidence": 0,
            "maturity_level": "Novice",
        }
    by_agent: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    all_bids = set()
    for l in store:
        by_agent[l["agent_name"]] = by_agent.get(l["agent_name"], 0) + 1
        by_type[l["learning_type"]] = by_type.get(l["learning_type"], 0) + 1
        all_bids.update(l.get("reinforced_by_bids", []))

    total = len(store)
    avg_conf = sum(l["confidence"] for l in store) / total if total else 0
    bid_count = len(all_bids)

    # Maturity level based on learnings + bids
    if bid_count >= 20 and total >= 100:
        maturity = "Expert"
    elif bid_count >= 10 and total >= 50:
        maturity = "Advanced"
    elif bid_count >= 5 and total >= 20:
        maturity = "Intermediate"
    elif bid_count >= 2:
        maturity = "Learning"
    else:
        maturity = "Novice"

    return {
        "total_learnings": total,
        "total_bids_learned": bid_count,
        "by_agent": by_agent,
        "by_type": by_type,
        "avg_confidence": round(avg_conf, 2),
        "maturity_level": maturity,
    }


def delete_learning(learning_id: str) -> bool:
    """Delete a specific learning."""
    store = _load_store()
    initial_len = len(store)
    store = [l for l in store if l["id"] != learning_id]
    if len(store) < initial_len:
        _save_store(store)
        return True
    return False


def _similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity for deduplication."""
    if not a or not b:
        return 0.0
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b)
    return overlap / max(len(words_a | words_b), 1)
