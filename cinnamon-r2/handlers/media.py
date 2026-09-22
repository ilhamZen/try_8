from handlers import register, register_feature_specs
from handlers.auth import require_login, require_paid_cooldown
import config
from pathlib import Path
import base64
import io
import inspect
import logging
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import httpx
from PIL import ImageFilter, ImageEnhance, ImageOps
from core.utils import FFMPEG_AVAILABLE, Image, ImageDraw, ImageFont, PILLOW_AVAILABLE, YTDLP_AVAILABLE, box_bottom, box_title, validate_input, yt_dlp, ensure_dir
from core.economy import deduct_tokens
from core.send import safe_reply, safe_send_audio, safe_send_image, safe_send_sticker, safe_send_video
from core.economy import deduct_tokens
from core.send import _ensure_jid_obj
from core.storage import user_store
_FONT_CACHE = {"path": None}
def _find_font():
    if _FONT_CACHE["path"]:
        return _FONT_CACHE["path"]
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        if os.path.exists(p):
            _FONT_CACHE["path"] = p
            return p
    return None
def _load_font(size):
    p = _find_font()
    if p:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()
def _brat_img(text, size=config.BRAT_SIZE, vibrate=0, bg=(255, 255, 255, 255)):
    if not PILLOW_AVAILABLE:
        return None
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    text = (text or " ") or " "
    fs = int(size * 0.20)
    try:
        font = _load_font(fs)
    except Exception:
        return None
    words = text[:60].split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbt = draw.textbbox((0, 0), test, font=font)
        if bbt[2] - bbt[0] > size - 60 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    if not lines:
        lines = [text[:60]]
    line_h = fs + 12
    total_h = line_h * len(lines)
    y = (size - total_h) // 2
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        x = (size - tw) // 2 + (random.randint(-vibrate, vibrate) if vibrate else 0)
        yy = y + (random.randint(-vibrate, vibrate) if vibrate else 0)
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            for dy in (-3, -2, -1, 0, 1, 2, 3):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, yy + dy), line, fill=(0, 0, 0, 255), font=font)
        draw.text((x, yy), line, fill=(0, 0, 0, 255), font=font)
        y += line_h
    return img
def _fit_square(img, size=config.STICKER_SIZE, bg=(0, 0, 0, 0)):
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    scale = min(size / w, size / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), bg)
    canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2), resized)
    return canvas
def _save_sticker_webp(img_or_frames, out_path, duration=120, loop=0):
    try:
        ensure_dir(os.path.dirname(out_path) or config.MEDIA_DIR)
        if isinstance(img_or_frames, list):
            frames = [_fit_square(f, config.STICKER_SIZE) for f in img_or_frames]
            if not frames:
                return False
            frames[0].save(out_path, format="WEBP", save_all=True,
                           append_images=frames[1:], duration=duration, loop=loop,
                           quality=90, method=6, lossless=False)
        else:
            single = _fit_square(img_or_frames, config.STICKER_SIZE)
            single.save(out_path, format="WEBP", quality=90, method=6, lossless=False)
        sz = os.path.getsize(out_path)
        max_sz = 500 * 1024 if isinstance(img_or_frames, list) else 100 * 1024
        if sz > max_sz:
            if isinstance(img_or_frames, list):
                frames = [_fit_square(f, config.STICKER_SIZE) for f in img_or_frames]
                frames[0].save(out_path, format="WEBP", save_all=True,
                               append_images=frames[1:], duration=duration, loop=loop,
                               quality=60, method=6)
            else:
                _fit_square(img_or_frames, config.STICKER_SIZE).save(out_path, format="WEBP", quality=60, method=6)
        return True
    except Exception as e:
        logging.error(f"[STICKER] save: {e}")
        return False
