from handlers import register, register_feature_specs
from handlers.auth import require_login
import config
from datetime import datetime, timedelta
import logging
import os
import random
import time
from pathlib import Path
from core.utils import box_title, hline, now_ts, short_name, shutdown_event, validate_number
from core.storage import _shared_read, _shared_update, user_store, buyer_store, atomic_json_read, atomic_json_write
from core.economy import add_tokens, get_cash
from apscheduler.triggers.cron import CronTrigger
from core.send import _ensure_jid_obj, safe_reply
from core.economy import add_tokens
from core.send import _ensure_jid_obj, safe_send_text
@register('/event')
def handle_event(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    sub = parts[0].lower() if parts else "list"
    if sub == "list":
        active = event_manager.list_active()
        if not active:
            safe_reply(client, f"{config.SYM_NOTE} Tidak ada event.", message, cj)
            return
        lines = [f"{box_title('EVENT AKTIF', 22)}"]
        for eid, ev in active:
            left = max(0, int(ev.get("end", 0) - now_ts()))
            h, r = divmod(left, 3600)
            m, _ = divmod(r, 60)
            lines.append(f"{config.SYM_BULLET} *{eid}* {config.SYM_DOT} {config.EVENT_TYPES.get(ev.get('type'), {}).get('name', '?')}")
            lines.append(f"  {config.SYM_DOT} Target `{ev.get('target', 0)}` {config.SYM_DOT} Reward {ev.get('reward_tokens', 0)} {config.SYM_DOT} {h}j {m}m")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub == "progress":
        active = event_manager.list_active()
        if not active:
            safe_reply(client, f"{config.SYM_NOTE} Tidak ada.", message, cj)
            return
        lines = [f"{box_title('PROGRESS', 22)}"]
        for eid, ev in active:
            p = event_manager.get_progress(sender, eid)
            ic = config.SYM_CHECK if sender in ev.get("claimed_by", []) else config.SYM_DOT
            lines.append(f"{ic} *{eid}*: {p}/{ev.get('target', 0)}")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub == "claim":
        for eid, ev in event_manager.list_active():
            p = event_manager.get_progress(sender, eid)
            if p >= ev.get("target", 0) and sender not in ev.get("claimed_by", []):
                ok, msg = event_manager.claim(sender, eid)
                safe_reply(client, msg, message, cj)
                return
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada klaim.", message, cj)
        return
    if sub == "leaderboard":
        active = event_manager.list_active()
        if not active:
            safe_reply(client, f"{config.SYM_NOTE} Tidak ada.", message, cj)
            return
        eid, ev = active[0]
        prog = ev.get("progress", {})
        ranked = sorted(prog.items(), key=lambda kv: -kv[1])[:10]
        lines = [f"{box_title('LEADERBOARD ' + eid, 22)}"]
        for i, (uid, pp) in enumerate(ranked, 1):
            nm = user_store.get_profile(uid).get("name") or short_name(uid, 12)
            lines.append(f"`{i}.` *{nm}* {config.SYM_DOT} {pp}")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    is_mini = buyer_store.is_buyer(sender)
    if sub == "create":
        if not (ctx["is_owner"] or is_mini):
            safe_reply(client, config.SYM_CROSS, message, cj)
            return
        if len(parts) < 6:
            safe_reply(client, "`/event create <id> <tipe> <target> <jam> <reward>`", message, cj)
            return
        eid = parts[1][:32]
        et = parts[2].lower()
        tg = validate_number(parts[3], 1, 10**9)
        hr = validate_number(parts[4], 1, 168)
        rw = validate_number(parts[5], 1, 50000)
        if not all([tg, hr, rw]):
            safe_reply(client, f"{config.SYM_CROSS} Angka invalid.", message, cj)
            return
        ok, msg = event_manager.create(eid, et, tg, hr, rw, sender)
        safe_reply(client, msg, message, cj)
        return
    if sub == "end":
        if not (ctx["is_owner"] or is_mini):
            return
        if len(parts) < 2:
            return
        ok = event_manager.end(parts[1])
        safe_reply(client, f"{config.SYM_CHECK} Ended." if ok else config.SYM_CROSS, message, cj)
        return
    if sub == "delete":
        if not ctx["is_owner"]:
            return
        event_manager.delete(parts[1])
        safe_reply(client, config.SYM_CHECK, message, cj)
        return
    safe_reply(client, f"{config.SYM_BULLET} `/event list|progress|claim|leaderboard`", message, cj)
@register('/claimbox')
def handle_claimbox(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} Grup only.", message, cj)
        return
    ok, msg = airdrop.claim(sender, chat)
    safe_reply(client, msg, message, cj)
def setup_scheduler(client, scheduler):
    scheduler.add_job(lambda: _airdrop_cb(client), trigger=CronTrigger(minute="*/5", timezone=config.WIB), id="airdrop_check", replace_existing=True)
class EventManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "events.json")
    def create(self, eid, etype, target, dur_h, reward, host):
        if etype not in config.EVENT_TYPES:
            return False, "Tipe invalid"
        active = self.list_active()
        if len([e for _, e in active if e.get("host") == host]) >= 3:
            return False, "Max 3 event per host"
        if dur_h > 168:
            return False, "Max 7 hari"
        if reward > 50000:
            return False, "Max 50000"
        r = {"ok": False, "msg": ""}
        def mut(d):
            ev = d.setdefault("events", {})
            if eid in ev and ev[eid].get("active"):
                r["msg"] = "Sudah aktif."
                return
            n = now_ts()
            ev[eid] = {"id": eid, "type": etype, "target": target, "reward_tokens": reward,
                       "host": host, "start": n, "end": n + dur_h * 3600,
                       "active": True, "claimed_by": [], "progress": {}}
            r["ok"] = True
            r["msg"] = f"{config.SYM_CHECK} Event *{eid}*\n{config.SYM_BULLET} Target: {target} {config.SYM_DOT} Reward: {reward}"
        _shared_update(self._p(), {"events": {}}, mut)
        return r["ok"], r["msg"]
    def get(self, eid):
        return _shared_read(self._p(), default={"events": {}}).get("events", {}).get(eid)
    def list_active(self):
        d = _shared_read(self._p(), default={"events": {}})
        n = now_ts()
        return [(eid, ev) for eid, ev in d.get("events", {}).items()
                if ev.get("active") and n <= ev.get("end", 0)]
    def end(self, eid):
        r = {"ok": False}
        def mut(d):
            ev = d.setdefault("events", {}).get(eid)
            if not ev:
                return
            ev["active"] = False
            r["ok"] = True
        _shared_update(self._p(), {"events": {}}, mut)
        return r["ok"]
    def delete(self, eid):
        def mut(d):
            d.setdefault("events", {}).pop(eid, None)
        _shared_update(self._p(), {"events": {}}, mut)
        return True
    def progress(self, uid, etype, amt=1):
        d = _shared_read(self._p(), default={"events": {}})
        n = now_ts()
        for eid, ev in d.get("events", {}).items():
            if not ev.get("active") or n > ev.get("end", 0):
                continue
            if ev.get("type") != etype:
                continue
            if uid in ev.get("claimed_by", []):
                continue
            def mut(dd):
                e = dd.setdefault("events", {}).get(eid)
                if not e:
                    return
                p = e.setdefault("progress", {})
                p[uid] = p.get(uid, 0) + amt
            _shared_update(self._p(), {"events": {}}, mut)
    def get_progress(self, uid, eid):
        ev = self.get(eid)
        return ev.get("progress", {}).get(uid, 0) if ev else 0
    def claim(self, uid, eid):
        r = {"ok": False, "msg": "", "reward": 0}
        def mut(d):
            ev = d.setdefault("events", {}).get(eid)
            if not ev:
                r["msg"] = "Tidak ada."
                return
            if not ev.get("active"):
                r["msg"] = "Tidak aktif."
                return
            if now_ts() > ev.get("end", 0):
                ev["active"] = False
                r["msg"] = "Berakhir."
                return
            prog = ev.get("progress", {}).get(uid, 0)
            if prog < ev.get("target", 0):
                r["msg"] = f"Progress {prog}/{ev.get('target', 0)}"
                return
            if uid in ev.get("claimed_by", []):
                r["msg"] = "Sudah klaim."
                return
            ev.setdefault("claimed_by", []).append(uid)
            r["ok"] = True
            r["reward"] = ev.get("reward_tokens", 0)
            r["msg"] = f"{config.SYM_CHECK} +{r['reward']} token"
        _shared_update(self._p(), {"events": {}}, mut)
        if r["ok"]:
            add_tokens(uid, r["reward"])
        return r["ok"], r["msg"]
class AirdropManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "airdrop.json")
    def _ap(self):
        return os.path.join(config.SHARED_DIR, "airdrop_active.json")
    def get_config(self):
        return _shared_read(self._p(), default={"enabled": True, "hours": [8, 14, 20]})
    def set_hours(self, hours):
        def mut(d):
            d["hours"] = hours
            d["enabled"] = True
        _shared_update(self._p(), {"enabled": True, "hours": []}, mut)
    def set_enabled(self, en):
        def mut(d):
            d["enabled"] = en
        _shared_update(self._p(), {"enabled": True, "hours": []}, mut)
    def get_active(self, cj):
        return _shared_read(self._ap(), default={"active": {}}).get("active", {}).get(cj)
    def trigger_now(self, groups, client):
        if not groups:
            return 0
        tr = random.random()
        if tr < 0.40:
            tier, rng = "common", (100, 500)
        elif tr < 0.70:
            tier, rng = "rare", (500, 2000)
        elif tr < 0.90:
            tier, rng = "epic", (2000, 8000)
        elif tr < 0.99:
            tier, rng = "legend", (8000, 30000)
        else:
            tier, rng = "mythic", (50000, 50000)
        reward = random.randint(*rng)
        n = now_ts()
        exp = n + 60
        def mut(d):
            a = d.setdefault("active", {})
            for g in groups[:20]:
                a[g] = {"tier": tier, "reward": reward, "expires": exp, "created": n}
        _shared_update(self._ap(), {"active": {}}, mut)
        sent = 0
        for g in groups[:20]:
            if shutdown_event.is_set():
                break
            try:
                body = (f"{config.SYM_STAR} *AIRDROP JATUH* {config.SYM_STAR}\n"
                        f"{hline(20)}\n"
                        f"{config.SYM_DIAMOND} Tier: *{tier.upper()}*\n"
                        f"{config.SYM_RING} 60 detik\n"
                        f"{config.SYM_ARROW} `/claimbox`")
                client.send_message(_ensure_jid_obj(g), text=body)
                sent += 1
                time.sleep(random.uniform(2.0, 4.0))
            except Exception as e:
                logging.warning(f"[AIRDROP] {g}: {e}")
        return sent
    def claim(self, uid, cj):
        d = _shared_read(self._ap(), default={"active": {}})
        act = d.get("active", {}).get(cj)
        if not act:
            return False, "Tidak ada airdrop."
        if now_ts() > act.get("expires", 0):
            def mut(dd):
                dd.setdefault("active", {}).pop(cj, None)
            _shared_update(self._ap(), {"active": {}}, mut)
            return False, "Expired."
        reward = act.get("reward", 0)
        tier = act.get("tier", "common")
        def mut(dd):
            dd.setdefault("active", {}).pop(cj, None)
        _shared_update(self._ap(), {"active": {}}, mut)
        add_tokens(uid, reward, source="airdrop")
        return True, f"{config.SYM_STAR} CLAIMED {config.SYM_ARROW} {tier.upper()} {config.SYM_DOT} +{reward}"
