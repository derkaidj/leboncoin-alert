import requests
import time
import json
import os
from datetime import datetime

# ============================================================
#  CONFIGURATION
# ============================================================
TELEGRAM_TOKEN   = "8760062971:AAHgRGZRLSMARkQd5qmZLS9XTha3bZGURbY"
TELEGRAM_CHAT_ID = "8035951279"
INTERVAL         = 60
SEEN_FILE        = "seen_ids.json"

# ============================================================
#  CATEGORIES — Brocante / Cuisine ancienne / Déco vintage
#  Stratégie : acheter particulier LBC sous-évalué → revente
#  Etsy international x4/x5
#  Format : (label, mots-clés, prix_max_achat, prix_etsy_min)
# ============================================================
SEARCHES = [

    # ── CUIVRE & USTENSILES ANCIENS ──────────────────────────
    ("🟤 Casserole cuivre ancienne",    "casserole cuivre ancienne",       25,  100),
    ("🟤 Poele cuivre vintage",         "poele cuivre",                    20,   90),
    ("🟤 Bassine confiture cuivre",     "bassine cuivre confiture",        20,   90),
    ("🟤 Bouilloire cuivre ancienne",   "bouilloire cuivre",               20,   70),
    ("🟤 Braconnier bouilloire cuivre", "braconnier cuivre",               15,   70),
    ("🟤 Moule cuivre ancien",          "moule cuivre ancien",             15,   80),
    ("🟤 Daubiere cuivre ancienne",     "daubiere cuivre",                 20,  100),
    ("🟤 Chaudron cuivre ancien",       "chaudron cuivre",                 25,  150),
    ("🟤 Lechefrite cuivre ancienne",   "lechefrite cuivre",               20,  100),
    ("🟤 Couvercle cuivre ancien",      "couvercle cuivre ancien",         10,   60),
    ("🟤 Verseuse cuivre ancienne",     "verseuse cuivre ancienne",        15,   70),
    ("🟤 Lot casseroles cuivre",        "lot casseroles cuivre",           50,  300),

    # ── LAITON & BRONZE ──────────────────────────────────────
    ("🟡 Mortier laiton ancien",        "mortier laiton bronze ancien",    20,   90),
    ("🟡 Robinet tonneau laiton",       "robinet tonneau laiton",          20,  100),
    ("🟡 Encrier laiton ancien",        "encrier laiton ancien",           15,   80),
    ("🟡 Chandelier bronze ancien",     "chandelier bronze ancien",        15,   80),
    ("🟡 Applique bronze ancienne",     "applique murale bronze",          20,  100),
    ("🟡 Lustre bronze ancien",         "lustre bronze ancien",            30,  200),
    ("🟡 Bougeoir bronze laiton",       "bougeoir bronze laiton",          10,   60),
    ("🟡 Embrasse rideau laiton",       "embrasse rideau laiton bronze",   15,   80),
    ("🟡 Ustensiles cuisine laiton",    "ustensiles cuisine laiton",       15,   90),

    # ── FAIENCE & PORCELAINE ─────────────────────────────────
    ("🫙 Pichet emaille ancien",        "pichet emaille ancien",           10,   60),
    ("🫙 Seau emaille vintage",         "seau emaille vintage",            10,   50),
    ("🫙 Cafetiere emaillee ancienne",  "cafetiere emaillee ancienne",     10,   65),
    ("🫙 Assiettes Sarreguemines",      "assiettes sarreguemines",         15,   70),
    ("🫙 Assiettes Digoin ancienne",    "assiettes digoin",                12,   65),
    ("🫙 Soupiere ancienne porcelaine", "soupiere ancienne porcelaine",    15,   80),
    ("🫙 Bol faience ancienne",         "bol faience ancienne",            10,   55),
    ("🫙 Pot moutarde gres ancien",     "pot moutarde gres ancien",         8,   45),
    ("🫙 Service vaisselle ancien",     "service vaisselle ancien",        20,  100),
    ("🫙 Pot rillettes gres ancien",    "pot rillettes gres",               8,   45),
    ("🫙 Cruche ancienne faience",      "cruche ancienne faience",         10,   60),
    ("🫙 Terrrine gres ancienne",       "terrine gres ancienne",           10,   55),
    ("🫙 Bocaux anciens verre",         "bocaux anciens verre",            10,   50),
    ("🫙 Pot apothicaire porcelaine",   "pot apothicaire porcelaine",      10,   60),
    ("🫙 Assiettes huitres anciennes",  "assiettes huitres anciennes",     15,   80),
    ("🫙 Pots escargots gres",          "pots escargots gres",             10,   50),

    # ── ABAT-JOURS & LUMINAIRES ──────────────────────────────
    ("💡 Abat-jour verre ancien",       "abat-jour verre ancien",          15,   80),
    ("💡 Abat-jour opaline vintage",    "abat-jour opaline",               15,   90),

    # ── DÉCO VINTAGE DIVERS ──────────────────────────────────
    ("🏺 Balance ancienne fonte",       "balance ancienne fonte",          15,   80),
    ("🏺 Benitier ancien",              "benitier ancien",                  8,   45),
    ("🏺 Statue Vierge ancienne",       "statue vierge ancienne",          10,   60),
    ("🏺 Moulin cafe vintage",          "moulin cafe vintage",             10,   60),
    ("🏺 Tapisserie ancienne",          "tapisserie ancienne",             15,   80),
    ("🏺 Vase ceramique ancien",        "vase ceramique ancien",           10,   55),
    ("🏺 Couverts argent ancien",       "couverts argent ancien",          15,   80),
]

