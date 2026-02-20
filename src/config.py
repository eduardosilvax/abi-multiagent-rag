# Configuração centralizada. Tudo vem de variáveis de ambiente (.env).
#
# Troca de provider:
#   LLM_PROVIDER=openai  → OpenAI (padrão)
#   LLM_PROVIDER=google  → Google Gemini (tem free tier)
#   LLM_PROVIDER=azure   → Azure OpenAI (enterprise)
#
# Cada provider tem suas env vars de modelo, chave e endpoint.
# O resto da aplicação é provider-agnostic — LLMFactory e
# VectorManager abstraem toda lógica específica.

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("abi_assistant")

# provedor: "openai" (padrão), "azure" ou "google"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Azure OpenAI (opcional)
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_DEPLOYMENT_CHEAP: str = os.getenv("AZURE_DEPLOYMENT_CHEAP", "gpt-4o-mini")
AZURE_DEPLOYMENT_PREMIUM: str = os.getenv("AZURE_DEPLOYMENT_PREMIUM", "gpt-4o")
AZURE_DEPLOYMENT_EMBEDDING: str = os.getenv("AZURE_DEPLOYMENT_EMBEDDING", "text-embedding-3-small")

# Google Gemini (opcional)
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_CHEAP_MODEL: str = os.getenv("GEMINI_CHEAP_MODEL", "gemini-2.5-flash")
GEMINI_PREMIUM_MODEL: str = os.getenv("GEMINI_PREMIUM_MODEL", "gemini-2.5-pro")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# model tiers (padrão OpenAI, sobrescritos se provider=google)
LLM_CHEAP_MODEL: str = os.getenv("LLM_CHEAP_MODEL", "gpt-4.1-nano")
LLM_PREMIUM_MODEL: str = os.getenv("LLM_PREMIUM_MODEL", "gpt-4.1")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Qdrant
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "abi_docs")

# Redis
REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

# RAG
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))

# paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"

# API auth (vazio = sem auth, pra dev local)
API_KEY: str = os.getenv("API_KEY", "")
