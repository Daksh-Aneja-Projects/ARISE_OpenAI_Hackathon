"""
Organization Structure API — Org-agnostic hierarchy with bid metrics aggregation.
Supports any org shape: configurable levels, roles, and practices.
Executive-level view with recursive bid metric rollups.

DESIGN: The org tree is built from a generic template. To customize:
  1. Set ORG_CONFIG in .env or pass via API
  2. Or modify the DEFAULT_ORG_TEMPLATE below
  3. The frontend renders any depth of levels automatically
"""

import uuid
import json
import os
from fastapi import APIRouter, Depends, HTTPException
from app.services.auth import get_current_user
from app.config import settings
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bid_repository import BidRepository

router = APIRouter(prefix="/api/org", tags=["Organization"])


# ── Generic Org Template ──────────────────────────────────────
# This replaces the hardcoded HCLTech hierarchy. Each node is:
#   { role, practice, level, highlight?, is_self?, children[] }
# Customize this for any organization.

DEFAULT_ORG_TEMPLATE = {
    "levels": {
        1: {"label": "Executive Leadership", "desc": "C-Suite & Board"},
        2: {"label": "Business Unit Heads", "desc": "Division & regional leadership"},
        3: {"label": "Service Line Heads", "desc": "Service line ownership"},
        4: {"label": "Practice Directors", "desc": "Domain practice leads"},
    },
    "tree": {
        "role": "CEO & Managing Director",
        "practice": "Executive Office",
        "level": 1,
        "highlight": True,
        "children": [
            # ── Business Unit Heads (Level 2) ──
            {"role": "Chief Growth Officer", "practice": "Americas", "level": 2},
            {"role": "Chief Growth Officer", "practice": "EMEA", "level": 2},
            {"role": "Chief Growth Officer", "practice": "APAC", "level": 2},
            {"role": "Chief Financial Officer", "practice": "Finance", "level": 2},
            {"role": "Chief Technology Officer", "practice": "Technology", "level": 2},
            {"role": "Chief Operating Officer", "practice": "Operations", "level": 2},
            {"role": "Chief Product Officer", "practice": "Product", "level": 2},
            {"role": "Chief Revenue Officer", "practice": "Revenue", "level": 2},
            {
                "role": "Chief People Officer",
                "practice": "People & Culture",
                "level": 2,
            },
            {"role": "VP & General Counsel", "practice": "Legal", "level": 2},
            {"role": "VP Strategy & Corp Dev", "practice": "Strategy", "level": 2},
            # ── Digital Business (highlighted chain to user) ──
            {
                "role": "VP & Head of Digital Business",
                "practice": "Digital Business Services",
                "level": 2,
                "highlight": True,
                "children": [
                    # ── Service Line Heads (Level 3) ──
                    {
                        "role": "Service Line Head",
                        "practice": "Cloud & Infrastructure",
                        "level": 3,
                    },
                    {
                        "role": "Service Line Head",
                        "practice": "Data & Analytics",
                        "level": 3,
                    },
                    {
                        "role": "Service Line Head",
                        "practice": "Application Services",
                        "level": 3,
                    },
                    {
                        "role": "Service Line Head",
                        "practice": "Digital Transformation",
                        "level": 3,
                    },
                    {
                        "role": "Service Line Head",
                        "practice": "Cybersecurity",
                        "level": 3,
                    },
                    {
                        "role": "Service Line Head",
                        "practice": "AI & Automation",
                        "level": 3,
                    },
                    # ── User's position (highlighted + is_self) ──
                    {
                        "role": "Service Line Head",
                        "practice": "Enterprise Platform Services",
                        "level": 3,
                        "highlight": True,
                        "is_self": True,
                        "children": [
                            # ── Practice Directors (Level 4) ──
                            # Generic practice names — replace by setting ORG_CONFIG_FILE in .env
                            {"role": "Director", "practice": "Practice A", "level": 4},
                            {"role": "Director", "practice": "Practice B", "level": 4},
                            {"role": "Director", "practice": "Practice C", "level": 4},
                            {"role": "Director", "practice": "Practice D", "level": 4},
                            {"role": "Director", "practice": "Practice E", "level": 4},
                            {"role": "Director", "practice": "Practice F", "level": 4},
                            {
                                "role": "Director",
                                "practice": "Quality Engineering",
                                "level": 4,
                            },
                            {
                                "role": "Director",
                                "practice": "Cloud & DevOps",
                                "level": 4,
                            },
                        ],
                    },
                ],
            },
        ],
    },
}


def _load_org_template() -> dict:
    """Load org template from ORG_CONFIG_FILE if set and exists, else use default."""
    config_path = settings.ORG_CONFIG_FILE
    if config_path and os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                custom = json.load(f)
            print(f"[ORG] Loaded custom org config from {config_path}")
            return custom
        except Exception as e:
            print(
                f"[ORG] Warning: could not load org config from {config_path}: {e}. Using default."
            )
    return DEFAULT_ORG_TEMPLATE


