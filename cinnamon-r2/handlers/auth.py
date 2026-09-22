from handlers import register, register_feature_specs
from apscheduler.triggers.cron import CronTrigger
import config
from config import MAX_NAME_LEN, MIN_NAME_LEN
from datetime import datetime
import json
import logging
import os
import random
import re
import sys
import time
import traceback
import threading
from pathlib import Path
from core.utils import _digits_match, _is_lid, _is_owner_by_number, _stable_key, box_bottom, box_title, hash_password, log_activity, now_ts, paid_cooldown, read_activity, safe_jid_str, short_name, verify_password
from core.storage import add_owner_registry, atomic_json_read, atomic_json_write, is_registered_owner, owner_store, user_store
from core.identity import identity_registry, merge_fragmented_folders
from core.send import safe_reply
from core.economy import xp_for_level
from core.identity import identity_registry, session_identity, register_jid_pair, merge_fragmented_folders, _find_session_db, _read_session_lid_map, _session_lid_map, _SESSION_LID_CACHE
from core.send import safe_reply
from core.storage import add_owner_registry, atomic_json_read, atomic_json_write, user_store, owner_store, buyer_store, is_registered_owner, load_owner_number, save_owner_number, load_owner_registry, save_owner_registry, _shared_read, _shared_update
class PendingStore:
    def __init__(self):
        self._lock = threading.RLock()
    def _p(self, key):
        safe = re.sub(r"[^a-zA-Z0-9@._-]", "_", _stable_key(key))
        return Path(config.PENDING_DIR) / f"{safe}.json"
    def save(self, key, data):
        with self._lock:
            data["_created"] = now_ts()
            data["_key"] = _stable_key(key)
            atomic_json_write(self._p(key), data)
    def get(self, key):
        with self._lock:
            p = self._p(key)
            if not p.exists():
                return None
            d = atomic_json_read(p)
            if now_ts() - d.get("_created", 0) > config.PENDING_TTL:
                try:
                    p.unlink()
                except Exception:
                    pass
                return None
            return d
    def delete(self, key):
        with self._lock:
            try:
                self._p(key).unlink()
            except Exception:
                pass
    def cleanup(self):
        with self._lock:
            for p in Path(config.PENDING_DIR).glob("*.json"):
                try:
                    d = atomic_json_read(p)
                    if now_ts() - d.get("_created", 0) > config.PENDING_TTL:
                        p.unlink()
                except Exception:
                    pass
def is_owner_anywhere(message):
    cands = []
    try:
        src = message.Info.MessageSource
        for attr in ("Sender", "SenderAlt", "Recipient", "RecipientAlt", "Participant", "ParticipantAlt"):
            val = getattr(src, attr, None)
            if val is not None:
                cands.append(str(val))
        cj = getattr(src, "Chat", None)
        if cj is not None:
            cands.append(str(cj))
    except Exception:
        pass
    for c in cands:
        if _digits_match(c, config.OWNER_NUMBER_DIGITS):
            return True
    return False
def detect_owner(message, client_obj, sender):
    if is_owner_anywhere(message):
        return True
    try:
        src = message.Info.MessageSource
        for alt_attr in ("SenderAlt", "ParticipantAlt"):
            val = getattr(src, alt_attr, None)
            if val and _digits_match(str(val), config.OWNER_NUMBER_DIGITS):
                return True
    except Exception:
        pass
    if is_registered_owner(sender):
        return True
    try:
        if _digits_match(sender, config.OWNER_NUMBER_DIGITS):
            return True
    except Exception:
        pass
    try:
        p = user_store.get_profile(sender)
        if (p.get("name") or "").lower() == config.OWNER_USERNAME.lower():
            return True
    except Exception:
        pass
    try:
        if client_obj:
            me = client_obj.me
            if me:
                if _digits_match(sender, str(me.JID)):
                    return True
                lid = getattr(me, "LID", None)
                if lid and _digits_match(sender, str(lid)):
                    return True
    except Exception:
        pass
    return False
