from handlers import register, register_feature_specs
from handlers.auth import require_login
from handlers.fishing import handle_fishing_router, handle_gathering_router
import config
from config import DAILY_MAX, DAILY_MIN, MARRY_COST, MARRY_DIVORCE_COST, ROB_MAX_STEAL_PCT, ROB_MIN_STEAL_PCT, WORK_COOLDOWN, WORK_MAX, WORK_MIN
from datetime import datetime, timedelta
import json
import random
import time
from core.utils import box_bottom, box_title, log_activity, now_ts, validate_number
from core.storage import user_store
from core.economy import achievement_manager, add_tokens, deduct_tokens, get_cash, get_luck, get_rank_display, get_tokens, miner_level_for, miner_manager, stock_market, add_cash, deduct_cash
from core.send import safe_reply
from core.economy import achievement_manager
from core.storage import user_store, buyer_store, event_manager, atomic_json_read, atomic_json_write
@register('/balance')
def handle_balance(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    name = user_store.get_profile(sender).get("name") or "Guest"
    safe_reply(client,
        f"{box_title('WALLET', 22)}\n"
        f"{config.SYM_BULLET} {name}\n"
        f"{config.SYM_BULLET} Token: *{e.get('tokens', 0)}/{config.TOKEN_CAP}*\n"
        f"{config.SYM_BULLET} Cash: *{e.get('cash', 0)}*\n"
        f"{config.SYM_BULLET} Luck: +{int(get_luck(sender) * 100)}%\n"
        f"{box_bottom(22)}",
        message, cj)
@register('/daily')
def handle_daily(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    n = now_ts()
    if n - e.get("daily_last", 0) < 86400 and not ctx["is_owner"]:
        left = int(86400 - (n - e.get("daily_last", 0)))
        h, m = divmod(left // 60, 60)
        safe_reply(client, f"{config.SYM_RING} {h}j {m}m.", message, cj)
        return
    last = e.get("daily_last", 0)
    streak = e.get("daily_streak", 0)
    streak = streak + 1 if last > 0 and n - last < 86400 * 2 else 1
    def mut(ee):
        ee["daily_last"] = n
        ee["daily_streak"] = streak
    user_store.update_economy(sender, mut)
    amt = random.randint(DAILY_MIN, DAILY_MAX) + min(streak, 7) * 5
    add_tokens(sender, amt, source="daily")
    event_manager.progress(sender, "daily", 1)
    safe_reply(client, f"{config.SYM_STAR} Streak ×{streak} {config.SYM_DOT} +{amt}", message, cj)
@register('/work')
def handle_work(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} Grup only.", message, cj)
        return
    e = user_store.get_economy(sender)
    n = now_ts()
    if n - e.get("work_last", 0) < WORK_COOLDOWN and not ctx["is_owner"]:
        left = int(WORK_COOLDOWN - (n - e.get("work_last", 0)))
        m, s = divmod(left, 60)
        safe_reply(client, f"{config.SYM_RING} {m}m {s}s.", message, cj)
        return
    def mut(ee):
        ee["work_last"] = n
    user_store.update_economy(sender, mut)
    amt = random.randint(WORK_MIN, WORK_MAX)
    add_tokens(sender, amt, source="work")
    jobs = ["barista", "kurir", "programmer", "guru", "youtuber"]
    safe_reply(client, f"{config.SYM_BULLET} {random.choice(jobs)} {config.SYM_DOT} +{amt}", message, cj)
@register('/rob')
def handle_rob(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} PM only.", message, cj)
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, "`/rob <user>`", message, cj)
        return
    name = parts[0]
    target = user_store.find_by_name(name)
    if not target or not user_store.user_exists(target):
        safe_reply(client, f"{config.SYM_CROSS} `{name}` tidak ada.", message, cj)
        return
    if target == sender:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    me = user_store.get_economy(sender)
    mt = me.get("tokens", 0)
    if mt < 100:
        safe_reply(client, f"{config.SYM_CROSS} Butuh 100 token.", message, cj)
        return
    if now_ts() - me.get("rob_last", 0) < config.ROB_COOLDOWN and not ctx["is_owner"]:
        left = int(config.ROB_COOLDOWN - (now_ts() - me.get("rob_last", 0)))
        m, s = divmod(left, 60)
        safe_reply(client, f"{config.SYM_RING} {m}m {s}s.", message, cj)
        return
    tgt = user_store.get_economy(target)
    tt = tgt.get("tokens", 0)
    if tt < 50:
        safe_reply(client, f"{config.SYM_CROSS} Target miskin.", message, cj)
        return
    if random.random() < min(0.95, config.ROB_SUCCESS_RATE + get_luck(sender)):
        stolen = max(1, int(tt * random.uniform(ROB_MIN_STEAL_PCT, ROB_MAX_STEAL_PCT)))
        deduct_tokens(target, stolen, source="rob_target")
        add_tokens(sender, stolen, source="rob_win")
        def mut(ee):
            ee["rob_last"] = now_ts()
        user_store.update_economy(sender, mut)
        log_activity(sender, "rob", {"target": target, "amount": stolen, "result": "win"})
        safe_reply(client, f"{config.SYM_CHECK} +{stolen}", message, cj)
    else:
        def mut(ee):
            ee["rob_last"] = now_ts()
        user_store.update_economy(sender, mut)
        fine = max(1, int(mt * config.ROB_FAIL_FINE))
        deduct_tokens(sender, fine, source="rob_fail")
        add_tokens(target, fine, source="rob_defend")
        log_activity(sender, "rob", {"target": target, "amount": fine, "result": "fail"})
        safe_reply(client, f"{config.SYM_CROSS} -{fine}", message, cj)
@register('/dailybox')
def handle_dailybox(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    n = now_ts()
    if n - e.get("dailybox_last", 0) < 86400 and not ctx["is_owner"]:
        left = int(86400 - (n - e.get("dailybox_last", 0)))
        h, m = divmod(left // 60, 60)
        safe_reply(client, f"{config.SYM_RING} {h}j {m}m.", message, cj)
        return
    def mut(ee):
        ee["dailybox_last"] = n
    user_store.update_economy(sender, mut)
    luck = get_luck(sender)
    roll = max(0.0, random.random() - luck)
    amt = random.randint(30, 100) if roll < 0.5 else (random.randint(100, 300) if roll < 0.8 else random.randint(300, 800))
    add_tokens(sender, amt, source="dailybox")
    safe_reply(client, f"{config.SYM_NOTE} +{amt}", message, cj)
@register('/gift')
def handle_gift(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    if len(parts) < 3:
        safe_reply(client, "`/gift token <u> <n>` atau `/gift item <u> <key> <qty>`", message, cj)
        return
    kind = parts[0].lower()
    name = parts[1]
    target = user_store.find_by_name(name)
    if not target or not user_store.user_exists(target):
        safe_reply(client, f"{config.SYM_CROSS} `{name}` tidak ada.", message, cj)
        return
    if target == sender:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    if kind == "token":
        amt = validate_number(parts[2], 1, 2500)
        if not amt:
            safe_reply(client, f"{config.SYM_CROSS} 1-2500.", message, cj)
            return
        tax = int(amt * 0.05)
        ok, rem = deduct_tokens(sender, amt + tax, source="gift")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
            return
        add_tokens(target, amt, source="gift_received")
        event_manager.progress(sender, "gift", 1)
        log_activity(sender, "gift_send", {"to": target, "amount": amt, "kind": "token"})
        safe_reply(client, f"{config.SYM_CHECK} {name} +{amt}", message, cj)
        return
    if kind == "item":
        if len(parts) < 4:
            safe_reply(client, "`/gift item <u> <key> <qty>`", message, cj)
            return
        key = parts[2]
        qty = validate_number(parts[3], 1, 1000)
        if not qty:
            safe_reply(client, f"{config.SYM_CROSS} Qty 1-1000.", message, cj)
            return
        have = user_store.item_count(sender, key, 1)
        if have < qty:
            safe_reply(client, f"{config.SYM_CROSS} Punya {have}.", message, cj)
            return
        user_store.remove_item(sender, key, qty, 1, source="gift")
        user_store.add_item(target, key, qty=qty, level=1, source="gift_received")
        event_manager.progress(sender, "gift", 1)
        log_activity(sender, "gift_send", {"to": target, "key": key, "qty": qty, "kind": "item"})
        safe_reply(client, f"{config.SYM_CHECK} {name} ×{qty} {key}", message, cj)
@register('/marry')
def handle_marry(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if ctx["is_group"]:
        safe_reply(client, f"{config.SYM_NOTE} PM only.", message, cj)
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, "`/marry <user>`", message, cj)
        return
    name = parts[0]
    target = user_store.find_by_name(name)
    if not target or not user_store.user_exists(target):
        safe_reply(client, f"{config.SYM_CROSS} Tidak ada.", message, cj)
        return
    if target == sender:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    p = user_store.get_profile(sender)
    if p.get("married_to"):
        safe_reply(client, f"{config.SYM_CROSS} Sudah menikah.", message, cj)
        return
    tp = user_store.get_profile(target)
    if tp.get("married_to"):
        safe_reply(client, f"{config.SYM_CROSS} Target menikah.", message, cj)
        return
    ok, rem = deduct_tokens(sender, MARRY_COST, source="marry")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Butuh {MARRY_COST}.", message, cj)
        return
    def m1(pp):
        pp["married_to"] = target
    def m2(pp):
        pp["married_to"] = sender
    user_store.update_profile(sender, m1)
    user_store.update_profile(target, m2)
    achievement_manager.grant(sender, "marry")
    log_activity(sender, "marry", {"to": target})
    safe_reply(client, f"{config.SYM_STAR} Married! {name}", message, cj)
@register('/divorce')
def handle_divorce(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    p = user_store.get_profile(sender)
    partner = p.get("married_to")
    if not partner:
        safe_reply(client, f"{config.SYM_CROSS} Belum menikah.", message, cj)
        return
    ok, rem = deduct_tokens(sender, MARRY_DIVORCE_COST, source="divorce")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Butuh {MARRY_DIVORCE_COST}.", message, cj)
        return
    def m1(pp):
        pp["married_to"] = None
    def m2(pp):
        pp["married_to"] = None
    user_store.update_profile(sender, m1)
    user_store.update_profile(partner, m2)
    safe_reply(client, f"{config.SYM_CHECK} Divorced.", message, cj)
@register('/miner')
def handle_miner(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    p = user_store.get_profile(sender)
    if not (p.get("premium") or buyer_store.is_buyer(sender) or p.get("title") == config.REGISTER_TITLE or ctx["is_owner"]):
        safe_reply(client, f"{config.SYM_CROSS} Butuh Premium/Early Access.", message, cj)
        return
    sub = (args or "").strip().lower().split()[0] if args else "status"
    if sub == "start":
        if miner_manager.is_mining(sender):
            safe_reply(client, f"{config.SYM_NOTE} Aktif.", message, cj)
            return
        ok, msg = miner_manager.start(sender)
        safe_reply(client, f"{config.SYM_CHECK} STARTED Lv{miner_level_for(sender)}/10" if ok else f"{config.SYM_CROSS} {msg}", message, cj)
        return
    if sub == "stop":
        ok, sess = miner_manager.stop(sender)
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada sesi.", message, cj)
            return
        total = sum(sess.collected.values())
        def mut(pp):
            pp["total_mined"] = pp.get("total_mined", 0) + total
        user_store.update_profile(sender, mut)
        safe_reply(client, f"{config.SYM_CHECK} Mined *{total}* item.", message, cj)
        achievement_manager.check_all(sender)
        return
    s = miner_manager.get_status(sender)
    if not s:
        safe_reply(client, f"{config.SYM_CROSS} Tidak aktif. `/miner start`", message, cj)
        return
    safe_reply(client, f"{config.SYM_BULLET} Lv{s.level}/10 {config.SYM_DOT} {s.progress_pct():.1f}% {config.SYM_DOT} {sum(s.collected.values())}/{s.max_items}", message, cj)
@register('/stock')
def handle_stock(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    sub = parts[0].lower() if parts else "list"
    if sub in ("list", "market", ""):
        ordered = stock_market.get_ordered()
        lines = [f"{box_title('STOCK', 22)}"]
        for idx, (t, s) in enumerate(ordered, 1):
            p = s["price"]
            b = s["base_price"]
            ch = ((p - b) / max(b, 1)) * 100
            ar = "▲" if ch > 2 else ("▼" if ch < -2 else "▬")
            lines.append(f"`{idx}.` {ar} *{t}* {config.SYM_DOT} {s['name']}")
            lines.append(f"  {config.SYM_DOT} `{p}` {config.SYM_DOT} {ch:+.1f}%")
        lines.append(f"\n{config.SYM_ARROW} `/stock buy <n> <qty>` {config.SYM_DOT} `/stock sell`")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    if sub in ("buy", "sell"):
        if len(parts) < 3 or not parts[1].isdigit():
            safe_reply(client, f"`/stock {sub} <n> <qty>`", message, cj)
            return
        qty = validate_number(parts[2], 1, 1000)
        if not qty:
            safe_reply(client, f"{config.SYM_CROSS} Qty.", message, cj)
            return
        s = stock_market.get_by_order(int(parts[1]))
        if not s:
            safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
            return
        if sub == "buy":
            ok, msg = stock_market.buy(sender, s["ticker"], qty)
        else:
            ok, msg = stock_market.sell(sender, s["ticker"], qty)
        safe_reply(client, f"{config.SYM_CHECK if ok else config.SYM_CROSS} {msg}", message, cj)
        return
    if sub == "portfolio":
        p = user_store.get_profile(sender)
        h = p.get("holdings", {})
        if not h:
            safe_reply(client, f"{config.SYM_NOTE} Kosong.", message, cj)
            return
        lines = [f"{box_title('PORTFOLIO', 22)}"]
        for t, hh in h.items():
            lines.append(f"{config.SYM_BULLET} *{t}* {hh.get('qty', 0)} {config.SYM_DOT} avg `{hh.get('avg_price', 0)}`")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    safe_reply(client, f"{config.SYM_BULLET} `/stock` {config.SYM_DOT} `buy` {config.SYM_DOT} `sell` {config.SYM_DOT} `portfolio`", message, cj)

@register('/index')
def handle_index(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    p = user_store.get_profile(sender)
    e = user_store.get_economy(sender)
    fish = p.get("fishing", {})
    gath = p.get("gathering", {})
    ach = achievement_manager.get_user(sender)
    lines = [f"{box_title('INDEX', 22)}",
             f"{config.SYM_BULLET} {p.get('name', '?')}",
             f"{config.SYM_BULLET} {get_rank_display(p.get('level', 1))} {config.SYM_DOT} Lv {p.get('level', 1)}",
             hline(22),
             f"{config.SYM_DIAMOND} *GAME*",
             f"{config.SYM_BULLET} `1.` Fishing     Lv {fish.get('level', 1)}/{config.GAME_MAX_LEVEL}",
             f"{config.SYM_BULLET} `2.` Gathering   Lv {gath.get('level', 1)}/{config.GAME_MAX_LEVEL}",
             f"{config.SYM_BULLET} `3.` Mining      {p.get('total_mined', 0)} item",
             f"{config.SYM_BULLET} `4.` Stock       {len(p.get('holdings', {}))} saham",
             f"{config.SYM_DIAMOND} *EKONOMI*",
             f"{config.SYM_BULLET} `5.` Token       {e.get('tokens', 0)}/{config.TOKEN_CAP}",
             f"{config.SYM_BULLET} `6.` Cash        {e.get('cash', 0)}",
             f"{config.SYM_DIAMOND} *SOCIAL*",
             f"{config.SYM_BULLET} `7.` Achievement {len(ach)}/{len(config.UNIVERSAL_ACHIEVEMENTS)}",
             f"{config.SYM_BULLET} `8.` Marriage    {'aktif' if p.get('married_to') else '—'}",
             f"\n{config.SYM_ARROW} `/i <nomor>` detail"]
    safe_reply(client, "\n".join(lines), message, cj)
@register('/i')
def handle_i_detail(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    if not parts:
        safe_reply(client, "`/i <nomor>`", message, cj)
        return
    num = parts[0]
    if num == "1":
        handle_fishing_router(client, message, cj, chat, sender, "", ctx)
        return
    if num == "2":
        handle_gathering_router(client, message, cj, chat, sender, "", ctx)
        return
    if num == "5":
        safe_reply(client, f"{config.SYM_BULLET} Token: {get_tokens(sender)}/{config.TOKEN_CAP}", message, cj)
        return
    if num == "6":
        safe_reply(client, f"{config.SYM_BULLET} Cash: {get_cash(sender)}", message, cj)
        return
    if num == "7":
        handle_achievements(client, message, cj, chat, sender, args, ctx)
        return
    safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
@register('/achievements')
def handle_achievements(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    u = achievement_manager.get_user(sender)
    tot = len(config.UNIVERSAL_ACHIEVEMENTS)
    unl = len(u)
    lines = [f"{box_title('ACHIEVEMENTS', 22)}",
             f"{config.SYM_BULLET} Progress: *{unl}/{tot}*",
             hline(22)]
    for k, a in config.UNIVERSAL_ACHIEVEMENTS.items():
        ic = config.SYM_CHECK if k in u else config.SYM_DOT
        lines.append(f"{ic} {a['emoji']} *{a['name']}* {config.SYM_DOT} {a['desc']}")
    safe_reply(client, "\n".join(lines), message, cj)

from pathlib import Path
import json, math
from core.identity import permission_manager

_R2_FIN_PATH = lambda uid: Path(config.USER_DIR) / uid / "finance.json"

def _fin(uid):
    path=_R2_FIN_PATH(uid); return atomic_json_read(path, default={"bank":0,"loan":0,"loan_rate":0.05,"investments":{},"auction":{},"insurance":0,"tax_paid":0,"ledger":[]})

def _save_fin(uid,data):
    path=_R2_FIN_PATH(uid); path.parent.mkdir(parents=True,exist_ok=True); atomic_json_write(path,data); return data

def _ledger(uid,entry):
    d=_fin(uid); d.setdefault("ledger",[]).append(dict(entry,ts=now_ts())); _save_fin(uid,d)

def _amount(args, minimum=1):
    parts=(args or '').split();
    if not parts: return None
    n=validate_number(parts[0],minimum,10**12); return n

def _r2_economy_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"]; e=user_store.get_economy(sender); f=_fin(sender)
    if op=="balance": handle_balance(client,message,cj,chat,sender,args,ctx); return
    if op=="daily": handle_daily(client,message,cj,chat,sender,args,ctx); return
    if op=="work": handle_work(client,message,cj,chat,sender,args,ctx); return
    if op=="rob": handle_rob(client,message,cj,chat,sender,args,ctx); return
    if op=="dailybox": handle_dailybox(client,message,cj,chat,sender,args,ctx); return
    if op=="bank":
        safe_reply(client,f"🏦 Bank\nSaldo bank: *{int(f.get('bank',0))}*\nCash: *{int(e.get('cash',0))}*",message,cj); return
    if op=="deposit":
        n=_amount(args); 
        if not n or e.get('cash',0)<n: safe_reply(client,f"{config.SYM_CROSS} Cash tidak cukup.",message,cj); return
        deduct_cash(sender,n,"bank_deposit"); f['bank']=f.get('bank',0)+n; _save_fin(sender,f); _ledger(sender,{'type':'deposit','amount':n}); safe_reply(client,f"{config.SYM_CHECK} Deposit *{n}*.",message,cj); return
    if op=="withdraw":
        n=_amount(args)
        if not n or f.get('bank',0)<n: safe_reply(client,f"{config.SYM_CROSS} Saldo bank kurang.",message,cj); return
        f['bank']-=n; _save_fin(sender,f); add_cash(sender,n,"bank_withdraw"); _ledger(sender,{'type':'withdraw','amount':n}); safe_reply(client,f"{config.SYM_CHECK} Withdraw *{n}*.",message,cj); return
    if op=="transfer":
        parts=(args or '').split(); target=parts[0] if parts else ''; n=validate_number(parts[1],1,10**9) if len(parts)>1 else None
        if not target or not n or not user_store.user_exists(target) or target==sender: safe_reply(client,"`/transfer <uid> <cash>`",message,cj); return
        if not deduct_cash(sender,n,"transfer"): safe_reply(client,f"{config.SYM_CROSS} Cash tidak cukup.",message,cj); return
        add_cash(target,n,"transfer"); _ledger(sender,{'type':'transfer_out','amount':n,'to':target}); _ledger(target,{'type':'transfer_in','amount':n,'from':sender}); safe_reply(client,f"{config.SYM_CHECK} Transfer *{n}* → `{target}`",message,cj); return
    if op=="loan":
        n=_amount(args,100); maxloan=max(100, int(user_store.get_economy(sender).get('cash',0))*2+1000)
        if not n or n>maxloan or f.get('loan',0)>0: safe_reply(client,f"{config.SYM_CROSS} Loan invalid atau masih ada pinjaman.",message,cj); return
        f['loan']=n; f['loan_rate']=0.05; _save_fin(sender,f); add_cash(sender,n,"loan"); safe_reply(client,f"{config.SYM_CHECK} Loan *{n}*, total repayment *{int(n*1.05)}*.",message,cj); return
    if op=="repay":
        loan=f.get('loan',0); n=_amount(args) or int(loan*1.05)
        due=int(loan*1.05)
        if not loan or n<due or not deduct_cash(sender,due,"loan_repay"): safe_reply(client,f"{config.SYM_CROSS} Butuh *{due}* untuk melunasi.",message,cj); return
        f['loan']=0; _save_fin(sender,f); safe_reply(client,f"{config.SYM_CHECK} Loan lunas.",message,cj); return
    if op=="invest":
        parts=(args or '').split(); asset=(parts[0] if parts else 'NYX').upper(); n=validate_number(parts[1],1,10**9) if len(parts)>1 else 100
        if not asset or not n or not deduct_cash(sender,n,"invest"): safe_reply(client,f"{config.SYM_CROSS} Format `/invest <aset> <cash>`.",message,cj); return
        inv=f.setdefault('investments',{}); inv[asset]=inv.get(asset,0)+n; _save_fin(sender,f); _ledger(sender,{'type':'invest','asset':asset,'amount':n}); safe_reply(client,f"{config.SYM_CHECK} Invest *{n}* pada `{asset}`.",message,cj); return
    if op=="portfolio":
        safe_reply(client,"📊 *PORTFOLIO*\n"+"\n".join(f"▸ `{k}` = {v}" for k,v in f.get('investments',{}).items()) if f.get('investments') else "📊 Portfolio kosong.",message,cj); return
    if op=="interest":
        interest=int(f.get('bank',0)*0.01); f['bank']=f.get('bank',0)+interest; _save_fin(sender,f); safe_reply(client,f"🏦 Bunga 1% diterapkan: *+{interest}*",message,cj); return
    if op=="budget":
        n=_amount(args) or 0; f['budget']=n; _save_fin(sender,f); safe_reply(client,f"📒 Budget bulanan: *{n}*",message,cj); return
    if op=="networth":
        inv=sum(f.get('investments',{}).values()); safe_reply(client,f"💎 Net worth ≈ *{int(e.get('cash',0)+f.get('bank',0)+inv-f.get('loan',0))}*",message,cj); return
    if op=="tax":
        n=max(0,int(e.get('cash',0)*0.01));
        if n and deduct_cash(sender,n,'tax'): f['tax_paid']=f.get('tax_paid',0)+n; _save_fin(sender,f)
        safe_reply(client,f"🧾 Tax 1%: *{n}*",message,cj); return
    if op=="gift": handle_gift(client,message,cj,chat,sender,args,ctx); return
    if op=="cashflow": safe_reply(client,f"💸 Cash *{e.get('cash',0)}* · Bank *{f.get('bank',0)}* · Loan *{f.get('loan',0)}*",message,cj); return
    if op=="ledger":
        rows=f.get('ledger',[])[-10:]; safe_reply(client,"📒 *LEDGER*\n"+"\n".join(f"▸ {x.get('type')} {x.get('amount',0)}" for x in rows) if rows else "📒 Ledger kosong.",message,cj); return

def _r2_market_state():
    return atomic_json_read(Path(config.SHARED_DIR)/"market_r2.json", default={"open":True,"watch":{}})
def _save_market_state(d):
    atomic_json_write(Path(config.SHARED_DIR)/"market_r2.json", d)
def _r2_trade_ledger(sender, kind, ticker, qty, amount):
    f=_fin(sender); _ledger(sender,{"type":f"stock_{kind}","ticker":ticker,"qty":qty,"amount":amount})
def _r2_market_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"]; stocks=stock_market.get_all(); f=_fin(sender); a=(args or "").split(); ms=_r2_market_state()
    if op in ("market","stocks","marketlist"):
        lines=[f"▸ `{t}` {x['name']} · {x['price']} (H:{x['high']} L:{x['low']})" for t,x in stocks.items()]
        safe_reply(client,"📊 *MARKET*\n"+"\n".join(lines),message,cj); return
    if op=="stockquote":
        t=(a[0] if a else "NYX").upper(); x=stocks.get(t); safe_reply(client,f"📈 `{t}` · {x['price']} · H {x['high']} · L {x['low']}" if x else "Ticker tidak ada.",message,cj); return
    if op in ("stockbuy","stocksell"):
        if not ms.get("open",True): safe_reply(client,"📊 Market sedang closed.",message,cj); return
        t=(a[0] if a else "").upper(); q=validate_number(a[1],1,100000) if len(a)>1 else None
        if not t or not q: safe_reply(client,f"`/{op} <ticker> <qty>`",message,cj); return
        ok,msg=(stock_market.buy(sender,t,q) if op=="stockbuy" else stock_market.sell(sender,t,q));
        if ok:
            px=stocks.get(t,{}).get("price",0); _r2_trade_ledger(sender,"buy" if op=="stockbuy" else "sell",t,q,int(px*q))
        safe_reply(client,("✅ " if ok else "❌ ")+msg,message,cj); return
    if op=="portfolio":
        h=user_store.get_profile(sender).get("holdings",{}); total=0; lines=[]
        for t,v in h.items():
            px=stocks.get(t,{}).get("price",0); val=int(px*v.get("qty",0)); total+=val; lines.append(f"▸ {t} ×{v.get('qty',0)} · {val}")
        safe_reply(client,"📊 *PORTFOLIO*\n"+("\n".join(lines) or "Kosong.")+f"\nTotal *{total}*",message,cj); return
    if op=="watchlist":
        target=(a[0] if a else "").upper(); w=f.setdefault("watchlist",[])
        if target in stocks and target not in w: w.append(target)
        elif target in w: w.remove(target)
        _save_fin(sender,f); safe_reply(client,"👁️ "+(", ".join(w) or "Watchlist kosong."),message,cj); return
    if op=="pricechart":
        t=(a[0] if a else "NYX").upper(); x=stocks.get(t); safe_reply(client,f"📉 {t}\nL:{x.get('low')} ━━━━━●━━━━ H:{x.get('high')}\nNow:{x.get('price')}" if x else "Ticker tidak ada.",message,cj); return
    if op=="marketstatus": safe_reply(client,f"📊 Market: *{'OPEN' if ms.get('open',True) else 'CLOSED'}*",message,cj); return
    if op in ("marketopen","marketclose"):
        if not ctx.get("is_owner"): safe_reply(client,"❌ Owner only.",message,cj); return
        ms["open"]=op=="marketopen"; _save_market_state(ms); safe_reply(client,f"📊 Market {'opened' if ms['open'] else 'closed'}.",message,cj); return
    if op=="tradehistory":
        rows=[x for x in f.get("ledger",[]) if str(x.get("type","")).startswith("stock_")][-12:]; lines=[f"▸ {x.get('type')} {x.get('ticker','')} ×{x.get('qty','')} {x.get('amount','')}" for x in rows]
        safe_reply(client,"📒 *TRADE HISTORY*\n"+("\n".join(lines) if lines else "Belum ada trade."),message,cj); return
    if op=="fees": safe_reply(client,f"💸 Trade fee: *{config.STOCK_TRADE_FEE:.1%}*",message,cj); return
    if op=="dividends":
        last=f.get("last_dividend",0); now=now_ts()
        if now-last<86400: safe_reply(client,"💰 Dividend sudah diklaim hari ini.",message,cj); return
        div=sum(int(stocks.get(t,{}).get("price",0)*v.get("qty",0)*0.01) for t,v in user_store.get_profile(sender).get("holdings",{}).items()); f["last_dividend"]=now; _save_fin(sender,f); add_tokens(sender,div,"dividend"); safe_reply(client,f"💰 Dividend +{div} token.",message,cj); return
    if op=="volatility": safe_reply(client,f"📈 Volatility: *{config.STOCK_VOLATILITY:.1%}*",message,cj); return
    if op=="highlow":
        t=(a[0] if a else "NYX").upper(); x=stocks.get(t); safe_reply(client,f"📈 {t} H:{x.get('high')} L:{x.get('low')}" if x else "Ticker tidak ada.",message,cj); return
    if op=="volume":
        raw=atomic_json_read(Path(config.SHARED_DIR)/"stock.json",default={}).get("global_flow",{}); lines=[f"▸ {t}: buy {v.get('buys',0)} sell {v.get('sells',0)}" for t,v in raw.items()]; safe_reply(client,"📊 Volume flow\n"+("\n".join(lines) or "Belum ada flow."),message,cj); return
    if op=="marketnews":
        lines=[f"▸ {t}: {x['price']} · updated {int(now_ts()-x.get('last_update',now_ts()))}s ago" for t,x in stocks.items()]; safe_reply(client,"📰 Local market\n"+"\n".join(lines),message,cj); return
    if op=="mocktrade":
        t=(a[0] if a else "NYX").upper(); q=validate_number(a[1],1,100000) if len(a)>1 else 1; x=stocks.get(t); safe_reply(client,f"🧪 Simulasi {t} ×{q} = {int((x['price'] if x else 0)*q)} token",message,cj); return

register_feature_specs("economy", _r2_economy_runner, category="economy")
register_feature_specs("economy", _r2_market_runner, category="market")
