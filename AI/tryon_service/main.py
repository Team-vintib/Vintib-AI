"""
가상 시착 서비스 FastAPI 앱.

S15P11A108-189에서 스캐폴딩된 모듈 구조에 맞춰, 이 파일은 tryon 라우터만
등록한다. 다른 도메인(인증, 상품 등) 라우터가 이미 있다면 그쪽 main.py에
`app.include_router(tryon_router)`만 추가하는 형태로 통합하는 것을 권장.
(이 파일은 tryon 서비스 단독 실행/테스트용 엔트리포인트)
"""

from fastapi import FastAPI

from app.api.routes.tryon import router as tryon_router

app = FastAPI(title="Vintage Try-On Service", version="0.1.0")

app.include_router(tryon_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