def _id(role: str, practice: str, level: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{role}::{practice}::{level}"))


def _build_node(template: dict) -> dict:
    """Recursively build an org node from a template dict."""
    node = {
        "id": _id(template["role"], template["practice"], template["level"]),
        "role": template["role"],
        "practice": template["practice"],
        "level": template["level"],
        "highlight": template.get("highlight", False),
        "is_self": template.get("is_self", False),
        "children": [],
    }
    for child_tmpl in template.get("children", []):
        node["children"].append(_build_node(child_tmpl))
    return node


def _build_tree() -> dict:
    """Build the org tree from config (file or default template)."""
    template = _load_org_template()
    return _build_node(template["tree"])


# Build once at import time
ORG_TREE = _build_tree()

# Level metadata (used by frontend for display)
LEVEL_META = _load_org_template()["levels"]


def _flatten_nodes(node: dict, result: list = None) -> list:
    """Flatten org tree into a list of {id, role, practice, level} for dropdown use."""
    if result is None:
        result = []
    result.append(
        {
            "id": node["id"],
            "role": node["role"],
            "practice": node["practice"],
            "level": node["level"],
            "label": f"{node['role']} – {node['practice']}",
        }
    )
    for child in node.get("children", []):
        _flatten_nodes(child, result)
    return result


def _collect_at_level(node: dict, target_level: int, result: list = None) -> list:
    """Collect all nodes at a specific level."""
    if result is None:
        result = []
    if node["level"] == target_level:
        result.append(node)
    for child in node.get("children", []):
        _collect_at_level(child, target_level, result)
    return result


def _aggregate_bid_metrics(node: dict, bids: list) -> dict:
    """Recursively attach bid metrics to each org node. Metrics roll up."""
    node_id = node["id"]
    direct_bids = [b for b in bids if b.get("org_unit_id") == node_id]

    child_results = []
    for child in node.get("children", []):
        child_results.append(_aggregate_bid_metrics(child, bids))

    all_bids = list(direct_bids)
    for cr in child_results:
        all_bids.extend(cr["_all_bids"])

    total_deals = len(all_bids)
    active_deals = len(
        [
            b
            for b in all_bids
            if b.get("status")
            not in ("submitted", "won", "lost", "abandoned", "no_bid")
        ]
    )
    won_deals = len([b for b in all_bids if b.get("status") == "won"])
    lost_deals = len([b for b in all_bids if b.get("status") == "lost"])
    total_tcv = sum(b.get("estimated_tcv") or 0 for b in all_bids)
    won_tcv = sum(
        b.get("estimated_tcv") or 0 for b in all_bids if b.get("status") == "won"
    )
    probs = [b.get("win_probability") for b in all_bids if b.get("win_probability")]
    avg_win_prob = round(sum(probs) / len(probs), 2) if probs else 0
    completed = won_deals + lost_deals
    win_rate = round((won_deals / completed * 100), 1) if completed > 0 else 0

    enriched = {
        **{k: v for k, v in node.items() if k != "children"},
        "metrics": {
            "total_deals": total_deals,
            "direct_deals": len(direct_bids),
            "active_deals": active_deals,
            "won_deals": won_deals,
            "lost_deals": lost_deals,
            "total_revenue": total_tcv,
            "won_revenue": won_tcv,
            "avg_win_probability": avg_win_prob,
            "win_rate": win_rate,
        },
        "children": child_results,
        "_all_bids": all_bids,
    }
    return enriched


def _strip_internal(node: dict) -> dict:
    """Remove _all_bids key before returning to frontend."""
    cleaned = {k: v for k, v in node.items() if k != "_all_bids"}
    cleaned["children"] = [_strip_internal(c) for c in cleaned.get("children", [])]
    return cleaned


# ── Endpoints ──────────────────────────────────────────────────


@router.get("/tree")
async def get_org_tree(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get the full org tree with aggregated bid metrics per node."""
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]
    enriched = _aggregate_bid_metrics(ORG_TREE, bids)
    return _strip_internal(enriched)


@router.get("/levels")
async def get_level_metadata(user: dict = Depends(get_current_user)):
    """Get level metadata for frontend rendering."""
    return LEVEL_META


@router.get("/nodes")
async def get_org_nodes(user: dict = Depends(get_current_user)):
    """Get a flat list of all org nodes for dropdown selection."""
    return _flatten_nodes(ORG_TREE)


@router.get("/level/{level}")
async def get_org_level(
    level: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all nodes at a specific org level with bid metrics."""
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]
    enriched_tree = _aggregate_bid_metrics(ORG_TREE, bids)
    stripped = _strip_internal(enriched_tree)
    nodes = _collect_at_level(stripped, level)
    return nodes


@router.get("/{node_id}/metrics")
async def get_org_node_metrics(
    node_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed bid metrics for a specific org node."""
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]

    def _find_node(n, target_id):
        if n["id"] == target_id:
            return n
        for child in n.get("children", []):
            found = _find_node(child, target_id)
            if found:
                return found
        return None

    node = _find_node(ORG_TREE, node_id)
    if not node:
        raise HTTPException(404, "Org node not found")

    enriched = _aggregate_bid_metrics(node, bids)
    result = _strip_internal(enriched)

    node_bids = [b for b in bids if b.get("org_unit_id") == node_id]
    result["direct_bids"] = [
        {
            "id": b["id"],
            "bid_reference": b.get("bid_reference"),
            "client_name": b.get("client_name"),
            "status": b.get("status"),
            "estimated_tcv": b.get("estimated_tcv"),
            "win_probability": b.get("win_probability"),
        }
        for b in node_bids
    ]

    return result
