"""
Documents API — file upload, management, and text extraction.
Persists all document metadata to the BidDocument database table.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import get_current_user
from app.services.storage import storage_service
from app.database import get_db
from app.models.bid import BidDocument

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def _doc_to_dict(doc: BidDocument) -> dict:
    return {
        "id": doc.id,
        "bid_id": doc.bid_id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "file_type": doc.file_type,
        "file_size": doc.file_size_bytes,
        "document_type": doc.document_type,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    bid_id: str = Form(""),
    document_type: str = Form("rfp"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document and extract text content. Persists to DB."""
    content = await file.read()
    doc_id = str(uuid.uuid4())

    # Save via storage service
    stored = storage_service.save_file(
        content=content,
        filename=file.filename,
        subdirectory=document_type,
        file_id=doc_id,
    )

    # Extract text
    text = ""
    try:
        from app.knowledge.upload import extract_text_from_file

        text = extract_text_from_file(stored["path"])
    except Exception:
        pass

    # Persist to database
    db_doc = BidDocument(
        id=doc_id,
        bid_id=bid_id,
        filename=file.filename,
        file_path=stored["path"],
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        document_type=document_type,
        uploaded_by=user.get("id", user.get("name", "Unknown")),
    )
    db.add(db_doc)
    await db.commit()

    result = _doc_to_dict(db_doc)
    result["text_content"] = text[:5000] if text else ""
    result["text_length"] = len(text)
    return result


@router.get("/")
async def list_documents(
    bid_id: Optional[str] = None,
    document_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List uploaded documents with optional filtering."""
    query = select(BidDocument).order_by(BidDocument.uploaded_at.desc())
    if bid_id:
        query = query.where(BidDocument.bid_id == bid_id)
    if document_type:
        query = query.where(BidDocument.document_type == document_type)
    result = await db.execute(query)
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BidDocument).where(BidDocument.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return _doc_to_dict(doc)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BidDocument).where(BidDocument.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")
    # Delete physical file
    try:
        storage_service.delete_file(doc.file_path)
    except Exception:
        pass
    # Delete DB record
    await db.execute(delete(BidDocument).where(BidDocument.id == doc_id))
    await db.commit()
    return {"status": "deleted", "id": doc_id}
