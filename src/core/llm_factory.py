# Fábrica de LLMs com roteamento barato/premium e fallback automático.
# Usa gpt-4.1-nano pra maioria das chamadas, escala pro gpt-4.1 se falhar.
# Cache Redis opcional pra evitar chamadas repetidas.

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import redis
from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.config import (
    AZURE_DEPLOYMENT_CHEAP,
    AZURE_DEPLOYMENT_PREMIUM,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    GEMINI_CHEAP_MODEL,
    GEMINI_PREMIUM_MODEL,
    GOOGLE_API_KEY,
    LLM_CHEAP_MODEL,
    LLM_PREMIUM_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    REDIS_HOST,
    REDIS_PORT,
)

logger = logging.getLogger("abi_assistant.llm_factory")

# TTL do cache Redis (1 hora)
_CACHE_TTL_SECONDS: int = 3600


class LLMFactory:
    """Gerenciador de LLMs com dois tiers e fallback automático.

    - Cheap (ex: gpt-4.1-nano): ~95% das chamadas.
    - Premium (ex: gpt-4.1): fallback ou quando forçado.
    - Cache Redis opcional (TTL 1h) pra evitar chamadas repetidas.
    - Multi-provider: OpenAI, Azure, Gemini via env var.
    """

    def __init__(self) -> None:
        self._provider = LLM_PROVIDER.lower()

        if self._provider == "azure":
            self._cheap = AzureChatOpenAI(
                azure_deployment=AZURE_DEPLOYMENT_CHEAP,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=0,
                max_retries=2,
                request_timeout=15,
            )
            self._premium = AzureChatOpenAI(
                azure_deployment=AZURE_DEPLOYMENT_PREMIUM,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=0,
                max_retries=2,
                request_timeout=15,
            )
            cheap_label = f"azure/{AZURE_DEPLOYMENT_CHEAP}"
            premium_label = f"azure/{AZURE_DEPLOYMENT_PREMIUM}"
        elif self._provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._cheap = ChatGoogleGenerativeAI(
                model=GEMINI_CHEAP_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0,
                max_retries=2,
                timeout=15,
            )
            self._premium = ChatGoogleGenerativeAI(
                model=GEMINI_PREMIUM_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0,
                max_retries=2,
                timeout=15,
            )
            cheap_label = GEMINI_CHEAP_MODEL
            premium_label = GEMINI_PREMIUM_MODEL
        else:
            self._cheap = ChatOpenAI(
                model=LLM_CHEAP_MODEL,
                temperature=0,
                api_key=OPENAI_API_KEY,
                max_retries=2,
                request_timeout=15,
            )
            self._premium = ChatOpenAI(
                model=LLM_PREMIUM_MODEL,
                temperature=0,
                api_key=OPENAI_API_KEY,
                max_retries=2,
                request_timeout=15,
            )
            cheap_label = LLM_CHEAP_MODEL
            premium_label = LLM_PREMIUM_MODEL

        self._cache = self._connect_redis()

        self._metrics: dict[str, Any] = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        logger.info(
            "LLMFactory ready – provider=%s  cheap=%s  premium=%s  cache=%s",
            self._provider,
            cheap_label,
            premium_label,
            "redis" if self._cache else "disabled",
        )

    @staticmethod
    def _connect_redis() -> redis.Redis | None:
        """Tenta conectar ao Redis; retorna None se falhar (degrada sem cache)."""
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            client.ping()
            logger.info("Redis cache connected at %s:%s", REDIS_HOST, REDIS_PORT)
            return client
        except Exception:
            logger.warning("Redis unavailable – running without LLM cache.")
            return None

    @staticmethod
    def _cache_key(prompt: str) -> str:
        return f"llm:cache:{hashlib.sha256(prompt.encode()).hexdigest()}"

    def _get_cached(self, prompt: str) -> str | None:
        if self._cache is None:
            return None
        try:
            return self._cache.get(self._cache_key(prompt))
        except Exception:
            return None

    def _set_cached(self, prompt: str, response: str) -> None:
        if self._cache is None:
            return
        try:
            self._cache.setex(self._cache_key(prompt), _CACHE_TTL_SECONDS, response)
        except Exception:
            logger.debug("Failed to write LLM cache – skipping.")

    @property
    def cheap(self) -> BaseChatModel:
        return self._cheap

    @property
    def premium(self) -> BaseChatModel:
        return self._premium

    def invoke_with_fallback(
        self,
        prompt: str,
        *,
        force_premium: bool = False,
        use_cache: bool = True,
    ) -> str:
        """Envia prompt com fallback automático: cache → cheap → premium.

        Levanta RuntimeError se ambos os tiers falharem.
        """
        # 1. verifica cache
        if use_cache:
            cached = self._get_cached(prompt)
            if cached is not None:
                logger.info("Cache HIT – returning stored response.")
                self._metrics["cache_hits"] += 1
                self._metrics["requests_total"] += 1
                return cached

        self._metrics["cache_misses"] += 1
        self._metrics["requests_total"] += 1
        start = time.perf_counter()

        # 2. tenta tier barato (salvo se forçou premium)
        if not force_premium:
            try:
                logger.info("Invoking CHEAP model (%s)…", LLM_CHEAP_MODEL)
                result = self._cheap.invoke(prompt)
                text = result.content if hasattr(result, "content") else str(result)
                elapsed = (time.perf_counter() - start) * 1000
                self._metrics["cheap_calls"] += 1
                self._metrics["total_latency_ms"] += elapsed
                logger.info("Cheap model responded in %.0f ms.", elapsed)
                if use_cache:
                    self._set_cached(prompt, text)
                return text
            except Exception as exc:
                logger.warning("Cheap model failed (%s) – falling back to premium.", exc)

        # 3. fallback pro premium
        try:
            logger.info("Invoking PREMIUM model (%s)…", LLM_PREMIUM_MODEL)
            result = self._premium.invoke(prompt)
            text = result.content if hasattr(result, "content") else str(result)
            elapsed = (time.perf_counter() - start) * 1000
            self._metrics["premium_calls"] += 1
            self._metrics["total_latency_ms"] += elapsed
            logger.info("Premium model responded in %.0f ms.", elapsed)
            if use_cache:
                self._set_cached(prompt, text)
            return text
        except Exception as exc:
            self._metrics["errors"] += 1
            logger.error("Both LLM tiers failed. Last error: %s", exc)
            raise RuntimeError("All LLM tiers exhausted. Please check API keys and quotas.") from exc

    def invoke_structured(
        self,
        prompt: str,
        *,
        force_premium: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Invoca LLM e parseia a resposta como JSON.

        Trata code fences de markdown e faz fallback pra {"raw_response": text}.
        """
        raw = self.invoke_with_fallback(prompt, force_premium=force_premium, use_cache=use_cache)
        # tenta extrair JSON da resposta
        try:
            # trata possíveis code fences de markdown
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM response is not valid JSON – wrapping as text.")
            return {"raw_response": raw}

    @property
    def metrics(self) -> dict[str, Any]:
        """Métricas de uso pra observabilidade (cache hit ratio, latência média, provider)."""
        m = dict(self._metrics)
        total = m["requests_total"]
        calls = m["cheap_calls"] + m["premium_calls"]
        m["cache_hit_ratio"] = round(m["cache_hits"] / total, 3) if total > 0 else 0.0
        m["avg_latency_ms"] = round(m["total_latency_ms"] / calls, 1) if calls > 0 else 0.0
        m["provider"] = self._provider
        return m
