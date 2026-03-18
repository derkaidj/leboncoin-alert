import feedparser
import requests
import time
import json
import os
from datetime import datetime

# ============================================================
#  CONFIGURATION — MODIFIE CES 2 LIGNES
# ============================================================
TELEGRAM_TOKEN = "8760062971:AAHgRGZRLSMARkQd5qmZLS9XTha3bZGURbY"       # ex: 7234567890:AAFxxx
TELEGRAM_CHAT_ID = "8035951279"   # ex: 123456789
# ============================================================

# Intervalle de vérification en secondes (60 = toutes les minutes)
INTERVAL = 60

# Fichier pour mémoriser les annonces déjà vues
SEEN_FILE = "seen_ids.json"

# ============================================================
#  TES RECHERCHES LEBONCOIN
#  Format : ("Nom affiché", "URL RSS Leboncoin")
#
#  Comment obtenir une URL RSS :
#  1. Va sur leboncoin.fr
#  2. Fais ta recherche
#  3. Ajoute &rss=1 à la fin de l'URL
# ============================================================
SEARCHES = [
    (
        "💍 Bijoux anciens",
        "https://www.leboncoin.fr/recherche?category=15&keywords=bijou+ancien&rss=1"
    ),
    (
        "🕯️ Laiton / Cuivre",
        "https://www.leboncoin.fr/recherche?category=17&keywords=laiton+ancien&rss=1"
    ),
    (
        "⌚ Montre ancienne",
        "https://www.leboncoin.fr/recherche?category=15&keywords=montre+ancienne+vintage&rss=1"
    ),
    (
        "🥈 Argenterie",
        "https://www.leboncoin.fr/recherche?category=17&keywords=argent+ancien+argente&rss=1"
    ),
    (
        "🎖️ Médailles / Monnaies",
        "https://www.leboncoin.fr/recherche?category=17&keywords=medaille+ancienne+monnaie&rss=1"
    ),
    (
        "🪆 Figurines / Miniatures",
        "https://www.leboncoin.fr/recherche?category=17&keywords=figurine+miniature+ancienne&rss=1"
    ),
    (
        "🔍 Broches / Camées",
        "https://www.leboncoin.fr/recherche?category=15&keywords=broche+camee+vintage&rss=1"
    ),
]

# Mots-clés à EXCLURE (pour éviter les fausses alertes)
EXCLUDE_KEYWORDS = [
    "reproduction", "copie", "moderne", "neuf", "plastique",
    "lot de 10", "lot de 20", "grossiste"
]

# Prix maximum (None = pas de limite)
MAX_PRICE = 150  # euros


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"[Telegram ERROR] {r.text}")
    except Exception as e:
        print(f"[Telegram EXCEPTION] {e}")


def extract_price(entry):
    """Tente d'extraire le prix depuis le titre ou la description."""
    text = entry.get("title", "") + " " + entry.get("summary", "")
    import re
    matches = re.findall(r'(\d+[\s,.]?\d*)\s*€', text.replace("\u202f", "").replace("\xa0", ""))
    if matches:
        try:
            return float(matches[0].replace(",", ".").replace(" ", ""))
        except:
            return None
    return None


def is_excluded(entry):
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            return True
    return False


def check_feed(label, url, seen):
    new_alerts = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            uid = entry.get("id") or entry.get("link")
            if uid in seen:
                continue

            seen.add(uid)

            if is_excluded(entry):
                continue

            price = extract_price(entry)
            if MAX_PRICE and price and price > MAX_PRICE:
                continue

            title = entry.get("title", "Sans titre")
            link = entry.get("link", "")
            pub = entry.get("published", "")

            price_str = f"{price:.0f}€" if price else "Prix non indiqué"

            message = (
                f"{label}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"<b>{title}</b>\n"
                f"💰 {price_str}\n"
                f"🕐 {pub}\n"
                f"🔗 <a href='{link}'>Voir l'annonce</a>"
            )
            new_alerts.append(message)

    except Exception as e:
        print(f"[FEED ERROR] {label}: {e}")

    return new_alerts


def main():
    print("🚀 Kadexa Alert — Démarrage")
    print(f"⏱️  Vérification toutes les {INTERVAL} secondes")
    print(f"🔍 {len(SEARCHES)} recherches actives\n")

    # Envoi d'un message de démarrage
    send_telegram(
        "🟢 <b>Kadexa Alert démarré !</b>\n"
        f"Je surveille {len(SEARCHES)} catégories sur Leboncoin.\n"
        f"Tu seras alerté en moins de {INTERVAL} secondes."
    )

    seen = load_seen()

    # Premier passage : on mémorise sans alerter (évite le flood au démarrage)
    print("📡 Premier scan (initialisation)...")
    for label, url in SEARCHES:
        check_feed(label, url, seen)
    save_seen(seen)
    print("✅ Initialisation terminée. Surveillance active.\n")

    # Boucle principale
    while True:
        time.sleep(INTERVAL)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Vérification en cours...")

        total_new = 0
        for label, url in SEARCHES:
            alerts = check_feed(label, url, seen)
            for msg in alerts:
                send_telegram(msg)
                total_new += 1
                time.sleep(1)  # évite le spam Telegram

        save_seen(seen)
        if total_new:
            print(f"  → {total_new} nouvelle(s) annonce(s) envoyée(s)")
        else:
            print(f"  → Rien de nouveau")


if __name__ == "__main__":
    main()
