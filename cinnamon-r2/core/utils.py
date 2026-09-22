"""Pure/shared helpers and lightweight runtime guards."""
import hashlib
import json
import logging
import os
import re
import secrets
import signal
import subprocess
import tempfile
import threading
import time
import urllib.parse
from collections import deque
from datetime import datetime
from pathlib import Path
try:
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    qrcode = None
    QR_AVAILABLE = False
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    gTTS = None
    GTTS_AVAILABLE = False
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    yt_dlp = None
    YTDLP_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
import config

def ensure_dir(path: str) -> Path:
    """Ensure a directory exists; tolerate a concurrent creator safely."""
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not p.is_dir():
            raise RuntimeError(f"Path exists but is not a directory: {path}")
    except PermissionError as e:
        raise RuntimeError(f"Cannot create directory {path}: {e}") from e
    return p

def ensure_media_dirs():
    """Ensure all runtime media/download directories exist."""
    for d in (config.MEDIA_DIR, config.TIKTOK_DIR, config.YTM_DIR):
        ensure_dir(d)

shutdown_event = threading.Event()
_processed_msg_ids = deque(maxlen=2000)
_processed_lock = threading.Lock()
def is_duplicate_message(mid):
    if not mid:
        return False
    with _processed_lock:
        if mid in _processed_msg_ids:
            return True
        _processed_msg_ids.append(mid)
        return False
def now_ts():
    return time.time()
def wib_day_start(ts=None):
    if ts is None:
        ts = now_ts()
    dt = datetime.fromtimestamp(ts, config.WIB)
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.timestamp()
def short_name(jid, n=14):
    u = str(jid).split("@")[0].split(":")[0]
    return u if len(u) <= n else u[:n - 3] + "..."
def safe_jid_str(jid):
    if jid is None:
        return ""
    try:
        return re.sub(r":\d+@", "@", str(jid))
    except Exception:
        return str(jid)
