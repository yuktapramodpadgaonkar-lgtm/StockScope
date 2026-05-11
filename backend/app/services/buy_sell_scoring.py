from __future__ import annotations

import logging
from statistics import pstdev
from typing import Any

from app.core.config import settings
from app.services.huggingface_llm import generate_hf_llm_review

logger = logging.getLogger(__name__)
from app.schemas.buy_sell_analysis import (
    BuySellReport,
    CitationItem,
    DimensionRuleScore,
    FinalVerdict,
    FundamentalAnalysis,
    InvestmentThesis,
    LlmAgreement,
    LlmReview,
    LlmScoreSuggestion,
    OverallRuleScore,
    Recommendation,
    RiskActionPlan,
    RiskAssessment,
    RuleScores,
    ScoreSignal,
    ScoringEngineBlock,
    ScoreWeights,
    SentimentAnalysis,
    TechnicalAnalysis,
    TechnicalIndicators,
    ValuationAnalysis,
)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def score_fundamentals(bundle: dict[str, Any]) -> DimensionRuleScore:
    fields = (bundle.get("fundamentals") or {}).get("fields") or {}
    signals: list[ScoreSignal] = []
    base = 50.0
    total_metrics = 7
    observed = 0

    def add(name: str, value: Any, points: float, reason: str) -> None:
        nonlocal base
        base += points
        signals.append(ScoreSignal(name=name, value=value, points=points, reason=reason))

    rg = _to_float(fields.get("revenueGrowth"))
    if rg is not None:
        observed += 1
        if rg > 0.10:
            add("revenue_growth", rg, 14, "Strong revenue growth.")
        elif rg > 0:
            add("revenue_growth", rg, 8, "Positive revenue growth.")
        else:
            add("revenue_growth", rg, -8, "Negative/flat revenue growth.")

    eg = _to_float(fields.get("earningsGrowth"))
    if eg is not None:
        observed += 1
        if eg > 0.10:
            add("earnings_growth", eg, 14, "Strong earnings growth.")
        elif eg > 0:
            add("earnings_growth", eg, 8, "Positive earnings growth.")
        else:
            add("earnings_growth", eg, -10, "Negative/flat earnings growth.")

    gm = _to_float(fields.get("grossMargins"))
    if gm is not None:
        observed += 1
        if gm >= 0.45:
            add("gross_margin", gm, 8, "Healthy gross margin profile.")
        elif gm >= 0.30:
            add("gross_margin", gm, 4, "Acceptable gross margin.")
        else:
            add("gross_margin", gm, -4, "Low gross margin.")

    pm = _to_float(fields.get("profitMargins"))
    if pm is not None:
        observed += 1
        if pm >= 0.15:
            add("profit_margin", pm, 10, "Strong profitability.")
        elif pm >= 0.05:
            add("profit_margin", pm, 5, "Positive profitability.")
        elif pm < 0:
            add("profit_margin", pm, -8, "Negative profitability.")

    d2e = _to_float(fields.get("debtToEquity"))
    if d2e is not None:
        observed += 1
        if d2e <= 80:
            add("debt_to_equity", d2e, 8, "Conservative leverage.")
        elif d2e <= 150:
            add("debt_to_equity", d2e, 3, "Manageable leverage.")
        elif d2e >= 250:
            add("debt_to_equity", d2e, -8, "High leverage risk.")

    pe = _to_float(fields.get("trailingPE"))
    if pe is not None:
        observed += 1
        if pe <= 25:
            add("trailing_pe", pe, 6, "Reasonable valuation multiple.")
        elif pe <= 35:
            add("trailing_pe", pe, 3, "Moderately elevated valuation.")
        elif pe > 50:
            add("trailing_pe", pe, -5, "Rich valuation multiple.")

    beta = _to_float(fields.get("beta"))
    if beta is not None:
        observed += 1
        if beta <= 1.2:
            add("beta", beta, 4, "Lower volatility profile.")
        elif beta <= 1.8:
            add("beta", beta, 1, "Moderate volatility profile.")
        elif beta > 2.2:
            add("beta", beta, -4, "High volatility risk.")

    completeness = observed / total_metrics if total_metrics else 0.0
    if completeness < 0.5:
        add("data_completeness_penalty", completeness, -6, "Insufficient fundamental coverage.")

    return DimensionRuleScore(
        score=int(round(_clamp(base))),
        signals=signals,
        data_completeness=round(completeness, 3),
    )


