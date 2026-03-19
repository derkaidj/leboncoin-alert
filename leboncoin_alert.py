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
#  CATEGORIES BROCANTE — Particuliers uniquement, < 2kg
#  Prix achat max / Revente estimee x4 sur Etsy/Vinted
# ============================================================
SEARCHES = [
    # CUIVRE & LAITON
    ("🟤 Casserole cuivre ancienne",     "casserole cuivre ancienne",     25),
    ("🟤 Poele cuivre vintage",          "poele cuivre",                  20),
    ("🟤 Bassine cuivre",                "bassine cuivre",                20),
    ("🟤 Bouilloire cuivre ancienne",    "bouilloire cuivre",             20),
    ("🟤 Mortier cuivre laiton",         "mortier cuivre laiton",         15),
    ("🟤 Plateau laiton ancien",         "plateau laiton ancien",         15),
    ("🟤 Vase laiton bronze",            "vase laiton bronze",            15),
    ("🟤 Chandelier laiton cuivre",      "chandelier laiton cuivre",      15),
    # DECO & OBJETS ANCIENS
    ("🏺 Statuette bronze figurine",     "statuette bronze figurine",     20),
    ("🏺 Vase ancien cristal",           "vase ancien cristal",           15),
    ("🏺 Bougeoir chandelier argent",    "bougeoir chandelier argent",    15),
    ("🏺 Miroir ancien dore",            "miroir ancien dore",            20),
    ("🏺 Cadre dore ancien",             "cadre dore ancien",             10),
    ("🏺 Boite ancienne coffret bois",   "boite ancienne coffret",        10),
    ("🏺 Plaque emaillee publicitaire",  "plaque emaillee ancienne",      15),
    # CERAMIQUE
    ("🫙 Ceramique Vallauris",           "ceramique vallauris",           15),
    ("🫙 Ceramique Accolay",             "ceramique accolay",             15),
    ("🫙 Faience ancienne porcelaine",   "faience ancienne porcelaine",   10),
    # VAISSELLE VINTAGE
    ("🍽️ Service Arcopal fleuri",        "arcopal fleuri",                10),
    ("🍽️ Plat Pyrex colore vintage",     "pyrex colore vintage",          10),
    ("🍽️ Assiettes anciennes lot",       "assiettes anciennes lot",       10),
    ("🍽️ Bols bretons faience",          "bols bretons faience",          10),
    ("🍽️ Couverts argent massif",        "couverts argent massif",        20),
    ("🍽️ Cafetiere emaillee ancienne",   "cafetiere emaillee ancienne",   10),
    # MODE VINTAGE
    ("👖 Jean Levi's 501 vintage",       "levi's 501 vintage",            20),
    ("👗 Veste vintage marque",          "veste vintage",                 15),
    ("👗 Blouson cuir vintage",          "blouson cuir vintage",          25),
    ("👗 Manteau vintage femme",         "manteau vintage",               20),
    ("👗 Sac cuir vintage",              "sac cuir vintage",              20),
    ("👗 Foulard soie vintage",          "foulard soie vintage",          10),
    ("👗 Lunettes vintage",              "lunettes vintage",              10),
    # BIJOUX & MONTRES
    ("💍 Montre vintage mecanique",      "montre vintage mecanique",      25),
    ("💍 Bracelet argent ancien",        "bracelet argent ancien",        15),
    ("💍 Broche ancienne bijou",         "broche ancienne bijou",         10),
    ("💍 Bague ancienne or argent",      "bague ancienne or argent",      20),
    # COLLECTIBLES LEGERS
    ("📷 Appareil photo argentique",     "appareil photo argentique",     20),
    ("✒️ Stylo plume ancien",            "stylo plume ancien",            10),
    ("🔥 Briquet Zippo vintage",         "briquet zippo vintage",         10),
    ("🖼️ Affiche publicitaire ancienne", "affiche publicitaire ancienne", 10),
    ("📚 Livre ancien reliure cuir",     "livre ancien reliure",          10),
    # PETIT MOBILIER
    ("🪑 Tabouret bois ancien",          "tabouret bois ancien",          15),
    ("🪑 Chaise bistrot vintage",        "chaise bistrot vintage",        20),
]

EXCLUDE_KEYWORDS = [
    "cherche", "recherche", "wanted", "reproduction",
    "copie", "faux", "neuf jamais", "drop", "inspired",
    "lot de 50", "lot de 100", "professionnel", "boutique",
    "depot vente", "antiquaire", "brocanteur"
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
        json.dump(list(seen)[-3000:], f)


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
            "ranges": {"price": {"max": max_price}},
            "enums": {"owner_type": ["private"]}
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
        marge = (price_val * 4) - price_val
        prix_str = f"{price_val}€"
        marge_str = f"~{marge:.0f}€ de marge potentielle"
    else:
        prix_str = "Prix non indique"
        marge_str = ""

    message = (
        f"🚨 <b>BONNE AFFAIRE !</b>\n"
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
    print(f"{len(SEARCHES)} categories surveillees")

    send_telegram(
        "🟢 <b>Kadexa Alert v3 — Brocante !</b>\n"
        f"Surveillance de {len(SEARCHES)} categories.\n"
        "Cuivre · Deco · Vaisselle · Mode · Bijoux.\n"
        "✅ Particuliers uniquement.\n"
        "Alertes uniquement si prix rentable (marge x4)."
    )

    seen = load_seen()

    print("Initialisation...")
    for label, keywords, max_price in SEARCHES:
        ads = search_leboncoin(keywords, max_price)
        for ad in ads:
            ad_id = str(ad.get("list_id", ""))
            if ad_id:
                seen.add(ad_id)
    save_seen(seen)
    print("Surveillance active.")

    while True:
        time.sleep(INTERVAL)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Scan...")

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
            print(f"  -> Rien")


if __name__ == "__main__":
    main()
