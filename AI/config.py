from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Service"
    server_port: int = 8000

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "vintage_auction"
    db_username: str = "postgres"
    db_password: str = "postgres"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    worker_api_key: str = ""

    public_base_url: str = "https://i15a108.p.ssafy.io"   # 추가 필요


settings = Settings()   # 추가 필요