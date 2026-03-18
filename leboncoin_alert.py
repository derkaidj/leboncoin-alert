import requests
import time
import json
import os
from datetime import datetime
 
# ============================================================
#  CONFIGURATION
# ============================================================
TELEGRAM_TOKEN = "8760062971:AAHgRGZRLSMARkQd5qmZLS9XTha3bZGURbY"
TELEGRAM_CHAT_ID = "8035951279"
INTERVAL = 60
SEEN_FILE = "seen_ids.json"
 
# ============================================================
#  RECHERCHES ET PRIX MAXIMUM PAR CATEGORIE
# ============================================================
SEARCHES = [
    ("💍 Bijou argent ancien",     "bijou argent ancien",        15),
    ("⌚ Montre ancienne",          "montre ancienne gousset",    20),
    ("🕯️ Bougeoir laiton",         "bougeoir laiton ancien",     10),
    ("🎖️ Médaille ancienne",       "medaille ancienne",           8),
    ("🔍 Broche camée vintage",    "broche camee vintage",       10),
    ("👜 Sac Louis Vuitton",       "sac louis vuitton",          50),
    ("👗 Veste Moncler",           "veste moncler",              60),
    ("👟 Nike Air Jordan",         "nike air jordan",            30),
    ("🥈 Argenterie ancienne",     "argenterie argent massif",   20),
    ("🪙 Pièce monnaie ancienne",  "piece monnaie ancienne",      5),
]
 
EXCLUDE_KEYWORDS = [
    "cherche", "recherche", "wanted", "reproduction",
    "copie", "faux", "plaque", "lot de 50", "lot de 100"
]
 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.leboncoin.fr/",
}
 
 
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()
 
 
def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-2000:], f)
 
 
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
 
 
def is_excluded(text):
    text_lower = text.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False
 
 
def search_leboncoin(keywords, max_price):
    url = "https://api.leboncoin.fr/api/adfinder/v1/search"
    payload = {
        "filters": {
            "keywords": {"text": keywords, "type": "all"},
            "ranges": {"price": {"max": max_price}}
        },
        "sort_by": "time",
        "sort_order": "desc",
        "limit": 20,
        "offset": 0
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("ads", [])
        else:
            print(f"[API ERROR] {r.status_code}")
            return []
    except Exception as e:
        print(f"[SEARCH EXCEPTION] {e}")
        return []
 
 
def format_alert(label, ad, max_price):
    title = ad.get("subject", "Sans titre")
    price = ad.get("price", [None])
    price_val = price[0] if price else None
    location = ad.get("location", {})
    city = location.get("city", "")
    dept = location.get("zipcode", "")[:2]
    ad_id = str(ad.get("list_id", ""))
    url = f"https://www.leboncoin.fr/ad/{ad_id}"
 
    if price_val:
        revente = price_val * 4
        marge = revente - price_val
        prix_str = f"{price_val}€"
        marge_str = f"~{marge:.0f}€ de marge potentielle"
    else:
        prix_str = "Prix non indiqué"
        marge_str = ""
 
    message = (
        f"🚨 <b>BONNE AFFAIRE</b>\n"
        f"{label}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>{title}</b>\n"
        f"💰 {prix_str}\n"
        f"📍 {city} ({dept})\n"
    )
    if marge_str:
        message += f"📈 {marge_str}\n"
    message += f"🔗 <a href='{url}'>Voir l'annonce</a>"
    return message, ad_id
 
 
def check_search(label, keywords, max_price, seen):
    new_alerts = []
    ads = search_leboncoin(keywords, max_price)
    for ad in ads:
        ad_id = str(ad.get("list_id", ""))
        if not ad_id or ad_id in seen:
            continue
        title = ad.get("subject", "")
        if is_excluded(title):
            seen.add(ad_id)
            continue
        seen.add(ad_id)
        msg, _ = format_alert(label, ad, max_price)
        new_alerts.append(msg)
    return new_alerts
 
 
def main():
    print("Kadexa Alert - Demarrage")
    print(f"Verification toutes les {INTERVAL} secondes")
    print(f"{len(SEARCHES)} recherches actives")
 
    send_telegram(
        "🟢 <b>Kadexa Alert démarré !</b>\n"
        f"Je surveille {len(SEARCHES)} catégories.\n"
        "Alertes uniquement si prix rentable."
    )
 
    seen = load_seen()
 
    print("Premier scan (initialisation)...")
    for label, keywords, max_price in SEARCHES:
        ads = search_leboncoin(keywords, max_price)
        for ad in ads:
            ad_id = str(ad.get("list_id", ""))
            if ad_id:
                seen.add(ad_id)
    save_seen(seen)
    print("Initialisation terminee. Surveillance active.")
 
    while True:
        time.sleep(INTERVAL)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Verification...")
 
        total_new = 0
        for label, keywords, max_price in SEARCHES:
            alerts = check_search(label, keywords, max_price, seen)
            for msg in alerts:
                send_telegram(msg)
                total_new += 1
                time.sleep(1)
 
        save_seen(seen)
        if total_new:
            print(f"  -> {total_new} bonne(s) affaire(s) !")
        else:
            print(f"  -> Rien sous les seuils")
 
 
if __name__ == "__main__":
    main()
