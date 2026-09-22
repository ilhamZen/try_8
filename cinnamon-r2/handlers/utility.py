from handlers import register, register_feature_specs
from handlers.auth import require_login
from handlers.games import EIGHT_BALL
from handlers.media import _safe_http_get
import config
from datetime import datetime
import base64, json, os, random, re, time, urllib.parse, httpx
from core.utils import FFMPEG_AVAILABLE, GTTS_AVAILABLE, PILLOW_AVAILABLE, PSUTIL_AVAILABLE, QR_AVAILABLE, YTDLP_AVAILABLE, _strip_device, box_bottom, box_title, gTTS, health, hline, psutil, qrcode, safe_jid_str, short_name, validate_input, run_r2_utility_feature, ensure_dir
from core.identity import _find_session_db, _session_lid_map, session_identity
from core.economy import deduct_tokens, get_tokens, achievement_manager
from core.send import safe_reply, safe_send_audio, safe_send_image, safe_send_text
from core.storage import user_store
@register('/translate')
@register('/tr')
def handle_translate(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split(None, 1)
    if len(parts) < 2:
        safe_reply(client, "`/translate <lang> <text>`", message, cj)
        return
    lang, text = parts[0].lower()[:10], validate_input(parts[1], 500)
    ok, rem = deduct_tokens(sender, config.TOKEN_TRANSLATE, source="translate")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
        return
    try:
        r = httpx.get("https://translate.googleapis.com/translate_a/single",
                      params={"client": "gtx", "sl": "auto", "tl": lang, "dt": "t", "q": text},
                      timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        res = r.json()
        tr = "".join(s[0] for s in res[0] if s[0])
        safe_reply(client, f"{config.SYM_NOTE} _{tr[:1000]}_", message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/cuaca')
def handle_cuaca(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    city = validate_input(args or "Jakarta", 100) or "Jakarta"
    ok, rem = deduct_tokens(sender, config.TOKEN_CUACA, source="cuaca")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
        return
    try:
        g = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                      params={"name": city, "count": 1, "language": "id"}, timeout=15)
        if g.status_code != 200 or not g.json().get("results"):
            safe_reply(client, f"{config.SYM_CROSS} Kota tidak ditemukan.", message, cj)
            return
        geo = g.json()["results"][0]
        lat, lon = geo["latitude"], geo["longitude"]
        w = httpx.get("https://api.open-meteo.com/v1/forecast",
                      params={"latitude": lat, "longitude": lon, "current_weather": "true"}, timeout=15)
        if w.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        cw = w.json().get("current_weather", {})
        safe_reply(client, f"{config.SYM_BULLET} *{geo.get('name', city)}* {config.SYM_DOT} {cw.get('temperature', '?')}°C {config.SYM_DOT} {cw.get('windspeed', '?')} km/j", message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/gempa')
def handle_gempa(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_GEMPA, source="gempa")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson", timeout=15)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        feats = r.json().get("features", [])[:5]
        if not feats:
            safe_reply(client, f"{config.SYM_NOTE} Tidak ada gempa M2.5+ 24 jam.", message, cj)
            return
        lines = [f"{box_title('GEMPA M2.5+', 22)}"]
        for f in feats:
            p = f.get("properties", {})
            t = p.get("time", 0) / 1000
            dt = datetime.fromtimestamp(t, config.WIB).strftime("%d/%m %H:%M")
            lines.append(f"{config.SYM_BULLET} M{p.get('mag', '?')} {config.SYM_DOT} {p.get('place', '?')} {config.SYM_DOT} `{dt}`")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/libur')
def handle_libur(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    year = int(args.strip()) if args and args.strip().isdigit() else datetime.now(config.WIB).year
    if year < 2000 or year > 2100:
        year = datetime.now(config.WIB).year
    ok, rem = deduct_tokens(sender, config.TOKEN_LIBUR, source="libur")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/ID", timeout=15)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        hol = r.json()
        if not hol:
            safe_reply(client, f"{config.SYM_NOTE} Kosong.", message, cj)
            return
        today = datetime.now(config.WIB).date()
        lines = [f"{box_title('LIBUR ' + str(year), 22)}"]
        for h in hol[:10]:
            try:
                dt = datetime.strptime(h["date"], "%Y-%m-%d").date()
                diff = f" {config.SYM_DOT} *{(dt - today).days}h lagi*" if dt > today else (f" {config.SYM_DOT} *HARI INI*" if dt == today else "")
            except Exception:
                diff = ""
            lines.append(f"{config.SYM_BULLET} `{h.get('date', '?')}` {config.SYM_DOT} {h.get('localName') or h.get('name', '?')}{diff}")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/news')
def handle_news(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_NEWS, source="news")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        ids = r.json()[:5]
        lines = [f"{box_title('HN', 22)}"]
        for i, sid in enumerate(ids, 1):
            try:
                d = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
                lines.append(f"`{i}.` {d.get('title', '?')[:90]} {config.SYM_DOT} {d.get('score', 0)}")
            except Exception:
                continue
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/buku')
def handle_buku(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    q = validate_input(args or "", 200)
    if not q:
        safe_reply(client, "`/buku <judul>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_BUKU, source="buku")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get("https://openlibrary.org/search.json", params={"q": q, "limit": 5}, timeout=20)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        docs = r.json().get("docs", [])[:5]
        if not docs:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
            return
        lines = [f"{box_title('BUKU', 22)}"]
        for b in docs:
            a = b.get("author_name", ["?"])[0] if b.get("author_name") else "?"
            lines.append(f"{config.SYM_BULLET} *{b.get('title', '?')[:80]}* {config.SYM_DOT} {a} {config.SYM_DOT} {b.get('first_publish_year', '?')}")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/resep')
def handle_resep(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    q = validate_input(args or "", 100)
    if not q:
        safe_reply(client, "`/resep <nama>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_RESEP, source="resep")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get("https://www.themealdb.com/api/json/v1/1/search.php", params={"s": q}, timeout=15)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        meals = r.json().get("meals") or []
        if not meals:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
            return
        m = meals[0]
        lines = [f"{box_title(m.get('strMeal', '?')[:20], 22)}"]
        for i in range(1, 21):
            ing = m.get(f"strIngredient{i}")
            me = m.get(f"strMeasure{i}")
            if ing and ing.strip():
                lines.append(f"{config.SYM_BULLET} {me} {ing}")
        lines.append(f"\n_{config.SYM_DOT} Cara:_\n{(m.get('strInstructions') or '')[:400]}")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/ip')
def handle_ip(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    ip = validate_input(args or "", 45)
    if not ip:
        safe_reply(client, "`/ip <ip>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_IP_LOOKUP, source="ip")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    r = _safe_http_get(f"http://ip-api.com/json/{ip}")
    if not r or r.json().get("status") != "success":
        safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
        return
    d = r.json()
    safe_reply(client, f"{config.SYM_BULLET} {d.get('country', '?')} {config.SYM_DOT} {d.get('city', '?')} {config.SYM_DOT} {d.get('isp', '?')}", message, cj)
@register('/short')
def handle_short(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    u = validate_input(args or "", 500)
    if not u.startswith(("http://", "https://")):
        safe_reply(client, "`/short <url>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_SHORT, source="short")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get(f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(u)}", timeout=15)
        if r.status_code == 200:
            safe_reply(client, f"{config.SYM_ARROW} {r.text.strip()}", message, cj)
    except Exception:
        pass
@register('/ss')
@register('/screenshot')
def handle_screenshot(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    url = validate_input(args or "", 500)
    if not url:
        safe_reply(client, "`/ss <url>`", message, cj)
        return
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    ok, rem = deduct_tokens(sender, config.TOKEN_SCREENSHOT, source="ss")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get(f"https://image.thum.io/get/width/1200/crop/900/noanimate/{url}", timeout=30, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1024:
            safe_send_image(client, cj, r.content, caption=f"{config.SYM_DOT} {url[:50]}")
    except Exception:
        pass
@register('/crypto')
def handle_crypto(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    sym = (args or "").strip().lower()[:20] or "bitcoin"
    sym_map = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "doge": "dogecoin"}
    coin = sym_map.get(sym, sym)
    ok, rem = deduct_tokens(sender, config.TOKEN_CRYPTO, source="crypto")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    r = _safe_http_get("https://api.coingecko.com/api/v3/simple/price",
                       params={"ids": coin, "vs_currencies": "usd,idr"})
    if not r or coin not in r.json():
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
        return
    d = r.json()[coin]
    safe_reply(client, f"{config.SYM_BULLET} {sym.upper()} {config.SYM_DOT} ${d.get('usd', 0):,.2f} {config.SYM_DOT} Rp{d.get('idr', 0):,.0f}", message, cj)
@register('/country')
def handle_country(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    name = validate_input(args or "", 100)
    if not name:
        safe_reply(client, "`/country <nama>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_COUNTRY, source="country")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    r = _safe_http_get(f"https://restcountries.com/v3.1/name/{urllib.parse.quote(name)}")
    if not r:
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
        return
    try:
        d = r.json()[0]
        safe_reply(client, f"{config.SYM_BULLET} *{d.get('name', {}).get('common', name)}* {config.SYM_DOT} Pop: {d.get('population', 0):,}", message, cj)
    except Exception:
        pass
@register('/pokemon')
def handle_pokemon(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    name = validate_input(args or "", 50).lower().replace(" ", "-")
    if not name:
        safe_reply(client, "`/pokemon <nama>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_POKEMON, source="pokemon")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    r = _safe_http_get(f"https://pokeapi.co/api/v2/pokemon/{name}")
    if not r:
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
        return
    d = r.json()
    types = f" {config.SYM_DOT} ".join(t["type"]["name"] for t in d.get("types", []))
    safe_reply(client, f"{config.SYM_BULLET} *#{d.get('id', '?')} {d.get('name', '?').title()}* {config.SYM_DOT} {types}", message, cj)
@register('/anime')
def handle_anime(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    q = validate_input(args or "", 100)
    if not q:
        safe_reply(client, "`/anime <judul>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_ANIME, source="anime")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    r = _safe_http_get("https://api.jikan.moe/v4/anime", params={"q": q, "limit": 3})
    if not r:
        safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
        return
    data = r.json().get("data", [])
    if not data:
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
        return
    lines = [f"{box_title('ANIME', 22)}"]
    for a in data[:3]:
        lines.append(f"{config.SYM_BULLET} *{a.get('title', '?')}* {config.SYM_DOT} ⭐{a.get('score', '?')}")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/qr')
def handle_qr(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)
    if not require_login(client, message, cj, sender, ctx):
        return
    if not QR_AVAILABLE:
        safe_reply(client, f"{config.SYM_CROSS} qrcode.", message, cj)
        return
    text = validate_input(args or "", 500)
    if not text:
        safe_reply(client, "`/qr <teks>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_QR, source="qr")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        p = os.path.join(config.MEDIA_DIR, f"qr_{int(time.time()*1000)}.png")
        qr.make_image(fill_color="black", back_color="white").save(p)
        safe_send_image(client, cj, p, caption=config.SYM_CHECK)
    except Exception:
        pass
@register('/tts')
def handle_tts(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)
    if not require_login(client, message, cj, sender, ctx):
        return
    if not GTTS_AVAILABLE:
        safe_reply(client, f"{config.SYM_CROSS} gTTS.", message, cj)
        return
    text = validate_input(args or "", 500)
    if not text:
        safe_reply(client, "`/tts <teks>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_TTS, source="tts")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
        return
    try:
        tts = gTTS(text=text, lang="id")
        p = os.path.join(config.MEDIA_DIR, f"tts_{int(time.time()*1000)}.mp3")
        tts.save(p)
        safe_send_audio(client, cj, p, ptt=True)
    except Exception:
        pass
@register('/wiki')
def handle_wiki(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    q = validate_input(args or "", 100)
    if not q:
        safe_reply(client, "`/wiki <query>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_WIKI, source="wiki")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get(f"https://id.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(q)}",
                      timeout=15, headers={"User-Agent": "Nyx1024Bot/1.0"})
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
            return
        d = r.json()
        safe_reply(client, f"{config.SYM_BULLET} *{d.get('title', q)}*\n{(d.get('extract') or '—')[:800]}", message, cj)
    except Exception:
        pass
@register('/define')
def handle_define(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    w = validate_input(args or "", 50)
    if not w:
        safe_reply(client, "`/define <kata>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_DEFINE, source="define")
    if not ok:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    try:
        r = httpx.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(w)}", timeout=15)
        if r.status_code != 200:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
            return
        d = r.json()[0]
        lines = [f"{config.SYM_BULLET} *{d.get('word', w)}*"]
        for m in d.get("meanings", [])[:2]:
            for dfn in m.get("definitions", [])[:2]:
                lines.append(f"{config.SYM_DOT} {dfn.get('definition', '')[:150]}")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception:
        pass
@register('/kalkulator')
@register('/calc')
def handle_kalkulator(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    expr = validate_input(args or "", 200)
    if not expr:
        safe_reply(client, "`/kalkulator <expr>`", message, cj)
        return
    clean = re.sub(r"[^0-9+\-*/(). %^]", "", expr).replace("^", "**")
    if not clean or len(clean) > 200:
        safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
        return
    try:
        res = eval(clean, {"__builtins__": {}}, {})
        safe_reply(client, f"{config.SYM_BULLET} `{expr}` = *{res}*", message, cj)
    except Exception:
        safe_reply(client, f"{config.SYM_CROSS} Error.", message, cj)
@register('/encode')
def handle_encode(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    t = validate_input(args or "", 500)
    if not t:
        return
    safe_reply(client, f"{config.SYM_BULLET} `{base64.b64encode(t.encode()).decode()}`", message, cj)
@register('/decode')
def handle_decode(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    t = validate_input(args or "", 500)
    if not t:
        return
    try:
        safe_reply(client, f"{config.SYM_BULLET} `{base64.b64decode(t).decode('utf-8', errors='ignore')}`", message, cj)
    except Exception:
        pass
@register('/pw')
def handle_pw(client, message, cj, chat, sender, args, ctx):
    try:
        n = int((args or "16").strip())
        n = max(8, min(64, n))
    except Exception:
        n = 16
    alpha = string.ascii_letters + string.digits + "!@#$%^&*"
    safe_reply(client, f"{config.SYM_BULLET} `{''.join(secrets.choice(alpha) for _ in range(n))}`", message, cj)
@register('/info')
def handle_info(client, message, cj, chat, sender, args, ctx):
    st = health.status()
    sdb = _find_session_db()
    safe_reply(client,
        f"{box_title('CINNAMON v53', 22)}\n"
        f"{config.SYM_BULLET} Uptime: *{st['uptime_hours']}h*\n"
        f"{config.SYM_BULLET} Messages: *{st['total_messages']}*\n"
        f"{config.SYM_BULLET} Errors: *{st['total_errors']}*\n"
        f"{config.SYM_BULLET} Pillow: {'YES' if PILLOW_AVAILABLE else 'NO'} {config.SYM_DOT} "
        f"FFmpeg: {'YES' if FFMPEG_AVAILABLE else 'NO'} {config.SYM_DOT} "
        f"yt-dlp: {'YES' if YTDLP_AVAILABLE else 'NO'}\n"
        f"{config.SYM_BULLET} Session DB: `{short_name(str(sdb), 28) if sdb else 'NOT FOUND'}`\n"
        f"{config.SYM_BULLET} LID map: *{len(_session_lid_map())}* entries\n"
        f"{box_bottom(22)}",
        message, cj)
@register('/health', scope='owner')
def handle_health(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    st = health.status()
    lines = [f"{box_title('HEALTH', 22)}",
             f"{config.SYM_BULLET} Uptime: *{st['uptime_hours']}h*",
             f"{config.SYM_BULLET} Last msg: *{st['last_message_ago_sec']}s*",
             f"{config.SYM_BULLET} Total msg: *{st['total_messages']}*",
             f"{config.SYM_BULLET} Errors: *{st['total_errors']}*",
             f"{config.SYM_BULLET} Miners: *{st['active_miners']}*"]
    if PSUTIL_AVAILABLE:
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            lines.append(f"{config.SYM_BULLET} CPU: *{cpu}%* {config.SYM_DOT} RAM: *{mem.percent}%*")
        except Exception:
            pass
    safe_reply(client, "\n".join(lines), message, cj)
@register('/nama')
def handle_nama(client, message, cj, chat, sender, args, ctx):
    try:
        r = httpx.get("https://randomuser.me/api/", timeout=15)
        if r.status_code != 200:
            return
        u = r.json()["results"][0]
        safe_reply(client, f"{config.SYM_BULLET} {u['name']['title']} {u['name']['first']}", message, cj)
    except Exception:
        pass
@register('/menfess')
def handle_menfess(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} Grup only.", message, cj)
        return
    text = validate_input(args or "", 1000)
    if not text:
        safe_reply(client, "`/menfess <pesan>`", message, cj)
        return
    ok, rem = deduct_tokens(sender, 2, source="menfess")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Butuh 2 token.", message, cj)
        return
    safe_send_text(client, chat, f"{config.SYM_NOTE} *MENFESS*\n{hline(22)}\n\n_{text}_\n\n_{config.SYM_DOT} Anonymous_")
    safe_reply(client, f"{config.SYM_CHECK} Terkirim!", message, cj)
@register('/joke')
def handle_joke(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_NOTE} Programmer butuh Java ☕", m, jid)
@register('/quote')
def handle_quote(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_NOTE} _Mulai dari yang kecil._", m, jid)
@register('/fact')
def handle_fact(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_NOTE} Madu tidak basi.", m, jid)
@register('/8ball')
def handle_8ball(client, m, jid, c, s, a, x):
    if not a:
        safe_reply(client, "`/8ball <q>`", m, jid)
        return
    safe_reply(client, f"{config.SYM_DIAMOND} {random.choice(EIGHT_BALL)}", m, jid)
@register('/truth')
def handle_truth(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_NOTE} Paling memalukan?", m, jid)
@register('/dare')
def handle_dare(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_NOTE} Chat mantan 'kangen'.", m, jid)
@register('/say')
def handle_say(client, m, jid, c, s, a, x):
    if a:
        safe_reply(client, a, m, jid)
@register('/dice')
def handle_dice(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_BULLET} {random.randint(1, 6)}", m, jid)
@register('/roll')
def handle_roll(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_BULLET} {random.randint(1, 100)}", m, jid)
@register('/ping')
def handle_ping(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_RING} Pong!", m, jid)
@register('/id')
def handle_id(client, m, jid, c, s, a, x):
    safe_reply(client, f"{config.SYM_BULLET} `{safe_jid_str(c)}`", m, jid)
@register('/rate')
def handle_rate(client, message, cj, chat, sender, args, ctx):
    safe_reply(client, f"{config.SYM_STAR} {random.randint(1, 100)}/100", message, cj)
@register('/gay')
def handle_gay(client, message, cj, chat, sender, args, ctx):
    safe_reply(client, f"{config.SYM_DIAMOND} {random.randint(0, 100)}%", message, cj)
@register('/jodoh')
def handle_jodoh(client, message, cj, chat, sender, args, ctx):
    safe_reply(client, f"{config.SYM_STAR} {random.randint(0, 100)}%", message, cj)
def _r2_utility_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    res=run_r2_utility_feature(spec,args,sender,ctx)
    if isinstance(res,dict) and res.get('path'): safe_reply(client,f"✅ {res['path']}",message,cj)
    else: safe_reply(client,str(res),message,cj)
register_feature_specs('utility',_r2_utility_runner,category='converter'); register_feature_specs('utility',_r2_utility_runner,category='utility'); register_feature_specs('utility',_r2_utility_runner,category='search'); register_feature_specs('utility',_r2_utility_runner,category='funtext')