def _download_quoted_media(client, message, tmp_ext=".jpg"):
    try:
        ensure_dir(config.MEDIA_DIR)
        if not message.Message.HasField("extendedTextMessage"):
            return None
        qm = message.Message.extendedTextMessage.contextInfo.quotedMessage
        if qm is None or not qm.ByteSize():
            return None
        tmp = os.path.join(config.MEDIA_DIR, f"quoted_{int(time.time()*1000)}{tmp_ext}")
        try:
            n = len(inspect.signature(client.download_any).parameters)
        except Exception:
            n = 1
        if n >= 2:
            client.download_any(qm, tmp)
        else:
            with open(tmp, "wb") as f:
                f.write(client.download_any(qm))
        return tmp if os.path.exists(tmp) else None
    except Exception as e:
        logging.warning(f"[STC] download quoted: {e}")
        return None
def _has_quoted_image(message):
    try:
        if not message.Message.HasField("extendedTextMessage"):
            return False
        qm = message.Message.extendedTextMessage.contextInfo.quotedMessage
        if qm is None:
            return False
        return qm.HasField("imageMessage")
    except Exception:
        return False
@register('/stc')
def handle_stc(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    if not PILLOW_AVAILABLE:
        safe_reply(client, f"{config.SYM_CROSS} Pillow tidak ada.", message, cj)
        return
    body = validate_input(args or "", 500)
    sub = (body.split()[0].lower() if body else "")
    if not body:
        if _has_quoted_image(message):
            ok, rem = deduct_tokens(sender, config.TOKEN_STC_IMG2STK, source="stc")
            if not ok:
                safe_reply(client, f"{config.SYM_CROSS} Token kurang ({rem}).", message, cj)
                return
            src = _download_quoted_media(client, message, ".png")
            if not src:
                safe_reply(client, f"{config.SYM_CROSS} Gagal ambil gambar.", message, cj)
                return
            try:
                base = Image.open(src).convert("RGBA")
                out = os.path.join(config.MEDIA_DIR, f"stk_img_{int(time.time()*1000)}.webp")
                if not _save_sticker_webp(base, out):
                    safe_reply(client, f"{config.SYM_CROSS} Gagal simpan sticker.", message, cj)
                    return
                res = safe_send_sticker(client, cj, out)
                if not res:
                    safe_reply(client, f"{config.SYM_CROSS} Gagal kirim sticker.", message, cj)
            except Exception as ex:
                safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:120]}", message, cj)
            return
        safe_reply(client,
            f"{box_title('STICKER', 22)}\n"
            f"{config.SYM_BULLET} `/stc` (reply img) {config.SYM_ARROW} polosan\n"
            f"{config.SYM_BULLET} `/stc brat <teks>`\n"
            f"{config.SYM_BULLET} `/stc vbrat <teks>`\n"
            f"{config.SYM_BULLET} Reply img {config.SYM_ARROW} `/stc up <teks>`\n"
            f"{config.SYM_BULLET} Reply img {config.SYM_ARROW} `/stc down <teks>`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if sub not in ("brat", "vbrat", "up", "down"):
        safe_reply(client, f"{config.SYM_CROSS} Subcommand tidak dikenal. Lihat `/stc`.", message, cj)
        return
    cost = config.TOKEN_STC_BRAT if sub in ("brat", "up", "down") else config.TOKEN_STC_VBRAT
    rest = body[len(sub):].strip().strip("'\"")
    text = rest[:60] if rest else ""
    if sub in ("brat", "vbrat") and not text:
        safe_reply(client, f"{config.SYM_CROSS} Kasih teks: `/stc {sub} <teks>`", message, cj)
        return
    if sub in ("up", "down") and not text:
        safe_reply(client, f"{config.SYM_CROSS} Kasih teks caption.", message, cj)
        return
    ok, rem = deduct_tokens(sender, cost, source="stc")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang ({rem}).", message, cj)
        return
    try:
        if sub == "brat":
            img = _brat_img(text)
            if not img:
                safe_reply(client, f"{config.SYM_CROSS} Gagal render.", message, cj)
                return
            out = os.path.join(config.MEDIA_DIR, f"stk_brat_{int(time.time()*1000)}.webp")
            if not _save_sticker_webp(img, out):
                safe_reply(client, f"{config.SYM_CROSS} Gagal simpan sticker.", message, cj)
                return
            res = safe_send_sticker(client, cj, out)
            if not res:
                safe_reply(client, f"{config.SYM_CROSS} Gagal kirim sticker.", message, cj)
        elif sub == "vbrat":
            frames = [_brat_img(text, vibrate=0),
                      _brat_img(text, vibrate=6),
                      _brat_img(text, vibrate=3),
                      _brat_img(text, vibrate=0)]
            frames = [f for f in frames if f]
            if not frames:
                safe_reply(client, f"{config.SYM_CROSS} Gagal render.", message, cj)
                return
            out = os.path.join(config.MEDIA_DIR, f"stk_vbrat_{int(time.time()*1000)}.webp")
            if not _save_sticker_webp(frames, out, duration=120, loop=0):
                safe_reply(client, f"{config.SYM_CROSS} Gagal simpan sticker.", message, cj)
                return
            res = safe_send_sticker(client, cj, out)
            if not res:
                safe_reply(client, f"{config.SYM_CROSS} Gagal kirim sticker.", message, cj)
        elif sub in ("up", "down"):
            src = _download_quoted_media(client, message, ".png")
            if not src:
                safe_reply(client, f"{config.SYM_CROSS} Reply ke gambar + `/stc up <teks>`", message, cj)
                return
            base = Image.open(src).convert("RGBA")
            base = _fit_square(base, config.STICKER_SIZE)
            draw = ImageDraw.Draw(base)
            font = _load_font(max(28, config.STICKER_SIZE // 14))
            bb = draw.textbbox((0, 0), text, font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            x = (config.STICKER_SIZE - tw) // 2
            y = 24 if sub == "up" else config.STICKER_SIZE - th - 40
            for dx in (-3, -2, -1, 0, 1, 2, 3):
                for dy in (-3, -2, -1, 0, 1, 2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), text, fill=(0, 0, 0, 255), font=font)
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
            out = os.path.join(config.MEDIA_DIR, f"stk_{sub}_{int(time.time()*1000)}.webp")
            if not _save_sticker_webp(base, out):
                safe_reply(client, f"{config.SYM_CROSS} Gagal simpan sticker.", message, cj)
                return
            res = safe_send_sticker(client, cj, out)
            if not res:
                safe_reply(client, f"{config.SYM_CROSS} Gagal kirim sticker.", message, cj)
    except Exception as ex:
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:120]}", message, cj)
@register('/toimg')
def handle_toimg(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    if not PILLOW_AVAILABLE:
        safe_reply(client, f"{config.SYM_CROSS} Pillow.", message, cj)
        return
    try:
        src = _download_quoted_media(client, message, ".webp")
        if not src:
            safe_reply(client, "Reply sticker.", message, cj)
            return
        png = os.path.join(config.MEDIA_DIR, f"stc_png_{int(time.time()*1000)}.png")
        Image.open(src).convert("RGBA").save(png, "PNG")
        safe_send_image(client, cj, png, caption=config.SYM_CHECK)
    except Exception as ex:
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:80]}", message, cj)
@register('/tovn')
def handle_tovn(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    if not FFMPEG_AVAILABLE:
        safe_reply(client, f"{config.SYM_CROSS} FFmpeg.", message, cj)
        return
    ok, rem = deduct_tokens(sender, config.TOKEN_TTS, source="tovn")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
        return
    try:
        src = _download_quoted_media(client, message, ".mp4")
        if not src:
            safe_reply(client, "Reply video.", message, cj)
            return
        op = os.path.join(config.MEDIA_DIR, f"vn_{int(time.time()*1000)}.ogg")
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                            "-i", src, "-vn", "-c:a", "libopus", "-b:a", "32k",
                            "-ar", "48000", "-ac", "1", "-application", "voip",
                            "-f", "ogg", op], capture_output=True, timeout=120)
        if r.returncode == 0 and os.path.exists(op):
            safe_send_audio(client, cj, op, ptt=True)
    except Exception:
        pass
