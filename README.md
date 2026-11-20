<div align="right">
  <a href="#-english">🇬🇧 English</a> • <a href="#-türkçe">🇹🇷 Türkçe</a>
</div>

# 🇬🇧 English

# 🔮 Fortune Teller Bot

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Auto%20Flash%20%2B%20Vision-orange?style=for-the-badge&logo=google)
![Telegram](https://img.shields.io/badge/Telegram-Webhook%20%26%20Polling-26A5E4?style=for-the-badge&logo=telegram)
![Render](https://img.shields.io/badge/Render-Web%20Service%20Blueprint-46E3B7?style=for-the-badge&logo=render)

**Fortune Teller Bot** is an AI-powered multimodal Telegram bot combining real Tarot spreads, multimodal **coffee cup photo reading**, daily zodiac readings, dream interpretation, and Yes/No oracle guidance using **Google Gemini Flash** (with automatic model discovery & fallback).

## ✨ What's New (v2.0)

- ☕ **Coffee Cup Photo Reading (Gemini Vision):** Send a photo of your Turkish coffee cup and get an interpretation based on the visible shapes in the grounds.
- 🃏 **Real 3-Card Tarot Spread (`/tarot`):** Draws 3 unique Major Arcana cards (Past / Present / Future, Upright or Reversed) and weaves them into a personalized reading.
- 🌙 **Daily Tarot Card (`/gunun_karti`):** Deterministic daily card tied to each user and calendar day.
- ✨ **12 Zodiac Signs & Buttons (`/burc`):** Interactive keyboard for all 12 signs + Turkish/English alias support.
- ❓ **Yes/No Pendulum (`/evethayir`)** & 💭 **Dream Interpretation (`/ruya`)** with short-term conversation memory (`/sifirla` to reset).
- 🌐 **Render Free Web Service Ready (`Webhook` + `/health`):** Bound to `$PORT` (`GET /health` returns `200 OK`) with secret-token verification on `/webhook`, plus optional **GitHub Actions Keep-Alive** (`RENDER_URL`) or standalone `--once` runner (`ENABLE_ACTIONS_POLLING=true`).
- 🔄 **Auto Flash Model Discovery & Failover:** Queries active `Gemini Flash` models via REST API (zero heavy SDK dependencies) and seamlessly falls back if a model returns 404/429.

---

## 🛠️ Quick Setup (Render 24/7 or GitHub Actions Free)

### Option A — Deploy 24/7 on Render (Recommended)
1. Fork this repository to your GitHub account.
2. On [Render.com](https://render.com), choose **New → Blueprint** (or **New → Web Service** using `render.yaml` / `python main.py`).
3. Add **Environment Variables**:
   - `TELEGRAM_TOKEN` = your bot token from [@BotFather](https://t.me/BotFather)
   - `GEMINI_API_KEY` = your key from [Google AI Studio](https://aistudio.google.com/app/apikey)
4. *(Optional anti-sleep keep-alive):* In your GitHub repo **Settings → Secrets and variables → Actions → Variables**, add `RENDER_URL` = `https://your-service.onrender.com` so the included `Fortune Teller Bot Runner` workflow pings `/health` every 14 minutes.

### Option B — Run Free via GitHub Actions Only (No Render Needed)
1. In your GitHub repo **Settings → Secrets and variables → Actions**:
   - **Secrets:** `TELEGRAM_TOKEN` and `GEMINI_API_KEY`
   - **Variables:** `ENABLE_ACTIONS_POLLING` = `true`
2. Enable workflows under **Actions**; pending Telegram messages are processed automatically on schedule or anytime via **Run workflow**.

### Option C — Local / Docker
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1 | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill TELEGRAM_TOKEN and GEMINI_API_KEY
python main.py
```

---

<br>

---

# 🇹🇷 Türkçe

# 🔮 Fortune Teller Bot (Yapay Zekâlı Telegram Falcısı)

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Otomatik%20Flash%20%2B%20Vision-orange?style=for-the-badge&logo=google)
![Telegram](https://img.shields.io/badge/Telegram-Webhook%20%26%20Polling-26A5E4?style=for-the-badge&logo=telegram)
![Render](https://img.shields.io/badge/Render-Web%20Service%20Blueprint-46E3B7?style=for-the-badge&logo=render)

**Fortune Teller Bot**, Telegram üzerinden **kahve fincanı fotoğrafı yorumlama**, gerçek 3 kartlı Tarot açılımı, günlük burç yorumları, rüya tabiri ve Evet/Hayır sarkaç yanıtları sunan yapay zekâ destekli çok modlu kişisel fal asistanıdır.

## 🚀 Özellikler

- ☕ **Fotoğrafla Kahve Falı (Gemini Vision):** Kapattığın kahve fincanının fotoğrafını doğrudan bota gönder; telvedeki sembolleri (yol, kalp, kuş, anahtar vb.) inceleyip yorumlasın.
- 🃏 **3 Kartlı Tarot Açılımı (`/tarot`):** 22 Büyük Arkana destesinden **Geçmiş / Şimdi / Gelecek** için Düz veya Ters 3 kart çekip soruna özel yorum yazar.
- 🌙 **Günün Kartı (`/gunun_karti`):** Sana ve bugüne özel gün boyu tutarlı tarot kartı enerjisi verir.
- ✨ **12 Burç Yorumu (`/burc`):** Etkileşimli burç butonlarıyla tek dokunuşta günlük astroloji rehberliği sağlar.
- ❓ **Evet / Hayır Sarkaçı (`/evethayir`) & 💭 Rüya Tabiri (`/ruya`):** Aklındaki sorular ve rüyalar için hızlı, kısa sohbet hafızalı (`/sifirla` ile temizlenir) yanıtlar sunar.
- 🔄 **Otomatik Aktif Gemini Flash Keşfi:** Sabit eski model adlarına takılı kalmaz; Google AI üzerinden güncel `Flash` modellerini otomatik bulur, `404`/`429` durumunda sıradaki modele otomatik geçer.
- ☁️ **Render Webhook + Sağlık Ucu (`/health`) & Actions Keep-Alive:** Render Free Web Service kapanmasın diye `$PORT` üzerinde `/health` ve güvenlik gizli anahtarlı (`/webhook`) HTTP sunucusu açar.

---

## 💬 Telegram Komutları

| Komut | Açıklama |
| --- | --- |
| `/start` | Botu başlatır ve etkileşimli ana menüyü açar |
| `/tarot [soru]` | Geçmiş / Şimdi / Gelecek 3 kartlı Tarot açılımı yapar |
| `/gunun_karti` (veya `/kart`) | Bugüne özel tarot kartını çeker |
| `/kahve` *(veya doğrudan fotoğraf)* | Kahve fincanı fotoğrafıyla görsel fal yorumu yapar |
| `/burc` (veya `/burc akrep`) | Burç seçim menüsünü açar veya doğrudan yorum getirir |
| `/evethayir <soru>` | Mistik sarkaçtan Evet / Hayır yanıtı alır |
| `/ruya <rüya>` | Rüyandaki sembolleri yorumlar |
| `/sifirla` | Sohbet geçmişini temizler |
| `/yardim` | Kullanım rehberini gösterir |

---

## 🛠️ Kurulum ve Tekrar Aktifleştirme

### Yöntem 1: Render.com Üzerinde 7/24 Çalıştırma (Önerilen)
1. Bu depoyu hesabına Forkla veya doğrudan bağla.
2. [Render.com](https://render.com) üzerinde **New → Web Service** (veya repo kökündeki [`render.yaml`](render.yaml) ile **Blueprint**) oluştur:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Health Check Path:** `/health`
3. **Environment Variables** alanına şu iki gizli bilgiyi ekle:
   - `TELEGRAM_TOKEN` = [@BotFather](https://t.me/BotFather) üzerinden aldığın Telegram Bot Token
   - `GEMINI_API_KEY` = [Google AI Studio](https://aistudio.google.com/app/apikey) üzerinden aldığın Gemini API Anahtarı
4. Servis ayağa kalktığında `RENDER_EXTERNAL_URL` otomatik algılanır ve bot **Webhook** kipine geçip anında yanıt verir.
5. **Uykuya Geçmesini Önleme (Keep-Alive):** GitHub deponda **Settings → Secrets and variables → Actions → Variables** içine `RENDER_URL` = `https://senin-servisin.onrender.com` eklersen, GitHub Actions her 14 dakikada bir `/health` adresine ping atarak servisi uyanık tutar.

### Yöntem 2: Sadece GitHub Actions İle Ücretsiz Çalıştırma (Sunucusuz)
Render kullanmak istemezsen GitHub Actions üzerinde de çalıştırabilirsin:
1. GitHub deponda **Settings → Secrets and variables → Actions** altına:
   - **Secrets:** `TELEGRAM_TOKEN`, `GEMINI_API_KEY`
   - **Variables:** `ENABLE_ACTIONS_POLLING` = `true`
2. **Actions → Fortune Teller Bot Runner** sekmesinden workflow'u etkinleştir (`python main.py --once` ile bekleyen mesajları düzenli olarak yanıtlar).

### Yöntem 3: Kendi Bilgisayarında / Docker
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # TELEGRAM_TOKEN ve GEMINI_API_KEY ekle
python main.py
```

Testleri çalıştırmak için:
```bash
python -m unittest discover -s tests -v
```

---

## ⚠️ Yasal Uyarı

Bu bot eğlence ve kişisel farkındalık amacıyla yapay zekâ dil ve görsel modelleri kullanılarak geliştirilmiştir; üretilen yanıtlar tıbbi, hukuki, psikolojik veya finansal tavsiye niteliği taşımaz.

---

<div align="center">
<i>Made with ❤️ by Yusuf Sami Turan</i><br><br>
<a href="https://www.linkedin.com/in/yusufsamituran">
  <img src="https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
</a>
</div>
