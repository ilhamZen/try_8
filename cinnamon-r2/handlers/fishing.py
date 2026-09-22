from handlers import register, register_feature_specs
from handlers.auth import require_login, require_paid_cooldown
import config
import logging
import random
import time
from core.utils import box_title, hline, log_activity, now_ts, wib_day_start
from core.storage import user_store
from core.economy import achievement_manager, add_cash, deduct_tokens, get_luck
from core.send import safe_reply
from core.economy import achievement_manager
from core.economy import get_luck, add_tokens
from core.storage import GroupIDManager
from core.storage import user_store, event_manager, buyer_store
def do_fishing(uid):
    p = user_store.get_profile(uid)
    g = p.get("fishing", {})
    luck = get_luck(uid)
    rod = g.get("rod_level", 1)
    rb = config.ROD_RARE_BOOST.get(rod, 0.05)
    basket = g.get("basket_level", 1)
    bc = config.BASKET_BONUS.get(basket, 0.10)
    tier = _roll_rarity(luck, rb)
    items = [(tier, config.FISHING_ITEMS[tier])]
    if random.random() < bc:
        t2 = _roll_rarity(luck * 0.5, rb * 0.5)
        items.append((t2, config.FISHING_ITEMS[t2]))
    return items
def do_gathering(uid):
    p = user_store.get_profile(uid)
    g = p.get("gathering", {})
    luck = get_luck(uid)
    basket = g.get("basket_level", 1)
    bc = config.BASKET_BONUS.get(basket, 0.10)
    tier = _roll_rarity(luck)
    items = [(tier, config.GATHER_ITEMS[tier])]
    if random.random() < bc:
        t2 = _roll_rarity(luck * 0.5)
        items.append((t2, config.GATHER_ITEMS[t2]))
    return items
def _daily_game_state(e, which):
    day_start = wib_day_start()
    last_key = "fishing_last" if which == "fishing" else "gathering_last"
    today_key = "fishing_today" if which == "fishing" else "gathering_today"
    last = e.get(last_key, 0)
    if last < day_start:
        return 0
    return e.get(today_key, 0)
def _roll_rarity(luck, rod_boost=0):
    w = {}
    for tier, base in config.RARITY_BASE_WEIGHTS.items():
        if tier == "common":
            mult = max(0.2, 1 - luck * 1.5)
        elif tier == "uncommon":
            mult = max(0.4, 1 - luck * 0.8)
        elif tier == "rare":
            mult = 1 + (luck + rod_boost) * 2.0
        elif tier == "epic":
            mult = 1 + (luck + rod_boost) * 3.0
        elif tier == "legend":
            mult = 1 + (luck + rod_boost) * 4.0
        elif tier == "mythic":
            mult = 1 + (luck + rod_boost) * 5.0
        else:
            mult = 1
        w[tier] = max(0.001, base * mult)
    return random.choices(list(w.keys()), weights=list(w.values()), k=1)[0]
def check_game_quests(uid, game_type):
    p = user_store.get_profile(uid)
    g = p.get(game_type, {})
    lvl = g.get("level", 1)
    if lvl >= config.GAME_MAX_LEVEL:
        return None
    quests = (config.FISHING_QUESTS if game_type == "fishing" else config.GATHER_QUESTS).get(lvl)
    if not quests:
        return None
    rc = g.get("rarity_count", {})
    rare_plus = rc.get("rare", 0) + rc.get("epic", 0) + rc.get("legend", 0) + rc.get("mythic", 0)
    epic_plus = rc.get("epic", 0) + rc.get("legend", 0) + rc.get("mythic", 0)
    total = g.get("total_catch" if game_type == "fishing" else "total_gather", 0)
    def ck(q):
        if q["type"] == "total":
            return total >= q["target"]
        if q["type"] == "rare_plus":
            return rare_plus >= q["target"]
        if q["type"] == "epic_plus":
            return epic_plus >= q["target"]
        return False
    if all(ck(q) for q in quests):
        nl = lvl + 1
        def mut(pp):
            gg = pp.setdefault(game_type, {})
            gg["level"] = nl
        user_store.update_profile(uid, mut)
        reward = config.GAME_LEVEL_REWARDS.get(nl, 0)
        add_cash(uid, reward, source=f"{game_type}_quest")
        return nl, reward
    return None