def score_technicals(bundle: dict[str, Any]) -> DimensionRuleScore:
    ind = (bundle.get("technical_indicators") or {}).get("indicators") or {}
    signals: list[ScoreSignal] = []
    base = 50.0
    total_metrics = 4
    observed = 0

    def add(name: str, value: Any, points: float, reason: str) -> None:
        nonlocal base
        base += points
        signals.append(ScoreSignal(name=name, value=value, points=points, reason=reason))

    rsi = _to_float(ind.get("rsi_14"))
    if rsi is not None:
        observed += 1
        if 45 <= rsi <= 65:
            add("rsi_14", rsi, 12, "Balanced momentum zone.")
        elif 35 <= rsi < 45 or 65 < rsi <= 75:
            add("rsi_14", rsi, 6, "Moderate momentum signal.")
        elif rsi > 80:
            add("rsi_14", rsi, -8, "Overbought extension risk.")
        elif rsi < 30:
            add("rsi_14", rsi, 2, "Oversold rebound potential.")

    macd = str(ind.get("macd_label") or "neutral")
    observed += 1
    if macd == "bullish":
        add("macd_label", macd, 10, "Bullish MACD regime.")
    elif macd == "bearish":
        add("macd_label", macd, -10, "Bearish MACD regime.")
    else:
        add("macd_label", macd, 2, "Neutral MACD.")

    pma = str(ind.get("price_vs_ma") or "insufficient_data")
    observed += 1
    if pma == "above_50_and_200":
        add("price_vs_ma", pma, 12, "Price above major moving averages.")
    elif pma == "above_50_below_200":
        add("price_vs_ma", pma, 4, "Short-term recovery but long-term resistance remains.")
    elif pma == "below_50_and_200":
        add("price_vs_ma", pma, -12, "Below key trend anchors.")
    elif pma == "mixed":
        add("price_vs_ma", pma, 0, "Mixed moving-average signal.")

    trend = str(ind.get("trend_short") or "sideways")
    observed += 1
    if trend == "up":
        add("trend_short", trend, 10, "Positive short-term trend.")
    elif trend == "down":
        add("trend_short", trend, -10, "Negative short-term trend.")
    else:
        add("trend_short", trend, 2, "Sideways trend.")

    completeness = observed / total_metrics if total_metrics else 0.0
    return DimensionRuleScore(
        score=int(round(_clamp(base))),
        signals=signals,
        data_completeness=round(completeness, 3),
    )


def _news_snippet_for_finbert(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("headline") or "").strip()
    summary = str(item.get("summary") or item.get("text") or "").strip()
    combined = f"{title}. {summary}".strip()
    out = combined if combined else title
    return out[:800]


def score_sentiment(bundle: dict[str, Any]) -> DimensionRuleScore:
    ns = bundle.get("news_and_sentiment") or {}
    av_items = ((ns.get("alpha_vantage") or {}).get("items") or []) if ns else []
    yf_items = ((ns.get("headlines") or {}).get("items") or []) if ns else []
    signals: list[ScoreSignal] = []
    base = 50.0

    def add(name: str, value: Any, points: float, reason: str) -> None:
        nonlocal base
        base += points
        signals.append(ScoreSignal(name=name, value=value, points=points, reason=reason))

    pos = 0
    neg = 0
    neu = 0
    sample = av_items if av_items else yf_items
    texts: list[str] = []
    for item in sample[:20]:
        if isinstance(item, dict):
            snip = _news_snippet_for_finbert(item)
            if snip:
                texts.append(snip)

    use_finbert = bool(
        settings.finbert_enabled
        and (settings.huggingface_api_token or "").strip()
        and texts
    )

    if use_finbert:
        from services.news_sentiment_service import classify_finbert_batch

        for lbl in classify_finbert_batch(texts):
            if lbl == "positive":
                pos += 1
            elif lbl == "negative":
                neg += 1
            else:
                neu += 1
        total = max(1, pos + neg + neu)
        balance = (pos - neg) / total
        add(
            "headline_balance",
            round(balance, 3),
            balance * 20.0,
            f"FinBERT headline tilt (pos={pos}, neg={neg}, neu={neu}) via {settings.finbert_model_id}.",
        )
        add(
            "sentiment_source",
            "finbert",
            0.0,
            "Sentiment score used FinBERT (Hugging Face Inference); independent of the AI model dropdown.",
        )
    else:
        for item in sample[:20]:
            if not isinstance(item, dict):
                continue
            lbl = str(item.get("overall_sentiment_label") or "").lower()
            title = str(item.get("title") or "").lower()
            if "bull" in lbl or "positive" in lbl:
                pos += 1
            elif "bear" in lbl or "negative" in lbl:
                neg += 1
            else:
                for k in ("beat", "upgrade", "growth", "surge", "strong", "record"):
                    if k in title:
                        pos += 1
                        break
                for k in ("miss", "downgrade", "lawsuit", "cut", "weak", "decline"):
                    if k in title:
                        neg += 1
                        break

        total = max(1, pos + neg)
        balance = (pos - neg) / total
        if settings.finbert_enabled and (settings.huggingface_api_token or "").strip() and not texts:
            why = "Keyword heuristic — no non-empty headlines to classify."
        elif not settings.finbert_enabled or not (settings.huggingface_api_token or "").strip():
            why = "Keyword heuristic (enable FINBERT and set HUGGINGFACE_API_TOKEN for FinBERT)."
        else:
            why = "Alpha Vantage / keyword cues (FinBERT not applied for this run)."
        add("headline_balance", round(balance, 3), balance * 20.0, f"Positive vs negative headline tilt. {why}")
        add(
            "sentiment_source",
            "keyword_heuristic",
            0.0,
            "Sentiment score did not use FinBERT; see headline_balance.",
        )

    coverage = min(len(sample), 20) / 20.0
    if coverage >= 0.5:
        add("coverage_depth", coverage, 4, "Adequate recent news coverage.")
    else:
        add("coverage_depth", coverage, -2, "Limited news coverage.")

    completeness = 1.0 if len(sample) > 0 else 0.0
    if not sample:
        add("no_news_penalty", 0, -6, "No usable recent news records.")

    return DimensionRuleScore(
        score=int(round(_clamp(base))),
        signals=signals,
        data_completeness=round(completeness, 3),
    )


