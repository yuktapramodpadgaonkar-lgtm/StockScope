# docs/ — Index

This directory contains supplementary documentation for StockScope. Start here for design context, RAG/agent status, and API reference details.

| File | Purpose |
|------|---------|
| [AGENT_RAG_MEMORY_STATUS.md](AGENT_RAG_MEMORY_STATUS.md) | Honest implementation status for every agent, RAG, and memory component. Shows what is fully done, partially done, and not yet implemented. **Read this first if you are a grader or reviewer.** |
| [AGENTIC_RAG_AND_MEMORY.md](AGENTIC_RAG_AND_MEMORY.md) | Deep-dive on the agentic research pipeline: planner → tools → writer → critic → repair loop. Covers the evidence bundle format, critic checks, repair prompt, and memory profile. |
| [BuySellAnalysis-roadmap.md](BuySellAnalysis-roadmap.md) | Phase roadmap for the Buy/Sell analysis feature (Layer 1 data, scoring, LLM review, RAG, agent orchestration). |
| [BuySellAnalysis-data-sources.md](BuySellAnalysis-data-sources.md) | Data sources and field mapping used by the buy/sell scoring engine (yfinance fields → scoring dimensions). |
| [BuySellAnalysis-retrieval-sources.md](BuySellAnalysis-retrieval-sources.md) | RAG retrieval sources for buy/sell: news chunk ingest, SEC filing ingest, retrieval query construction. |
| [Phase5-RAG-checklist.md](Phase5-RAG-checklist.md) | Checklist tracking RAG implementation milestones (BM25, embedding index, hybrid retriever, citation checker). |
| [MARKET_MOVERS.md](MARKET_MOVERS.md) | Market movers implementation notes: universe CSVs, snapshot cache, batch-download rationale, known limitations. |
| [API-keys.md](API-keys.md) | API key setup guide for all optional external providers (Gemini, Finnhub, Alpha Vantage, HuggingFace, SEC EDGAR). |
| [API-keys-testing.md](API-keys-testing.md) | Notes on testing with and without API keys; fallback behavior for each provider when key is absent. |
| [Layer1-api-call-ledger.md](Layer1-api-call-ledger.md) | Ledger of all external API calls made during a buy/sell analysis run (Layer 1 data bundle). |

## Quick Navigation for Graders

- **What does the system actually implement?** → [AGENT_RAG_MEMORY_STATUS.md](AGENT_RAG_MEMORY_STATUS.md)
- **How does the agentic pipeline work?** → [AGENTIC_RAG_AND_MEMORY.md](AGENTIC_RAG_AND_MEMORY.md)
- **How does the scoring engine work?** → `backend/app/services/buy_sell_scoring.py` (747 lines, inline comments)
- **How does hybrid retrieval work?** → `backend/app/rag/hybrid_retriever.py` + [Phase5-RAG-checklist.md](Phase5-RAG-checklist.md)
- **How do I run the evaluation?** → `backend/evaluation/run_batch_eval.py --help`
- **What are the academic references?** → [README.md References section](../README.md#references)
