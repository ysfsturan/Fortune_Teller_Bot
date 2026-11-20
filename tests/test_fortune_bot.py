"""Fortune Teller Bot birim ve entegrasyon testleri."""

from __future__ import annotations

import base64
import json
import os
import threading
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import httpx

from main import main as cli_main
from src.bot import FortuneTellerBot, main_menu_keyboard, zodiac_keyboard
from src.config import Config, ConfigError, load_config
from src.gemini_client import (
    GeminiError,
    GeminiFortuneClient,
    extract_generated_text,
    parse_and_rank_flash_models,
)
from src.mystic_data import (
    MAJOR_ARCANA,
    ZODIAC_SIGNS,
    draw_daily_card,
    draw_tarot_spread,
    draw_yes_no_oracle,
    resolve_zodiac_sign,
)
from src.server import create_webhook_server
from src.telegram_client import (
    TelegramClient,
    TelegramError,
    detect_image_mime,
    sanitize_telegram_html,
    split_message,
)


class ConfigTests(unittest.TestCase):
    def test_load_config_aliases_and_render_auto_webhook(self) -> None:
        env = {
            "BOT_TOKEN": "123456:ABC_TEST_TOKEN",
            "GEMINI_API_KEY": "AIza-test-key",
            "RENDER_EXTERNAL_URL": "https://fortune-teller-bot.onrender.com/",
            "PORT": "8080",
            "USER_COOLDOWN_SECONDS": "1.5",
        }
        with patch("src.config.load_dotenv", None), patch.dict(os.environ, env, clear=True):
            cfg = load_config()
        self.assertEqual(cfg.telegram_token, "123456:ABC_TEST_TOKEN")
        self.assertEqual(cfg.resolved_mode, "webhook")
        self.assertEqual(
            cfg.webhook_endpoint,
            "https://fortune-teller-bot.onrender.com/webhook",
        )
        self.assertEqual(cfg.port, 8080)
        self.assertEqual(cfg.user_cooldown_seconds, 1.5)
        self.assertGreaterEqual(len(cfg.webhook_secret), 16)

    def test_load_config_missing_token_raises(self) -> None:
        with patch("src.config.load_dotenv", None), patch.dict(os.environ, {"GEMINI_API_KEY": "k"}, clear=True):
            with self.assertRaises(ConfigError):
                load_config(require_telegram=True, require_gemini=True)


class MysticDataTests(unittest.TestCase):
    def test_tarot_spread_daily_card_and_zodiac_resolution(self) -> None:
        self.assertEqual(len(MAJOR_ARCANA), 22)
        self.assertEqual(len(ZODIAC_SIGNS), 12)

        spread = draw_tarot_spread(3)
        self.assertEqual([c.position for c in spread], ["Geçmiş", "Şimdi", "Gelecek"])
        self.assertEqual(len({c.card.number for c in spread}), 3)

        c1 = draw_daily_card(998877, date(2026, 11, 20))
        c2 = draw_daily_card(998877, date(2026, 11, 20))
        self.assertEqual(c1, c2)

        self.assertEqual(resolve_zodiac_sign("akrep").name_tr, "Akrep")
        self.assertEqual(resolve_zodiac_sign("Oğlak Burcu").key, "oglak")
        self.assertEqual(resolve_zodiac_sign("koc").key, "koc")
        self.assertEqual(resolve_zodiac_sign("virgo").key, "basak")
        self.assertIsNone(resolve_zodiac_sign("bilinmeyen"))

        oracle = draw_yes_no_oracle()
        self.assertIn(oracle.verdict, {"EVET", "HAYIR", "BELİRSİZ / ZAMANI VAR"})