def is_owner_uid(uid):
    if _is_owner_by_number(uid):
        return True
    if is_registered_owner(uid):
        return True
    try:
        p = user_store.get_profile(uid)
        if (p.get("name") or "").lower() == config.OWNER_USERNAME.lower():
            return True
    except Exception:
        pass
    return False
def owner_uid():
    return f"{config.OWNER_NUMBER_DIGITS}@s.whatsapp.net"
def ensure_owner_profile(client_obj=None):
    oid = owner_uid()
    if not user_store.user_exists(oid):
        user_store.create_user(oid, config.OWNER_USERNAME, "", "")
    def mut(p):
        p["name"] = config.OWNER_USERNAME
        p["premium"] = True
        p["premium_expires"] = 0
        p["title"] = "👑 Owner"
        p["logged_in"] = True
        p["level"] = max(p.get("level", 1), 100)
    user_store.update_profile(oid, mut)
    owner_store.ensure(oid, config.OWNER_USERNAME)
    owner_store.audit(oid, "owner_profile_sync", {"username": config.OWNER_USERNAME})
    identity_registry.register_user(oid, name=config.OWNER_USERNAME)
    add_owner_registry(oid)
    if client_obj:
        try:
            me = client_obj.me
            if me:
                me_jid = safe_jid_str(me.JID)
                if me_jid:
                    add_owner_registry(me_jid)
                    identity_registry.add_alias(oid, me_jid)
                lid = getattr(me, "LID", None)
                if lid:
                    lid_s = safe_jid_str(lid)
                    add_owner_registry(lid_s)
                    identity_registry.add_alias(oid, lid_s)
                    identity_registry.link_lid_pn(lid_s, oid)
        except Exception as e:
            logging.warning(f"[OWNER] me: {e}")
def require_login(client, message, cj, sender, ctx):
    if ctx["is_owner"]:
        return True
    p = user_store.get_profile(sender)
    if not p.get("name") or not p.get("logged_in"):
        safe_reply(client, f"{config.SYM_CROSS} Login dulu: `!register` / `!login`", message, cj)
        return False
    return True
def require_paid_cooldown(client, message, cj, sender, ctx):
    if ctx["is_owner"]:
        return True
    ok, wait = paid_cooldown.check(sender)
    if not ok:
        safe_reply(client, f"{config.SYM_RING} Tunggu {wait}s.", message, cj)
        return False
    return True
@register('!register')
def handle_register(client, message, cj, chat, sender, args, ctx):
    if ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_SHIELD} Owner sudah terdaftar.", message, cj)
        return
    if ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} PM only.", message, cj)
        return
    raw_sender = ctx.get("raw_sender", sender)
    stable = _stable_key(raw_sender)
    existing = user_store.find_by_any(sender, raw_sender)
    if existing and user_store.user_exists(existing):
        p = user_store.get_profile(existing)
        if p.get("name"):
            pending_store.delete(stable)
            safe_reply(client, f"{config.SYM_CROSS} Kamu sudah terdaftar sebagai *{p.get('name')}*. Gunakan `!login`.", message, cj)
            return
    parts = (args or "").split(None, 1)
    if len(parts) < 2:
        safe_reply(client, "`!register <nama> <pass>`", message, cj)
        return
    name = parts[0].strip()[:MAX_NAME_LEN]
    pw = parts[1].strip()[:100]
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        safe_reply(client, f"{config.SYM_CROSS} Format nama (huruf/angka/_).", message, cj)
        return
    if len(name) < MIN_NAME_LEN or len(pw) < config.MIN_PASSWORD_LEN:
        safe_reply(client, f"{config.SYM_CROSS} Min {MIN_NAME_LEN} char / pass {config.MIN_PASSWORD_LEN} char.", message, cj)
        return
    if name.lower() == config.OWNER_USERNAME.lower():
        safe_reply(client, f"{config.SYM_CROSS} Nama dilindungi.", message, cj)
        return
    existing_uid = user_store.find_by_name(name)
    if existing_uid and user_store.user_exists(existing_uid):
        safe_reply(client, f"{config.SYM_CROSS} Nama sudah dipakai.", message, cj)
        return
    ph, salt = hash_password(pw)
    pending_store.save(stable, {
        "name": name,
        "password_hash": ph,
        "password_salt": salt,
        "raw_sender": raw_sender,
        "canonical_hint": sender,
    })
    safe_reply(client, f"{config.SYM_CHECK} Kirim `!confirm` untuk menyelesaikan.", message, cj)
