"""Tarot destesi (22 Büyük Arkana), 12 burç ve evet/hayır mistik sarkaç verileri."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date
from typing import Optional

_TR_FOLD = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
        "Ö": "o",
        "ö": "o",
        "Ş": "s",
        "ş": "s",
        "Ü": "u",
        "ü": "u",
    }
)


def fold_tr(text: str) -> str:
    """Türkçe karakterleri ASCII'ye katlayıp küçük harfe çevirir."""
    return " ".join(str(text or "").translate(_TR_FOLD).lower().split())


@dataclass(frozen=True)
class TarotCard:
    """Büyük Arkana tarot kartı tanımı."""

    number: int
    name_tr: str
    name_en: str
    emoji: str
    upright: str
    reversed: str


@dataclass(frozen=True)
class DrawnTarotCard:
    """Açılımda çekilen tekil kart."""

    card: TarotCard
    position: str
    is_reversed: bool

    @property
    def orientation_label(self) -> str:
        return "Ters" if self.is_reversed else "Düz"

    @property
    def active_meaning(self) -> str:
        return self.card.reversed if self.is_reversed else self.card.upright


@dataclass(frozen=True)
class ZodiacSign:
    """Astroloji burç bilgisi."""

    key: str
    name_tr: str
    symbol: str
    element: str
    date_range: str
    aliases: tuple[str, ...]


MAJOR_ARCANA: tuple[TarotCard, ...] = (
    TarotCard(0, "Deli", "The Fool", "🎒", "Yeni başlangıç, cesaret, spontanlık", "Düşüncesiz risk, tereddüt, hazırlıksızlık"),
    TarotCard(1, "Büyücü", "The Magician", "🪄", "Yaratım gücü, irade, harekete geçme", "Yetenekleri saklama, kararsızlık, manipülasyon"),
    TarotCard(2, "Başrahibe", "The High Priestess", "🌙", "Güçlü sezgi, içgörü, gizli bilgi", "İç sesi bastırma, yüzeysellik, sabırsızlık"),
    TarotCard(3, "İmparatoriçe", "The Empress", "🌺", "Bereket, şefkat, yaratıcılık, huzur", "Aşırı koruyuculuk, durgunluk, ihmal"),
    TarotCard(4, "İmparator", "The Emperor", "👑", "Düzen, otorite, istikrar, net sınırlar", "Katılık, kontrol takıntısı, otorite çatışması"),
    TarotCard(5, "Aziz", "The Hierophant", "🕯️", "Bilgelik, gelenek, rehberlik, öğrenme", "Kalıpları kırma, önyargı, kendi yolunu çizme"),
    TarotCard(6, "Aşıklar", "The Lovers", "💞", "Uyum, kalpten seçim, derin bağ", "Kararsızlık, değer çatışması, dengesizlik"),
    TarotCard(7, "Savaş Arabası", "The Chariot", "🛡️", "Kararlılık, zafer, hız ve odak", "Yön kaybı, acelecilik, dağılma"),
    TarotCard(8, "Güç", "Strength", "🦁", "İçsel cesaret, şefkatli direnç, sabır", "Özgüven dalgalanması, yorgunluk, öfke"),
    TarotCard(9, "Ermiş", "The Hermit", "🏮", "İçe dönüş, bilge arayış, dinginlik", "İzolasyon, aşırı kapanma, rehberliği reddetme"),
    TarotCard(10, "Kader Çarkı", "Wheel of Fortune", "🎡", "Dönüm noktası, şanslı döngü, değişim", "Beklenmedik aksaklık, direnç, geçici durağanlık"),
    TarotCard(11, "Adalet", "Justice", "⚖️", "Denge, dürüstlük, hakkaniyetli sonuç", "Önyargı, dengesizlik, sorumluluktan kaçış"),
    TarotCard(12, "Asılan Adam", "The Hanged Man", "🫧", "Farklı bakış açısı, sabırlı bekleyiş", "Gereksiz erteleme, takılı kalma"),
    TarotCard(13, "Ölüm", "Death", "🦋", "Köklü dönüşüm, eskiyi bırakıp yenilenme", "Değişime direnç, geçmişe tutunma"),
    TarotCard(14, "Denge", "Temperance", "🏺", "Uyum, ölçülülük, şifa ve sabır", "Aşırılık, içsel huzursuzluk, acele"),
    TarotCard(15, "Şeytan", "The Devil", "⛓️", "Güçlü tutku, gölgeyle yüzleşme, sınav", "Bağlardan özgürleşme, uyanış, zinciri kırma"),
    TarotCard(16, "Yıkılan Kule", "The Tower", "⚡", "Ani aydınlanma, sahte yapıların yıkımı", "Kaçınılmaz değişimi yumuşatma, uyarı"),
    TarotCard(17, "Yıldız", "The Star", "⭐", "Umut, şifa, ilham ve berrak gelecek", "Geçici umutsuzluk, inanç tazeleme ihtiyacı"),
    TarotCard(18, "Ay", "The Moon", "🌕", "Bilinçaltı rüyalar, derin sezgi, gizem", "Sislerin dağılması, gerçeğin netleşmesi"),
    TarotCard(19, "Güneş", "The Sun", "☀️", "Sevinç, başarı, canlılık, netlik", "Geçici bulutlar, gecikmiş ama gelecek başarı"),
    TarotCard(20, "Mahkeme", "Judgement", "🎺", "Uyanış, önemli karar, çağrıya yanıt", "Kendini fazla eleştirme, kararsızlık"),
    TarotCard(21, "Dünya", "The World", "🌍", "Tamamlanma, bütünlük, büyük döngü zaferi", "Eksik kalan son adım, kapanış öncesi sabır"),
)

