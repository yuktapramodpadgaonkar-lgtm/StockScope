from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "StockScope API"
    app_env: str = "dev"
    app_debug: bool = True

    market_data_provider: str = "yfinance"
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    # Optional — advanced valuation / transcripts later (Layer 1 MVP does not call FMP).
    fmp_api_key: str = ""
    # Buy/Sell LLM review (Phase 4)
    buysell_llm_provider: str = "gemini"  # gemini | ollama | huggingface | none
    buysell_llm_enabled: bool = True
    buysell_llm_model: str = ""  # e.g. FinGPT model id on Hugging Face
    buysell_llm_timeout_seconds: int = 45
    # When true, explanation mode "finbert" uses FinBERT+RAG narrative; other dropdown values use HF or LLMService.
    buysell_explanation_use_finbert: bool = True
    # Hugging Face Inference — instruction models for Buy/Sell narrative (plain text).
    hf_buy_sell_instruction_qwen_model_id: str = "Qwen/Qwen2.5-1.5B-Instruct:featherless-ai"
    hf_buy_sell_instruction_mistral_model_id: str = "mistralai/Mistral-7B-Instruct-v0.3"
    huggingface_api_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HUGGINGFACE_API_TOKEN",
            "HUGGINGFACE_API_KEY",
            "HF_TOKEN",
            "huggingface_api_token",
        ),
    )
    hf_model_id: str = ""
    hf_inference_url: str = ""  # optional dedicated endpoint URL

    # Comma-separated origins for browser access to the API (Next.js dev server).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Market movers: cache full universe snapshot in memory (see snapshot_cache).
    movers_cache_enabled: bool = True
    movers_cache_ttl_intraday_seconds: int = 60
    movers_cache_ttl_previous_day_seconds: int = 300

    # Phase 5.1 — RAG retrieval (embeddings + store hygiene)
    rag_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_embedding_batch_size: int = 16
    rag_bm25_weight: float = 0.45
    rag_embedding_weight: float = 0.55
    rag_max_chunk_age_days: int = 730
    rag_max_total_chunks: int = 80_000
    rag_max_chunks_per_ticker: int = 600
    rag_rotate_bytes: int = 100 * 1024 * 1024
    sec_edgar_enabled: bool = True
    sec_user_agent: str = "StockScope student-project revatishailesh.pathrudkar@sjsu.edu"
    sec_filings_limit: int = 2
    sec_filing_max_download_chars: int = 200_000
    sec_cik_cache_hours: int = 168
    sec_request_delay_seconds: float = 0.15

    memory_enabled: bool = True
    memory_max_recent_tickers: int = 30

    eval_output_dir: str = ""

    # Gemini (chat, news, fundamentals AI explanation) — use AI Studio key in .env
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"),
    )
    gemini_model: str = "gemini-2.0-flash"

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "ollama_base_url"),
    )
    ollama_llama_model: str = "llama3.1:8b"
    ollama_mistral_model: str = "mistral:7b"
    ollama_timeout_seconds: int = 180

    default_llm_provider: str = "llama"  # gemini | llama | mistral

    finbert_enabled: bool = True
    finbert_model_id: str = "ProsusAI/finbert"

    # JWT authentication
    jwt_secret_key: str = "changeme-dev-secret-minimum-32-chars!!"
    jwt_expire_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