class GeminiClientTests(unittest.TestCase):
    def test_model_ranking_excludes_non_text_and_handles_failover_and_vision(self) -> None:
        models_payload = {
            "models": [
                {"name": "models/gemini-2.5-flash-tts", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-flash-preview-image", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3-flash-preview", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }
        ranked = parse_and_rank_flash_models(models_payload)
        self.assertEqual(ranked[0], "gemini-3-flash-preview")
        self.assertIn("gemini-2.5-flash", ranked)
        self.assertNotIn("gemini-2.5-flash-tts", ranked)
        self.assertNotIn("gemini-2.5-flash-preview-image", ranked)

        # İlk model 404 dönünce sonraki modele geçmeli ve görsel inlineData göndermeli
        resp_models = MagicMock(status_code=200)
        resp_models.json.return_value = models_payload
        resp_404 = MagicMock(status_code=404, text="not found")
        resp_ok = MagicMock(status_code=200)
        resp_ok.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "☕ Fincanda güzel bir yol var."}]}}]
        }

        client = GeminiFortuneClient("AIza-fake")
        with patch("src.gemini_client.httpx.Client") as mock_http_cls:
            http_inst = mock_http_cls.return_value.__enter__.return_value
            http_inst.get.return_value = resp_models
            http_inst.post.side_effect = [resp_404, resp_ok]

            reply, used_model = client.generate_reading(
                system_instruction="Falcısın",
                user_prompt="Fincana bak",
                image_bytes=b"\xff\xd8\xff\xe0test-jpeg",
                image_mime="image/jpeg",
            )

        self.assertEqual(used_model, "gemini-2.5-flash")
        self.assertIn("güzel bir yol", reply)
        post_json = http_inst.post.call_args_list[1].kwargs["json"]
        parts = post_json["contents"][-1]["parts"]
        self.assertEqual(parts[0]["inlineData"]["mimeType"], "image/jpeg")
        self.assertEqual(
            base64.b64decode(parts[0]["inlineData"]["data"]),
            b"\xff\xd8\xff\xe0test-jpeg",
        )


class TelegramClientTests(unittest.TestCase):
    def test_html_sanitization_split_and_plain_fallback(self) -> None:
        raw = "**Başlık** <script>alert(1)</script> <b>kalın</b> ve 'tek'"
        cleaned = sanitize_telegram_html(raw)
        self.assertIn("<b>Başlık</b>", cleaned)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", cleaned)
        self.assertIn("<b>kalın</b>", cleaned)

        long_text = "\n\n".join([f"Paragraf {i}: " + ("a" * 350) for i in range(15)])
        parts = split_message(long_text, max_length=1200)
        self.assertGreater(len(parts), 3)
        self.assertTrue(all(len(p) <= 1200 for p in parts))

        self.assertEqual(detect_image_mime("photos/file.png"), "image/png")
        self.assertEqual(detect_image_mime("photos/file.jpg"), "image/jpeg")

        # HTML parse hatasında düz metin yedeği
        tg = TelegramClient("123:ABC")
        err_resp = MagicMock(status_code=400)
        err_resp.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: can't parse entities",
        }
        ok_resp = MagicMock(status_code=200)
        ok_resp.json.return_value = {"ok": True, "result": {"message_id": 1}}

        with patch("src.telegram_client.httpx.Client") as mock_cli_cls:
            cli = mock_cli_cls.return_value.__enter__.return_value
            cli.post.side_effect = [err_resp, ok_resp]
            tg.send_message(12345, "<b>bozuk < html</b>")

        self.assertEqual(cli.post.call_count, 2)
        second_payload = cli.post.call_args_list[1].kwargs["json"]
        self.assertNotIn("parse_mode", second_payload)


