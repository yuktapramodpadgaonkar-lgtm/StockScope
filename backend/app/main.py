from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis_fundamental import router as analysis_fundamental_router
from app.api.analysis_news_sentiment import router as analysis_news_sentiment_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router
from app.api.market_movers import router as market_movers_router
from app.core.config import settings


def _parse_cors_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analysis_fundamental_router)
app.include_router(market_movers_router)
app.include_router(chat_router)
app.include_router(analysis_news_sentiment_router)
app.include_router(history_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
