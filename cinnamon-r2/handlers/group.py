from handlers import register, register_feature_specs
from neonize.utils import build_jid
from apscheduler.triggers.cron import CronTrigger
import config
import logging
import random
import os
import re
import time
import json
from pathlib import Path
from core.utils import _digits_match, _normalize_phone_digits, _strip_device, antibane, hline, now_ts, safe_jid_str, short_name, shutdown_event, validate_input
from core.storage import _shared_read, _shared_update, group_id_manager
_sched_path = config._sched_path
from core.identity import session_identity
from core.send import _ensure_jid_obj, safe_reply, safe_send_text
from core.send import safe_reply
from core.storage import user_store, buyer_store, group_id_manager
def _get_mention(message):
    try:
        ext = message.Message.extendedTextMessage
        if ext.HasField("contextInfo") and ext.contextInfo.mentionedJID:
            return _strip_device(ext.contextInfo.mentionedJID[0])
    except Exception:
        pass
    return None
def _is_group_admin(client, chat_jid, sender_jid):
    try:
        info = client.get_group_info(_ensure_jid_obj(chat_jid))
        participants = list(getattr(info, "participants", []) or [])
        sender_canon = session_identity.resolve(sender_jid, client)[0]
        for p in participants:
            jid = getattr(p, "JID", None) or getattr(p, "jid", None)
            if not jid:
                continue
            jid_s = safe_jid_str(jid)
            if jid_s == sender_jid or session_identity.resolve(jid_s, client)[0] == sender_canon:
                if getattr(p, "IsAdmin", False) or getattr(p, "IsSuperAdmin", False):
                    return True
                return False
    except Exception:
        pass
    return False
@register('/kick', scope='group')
def handle_kick(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"]):
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok_op, wait = antibane.allow_group_op(chat)
    if not ok_op:
        safe_reply(client, f"{config.SYM_RING} {wait}s.", message, cj)
        return
    target = _get_mention(message)
    if not target:
        safe_reply(client, "`/kick @user`", message, cj)
        return
    try:
        client.update_group_participants(_ensure_jid_obj(chat), [_ensure_jid_obj(target)], "remove")
        antibane.mark_success()
        safe_reply(client, f"{config.SYM_CHECK} {short_name(target)} keluar.", message, cj)
    except Exception as ex:
        antibane.mark_failure()
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:100]}", message, cj)
@register('/add', scope='group')
def handle_add(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"]):
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok_op, wait = antibane.allow_group_op(chat)
    if not ok_op:
        safe_reply(client, f"{config.SYM_RING} {wait}s.", message, cj)
        return
    m = re.search(r"(\+?\d{8,15})", args or "")
    if not m:
        safe_reply(client, "`/add <nomor>`", message, cj)
        return
    num = _normalize_phone_digits(re.sub(r"\D", "", m.group(1)))
    try:
        info = client.get_group_info(_ensure_jid_obj(chat))
        for p in list(getattr(info, "participants", []) or []):
            jid = getattr(p, "JID", None) or getattr(p, "jid", None)
            if jid and _digits_match(safe_jid_str(jid), num):
                safe_reply(client, f"{config.SYM_NOTE} `{num}` sudah jadi member grup.", message, cj)
                return
    except Exception as e:
        logging.warning(f"[ADD] cek member: {e}")
    try:
        client.update_group_participants(_ensure_jid_obj(chat),
                                          [build_jid(num, "s.whatsapp.net")], "add")
        antibane.mark_success()
        safe_reply(client, f"{config.SYM_CHECK} +{num}", message, cj)
    except Exception as ex:
        antibane.mark_failure()
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:100]}", message, cj)
def _group_set_announce(client, cj, ann):
    cs = safe_jid_str(cj)
    iq = random.randint(100000, 999999999)
    tag = "announcement" if ann else "not_announcement"
    xml = f'<iq type="set" xmlns="w:g2" to="{cs}" id="{iq}"><{tag}/></iq>'
    jo = _ensure_jid_obj(cj)
    for nm in ("set_group_announcement", "set_group_announce", "group_set_announce"):
        fn = getattr(client, nm, None)
        if callable(fn):
            try:
                fn(jo, ann)
                return True, nm
            except Exception:
                pass
    for nm in ("send_node", "send_iq", "sendIQ"):
        fn = getattr(client, nm, None)
        if callable(fn):
            try:
                fn(xml)
                return True, f"raw:{nm}"
            except Exception:
                pass
    gc = getattr(client, "_client", None)
    if gc:
        for nm in ("send_iq", "SendIQ"):
            fn = getattr(gc, nm, None)
            if callable(fn):
                try:
                    fn(xml)
                    return True, f"gc:{nm}"
                except Exception:
                    pass
    return False, "no_method"