def apply_game_rewards(uid, game_type, items):
    """Persist game loot, verify it exists, then update game counters."""
    receipt = []
    for tier, info in items:
        key = f"{game_type}_{tier}"
        ok = user_store.add_item(uid, key, qty=1, level=1, source=game_type)
        after = user_store.item_count(uid, key, 1) if ok else 0
        receipt.append({"tier": tier, "key": key, "name": info.get("name", key),
                        "emoji": info.get("emoji", "❖"), "ok": bool(ok), "qty_after": after})
        if not ok:
            logging.error(f"[REWARD] inventory write failed uid={uid} key={key}")
    def mut(pp):
        g = pp.setdefault(game_type, {})
        cnt = g.setdefault("rarity_count", {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legend": 0, "mythic": 0})
        for tier, _ in items:
            cnt[tier] = cnt.get(tier, 0) + 1
        k = "total_catch" if game_type == "fishing" else "total_gather"
        g[k] = g.get(k, 0) + len(items)
    user_store.update_profile(uid, mut)
    return receipt
@register('/mancing')
def handle_mancing(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    n = now_ts()
    today = _daily_game_state(e, "fishing")
    if today >= config.FISHING_MAX_PER_DAY and not ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_RING} Max {config.FISHING_MAX_PER_DAY}x/hari.", message, cj)
        return
    if n - e.get("fishing_last", 0) < config.FISHING_COOLDOWN and not ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_RING} CD {int(config.FISHING_COOLDOWN - (n - e.get('fishing_last', 0)))}s.", message, cj)
        return
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, config.FISHING_COST, source="fishing")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang ({rem}).", message, cj)
            return
    items = do_fishing(sender)
    receipt = apply_game_rewards(sender, "fishing", items)
    def mut(ee):
        ee["fishing_last"] = n
        ee["fishing_today"] = today + 1
    user_store.update_economy(sender, mut)
    event_manager.progress(sender, "fish", 1)
    lines = [f"{box_title('MANCING', 22)}"]
    for tier, info in items:
        lines.append(f"{config.SYM_BULLET} {info['emoji']} *{info['name']}* _{tier}_")
    saved = [r for r in receipt if r.get("ok")]
    failed = [r for r in receipt if not r.get("ok")]
    if saved:
        lines.append(f"\n{config.SYM_CHECK} Masuk TAS: *{len(saved)} item*")
        for r in saved:
            lines.append(f"  {config.SYM_DOT} {r['emoji']} {r['name']} ×{r['qty_after']}")
    if failed:
        lines.append(f"{config.SYM_CROSS} {len(failed)} item gagal disimpan. Cek `/invcheck`.")
    lines.append(f"\n{config.SYM_ARROW} `/tas` {config.SYM_DOT} `/inventory`")
    lines.append(f"{config.SYM_ARROW} `/sell fishing_{items[0][0]}`")
    lvr = check_game_quests(sender, "fishing")
    if lvr:
        lines.append(f"\n{config.SYM_STAR} *LEVEL UP!* Lv{lvr[0]} {config.SYM_DOT} +{lvr[1]} cash")
    safe_reply(client, "\n".join(lines), message, cj)
    achievement_manager.check_all(sender)
@register('/mungut')
def handle_mungut(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    n = now_ts()
    today = _daily_game_state(e, "gathering")
    if today >= config.FISHING_MAX_PER_DAY and not ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_RING} Max {config.FISHING_MAX_PER_DAY}x/hari.", message, cj)
        return
    if n - e.get("gathering_last", 0) < config.FISHING_COOLDOWN and not ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_RING} CD {int(config.FISHING_COOLDOWN - (n - e.get('gathering_last', 0)))}s.", message, cj)
        return
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, config.FISHING_COST, source="gathering")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang ({rem}).", message, cj)
            return
    items = do_gathering(sender)
    apply_game_rewards(sender, "gathering", items)
    def mut(ee):
        ee["gathering_last"] = n
        ee["gathering_today"] = today + 1
    user_store.update_economy(sender, mut)
    event_manager.progress(sender, "gather", 1)
    lines = [f"{box_title('MUNGUT', 22)}"]
    for tier, info in items:
        lines.append(f"{config.SYM_BULLET} {info['emoji']} *{info['name']}* _{tier}_")
    lines.append(f"\n{config.SYM_ARROW} `/sell gathering_{items[0][0]}`")
    lvr = check_game_quests(sender, "gathering")
    if lvr:
        lines.append(f"\n{config.SYM_STAR} *LEVEL UP!* Lv{lvr[0]} {config.SYM_DOT} +{lvr[1]} cash")
    safe_reply(client, "\n".join(lines), message, cj)
    achievement_manager.check_all(sender)
