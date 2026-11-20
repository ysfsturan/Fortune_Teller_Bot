"""Fortune Teller Bot ana güncelleme yönlendiricisi ve çok modlu fal akışları."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, date
from typing import Any, Optional
from zoneinfo import ZoneInfo

from .config import Config
from .gemini_client import GeminiError, GeminiFortuneClient
from .mystic_data import (
    ZODIAC_SIGNS,
    DrawnTarotCard,
    draw_daily_card,
    draw_tarot_spread,
    draw_yes_no_oracle,
    resolve_zodiac_sign,
)
from .telegram_client import TelegramClient, TelegramError

logger = logging.getLogger(__name__)

BOT_COMMANDS: list[dict[str, str]] = [
    {"command": "start", "description": "Botu başlat ve ana menüyü aç"},
    {"command": "tarot", "description": "3 kartlı Tarot açılımı yap"},
    {"command": "gunun_karti", "description": "Bugün için günlük tarot kartını çek"},
    {"command": "kahve", "description": "Kahve fincanı fotoğrafıyla fal baktır"},
    {"command": "burc", "description": "12 burçtan günlük mistik yorum al"},
    {"command": "evethayir", "description": "Evet/Hayır sarkaçına soru sor"},
    {"command": "ruya", "description": "Gördüğün rüyayı sembolleriyle yorumla"},
    {"command": "sifirla", "description": "Sohbet hafızasını temizle"},
    {"command": "yardim", "description": "Tüm komutları ve rehberi gör"},
]

_TEXT_SYSTEM_PROMPT = (
    "Sen eğlenceli, zarif, gizemli ama samimi ve bilge bir Türk astroloji, tarot ve kahve falı yorumcususun. "
    "Kullanıcıya sıcak bir kahve falı, tarot ya da yıldız haritası eşliğinde akıcı, içten, motive edici "
    "ve 150-240 kelimelik dengeli bir yanıt ver. Doğal ve okunaklı biçimlendirme için yalnızca kısa <b>kalın</b> "
    "başlıklar ve maddeler kullan; kesin tıbbi, hukuki veya finansal garanti verme."
)

_COFFEE_VISION_SYSTEM_PROMPT = (
    "Sen deneyimli, sezgisi güçlü bir Türk kahve falı ustasısın. Gönderilen kahve fincanı veya tabak "
    "fotoğrafındaki telve desenlerini incele; fincandaki gerçek görsel formları (ör. yol, kuş, kalp, "
    "anahtar, balık, göz, dağ, ağaç, silüet vb.) gözlemleyerek anlat:\n"
    "1. ☕ <b>Fincanda Görülen Semboller</b>\n"
    "2. 💞 <b>Aşk, İlişkiler ve Çevre</b>\n"
    "3. 🎯 <b>İş, Para ve Yakın Gelecek</b>\n"
    "4. ✨ <b>Fincanın Kısa Öğüdü</b>\n"
    "Eğer görsel bir kahve fincanı değilse bunu kibar ve esprili bir dille belirt. Samimi, akıcı Türkçe yaz."
)


def main_menu_keyboard() -> dict[str, Any]:
    """Telegram sohbeti için etkileşimli ana menü butonlarını oluşturur."""
    return {
        "inline_keyboard": [
            [
                {"text": "🃏 3 Kart Tarot", "callback_data": "menu:tarot"},
                {"text": "🌙 Günün Kartı", "callback_data": "menu:daily"},
            ],
            [
                {"text": "☕ Kahve Falı", "callback_data": "menu:coffee"},
                {"text": "✨ Burç Yorumu", "callback_data": "menu:zodiac"},
            ],
            [
                {"text": "❓ Evet / Hayır", "callback_data": "menu:yesno"},
                {"text": "💭 Rüya Tabiri", "callback_data": "menu:dream"},
            ],
        ]
    }


def zodiac_keyboard() -> dict[str, Any]:
    """12 burç seçim butonlarını 4x3 düzeninde döndürür."""
    rows: list[list[dict[str, str]]] = []
    current_row: list[dict[str, str]] = []
    for sign in ZODIAC_SIGNS:
        current_row.append(
            {"text": f"{sign.symbol} {sign.name_tr}", "callback_data": f"zodiac:{sign.key}"}
        )
        if len(current_row) == 3:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([{"text": "🔙 Ana Menü", "callback_data": "menu:home"}])
    return {"inline_keyboard": rows}


def _format_cards_header(cards: list[DrawnTarotCard]) -> str:
    lines: list[str] = []
    for item in cards:
        lines.append(
            f"• <b>{item.position}:</b> {item.card.emoji} <b>{item.card.name_tr}</b> "
            f"<i>({item.orientation_label})</i> — {item.active_meaning}"
        )
    return "\n".join(lines)


class FortuneTellerBot:
    """Telegram güncellemelerini işleyen çok modlu Fortune Teller Bot motoru."""

    def __init__(
        self,
        config: Config,
        telegram_client: TelegramClient,
        gemini_client: GeminiFortuneClient,
        *,
        max_history_turns: int = 6,
        max_cached_chats: int = 500,
    ) -> None:
        self.config = config
        self.telegram = telegram_client
        self.gemini = gemini_client
        self.max_history_turns = max_history_turns
        self.max_cached_chats = max_cached_chats
        self._lock = threading.Lock()
        self._histories: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._last_request_at: dict[str, float] = {}

    def _today_local(self) -> date:
        try:
            tz = ZoneInfo(self.config.timezone_name)
            return datetime.now(tz).date()
        except Exception:
            return datetime.now().date()

    def _is_authorized(self, chat_id: int | str) -> bool:
        if not self.config.allowed_chat_ids:
            return True
        return str(chat_id) in set(self.config.allowed_chat_ids)

    def _check_cooldown(self, user_key: str) -> bool:
        """Kullanıcının ardışık spam yapmasını nazikçe sınırlar; izin verirse True döndürür."""
        cooldown = self.config.user_cooldown_seconds
        if cooldown <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            last = self._last_request_at.get(user_key, 0.0)
            if (now - last) < cooldown:
                return False
            self._last_request_at[user_key] = now
            if len(self._last_request_at) > 2000:
                oldest = next(iter(self._last_request_at))
                self._last_request_at.pop(oldest, None)
        return True

    def _get_history(self, chat_key: str) -> list[dict[str, str]]:
        with self._lock:
            hist = self._histories.get(chat_key)
            if hist is None:
                return []
            self._histories.move_to_end(chat_key)
            return list(hist)

    def _append_history(self, chat_key: str, user_text: str, model_text: str) -> None:
        with self._lock:
            hist = self._histories.setdefault(chat_key, [])
            hist.append({"role": "user", "text": user_text[:500]})
            hist.append({"role": "model", "text": model_text[:800]})
            if len(hist) > self.max_history_turns:
                self._histories[chat_key] = hist[-self.max_history_turns :]
            self._histories.move_to_end(chat_key)
            while len(self._histories) > self.max_cached_chats:
                self._histories.popitem(last=False)

    def _clear_history(self, chat_key: str) -> None:
        with self._lock:
            self._histories.pop(chat_key, None)

    @staticmethod
    def _help_text() -> str:
        return (
            "🔮 <b>Fortune Teller Bot — Kullanım Rehberi</b>\n\n"
            "• <code>/tarot [soru]</code> — Geçmiş / Şimdi / Gelecek 3 kart açılımı\n"
            "• <code>/gunun_karti</code> (veya <code>/kart</code>) — Bugüne özel tarot kartın\n"
            "• <code>/kahve</code> veya <b>fincan fotoğrafı gönder</b> — Yapay zekâ destekli kahve falı\n"
            "• <code>/burc akrep</code> (veya <code>/burc</code>) — 12 burç için mistik günlük yorum\n"
            "• <code>/evethayir &lt;soru&gt;</code> — Mistik sarkaçla hızlı Evet / Hayır cevabı\n"
            "• <code>/ruya &lt;rüya&gt;</code> — Rüyandaki sembollerin yorumu\n"
            "• <code>/sifirla</code> — Önceki sohbet hafızasını temizle\n\n"
            "💬 Ayrıca doğrudan aklındaki herhangi bir soruyu yazabilir ya da aşağıdan mod seçebilirsin!"
        )

    @staticmethod
    def _welcome_text() -> str:
        return (
            "🔮 <b>Hoş geldin! Ben senin kişisel mistik falcınım.</b>\n\n"
            "Bana aklındaki bir soruyu yazabilir, kahve fincanının fotoğrafını gönderebilir "
            "veya aşağıdaki düğmelerden hemen bir fal açabilirsin:"
        )

    def _safe_generate(
        self,
        *,
        chat_id: int | str,
        system_instruction: str,
        user_prompt: str,
        use_history: bool = False,
        history_label: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/jpeg",
    ) -> Optional[str]:
        chat_key = str(chat_id)
        history = self._get_history(chat_key) if use_history else None
        try:
            text, used_model = self.gemini.generate_reading(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                history=history,
                image_bytes=image_bytes,
                image_mime=image_mime,
            )
            logger.debug("Yanıt üretildi (chat=%s, model=%s).", chat_key, used_model)
            if use_history or history_label:
                self._append_history(chat_key, history_label or user_prompt, text)
            return text
        except GeminiError as exc:
            logger.error("Gemini fal hatası (chat=%s): %s", chat_key, exc)
            return None
        except Exception as exc:
            logger.exception("Beklenmeyen Gemini hatası (chat=%s): %s", chat_key, exc)
            return None

    def _handle_tarot(self, chat_id: int | str, question: str) -> None:
        self.telegram.send_chat_action(chat_id, "typing")
        cards = draw_tarot_spread(3)
        cards_summary = _format_cards_header(cards)
        q_part = f"Kullanıcının niyeti/sorusu: '{question}'." if question else "Kullanıcı genel bir rehberlik niyetiyle açılım yaptı."
        prompt = (
            f"{q_part}\n"
            "Aşağıdaki 3 Büyük Arkana kartı çekildi. Bu kartların düz/ters anlamlarını ve aralarındaki "
            "bağı kullanarak derin, bütünlüklü ve sıcak bir Türkçe tarot okuması yap:\n"
            + "\n".join(
                f"- {c.position}: {c.card.name_tr} ({c.orientation_label}) - {c.active_meaning}"
                for c in cards
            )
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            history_label=f"/tarot {question}".strip(),
        )
        if reading is None:
            body = "✨ Yıldızlar şu an biraz puslu, enerjiyi tam alamadım. Lütfen birazdan tekrar dene!"
        else:
            body = reading
        msg = f"🃏 <b>3 Kart Tarot Açılımı</b>\n\n{cards_summary}\n\n{body}"
        self.telegram.send_message(chat_id, msg, reply_markup=main_menu_keyboard())

    def _handle_daily_card(self, chat_id: int | str, user_id: int | str) -> None:
        self.telegram.send_chat_action(chat_id, "typing")
        today = self._today_local()
        drawn = draw_daily_card(user_id, today)
        prompt = (
            f"Kullanıcı {today.strftime('%d.%m.%Y')} günü için 'Günün Kartı' olarak "
            f"{drawn.card.name_tr} ({drawn.orientation_label}: {drawn.active_meaning}) kartını çekti. "
            "Bu kartın bugün için verdiği ana mesajı, dikkat edilecek noktayı ve küçük bir günün niyetini yaz."
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            history_label=f"/gunun_karti ({drawn.card.name_tr})",
        )
        header = (
            f"🌙 <b>Günün Tarot Kartı ({today.strftime('%d.%m.%Y')})</b>\n\n"
            f"{drawn.card.emoji} <b>{drawn.card.name_tr}</b> <i>({drawn.orientation_label})</i>\n"
            f"🔑 <i>{drawn.active_meaning}</i>"
        )
        body = reading or "✨ Bugün sezgilerine kulak ver ve sakin adımlarla ilerle."
        self.telegram.send_message(chat_id, f"{header}\n\n{body}", reply_markup=main_menu_keyboard())

    def _handle_zodiac(self, chat_id: int | str, raw_arg: str) -> None:
        sign = resolve_zodiac_sign(raw_arg)
        if sign is None:
            self.telegram.send_message(
                chat_id,
                "✨ <b>Hangi burcun yorumunu görmek istersin?</b>\nAşağıdan seçebilir veya <code>/burc akrep</code> yazabilirsin:",
                reply_markup=zodiac_keyboard(),
            )
            return
        self.telegram.send_chat_action(chat_id, "typing")
        today = self._today_local()
        prompt = (
            f"Tarih: {today.strftime('%d.%m.%Y')}. Kullanıcı <b>{sign.name_tr} ({sign.element})</b> burcu "
            "için günlük yorum istiyor. Aşk, iş/hedefler ve günün şans enerjisi başlıklarıyla akıcı Türkçe yorum yaz."
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            history_label=f"/burc {sign.name_tr}",
        )
        if reading is None:
            reading = "✨ Gökyüzü verisi şu an yoğun, lütfen birkaç saniye sonra tekrar dene!"
        header = f"{sign.symbol} <b>{sign.name_tr} Burcu Mistik Yorumu</b> <i>({sign.element})</i>"
        self.telegram.send_message(chat_id, f"{header}\n\n{reading}", reply_markup=main_menu_keyboard())

    def _handle_yes_no(self, chat_id: int | str, question: str) -> None:
        if not question:
            self.telegram.send_message(
                chat_id,
                "❓ <b>Evet / Hayır Sarkaçı</b>\nSorunu şu şekilde yazabilirsin:\n<code>/evethayir Yeni iş teklifini kabul etmeli miyim?</code>",
            )
            return
        self.telegram.send_chat_action(chat_id, "typing")
        oracle = draw_yes_no_oracle()
        prompt = (
            f"Kullanıcının Evet/Hayır sorusu: '{question}'.\n"
            f"Mistik sarkaç cevabı: {oracle.verdict} ({oracle.tone_note}).\n"
            "Bu cevaba sadık kalarak soruya 3-4 cümlelik sezgisel ve yapıcı Türkçe yorum ekle."
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            history_label=f"/evethayir {question}",
        )
        msg = (
            f"❓ <b>Mistik Sarkaç Yanıtı</b>\n\n"
            f"<b>Soru:</b> {question}\n"
            f"<b>Yanıt:</b> {oracle.emoji} <b>{oracle.verdict}</b>\n\n"
            f"{reading or oracle.tone_note}"
        )
        self.telegram.send_message(chat_id, msg, reply_markup=main_menu_keyboard())

    def _handle_dream(self, chat_id: int | str, dream_text: str) -> None:
        if not dream_text:
            self.telegram.send_message(
                chat_id,
                "💭 <b>Rüya Tabiri</b>\nRüyanı kısaca anlat, sembollerini yorumlayayım:\n"
                "<code>/ruya Rüyamda berrak bir denizde yüzdüğümü gördüm</code>",
            )
            return
        self.telegram.send_chat_action(chat_id, "typing")
        prompt = (
            f"Kullanıcının gördüğü rüya: '{dream_text}'.\n"
            "Bu rüyadaki ana sembolleri, psikolojik/sezgisel çağrışımları ve önümüzdeki günler için "
            "verdiği mesajı 2-3 kısa başlıkta yorumla."
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            use_history=True,
            history_label=f"/ruya {dream_text}",
        )
        if reading is None:
            self.telegram.send_message(
                chat_id,
                "✨ Rüya sembolleri şu an biraz sisli, lütfen az sonra tekrar dene!",
            )
            return
        self.telegram.send_message(
            chat_id,
            f"💭 <b>Rüya Tabiri</b>\n\n{reading}",
            reply_markup=main_menu_keyboard(),
        )

    def _handle_photo(self, chat_id: int | str, user_id: int | str, message: dict[str, Any]) -> None:
        user_key = str(user_id or chat_id)
        if not self._check_cooldown(user_key):
            self.telegram.send_message(
                chat_id,
                "⏳ Fincan soğurken birkaç saniye nefes alalım; hemen ardından tekrar gönderebilirsin.",
            )
            return

        photos = message.get("photo")
        file_id: Optional[str] = None
        if isinstance(photos, list) and photos:
            best = photos[-1]
            if isinstance(best, dict) and best.get("file_id"):
                file_id = str(best["file_id"])
        elif isinstance(message.get("document"), dict):
            doc = message["document"]
            mime = str(doc.get("mime_type") or "").lower()
            if mime.startswith("image/") and doc.get("file_id"):
                file_id = str(doc["file_id"])

        if not file_id:
            return

        self.telegram.send_chat_action(chat_id, "typing")
        try:
            img_bytes, mime_type = self.telegram.get_file_bytes(file_id)
        except TelegramError as exc:
            logger.warning("Fotoğraf indirilemedi (chat=%s): %s", chat_id, exc)
            self.telegram.send_message(
                chat_id,
                "⚠️ Fotoğrafı Telegram sunucusundan indirirken sorun oldu. Lütfen 5 MB altında net bir fincan fotoğrafı gönder.",
            )
            return

        caption = str(message.get("caption") or "").strip()
        user_prompt = (
            f"Kullanıcının notu: '{caption}'. Lütfen fotoğrafını gönderdiği kahve falını detaylı ama sıcak biçimde yorumla."
            if caption
            else "Kullanıcı kahve falına baktırmak için fincan fotoğrafını gönderdi. Fincandaki telveyi yorumla."
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_COFFEE_VISION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            image_bytes=img_bytes,
            image_mime=mime_type,
            history_label=f"[Kahve Fincanı Fotoğrafı] {caption}".strip(),
        )
        if reading is None:
            self.telegram.send_message(
                chat_id,
                "✨ Fincandaki telveleri şu an net seçemedim; lütfen birazdan yeniden dene!",
            )
            return
        self.telegram.send_message(
            chat_id,
            f"☕ <b>Kahve Falın Hazır</b>\n\n{reading}",
            reply_markup=main_menu_keyboard(),
        )

    def _handle_free_text(self, chat_id: int | str, user_id: int | str, text: str) -> None:
        user_key = str(user_id or chat_id)
        if not self._check_cooldown(user_key):
            self.telegram.send_message(
                chat_id,
                "⏳ Yıldız enerjisi toplanıyor, lütfen birkaç saniye bekleyip tekrar yaz.",
            )
            return

        self.telegram.send_chat_action(chat_id, "typing")
        prompt = (
            "Kullanıcının mesajına kahve falı / tarot / astroloji harmanıyla samimi, bilge ve gizemli bir "
            f"yanıt ver:\n'{text}'"
        )
        reading = self._safe_generate(
            chat_id=chat_id,
            system_instruction=_TEXT_SYSTEM_PROMPT,
            user_prompt=prompt,
            use_history=True,
            history_label=text,
        )
        if reading is None:
            self.telegram.send_message(
                chat_id,
                "✨ Yıldızlar şu an biraz puslu, enerjiyi tam alamadım. Lütfen birazdan tekrar dene!",
            )
            return
        self.telegram.send_message(chat_id, reading, reply_markup=main_menu_keyboard())

    def _handle_command(
        self,
        chat_id: int | str,
        user_id: int | str,
        raw_text: str,
    ) -> None:
        parts = raw_text.strip().split(maxsplit=1)
        cmd_raw = parts[0][1:].split("@")[0]
        cmd = cmd_raw.replace("İ", "i").replace("I", "ı").lower()
        cmd = (
            cmd.replace("ğ", "g")
            .replace("ü", "u")
            .replace("ş", "s")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("ı", "i")
        )
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "start":
            self.telegram.send_message(chat_id, self._welcome_text(), reply_markup=main_menu_keyboard())
            return
        if cmd in {"yardim", "help"}:
            self.telegram.send_message(chat_id, self._help_text(), reply_markup=main_menu_keyboard())
            return
        if cmd in {"sifirla", "reset"}:
            self._clear_history(str(chat_id))
            self.telegram.send_message(
                chat_id,
                "🧹 Sohbet hafızası temizlendi. Yepyeni bir niyetle başlayabilirsin!",
                reply_markup=main_menu_keyboard(),
            )
            return
        if cmd == "kahve":
            self.telegram.send_message(
                chat_id,
                "☕ <b>Kahve Falı</b>\n\n"
                "Kapattığın fincanın içini (ve istersen tabağını) aydınlıkta çekip bu sohbete "
                "<b>fotoğraf olarak gönder</b> — telvedeki tüm sembolleri tek tek yorumlayayım!",
            )
            return

        user_key = str(user_id or chat_id)
        if not self._check_cooldown(user_key):
            self.telegram.send_message(
                chat_id,
                "⏳ Yıldız enerjisi toplanıyor, lütfen birkaç saniye sonra tekrar dene.",
            )
            return

        if cmd == "tarot":
            self._handle_tarot(chat_id, arg)
        elif cmd in {"gunun_karti", "kart"}:
            self._handle_daily_card(chat_id, user_id)
        elif cmd == "burc":
            self._handle_zodiac(chat_id, arg)
        elif cmd in {"evethayir", "evet_hayir"}:
            self._handle_yes_no(chat_id, arg)
        elif cmd == "ruya":
            self._handle_dream(chat_id, arg)
        else:
            self.telegram.send_message(chat_id, self._help_text(), reply_markup=main_menu_keyboard())

    def _handle_callback(self, callback: dict[str, Any]) -> None:
        cb_id = str(callback.get("id") or "")
        msg = callback.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        from_user = (callback.get("from") or {}).get("id") or chat_id
        data = str(callback.get("data") or "").strip()

        if cb_id:
            self.telegram.answer_callback_query(cb_id)
        if chat_id is None or not self._is_authorized(chat_id):
            return

        if data == "menu:home":
            self.telegram.send_message(chat_id, self._welcome_text(), reply_markup=main_menu_keyboard())
            return
        if data == "menu:coffee":
            self.telegram.send_message(
                chat_id,
                "☕ Fincanının net bir fotoğrafını bu sohbete gönder; hemen falına bakayım!",
            )
            return
        if data == "menu:zodiac":
            self.telegram.send_message(
                chat_id,
                "✨ <b>Burcunu Seç:</b>",
                reply_markup=zodiac_keyboard(),
            )
            return
        if data == "menu:yesno":
            self.telegram.send_message(
                chat_id,
                "❓ <b>Evet / Hayır Sarkaçı</b>\nSorunu şu biçimde gönder:\n<code>/evethayir ...</code>",
            )
            return
        if data == "menu:dream":
            self.telegram.send_message(
                chat_id,
                "💭 <b>Rüya Tabiri</b>\nRüyanı şu biçimde gönder:\n<code>/ruya ...</code>",
            )
            return

        user_key = str(from_user or chat_id)
        if not self._check_cooldown(user_key):
            self.telegram.send_message(
                chat_id,
                "⏳ Yıldız enerjisi toplanıyor, birkaç saniye sonra tekrar dokun.",
            )
            return

        if data == "menu:tarot":
            self._handle_tarot(chat_id, "")
        elif data == "menu:daily":
            self._handle_daily_card(chat_id, user_key)
        elif data.startswith("zodiac:"):
            sign_key = data.split(":", 1)[1]
            self._handle_zodiac(chat_id, sign_key)

    def handle_update(self, update: dict[str, Any]) -> None:
        """Tek bir Telegram Update JSON nesnesini güvenli biçimde işler."""
        if not isinstance(update, dict):
            return
        try:
            if isinstance(update.get("callback_query"), dict):
                self._handle_callback(update["callback_query"])
                return

            message = update.get("message")
            if not isinstance(message, dict):
                return
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is None or not self._is_authorized(chat_id):
                return

            user_id = (message.get("from") or {}).get("id") or chat_id
            if message.get("photo") or (
                isinstance(message.get("document"), dict)
                and str(message["document"].get("mime_type") or "").lower().startswith("image/")
            ):
                self._handle_photo(chat_id, user_id, message)
                return

            raw_text = str(message.get("text") or "").strip()
            if not raw_text:
                return
            if raw_text.startswith("/"):
                self._handle_command(chat_id, user_id, raw_text)
            else:
                self._handle_free_text(chat_id, user_id, raw_text)
        except Exception as exc:
            logger.exception("Telegram update işlenirken hata oluştu: %s", exc)
