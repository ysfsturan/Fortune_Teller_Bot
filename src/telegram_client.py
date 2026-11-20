"""Telegram Bot API istemcisi: IPv4 zorlaması, HTML temizleme, mesaj bölme ve dosya indirme."""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4000
MAX_PHOTO_BYTES = 5 * 1024 * 1024

_ALLOWED_HTML_TAGS = ("b", "strong", "i", "em", "u", "s", "code", "pre", "blockquote")
_TAG_RESTORE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"&lt;(/?{tag})&gt;", re.IGNORECASE), r"<\1>")
    for tag in _ALLOWED_HTML_TAGS
]
_LINK_RESTORE_RE = re.compile(
    r"&lt;a\s+href=(?:&quot;|&#x27;)(https?://[^&\"'<>\s]+)(?:&quot;|&#x27;)&gt;(.*?)&lt;/a&gt;",
    re.IGNORECASE | re.DOTALL,
)
_BOLD_MD_RE = re.compile(r"\*\*(.+?)\*\*")
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


class TelegramError(Exception):
    """Telegram Bot API çağrısı başarısız olduğunda fırlatılır."""


def sanitize_telegram_html(raw: str) -> str:
    """Gemini Markdown/metnini Telegram'ın desteklediği güvenli HTML alt kümesine dönüştürür."""
    text = (raw or "").strip()
    if not text:
        return ""
    text = _BOLD_MD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    escaped = html.escape(text, quote=False)
    for pattern, repl in _TAG_RESTORE_PATTERNS:
        escaped = pattern.sub(repl, escaped)
    escaped = _LINK_RESTORE_RE.sub(
        lambda m: f'<a href="{html.escape(m.group(1), quote=True)}">{m.group(2)}</a>',
        escaped,
    )
    return escaped


def strip_html_tags(raw: str) -> str:
    """HTML biçimlendirme etiketlerini kaldırıp düz metin döndürür."""
    return html.unescape(_TAG_STRIP_RE.sub("", raw or ""))


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Uzun Telegram mesajlarını paragraf ve satır sınırlarını koruyarak parçalar."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_length:
        return [cleaned]

    chunks: list[str] = []
    current = ""
    for para in cleaned.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_length:
            current = para
            continue

        for line in para.splitlines():
            line_cand = f"{current}\n{line}" if current else line
            if len(line_cand) <= max_length:
                current = line_cand
            else:
                if current:
                    chunks.append(current)
                    current = ""
                for start in range(0, len(line), max_length):
                    part = line[start : start + max_length]
                    if len(part) == max_length:
                        chunks.append(part)
                    else:
                        current = part

    if current:
        chunks.append(current)
    return chunks


def detect_image_mime(file_path: str) -> str:
    """Telegram dosya uzantısından MIME türünü belirler."""
    low = (file_path or "").lower()
    if low.endswith(".png"):
        return "image/png"
    if low.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