def _download_media(url, out_dir, audio_only=False):
    ensure_dir(out_dir)
    if not YTDLP_AVAILABLE:
        return None
    outtmpl = os.path.join(out_dir, f"dl_{int(time.time()*1000)}_%(id)s.%(ext)s")
    opts = {"outtmpl": outtmpl, "quiet": True, "no_warnings": True,
            "noplaylist": True, "socket_timeout": 30, "retries": 3}
    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    else:
        opts["format"] = f"best[ext=mp4][filesize<{config.DL_MAX_VIDEO_MB}M]/best[ext=mp4]/best"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
            fn = ydl.prepare_filename(info)
            base = os.path.splitext(fn)[0]
            for ext in (".mp3", ".mp4", ".webm", ".mkv", ".m4a"):
                if os.path.exists(base + ext):
                    return base + ext
            if os.path.exists(fn):
                return fn
    except Exception as e:
        logging.error(f"[DL] {e}")
    return None
@register('/dl')
def handle_dl(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    body = validate_input(args or "", 500)
    if not body:
        safe_reply(client, "`/dl mp4|mp3 <link>`", message, cj)
        return
    m = re.match(r"^(mp3|mp4|audio|video)\s+(.+)$", body, re.I)
    mode = "audio" if (m and m.group(1).lower() in ("mp3", "audio")) else "video"
    url_part = m.group(2) if m else body
    um = re.search(r"https?://\S+", url_part)
    if not um:
        safe_reply(client, f"{config.SYM_CROSS} Link tidak ada.", message, cj)
        return
    url = um.group(0).rstrip(".,;!?")[:500]
    cost = config.TOKEN_DL_MP3 if mode == "audio" else config.TOKEN_DL
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, cost, source="dl")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
            return
    safe_reply(client, f"{config.SYM_RING} Download...", message, cj)
    path = _download_media(url, config.MEDIA_DIR, audio_only=(mode == "audio"))
    if not path:
        safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
        return
    sz = os.path.getsize(path) / (1024 * 1024)
    if mode == "audio":
        safe_send_audio(client, cj, path, caption=f"{config.SYM_CHECK} {sz:.1f}MB")
    else:
        safe_send_video(client, cj, path, caption=f"{config.SYM_CHECK} {sz:.1f}MB")
