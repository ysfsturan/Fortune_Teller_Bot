"""Webhook HTTP sunucusu (Render Web Service), sağlık ucu (/health) ve polling çalışma kipleri."""

from __future__ import annotations

import hmac
import json
import logging
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

from .bot import BOT_COMMANDS, FortuneTellerBot
from .telegram_client import TelegramError

logger = logging.getLogger(__name__)


def create_webhook_server(
    bot: FortuneTellerBot,
    *,
    host: str = "0.0.0.0",
    port: int = 10000,
    secret_token: str = "",
    mode_label: str = "webhook",
    max_workers: int = 4,
) -> tuple[ThreadingHTTPServer, ThreadPoolExecutor]:
    """Render sağlık denetimleri ve Telegram webhook istekleri için HTTP sunucusu kurar."""
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fortune-worker")

    class FortuneHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("HTTP %s - %s", self.address_string(), format % args)

        def _send_json(self, status: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in {"/", "/health", "/healthz"}:
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "service": "fortune-teller-bot",
                        "mode": mode_label,
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_HEAD(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            self.send_response(HTTPStatus.OK if path in {"/", "/health", "/healthz"} else HTTPStatus.NOT_FOUND)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path != "/webhook":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return

            if secret_token:
                incoming = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
                if not hmac.compare_digest(incoming, secret_token):
                    self._send_json(HTTPStatus.FORBIDDEN, {"error": "invalid_secret"})
                    return

            try:
                content_len = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_length"})
                return

            if content_len <= 0 or content_len > 2 * 1024 * 1024:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_payload_size"})
                return

            raw_body = self.rfile.read(content_len)
            try:
                update = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return

            # Telegram'ın yeniden denemelerini önlemek için hemen 200 OK dönüp arka planda işle
            executor.submit(bot.handle_update, update)
            self._send_json(HTTPStatus.OK, {"ok": True})

    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), FortuneHTTPHandler)
    return server, executor


def run_webhook(bot: FortuneTellerBot) -> None:
    """Webhook sunucusunu başlatır ve Telegram'a HTTPS webhook adresini kaydeder."""
    endpoint = bot.config.webhook_endpoint
    if not endpoint:
        raise ValueError("Webhook kipi için WEBHOOK_URL veya RENDER_EXTERNAL_URL gerekli.")

    bot.telegram.set_my_commands(BOT_COMMANDS)
    bot.telegram.set_webhook(endpoint, secret_token=bot.config.webhook_secret)
    logger.info("Telegram webhook kaydedildi: %s", endpoint)

    server, executor = create_webhook_server(
        bot,
        host=bot.config.host,
        port=bot.config.port,
        secret_token=bot.config.webhook_secret,
        mode_label="webhook",
    )

    def _shutdown_handler(signum: int, _frame: Any) -> None:
        logger.info("Kapatma sinyali alındı (%s); sunucu durduruluyor...", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                signal.signal(sig, _shutdown_handler)
            except ValueError:
                pass

    logger.info("🔮 Fortune Teller Bot Webhook sunucusu %s:%d üzerinde dinliyor...", bot.config.host, bot.config.port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        executor.shutdown(wait=False)


def run_polling(bot: FortuneTellerBot, *, start_health_server: bool = True) -> None:
    """Long-polling döngüsünü başlatır; istenirse $PORT üzerinde /health sunucusu da açar."""
    try:
        bot.telegram.delete_webhook(drop_pending_updates=False)
    except TelegramError as exc:
        logger.warning("Eski webhook temizlenemedi (devam ediliyor): %s", exc)
    bot.telegram.set_my_commands(BOT_COMMANDS)

    health_srv: Optional[ThreadingHTTPServer] = None
    health_exec: Optional[ThreadPoolExecutor] = None
    if start_health_server and bot.config.port > 0:
        try:
            health_srv, health_exec = create_webhook_server(
                bot,
                host=bot.config.host,
                port=bot.config.port,
                secret_token=bot.config.webhook_secret,
                mode_label="polling",
                max_workers=2,
            )
            threading.Thread(target=health_srv.serve_forever, daemon=True, name="health-http").start()
            logger.info("Sağlık kontrol sunucusu %s:%d (/health) üzerinde açık.", bot.config.host, bot.config.port)
        except OSError as exc:
            logger.debug("Sağlık sunucusu başlatılamadı (%s); yalnız polling devam ediyor.", exc)

    offset: Optional[int] = None
    logger.info("🔮 Fortune Teller Bot polling kipinde uyandı ve Telegram mesajlarını bekliyor...")
    try:
        while True:
            try:
                updates = bot.telegram.get_updates(offset=offset, timeout=25)
                for upd in updates:
                    uid = upd.get("update_id")
                    if isinstance(uid, int):
                        offset = uid + 1
                    bot.handle_update(upd)
            except KeyboardInterrupt:
                logger.info("Polling kullanıcı tarafından durduruldu.")
                break
            except Exception as exc:
                logger.warning("Polling geçici hata (%s); 4 sn sonra yeniden denenecek.", exc)
                time.sleep(4)
    finally:
        if health_srv is not None:
            health_srv.shutdown()
            health_srv.server_close()
        if health_exec is not None:
            health_exec.shutdown(wait=False)


def run_once(bot: FortuneTellerBot) -> int:
    """Bekleyen tüm Telegram mesajlarını tek seferde işleyip ofseti onaylar (Actions kipi)."""
    bot.telegram.set_my_commands(BOT_COMMANDS)
    updates = bot.telegram.get_updates(timeout=0)
    if not updates:
        logger.info("Bekleyen yeni Telegram mesajı bulunamadı.")
        return 0

    max_uid: Optional[int] = None
    for upd in updates:
        uid = upd.get("update_id")
        if isinstance(uid, int) and (max_uid is None or uid > max_uid):
            max_uid = uid
        bot.handle_update(upd)

    if max_uid is not None:
        # İşlenen güncellemeleri Telegram kuyruğundan temizle
        bot.telegram.get_updates(offset=max_uid + 1, timeout=0)
    logger.info("Toplam %d Telegram güncellemesi işlendi.", len(updates))
    return len(updates)
