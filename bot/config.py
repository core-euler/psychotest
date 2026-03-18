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
    yookassa_shop_id: str = Field(alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(alias="YOOKASSA_SECRET_KEY")
    yookassa_payment_amount: str = Field(default="2999.00", alias="YOOKASSA_PAYMENT_AMOUNT")
    yookassa_return_url: str = Field(default="", alias="YOOKASSA_RETURN_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    webhook_host: str = Field(default="0.0.0.0", alias="WEBHOOK_HOST")
    webhook_port: int = Field(default=8081, alias="WEBHOOK_PORT")

    @property
    def admin_ids(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