@register('!confirm')
def handle_confirm(client, message, cj, chat, sender, args, ctx):
    raw_sender = ctx.get("raw_sender", sender)
    stable = _stable_key(raw_sender)
    pend = pending_store.get(stable)
    if not pend:
        pend = pending_store.get(sender)
    if not pend:
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada pending registrasi. Jalankan `!register` dulu.", message, cj)
        return
    existing = user_store.find_by_any(sender, raw_sender, pend.get("canonical_hint", ""))
    if existing and user_store.user_exists(existing):
        p = user_store.get_profile(existing)
        if p.get("name"):
            pending_store.delete(stable)
            pending_store.delete(sender)
            safe_reply(client, f"{config.SYM_CROSS} Sudah terdaftar sebagai *{p.get('name')}*. Gunakan `!login`.", message, cj)
            return
    final_uid = pend.get("canonical_hint") or sender or raw_sender
    if not final_uid:
        final_uid = raw_sender
    if "@" not in final_uid:
        final_uid = raw_sender
    user_store.create_user(final_uid, pend["name"], pend["password_hash"], pend["password_salt"])
    def mut(e):
        e["tokens"] = config.TOKEN_USER_BARU + config.REGISTER_BONUS_TOKENS
    user_store.update_economy(final_uid, mut)
    identity_registry.set_session_canonical(stable, final_uid)
    identity_registry.register_user(final_uid, name=pend["name"])
    for alias in (raw_sender, sender, final_uid):
        if alias and alias != final_uid:
            user_store.register_alias(final_uid, alias)
            identity_registry.add_alias(final_uid, alias)
    pending_store.delete(stable)
    pending_store.delete(sender)
    log_activity(final_uid, "register_confirmed", {"name": pend["name"]})
    safe_reply(client,
        f"{config.SYM_STAR} Akun aktif! +{config.REGISTER_BONUS_TOKENS} token\n"
        f"{config.SYM_ARROW} Login: `!login {pend['name']} <pass>`\n"
        f"{config.SYM_DOT} UID: `{short_name(final_uid, 22)}`",
        message, cj)
