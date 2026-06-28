from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Kite Connect
    kite_api_key: str = ""
    kite_secret: str = ""
    kite_user_id: str = ""
    kite_access_token: Optional[str] = None

    # AI
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"

    # Web Research
    serpapi_key: str = ""
    news_api_key: str = ""

    # Database / Cache
    database_url: str = "postgresql://trading_user:password@localhost:5432/trading_db"
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "changeme"
    environment: str = "development"
    log_level: str = "INFO"

    # Trading parameters
    capital: float = 150000.0
    max_risk_per_trade: float = 0.01
    max_daily_loss: float = 0.02
    max_weekly_loss: float = 0.05
    max_open_positions: int = 3
    min_confidence_score: int = 70
    squareoff_time: str = "15:25"
    no_trade_buffer_minutes: int = 5

    # Derived helpers
    @property
    def risk_amount(self) -> float:
        return self.capital * self.max_risk_per_trade

    @property
    def daily_loss_limit(self) -> float:
        return self.capital * self.max_daily_loss

    @property
    def weekly_loss_limit(self) -> float:
        return self.capital * self.max_weekly_loss

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
