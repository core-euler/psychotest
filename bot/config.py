from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    postgres_dsn: str = Field(alias="POSTGRES_DSN")
    admin_ids_raw: str = Field(alias="ADMIN_IDS")
    masterclass_link: str = Field(alias="MASTERCLASS_LINK")
    channel_invite_link: str = Field(alias="CHANNEL_INVITE_LINK")
    prodamus_payment_url: str = Field(alias="PRODAMUS_PAYMENT_URL")
    prodamus_webhook_secret: str = Field(default="", alias="PRODAMUS_WEBHOOK_SECRET")
    prodamus_key: str = Field(default="", alias="PRODAMUS_KEY")
    payment_stub_mode: bool = Field(default=True, alias="PAYMENT_STUB_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    webhook_host: str = Field(default="0.0.0.0", alias="WEBHOOK_HOST")
    webhook_port: int = Field(default=8081, alias="WEBHOOK_PORT")

    @property
    def admin_ids(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