def hash_password(pw, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
    return dk.hex(), salt
def verify_password(pw, h, s):
    if not h or not s:
        return False
    try:
        c, _ = hash_password(pw, s)
        return secrets.compare_digest(c, h)
    except Exception:
        return False
def _normalize_phone_digits(d):
    if not d:
        return ""
    d = str(d).strip()
    if d.startswith("0") and len(d) > 10:
        return "62" + d[1:]
    if d.startswith("62"):
        return d
    return d.lstrip("0") if d.startswith("0") else d
def _digits_match(a, b):
    if a is None or b is None:
        return False
    a_s = re.sub(r":\d+@", "@", str(a))
    b_s = re.sub(r":\d+@", "@", str(b))
    a_d = re.sub(r"\D", "", a_s)
    b_d = re.sub(r"\D", "", b_s)
    if not a_d or not b_d:
        return False
    a_n = _normalize_phone_digits(a_d)
    b_n = _normalize_phone_digits(b_d)
    if a_n == b_n or a_d == b_d or a_d.lstrip("0") == b_d.lstrip("0"):
        return True
    if a_n.startswith(b_n) or b_n.startswith(a_n):
        return min(len(a_n), len(b_n)) >= 10
    return False
def _is_owner_by_number(uid_or_jid):
    if uid_or_jid is None:
        return False
    try:
        s = re.sub(r":\d+@", "@", str(uid_or_jid))
        d = re.sub(r"\D", "", s)
        if not d:
            return False
        owner_d = config.OWNER_NUMBER_DIGITS
        owner_local = owner_d[2:] if len(owner_d) > 2 else owner_d
        d_n = _normalize_phone_digits(d)
        if d in (owner_d, owner_local) or d_n in (owner_d, owner_local):
            return True
        if d.lstrip("0") == owner_d.lstrip("0"):
            return True
        if d.startswith(owner_d) or d.startswith(owner_local) or d.endswith(owner_d) or d.endswith(owner_local):
            return True
    except Exception:
        pass
    try:
        from core.storage import is_registered_owner
        return bool(is_registered_owner(uid_or_jid))
    except Exception:
        return False
def _is_lid(j):
    return "@lid" in str(j)
def _is_pn(j):
    return "@s.whatsapp.net" in str(j)
def _strip_device(j):
    return re.sub(r":\d+@", "@", str(j)).strip()
def _bare_lid(j):
    return str(j).split("@")[0].split(":")[0]
def _stable_key(j):
    return _strip_device(j)
def validate_input(text, max_len=config.MAX_INPUT_LEN):
    if not text:
        return ""
    text = str(text)
    return text[:max_len].strip()
def validate_number(val, min_val=0, max_val=10**9):
    try:
        n = int(val)
        return n if min_val <= n <= max_val else None
    except (ValueError, TypeError):
        return None
def is_group_message(message):
    is_group = False
    chat_jid = None
    try:
        src = message.Info.MessageSource
        is_group = bool(src.IsGroup)
        chat_jid = src.Chat
    except Exception:
        pass
    if not is_group and chat_jid is not None:
        try:
            is_group = getattr(chat_jid, "Server", None) == "g.us"
        except Exception:
            pass
    if chat_jid is not None and "@g.us" in str(chat_jid):
        is_group = True
    return is_group, chat_jid, (safe_jid_str(chat_jid) if chat_jid else "")
def parse_command(text):
    if not text:
        return "", ""
    t = text.strip()
    if not (t.startswith("/") or t.startswith("!")):
        return "", ""
    parts = t.split(None, 1)
    return parts[0].lower(), (parts[1] if len(parts) > 1 else "")
def hline(n=22, ch=config.SYM_LINE):
    return ch * n
def box_title(title, n=22):
    pad = max(0, n - len(title) - 2); left = pad // 2; right = pad - left
    return f"{config.SYM_TOP_L}{config.SYM_LINE * left} {title} {config.SYM_LINE * right}{config.SYM_TOP_R}"
def box_bottom(n=22):
    return f"{config.SYM_BOT_L}{config.SYM_LINE * (n - 2)}{config.SYM_BOT_R}"
def build_roman(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    pairs = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    out=[]
    for unit, roman in pairs:
        q,n=divmod(n,unit)
        if q: out.append(roman*q)
    return "".join(out)
UI_SDIV = hline(22)
def _ffmpeg_exists():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return True
    except Exception:
        return False
FFMPEG_AVAILABLE = _ffmpeg_exists()
def log_activity(uid, action, detail=None):
    if not uid or _is_owner_by_number(uid):
        return
    try:
        d = Path(config.USER_DIR) / uid
        d.mkdir(parents=True, exist_ok=True)
        entry = {"ts": round(now_ts(), 2), "when": datetime.now(config.WIB).strftime("%Y-%m-%d %H:%M:%S"), "action": action}
        if detail:
            entry["detail"] = detail
        with open(d / "activity.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.debug(f"[ACTIVITY] {e}")
def read_activity(uid, limit=30):
    try:
        p = Path(config.USER_DIR) / uid / "activity.log"
        if not p.exists(): return []
        lines = p.read_text(encoding="utf-8").strip().split("\n")
        out=[]
        for line in lines[-limit:]:
            try: out.append(json.loads(line))
            except Exception: continue
        return out
    except Exception:
        return []
class RateLimiter:
    def __init__(self, m=20):
        self.m=m; self._b={}; self._l=threading.Lock()
    def allow(self, uid):
        n=time.time()
        with self._l:
            a=self._b.setdefault(uid,deque(maxlen=self.m))
            while a and n-a[0]>60: a.popleft()
            if len(a)>=self.m: return False
            a.append(n); return True
class PaidCooldown:
    def __init__(self, cd=5): self.cd=cd; self._d={}; self._l=threading.Lock()
    def check(self, uid):
        n=time.time()
        with self._l:
            last=self._d.get(uid,0); wait=max(0,self.cd-(n-last))
            if wait>0: return False,wait
            self._d[uid]=n; return True,0
class CommandQueue:
    def __init__(self, max_concurrent=20): self.sem=threading.BoundedSemaphore(max_concurrent); self._l=threading.Lock(); self._active=0
    def acquire(self, uid):
        if self.sem.acquire(blocking=False):
            with self._l: self._active += 1
            return True,0
        with self._l: return False,self._active+1
    def release(self):
        with self._l: self._active=max(0,self._active-1)
        self.sem.release()
class AntiBanManager:
    def __init__(self): self._last={}; self._l=threading.Lock(); self._fails={}
    def allow_group_op(self, group):
        n=time.time()
        with self._l:
            wait=max(0,config.GROUP_OP_COOLDOWN-(n-self._last.get(group,0)))
            return (False,wait) if wait>0 else (True,0)
    def mark_success(self): return None
    def mark_failure(self): return None
class HealthCheck:
    def __init__(self): self.started=time.time(); self.messages=0; self.errors=0; self._l=threading.Lock()
    def on_message(self):
        with self._l: self.messages+=1
    def on_error(self):
        with self._l: self.errors+=1
    def status(self):
        with self._l:
            return {"uptime":int(time.time()-self.started),"messages":self.messages,"errors":self.errors}
rate_limiter=RateLimiter(config.RATE_LIMIT_PER_USER)
paid_cooldown=PaidCooldown(config.PAID_COOLDOWN)
cmd_queue=CommandQueue(config.MAX_CONCURRENT_COMMANDS)
antibane=AntiBanManager()
health=HealthCheck()


# ---------------------------------------------------------------------------
# CINNAMON R1 GENERATED FEATURE BANK (pure/deterministic; no AI/LLM)
# ---------------------------------------------------------------------------
def feature_menu_lines(category, page=0, page_size=14):
    """Return command names for a category without dumping the global registry."""
    import config
    specs = config.R2_FEATURES_BY_CATEGORY.get(category, ())
    page = max(0, int(page or 0))
    chunk = specs[page * page_size:(page + 1) * page_size]
    return [f"`{s['aliases'][0]}`" for s in chunk]

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def clamp(value, low, high):
    return max(low, min(high, value))

def process_start_ts():
    return getattr(process_start_ts, "started", now_ts())
process_start_ts.started = now_ts()

def run_r2_utility_feature(spec, args="", sender=None, ctx=None):
    """Real local/web utility branches. Returns text or {path,kind}."""
    import ast, base64, codecs, hashlib, math, random, statistics, uuid
    op=spec["operation"]; a=(args or "").strip()
    if op=="calculator":
        allowed={ast.Add:__import__('operator').add,ast.Sub:__import__('operator').sub,ast.Mult:__import__('operator').mul,ast.Div:__import__('operator').truediv,ast.Pow:__import__('operator').pow,ast.Mod:__import__('operator').mod}
        def walk(n):
            if isinstance(n,ast.Expression): return walk(n.body)
            if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub): return -walk(n.operand)
            if isinstance(n,ast.BinOp) and type(n.op) in allowed: return allowed[type(n.op)](walk(n.left),walk(n.right))
            raise ValueError("unsupported")
        return f"🧮 {walk(ast.parse(a or '0',mode='eval'))}"
    if op in ("percentage","ratio","average","median","mode","gcd","lcm","primefactor","fibonacci"):
        nums=[int(x) for x in re.findall(r'-?\d+',a)]
        if op=="percentage" and len(nums)>=2: return f"📐 {nums[0]/nums[1]*100:.2f}%"
        if op=="ratio" and len(nums)>=2: return f"📐 {nums[0]}:{nums[1]}"
        if op=="average" and nums: return f"📐 {statistics.fmean(nums):.4f}"
        if op=="median" and nums: return f"📐 {statistics.median(nums):.4f}"
        if op=="mode" and nums: return f"📐 {statistics.mode(nums)}"
        if op=="gcd" and len(nums)>=2: return f"📐 {math.gcd(*nums[:6])}"
        if op=="lcm" and len(nums)>=2: return f"📐 {math.lcm(*nums[:6])}"
        if op=="primefactor" and nums:
            n=abs(nums[0]); f=[]; d=2
            while d*d<=n:
                while n%d==0: f.append(d); n//=d
                d+=1
            if n>1: f.append(n)
            return f"📐 {' × '.join(map(str,f)) or '1'}"
        if op=="fibonacci":
            n=max(0,min(100,nums[0] if nums else 10)); seq=[0,1]
            for _ in range(2,n): seq.append(seq[-1]+seq[-2])
            return f"📐 {seq[:n]}"
        return "📐 Masukkan angka yang cukup."
    if op in ("units","length","area","volume","weight","temperature"):
        nums=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',a)]; n=nums[0] if nums else 1
        if op=="length": return f"📏 {n} m = {n*100:.2f} cm = {n*1000:.2f} mm"
        if op=="area": return f"📐 {n} m² = {n*10000:.2f} cm²"
        if op=="volume": return f"🧊 {n} L = {n*1000:.2f} mL"
        if op=="weight": return f"⚖️ {n} kg = {n*1000:.2f} g"
        if op=="temperature": return f"🌡️ {n}°C = {(n*9/5)+32:.2f}°F = {n+273.15:.2f}K"
        return "🧰 unit conversions: length/area/volume/weight/temperature"
    if op in ("time","date","timestamp"): return f"🕒 {datetime.now(config.WIB).isoformat()} · ts {int(time.time())}"
    if op=="uuid": return str(uuid.uuid4())
    if op=="password":
        n=max(8,min(64,int(a) if a.isdigit() else 16)); chars='abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%'; return ''.join(random.choice(chars) for _ in range(n))
    if op=="hash": return hashlib.sha256(a.encode()).hexdigest() if a else "Masukkan teks."
    if op=="base64encode": return base64.b64encode(a.encode()).decode()
    if op=="base64decode":
        try: return base64.b64decode(a.encode()).decode()
        except Exception: return "Base64 invalid."
    if op=="qrgen":
        try:
            import qrcode
            ensure_dir(config.MEDIA_DIR); out=os.path.join(config.MEDIA_DIR,f"r2_qr_{int(time.time()*1000)}.png"); qrcode.make(a or 'CINNAMON').save(out); return {"path":out,"kind":"image"}
        except Exception: return "qrcode belum tersedia."
    if op=="qrscan":
        p=Path(a.split()[0]) if a else None
        if not p or not p.exists(): return "Kirim path gambar QR."
        try:
            import cv2
            img=cv2.imread(str(p)); text,_,_=cv2.QRCodeDetector().detectAndDecode(img); return text or "QR tidak terbaca."
        except ImportError: return "qrscan memerlukan opencv-python-headless."
        except Exception as ex: return f"QR scan gagal: {ex}"
    if op=="fileinfo":
        p=Path(a); return f"📄 {p.name} · {p.stat().st_size} bytes · exists={p.exists()}" if p.exists() else "File tidak ditemukan."
    if op in ("pdf2img","img2pdf","png2jpg","jpg2png","png2webp","webp2png","avif2png","csv2json","json2csv","csv2xlsx","xlsx2csv","md2html","html2md","pdf2docx","docx2pdf"):
        p=Path(a.split()[0]) if a else None
        if not p or not p.exists(): return "Kirim path file sebagai argumen."
        outdir=ensure_dir(config.MEDIA_DIR); stem=outdir/f"r2_{op}_{int(time.time()*1000)}"
        try:
            from PIL import Image
            if op in ('png2jpg','jpg2png','png2webp','webp2png','avif2png'):
                im=Image.open(p); ext={'png2jpg':'jpg','jpg2png':'png','png2webp':'webp','webp2png':'png','avif2png':'png'}[op]; out=f'{stem}.{ext}'; im.convert('RGB' if ext=='jpg' else 'RGBA').save(out); return {'path':out,'kind':'image'}
            if op=='pdf2img':
                import fitz; doc=fitz.open(p); page=doc[0]; pix=page.get_pixmap(); out=f'{stem}.png'; pix.save(out); doc.close(); return {'path':out,'kind':'image'}
            if op=='img2pdf':
                im=Image.open(p).convert('RGB'); out=f'{stem}.pdf'; im.save(out,'PDF'); return {'path':out,'kind':'document'}
            if op=='pdf2docx':
                import fitz; from docx import Document
                docx=Document(); pdf=fitz.open(p); [docx.add_paragraph(pg.get_text()) for pg in pdf]; out=f'{stem}.docx'; docx.save(out); pdf.close(); return {'path':out,'kind':'document'}
            if op=='docx2pdf':
                from docx import Document; from reportlab.pdfgen import canvas
                doc=Document(p); out=f'{stem}.pdf'; c=canvas.Canvas(out); y=800
                for para in doc.paragraphs:
                    for line in (para.text or ' ').split('\n'): c.drawString(40,y,line[:110]); y-=14; 
                    if y<40: c.showPage(); y=800
                c.save(); return {'path':out,'kind':'document'}
            if op=='csv2json':
                import csv,json; rows=list(csv.DictReader(open(p,encoding='utf-8',newline=''))); out=f'{stem}.json'; json.dump(rows,open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=2); return {'path':out,'kind':'document'}
            if op=='json2csv':
                import csv,json; rows=json.load(open(p,encoding='utf-8')); out=f'{stem}.csv'; fields=sorted({k for r in rows for k in r});
                with open(out,'w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
                return {'path':out,'kind':'document'}
            if op=='csv2xlsx':
                import csv,openpyxl; wb=openpyxl.Workbook(); ws=wb.active
                for row in csv.reader(open(p,encoding='utf-8',newline='')): ws.append(row)
                out=f'{stem}.xlsx'; wb.save(out); return {'path':out,'kind':'document'}
            if op=='xlsx2csv':
                import csv,openpyxl; wb=openpyxl.load_workbook(p,read_only=True); ws=wb.active; out=f'{stem}.csv'
                with open(out,'w',encoding='utf-8',newline='') as f: csv.writer(f).writerows(ws.iter_rows(values_only=True))
                return {'path':out,'kind':'document'}
            if op=='md2html':
                text=p.read_text(encoding='utf-8'); html=''.join(f'<p>{__import__("html").escape(x)}</p>' for x in text.splitlines()); out=f'{stem}.html'; Path(out).write_text(f'<html><body>{html}</body></html>',encoding='utf-8'); return {'path':out,'kind':'document'}
            if op=='html2md':
                from html.parser import HTMLParser
                raw=p.read_text(encoding='utf-8'); out=f'{stem}.md'; Path(out).write_text(re.sub(r'<[^>]+>',' ',raw),encoding='utf-8'); return {'path':out,'kind':'document'}
        except Exception as ex: return f"Converter gagal: {ex}"
    if op in ("google","bing","ddg","imagesearch","youtubesearch","githubsearch","wikipedia","news","weather","dictionary","translate","currency","crypto","stockinfo","package","domain","dns","iplookup","books","anime"):
        import html as _html, httpx
        q=a or "cinnamon"
        try:
            H={"User-Agent":"Mozilla/5.0 (Cinnamon/2.0)"}
            if op in ("google","bing","ddg","imagesearch","youtubesearch"):
                base={"google":"https://www.google.com/search","bing":"https://www.bing.com/search","ddg":"https://html.duckduckgo.com/html/","imagesearch":"https://www.google.com/search","youtubesearch":"https://www.youtube.com/results"}[op]
                params={"q":q};
                if op=="imagesearch": params["tbm"]="isch"
                r=httpx.get(base,params=params,headers=H,timeout=8); r.raise_for_status(); raw=re.sub(r"<script.*?</script>|<style.*?</style>"," ",r.text,flags=re.S); text=re.sub(r"<[^>]+>"," ",raw); text=_html.unescape(re.sub(r"\s+"," ",text)); return f"🔎 {op.upper()} · {q}\n{text[:1600]}"
            if op=="githubsearch":
                j=httpx.get("https://api.github.com/search/repositories",params={"q":q,"per_page":8},headers=H,timeout=8).json(); return "\n".join(f"{i+1}. {x['full_name']} ★{x.get('stargazers_count',0)}\n{x.get('html_url','')}" for i,x in enumerate(j.get('items',[]))) or "Tidak ditemukan."
            if op=="wikipedia":
                j=httpx.get("https://id.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(q),headers=H,timeout=8).json(); return f"📚 {j.get('title',q)}\n{j.get('extract','Tidak ditemukan.')[:1400]}"
            if op=="news":
                j=httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",params={"query":q,"mode":"artlist","format":"json","maxrecords":5},headers=H,timeout=8); return f"📰 {q}\n"+re.sub(r"\\n+","\n",json.dumps(j.json() if j.headers.get("content-type","").startswith("application/json") else {"status":j.status_code},ensure_ascii=False)[:1800])
            if op=="weather": return httpx.get("https://wttr.in/"+urllib.parse.quote(q),params={"format":"j1"},headers=H,timeout=8).text[:1800]
            if op=="dictionary":
                j=httpx.get("https://api.dictionaryapi.dev/api/v2/entries/en/"+urllib.parse.quote(q),headers=H,timeout=8).json(); x=j[0]; return f"📖 {x.get('word')}\n"+"\n".join(m.get('definition','') for m in x.get('meanings',[{}])[0].get('definitions',[])[:8])
            if op=="translate":
                parts=a.split(None,1); lang,text=(parts[0],parts[1]) if len(parts)>1 else ("id",a); j=httpx.get("https://translate.googleapis.com/translate_a/single",params={"client":"gtx","sl":"auto","tl":lang,"dt":"t","q":text},headers=H,timeout=8).json(); return "🌐 "+"".join(x[0] for x in j[0] if x[0])
            if op=="currency":
                parts=(a or "USD IDR").upper().split(); frm=parts[0]; to=parts[1] if len(parts)>1 else "IDR"; j=httpx.get(f"https://api.frankfurter.app/latest",params={"from":frm,"to":to},headers=H,timeout=8).json(); return f"💱 {frm}/{to} = {j.get('rates',{}).get(to)}"
            if op=="crypto":
                coin=q.split()[0].lower(); j=httpx.get("https://api.coingecko.com/api/v3/simple/price",params={"ids":coin,"vs_currencies":"usd,idr"},headers=H,timeout=8).json(); return f"🪙 {coin.upper()}\n{json.dumps(j,ensure_ascii=False)}"
            if op=="stockinfo":
                t=(q.split()[0] or "AAPL").upper(); r=httpx.get("https://stooq.com/q/l/",params={"s":t.lower(),"f":"sd2t2ohlcv","h":"","e":"csv"},headers=H,timeout=8); return f"📈 {t}\n{r.text[:900]}"
            if op=="package":
                j=httpx.get("https://pypi.org/pypi/"+q+"/json",headers=H,timeout=8).json(); return f"📦 {j['info']['name']} {j['info']['version']}\n{j['info']['summary'] or ''}\n{j['info']['home_page'] or ''}"
            if op in ("domain","dns"):
                host=q.split('/')[0].split(':')[0]; j=httpx.get("https://cloudflare-dns.com/dns-query",params={"name":host,"type":"A"},headers={"accept":"application/dns-json"},timeout=8).json(); return json.dumps(j.get('Answer',[]),ensure_ascii=False)[:1500]
            if op=="iplookup":
                j=httpx.get(f"https://ipapi.co/{q or 'ip'}/json/",headers=H,timeout=8).json(); return json.dumps(j,ensure_ascii=False)[:1500]
            if op=="books":
                j=httpx.get("https://openlibrary.org/search.json",params={"q":q,"limit":5},headers=H,timeout=8).json(); return "\n".join(f"{d.get('title','?')} — {', '.join(d.get('author_name',[])[:2])}" for d in j.get('docs',[])) or "Tidak ditemukan."
            if op=="anime":
                j=httpx.get("https://api.jikan.moe/v4/anime",params={"q":q,"limit":5},headers=H,timeout=10).json(); return "\n".join(f"{x['title']} · score={x.get('score')}\n{x.get('url','')}" for x in j.get('data',[])) or "Tidak ditemukan."
        except Exception as ex: return f"{op}: request failed: {str(ex)[:180]}"
    if op in ('joke','quote','fact','truth','dare','roast','compliment','ship','rate','coin','dice','roll','randomname','randomcolor','randomnumber','randomword','choose','shuffle','upper','lower'):
        vals={'joke':'Kenapa programmer suka kopi? Karena bug tidak minum air.','quote':'Mulai kecil, konsisten besar.','fact':'Lebah dapat mengenali pola wajah.','truth':'Apa targetmu bulan ini?','dare':'Kirim emoji favoritmu.','roast':'Kode kamu butuh unit test, bukan keberanian.','compliment':'Kamu makin jago.','ship':f'{a or "A"} × {random.randint(60,99)}%','rate':f'{random.randint(1,100)}/100','coin':random.choice(['HEADS','TAILS']),'dice':str(random.randint(1,6)),'roll':str(random.randint(1,100)),'randomname':random.choice(['Alya','Bima','Citra','Damar','Naya','Raka']),'randomcolor':f'#{random.randint(0,0xFFFFFF):06X}','randomnumber':str(random.randint(0,999999)),'randomword':random.choice(['cinnamon','adventure','quest','ember','nyx']),'choose':random.choice([x for x in a.split('|') if x] or ['A','B']),'shuffle':' '.join(random.sample(a.split(),len(a.split()))) if a.split() else '', 'upper':a.upper(),'lower':a.lower()}; return str(vals[op])
    return f"Operation `{op}` requires a concrete argument or file."