@register('/fishing')
def handle_fishing_router(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    if parts and parts[0].lower() == "prestige":
        p = user_store.get_profile(sender)
        g = p.get("fishing", {})
        lvl = g.get("level", 1)
        pr = g.get("prestige", 0)
        if lvl < config.GAME_MAX_LEVEL:
            safe_reply(client, f"{config.SYM_CROSS} Butuh Lv{config.GAME_MAX_LEVEL}.", message, cj)
            return
        if pr >= config.PRESTIGE_MAX:
            safe_reply(client, f"{config.SYM_CROSS} Max prestige {config.PRESTIGE_MAX}.", message, cj)
            return
        def mut(pp):
            pp.setdefault("fishing", {})["level"] = 1
            pp["fishing"]["prestige"] = pr + 1
            pp["fishing"]["total_catch"] = 0
            pp["fishing"]["rarity_count"] = {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legend": 0, "mythic": 0}
        user_store.update_profile(sender, mut)
        log_activity(sender, "prestige", {"game": "fishing", "level": pr + 1})
        safe_reply(client, f"{config.SYM_STAR} Prestige {pr + 1}/{config.PRESTIGE_MAX}! +5% luck", message, cj)
        achievement_manager.check_all(sender)
        return
    p = user_store.get_profile(sender)
    g = p.get("fishing", {})
    rc = g.get("rarity_count", {})
    lines = [f"{box_title('FISHING', 22)}",
             f"{config.SYM_BULLET} Level: *{g.get('level', 1)}/{config.GAME_MAX_LEVEL}*",
             f"{config.SYM_BULLET} Prestige: *{g.get('prestige', 0)}/{config.PRESTIGE_MAX}*",
             f"{config.SYM_BULLET} Total: *{g.get('total_catch', 0)}*",
             f"{config.SYM_BULLET} Rod: *Lv {g.get('rod_level', 1)}*",
             f"{config.SYM_BULLET} Basket: *Lv {g.get('basket_level', 1)}*",
             hline(22)]
    for t in ["common", "uncommon", "rare", "epic", "legend", "mythic"]:
        lines.append(f"{config.SYM_DOT} {t}: *{rc.get(t, 0)}*")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/gathering')
def handle_gathering_router(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    if parts and parts[0].lower() == "prestige":
        p = user_store.get_profile(sender)
        g = p.get("gathering", {})
        lvl = g.get("level", 1)
        pr = g.get("prestige", 0)
        if lvl < config.GAME_MAX_LEVEL:
            safe_reply(client, f"{config.SYM_CROSS} Butuh Lv{config.GAME_MAX_LEVEL}.", message, cj)
            return
        if pr >= config.PRESTIGE_MAX:
            safe_reply(client, f"{config.SYM_CROSS} Max {config.PRESTIGE_MAX}.", message, cj)
            return
        def mut(pp):
            pp.setdefault("gathering", {})["level"] = 1
            pp["gathering"]["prestige"] = pr + 1
            pp["gathering"]["total_gather"] = 0
            pp["gathering"]["rarity_count"] = {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legend": 0, "mythic": 0}
        user_store.update_profile(sender, mut)
        log_activity(sender, "prestige", {"game": "gathering", "level": pr + 1})
        safe_reply(client, f"{config.SYM_STAR} Prestige {pr + 1}/{config.PRESTIGE_MAX}! +5% luck", message, cj)
        achievement_manager.check_all(sender)
        return
    p = user_store.get_profile(sender)
    g = p.get("gathering", {})
    rc = g.get("rarity_count", {})
    lines = [f"{box_title('GATHERING', 22)}",
             f"{config.SYM_BULLET} Level: *{g.get('level', 1)}/{config.GAME_MAX_LEVEL}*",
             f"{config.SYM_BULLET} Prestige: *{g.get('prestige', 0)}/{config.PRESTIGE_MAX}*",
             f"{config.SYM_BULLET} Total: *{g.get('total_gather', 0)}*",
             f"{config.SYM_BULLET} Basket: *Lv {g.get('basket_level', 1)}*",
             hline(22)]
    for t in ["common", "uncommon", "rare", "epic", "legend", "mythic"]:
        lines.append(f"{config.SYM_DOT} {t}: *{rc.get(t, 0)}*")
    safe_reply(client, "\n".join(lines), message, cj)


def _r2_fishing_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec['operation']; a=(args or '').strip(); p=user_store.get_profile(sender); fish=p.get('fishing',{}); rc=fish.get('rarity_count',{})
    if op in ('fish','fishing','cast','rarefish','epicfish','legendfish','mythicfish'): return handle_fishing_router(client,message,cj,chat,sender,a,ctx)
    if op=='bait':
        user_store.update_profile(sender,lambda x:x.setdefault('fishing',{}).__setitem__('bait',a or 'basic')); safe_reply(client,f'🎣 Bait: {a or "basic"}',message,cj); return
    if op=='rod': safe_reply(client,f"🎣 Rod Lv.{fish.get('rod_level',1)}",message,cj); return
    if op=='basket': safe_reply(client,f"🧺 Basket Lv.{p.get('gathering',{}).get('basket_level',1)}",message,cj); return
    if op in ('pond','river','lake'):
        user_store.update_profile(sender,lambda x:x.setdefault('fishing',{}).__setitem__('spot',op)); safe_reply(client,f'🌊 Spot `{op}` aktif.',message,cj); return
    if op=='fishquest': safe_reply(client,f"📜 Catch {fish.get('total_catch',0)} · rare {sum(rc.get(k,0) for k in ('rare','epic','legend','mythic'))}",message,cj); return
    if op=='fishlevel': safe_reply(client,f"🐟 Level {fish.get('level',1)}",message,cj); return
    if op=='fishprestige': safe_reply(client,f"⭐ Prestige {fish.get('prestige',0)}",message,cj); return
    if op=='fishsell': return handle_sell(client,message,cj,chat,sender,'fish',ctx)
    if op in ('fishequip','fishgear'): safe_reply(client,f"🎣 Rod {fish.get('rod_level',1)} · Bait {fish.get('bait','basic')}",message,cj); return
    if op=='fishcollection': safe_reply(client,"🎣 Collection\n"+'\n'.join(f"▸ {k}: {rc.get(k,0)}" for k in ('common','uncommon','rare','epic','legend','mythic')),message,cj); return
    safe_reply(client,f"🐟 Catch *{fish.get('total_catch',0)}*",message,cj)
def _r2_mining_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec['operation']; a=(args or '').strip(); p=user_store.get_profile(sender); inv=user_store.get_inventory(sender)
    if op in ('mine','miner','minestart'):
        ok,msg=miner_manager.start(sender);safe_reply(client,f"⛏️ {msg if msg!='OK' else 'Mining dimulai.'}",message,cj);return
    if op=='minestop':
        ok,sess=miner_manager.stop(sender);safe_reply(client,"⛏️ Mining dihentikan." if ok else "⛏️ Tidak sedang mining.",message,cj);return
    if op=='minestatus':
        ss=miner_manager.get_status(sender);safe_reply(client,f"⛏️ {'ACTIVE' if ss else 'IDLE'}",message,cj);return
    if op=='minelevel': safe_reply(client,f"⛏️ Total mined {p.get('total_mined',0)}",message,cj);return
    if op=='mineprogress': safe_reply(client,f"⛏️ Active={bool(miner_manager.get_status(sender))} · total={p.get('total_mined',0)}",message,cj);return
    if op in ('mineore','minegold','minediamond','minecrystal'):
        term={'mineore':'ore','minegold':'gold','minediamond':'diamond','minecrystal':'crystal'}[op];n=sum(x.get('qty',0) for x in inv if term in x.get('key','').lower());safe_reply(client,f"⛏️ {term}: *{n}*",message,cj);return
    if op=='mineloot':
        safe_reply(client,'⛏️ Loot\n'+'\n'.join(f"▸ {x['key']} ×{x['qty']}" for x in inv if any(k in x['key'] for k in ('ore','gold','diamond','crystal','shard'))) or 'Kosong.',message,cj);return
    if op=='mineboost':
        e=user_store.get_economy(sender);e.setdefault('active_boosts',{})['miner']=now_ts()+1800;user_store.update_economy(sender,lambda x:x.update(e));safe_reply(client,'⚡ Miner boost 30m.',message,cj);return
    if op=='mineinventory': safe_reply(client,f"🎒 Mining loot {sum(x.get('qty',0) for x in inv if any(k in x['key'] for k in ('ore','gold','diamond','crystal','shard')))} item.",message,cj);return
    if op=='minestats': safe_reply(client,f"⛏️ mined={p.get('total_mined',0)} level={p.get('level',1)}",message,cj);return
    if op=='minelogs': safe_reply(client,"📜 Mining tersimpan di activity.log.",message,cj);return
    if op=='minerdaily':
        day=wib_day_start(); e=user_store.get_economy(sender); used=e.get('mining_today',0);safe_reply(client,f"⛏️ Daily {used}/100",message,cj);return
    if op=='mineupgrade':
        cost=500; e=user_store.get_economy(sender)
        if not deduct_tokens(sender,cost,'mineupgrade'):safe_reply(client,f"🪙 Butuh {cost} token.",message,cj);return
        user_store.update_profile(sender,lambda x:x.__setitem__('miner_level',min(10,x.get('miner_level',1)+1)));safe_reply(client,f"⛏️ Miner level {user_store.get_profile(sender).get('miner_level',1)}",message,cj);return
    if op=='mineclaim':
        ss=miner_manager.get_status(sender)
        if ss: miner_manager.stop(sender)
        safe_reply(client,'⛏️ Current loot tersimpan otomatis ke inventory.',message,cj);return
    if op=='mineauto':
        ok,msg=miner_manager.start(sender);safe_reply(client,'⛏️ Auto-miner started.' if ok else f'⛏️ {msg}',message,cj);return
register_feature_specs("fishing", _r2_fishing_runner, category="fishing")
register_feature_specs("fishing", _r2_mining_runner, category="mining")