EXCLUDE_KEYWORDS = [
    "cherche", "recherche", "wanted", "reproduction",
    "copie", "faux", "neuf jamais", "drop", "inspired",
    "lot de 50", "lot de 100", "professionnel", "boutique",
    "depot vente", "antiquaire", "brocanteur", "marchand"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.leboncoin.fr/",
}


# ============================================================
#  SCORE REVENTE (1–10)
#  Basé sur le ratio prix achat vs estimation Etsy
# ============================================================
def compute_score(price_val, etsy_min):
    if not price_val or price_val == 0:
        return 5, "~200€"
    ratio = etsy_min / price_val
    etsy_est = int(price_val * min(ratio, 5))
    if ratio >= 5:
        score = 10
    elif ratio >= 4:
        score = 9
    elif ratio >= 3.5:
        score = 8
    elif ratio >= 3:
        score = 7
    elif ratio >= 2.5:
        score = 6
    elif ratio >= 2:
        score = 5
    else:
        score = 3
    return score, f"~{etsy_est}€"


def score_stars(score):
    filled = "⭐" * (score // 2)
    half   = "✨" if score % 2 else ""
    return filled + half


# ============================================================
#  UTILS
# ============================================================
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-3000:], f)


def is_excluded(text):
    text_lower = text.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


# ============================================================
#  TELEGRAM — texte + photo séparément
# ============================================================
def send_telegram_text(message):
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
            print(f"[Telegram TEXT ERROR] {r.text}")
    except Exception as e:
        print(f"[Telegram TEXT EXCEPTION] {e}")


def send_telegram_photo(photo_url, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            # Photo échouée → on envoie en texte simple
            send_telegram_text(caption)
    except Exception as e:
        print(f"[Telegram PHOTO EXCEPTION] {e}")
        send_telegram_text(caption)


# ============================================================
#  LEBONCOIN API
# ============================================================
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


# ============================================================
#  FORMAT ALERTE
# ============================================================
def format_and_send(label, ad, etsy_min):
    title    = ad.get("subject", "Sans titre")
    price    = ad.get("price", [None])
    price_val = price[0] if price else None
    location = ad.get("location", {})
    city     = location.get("city", "")
    dept     = location.get("zipcode", "")[:2]
    ad_id    = str(ad.get("list_id", ""))
    ad_url   = f"https://www.leboncoin.fr/ad/{ad_id}"

    # Photo
    images   = ad.get("images", {})
    thumb    = images.get("thumb_url") or images.get("small_url") or ""
    urls     = images.get("urls", [])
    photo_url = urls[0] if urls else thumb

    # Prix
    prix_str = f"{price_val}€" if price_val else "Prix non indiqué"

    # Score
    score, etsy_est = compute_score(price_val, etsy_min)
    stars = score_stars(score)

    caption = (
        f"🚨 <b>BONNE AFFAIRE BROCANTE !</b>\n"
        f"{label}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>{title}</b>\n"
        f"💰 {prix_str}  |  📍 {city} ({dept})\n"
        f"🔗 <a href='{ad_url}'>Voir l'annonce</a>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ Score revente : {score}/10  {stars}\n"
        f"📦 Estimation Etsy : {etsy_est}"
    )

    if photo_url:
        send_telegram_photo(photo_url, caption)
    else:
        send_telegram_text(caption)


# ============================================================
#  BOUCLE PRINCIPALE
# ============================================================
def check_search(label, keywords, max_price, etsy_min, seen):
    ads = search_leboncoin(keywords, max_price)
    new_count = 0
    for ad in ads:
        ad_id = str(ad.get("list_id", ""))
        if not ad_id or ad_id in seen:
            continue
        title = ad.get("subject", "")
        seen.add(ad_id)
        if is_excluded(title):
            continue
        format_and_send(label, ad, etsy_min)
        new_count += 1
        time.sleep(1)
    return new_count


def main():
    print("Kadexa Brocante Alert — Démarrage")
    print(f"Vérification toutes les {INTERVAL} secondes")
    print(f"{len(SEARCHES)} catégories surveillées")

    send_telegram_text(
        "🟢 <b>Kadexa Brocante Alert — Démarrage !</b>\n"
        f"📦 {len(SEARCHES)} catégories surveillées\n"
        "🏺 Cuivre · Faïence · Laiton · Déco vintage\n"
        "👤 Particuliers uniquement\n"
        "⭐ Score revente + estimation Etsy à chaque alerte"
    )

    seen = load_seen()

    # Initialisation — on mémorise les annonces déjà en ligne
    print("Initialisation (mémorisation annonces existantes)...")
    for label, keywords, max_price, etsy_min in SEARCHES:
        ads = search_leboncoin(keywords, max_price)
        for ad in ads:
            ad_id = str(ad.get("list_id", ""))
            if ad_id:
                seen.add(ad_id)
    save_seen(seen)
    print("✅ Surveillance active — en attente de nouvelles annonces.")

    while True:
        time.sleep(INTERVAL)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Scan...")

        total_new = 0
        for label, keywords, max_price, etsy_min in SEARCHES:
            n = check_search(label, keywords, max_price, etsy_min, seen)
            total_new += n

        save_seen(seen)
        if total_new:
            print(f"  -> {total_new} bonne(s) affaire(s) trouvée(s) !")
        else:
            print(f"  -> Rien de nouveau")


if __name__ == "__main__":
    main()
