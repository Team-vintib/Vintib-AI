import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.chat.router import router as chat_router
from app.chat.service import get_chat_service
from app.core.config import settings
from app.gateway.router import RESULTS_DIR
from app.gateway.router import router as gateway_router
from app.measurement.router import router as measurement_router
from app.pricing.router import router as pricing_router
from app.product_classifier.router import router as product_classifier_router
from app.quality.router import router as quality_router
from app.recommend.personalize.router import router as personalize_router
from app.recommend.router import router as recommend_router
from app.recommend.similar.router import router as similar_router
from app.tryon.router import router as tryon_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 채팅 욕설 판정기(KcELECTRA-base-hate) 로딩이 130초대라(CH030), 배포 후 첫 채팅
    # 메시지가 그 지연을 그대로 떠안지 않도록 기동 시점에 미리 로드해둔다.
    # get_chat_service()는 @lru_cache 싱글턴이라 여기서 한 번 호출해두면 이후 요청은
    # 캐시된 인스턴스를 그대로 재사용한다.
    get_chat_service()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# similar_router가 recommend_router보다 먼저 등록돼야 한다 — 둘 다 3세그먼트 경로
# (/products/{id}/similar vs /{entity}/{entity_id}/similar)라 순서가 매칭 우선순위를
# 정한다. "products"는 EntityType(brand/seller)과 절대 겹치지 않는 리터럴이라 안전하다.
app.include_router(similar_router, prefix="/recommend", tags=["recommend-similar"])
app.include_router(recommend_router, prefix="/recommend", tags=["recommend"])
app.include_router(personalize_router, prefix="/recommend", tags=["recommend-personalize"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(quality_router, prefix="/quality", tags=["quality"])
app.include_router(measurement_router, prefix="/measurement", tags=["measurement"])
app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])
app.include_router(
    product_classifier_router, prefix="/product-classifier", tags=["product-classifier"]
)
app.include_router(gateway_router, prefix="/ai", tags=["ai-gateway"])
app.include_router(tryon_router, prefix="/ai/tryon", tags=["tryon"])

app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")
app.mount(
    "/personas",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static", "personas")),
    name="personas",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
