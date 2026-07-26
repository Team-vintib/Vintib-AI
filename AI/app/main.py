from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.chat.router import router as chat_router
from app.core.config import settings
from app.gateway.router import RESULTS_DIR
from app.gateway.router import router as gateway_router
from app.recommend.personalize.router import router as personalize_router
from app.recommend.router import router as recommend_router

app = FastAPI(title=settings.app_name)

app.include_router(recommend_router, prefix="/recommend", tags=["recommend"])
app.include_router(personalize_router, prefix="/recommend", tags=["recommend-personalize"])
app.include_router(chas=["chat"])
app.include_router(gateway_router, prefix="/ai", tags=["ai-gateway"])

app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")


@app.get("/health")
def health_check() ->
    return {"status": "ok"}