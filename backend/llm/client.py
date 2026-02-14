"""
LLM Client – thin wrapper around glm-bridge (OpenAI-compatible endpoint).

Usage:
    client = LLMClient()
    result = await client.chat("Analyze this job posting...", system="You are an expert.")
    structured = await client.chat_json(prompt, system, schema_hint="...")
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("upwork-dna.llm")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
GLM_BRIDGE_URL = "http://localhost:8765"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.15  # Low for structured/analytical tasks — deterministic scoring
REQUEST_TIMEOUT = 120.0  # seconds
MAX_RETRIES = 2
RETRY_DELAY = 3.0  # seconds


class LLMError(Exception):
    """Base exception for LLM operations."""
    pass


class LLMConnectionError(LLMError):
    """glm-bridge is unreachable."""
    pass


class LLMResponseError(LLMError):
    """glm-bridge returned an error."""
    pass


class LLMClient:
    """Async client for glm-bridge at localhost:8765."""

    def __init__(
        self,
        base_url: str = GLM_BRIDGE_URL,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    async def health(self) -> dict:
        """Check glm-bridge health."""
        try:
            http = await self._get_http()
            r = await http.get("/health")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise LLMConnectionError(f"glm-bridge unreachable: {e}") from e

    async def is_available(self) -> bool:
        try:
            h = await self.health()
            return h.get("status") in ("healthy", "degraded")
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Core chat
    # ------------------------------------------------------------------
    async def chat(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a chat completion request and return the assistant's text."""
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if system:
            payload["system"] = system

        http = await self._get_http()

        last_error = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                t0 = time.time()
                r = await http.post("/v1/chat/completions", json=payload)
                elapsed = time.time() - t0
                logger.info(f"LLM request completed in {elapsed:.1f}s (attempt {attempt})")

                if r.status_code == 503:
                    raise LLMConnectionError("glm-bridge has no available provider")
                r.raise_for_status()

                data = r.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMResponseError("Empty choices in LLM response")

                return choices[0]["message"]["content"]

            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = LLMConnectionError(f"Cannot reach glm-bridge: {e}")
                if attempt <= MAX_RETRIES:
                    logger.warning(f"LLM connection failed, retrying in {RETRY_DELAY}s...")
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise last_error from e

            except httpx.HTTPStatusError as e:
                last_error = LLMResponseError(f"HTTP {e.response.status_code}: {e.response.text}")
                if e.response.status_code in (429, 502, 503) and attempt <= MAX_RETRIES:
                    logger.warning(f"LLM rate-limited/unavailable, retrying in {RETRY_DELAY}s...")
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise last_error from e

            except LLMError:
                raise

            except Exception as e:
                raise LLMResponseError(f"Unexpected error: {e}") from e

        raise last_error or LLMError("Max retries exceeded")

    # ------------------------------------------------------------------
    # Structured JSON chat
    # ------------------------------------------------------------------
    async def chat_json(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Send a chat request that expects a JSON response.
        Extracts the first JSON object/array from the response text.
        """
        temp = temperature if temperature is not None else 0.2  # Lower for structured output

        # Append JSON instruction to system prompt
        json_system = (system or "") + (
            "\n\nIMPORTANT: You MUST respond with valid JSON only. "
            "No markdown code fences, no explanatory text before or after. "
            "Just the raw JSON object."
        )

        raw = await self.chat(
            prompt,
            system=json_system.strip(),
            model=model,
            max_tokens=max_tokens,
            temperature=temp,
        )

        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Extract JSON from LLM response, handling markdown fences and extra text."""
        # Strip markdown code fences
        cleaned = text.strip()

        # Try: ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to find first { ... } or [ ... ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = cleaned.find(start_char)
            if start == -1:
                continue
            # Find matching closing bracket
            depth = 0
            for i in range(start, len(cleaned)):
                if cleaned[i] == start_char:
                    depth += 1
                elif cleaned[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(cleaned[start : i + 1])
                        except json.JSONDecodeError:
                            break

        raise LLMResponseError(f"Could not extract valid JSON from LLM response: {text[:300]}")
