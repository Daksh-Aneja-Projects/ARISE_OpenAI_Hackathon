"""
Core LLM Service - OpenAI Exclusive Setup

This module wraps the OpenAI Python client to provide a unified interface for all agents.
All fallback providers and complex routing logic have been removed.

Models:
- "gpt-4o" is used for critical/analytical reasoning
- "gpt-4o-mini" is used for volume/lightweight parsing
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.total_calls = 0
        self.total_tokens_used = 0
        self._override_openai_key = None
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        key = self._override_openai_key or settings.OPENAI_API_KEY
        if key:
            self._client = AsyncOpenAI(api_key=key)
        else:
            self._client = None

    def set_override_keys(self, openai_key: str = ""):
        if openai_key:
            self._override_openai_key = openai_key
            self._initialize_client()

    def clear_override_keys(self):
        self._override_openai_key = None
        self._initialize_client()

    def get_config_status(self) -> Dict[str, Any]:
        has_key = bool(self._override_openai_key or settings.OPENAI_API_KEY)
        return {
            "configured": has_key,
            "provider": "openai",
            "models": ["gpt-4o", "gpt-4o-mini"],
            "pool_size": 1 if has_key else 0,
            "total_calls": self.total_calls,
            "total_tokens_used": self.total_tokens_used,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        max_tokens: int = 4000,
        temperature: float = 0.2,
        agent_tier: str = "analytical",
        require_json: bool = False,
    ) -> str:
        if not self._client:
            raise ValueError(
                "No OpenAI API key configured. Please add one in Settings or .env."
            )

        model = (
            settings.LLM_MODEL
            if agent_tier in ["critical", "analytical"]
            else settings.LLM_FAST_MODEL
        )

        self.total_calls += 1

        start_time = time.time()
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if require_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self._client.chat.completions.create(**kwargs)

            usage = response.usage
            if usage:
                self.total_tokens_used += usage.total_tokens

            elapsed = time.time() - start_time
            logger.info(
                f"[LLM] OpenAI generated response in {elapsed:.2f}s using {model}"
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[LLM] OpenAI generation failed: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant that always responds in valid JSON.",
        max_tokens: int = 4000,
        temperature: float = 0.1,
        tier: str = "analytical",
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_tier=tier,
            require_json=True,
        )
        try:
            import json

            return json.loads(result)
        except Exception as e:
            logger.error(f"[LLM] Failed to parse structured JSON: {e}")
            # Fallback for when OpenAI returns markdown-wrapped JSON
            try:
                if "```json" in result:
                    clean = result.split("```json")[1].split("```")[0].strip()
                    return json.loads(clean)
                elif "```" in result:
                    clean = result.split("```")[1].split("```")[0].strip()
                    return json.loads(clean)
            except Exception:
                pass
            return {}


llm_service = LLMService()