def _airdrop_cb(client):
    if shutdown_event.is_set():
        return
    try:
        cfg = airdrop.get_config()
        if not cfg.get("enabled"):
            return
        h = datetime.now(config.WIB).hour
        if h not in cfg.get("hours", []):
            return
        buyers = buyer_store.list_active()
        groups = []
        for uid, info in buyers:
            for g in info.get("bound_groups", []):
                if g not in groups:
                    groups.append(g)
        if groups:
            airdrop.trigger_now(groups, client)
    except Exception as e:
        logging.warning(f"[AIRDROP CB] {e}")
config.EVENT_TYPES = config.EVENT_TYPES
airdrop = AirdropManager()
event_manager = EventManager()

_R2_QUEST_PATH=Path(config.SHARED_DIR)/"r2_quests.json"

def _quest_state(uid):
    return atomic_json_read(Path(config.USER_DIR)/uid/"quests_r2.json",default={"active":[],"done":[]})
def _save_quest(uid,d):
    path=Path(config.USER_DIR)/uid/"quests_r2.json"; path.parent.mkdir(parents=True,exist_ok=True); atomic_json_write(path,d)

def _quest_state(uid): return atomic_json_read(Path(config.USER_DIR)/uid/"quests_r2.json",default={"active":[],"done":[],"streak":0})
def _save_quest(uid,d): atomic_json_write(Path(config.USER_DIR)/uid/"quests_r2.json",d)
def _r2_quest_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    q=_quest_state(sender);op=spec['operation'];templates={"dailyquest":("Daily activity",3),"weeklyquest":("Weekly activity",10),"economyquest":("Earn cash",500),"gamequest":("Win games",2),"huntquest":("Finish hunts",2),"collectionquest":("Collect items",3),"bounty":("Defeat targets",1),"mission":("Complete actions",5),"contract":("Contract actions",5),"objective":("Complete objectives",3),"questboard":("Board challenge",5)}
    if op in ('quest','quests','questinfo','questlog','objective','contract','questboard'):
        if not q['active']: q['active']=[{"id":"daily","text":"Daily activity","target":3,"progress":0,"reward":50}];_save_quest(sender,q)
        safe_reply(client,f"{box_title('QUEST',28)}\n"+"\n".join(f"▸ {x['text']} {x['progress']}/{x['target']} · +{x['reward']}" for x in q['active'])+f"\n{box_bottom(28)}",message,cj);return
    if op in templates:
        name,target=templates[op]; found=next((x for x in q['active'] if x['id']==op),None)
        if not found:found={"id":op,"text":name,"target":target,"progress":0,"reward":max(20,target*10)};q['active'].append(found)
        found['progress']=min(target,found['progress']+1);_save_quest(sender,q);safe_reply(client,f"📜 {name}: {found['progress']}/{target}",message,cj);return
    if op=='claimquest':
        done=next((x for x in q['active'] if x['progress']>=x['target']),None)
        if not done:safe_reply(client,'📜 Belum siap.',message,cj);return
        q['active'].remove(done);q['done'].append(done['id']);q['streak']=q.get('streak',0)+1;_save_quest(sender,q);add_tokens(sender,done['reward'],'quest');safe_reply(client,f"✅ Quest +{done['reward']} token.",message,cj);return
    if op=='questprogress':safe_reply(client,f"📜 Active {len(q['active'])} · Done {len(q['done'])}",message,cj);return
    if op=='questreset':q['active']=[];_save_quest(sender,q);safe_reply(client,'📜 Quest reset.',message,cj);return
    if op=='questreward':
        ready=[x for x in q['active'] if x['progress']>=x['target']];safe_reply(client,"🎁 Ready rewards: "+", ".join(str(x['reward']) for x in ready) if ready else 'Tidak ada reward siap.',message,cj);return
    if op=='queststreak':safe_reply(client,f"🔥 Quest streak *{q.get('streak',0)}*",message,cj);return

