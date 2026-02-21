# Testes da LLMFactory: fallback cheap→premium, cache Redis e invoke_structured.
# Tudo mockado (sem API key nem Redis real).

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFallback:
    """Testa roteamento de custo: cheap primeiro, premium se falhar."""

    @patch("src.core.llm_factory.LLMFactory._connect_redis", return_value=None)
    @patch("src.core.llm_factory.ChatOpenAI")
    def test_cheap_succeeds(self, mock_chat_cls, _mock_redis):
        cheap_instance = MagicMock()
        cheap_instance.invoke.return_value = MagicMock(content="resposta barata")
        premium_instance = MagicMock()

        mock_chat_cls.side_effect = [cheap_instance, premium_instance]

        from src.core.llm_factory import LLMFactory

        with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}):
            factory = LLMFactory.__new__(LLMFactory)
            factory._cheap = cheap_instance
            factory._premium = premium_instance
            factory._cache = None
            factory._provider = "openai"
            factory._metrics = {
                "requests_total": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cheap_calls": 0,
                "premium_calls": 0,
                "errors": 0,
                "total_latency_ms": 0.0,
            }

        result = factory.invoke_with_fallback("teste", use_cache=False)

        assert result == "resposta barata"
        cheap_instance.invoke.assert_called_once()
        premium_instance.invoke.assert_not_called()
        assert factory._metrics["cheap_calls"] == 1
        assert factory._metrics["premium_calls"] == 0

    def test_cheap_fails_premium_succeeds(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        cheap = MagicMock()
        cheap.invoke.side_effect = Exception("Rate limit exceeded")
        premium = MagicMock()
        premium.invoke.return_value = MagicMock(content="resposta premium")

        factory._cheap = cheap
        factory._premium = premium
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_with_fallback("teste", use_cache=False)

        assert result == "resposta premium"
        assert factory._metrics["premium_calls"] == 1

    def test_both_fail_raises_runtime_error(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        cheap = MagicMock()
        cheap.invoke.side_effect = Exception("cheap dead")
        premium = MagicMock()
        premium.invoke.side_effect = Exception("premium dead")

        factory._cheap = cheap
        factory._premium = premium
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        with pytest.raises(RuntimeError, match="All LLM tiers exhausted"):
            factory.invoke_with_fallback("teste", use_cache=False)

        assert factory._metrics["errors"] == 1

    def test_force_premium_skips_cheap(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        cheap = MagicMock()
        premium = MagicMock()
        premium.invoke.return_value = MagicMock(content="premium direto")

        factory._cheap = cheap
        factory._premium = premium
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_with_fallback("teste", force_premium=True, use_cache=False)

        assert result == "premium direto"
        cheap.invoke.assert_not_called()
        assert factory._metrics["premium_calls"] == 1


class TestCache:
    """Testa Redis cache hit/miss."""

    def test_cache_hit_returns_stored(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"

        mock_redis = MagicMock()
        mock_redis.get.return_value = "cached response"
        factory._cache = mock_redis

        factory._cheap = MagicMock()
        factory._premium = MagicMock()
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_with_fallback("pergunta test")

        assert result == "cached response"
        factory._cheap.invoke.assert_not_called()
        assert factory._metrics["cache_hits"] == 1

    def test_cache_miss_calls_llm(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        factory._cache = mock_redis

        cheap = MagicMock()
        cheap.invoke.return_value = MagicMock(content="nova resposta")
        factory._cheap = cheap
        factory._premium = MagicMock()
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_with_fallback("pergunta nova")

        assert result == "nova resposta"
        cheap.invoke.assert_called_once()
        assert factory._metrics["cache_misses"] == 1
        # deve ter cacheado o resultado
        mock_redis.setex.assert_called_once()


class TestInvokeStructured:
    """Testa parsing de JSON na invoke_structured."""

    def test_parses_clean_json(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        cheap = MagicMock()
        cheap.invoke.return_value = MagicMock(content='{"approved": true, "category": "allowed", "reason": "OK"}')
        factory._cheap = cheap
        factory._premium = MagicMock()
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_structured("prompt json")

        assert result["approved"] is True
        assert result["category"] == "allowed"

    def test_handles_markdown_code_fences(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        json_inside_fence = '```json\n{"route": "rag", "reasoning": "docs"}\n```'
        cheap = MagicMock()
        cheap.invoke.return_value = MagicMock(content=json_inside_fence)
        factory._cheap = cheap
        factory._premium = MagicMock()
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_structured("prompt fenced")

        assert result["route"] == "rag"

    def test_invalid_json_returns_raw(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._cache = None

        cheap = MagicMock()
        cheap.invoke.return_value = MagicMock(content="not json at all")
        factory._cheap = cheap
        factory._premium = MagicMock()
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        result = factory.invoke_structured("prompt bad")

        assert "raw_response" in result
        assert result["raw_response"] == "not json at all"


class TestMetrics:
    """Testa propriedade de métricas."""

    def test_metrics_calculates_ratios(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "openai"
        factory._metrics = {
            "requests_total": 10,
            "cache_hits": 3,
            "cache_misses": 7,
            "cheap_calls": 5,
            "premium_calls": 2,
            "errors": 0,
            "total_latency_ms": 7000.0,
        }

        m = factory.metrics

        assert m["cache_hit_ratio"] == 0.3
        assert m["avg_latency_ms"] == 1000.0
        assert m["provider"] == "openai"

    def test_metrics_zero_requests(self):
        from src.core.llm_factory import LLMFactory

        factory = LLMFactory.__new__(LLMFactory)
        factory._provider = "google"
        factory._metrics = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cheap_calls": 0,
            "premium_calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        m = factory.metrics

        assert m["cache_hit_ratio"] == 0.0
        assert m["avg_latency_ms"] == 0.0
        assert m["provider"] == "google"