def combine_scores(
    f: DimensionRuleScore, t: DimensionRuleScore, s: DimensionRuleScore, weights: ScoreWeights
) -> OverallRuleScore:
    weighted = (
        (weights.fundamental / 100.0) * f.score
        + (weights.technical / 100.0) * t.score
        + (weights.sentiment / 100.0) * s.score
    )

    if weighted >= 75:
        rec = Recommendation.BUY
        band = "75-100"
    elif weighted >= 55:
        rec = Recommendation.HOLD
        band = "55-74"
    else:
        rec = Recommendation.SELL
        band = "0-54"

    completeness = (f.data_completeness + t.data_completeness + s.data_completeness) / 3.0
    dispersion = pstdev([f.score, t.score, s.score])
    agreement = 1.0 - min(1.0, dispersion / 40.0)
    confidence = int(round(_clamp((0.6 * completeness + 0.4 * agreement) * 100.0)))
    setup_quality = int(round(_clamp(0.75 * weighted + 0.25 * confidence)))

    return OverallRuleScore(
        weighted_score=round(weighted, 1),
        recommendation=rec,
        band=band,
        confidence=confidence,
        setup_quality=setup_quality,
    )


def _llm_review_stub(
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
    *,
    enabled: bool,
) -> LlmReview:
    if not enabled:
        return LlmReview(
            enabled=False,
            model="disabled",
            llm_score_suggestion=LlmScoreSuggestion(
                fundamental=f.score,
                technical=t.score,
                sentiment=s.score,
                overall=int(round(overall.weighted_score)),
                recommendation=overall.recommendation,
            ),
            agreement_with_rules=LlmAgreement(matches_recommendation=True, overall_score_delta=0),
            rationale="LLM review disabled; deterministic rule scores are authoritative.",
            warnings=[],
        )

    # Phase 3: advisory-only placeholder until LLM client is wired.
    return LlmReview(
        enabled=False,
        model="not_configured",
        llm_score_suggestion=LlmScoreSuggestion(
            fundamental=f.score,
            technical=t.score,
            sentiment=s.score,
            overall=int(round(overall.weighted_score)),
            recommendation=overall.recommendation,
        ),
        agreement_with_rules=LlmAgreement(matches_recommendation=True, overall_score_delta=0),
        rationale="LLM review requested but no model client is configured; returning score mirror.",
    warnings=["Configure an LLM client in Phase 4 to enable advisory review."],
    )


def _scoring_signal_reasons(f: DimensionRuleScore, t: DimensionRuleScore, s: DimensionRuleScore) -> list[str]:
    return [sig.reason for sig in (f.signals + t.signals + s.signals) if sig.points != 0][:8]


