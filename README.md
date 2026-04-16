<div align="right">
  <a href="#-english">🇬🇧 English</a> • <a href="#-türkçe">🇹🇷 Türkçe</a>
</div>

# 🇬🇧 English

# 🔮 Fortune Teller Bot

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-3%20Flash-orange?style=for-the-badge&logo=google)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram)
![Render](https://img.shields.io/badge/Render-Cloud%20Hosting-46E3B7?style=for-the-badge&logo=render)

**Fortune Teller Bot** is an AI-powered chatbot that provides users with personalized mystical readings via Telegram, combining the flavors of astrology, coffee cup reading, and tarot.

Unlike standard template sentences, this bot uses the speed and intelligence of the **Google Gemini 3 Flash** model to generate instant, fluent, and highly contextual responses to user questions in a "fortune teller" persona.

## 🚀 Features

* **🎭 Realistic Fortune Teller Persona:** It doesn't just give horoscope readings; it approaches your questions, a specific name, or a topic you want to vent about with a mystical tone.
* **⚡ High Speed & Low Latency:** Thanks to Google's low-latency focused Gemini 3 Flash model and asynchronous (async) Telegram infrastructure, it replies to messages within seconds.
* **☁️ 24/7 Uninterrupted Service:** Since it is hosted on the Render cloud server, it remains continuously online even if your local computer is turned off.

---

## ⚙️ How It Works

1. **Interaction:** The user contacts the bot by writing a direct question via Telegram.
2. **Prompt Engineering:** The user's message is combined with a special system command in the background that assigns the bot the identity of a "wise figure who blends mystery, sincerity, and astrological foresight."
3. **AI Generation:** The Gemini 3 Flash API processes this data and creates an impressive text as if looking into a coffee cup or reading tarot cards.
4. **Fast Delivery:** The generated response instantly drops into the user's Telegram chat.

---

## 🛠️ Installation

This project is optimized to run 24/7 on cloud platforms like **Render.com**. You can follow the steps below to set up your own bot:

### 1. Fork the Project 🍴
Add this project to your own GitHub account by clicking the **Fork** button in the top right corner of the page.

### 2. Get the Necessary Keys 🔑
* **Google Gemini API Key:** Get your free key from [Google AI Studio](https://aistudio.google.com/app/apikey).
* **Telegram Bot Token:** Start a chat with [@BotFather](https://t.me/BotFather) on Telegram, create your own bot using the `/newbot` command, and copy the provided HTTP API Token.

### 3. Deploy on Render ☁️
1. Log in to [Render.com](https://render.com) with your GitHub account.
2. Follow **New > Web Service** and select your forked repository.
3. Fill in the settings as follows:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python main.py`
4. Go to the **Environment Variables** section at the bottom of the page and add your secret keys:
   * `TELEGRAM_TOKEN` = (The token you got from BotFather)
   * `GEMINI_API_KEY` = (The key you got from Google AI Studio)
5. Start your bot by clicking the **Create Web Service** button!

> **💻 Local Installation:** If you want to test the bot on your own computer; you can clone the repo and install the libraries with the `pip install -r requirements.txt` command, create a `.env` file in the root directory, paste your tokens/keys inside, and run it with the `python main.py` command.

---

## 📞 Contact & Support

If you notice a bug or have a feature request regarding the project, please don't hesitate to open an **Issue** on GitHub.

<div align="center">

---

## ⚠️ Legal Disclaimer

This bot is designed entirely for entertainment and motivation purposes using artificial intelligence language models. 
* **Accuracy:** The generated content relies on random AI algorithms and has no function/certainty of reading or predicting the future.
* **Not Advisory:** The answers provided by the bot do not substitute for psychological, financial, medical, or legal advice. Please consult experts for your serious decisions.

---

<i>Made with ❤️ by Yusuf Sami Turan</i><br><br>
<a href="https://www.linkedin.com/in/yusufsamituran">
  <img src="https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
</a>
</div>

<br><br>

---

# 🇹🇷 Türkçe

# 🔮 Fortune Teller Bot

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-3%20Flash-orange?style=for-the-badge&logo=google)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram)
![Render](https://img.shields.io/badge/Render-Cloud%20Hosting-46E3B7?style=for-the-badge&logo=render)

**Fortune Teller Bot**, kullanıcılara Telegram üzerinden astroloji, kahve falı ve tarot tadında kişiselleştirilmiş mistik yorumlar yapan yapay zeka destekli bir sohbet botudur. 

Standart kalıp cümlelerin aksine, bu bot **Google Gemini 3 Flash** modelinin hızını ve zekasını kullanarak, kullanıcının sorduğu sorulara anında, akıcı ve tamamen bağlama uygun "falcı" personasıyla yanıtlar üretir.

## 🚀 Özellikler

* **🎭 Gerçekçi Falcı Personası:** Sadece burç yorumu yapmaz; aklınızdaki bir soruya, bir isme veya dertleşmek istediğiniz bir konuya mistik bir üslupla yaklaşır.
* **⚡ Yüksek Hız & Düşük Gecikme:** Google'ın low-latency odaklı Gemini 3 Flash modeli ve asenkron (async) Telegram altyapısı sayesinde mesajlara saniyeler içinde dönüş yapar.
* **☁️ 7/24 Kesintisiz Hizmet:** Render bulut sunucusu üzerinde barındırıldığı için yerel bilgisayarınız kapalı olsa bile sürekli çevrimiçidir.

---

## ⚙️ Nasıl Çalışır?

1. **Etkileşim:** Kullanıcı Telegram üzerinden bota direkt bir soru yazarak ulaşır.
2. **Prompt Mühendisliği:** Kullanıcının mesajı, arka planda bota "gizemi, samimiyeti ve astrolojik öngörüleri harmanlayan bir bilge" kimliği yükleyen özel bir sistem komutuyla birleştirilir.
3. **Yapay Zeka Üretimi:** Gemini 3 Flash API, bu verileri işleyerek sanki bir fincan kahveye veya tarot kartlarına bakıyormuşçasına etkileyici bir metin oluşturur.
4. **Hızlı Teslimat:** Üretilen yanıt anında kullanıcının Telegram sohbetine düşer.

---

## 🛠️ Kurulum

Bu proje, **Render.com** gibi bulut platformlarında 7/24 çalışacak şekilde optimize edilmiştir. Kendi botunuzu kurmak için aşağıdaki adımları izleyebilirsiniz:

### 1. Projeyi Forklayın 🍴
Sayfanın sağ üst köşesindeki **Fork** butonuna tıklayarak bu projeyi kendi GitHub hesabınıza ekleyiniz.

### 2. Gerekli Anahtarları Edinin 🔑
* **Google Gemini API Key:** [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden ücretsiz anahtarınızı alınız.
* **Telegram Bot Token:** Telegram'da [@BotFather](https://t.me/BotFather) ile sohbet başlatıp `/newbot` komutuyla kendi botunuzu oluşturun ve size verilen HTTP API Token'ı kopyalayınız.

### 3. Render Üzerinde Canlıya Alın ☁️
1. [Render.com](https://render.com) adresine GitHub hesabınızla giriş yapın.
2. **New > Web Service** adımlarını izleyerek forklayıp oluşturduğunuz deponuzu seçin.
3. Ayarları şu şekilde doldurun:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python main.py`
4. Sayfanın altındaki **Environment Variables** bölümüne giderek gizli anahtarlarınızı ekleyin:
   * `TELEGRAM_TOKEN` = (BotFather'dan aldığınız token)
   * `GEMINI_API_KEY` = (Google AI Studio'dan aldığınız anahtar)
5. **Create Web Service** butonuna basarak botunuzu başlatın!

> **💻 Yerel (Local) Kurulum:** Botu kendi bilgisayarınızda denemek isterseniz; repoyu klonlayıp `pip install -r requirements.txt` komutuyla kütüphaneleri kurabilir, ana dizinde `.env` dosyası oluşturarak aldığınız tokenleri/anahtarları içine yazdıktan sonra `python main.py` komutuyla çalıştırabilirsiniz.

---

## 📞 İletişim & Destek

Proje ile ilgili bir hata fark ederseniz veya özellik isteğiniz varsa lütfen GitHub üzerinden bir **Issue** açmaktan çekinmeyin.

<div align="center">

---

## ⚠️ Yasal Uyarı

Bu bot, tamamen eğlence ve motivasyon sağlamak amacıyla yapay zeka dil modelleri kullanılarak tasarlanmıştır. 
* **Kesinlik:** Üretilen içerikler rastgele yapay zeka algoritmalarına dayanır ve geleceği okuma, tahmin etme gibi bir işlevi/kesinliği yoktur.
* **Tavsiye Niteliği Taşımaz:** Bot tarafından verilen cevaplar; psikolojik, finansal, medikal veya hukuki bir tavsiye yerine geçmez. Ciddi kararlarınızda lütfen uzmanlara danışınız.

---

<i>Made with ❤️ by Yusuf Sami Turan</i><br><br>
<a href="https://www.linkedin.com/in/yusufsamituran">
  <img src="https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
</a>
</div>