@register('/open', scope='group')
def handle_open(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"] or ctx["is_buyer"]):
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok_op, wait = antibane.allow_group_op(chat)
    if not ok_op:
        safe_reply(client, f"{config.SYM_RING} {wait}s.", message, cj)
        return
    ok, info = _group_set_announce(client, chat, False)
    if ok:
        antibane.mark_success()
        safe_reply(client, f"{config.SYM_CHECK} Dibuka.", message, cj)
    else:
        antibane.mark_failure()
        safe_reply(client, f"{config.SYM_CROSS} {info}", message, cj)
@register('/close', scope='group')
def handle_close(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"] or ctx["is_buyer"]):
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok_op, wait = antibane.allow_group_op(chat)
    if not ok_op:
        safe_reply(client, f"{config.SYM_RING} {wait}s.", message, cj)
        return
    ok, info = _group_set_announce(client, chat, True)
    if ok:
        antibane.mark_success()
        safe_reply(client, f"{config.SYM_CHECK} Ditutup.", message, cj)
    else:
        antibane.mark_failure()
        safe_reply(client, f"{config.SYM_CROSS} {info}", message, cj)
@register('/everyone', scope='group')
@register('/tagall', scope='group')
def handle_everyone(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"] or ctx["is_buyer"]):
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok_op, wait = antibane.allow_group_op(chat)
    if not ok_op:
        safe_reply(client, f"{config.SYM_RING} {wait}s.", message, cj)
        return
    try:
        info = client.get_group_info(_ensure_jid_obj(chat))
        parts = list(getattr(info, "participants", []) or [])
        if not parts:
            safe_reply(client, f"{config.SYM_CROSS} Gagal.", message, cj)
            return
        jids = []
        names = []
        for p in parts:
            jid = getattr(p, "JID", None) or getattr(p, "jid", None)
            if jid:
                jids.append(_ensure_jid_obj(jid))
                names.append("@" + short_name(safe_jid_str(jid), 14))
        extra = validate_input(args or "", 500)
        mt = "\n".join(names)
        body = f"{config.SYM_STAR} *EVERYONE*\n{hline(22)}\n{mt}"
        if extra:
            body = f"{config.SYM_STAR} *EVERYONE*\n{hline(22)}\n{extra}\n\n{mt}"
        try:
            client.send_message(_ensure_jid_obj(chat), text=body, mentions=jids)
            antibane.mark_success()
        except Exception:
            safe_reply(client, body, message, cj)
    except Exception as ex:
        antibane.mark_failure()
        safe_reply(client, f"{config.SYM_CROSS} {str(ex)[:100]}", message, cj)
@register('/groupid')
def handle_groupid(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_group"]:
        safe_reply(client, config.SYM_NOTE, message, cj)
        return
    safe_reply(client, f"{config.SYM_BULLET} `{group_id_manager.get_or_create(chat)}`", message, cj)
@register('/remind')
def handle_remind(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} Grup only.", message, cj)
        return
    if not (ctx["is_owner"] or ctx["is_admin"] or ctx["is_buyer"]):
        safe_reply(client, f"{config.SYM_CROSS} Admin.", message, cj)
        return
    parts = (args or "").strip().split(None, 1)
    if len(parts) < 2:
        safe_reply(client, "`/remind <menit> <pesan>`", message, cj)
        return
    mins = validate_number(parts[0], 1, 1440)
    if not mins:
        safe_reply(client, f"{config.SYM_CROSS} 1-1440.", message, cj)
        return
    txt = validate_input(parts[1], 500)
    run_at = now_ts() + mins * 60
    def mut(d):
        d.setdefault("schedules", []).append({"chat": chat, "text": txt, "run_at": run_at})
    _shared_update(_sched_path, {"schedules": []}, mut)
    safe_reply(client, f"{config.SYM_RING} {mins}m {config.SYM_DOT} _{txt[:100]}_", message, cj)
def _check_schedules(client):
    if shutdown_event.is_set():
        return
    try:
        d = _shared_read(_sched_path, default={"schedules": []})
        n = now_ts()
        due = [x for x in d.get("schedules", []) if x.get("run_at", 0) <= n]
        if not due:
            return
        rem = [x for x in d.get("schedules", []) if x.get("run_at", 0) > n]
        _shared_update(_sched_path, {"schedules": []}, lambda dd: dd.__setitem__("schedules", rem))
        for x in due:
            if shutdown_event.is_set():
                break
            try:
                safe_send_text(client, x["chat"], f"{config.SYM_RING} *REMINDER*\n{hline(22)}\n_{x['text']}_")
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"[SCHED] {e}")
def setup_scheduler(client, scheduler):
    scheduler.add_job(lambda: _check_schedules(client), trigger=CronTrigger(second="*/30", timezone=config.WIB), id="sched_check", replace_existing=True)

_GROUP_STATE_PATH=Path(config.SHARED_DIR)/'group_runtime.json'
def _gstate(chat):
    d=_shared_read(_GROUP_STATE_PATH,default={'groups':{}}); return d.setdefault('groups',{}).setdefault(chat,{'settings':{},'warnings':{},'welcome':'','goodbye':'','rules':'','polls':[],'messages':0})
def _save_gstate(chat,g): _shared_update(_GROUP_STATE_PATH,{'groups':{}},lambda d:d.setdefault('groups',{}).__setitem__(chat,g))
def _require_admin(client,message,cj,chat,ctx):
    if not ctx.get('is_group'): safe_reply(client,'👥 Group only.',message,cj); return False
    if not (ctx.get('is_owner') or ctx.get('is_admin') or ctx.get('is_buyer')): safe_reply(client,'🛡️ Admin/MO only.',message,cj); return False
    return True

def _delete_replied(client,message,cj):
    info=getattr(message,'Info',None); src=getattr(info,'MessageSource',None); mid=getattr(info,'ID',None)
    chat=getattr(src,'Chat',None) or cj; sender=getattr(src,'Sender',None)
    fn=getattr(client,'revoke_message',None)
    if callable(fn) and mid is not None and sender is not None:
        try: fn(_ensure_jid_obj(chat),_ensure_jid_obj(sender),str(mid)); return True
        except Exception: pass
    for nm in ('delete_message','delete','send_delete','delete_for_everyone'):
        fn=getattr(client,nm,None)
        if callable(fn):
            for args in ((chat,mid),(mid,),(getattr(message,'Info',None),)):
                try: fn(*args); return True
                except Exception: pass
    return False

def _r2_group_runner(client,message,cj,chat,sender,args,ctx,spec):
    op=spec['operation']
    if op in ('kick','add','del','open','close','everyone','tagall','remind'):
        if op=='del':
            if not _require_admin(client,message,cj,chat,ctx): return
            ok=_delete_replied(client,message,cj); safe_reply(client,'🗑️ Pesan dihapus.' if ok else '🗑️ API delete tidak tersedia pada client.',message,cj); return
        if op=='kick': return handle_kick(client,message,cj,chat,sender,args,ctx)
        if op=='add': return handle_add(client,message,cj,chat,sender,args,ctx)
        if op=='open': return handle_open(client,message,cj,chat,sender,args,ctx)
        if op=='close': return handle_close(client,message,cj,chat,sender,args,ctx)
        if op in ('everyone','tagall'): return handle_everyone(client,message,cj,chat,sender,args,ctx)
        if op=='remind': return handle_remind(client,message,cj,chat,sender,args,ctx)
    if not _require_admin(client,message,cj,chat,ctx) and op not in ('groupid','ginfo','members','stats','activity','rules','pin','groupconfig','adminlist','linkinfo'): return
    g=_gstate(chat)
    if op=='groupid': return handle_groupid(client,message,cj,chat,sender,args,ctx)
    if op=='ginfo': safe_reply(client,f"👥 Group `{chat}`\nGID `{group_id_manager.get_or_create(chat)}`",message,cj); return
    if op=='members':
        try: n=len(getattr(client.get_group_info(_ensure_jid_obj(chat)),'participants',[]) or [])
        except Exception: n=0
        safe_reply(client,f'👥 Members: *{n}*',message,cj); return
    if op=='welcome':
        g['welcome']=validate_input(args,500); _save_gstate(chat,g); safe_reply(client,f'👋 Welcome: `{g["welcome"]}`',message,cj); return
    if op=='goodbye': g['goodbye']=validate_input(args,500); _save_gstate(chat,g); safe_reply(client,f'👋 Goodbye: `{g["goodbye"]}`',message,cj); return
    if op=='rules':
        if args: g['rules']=validate_input(args,1000); _save_gstate(chat,g)
        safe_reply(client,f'📜 Rules:\n{g.get("rules") or "Belum diatur."}',message,cj); return
    if op=='announce':
        if not args: safe_reply(client,'/announce <pesan>',message,cj); return
        safe_send_text(client,chat,f'📢 *ANNOUNCEMENT*\n{args[:1000]}'); safe_reply(client,'✅ Sent.',message,cj); return
    if op=='poll':
        opts=[x.strip() for x in args.split('|') if x.strip()]
        if len(opts)<2: safe_reply(client,'/poll pertanyaan | opsi1 | opsi2',message,cj); return
        g['polls'].append({'q':opts[0],'options':opts[1:8],'votes':{}}); _save_gstate(chat,g); safe_send_text(client,chat,'📊 *POLL*\n'+opts[0]+'\n'+'\n'.join(f'{i+1}. {x}' for i,x in enumerate(opts[1:8]))); return
    if op=='stats': safe_reply(client,f'📊 Messages tracked: *{g.get("messages",0)}* · Polls *{len(g.get("polls",[]))}*',message,cj); return
    if op=='activity': safe_reply(client,'📈 Activity dihitung dari event/message hooks.',message,cj); return
    if op=='cleanup':
        g['polls']=g.get('polls',[])[-10:]; _save_gstate(chat,g); safe_reply(client,'🧹 Runtime group cache dibersihkan.',message,cj); return
    if op=='pin':
        info=getattr(message,'Info',None); src=getattr(info,'MessageSource',None); mid=getattr(info,'ID',None)
        fn=getattr(client,'pin_message',None)
        if not callable(fn) or mid is None or src is None: safe_reply(client,'📌 pin_message tidak tersedia.',message,cj); return
        try: fn(_ensure_jid_obj(chat),_ensure_jid_obj(getattr(src,'Sender',sender)),str(mid),86400); safe_reply(client,'📌 Pesan dipin 24 jam.',message,cj)
        except Exception as ex: safe_reply(client,f'📌 Gagal pin: {str(ex)[:100]}',message,cj)
        return
    if op=='groupconfig': safe_reply(client,'⚙️ '+json.dumps(g.get('settings',{}),ensure_ascii=False)[:1500],message,cj); return
    if op=='adminlist':
        try: info=client.get_group_info(_ensure_jid_obj(chat)); rows=[safe_jid_str(getattr(x,'JID',None) or getattr(x,'jid',None)) for x in getattr(info,'participants',[]) or [] if getattr(x,'IsAdmin',False) or getattr(x,'IsSuperAdmin',False)]
        except Exception: rows=[]
        safe_reply(client,'🛡️ Admin:\n'+'\n'.join(f'▸ {x}' for x in rows[:30]),message,cj); return
    if op=='linkinfo': safe_reply(client,f'🔗 Group JID `{chat}`',message,cj); return

def _r2_moderation_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not _require_admin(client,message,cj,chat,ctx) and spec['operation'] not in ('scan','status','audit','modlog','ratelimit'): return
    g=_gstate(chat); op=spec['operation']
    if op in ('antilink','antispam','antibadword','antisticker','antistatus','antidelete','antiedit','mute','unmute','lock','unlock','ratelimit'):
        val=(args or '').strip().lower(); enabled=False if val in ('off','0','disable') else True
        if op in ('mute','unmute'): enabled=(op=='mute')
        g['settings'][op]=enabled; _save_gstate(chat,g); safe_reply(client,f'🛡️ `{op}` = *{"ON" if enabled else "OFF"}*',message,cj); return
    if op=='warn':
        target=_get_mention(message) or (args or '').strip();
        if not target: safe_reply(client,'Reply/tag target.',message,cj); return
        g['warnings'][target]=g['warnings'].get(target,0)+1; _save_gstate(chat,g); n=g['warnings'][target]; safe_reply(client,f'⚠️ Warn `{target}` = *{n}*',message,cj); return
    if op=='warnremove':
        target=_get_mention(message) or args.strip(); g['warnings'].pop(target,None); _save_gstate(chat,g); safe_reply(client,'✅ Warn dihapus.',message,cj); return
    if op=='warnlist': safe_reply(client,'⚠️\n'+'\n'.join(f'▸ {k}: {v}' for k,v in g['warnings'].items()) or 'Kosong.',message,cj); return
    if op in ('whitelist','blacklist'):
        key='whitelist' if op=='whitelist' else 'blacklist'; g['settings'].setdefault(key,[]); val=(args or '').strip();
        if val and val not in g['settings'][key]: g['settings'][key].append(val)
        _save_gstate(chat,g); safe_reply(client,f'🛡️ {key}: '+', '.join(g['settings'][key][-20:]),message,cj); return
    if op=='scan': safe_reply(client,'🔎 Security scan: settings aktif · warnings '+str(len(g['warnings'])),message,cj); return
    if op=='audit': safe_reply(client,'📜 Audit state tersimpan di group_runtime.json.',message,cj); return
    if op=='modlog': safe_reply(client,'📜 Modlog tersedia melalui `/activity`.',message,cj); return
    if op=='status': safe_reply(client,'🛡️ '+json.dumps(g['settings'],ensure_ascii=False),message,cj); return

def _r2_group_dispatch(client,message,cj,chat,sender,args,ctx,spec):
    return _r2_moderation_runner(client,message,cj,chat,sender,args,ctx,spec) if spec['category']=='moderation' else _r2_group_runner(client,message,cj,chat,sender,args,ctx,spec)

register_feature_specs('group',_r2_group_dispatch,category='group')
register_feature_specs('group',_r2_group_dispatch,category='moderation')