@register('!login')
def handle_login(client, message, cj, chat, sender, args, ctx):
    if ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_SHIELD} Auto-login (owner).", message, cj)
        return
    if ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} PM only.", message, cj)
        return
    parts = (args or "").split(None, 1)
    if len(parts) < 2:
        safe_reply(client, "`!login <nama> <pass>`", message, cj)
        return
    name, pw = parts[0].strip(), parts[1].strip()
    target = user_store.find_by_name(name)
    if not target or not user_store.user_exists(target):
        safe_reply(client, f"{config.SYM_CROSS} Nama *{name}* tidak terdaftar.", message, cj)
        return
    raw_sender = ctx.get("raw_sender", sender)
    stable = _stable_key(raw_sender)
    mapped = identity_registry.get_session_canonical(stable)
    if mapped and mapped != target:
        p_target = user_store.get_profile(target)
        aliases_target = p_target.get("aliases", []) or []
        if mapped in aliases_target or _digits_match(mapped, target):
            pass  # ok
        else:
            p_mapped = user_store.get_profile(mapped)
            if p_mapped.get("name") and p_mapped.get("name").lower() != name.lower():
                safe_reply(client, f"{config.SYM_CROSS} Nomor ini terdaftar sebagai *{p_mapped.get('name')}*, bukan *{name}*.", message, cj)
                return
    alias_uid = user_store.find_by_alias(raw_sender)
    if alias_uid and alias_uid != target:
        p_alias = user_store.get_profile(alias_uid)
        if p_alias.get("name") and p_alias.get("name").lower() != name.lower():
            safe_reply(client, f"{config.SYM_CROSS} Nomor ini terdaftar sebagai *{p_alias.get('name')}*.", message, cj)
            return
    elif alias_uid == target:
        pass  # ok
    elif target != sender and not _digits_match(target, sender) and not _digits_match(target, raw_sender):
        if _is_lid(raw_sender) or _is_lid(target):
            user_store.register_alias(target, raw_sender)
        else:
            safe_reply(client, f"{config.SYM_CROSS} Nama *{name}* milik nomor lain.", message, cj)
            return
    p = user_store.get_profile(target)
    if not verify_password(pw, p.get("password_hash"), p.get("password_salt")):
        safe_reply(client, f"{config.SYM_CROSS} Password salah.", message, cj)
        return
    def mut(pp):
        pp["logged_in"] = True
        pp["last_login"] = now_ts()
    user_store.update_profile(target, mut)
    identity_registry.set_session_canonical(stable, target)
    identity_registry.register_user(target, name=name)
    for alias in (raw_sender, sender):
        if alias and alias != target:
            user_store.register_alias(target, alias)
            identity_registry.add_alias(target, alias)
    log_activity(target, "login", {"name": name})
    try:
        _grant_ach(target, "universal.first_login")
    except Exception:
        pass
    safe_reply(client,
        f"{config.SYM_CHECK} Login sukses! Halo *{name}*\n"
        f"{config.SYM_DOT} UID: `{short_name(target, 22)}`",
        message, cj)
@register('!logout')
def handle_logout(client, message, cj, chat, sender, args, ctx):
    if ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_SHIELD} Owner tidak bisa logout.", message, cj)
        return
    def mut(p):
        p["logged_in"] = False
    user_store.update_profile(sender, mut)
    log_activity(sender, "logout")
    safe_reply(client, f"{config.SYM_CHECK} Logout.", message, cj)
@register('/whoami')
def handle_whoami(client, message, cj, chat, sender, args, ctx):
    raw = ctx.get("raw_sender", sender)
    canonical = sender
    method = ctx.get("uid_method", "unknown")
    profile = user_store.get_profile(canonical)
    name = profile.get("name") or "(belum terdaftar)"
    logged = profile.get("logged_in", False)
    aliases = profile.get("aliases", [])
    reg_user = identity_registry.get_user(canonical)
    lines = [
        f"{box_title('WHOAMI', 22)}",
        f"{config.SYM_BULLET} Raw: `{short_name(raw, 22)}`",
        f"{config.SYM_BULLET} Stable: `{short_name(_stable_key(raw), 22)}`",
        f"{config.SYM_BULLET} Canonical: `{short_name(canonical, 22)}`",
        f"{config.SYM_BULLET} Method: `{method}`",
        f"{config.SYM_BULLET} Name: *{name}*",
        f"{config.SYM_BULLET} Logged in: *{'YES' if logged else 'NO'}*",
        f"{config.SYM_BULLET} Alias count: *{len(aliases)}*",
    ]
    if aliases:
        for a in aliases[:5]:
            lines.append(f"  {config.SYM_DOT} `{short_name(a, 22)}`")
    if reg_user:
        try:
            dt = datetime.fromtimestamp(reg_user.get("registered_at", 0), config.WIB).strftime("%d/%m/%Y")
            lines.append(f"{config.SYM_DOT} Registry: registered {dt}")
        except Exception:
            pass
    lines.append(box_bottom(22))
    safe_reply(client, "\n".join(lines), message, cj)
