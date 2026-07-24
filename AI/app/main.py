from fastapi import FastAPI

from app.core.config import settings
from app.recommend.personalize.router import router as personalize_router
from app.recommend.router import router as recommend_router

app = FastAPI(title=settings.app_name)

app.include_router(recommend_router, prefix="/recommend", tags=["recommend"])
app.include_router(personalize_router, prefix="/recommend", tags=["recommend-personalize"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
