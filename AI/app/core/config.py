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

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    worker_api_key: str = ""

    public_base_url: str = "https://i15a108.p.ssafy.io"  # 추가 필요

    # 추천 아티팩트(사전계산 그래프) 루트 디렉터리. 비어 있으면
    # app/recommend/artifacts/ 를 기본값으로 사용한다.
    recommend_artifact_dir: str = ""


settings = Settings()  # 추가 필요