class BotFlowsTests(unittest.TestCase):
    def _make_bot(self) -> tuple[FortuneTellerBot, MagicMock, MagicMock]:
        cfg = Config(
            telegram_token="123:TOKEN",
            gemini_api_key="AIza-KEY",
            user_cooldown_seconds=0.0,
        )
        tg = MagicMock(spec=TelegramClient)
        gm = MagicMock(spec=GeminiFortuneClient)
        gm.generate_reading.return_value = ("✨ Yıldızlar seninle uyumlu.", "gemini-3-flash-preview")
        bot = FortuneTellerBot(cfg, tg, gm)
        return bot, tg, gm

    def test_commands_callbacks_photo_and_memory_flows(self) -> None:
        bot, tg, gm = self._make_bot()

        # 1. /start ana menü klavyesi döndürmeli
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "/start"}})
        self.assertEqual(tg.send_message.call_args.kwargs["reply_markup"], main_menu_keyboard())

        # 2. /tarot 3 kart açılımı + Gemini yorumu göndermeli
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "/tarot İş hayatım"}})
        tarot_msg = tg.send_message.call_args.args[1]
        self.assertIn("3 Kart Tarot Açılımı", tarot_msg)
        self.assertIn("Geçmiş", tarot_msg)
        self.assertIn("Gelecek", tarot_msg)

        # 3. /burc (argümansız) 12 burç butonlarını göstermeli, callback zodiac:akrep yorum üretmeli
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "/burc"}})
        self.assertEqual(tg.send_message.call_args.kwargs["reply_markup"], zodiac_keyboard())

        bot.handle_update(
            {
                "callback_query": {
                    "id": "cb-1",
                    "from": {"id": 111},
                    "message": {"chat": {"id": 111}},
                    "data": "zodiac:akrep",
                }
            }
        )
        tg.answer_callback_query.assert_called_with("cb-1")
        self.assertIn("Akrep Burcu Mistik Yorumu", tg.send_message.call_args.args[1])

        # 4. Kahve fincanı fotoğrafı indirilip Gemini Vision'a gönderilmeli
        tg.get_file_bytes.return_value = (b"fake-img", "image/jpeg")
        bot.handle_update(
            {
                "message": {
                    "chat": {"id": 111},
                    "from": {"id": 111},
                    "photo": [{"file_id": "small"}, {"file_id": "large-photo"}],
                    "caption": "Kariyerim için bak",
                }
            }
        )
        tg.get_file_bytes.assert_called_with("large-photo")
        self.assertEqual(gm.generate_reading.call_args.kwargs["image_bytes"], b"fake-img")
        self.assertIn("Kahve Falın Hazır", tg.send_message.call_args.args[1])

        # 5. Serbest metin sohbet hafızasını kullanmalı ve /sifirla temizlemeli
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "Bana şanslı günümü söyle"}})
        self.assertGreater(len(bot._get_history("111")), 0)
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "/sifirla"}})
        self.assertEqual(bot._get_history("111"), [])


class WebhookServerTests(unittest.TestCase):
    def test_webhook_http_health_secret_check_and_update_dispatch(self) -> None:
        dispatched: list[dict[str, object]] = []
        handled_event = threading.Event()

        mock_bot = MagicMock(spec=FortuneTellerBot)

        def _fake_handle(upd: dict[str, object]) -> None:
            dispatched.append(upd)
            handled_event.set()

        mock_bot.handle_update.side_effect = _fake_handle

        srv, executor = create_webhook_server(
            mock_bot,
            host="127.0.0.1",
            port=0,
            secret_token="top-secret-123",
            mode_label="webhook",
        )
        srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
        srv_thread.start()
        try:
            port = srv.server_address[1]
            base = f"http://127.0.0.1:{port}"

            with httpx.Client(timeout=5.0) as client:
                health = client.get(f"{base}/health")
                self.assertEqual(health.status_code, 200)
                self.assertEqual(health.json()["status"], "ok")

                forbidden = client.post(
                    f"{base}/webhook",
                    headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
                    json={"update_id": 1},
                )
                self.assertEqual(forbidden.status_code, 403)

                accepted = client.post(
                    f"{base}/webhook",
                    headers={"X-Telegram-Bot-Api-Secret-Token": "top-secret-123"},
                    json={"update_id": 42, "message": {"text": "/start"}},
                )
                self.assertEqual(accepted.status_code, 200)
                self.assertTrue(accepted.json()["ok"])

            self.assertTrue(handled_event.wait(timeout=2.0))
            self.assertEqual(len(dispatched), 1)
            self.assertEqual(dispatched[0]["update_id"], 42)
        finally:
            srv.shutdown()
            srv.server_close()
            executor.shutdown(wait=True)

    def test_cli_test_gemini_flag(self) -> None:
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-fake"}, clear=True),
            patch("src.config.load_dotenv", None),
            patch("main.GeminiFortuneClient.test_connection", return_value=("gemini-3-flash-preview", ["gemini-3-flash-preview"])),
        ):
            rc = cli_main(["--test-gemini"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
