"""
Knowledge Base API — persistent DB-backed storage.
All documents, collections, and metadata persisted via KBDocument model.
"""

import uuid
import os
from typing import Optional
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import StreamingResponse
import asyncio
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.knowledge import KBDocument, KBCollectionType

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])

# Static collection metadata (display info — doc counts come from DB)
COLLECTION_META = {
    "rfps": {"name": "RFPs", "desc": "Past RFP documents"},
    "sows": {"name": "SOWs", "desc": "Past scope of work documents"},
    "rate_cards": {"name": "Rate Cards", "desc": "Versioned rate cards by geo"},
    "scope_templates": {"name": "Scope Templates", "desc": "Standard scope templates"},
    "solution_templates": {
        "name": "Solution Templates",
        "desc": "Architecture & operating models",
    },
    "commercial_models": {
        "name": "Commercial Models",
        "desc": "Past commercial models",
    },
    "clause_library": {"name": "Clause Library", "desc": "Approved legal clauses"},
    "partner_profiles": {
        "name": "Partner Profiles",
        "desc": "Partner capability profiles",
    },
    "client_profiles": {"name": "Client Profiles", "desc": "Client preference memory"},
    "win_loss_data": {
        "name": "Win/Loss Data",
        "desc": "Bid outcomes with tagged decisions",
    },
    "brand": {"name": "Brand Assets", "desc": "Brand guidelines and assets"},
    "ticket_taxonomies": {
        "name": "Ticket Taxonomies",
        "desc": "AMS ticket classification",
    },
    "estimating_actuals": {
        "name": "Estimating Actuals",
        "desc": "Scoped vs actual data",
    },
}

# In-memory progress tracker for embedding jobs
EMBEDDING_JOBS = {}