class TelegramClient:
    """Thread-safe Telegram Bot API istemcisi (her çağrıda izole IPv4 httpx oturumu açar)."""

    def __init__(self, token: str, *, timeout: float = 20.0) -> None:
        self.token = token.strip()
        self.timeout = timeout
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.file_base = f"https://api.telegram.org/file/bot{self.token}"

    def _new_client(self, *, timeout: Optional[float] = None) -> httpx.Client:
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        return httpx.Client(
            transport=transport,
            timeout=timeout if timeout is not None else self.timeout,
            follow_redirects=True,
        )

    def _call(
        self,
        method: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        url = f"{self.api_base}/{method}"
        try:
            with self._new_client(timeout=timeout) as client:
                resp = client.post(url, json=payload or {})
                data = resp.json()
        except httpx.HTTPError as exc:
            raise TelegramError(f"Telegram {method} ağ hatası: {exc}") from exc
        except ValueError as exc:
            raise TelegramError(f"Telegram {method} geçersiz JSON yanıtı") from exc

        if not isinstance(data, dict) or not data.get("ok"):
            desc = data.get("description") if isinstance(data, dict) else "Bilinmeyen hata"
            code = data.get("error_code") if isinstance(data, dict) else resp.status_code
            raise TelegramError(f"Telegram {method} reddedildi ({code}): {desc}")
        return data.get("result")

    def send_chat_action(self, chat_id: int | str, action: str = "typing") -> None:
        """Kullanıcıya yazıyor / fotoğraf inceliyor durumu gösterir."""
        try:
            self._call("sendChatAction", {"chat_id": chat_id, "action": action}, timeout=5.0)
        except Exception as exc:
            logger.debug("sendChatAction atlandı: %s", exc)

    def answer_callback_query(
        self,
        callback_query_id: str,
        *,
        text: Optional[str] = None,
    ) -> None:
        """InlineKeyboard buton tıklamasının yükleniyor ikonunu kapatır."""
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:180]
        try:
            self._call("answerCallbackQuery", payload, timeout=5.0)
        except Exception as exc:
            logger.debug("answerCallbackQuery atlandı: %s", exc)

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        reply_markup: Optional[dict[str, Any]] = None,
        parse_mode: Optional[str] = "HTML",
    ) -> None:
        """Mesajı HTML korumalı biçimde ve 4000 karakter sınırı içinde gönderir."""
        formatted = sanitize_telegram_html(text) if parse_mode == "HTML" else (text or "").strip()
        parts = split_message(formatted)
        if not parts:
            return

        for idx, chunk in enumerate(parts):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if reply_markup is not None and idx == len(parts) - 1:
                payload["reply_markup"] = reply_markup

            try:
                self._call("sendMessage", payload)
            except TelegramError as exc:
                if parse_mode and "parse" in str(exc).lower():
                    logger.warning("Telegram HTML parse hatası (%s); düz metin deneniyor.", exc)
                    fallback_payload = {
                        "chat_id": chat_id,
                        "text": strip_html_tags(chunk),
                        "disable_web_page_preview": True,
                    }
                    if reply_markup is not None and idx == len(parts) - 1:
                        fallback_payload["reply_markup"] = reply_markup
                    self._call("sendMessage", fallback_payload)
                else:
                    raise

    def get_file_bytes(
        self,
        file_id: str,
        *,
        max_bytes: int = MAX_PHOTO_BYTES,
    ) -> tuple[bytes, str]:
        """Telegram üzerindeki fotoğrafı bellek içine indirir -> (bytes, mime_type)."""
        info = self._call("getFile", {"file_id": file_id})
        if not isinstance(info, dict) or not info.get("file_path"):
            raise TelegramError("Dosya yolu Telegram sunucusundan alınamadı.")
        file_size = info.get("file_size")
        if isinstance(file_size, int) and file_size > max_bytes:
            raise TelegramError(f"Görsel boyutu sınırı aşıyor ({file_size} bayt > {max_bytes}).")

        file_path = str(info["file_path"]).lstrip("/")
        download_url = f"{self.file_base}/{file_path}"
        with self._new_client(timeout=25.0) as client:
            resp = client.get(download_url)
            if resp.status_code >= 400:
                raise TelegramError(f"Dosya indirilemedi: HTTP {resp.status_code}")
            raw = resp.content
        if len(raw) > max_bytes:
            raise TelegramError("İndirilen görsel boyut sınırını aşıyor.")
        return raw, detect_image_mime(file_path)

    def get_updates(
        self,
        *,
        offset: Optional[int] = None,
        timeout: int = 25,
    ) -> list[dict[str, Any]]:
        """Bekleyen veya yeni Telegram güncellemelerini çeker."""
        payload: dict[str, Any] = {
            "timeout": max(0, int(timeout)),
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        res = self._call("getUpdates", payload, timeout=float(timeout) + 10.0)
        return list(res) if isinstance(res, list) else []

    def set_webhook(
        self,
        url: str,
        *,
        secret_token: Optional[str] = None,
    ) -> None:
        """Telegram webhook adresini ve güvenlik gizli anahtarını kaydeder."""
        payload: dict[str, Any] = {
            "url": url,
            "allowed_updates": ["message", "callback_query"],
        }
        if secret_token:
            payload["secret_token"] = secret_token
        self._call("setWebhook", payload)

    def delete_webhook(self, *, drop_pending_updates: bool = False) -> None:
        """Aktif Telegram webhook kaydını kaldırır (polling kipi için)."""
        self._call("deleteWebhook", {"drop_pending_updates": drop_pending_updates})

    def set_my_commands(self, commands: list[dict[str, str]]) -> None:
        """Telegram sohbet menüsüne `/` komut listesini kaydeder."""
        try:
            self._call("setMyCommands", {"commands": commands})
        except Exception as exc:
            logger.debug("setMyCommands atlandı: %s", exc)