@register('/fixme')
def handle_fixme(client, message, cj, chat, sender, args, ctx):
    if ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_SHIELD} Owner tidak butuh ini.", message, cj)
        return
    raw = ctx.get("raw_sender", sender)
    canonical = sender
    candidates = set()
    for ud in Path(config.USER_DIR).iterdir():
        if not ud.is_dir():
            continue
        if ud.name == canonical:
            continue
        p = atomic_json_read(ud / "profile.json", default={})
        aliases = p.get("aliases", []) or []
        if raw in aliases or canonical in aliases or _digits_match(ud.name, raw):
            candidates.add(ud.name)
            continue
        profile = user_store.get_profile(canonical)
        nm = profile.get("name")
        if nm and (p.get("name") or "").lower() == nm.lower():
            candidates.add(ud.name)
    if not candidates:
        safe_reply(client, f"{config.SYM_CHECK} Tidak ada fragmentasi. Akunmu konsisten.", message, cj)
        return
    results = []
    for alias in candidates:
        ok, info = merge_fragmented_folders(canonical, alias)
        if ok:
            results.append(f"{config.SYM_CHECK} {short_name(alias, 18)} {config.SYM_ARROW} merged")
        else:
            results.append(f"{config.SYM_CROSS} {short_name(alias, 18)}: {info}")
    safe_reply(client, "\n".join([f"{box_title('FIXME', 22)}"] + results + [box_bottom(22)]), message, cj)
