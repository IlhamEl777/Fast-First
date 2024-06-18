from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    MIN_AVAILABLE_ENERGY: int = 100
    SLEEP_BY_MIN_ENERGY: int = 200

    ADD_TAP_ON_TURBO: int = 2500

    APPLY_DAILY_ENERGY: bool = True
    APPLY_DAILY_TURBO: bool = True

    RANDOM_TAP_COUNT: list[int] = [200, 500]
    SLEEP_BETWEEN_TAP: list[int] = [20, 30]
    SLEEP_INCORECT_TIME: int = 120

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()
