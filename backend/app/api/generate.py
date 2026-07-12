"""
Document Generation & Download API.
Generates comprehensive bid response documents (Word) from bid data.
Persists generated document metadata to the GeneratedDocument database table.
"""

import os
import uuid
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import get_current_user
from app.database import get_db
from app.services.bid_repository import BidRepository
from app.models.bid import GeneratedDocument

router = APIRouter(prefix="/api/generate", tags=["Document Generation"])

OUTPUT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "knowledge_base", "outputs"
    )
)


def _doc_to_dict(doc: GeneratedDocument) -> dict:
    return {
        "id": doc.id,
        "bid_id": doc.bid_id,
        "type": doc.document_type,
        "format": doc.file_format,
        "filename": doc.filename,
        "path": doc.file_path,
        "generated_at": doc.generated_at.isoformat() if doc.generated_at else None,
        "generated_by": doc.generated_by,
        "download_url": f"/api/generate/download/{doc.id}",
    }


@router.post("/{bid_id}/sow")
async def generate_sow_doc(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a comprehensive Bid Response Document (Word) for the bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)

    from app.document_gen.word_generator import generate_sow

    out_dir = os.path.join(OUTPUT_DIR, bid_id)
    result = generate_sow(bid, out_dir)

    if result.get("status") != "success":
        raise HTTPException(500, result.get("message", "Document generation failed"))

    doc_id = str(uuid.uuid4())
    db_doc = GeneratedDocument(
        id=doc_id,
        bid_id=bid_id,
        document_type="bid_response",
        file_format="docx",
        filename=result["filename"],
        file_path=result["path"],
        generated_by=user.get("id", user.get("name", "System")),
    )
    db.add(db_doc)
    await db.commit()

    return {
        **result,
        "doc_id": doc_id,
        "download_url": f"/api/generate/download/{doc_id}",
    }


@router.post("/{bid_id}/ppt")
async def generate_ppt_doc(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a PowerPoint executive presentation for the bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)

    from app.document_gen.ppt_generator import generate_proposal_deck

    out_dir = os.path.join(OUTPUT_DIR, bid_id)
    result = generate_proposal_deck(bid, out_dir)

    if result.get("status") != "success":
        raise HTTPException(500, result.get("message", "PPT generation failed"))

    doc_id = str(uuid.uuid4())
    db_doc = GeneratedDocument(
        id=doc_id,
        bid_id=bid_id,
        document_type="presentation",
        file_format="pptx",
        filename=result["filename"],
        file_path=result["path"],
        generated_by=user.get("id", user.get("name", "System")),
    )
    db.add(db_doc)
    await db.commit()

    return {
        **result,
        "doc_id": doc_id,
        "download_url": f"/api/generate/download/{doc_id}",
    }


@router.post("/{bid_id}/excel")
async def generate_excel_doc(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an Excel commercial model for the bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)

    from app.document_gen.excel_generator import generate_commercial_model

    out_dir = os.path.join(OUTPUT_DIR, bid_id)
    result = generate_commercial_model(bid, out_dir)

    if result.get("status") != "success":
        raise HTTPException(500, result.get("message", "Excel generation failed"))

    doc_id = str(uuid.uuid4())
    db_doc = GeneratedDocument(
        id=doc_id,
        bid_id=bid_id,
        document_type="commercial_model",
        file_format="xlsx",
        filename=result["filename"],
        file_path=result["path"],
        generated_by=user.get("id", user.get("name", "System")),
    )
    db.add(db_doc)
    await db.commit()

    return {
        **result,
        "doc_id": doc_id,
        "download_url": f"/api/generate/download/{doc_id}",
    }


@router.get("/{bid_id}/generated")
async def list_generated_docs(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated documents for a bid."""
    result = await db.execute(
        select(GeneratedDocument)
        .where(GeneratedDocument.bid_id == bid_id)
        .order_by(GeneratedDocument.generated_at.desc())
    )
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@router.get("/download/{doc_id}")
async def download_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Download a generated document."""
    result = await db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == doc_id)
    )
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(404, "Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(404, "File not found on disk")

    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=media_types.get(doc.file_format, "application/octet-stream"),
    )