@register('/tdown')
def handle_tdown(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    body = validate_input(args or "", 500)
    audio = False
    if body.lower().startswith("mp3 "):
        audio = True
        body = body[4:].strip()
    m = re.search(r"https?://\S+", body)
    if not m:
        safe_reply(client, f"{config.SYM_CROSS} Link.", message, cj)
        return
    cost = config.TOKEN_TDOWN_MP3 if audio else config.TOKEN_TDOWN
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, cost, source="tdown")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
            return
    safe_reply(client, f"{config.SYM_RING} TikTok...", message, cj)
    path = _download_media(m.group(0)[:500], config.TIKTOK_DIR, audio_only=audio)
    if not path:
        safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
        return
    sz = os.path.getsize(path) / (1024 * 1024)
    if audio or path.endswith(".mp3"):
        safe_send_audio(client, cj, path, caption=f"{config.SYM_CHECK} {sz:.1f}MB")
    else:
        safe_send_video(client, cj, path, caption=f"{config.SYM_CHECK} {sz:.1f}MB")
@register('/ytm')
def handle_ytm(client, message, cj, chat, sender, args, ctx):
    ensure_dir(config.MEDIA_DIR)

    if not require_login(client, message, cj, sender, ctx):
        return
    body = validate_input(args or "", 200)
    if not body:
        safe_reply(client, "`/ytm <judul>`", message, cj)
        return
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, config.TOKEN_YTM, source="ytm")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
            return
    safe_reply(client, f"{config.SYM_RING} Cari _{body[:60]}_...", message, cj)
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(f"ytsearch1:{body}", download=False)
        if not info or not info.get("entries"):
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
            return
        first = info["entries"][0]
        vid = first.get("id", "")
        url = f"https://music.youtube.com/watch?v={vid}"
        path = _download_media(url, config.YTM_DIR, audio_only=True)
        if not path:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        safe_send_audio(client, cj, path, caption=f"{config.SYM_NOTE} {first.get('title', '?')[:80]}")
    except Exception as ex:
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:80]}", message, cj)
def _safe_http_get(url, headers=None, timeout=15, params=None):
    try:
        r = httpx.get(url, headers=headers or {"User-Agent": "Nyx1024Bot/1.0"},
                      timeout=timeout, params=params, follow_redirects=True)
        return r if r.status_code == 200 else None
    except Exception:
        return None

