"""LLM client wrapper for OpenRouter with persistent httpx client."""

import asyncio
import json
import re
import time
from typing import Any
from collections import deque
from datetime import datetime, timedelta

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("llm_client")

FALLBACK_MODELS = [
    "openrouter/free",
    "arcee-ai/trinity-large-preview:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


class LLMClient:
    def __init__(self) -> None:
        self._settings = None
        self.total_calls = 0
        self.total_tokens = 0
        self.total_latency = 0.0
        self.call_history = deque()
        self._current_key_index = 0
        self._blocked_models: set[str] = set()
        self._client: httpx.AsyncClient | None = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _get_client(self) -> httpx.AsyncClient:
        """Return a shared persistent client, creating it if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.settings.llm_timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def _api_keys(self) -> list[str]:
        keys = [self.settings.openrouter_api_key]
        if self.settings.openrouter_api_key_backup:
            keys.append(self.settings.openrouter_api_key_backup)
        return keys

    def _get_current_key(self) -> str:
        keys = self._api_keys
        return keys[self._current_key_index % len(keys)]

    def _rotate_key(self):
        keys = self._api_keys
        if len(keys) > 1:
            self._current_key_index = (self._current_key_index + 1) % len(keys)

    def _get_model(self) -> str:
        primary = self.settings.llm_model
        if primary not in self._blocked_models:
            return primary
        for m in FALLBACK_MODELS:
            if m not in self._blocked_models:
                return m
        self._blocked_models.clear()
        return primary

    async def _check_rate_limit(self):
        now = datetime.now()
        cutoff = now - timedelta(seconds=60)
        while self.call_history and self.call_history[0] < cutoff:
            self.call_history.popleft()
        if len(self.call_history) >= 20:
            oldest_call = self.call_history[0]
            wait_time = 60 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                log.warning("rate_limit_wait", wait_seconds=f"{wait_time:.1f}")
                await asyncio.sleep(wait_time)
        self.call_history.append(datetime.now())

    async def query(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | list:
        await self._check_rate_limit()

        last_error = None
        for attempt in range(4):
            try:
                return await self._do_query(system_prompt, user_prompt, temperature, max_tokens)
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    current_model = self._get_model()
                    log.warning("model_rate_limited", model=current_model, attempt=attempt + 1)
                    self._blocked_models.add(current_model)
                    self._rotate_key()
                    await asyncio.sleep(1)
                    continue
                raise
            except (httpx.TimeoutException, TimeoutError) as e:
                last_error = e
                log.warning("llm_timeout", attempt=attempt + 1)
                self._rotate_key()
                await asyncio.sleep(2)
                continue
            except Exception:
                raise

        log.error("llm_all_attempts_failed", attempts=4)
        raise last_error if last_error else RuntimeError("LLM query failed")

    async def _do_query(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any] | list:
        temp = temperature or self.settings.llm_temperature
        tokens = max_tokens or self.settings.llm_max_tokens
        api_key = self._get_current_key()
        model = self._get_model()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": self.settings.app_name,
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temp,
            "max_tokens": tokens,
        }

        start = time.monotonic()
        client = self._get_client()
        resp = await client.post(
            f"{self.settings.openrouter_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        elapsed = time.monotonic() - start
        self.total_calls += 1
        self.total_latency += elapsed
        self.total_tokens += data.get("usage", {}).get("total_tokens", 0)

        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content")
        log.debug("llm_ok", model=model, latency=f"{elapsed:.1f}s")

        if not raw_content:
            log.warning("llm_empty_response", model=model)
            return {"raw_response": "", "parse_error": True}

        return self._parse_json(raw_content)

    def _parse_json(self, raw: str) -> dict[str, Any] | list:
        text = raw.strip()
        if "<think>" in text:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if text.startswith("```"):
            lines = text.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            log.warning("llm_json_parse_failed", raw=text[:200])
            return {"raw_response": text, "parse_error": True}

    def get_stats(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_latency_seconds": round(self.total_latency, 2),
            "avg_latency_seconds": round(self.total_latency / max(self.total_calls, 1), 2),
            "current_model": self._get_model(),
        }


llm_client = LLMClient()
