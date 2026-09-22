import handlers
from handlers import register, register_feature_specs
from handlers.auth import owner_uid, require_login
import config
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time
import json
from core.utils import box_title, hline, safe_jid_str, short_name, validate_input, validate_number
from core.storage import group_id_manager, user_store
from core.send import safe_reply
from core.storage import buyer_store, user_store, group_id_manager, owner_store, atomic_json_write, ban_manager
from core.utils import now_ts
def _find_uid_by_name(name):
    return user_store.find_by_name(name)
@register('/addbuyer', scope='owner')
def handle_addbuyer(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, "`/addbuyer <u> [trial|weekly|plus] [days]`", message, cj)
        return
    target = parts[0][:50]
    pkg = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ("trial", "weekly", "plus") else "weekly"
    default_days = config.BUYER_DEFAULT_TRIAL_DAYS if pkg == "trial" else config.BUYER_DEFAULT_SERVICE_DAYS
    days = validate_number(parts[2], 1, config.BUYER_MAX_DAYS) if len(parts) > 2 else default_days
    if not days:
        days = default_days
    uid = _find_uid_by_name(target) or target
    buyer_store.create(uid, package=pkg, days=days, created_by=sender)
    def mut(p):
        p["is_buyer"] = True
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {target} {config.SYM_DOT} {pkg.upper()} {config.SYM_DOT} {days} hari {config.SYM_DOT} setter owner `{sender}`", message, cj)
@register('/delbuyer', scope='owner')
def handle_delbuyer(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    target = validate_input(args or "", 50)
    if not target:
        return
    uid = _find_uid_by_name(target) or target
    buyer_store.delete(uid)
    def mut(p):
        p["is_buyer"] = False
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {target} del", message, cj)
@register('/listbuyer', scope='owner')
def handle_listbuyer(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    buyers = buyer_store.list_active()
    if not buyers:
        safe_reply(client, f"{config.SYM_NOTE} Tidak ada.", message, cj)
        return
    lines = [f"{box_title('BUYERS', 22)}", f"Total: *{len(buyers)}*"]
    for uid, b in buyers:
        nm = user_store.get_profile(uid).get("name") or short_name(uid, 16)
        exp = b.get("expires", 0)
        es = "∞" if exp == 0 else datetime.fromtimestamp(exp, config.WIB).strftime("%d/%m/%Y %H:%M WIB")
        rem = buyer_store.remaining_seconds(uid)
        lines.append(f"{config.SYM_BULLET} *{nm}* {config.SYM_DOT} {b.get('package', '?').upper()} {config.SYM_DOT} {es} {config.SYM_DOT} sisa {_fmt_duration(rem)}")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/bindgroup')
def handle_bindgroup(client, message, cj, chat, sender, args, ctx):
    if not buyer_store.is_buyer(sender):
        safe_reply(client, f"{config.SYM_CROSS} Buyer only.", message, cj)
        return
    if not ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} Grup only.", message, cj)
        return
    ck = safe_jid_str(chat)
    info = buyer_store.get(sender) or {}
    bound = info.get("bound_groups", [])
    if ck in bound:
        safe_reply(client, f"{config.SYM_NOTE} Grup ini sudah ter-bind.", message, cj)
        return
    if len(bound) >= config.BUYER_MAX_GROUPS:
        safe_reply(client, f"{config.SYM_CROSS} Max {config.BUYER_MAX_GROUPS} grup. Hapus dulu via owner.", message, cj)
        return
    def mut(i):
        groups = i.setdefault("bound_groups", [])
        if ck not in groups:
            groups.append(ck)
    buyer_store.update(sender, mut)
    buyer_store.audit(sender, "bind_group", {"group": ck})
    safe_reply(client, f"{config.SYM_CHECK} Bind: `{group_id_manager.get_or_create(chat)}` {config.SYM_DOT} {len((buyer_store.get(sender) or {}).get('bound_groups', []))}/{config.BUYER_MAX_GROUPS}", message, cj)
@register('/mygroups')
def handle_mygroups(client, message, cj, chat, sender, args, ctx):
    if not buyer_store.is_buyer(sender):
        return
    info = buyer_store.get(sender) or {}
    groups = info.get("bound_groups", [])
    if not groups:
        safe_reply(client, f"{config.SYM_NOTE} Kosong.", message, cj)
        return
    lines = [f"{box_title('MY GROUPS', 22)}"]
    for g in groups:
        lines.append(f"{config.SYM_BULLET} `{group_id_manager.get_or_create(g)}`")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/myself')
def handle_myself(client, message, cj, chat, sender, args, ctx):
    if not buyer_store.is_buyer(sender):
        return
    body = (args or "").strip().lower()
    if body not in ("on", "off"):
        info = buyer_store.get(sender) or {}
        safe_reply(client, f"{config.SYM_BULLET} Self mode: *{'ON' if info.get('self_mode') else 'OFF'}*", message, cj)
        return
    def mut(i):
        i["self_mode"] = (body == "on")
    buyer_store.update(sender, mut)
    safe_reply(client, f"{config.SYM_CHECK} Self {body.upper()}", message, cj)
def _fmt_duration(seconds):
    if seconds is None:
        return "∞"
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f"{days} hari {hours}j"
    if hours:
        return f"{hours}j {mins}m"
    return f"{mins}m"
def _miniowner_status(uid):
    info = buyer_store.get(uid) or {}
    rem = buyer_store.remaining_seconds(uid)
    exp = info.get("expires", 0)
    exp_s = "∞" if not exp else datetime.fromtimestamp(exp, config.WIB).strftime("%d/%m/%Y %H:%M WIB")
    return info, rem, exp_s
@register('/miniowner')
@register('/minipanel')
@register('/buyerpanel')
def handle_miniowner(client, message, cj, chat, sender, args, ctx):
    if not buyer_store.is_buyer(sender):
        safe_reply(client, f"{config.SYM_CROSS} Panel ini khusus mini-owner/buyer aktif.", message, cj)
        return
    parts = (args or "").strip().split()
    sub = parts[0].lower() if parts else "status"
    if sub in ("status", "info", "panel"):
        info, rem, exp_s = _miniowner_status(sender)
        groups = info.get("bound_groups", [])
        features = info.get("features", {})
        lines = [f"{box_title('MINI-OWNER PANEL', 22)}",
                 f"{config.SYM_BULLET} Role: *MINI-OWNER / BUYER*",
                 f"{config.SYM_BULLET} Package: *{str(info.get('package', '?')).upper()}*",
                 f"{config.SYM_BULLET} Expire: *{exp_s}*",
                 f"{config.SYM_BULLET} Sisa: *{_fmt_duration(rem)}*",
                 f"{config.SYM_BULLET} Grup: *{len(groups)}/{config.BUYER_MAX_GROUPS}*",
                 f"{config.SYM_BULLET} Self mode: *{'ON' if info.get('self_mode') else 'OFF'}*",
                 f"{config.SYM_BULLET} Durasi ditetapkan oleh: `{info.get('duration_set_by', owner_uid())}`",
                 hline(22),
                 f"{config.SYM_CHECK if features.get('group_management', True) else config.SYM_CROSS} Group management",
                 f"{config.SYM_CHECK if features.get('reminder', True) else config.SYM_CROSS} Reminder",
                 f"{config.SYM_CHECK if features.get('shop', True) else config.SYM_CROSS} Shop",
                 f"{config.SYM_CHECK if features.get('fishing', True) else config.SYM_CROSS} Fishing",
                 f"{config.SYM_CHECK if features.get('gathering', True) else config.SYM_CROSS} Gathering",
                 hline(22),
                 f"{config.SYM_ARROW} `/miniowner groups`",
                 f"{config.SYM_ARROW} `/miniowner self on|off`",
                 f"{config.SYM_ARROW} `/miniowner help`"]
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub == "groups":
        info, rem, exp_s = _miniowner_status(sender)
        groups = info.get("bound_groups", [])
        if not groups:
            safe_reply(client, f"{config.SYM_NOTE} Belum ada grup ter-bind. Pakai `/bindgroup` di grup target.", message, cj)
            return
        lines = [f"{box_title('MINI-OWNER GROUPS', 22)}"]
        for idx, g in enumerate(groups, 1):
            lines.append(f"{idx}. `{group_id_manager.get_or_create(g)}`")
        lines.append(f"\n{config.SYM_BULLET} Sisa layanan: *{_fmt_duration(rem)}* {config.SYM_DOT} Exp: *{exp_s}*")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub == "self":
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            info = buyer_store.get(sender) or {}
            safe_reply(client, f"{config.SYM_BULLET} Self mode: *{'ON' if info.get('self_mode') else 'OFF'}*\n{config.SYM_ARROW} `/miniowner self on|off`", message, cj)
            return
        state = parts[1].lower() == "on"
        buyer_store.update(sender, lambda i: i.__setitem__("self_mode", state))
        buyer_store.audit(sender, "self_mode", {"enabled": state})
        safe_reply(client, f"{config.SYM_CHECK} Self mode {'ON' if state else 'OFF'}.", message, cj)
        return
    if sub == "help":
        safe_reply(client,
            f"{box_title('MINI-OWNER HELP', 22)}\n"
            f"{config.SYM_BULLET} `/miniowner` {config.SYM_DOT} panel/status\n"
            f"{config.SYM_BULLET} `/bindgroup` {config.SYM_DOT} bind grup aktif\n"
            f"{config.SYM_BULLET} `/miniowner groups` {config.SYM_DOT} daftar grup\n"
            f"{config.SYM_BULLET} `/miniowner self on|off` {config.SYM_DOT} mode khusus buyer\n"
            f"{config.SYM_BULLET} `/mygroups` {config.SYM_DOT} alias daftar grup\n"
            f"{config.SYM_BULLET} `/myself on|off` {config.SYM_DOT} alias self mode\n"
            f"{config.SYM_BULLET} Durasi layanan hanya owner yang menetapkan/memperpanjang.",
            message, cj)
        return
    safe_reply(client, f"{config.SYM_CROSS} Subcommand invalid. `/miniowner help`", message, cj)
def _owner_buyer_router(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").strip().split()
    if not ctx["is_owner"]:
        return
    if len(parts) < 2:
        safe_reply(client,
            "`/owner buyer info <u>`\n`/owner buyer extend <u> <hari>`\n`/owner buyer groups <u>`\n`/owner buyer revoke <u>`",
            message, cj)
        return
    sub = parts[0].lower()
    target = parts[1][:80]
    uid = _find_uid_by_name(target) or target
    info = buyer_store.get(uid)
    if sub == "info":
        if not info:
            safe_reply(client, f"{config.SYM_CROSS} Buyer tidak ditemukan/expired: `{target}`", message, cj)
            return
        rem = buyer_store.remaining_seconds(uid)
        exp = info.get("expires", 0)
        exp_s = "∞" if not exp else datetime.fromtimestamp(exp, config.WIB).strftime("%d/%m/%Y %H:%M WIB")
        safe_reply(client,
            f"{box_title('BUYER INFO', 22)}\n"
            f"{config.SYM_BULLET} UID: `{uid}`\n"
            f"{config.SYM_BULLET} Package: *{str(info.get('package','?')).upper()}*\n"
            f"{config.SYM_BULLET} Expire: *{exp_s}*\n"
            f"{config.SYM_BULLET} Sisa: *{_fmt_duration(rem)}*\n"
            f"{config.SYM_BULLET} Grup: *{len(info.get('bound_groups', []))}/{config.BUYER_MAX_GROUPS}*\n"
            f"{config.SYM_BULLET} Duration setter: `{info.get('duration_set_by', owner_uid())}`",
            message, cj)
        return
    if sub == "extend":
        if len(parts) < 3:
            safe_reply(client, "`/owner buyer extend <u> <hari>`", message, cj)
            return
        days = validate_number(parts[2], 1, config.BUYER_MAX_DAYS)
        if not days:
            safe_reply(client, f"{config.SYM_CROSS} Hari harus 1-{config.BUYER_MAX_DAYS}.", message, cj)
            return
        ok, updated = buyer_store.renew(uid, days, actor_uid=sender, reason="owner_extend")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Buyer tidak aktif.", message, cj)
            return
        exp_s = datetime.fromtimestamp(updated.get("expires", 0), config.WIB).strftime("%d/%m/%Y %H:%M WIB") if updated.get("expires") else "∞"
        safe_reply(client, f"{config.SYM_CHECK} `{uid}` +{days} hari {config.SYM_DOT} expire {exp_s}", message, cj)
        return
    if sub == "groups":
        if not info:
            safe_reply(client, f"{config.SYM_CROSS} Buyer tidak aktif.", message, cj)
            return
        groups = info.get("bound_groups", [])
        lines = [f"{box_title('BUYER GROUPS', 22)}", f"{config.SYM_BULLET} `{uid}` {config.SYM_DOT} {len(groups)}/{config.BUYER_MAX_GROUPS}"]
        for g in groups:
            lines.append(f"{config.SYM_DOT} `{group_id_manager.get_or_create(g)}`")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub == "revoke":
        buyer_store.delete(uid, actor_uid=sender)
        try:
            user_store.update_profile(uid, lambda p: p.__setitem__("is_buyer", False))
        except Exception:
            pass
        safe_reply(client, f"{config.SYM_CHECK} Buyer `{uid}` dicabut.", message, cj)
        return
    safe_reply(client, f"{config.SYM_CROSS} Subcommand invalid.", message, cj)

from core.identity import permission_manager

def _r2_mo_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    if not ctx.get('is_owner') and not buyer_store.is_buyer(sender): safe_reply(client,'❌ Mini-Owner/buyer aktif diperlukan.',message,cj);return
    op=spec['operation'];info=buyer_store.get(sender) or {}
    if op in ('mo','mopanel'): return handle_miniowner(client,message,cj,chat,sender,args,ctx)
    if op=='mogroups':safe_reply(client,'🤝\n'+'\n'.join(f'▸ `{x}`' for x in info.get('bound_groups',[])) or 'Kosong.',message,cj);return
    if op in ('moconfig','mosecurity','mowelcome','mogoodbye','momoderation','moperks','moschedule','moautoresponse','moevent','moaccess','motheme'):
        key=op[2:];val=(args or '').strip();
        if val:buyer_store.update(sender,lambda d:d.setdefault('features',{}).__setitem__(key,val))
        safe_reply(client,f'🤝 {key}: {((buyer_store.get(sender) or info).get("features",{}).get(key) or "default")}',message,cj);return
    if op=='mostats':safe_reply(client,f'📊 groups={len(info.get("bound_groups",[]))} · package={info.get("package","-")}',message,cj);return
    if op=='mobilling':safe_reply(client,f'💳 {info.get("package","-")} · {info.get("duration_days",0)} days',message,cj);return
    if op=='moexpiry':safe_reply(client,f'⏳ {datetime.fromtimestamp(info.get("expires",0),config.WIB).isoformat() if info.get("expires") else "∞"}',message,cj);return
    if op=='morole':safe_reply(client,f'🤝 Rank `{permission_manager.role(sender)}` · buyer={buyer_store.is_buyer(sender)}',message,cj);return
    if op=='mohelp':safe_reply(client,'🤝 `/mo groups|config|security|stats|billing|expiry|audit`',message,cj);return
    if op=='moaudit':
        safe_reply(client,'📜 Buyer audit: '+json.dumps(info.get('audit',[])[-10:],ensure_ascii=False)[:1400],message,cj);return
register_feature_specs('buyer',_r2_mo_runner,category='mo')

def _r2_owner_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not ctx.get('is_owner'): safe_reply(client,'❌ Owner only.',message,cj);return
    op=spec['operation'];parts=(args or '').split()
    if op=='ownerpanel':return handle_owner_panel(client,message,cj,chat,sender,args,ctx)
    if op=='users':
        root=Path(config.USER_DIR);rows=[]
        for d in root.iterdir() if root.exists() else []:
            if d.is_dir():rows.append((d.name,user_store.get_profile(d.name).get('name') or '-'))
        safe_reply(client,f'👥 Users {len(rows)}\n'+'\n'.join(f'▸ {n} `{u}`' for u,n in rows[:30]),message,cj);return
    if op=='buyers':return handle_listbuyer(client,message,cj,chat,sender,args,ctx)
    try:
        om=__import__('handlers.owner',fromlist=['handle_addowner'])
        mapping={'ban':'handle_ban','unban':'handle_unban','token':'handle_addtoken','premium':'handle_addprem','toggle':'handle_toggle','eval':'handle_eval','grant':'handle_addowner','revoke':'handle_delowner'}
        fn=getattr(om,mapping.get(op,''),None)
        if fn:return fn(client,message,cj,chat,sender,args,ctx)
    except Exception as ex:logging.debug('owner branch: %s',ex)
    if op=='system':safe_reply(client,f'🖥️ Build `{config.R2_BUILD}` · PID {os.getpid()}',message,cj);return
    if op=='health':safe_reply(client,'💚 storage=OK identity=OK economy=OK registry=OK',message,cj);return
    if op=='logs':
        p=Path(config.USER_DIR);safe_reply(client,f'📜 users={len(list(p.iterdir())) if p.exists() else 0}',message,cj);return
    if op=='backup':
        out=Path(config.DATA_DIR)/f'r2-backup-{int(now_ts())}.json';atomic_json_write(out,{'users':len(list(Path(config.USER_DIR).iterdir())) if Path(config.USER_DIR).exists() else 0,'buyers':len(buyer_store.list_active())});safe_reply(client,f'💾 {out.name}',message,cj);return
    if op=='restore':
        files=sorted(Path(config.DATA_DIR).glob('r2-backup-*.json'));safe_reply(client,f'💾 Latest: {files[-1].name if files else "none"}',message,cj);return
    if op=='reload':handlers.load_all();safe_reply(client,'🔄 Reloaded.',message,cj);return
    if op=='shutdown':from core.utils import shutdown_event;shutdown_event.set();safe_reply(client,'🛑 Shutdown requested.',message,cj);return
    if op in ('ownerstats','owneraudit'):
        safe_reply(client,f'👑 users={len(list(Path(config.USER_DIR).iterdir())) if Path(config.USER_DIR).exists() else 0} buyers={len(buyer_store.list_active())}',message,cj);return
    if op=='maintenance':
        ok,msg,_=feature_toggle.toggle('user','economy');safe_reply(client,f'🛠️ economy toggle → {msg}',message,cj);return
register_feature_specs('buyer',_r2_owner_runner,category='owner')