def _finance_facts_from_bundle(bundle: dict[str, Any]) -> list[str]:
    fields = (bundle.get("fundamentals") or {}).get("fields") or {}
    indicators = (bundle.get("technical_indicators") or {}).get("indicators") or {}
    out: list[str] = []
    rg = _to_float(fields.get("revenueGrowth"))
    if rg is not None:
        out.append(f"Revenue growth: {rg:.3f}")
    eg = _to_float(fields.get("earningsGrowth"))
    if eg is not None:
        out.append(f"Earnings growth: {eg:.3f}")
    pm = _to_float(fields.get("profitMargins"))
    if pm is not None:
        out.append(f"Profit margin: {pm:.3f}")
    pe = _to_float(fields.get("trailingPE"))
    if pe is not None:
        out.append(f"Trailing P/E: {pe:.2f}")
    d2e = _to_float(fields.get("debtToEquity"))
    if d2e is not None:
        out.append(f"Debt-to-equity: {d2e:.2f}")
    rsi = _to_float(indicators.get("rsi_14"))
    if rsi is not None:
        out.append(f"RSI-14: {rsi:.2f}")
    macd = str(indicators.get("macd_label") or "").strip()
    if macd:
        out.append(f"MACD regime: {macd}")
    return out[:8]


def _contradiction_risks(
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
) -> list[str]:
    risks: list[str] = []
    spread = max(f.score, t.score, s.score) - min(f.score, t.score, s.score)
    if spread >= 35:
        risks.append(
            f"High cross-dimension dispersion ({spread}) suggests mixed signals; headline recommendation can be brittle."
        )
    if overall.confidence < 45:
        risks.append("Low confidence indicates weak data completeness or weak agreement between dimensions.")
    if f.data_completeness < 0.6 or t.data_completeness < 0.6 or s.data_completeness < 0.6:
        risks.append("At least one scoring pillar has limited data coverage, which can skew the composite.")
    if any(sig.name == "coverage_depth" and sig.points < 0 for sig in s.signals):
        risks.append("News coverage depth is limited; sentiment read may miss key catalysts.")
    if not risks:
        risks.append("No major contradictions flagged in this snapshot, but rapid market/news shifts can invalidate signals.")
    return risks[:4]


def _build_llm_review_via_service(
    ticker: str,
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
    bundle: dict[str, Any] | None,
    preferred_model: str,
) -> LlmReview:
    """Use LLMService (Gemini → LLaMA → Mistral) to explain the deterministic scores (fallback)."""
    from services.buy_sell_llm_service import generate_buy_sell_explanation

    signals = _scoring_signal_reasons(f, t, s)
    finance_facts = _finance_facts_from_bundle(bundle or {})
    contradiction_warnings = _contradiction_risks(overall, f, t, s)

    rationale, model_used, provider_used = generate_buy_sell_explanation(
        ticker=ticker,
        recommendation=overall.recommendation.value,
        overall_score=int(round(overall.weighted_score)),
        fundamental_score=f.score,
        technical_score=t.score,
        sentiment_score=s.score,
        signals=signals,
        finance_facts=finance_facts,
        preferred_model=preferred_model,
    )

    return LlmReview(
        enabled=True,
        model=model_used or "none",
        llm_score_suggestion=LlmScoreSuggestion(
            fundamental=f.score,
            technical=t.score,
            sentiment=s.score,
            overall=int(round(overall.weighted_score)),
            recommendation=overall.recommendation,
        ),
        agreement_with_rules=LlmAgreement(matches_recommendation=True, overall_score_delta=0),
        rationale=rationale,
        warnings=contradiction_warnings,
    )


