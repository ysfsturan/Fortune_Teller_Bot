"""Fortune Teller Bot giriş noktası (`python main.py`)."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from src.bot import FortuneTellerBot
from src.config import ConfigError, load_config
from src.gemini_client import GeminiError, GeminiFortuneClient
from src.server import run_once, run_polling, run_webhook
from src.telegram_client import TelegramClient


def _configure_logging() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fortune Teller Bot — Yapay zekâ destekli çok modlu Telegram fal botu"
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "webhook", "polling", "once"],
        default=None,
        help="Çalıştırma kipini seçer (varsayılan: BOT_MODE veya ortamdan otomatik).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Bekleyen mesajları tek seferde işleyip çıkar (--mode once ile aynıdır).",
    )
    parser.add_argument(
        "--test-gemini",
        action="store_true",
        help="Telegram başlatmadan Gemini Flash model keşfini ve örnek yorumu test eder.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _configure_logging()
    logger = logging.getLogger(__name__)
    args = build_arg_parser().parse_args(argv)

    try:
        config = load_config(
            require_telegram=not args.test_gemini,
            require_gemini=True,
        )
    except ConfigError as exc:
        logger.error("Yapılandırma hatası: %s", exc)
        return 2

    gemini = GeminiFortuneClient(
        api_key=config.gemini_api_key,
        preferred_model=config.gemini_model,
    )

    if args.test_gemini:
        try:
            used_model, discovered = gemini.test_connection()
            print(f"Gemini test başarılı! Kullanılan model: {used_model}")
            if discovered:
                print(f"Keşfedilen aktif Flash modeller: {', '.join(discovered)}")
            return 0
        except GeminiError as exc:
            logger.error("Gemini test başarısız: %s", exc)
            return 1

    telegram = TelegramClient(config.telegram_token)
    bot = FortuneTellerBot(config=config, telegram_client=telegram, gemini_client=gemini)

    selected_mode = "once" if args.once else (args.mode or config.resolved_mode)
    logger.info("Çalıştırma kipi: %s", selected_mode)

    if selected_mode == "once":
        run_once(bot)
        return 0
    if selected_mode == "webhook":
        run_webhook(bot)
        return 0
    run_polling(bot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