def _r2_event_users(): return atomic_json_read(Path(config.SHARED_DIR)/"r2_event_users.json",default={"users":{}})
def _save_event_users(d): atomic_json_write(Path(config.SHARED_DIR)/"r2_event_users.json",d)
def _r2_event_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec['operation'];a=(args or '').strip();d=_r2_event_users();u=d.setdefault('users',{}).setdefault(sender,{"joined":[],'claimed':{},'special':{}})
    if op in ('event','events','eventstatus','worldevent'):
        rows=event_manager.list_active();safe_reply(client,"🎁 *ACTIVE EVENTS*\n"+"\n".join(f"▸ {eid} · {e.get('type')} · {e.get('progress',{}).get(sender,0)}/{e.get('target',0)}" for eid,e in rows[:12]) if rows else '🎁 Tidak ada event aktif.',message,cj);return
    if op=='eventhistory':
        raw=atomic_json_read(Path(config.SHARED_DIR)/'events.json',default={'events':{}}).get('events',{});safe_reply(client,'📜\n'+'\n'.join(f"▸ {k} · {v.get('type')} · {'ON' if v.get('active') else 'OFF'}" for k,v in list(raw.items())[-15:]) or 'Kosong.',message,cj);return
    if op=='airdrop':
        if not chat:safe_reply(client,'🎁 Airdrop membutuhkan grup.',message,cj);return
        n=airdrop.trigger_now([chat],client);safe_reply(client,f'🎁 Airdrop triggered to {n} group(s).',message,cj);return
    if op=='claimbox': return handle_claimbox(client,message,cj,chat,sender,args,ctx)
    if op=='claimraid':
        eid=a or 'raid';ok,msg=event_manager.claim(sender,eid);safe_reply(client,msg if msg else ('✅ Claimed' if ok else '❌ Not ready'),message,cj);return
    if op=='eventjoin':
        rows=event_manager.list_active();eid=a or (rows[0][0] if rows else '')
        if not eid:safe_reply(client,'🎁 Tidak ada event.',message,cj);return
        if eid not in u['joined']:u['joined'].append(eid);_save_event_users(d);event_manager.progress(sender,event_manager.get(eid).get('type',''),1);safe_reply(client,f'✅ Joined `{eid}`.',message,cj)
        else:safe_reply(client,'Sudah join.',message,cj)
        return
    if op=='eventleave':
        eid=a or (u['joined'][-1] if u['joined'] else '');u['joined']=[x for x in u['joined'] if x!=eid];_save_event_users(d);safe_reply(client,f'👋 Leave `{eid}`.',message,cj);return
    if op=='eventreward':
        eid=a or (u['joined'][-1] if u['joined'] else '')
        ok,msg=event_manager.claim(sender,eid) if eid else (False,'Tidak ada event')
        safe_reply(client,msg,message,cj);return
    if op=='eventleaderboard':
        eid=a or (event_manager.list_active()[0][0] if event_manager.list_active() else '')
        ev=event_manager.get(eid) if eid else None;prog=ev.get('progress',{}) if ev else {};rows=sorted(prog.items(),key=lambda kv:kv[1],reverse=True)[:10];safe_reply(client,'🏆\n'+'\n'.join(f'{i+1}. {uid} · {n}' for i,(uid,n) in enumerate(rows)) or 'Kosong.',message,cj);return
    specials=('seasonal','dailyfest','jackpot','meteor','chest','invasion','lottery_event','festival')
    if op in specials:
        now=datetime.now(config.WIB).strftime('%Y-%m-%d');key=f'{op}:{now}';seen=u['special'].get(key)
        if seen:safe_reply(client,f'🎁 {op}: sudah diambil hari ini.',message,cj);return
        base={'seasonal':100,'dailyfest':120,'jackpot':500,'meteor':250,'chest':150,'invasion':300,'lottery_event':400,'festival':200}[op];reward=base+random.randint(0,base);u['special'][key]=now;_save_event_users(d);add_tokens(sender,reward,'event');safe_reply(client,f'🎉 {op.upper()} +{reward} token.',message,cj);return
register_feature_specs("event", _r2_quest_runner, category="quest")
register_feature_specs("event", _r2_event_runner, category="event")