def _build_llm_review(
    ticker: str,
    overall: OverallRuleScore,
    f: DimensionRuleScore,
    t: DimensionRuleScore,
    s: DimensionRuleScore,
    *,
    include_llm_review: bool,
    bundle: dict[str, Any] | None = None,
    retrieval_chunks: list[dict[str, Any]] | None = None,
    preferred_model: str = "hf_qwen",
) -> LlmReview:
    if not include_llm_review:
        return _llm_review_stub(overall, f, t, s, enabled=False)

    pref = (preferred_model or "hf_qwen").strip().lower()
    sig_for_narrative = _scoring_signal_reasons(f, t, s)

    # FinBERT+RAG narrative only when explicitly selected (`finbert` in dropdown).
    if bundle is not None and settings.buysell_llm_enabled and pref == "finbert":
        from services.buy_sell_llm_service import finbert_buy_sell_llm_review

        fin = finbert_buy_sell_llm_review(
            ticker=ticker.upper(),
            overall=overall,
            fundamental=f,
            technical=t,
            sentiment=s,
            bundle=bundle,
            retrieval_chunks=retrieval_chunks,
            signals=sig_for_narrative,
        )
        if fin is not None:
            return fin.model_copy(update={"warnings": [*fin.warnings, *_contradiction_risks(overall, f, t, s)]})

    # Try HuggingFace text-generation review if explicitly configured
    hf_provider = (settings.buysell_llm_provider or "none").strip().lower()
    if settings.buysell_llm_enabled and hf_provider == "huggingface":
        try:
            return generate_hf_llm_review(
                ticker=ticker,
                overall=overall,
                fundamental=f,
                technical=t,
                sentiment=s,
                retrieval_chunks=retrieval_chunks or [],
            )
        except Exception as exc:
            logger.warning("HuggingFace LLM review failed for %s: %s", ticker, exc)
            # Fall through to LLMService

    # Use LLMService (Gemini → LLaMA → Mistral) as primary/fallback
    return _build_llm_review_via_service(
        ticker,
        overall,
        f,
        t,
        s,
        bundle=bundle,
        preferred_model=preferred_model,
    )


