"""
Vision Analysis Service — Uses multimodal LLM (Gemini) to describe
images, diagrams, charts, and architectural drawings extracted from RFP documents.

Converts visual content into structured text that agents can reason about,
ensuring no information is lost when RFPs contain infographics, network
topology maps, org charts, data flow diagrams, or comparative tables
rendered as images.
"""

import base64
import os
import asyncio
from typing import Any, Dict, List, Optional


class VisionService:
    """Analyse images via Gemini's multimodal vision API."""

    # System prompt for RFP diagram analysis
    SYSTEM_PROMPT = (
        "You are an expert enterprise IT pre-sales analyst specialising in RFP document analysis. "
        "Describe this image in detail for downstream bid-response agents. Focus on:\n"
        "1. WHAT it shows (architecture diagram, org chart, data flow, comparison table, timeline, etc.)\n"
        "2. KEY DATA — extract every label, number, percentage, system name, vendor name, "
        "technology stack component, SLA metric, or KPI visible\n"
        "3. RELATIONSHIPS — describe connections, flows, dependencies, hierarchies\n"
        "4. IMPLICATIONS — what does this mean for scope, pricing, transition planning, or risk\n\n"
        "Be exhaustive. Agents downstream cannot see the image — your description is their ONLY source."
    )

    def __init__(self):
        self._api_key: Optional[str] = None
        self._initialized = False

    def _ensure_init(self):
        """Lazy-load Gemini API key from environment."""
        if self._initialized:
            return
        self._api_key = os.environ.get("GEMINI_API_KEY", "")
        if not self._api_key:
            # Try multi-key config
            for i in range(1, 6):
                key = os.environ.get(f"GEMINI_API_KEY_{i}", "")
                if key:
                    self._api_key = key
                    break
        self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if vision analysis is available."""
        self._ensure_init()
        return bool(self._api_key)

    @staticmethod
    def _encode_image(image_path: str) -> tuple:
        """Read and base64-encode an image file. Returns (base64_str, mime_type)."""
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        mime_type = mime_map.get(ext, "image/png")
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8"), mime_type

    async def describe_image(
        self,
        image_path: str,
        context: str = "",
        max_tokens: int = 1500,
    ) -> str:
        """Send an image to Gemini vision and get a structured description.

        Args:
            image_path: Absolute path to the image file.
            context: Optional text context (e.g. surrounding RFP text) to help
                     the model understand the image better.
            max_tokens: Max output tokens for the description.

        Returns:
            Textual description of the image content.
        """
        self._ensure_init()
        if not self._api_key:
            return f"[IMAGE: {os.path.basename(image_path)} — vision analysis unavailable, no Gemini API key]"

        if not os.path.exists(image_path):
            return f"[IMAGE: {os.path.basename(image_path)} — file not found]"

        try:
            import httpx

            b64_data, mime_type = self._encode_image(image_path)

            prompt = self.SYSTEM_PROMPT
            if context:
                prompt += f"\n\nSurrounding document context:\n{context[:2000]}"

            # Use Gemini REST API directly (avoids needing google-generativeai SDK)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self._api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_data,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.2,
                },
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

            # Extract text from Gemini response
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = " ".join(p.get("text", "") for p in parts if p.get("text"))
                if text.strip():
                    return text.strip()

            return f"[IMAGE: {os.path.basename(image_path)} — vision analysis returned empty result]"

        except Exception as e:
            print(f"[Vision] Error analysing {image_path}: {e}")
            return f"[IMAGE: {os.path.basename(image_path)} — vision analysis failed: {str(e)[:100]}]"

    async def describe_images_batch(
        self,
        image_paths: List[str],
        context: str = "",
        max_concurrent: int = 3,
    ) -> List[Dict[str, Any]]:
        """Analyse multiple images with concurrency control.

        Returns list of [{path, filename, description, page}].
        """
        if not image_paths:
            return []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyse(img_info):
            async with semaphore:
                if isinstance(img_info, dict):
                    path = img_info.get("path", "")
                    page = img_info.get("page", img_info.get("slide", 0))
                else:
                    path = img_info
                    page = 0

                description = await self.describe_image(path, context)
                return {
                    "path": path,
                    "filename": os.path.basename(path),
                    "description": description,
                    "page": page,
                }

        results = await asyncio.gather(*[_analyse(img) for img in image_paths])
        return list(results)

    def format_image_descriptions_for_prompt(
        self,
        descriptions: List[Dict[str, Any]],
    ) -> str:
        """Format image descriptions as structured text for injection into agent prompts.

        Returns a block of text ready to be appended to rfp_text.
        """
        if not descriptions:
            return ""

        lines = ["\n\n=== VISUAL CONTENT EXTRACTED FROM RFP DOCUMENTS ==="]
        lines.append(
            "(The following diagrams, charts, and images were extracted and analysed by AI vision)"
        )
        lines.append("")

        for i, desc in enumerate(descriptions, 1):
            page_info = f" (Page {desc['page']})" if desc.get("page") else ""
            lines.append(
                f"--- DIAGRAM {i}{page_info}: {desc.get('filename', 'unknown')} ---"
            )
            lines.append(desc.get("description", "No description available"))
            lines.append("")

        lines.append("=== END VISUAL CONTENT ===\n")
        return "\n".join(lines)


# Singleton
vision_service = VisionService()