# R2 real media branches
_PLATFORM_HOSTS={'tiktok':('tiktok.com','vm.tiktok.com'),'youtube':('youtube.com','youtu.be','youtube-nocookie.com'),'instagram':('instagram.com','instagr.am'),'facebook':('facebook.com','fb.watch'),'twitter':('twitter.com','x.com'),'reddit':('reddit.com','redd.it'),'pinterest':('pinterest.com','pin.it'),'soundcloud':('soundcloud.com',),'spotify':('spotify.com',),'vimeo':('vimeo.com',),'dailymotion':('dailymotion.com','dai.ly'),'twitch':('twitch.tv',),'bilibili':('bilibili.com','b23.tv'),'mediafire':('mediafire.com',),'threads':('threads.net','threads.com'),'snapchat':('snapchat.com',),'likee':('likee.video',),'weibo':('weibo.com','weibo.cn'),'line':('line.me',),'tumblr':('tumblr.com',)}

def _clean_url(args):
    m=re.search(r'https?://[^\s]+',validate_input(args or '',1000)); return m.group(0).rstrip('.,;!?)]}') if m else ''
def _platform_ok(url,platform):
    host=urllib.parse.urlparse(url).netloc.lower().split(':',1)[0]; return any(host==h or host.endswith('.'+h) for h in _PLATFORM_HOSTS[platform])
def _ydl_opts(out_dir,mode,platform):
    Path(out_dir).mkdir(parents=True,exist_ok=True); out=os.path.join(out_dir,f'{platform}_{mode}_{int(time.time()*1000)}_%(id)s.%(ext)s'); o={'outtmpl':out,'quiet':True,'no_warnings':True,'noplaylist':True,'socket_timeout':30,'retries':3,'restrictfilenames':True}
    if mode=='video': o.update(format='bv*+ba/b',merge_output_format='mp4')
    elif mode=='audio':
        if not FFMPEG_AVAILABLE: raise RuntimeError('FFmpeg dibutuhkan untuk audio')
        o.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3'}])
    elif mode=='thumbnail': o.update(skip_download=True,writethumbnail=True)
    else: o.update(skip_download=True,writesubtitles=True,writeautomaticsub=True,subtitleslangs=['id','en','all'],subtitlesformat='srt/vtt/best')
    return o
def _result_file(ydl,info):
    for pth in (info.get('_filename'),info.get('filepath')):
        if pth and os.path.isfile(pth) and os.path.getsize(pth)>0: return pth
    try: pth=ydl.prepare_filename(info)
    except Exception: pth=''
    if pth:
        stem,_=os.path.splitext(pth)
        for ext in ('.mp4','.mp3','.m4a','.webm','.mkv','.jpg','.jpeg','.png','.srt','.vtt','.ass'):
            q=stem+ext
            if os.path.isfile(q) and os.path.getsize(q)>0: return q
    root=os.path.dirname(pth)
    if root and os.path.isdir(root):
        files=[os.path.join(root,x) for x in os.listdir(root) if os.path.isfile(os.path.join(root,x))]
        if files: return max(files,key=os.path.getmtime)
    return None
def _run_ytdlp(url,platform,mode,out_dir=config.MEDIA_DIR):
    ensure_dir(out_dir)
    if not YTDLP_AVAILABLE or yt_dlp is None: raise RuntimeError('yt-dlp belum terpasang')
    if platform not in _PLATFORM_HOSTS or not _platform_ok(url,platform): raise ValueError(f'URL bukan domain {platform}')
    with yt_dlp.YoutubeDL(_ydl_opts(out_dir,mode,platform)) as ydl:
        info=ydl.extract_info(url,download=True)
        if not info: raise RuntimeError('yt-dlp tidak mengembalikan info')
        path=_result_file(ydl,info)
        if not path: raise RuntimeError('file hasil tidak ditemukan')
        return {'path':path,'title':info.get('title') or platform,'platform':platform,'mode':mode}
