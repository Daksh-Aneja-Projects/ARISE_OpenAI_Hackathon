"""
File Storage Service — abstraction for local and cloud file storage.
Phase 1: local filesystem. Phase 2+: Azure Blob Storage.
"""

import os
import uuid
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from app.config import settings


class StorageService:
    """File storage abstraction layer."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(
        self,
        content: bytes,
        filename: str,
        subdirectory: str = "",
        file_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a file to storage. Returns metadata."""
        fid = file_id or str(uuid.uuid4())
        safe_name = f"{fid}_{filename}"
        target_dir = (
            os.path.join(self.base_dir, subdirectory) if subdirectory else self.base_dir
        )
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, safe_name)

        with open(path, "wb") as f:
            f.write(content)

        return {
            "file_id": fid,
            "filename": filename,
            "stored_name": safe_name,
            "path": path,
            "size_bytes": len(content),
            "subdirectory": subdirectory,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

    def read_file(self, path: str) -> Optional[bytes]:
        """Read a file from storage."""
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def delete_file(self, path: str) -> bool:
        """Delete a file from storage."""
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_files(self, subdirectory: str = "") -> list:
        """List files in a subdirectory."""
        target_dir = (
            os.path.join(self.base_dir, subdirectory) if subdirectory else self.base_dir
        )
        if not os.path.exists(target_dir):
            return []
        return [
            {
                "name": f,
                "path": os.path.join(target_dir, f),
                "size": os.path.getsize(os.path.join(target_dir, f)),
            }
            for f in os.listdir(target_dir)
            if os.path.isfile(os.path.join(target_dir, f))
        ]

    def get_collection_path(self, collection: str) -> str:
        """Get the full path for a KB collection directory."""
        path = os.path.join(self.base_dir, collection)
        os.makedirs(path, exist_ok=True)
        return path


# Singleton
storage_service = StorageService()