@register('/activity')
def handle_activity(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    n = 15
    if args and args.strip():
        parts = args.strip().split()
        if parts and parts[0].isdigit():
            n = max(1, min(50, int(parts[0])))
    entries = read_activity(sender, limit=n)
    if not entries:
        safe_reply(client, f"{config.SYM_NOTE} Belum ada aktivitas.", message, cj)
        return
    lines = [f"{box_title('ACTIVITY', 22)}"]
    for e in reversed(entries):
        when = e.get("when", "?")
        action = e.get("action", "?")
        detail = e.get("detail") or {}
        if action == "item_add":
            d = f"+{detail.get('qty', '?')} {detail.get('key', '?')} ({detail.get('source', '?')})"
        elif action == "item_remove":
            d = f"-{detail.get('qty', '?')} {detail.get('key', '?')} ({detail.get('source', '?')})"
        elif action in ("tokens_add", "cash_add"):
            d = f"+{detail.get('amount', '?')} ({detail.get('source', '?')})"
        elif action in ("tokens_deduct", "cash_deduct"):
            d = f"-{detail.get('amount', '?')} ({detail.get('source', '?')})"
        elif action == "stock_buy":
            d = f"{detail.get('qty', '?')}× {detail.get('ticker', '?')} = {detail.get('cost', '?')}"
        else:
            d = json.dumps(detail, ensure_ascii=False)[:40] if detail else ""
        lines.append(f"{config.SYM_BULLET} `{when[5:]}` {action} {config.SYM_DOT} {d}")
    lines.append(box_bottom(22))
    safe_reply(client, "\n".join(lines), message, cj)
pending_store = PendingStore()
def setup_scheduler(client, scheduler):
    scheduler.add_job(lambda: pending_store.cleanup(), trigger=CronTrigger(minute=30, timezone=config.WIB), id="pending_cleanup", replace_existing=True)

from core.identity import permission_manager, title_manager

_R2_ACH_PATH = os.path.join(config.SHARED_DIR, "r2_achievements.json")
_R2_ACH = {
    "universal.first_login": ("First Login", "Login pertama", "🌱", "Newcomer"),
    "universal.veteran": ("Veteran", "Account 30 hari", "🎖️", "Veteran"),
    "universal.collector": ("Collector", "Memiliki 20 item berbeda", "🎒", "Collector"),
    "universal.social": ("Social", "Interaksi sosial 25 kali", "💞", "Social Butterfly"),
    "universal.explorer": ("Explorer", "Gunakan 10 kategori", "🧭", "Explorer"),
    "game.slot100": ("Slot Regular", "100 permainan slot", "🎰", "High Roller"),
    "game.dungeon1": ("Dungeon Clear", "Selesaikan dungeon", "⚔️", "Dungeon Runner"),
    "game.fishing10": ("Angler", "10 tangkapan", "🎣", "Angler"),
    "game.mining10": ("Miner", "10 hasil tambang", "⛏️", "Miner"),
    "game.rpg10": ("RPG Adventurer", "10 aksi RPG", "🗡️", "Adventurer"),
}

def _ach_data():
    return atomic_json_read(_R2_ACH_PATH, default={"users": {}, "game": {}})

def _grant_ach(uid, key):
    if key not in _R2_ACH: return False
    d=_ach_data(); u=d.setdefault("users",{}).setdefault(uid,{})
    if key in u: return False
    u[key]=now_ts(); atomic_json_write(_R2_ACH_PATH,d)
    info=_R2_ACH[key]; title_manager.unlock(uid, info[3])
    log_activity(uid,"achievement",{"key":key,"title":info[3]})
    return True

def _r2_auth_runner(client,message,cj,chat,sender,args,ctx,spec):
    op=spec["operation"]; p=user_store.get_profile(sender); e=user_store.get_economy(sender)
    if op in ("profile","whoami","identity","activity","aliases","rank","level","xp","stats","session","security","title","titlelist","titleuse","recovery","preferences") and op not in ("whoami","identity"): 
        if not require_login(client,message,cj,sender,ctx): return
    if op=="profile":
        title=title_manager.active(sender) or p.get("title") or "—"
        safe_reply(client,f"{box_title('PROFILE',26)}\n👤 *{p.get('name') or 'Guest'}*\n👑 Rank: *{permission_manager.role(sender).upper()}*\n🏷️ Title: *{title}*\n⭐ Level: *{p.get('level',1)}*\n💰 Cash: *{e.get('cash',0)}*\n🪙 Token: *{e.get('tokens',0)}*\n🏆 Ach: *{len(_ach_data().get('users',{}).get(sender,{}))}*\n{box_bottom(26)}",message,cj); return
    if op=="whoami":
        safe_reply(client,f"{box_title('WHOAMI',26)}\nraw: `{ctx.get('raw_sender','')}`\ncanonical: `{sender}`\nmethod: `{ctx.get('uid_method','?')}`\nlogin: *{'YES' if p.get('logged_in') else 'NO'}*\nrank: *{permission_manager.role(sender)}*\n{box_bottom(26)}",message,cj); return
    if op=="identity":
        aliases=p.get("aliases",[]) or []; safe_reply(client,f"{box_title('IDENTITY',26)}\ncanonical: `{sender}`\nraw: `{ctx.get('raw_sender','')}`\naliases: *{len(aliases)}*\n"+"\n".join(f"▸ `{a}`" for a in aliases[:15]),message,cj); return
    if op=="activity": handle_activity(client,message,cj,chat,sender,"",ctx); return
    if op=="aliases":
        safe_reply(client,"\n".join([f"{box_title('ALIASES',24)}"]+[f"▸ `{a}`" for a in p.get('aliases',[])[:30]]+[box_bottom(24)]),message,cj); return
    if op=="login": handle_login(client,message,cj,chat,sender,args,ctx); return
    if op=="logout": handle_logout(client,message,cj,chat,sender,args,ctx); return
    if op=="rename":
        name=validate_input(args,config.MAX_NAME_LEN); 
        if not (config.MIN_NAME_LEN<=len(name)<=config.MAX_NAME_LEN): safe_reply(client,f"{config.SYM_CROSS} Nama {config.MIN_NAME_LEN}-{config.MAX_NAME_LEN} karakter.",message,cj); return
        user_store.update_profile(sender,lambda x:x.__setitem__("name",name)); identity_registry.register_user(sender,name=name); safe_reply(client,f"{config.SYM_CHECK} Nama → *{name}*",message,cj); return
    if op=="password":
        parts=args.split()
        if len(parts)!=2 or len(parts[1])<config.MIN_PASSWORD_LEN: safe_reply(client,"`/password <lama> <baru>`",message,cj); return
        if not verify_password(parts[0],p.get('password_hash'),p.get('password_salt')): safe_reply(client,f"{config.SYM_CROSS} Password lama salah.",message,cj); return
        h,s=hash_password(parts[1]); user_store.update_profile(sender,lambda x:(x.__setitem__('password_hash',h),x.__setitem__('password_salt',s))); safe_reply(client,f"{config.SYM_CHECK} Password diperbarui.",message,cj); return
    if op=="title": safe_reply(client,f"🏷️ Aktif: *{title_manager.active(sender) or p.get('title') or '—'}*",message,cj); return
    if op=="titlelist":
        vals=title_manager.list(sender); safe_reply(client,f"{box_title('TITLES',26)}\n"+("\n".join(f"▸ {x}" for x in vals) if vals else "Belum ada title kosmetik.")+f"\n{box_bottom(26)}",message,cj); return
    if op=="titleuse":
        name=validate_input(args,40); ok=title_manager.equip(sender,name); safe_reply(client,f"{config.SYM_CHECK} Title aktif: *{name}*" if ok else f"{config.SYM_CROSS} Title tidak unlocked.",message,cj); return
    if op in ("rank","role_info"):
        safe_reply(client,f"👑 Rank: *{permission_manager.role(sender).upper()}*\n🏷️ Title: *{title_manager.active(sender) or p.get('title') or '—'}*",message,cj); return
    if op=="level": safe_reply(client,f"⭐ Level: *{p.get('level',1)}*",message,cj); return
    if op=="xp": safe_reply(client,f"✨ XP: *{p.get('xp',0)}* / next *{xp_for_level(p.get('level',1)+1)}*",message,cj); return
    if op=="stats": safe_reply(client,f"{box_title('STATS',26)}\n⭐ Level {p.get('level',1)}\n✨ XP {p.get('xp',0)}\n💰 Cash {e.get('cash',0)}\n🪙 Token {e.get('tokens',0)}\n🎒 Items {len(user_store.get_inventory(sender))}\n{box_bottom(26)}",message,cj); return
    if op=="session": safe_reply(client,f"Session canonical: `{sender}`\nResolver: `{ctx.get('uid_method','?')}`",message,cj); return
    if op=="security": safe_reply(client,f"Login: *{'ON' if p.get('logged_in') else 'OFF'}*\nBot disabled: *{'YES' if p.get('bot_disabled') else 'NO'}*",message,cj); return
    if op=="recovery": safe_reply(client,"Recovery memakai `!login <nama> <password>` dan identity registry untuk alias LID/PN.",message,cj); return
    if op=="preferences": safe_reply(client,"Preferences tersimpan pada profile; title bersifat kosmetik.",message,cj); return
    return _r2_access_runner(client,message,cj,chat,sender,args,ctx,spec)

def _r2_access_runner(client,message,cj,chat,sender,args,ctx,spec):
    op=spec["operation"]
    if op in ("permissions","roles","roleinfo","group_role","context","accesscheck","inheritance","mo_status","owner_status","admin_status","premium_status","feature_access","permission_help","node_list"):
        role=permission_manager.role(sender); group=chat if ctx.get('is_group') else None
        if op=="permissions": out=[n for n in ("user.game.play","user.economy.use","user.rpg.play") if permission_manager.has(sender,n,group)]; safe_reply(client,"🔐 *Permissions*\n"+"\n".join(f"▸ `{x}`" for x in out),message,cj); return
        if op=="roles" or op=="roleinfo": safe_reply(client,f"Global rank: *{role.upper()}*\nInheritance: `{', '.join(permission_manager.INHERIT[role])}`",message,cj); return
        if op=="group_role": safe_reply(client,f"Group role: *{permission_manager.group_role(sender,group) or 'member'}*",message,cj); return
        if op=="context": safe_reply(client,f"Context group: `{group or 'private'}`",message,cj); return
        if op=="accesscheck":
            node=validate_input(args,80) or "user.game.play"; safe_reply(client,f"`{node}` → *{'ALLOW' if permission_manager.has(sender,node,group) else 'DENY'}*",message,cj); return
        if op=="inheritance": safe_reply(client,"OWNER → MO → USER",message,cj); return
        if op=="mo_status": safe_reply(client,f"MO: *{'ACTIVE' if permission_manager.role(sender) in ('mo','owner') else 'NO'}*",message,cj); return
        if op=="owner_status": safe_reply(client,f"Owner: *{'YES' if permission_manager.role(sender)=='owner' else 'NO'}*",message,cj); return
        if op=="admin_status": safe_reply(client,f"Admin: *{'YES' if ctx.get('is_admin') else 'NO'}*",message,cj); return
        if op=="premium_status": safe_reply(client,f"Premium: *{'YES' if p.get('premium') else 'NO'}*",message,cj); return
        if op=="feature_access": safe_reply(client,"Feature access dihitung dari role + context + toggle.",message,cj); return
        if op=="permission_help": safe_reply(client,"Permission memakai node dan context group.",message,cj); return
        if op=="node_list": safe_reply(client,"user.*, group.*, mo.*, owner.*",message,cj); return
    target=validate_input(args,80)
    if op in ("set_mo","revoke_mo","set_admin","revoke_admin"):
        if not ctx.get('is_owner'): safe_reply(client,f"{config.SYM_CROSS} Owner only.",message,cj); return
        if not target: safe_reply(client,"Butuh target UID/JID.",message,cj); return
        if op=="set_mo": permission_manager.set_role(target,"mo"); safe_reply(client,f"{config.SYM_CHECK} MO → `{target}`",message,cj); return
        if op=="revoke_mo": permission_manager.set_role(target,"user"); safe_reply(client,f"{config.SYM_CHECK} MO dicabut.",message,cj); return
        if op=="set_admin": permission_manager.grant_group_role(target,chat,"admin"); safe_reply(client,f"{config.SYM_CHECK} Admin group → `{target}`",message,cj); return
        permission_manager.revoke_group_role(target,chat); safe_reply(client,f"{config.SYM_CHECK} Admin dicabut.",message,cj); return


def _r2_achievement_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    d=_ach_data(); owned=d.get("users",{}).get(sender,{})
    op=spec["operation"]
    if op in ("achievement","achievements","universalach","gameach","achievementprogress","achievementstats","achievementreward","achievementtitle","achievementhelp","achievementrecent","achievementclaim"):
        if op in ("achievement","achievements","achievementrecent"):
            safe_reply(client,f"{box_title('ACHIEVEMENTS',28)}\nUnlocked: *{len(owned)}/{len(_R2_ACH)}*\n"+"\n".join(f"✅ {k}" for k in list(owned)[-12:])+f"\n{box_bottom(28)}",message,cj); return
        if op=="universalach": keys=[k for k in _R2_ACH if k.startswith('universal.')]
        elif op=="gameach": keys=[k for k in _R2_ACH if k.startswith('game.')]
        else: keys=list(_R2_ACH)
        safe_reply(client,"\n".join([f"🏆 *{op}*",*[("✅" if k in owned else "🔒")+" "+_R2_ACH[k][0] for k in keys]]),message,cj); return
    return

def _r2_auth_dispatch(client,message,cj,chat,sender,args,ctx,spec):
    if spec["category"]=="achievement": return _r2_achievement_runner(client,message,cj,chat,sender,args,ctx,spec)
    return _r2_auth_runner(client,message,cj,chat,sender,args,ctx,spec)

register_feature_specs("auth", _r2_auth_dispatch, category="account")
register_feature_specs("auth", _r2_auth_dispatch, category="access")
register_feature_specs("auth", _r2_auth_dispatch, category="achievement")