ZODIAC_SIGNS: tuple[ZodiacSign, ...] = (
    ZodiacSign("koc", "Koç", "♈", "Ateş", "21 Mart - 19 Nisan", ("koc", "aries")),
    ZodiacSign("boga", "Boğa", "♉", "Toprak", "20 Nisan - 20 Mayıs", ("boga", "taurus")),
    ZodiacSign("ikizler", "İkizler", "♊", "Hava", "21 Mayıs - 20 Haziran", ("ikizler", "gemini")),
    ZodiacSign("yengec", "Yengeç", "♋", "Su", "21 Haziran - 22 Temmuz", ("yengec", "cancer")),
    ZodiacSign("aslan", "Aslan", "♌", "Ateş", "23 Temmuz - 22 Ağustos", ("aslan", "leo")),
    ZodiacSign("basak", "Başak", "♍", "Toprak", "23 Ağustos - 22 Eylül", ("basak", "virgo")),
    ZodiacSign("terazi", "Terazi", "♎", "Hava", "23 Eylül - 22 Ekim", ("terazi", "libra")),
    ZodiacSign("akrep", "Akrep", "♏", "Su", "23 Ekim - 21 Kasım", ("akrep", "scorpio")),
    ZodiacSign("yay", "Yay", "♐", "Ateş", "22 Kasım - 21 Aralık", ("yay", "sagittarius")),
    ZodiacSign("oglak", "Oğlak", "♑", "Toprak", "22 Aralık - 19 Ocak", ("oglak", "capricorn")),
    ZodiacSign("kova", "Kova", "♒", "Hava", "20 Ocak - 18 Şubat", ("kova", "aquarius")),
    ZodiacSign("balik", "Balık", "♓", "Su", "19 Şubat - 20 Mart", ("balik", "pisces")),
)

_DEFAULT_POSITIONS = ("Geçmiş", "Şimdi", "Gelecek")


def draw_tarot_spread(
    count: int = 3,
    *,
    positions: Optional[tuple[str, ...]] = None,
    rng: Optional[random.Random] = None,
) -> list[DrawnTarotCard]:
    """Büyük Arkana destesi üzerinden tekrarsız tarot açılımı çeker."""
    picker = rng or random.Random()
    actual_count = max(1, min(count, len(MAJOR_ARCANA)))
    pos_labels = positions or _DEFAULT_POSITIONS
    chosen = picker.sample(MAJOR_ARCANA, k=actual_count)
    drawn: list[DrawnTarotCard] = []
    for idx, card in enumerate(chosen):
        pos = pos_labels[idx] if idx < len(pos_labels) else f"{idx + 1}. Kart"
        is_rev = picker.random() < 0.30
        drawn.append(DrawnTarotCard(card=card, position=pos, is_reversed=is_rev))
    return drawn


def draw_daily_card(user_id: int | str, target_date: date) -> DrawnTarotCard:
    """Kullanıcı ve tarih için gün boyunca değişmeyen deterministik Günün Kartı çeker."""
    seed_hex = hashlib.sha256(f"{user_id}:{target_date.isoformat()}".encode("utf-8")).hexdigest()
    seed_int = int(seed_hex[:12], 16)
    card = MAJOR_ARCANA[seed_int % len(MAJOR_ARCANA)]
    is_rev = (int(seed_hex[12:14], 16) % 4) == 0
    return DrawnTarotCard(card=card, position="Günün Enerjisi", is_reversed=is_rev)


def resolve_zodiac_sign(raw_text: str) -> Optional[ZodiacSign]:
    """Kullanıcı metninden veya callback anahtarından burç nesnesini bulur."""
    folded = fold_tr(raw_text)
    if not folded:
        return None
    tokens = folded.replace("burcu", "").replace("burc", "").strip()
    for sign in ZODIAC_SIGNS:
        if tokens == sign.key or any(alias == tokens for alias in sign.aliases):
            return sign
    for sign in ZODIAC_SIGNS:
        if any(alias in folded for alias in sign.aliases):
            return sign
    return None


@dataclass(frozen=True)
class OracleAnswer:
    """Evet / Hayır sarkaç cevabı."""

    verdict: str
    emoji: str
    tone_note: str


def draw_yes_no_oracle(rng: Optional[random.Random] = None) -> OracleAnswer:
    """Mistik sarkaç ile Evet / Hayır / Sabret sonucu üretir."""
    picker = rng or random.Random()
    pool = (
        OracleAnswer("EVET", "✅", "Enerji akışı açık ve destekleyici görünüyor."),
        OracleAnswer("HAYIR", "❌", "Yıldızlar şu an durup farklı bir açıdan bakmanı öneriyor."),
        OracleAnswer("BELİRSİZ / ZAMANI VAR", "🌓", "Koşullar henüz olgunlaşmamış; biraz sabırla tablo netleşecek."),
    )
    return picker.choice(pool)
