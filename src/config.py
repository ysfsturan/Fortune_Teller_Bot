"""Ortam değişkenlerinden ve .env dosyasından bot yapılandırmasını yükler."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


class ConfigError(Exception):
    """Eksik veya geçersiz yapılandırma durumunda fırlatılır."""


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        val = (os.getenv(name) or "").strip()
        if val:
            return val
    return default


def _parse_chat_ids(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_int(raw: str, var_name: str, default: int) -> int:
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{var_name} geçerli bir tam sayı olmalıdır: '{raw}'") from exc


def _parse_float(raw: str, var_name: str, default: float) -> float:
    if not raw:
        return default
    try:
        val = float(raw.replace(",", "."))
        return max(0.0, val)
    except ValueError as exc:
        raise ConfigError(f"{var_name} geçerli bir ondalık sayı olmalıdır: '{raw}'") from exc


@dataclass(frozen=True)
class Config:
    """Fortune Teller Bot çalışma ayarları."""

    telegram_token: str = ""
    gemini_api_key: str = ""
    gemini_model: Optional[str] = None
    bot_mode: str = "auto"
    webhook_url: Optional[str] = None
    webhook_secret: str = ""
    port: int = 10000
    host: str = "0.0.0.0"
    timezone_name: str = "Europe/Istanbul"
    allowed_chat_ids: list[str] = field(default_factory=list)
    user_cooldown_seconds: float = 3.0

    @property
    def resolved_mode(self) -> str:
        """Etkin çalıştırma kipini döndürür (auto ise webhook/polling)."""
        if self.bot_mode == "auto":
            return "webhook" if self.webhook_url else "polling"
        return self.bot_mode

    @property
    def webhook_endpoint(self) -> Optional[str]:
        """Telegram'a kaydedilecek tam HTTPS webhook URL'si."""
        if not self.webhook_url:
            return None
        base = self.webhook_url.rstrip("/")
        if base.endswith("/webhook"):
            return base
        return f"{base}/webhook"


def load_config(
    *,
    require_telegram: bool = True,
    require_gemini: bool = True,
) -> Config:
    """Ortam değişkenlerini ve .env dosyasını okuyarak doğrulanmış Config döndürür."""
    if load_dotenv is not None:
        load_dotenv()

    telegram_token = _first_env("TELEGRAM_TOKEN", "BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    gemini_api_key = _first_env("GEMINI_API_KEY", "GOOGLE_API_KEY")

    if require_telegram and not telegram_token:
        raise ConfigError(
            "TELEGRAM_TOKEN (veya BOT_TOKEN) tanımlı değil. Lütfen ortam değişkenlerini kontrol edin."
        )
    if require_gemini and not gemini_api_key:
        raise ConfigError(
            "GEMINI_API_KEY tanımlı değil. Lütfen Google AI Studio anahtarınızı ekleyin."
        )

    bot_mode = _first_env("BOT_MODE", default="auto").lower()
    if bot_mode not in {"auto", "webhook", "polling", "once"}:
        raise ConfigError(
            f"BOT_MODE geçersiz: '{bot_mode}' (geçerli değerler: auto, webhook, polling, once)"
        )

    raw_webhook_url = _first_env("WEBHOOK_URL", "RENDER_EXTERNAL_URL")
    webhook_url = raw_webhook_url.rstrip("/") if raw_webhook_url else None
    if webhook_url and not webhook_url.startswith("http"):
        webhook_url = f"https://{webhook_url}"

    if bot_mode == "webhook" and not webhook_url:
        raise ConfigError(
            "BOT_MODE=webhook seçildiğinde WEBHOOK_URL veya RENDER_EXTERNAL_URL tanımlanmalıdır."
        )

    explicit_secret = _first_env("WEBHOOK_SECRET")
    if explicit_secret:
        webhook_secret = explicit_secret
    elif telegram_token:
        webhook_secret = hashlib.sha256(f"fortune:{telegram_token}".encode("utf-8")).hexdigest()[:32]
    else:
        webhook_secret = "fortune-secret-token"

    port = _parse_int(_first_env("PORT"), "PORT", 10000)
    host = _first_env("HOST", default="0.0.0.0")
    timezone_name = _first_env("TIMEZONE", default="Europe/Istanbul")
    allowed_chat_ids = _parse_chat_ids(_first_env("ALLOWED_CHAT_IDS", "CHAT_ID"))
    cooldown = _parse_float(_first_env("USER_COOLDOWN_SECONDS"), "USER_COOLDOWN_SECONDS", 3.0)
    gemini_model = _first_env("GEMINI_MODEL") or None

    return Config(
        telegram_token=telegram_token,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        bot_mode=bot_mode,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        port=port,
        host=host,
        timezone_name=timezone_name,
        allowed_chat_ids=allowed_chat_ids,
        user_cooldown_seconds=cooldown,
    )