def _doc_to_dict(doc: KBDocument) -> dict:
    return {
        "id": doc.id,
        "collection": doc.collection.value
        if hasattr(doc.collection, "value")
        else doc.collection,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "file_type": doc.file_type,
        "file_size": doc.file_size_bytes,
        "product": doc.product,
        "engagement_type": doc.engagement_type,
        "client_industry": doc.client_industry,
        "outcome": doc.outcome,
        "version": doc.version,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@router.get("/collections")
async def list_collections(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all KB collections with document counts from DB."""
    # Get doc counts per collection
    count_query = select(KBDocument.collection, func.count(KBDocument.id)).group_by(
        KBDocument.collection
    )
    result = await db.execute(count_query)
    counts = {
        str(row[0].value if hasattr(row[0], "value") else row[0]): row[1]
        for row in result.all()
    }

    collections = []
    for coll_id, meta in COLLECTION_META.items():
        collections.append(
            {
                "id": coll_id,
                "name": meta["name"],
                "desc": meta["desc"],
                "count": counts.get(coll_id, 0),
            }
        )
    return collections


@router.get("/documents")
async def list_documents(
    collection: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List KB documents, optionally filtered by collection."""
    query = select(KBDocument).order_by(KBDocument.uploaded_at.desc())
    if collection:
        try:
            coll_enum = KBCollectionType(collection)
            query = query.where(KBDocument.collection == coll_enum)
        except ValueError:
            return []
    result = await db.execute(query)
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
    background_tasks: BackgroundTasks = None,
    product: str = Form(""),
    engagement_type: str = Form(""),
    client_industry: str = Form(""),
    outcome: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to the Knowledge Base. Persists to DB."""
    # Validate collection
    try:
        coll_enum = KBCollectionType(collection)
    except ValueError:
        raise HTTPException(
            400,
            f"Invalid collection: {collection}. Valid: {[c.value for c in KBCollectionType]}",
        )

    doc_id = str(uuid.uuid4())
    content = await file.read()

    # Save file to disk
    save_dir = os.path.join(settings.UPLOAD_DIR, collection)
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"{doc_id}_{file.filename}")
    with open(path, "wb") as f:
        f.write(content)

    # Extract text content
    text_content = ""
    try:
        from app.knowledge.upload import extract_text

        text_content = extract_text(path, file.filename)
    except Exception:
        pass

    # Persist to database
    db_doc = KBDocument(
        id=doc_id,
        collection=coll_enum,
        filename=file.filename,
        file_path=path,
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        product=product or None,
        engagement_type=engagement_type or None,
        client_industry=client_industry or None,
        outcome=outcome,
        content_text=text_content[:10000] if text_content else None,
        uploaded_by=user.get("id", user.get("name", "Unknown")),
        tags={},
    )
    db.add(db_doc)
    await db.commit()

    result = _doc_to_dict(db_doc)

    # Spawn background embedding job
    job_id = str(uuid.uuid4())
    EMBEDDING_JOBS[job_id] = {"status": "pending", "total": 0, "processed": 0}
    result["embedding_job_id"] = job_id

    async def _embed_background(text, d_id, c, f, p, i, o, j_id):
        try:
            from app.knowledge.embeddings import embedding_service
            from app.knowledge.rag import rag_pipeline

            if text and len(text) > 50:
                chunks = embedding_service.chunk_text(text, chunk_size=400, overlap=50)
                chunks_to_process = chunks[:50]
                EMBEDDING_JOBS[j_id]["total"] = len(chunks_to_process)
                EMBEDDING_JOBS[j_id]["status"] = "processing"

                for idx, chunk in enumerate(chunks_to_process):
                    embedding = await embedding_service.embed_async(chunk)
                    rag_pipeline.add_embedding(
                        doc_id=f"{d_id}_chunk_{idx}",
                        chunk_text=chunk,
                        embedding=embedding,
                        metadata={
                            "collection": c,
                            "filename": f,
                            "product": p,
                            "industry": i,
                            "outcome": o or "",
                            "chunk_index": idx,
                        },
                    )
                    EMBEDDING_JOBS[j_id]["processed"] += 1
                    # Small sleep to yield to event loop
                    await asyncio.sleep(0.01)

                EMBEDDING_JOBS[j_id]["status"] = "completed"
            else:
                EMBEDDING_JOBS[j_id]["status"] = "skipped"
        except Exception as e:
            EMBEDDING_JOBS[j_id]["status"] = "failed"
            EMBEDDING_JOBS[j_id]["error"] = str(e)

    if background_tasks:
        background_tasks.add_task(
            _embed_background,
            text_content,
            doc_id,
            collection,
            file.filename,
            product,
            client_industry,
            outcome,
            job_id,
        )
    else:
        # Fallback if no BackgroundTasks
        asyncio.create_task(
            _embed_background(
                text_content,
                doc_id,
                collection,
                file.filename,
                product,
                client_industry,
                outcome,
                job_id,
            )
        )

    return result


@router.get("/embed/progress/{job_id}")
async def get_embed_progress(job_id: str):
    """SSE endpoint for streaming embedding progress."""

    async def event_generator():
        while True:
            job = EMBEDDING_JOBS.get(job_id)
            if not job:
                yield 'data: {"status": "not_found"}\n\n'
                break

            import json

            yield f"data: {json.dumps(job)}\n\n"

            if job["status"] in ("completed", "failed", "skipped"):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a KB document from DB and disk."""
    result = await db.execute(select(KBDocument).where(KBDocument.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Not found")

    # Delete file from disk
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass

    await db.execute(delete(KBDocument).where(KBDocument.id == doc_id))
    await db.commit()
    return {"status": "deleted"}


# ── Institutional Learnings API ──


@router.get("/learnings/stats")
async def learning_stats(user: dict = Depends(get_current_user)):
    from app.knowledge.learning_store import get_learning_stats

    return get_learning_stats()


@router.get("/learnings")
async def list_learnings(
    agent: Optional[str] = None,
    learning_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    from app.knowledge.learning_store import get_all_learnings

    learnings = get_all_learnings()
    if agent:
        learnings = [l for l in learnings if l["agent_name"] == agent]
    if learning_type:
        learnings = [l for l in learnings if l["learning_type"] == learning_type]
    return learnings


@router.delete("/learnings/{learning_id}")
async def delete_learning(learning_id: str, user: dict = Depends(get_current_user)):
    from app.knowledge.learning_store import delete_learning as del_learning

    if del_learning(learning_id):
        return {"status": "deleted"}
    raise HTTPException(404, "Learning not found")


# ── RAG Stats ──────────────────────────────────────────────────────────────


@router.get("/stats")
async def knowledge_stats(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Return RAG embedding cache stats + DB document counts per collection."""
    from app.knowledge.rag import rag_pipeline
    from sqlalchemy import func

    rag_stats = rag_pipeline.stats()

    # DB doc counts per collection
    row_counts = await db.execute(
        select(KBDocument.collection, func.count(KBDocument.id)).group_by(
            KBDocument.collection
        )
    )
    db_counts = {str(col): cnt for col, cnt in row_counts.all()}

    total_docs = sum(db_counts.values())
    await db.execute(func.sum(KBDocument.file_size_bytes))
    total_size_val = (
        await db.execute(select(func.coalesce(func.sum(KBDocument.file_size_bytes), 0)))
    ).scalar_one()

    return {
        "rag": rag_stats,
        "db": {
            "total_documents": total_docs,
            "total_size_bytes": total_size_val,
            "by_collection": db_counts,
        },
        "collections": {
            col: {**meta, "doc_count": db_counts.get(col, 0)}
            for col, meta in COLLECTION_META.items()
        },
    }
