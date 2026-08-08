from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Service"
    server_port: int = 8000

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "vintib"
    db_username: str = "postgres"
    db_password: str = "postgres"

    # AI 전용 RAG 저장소(postgres-vector, S15P11A108-375). 위 db_*(BE 공유 DB)와는 별개 인스턴스 —
    # 혼동 방지를 위해 이름을 분리했다. 아직 어느 코드도 db_*를 안 쓰는 것과 달리 이건 rag_store.py가 쓴다.
    vector_db_host: str = "localhost"
    vector_db_port: int = 5433
    vector_db_name: str = "vintib_rag"
    vector_db_username: str = "postgres"
    vector_db_password: str = "postgres"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    worker_api_key: str = ""

    # 가격 책정(app/pricing/)이 시세 검색에 쓰는 SSAFY 공용 게이트웨이 키.
    # **비어 있는 것이 정상 기본값이다** — 그 경우 mock comps 백엔드로 떨어지고 서비스는 뜬다.
    # 실호출은 팀 공용 유료 쿼터를 소모하고 LLM 웹검색은 별도 과금이라, 채우는 건 의도적 행위여야 한다.
    gms_api_key: str = ""

    # 가격 책정(app/pricing/)이 신상품(정가) 조회에 쓰는 네이버 쇼핑 오픈API 키.
    # **비어 있는 것이 정상 기본값이다** — 그 경우 mock retail 백엔드로 떨어지고 서비스는 뜬다.
    # GMS와 무관한 무료 API지만 쿼터가 있어, 채우는 건 의도적 행위여야 한다.
    naver_client_id: str = ""
    naver_client_secret: str = ""

    public_base_url: str = "https://i15a108.p.ssafy.io"  # 추가 필요

    # BE 공개 REST API(컨테이너 내부망). 가격책정 internal 백엔드·게이트웨이의 임베딩 카테고리
    # 태깅(CH024)이 상품 상세(`GET /api/products/{id}`)를 조회하는 데 쓴다 — DB 뷰·읽기 전용
    # 계정 없이도 BE가 이미 공개로 내는 필드(brandId/price/saleType/saleStatus 등)로 충분하다.
    be_base_url: str = "http://backend:8080"

    # 추천 아티팩트(사전계산 그래프) 루트 디렉터리. 비어 있으면
    # app/recommend/artifacts/ 를 기본값으로 사용한다.
    recommend_artifact_dir: str = ""

    # 가격 책정(app/pricing/) comps 백엔드 스왑(CH030). **커밋 기본값은 항상 mock이어야
    # 한다**(test/pricing/test_pricing_registry.py::test_committed_defaults_are_mock가
    # 강제한다) — 실백엔드 전환은 배포 환경변수로만 한다(코드 커밋 X). GMS를 쓰는
    # llm_web_search는 이 방식으로도 켜지 않는다(AI/CLAUDE.md 하드 룰, 사용자만 직접 실행).
    pricing_comps_source: str = "mock"


settings = Settings()  # 추가 필요
