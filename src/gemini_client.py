"""Google Gemini Flash istemcisi: otomatik aktif model keşfi, çok modlu kahve falı ve güvenli fallback."""

from __future__ import annotations

import base64
import logging
import re
import threading
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
FALLBACK_FLASH_MODELS: tuple[str, ...] = (
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

_MODEL_VERSION_RE = re.compile(r"gemini-(\d+)(?:\.(\d+))?-flash")
_EXCLUDED_MODEL_TAGS = ("tts", "audio", "image", "embedding", "live", "robotics", "native")


class GeminiError(Exception):
    """Gemini API çağrısı başarısız olduğunda fırlatılır."""


def _rank_flash_model(model_name: str) -> tuple[int, int, int, int, int]:
    """Model adını önceliğe göre sıralar (büyük tuple önce seçilir)."""
    low = model_name.lower()
    match = _MODEL_VERSION_RE.search(low)
    major = int(match.group(1)) if match else 0
    minor = int(match.group(2) or 0) if match else 0
    is_not_lite = 0 if "lite" in low else 1
    is_stable = 1 if ("preview" not in low and "exp" not in low and "latest" not in low) else 0
    is_not_exp = 0 if "exp" in low else 1
    return (major, minor, is_not_lite, is_stable, is_not_exp)


def parse_and_rank_flash_models(models_payload: dict[str, Any]) -> list[str]:
    """Gemini /models JSON yanıtından aktif generateContent destekli Flash modelleri döndürür."""
    candidates: list[str] = []
    for entry in models_payload.get("models") or []:
        if not isinstance(entry, dict):
            continue
        raw_name = str(entry.get("name") or "").strip()
        short_name = raw_name.removeprefix("models/")
        low = short_name.lower()
        if "gemini" not in low or "flash" not in low:
            continue
        if any(tag in low for tag in _EXCLUDED_MODEL_TAGS):
            continue
        methods = entry.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        candidates.append(short_name)

    return sorted(set(candidates), key=_rank_flash_model, reverse=True)


def extract_generated_text(payload: dict[str, Any]) -> str:
    """Gemini generateContent yanıtından metni ayıklar."""
    for candidate in payload.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        chunks = [
            str(part.get("text") or "")
            for part in parts
            if isinstance(part, dict) and part.get("text")
        ]
        joined = "\n".join(c.strip() for c in chunks if c.strip()).strip()
        if joined:
            return joined
    return ""


class GeminiFortuneClient:
    """Aktif Gemini Flash modelleri arasında otomatik geçiş yapan çok modlu fal istemcisi."""

    def __init__(
        self,
        api_key: str,
        *,
        preferred_model: Optional[str] = None,
        timeout: float = 40.0,
        cache_ttl_seconds: float = 21600.0,
    ) -> None:
        self.api_key = api_key
        self.preferred_model = preferred_model.strip() if preferred_model else None
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self._lock = threading.Lock()
        self._cached_models: list[str] = []
        self._cached_at: float = 0.0

    def discover_flash_models(self, force_refresh: bool = False) -> list[str]:
        """Aktif Flash modellerini 6 saatlik bellek önbelleğiyle keşfeder."""
        now = time.monotonic()
        with self._lock:
            if (
                not force_refresh
                and self._cached_models
                and (now - self._cached_at) < self.cache_ttl_seconds
            ):
                return list(self._cached_models)

        discovered: list[str] = []
        try:
            with httpx.Client(timeout=min(self.timeout, 15.0)) as client:
                resp = client.get(
                    f"{GEMINI_API_BASE}/models",
                    headers={"x-goog-api-key": self.api_key},
                )
                if resp.status_code == 200:
                    discovered = parse_and_rank_flash_models(resp.json())
                else:
                    logger.warning("Gemini model keşfi HTTP %d döndü; yedek liste kullanılacak.", resp.status_code)
        except Exception as exc:
            logger.warning("Gemini model keşfi başarısız (%s); yedek liste kullanılacak.", exc)

        if discovered:
            with self._lock:
                self._cached_models = list(discovered)
                self._cached_at = time.monotonic()
        return discovered

    def _candidate_models(self) -> list[str]:
        candidates: list[str] = []
        if self.preferred_model:
            candidates.append(self.preferred_model.removeprefix("models/"))
        discovered = self.discover_flash_models()
        candidates.extend(discovered)
        candidates.extend(FALLBACK_FLASH_MODELS)

        unique: list[str] = []
        seen: set[str] = set()
        for m in candidates:
            if m and m not in seen:
                seen.add(m)
                unique.append(m)
        return unique

    @staticmethod
    def build_payload(
        *,
        system_instruction: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/jpeg",
        temperature: float = 0.85,
        max_output_tokens: int = 1400,
    ) -> dict[str, Any]:
        """Gemini REST generateContent JSON gövdesi oluşturur."""
        contents: list[dict[str, Any]] = []
        for turn in history or []:
            role = turn.get("role")
            text = (turn.get("text") or "").strip()
            if role in {"user", "model"} and text:
                contents.append({"role": role, "parts": [{"text": text}]})

        user_parts: list[dict[str, Any]] = []
        if image_bytes:
            user_parts.append(
                {
                    "inlineData": {
                        "mimeType": image_mime,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                }
            )
        user_parts.append({"text": user_prompt})
        contents.append({"role": "user", "parts": user_parts})

        return {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

    def generate_reading(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        history: Optional[list[dict[str, str]]] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/jpeg",
    ) -> tuple[str, str]:
        """Yorumu üretir ve `(yanıt_metni, kullanılan_model)` döndürür."""
        payload = self.build_payload(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            history=history,
            image_bytes=image_bytes,
            image_mime=image_mime,
        )
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        models = self._candidate_models()
        last_error = "Bilinmeyen Gemini API hatası"

        with httpx.Client(timeout=self.timeout) as client:
            for model in models:
                url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
                for attempt in range(2):
                    try:
                        resp = client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            text = extract_generated_text(resp.json())
                            if text:
                                return text, model
                            last_error = f"{model} boş yanıt döndürdü."
                            break
                        if resp.status_code in {401, 403}:
                            raise GeminiError(
                                f"Gemini API anahtarı geçersiz veya yetkisiz (HTTP {resp.status_code})."
                            )
                        if resp.status_code == 404:
                            last_error = f"{model} bulunamadı (HTTP 404)."
                            break
                        if resp.status_code in {429, 500, 502, 503, 504}:
                            last_error = f"{model} geçici hata HTTP {resp.status_code}"
                            if attempt == 0:
                                time.sleep(0.8)
                                continue
                            break
                        last_error = f"{model} HTTP {resp.status_code}: {resp.text[:200]}"
                        break
                    except GeminiError:
                        raise
                    except httpx.HTTPError as exc:
                        last_error = f"{model} ağ hatası: {exc}"
                        if attempt == 0:
                            time.sleep(0.6)
                            continue
                        break

        raise GeminiError(f"Hiçbir Gemini Flash modelinden yanıt alınamadı ({last_error}).")

    def test_connection(self) -> tuple[str, list[str]]:
        """Model keşfi ve kısa test üretimi yaparak `(kullanılan_model, keşfedilen_modeller)` döndürür."""
        discovered = self.discover_flash_models(force_refresh=True)
        text, used = self.generate_reading(
            system_instruction="Sen kısa ve sıcak bir fal asistanısın.",
            user_prompt="Tek cümlelik olumlu bir gün mesajı yaz.",
        )
        if not text:
            raise GeminiError("Gemini test yanıtı boş geldi.")
        return used, discovered