def build_buy_sell_report_from_layer1(
    ticker: str,
    bundle: dict[str, Any],
    *,
    include_llm_review: bool = False,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    preferred_model: str = "hf_qwen",
) -> BuySellReport:
    weights = ScoreWeights()
    f = score_fundamentals(bundle)
    t = score_technicals(bundle)
    s = score_sentiment(bundle)
    overall = combine_scores(f, t, s, weights)

    fields = (bundle.get("fundamentals") or {}).get("fields") or {}
    indicators = (bundle.get("technical_indicators") or {}).get("indicators") or {}
    news_items = ((bundle.get("news_and_sentiment") or {}).get("alpha_vantage") or {}).get("items") or []
    if not news_items:
        news_items = ((bundle.get("news_and_sentiment") or {}).get("headlines") or {}).get("items") or []

    growth_txt = "insufficient data"
    rg = _to_float(fields.get("revenueGrowth"))
    eg = _to_float(fields.get("earningsGrowth"))
    if rg is not None or eg is not None:
        growth_txt = f"Revenue growth={rg}, earnings growth={eg}"

    pe = _to_float(fields.get("trailingPE"))
    price = _to_float(fields.get("targetMeanPrice"))
    dcf_proxy = _to_float(fields.get("targetMeanPrice"))
    implied = None
    if dcf_proxy is not None and price not in (None, 0):
        implied = ((dcf_proxy - price) / price) * 100.0

    def _sentiment_verdict(sd: DimensionRuleScore) -> str:
        for sig in sd.signals:
            if sig.name == "sentiment_source" and str(sig.value) == "finbert":
                return (
                    "Sentiment score incorporates FinBERT on recent headlines. "
                    "For the written explanation, choose “FinBERT” in the model menu for label+RAG narrative; "
                    "choose Qwen/Mistral (HF) or Gemini/Llama/Ollama-Mistral for generative text."
                )
        return (
            "Sentiment score uses Alpha Vantage / keyword cues when FinBERT is off, the HF token is missing, "
            "or headlines are empty — enable FINBERT and set HUGGINGFACE_API_TOKEN for neural classification."
        )

    citations: list[CitationItem] = [
        CitationItem(
            id="layer1-fundamentals",
            title="Layer1 fundamentals snapshot",
            source=str((bundle.get("fundamentals") or {}).get("source") or "yfinance"),
            snippet="Structured field snapshot used for deterministic scoring.",
        ),
        CitationItem(
            id="layer1-technicals",
            title="Layer1 technical indicators",
            source=str((bundle.get("technical_indicators") or {}).get("source") or "computed_locally"),
            snippet="RSI/MACD/MAs computed from shared history fetch.",
        ),
        CitationItem(
            id="layer1-news",
            title="Layer1 news/sentiment feed",
            source=str((bundle.get("news_and_sentiment") or {}).get("primary_source") or "unknown"),
            snippet="Recent headlines/sentiment rows used for sentiment scoring.",
        ),
    ]
    for row in (retrieved_chunks or [])[:6]:
        cid = str(row.get("chunk_id") or "").strip()
        if not cid:
            continue
        citations.append(
            CitationItem(
                id=cid,
                title=str(row.get("title") or f"{row.get('doc_type', 'document')} chunk"),
                source=str(row.get("source") or row.get("doc_type") or "rag"),
                url=str(row.get("url") or "") or None,
                date=str(row.get("published_at") or "") or None,
                snippet=str(row.get("text") or "")[:220],
            )
        )

    llm_review = _build_llm_review(
        ticker=ticker.upper(),
        overall=overall,
        f=f,
        t=t,
        s=s,
        include_llm_review=include_llm_review,
        bundle=bundle,
        retrieval_chunks=retrieved_chunks,
        preferred_model=preferred_model,
    )
    contradiction_notes = _contradiction_risks(overall, f, t, s)

    report = BuySellReport(
        ticker=ticker.upper(),
        recommendation=overall.recommendation,
        confidence=overall.confidence,
        optimal_timeframe="3-6 months",
        setup_quality=overall.setup_quality,
        investment_thesis=InvestmentThesis(
            summary=(
                "Deterministic multi-factor score blends fundamentals, technical trend, and headline sentiment."
            ),
            key_drivers=[
                f"Rule-based weighted score: {overall.weighted_score}",
                f"Technical regime: {indicators.get('trend_short', 'unknown')}",
                f"News source: {(bundle.get('news_and_sentiment') or {}).get('primary_source', 'unknown')}",
            ],
        ),
        fundamental_analysis=FundamentalAnalysis(
            score=f.score,
            weight=weights.fundamental,
            business_performance=f"Growth/quality signals: {growth_txt}",
            valuation_analysis=ValuationAnalysis(
                pe=pe,
                dcf_value=dcf_proxy,
                current_price=price,
                implied_upside=round(implied, 2) if implied is not None else None,
            ),
            bull_bear_integration=(
                "Bull case: growth/profitability and manageable leverage; "
                "bear case: valuation and leverage sensitivity."
            ),
            verdict="Fundamental score derived from growth, margins, leverage, valuation, and volatility inputs.",
        ),
        technical_analysis=TechnicalAnalysis(
            score=t.score,
            weight=weights.technical,
            trend_analysis=(
                f"Trend={indicators.get('trend_short')}, price_vs_ma={indicators.get('price_vs_ma')}, "
                f"MACD={indicators.get('macd_label')}."
            ),
            indicators=TechnicalIndicators(
                rsi=_to_float(indicators.get("rsi_14")),
                macd_signal=str(indicators.get("macd_label") or ""),
                ma_50=_to_float(indicators.get("sma_50")),
                ma_200=_to_float(indicators.get("sma_200")),
                price_vs_ma=str(indicators.get("price_vs_ma") or ""),
            ),
            verdict="Technical score reflects momentum, moving-average structure, and short trend.",
        ),
        sentiment_analysis=SentimentAnalysis(
            score=s.score,
            weight=weights.sentiment,
            recent_developments=[
                str(x.get("title") or x.get("summary") or "") for x in news_items[:5] if isinstance(x, dict)
            ],
            verdict=_sentiment_verdict(s),
        ),
        final_verdict=FinalVerdict(
            overall_score=int(round(overall.weighted_score)),
            rating=overall.recommendation.value,
            why_dimensions_align=(
                "Final rating combines weighted deterministic scores with a confidence metric "
                "from data completeness and cross-dimension agreement."
            ),
            conflicts=" ".join(contradiction_notes),
        ),
        risk_assessment=RiskAssessment(
            key_risks=[
                "Model relies on available market/fundamental fields and can degrade with missing data.",
                "Headline sentiment can shift rapidly and lag intraday catalysts.",
                "Rule thresholds are phase-3 heuristics and should be backtested/tuned.",
            ],
            action_plan=RiskActionPlan(
                if_you_own="Review exposure against confidence score; rebalance if thesis drivers weaken.",
                if_you_want_to_buy="Prefer staged entries and require agreement between fundamentals and technicals.",
            ),
        ),
        scoring_engine=ScoringEngineBlock(
            weights=weights,
            rule_scores=RuleScores(fundamental=f, technical=t, sentiment=s),
            overall=overall,
        ),
        llm_review=llm_review,
        citations=citations,
    )

    if include_llm_review and settings.buysell_llm_enabled:
        try:
            from services.buy_sell_structured_narrative import generate_buy_sell_ai_narratives

            narr = generate_buy_sell_ai_narratives(
                bundle,
                report,
                preferred_model=preferred_model,
            )
            if narr is not None:
                report = report.model_copy(update={"ai_narratives": narr})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structured AI narratives skipped for %s: %s", ticker, exc)

    return report