def _r2_download_runner(client,message,cj,chat,sender,args,ctx,spec):
    ensure_dir(config.MEDIA_DIR)
    ensure_dir(config.TIKTOK_DIR)
    ensure_dir(config.YTM_DIR)
    if not require_login(client,message,cj,sender,ctx): return
    if not require_paid_cooldown(client,message,cj,sender,ctx): return
    url=_clean_url(args)
    if not url: safe_reply(client,'📥 Beri URL.',message,cj); return
    cost=5 if not ctx.get('is_owner') else 0
    if cost:
        ok,rem=deduct_tokens(sender,cost,'r2-download')
        if not ok: safe_reply(client,f'🪙 Token kurang ({rem}).',message,cj); return
    platform=spec['operation']
    try:
        res=_run_ytdlp(url,platform,'video'); safe_send_video(client,cj,res['path'],caption=f'📥 {res["title"][:100]}'); return res
    except Exception as ex: safe_reply(client,f'📥 Gagal: {str(ex)[:120]}',message,cj)

def _image_input(client,message,args):
    a=(args or '').strip();
    if a and os.path.isfile(a): return a
    return _download_quoted_media(client,message,'.png')
def _r2_image_runner(client,message,cj,chat,sender,args,ctx,spec):
    ensure_dir(config.MEDIA_DIR)
    if not require_login(client,message,cj,sender,ctx): return
    if not PILLOW_AVAILABLE: safe_reply(client,'Pillow tidak tersedia.',message,cj); return
    src=_image_input(client,message,args)
    if not src or not os.path.exists(src): safe_reply(client,'Reply gambar atau kirim path file.',message,cj); return
    op=spec['operation']; img=Image.open(src).convert('RGBA');
    if op=='blur': out=img.filter(ImageFilter.GaussianBlur(4))
    elif op=='sharpen': out=img.filter(ImageFilter.SHARPEN)
    elif op=='contrast': out=ImageEnhance.Contrast(img).enhance(1.6)
    elif op=='brightness': out=ImageEnhance.Brightness(img).enhance(1.4)
    elif op=='sepia':
        g=ImageOps.grayscale(img).convert('RGBA'); px=g.load(); out=Image.new('RGBA',g.size); out.putdata([(min(255,int(p[0]*1.1+35)),min(255,int(p[0]*0.9+20)),min(255,int(p[0]*0.6+5)),a) for (p,a) in [(g.getpixel((x,y)),img.getpixel((x,y))[3]) for y in range(g.height) for x in range(g.width)]])
    elif op=='grayscale': out=ImageOps.grayscale(img).convert('RGBA')
    elif op=='negate': out=ImageOps.invert(img.convert('RGB')).convert('RGBA')
    elif op=='emboss': out=img.filter(ImageFilter.EMBOSS)
    elif op=='edge': out=img.filter(ImageFilter.FIND_EDGES)
    elif op=='pixelate':
        n=max(8,min(64,16)); small=img.resize((max(1,img.width//n),max(1,img.height//n))); out=small.resize(img.size,Image.Resampling.NEAREST)
    elif op=='mirror': out=ImageOps.mirror(img)
    elif op=='flip': out=ImageOps.flip(img)
    elif op=='rotate': out=img.rotate(90,expand=True)
    elif op=='crop':
        w,h=img.size; out=img.crop((w//10,h//10,w-w//10,h-h//10))
    elif op=='resize':
        scale=min(1024/max(1,img.width),1024/max(1,img.height),1); out=img.resize((max(1,int(img.width*scale)),max(1,int(img.height*scale))))
    elif op=='watermark':
        out=img.copy(); d=ImageDraw.Draw(out); f=_load_font(max(24,out.width//18)); d.text((15,15),'CINNAMON',font=f,fill=(255,255,255,220),stroke_width=2,stroke_fill=(0,0,0,220))
    elif op=='autocontrast': out=ImageOps.autocontrast(img.convert('RGB')).convert('RGBA')
    elif op=='posterize': out=ImageOps.posterize(img.convert('RGB'),3).convert('RGBA')
    elif op=='solarize': out=ImageOps.solarize(img.convert('RGB'),128).convert('RGBA')
    elif op=='contour': out=img.filter(ImageFilter.CONTOUR)
    else: out=img
    outp=os.path.join(config.MEDIA_DIR,f'r2_{op}_{int(time.time()*1000)}.png'); out.save(outp,'PNG'); safe_send_image(client,cj,outp,caption=f'🖼️ {op}'); return outp

def _media_input(client,message,args,ext):
    a=(args or '').strip(); return a if a and os.path.isfile(a) else _download_quoted_media(client,message,ext)
def _ff(client,message,cj,chat,sender,args,ctx,spec):
    ensure_dir(config.MEDIA_DIR)
    if not require_login(client,message,cj,sender,ctx): return
    if not FFMPEG_AVAILABLE: safe_reply(client,'FFmpeg tidak tersedia.',message,cj); return
    src=_media_input(client,message,args,'.mp4')
    if not src or not os.path.exists(src): safe_reply(client,'Reply media atau kirim file path.',message,cj); return
    op=spec['operation']; out=os.path.join(config.MEDIA_DIR,f'r2_{op}_{int(time.time()*1000)}.'+('gif' if op=='gif' else 'mp3' if op=='extractaudio' else 'mp4'))
    vf={'trim':'trim=start=0:duration=10,setpts=PTS-STARTPTS','crop':'crop=iw*0.8:ih*0.8','speed':'setpts=0.5*PTS','slow':'setpts=2*PTS','fast':'setpts=0.5*PTS','reverse':'reverse','mute':'volume=0','volume':'volume=2','normalize':'loudnorm','gif':'fps=12,scale=480:-1','audiotrim':'atrim=start=0:duration=10','pitch':'asetrate=44100*1.10,aresample=44100','bass':'bass=g=6','treble':'treble=g=6','fadein':'afade=t=in:st=0:d=2'}.get(op)
    if op=='videoinfo' or op=='audioinfo': safe_reply(client,f'ℹ️ `{os.path.basename(src)}` size={os.path.getsize(src)//1024}KB',message,cj); return
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-i',src]
    if op=='extractaudio': cmd += ['-vn','-c:a','libmp3lame','-b:a','128k']
    elif op=='gif': cmd += ['-vf',vf,'-an','-f','gif']
    elif op in ('audiomerge',):
        safe_reply(client,'🎧 /audiomerge membutuhkan dua file: `/audiomerge <file1> <file2>`.',message,cj); return
    else:
        if vf and op in ('trim','crop','speed','slow','fast','reverse','mute','volume','normalize'): cmd += ['-vf',vf]
        elif vf: cmd += ['-af',vf]
        if op in ('trim','crop','speed','slow','fast','reverse','mute','volume','normalize'): cmd += ['-c:a','aac']
    cmd += [out]
    try:
        r=subprocess.run(cmd,capture_output=True,timeout=180); 
        if r.returncode or not os.path.exists(out): raise RuntimeError(r.stderr.decode(errors='ignore')[-300:])
        if out.endswith('.gif'): safe_send_image(client,cj,out,caption=f'🎬 {op}')
        elif out.endswith('.mp3'): safe_send_audio(client,cj,out,caption=f'🎧 {op}')
        else: safe_send_video(client,cj,out,caption=f'🎬 {op}')
        return out
    except Exception as ex: safe_reply(client,f'🎬 Gagal: {str(ex)[:100]}',message,cj)

def _r2_media_router(client,message,cj,chat,sender,args,ctx,spec):
    cat=spec['category']
    if cat=='media': return _r2_download_runner(client,message,cj,chat,sender,args,ctx,spec)
    if cat=='image': return _r2_image_runner(client,message,cj,chat,sender,args,ctx,spec)
    return _ff(client,message,cj,chat,sender,args,ctx,spec)

register_feature_specs('media',_r2_media_router,category='media')
register_feature_specs('media',_r2_media_router,category='image')
register_feature_specs('media',_r2_media_router,category='videoaudio')
