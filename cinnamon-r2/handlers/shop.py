from handlers import register, register_feature_specs
from handlers.auth import require_login
import config
from config import MAX_NAME_LEN
import logging
import os
import random
import re
import time
from core.utils import box_title, build_roman, hline, now_ts
from core.storage import _shared_read, _shared_update, atomic_json_read, atomic_json_write, user_store
from core.identity import identity_registry
from core.economy import add_cash, add_tokens, deduct_tokens, get_luck
from core.send import safe_reply
from core.economy import get_luck
from core.economy import get_tokens, deduct_tokens, add_tokens, get_cash, add_cash, deduct_cash
from core.storage import log_activity
from core.storage import user_store
def _category_for_key(key):
    if key.startswith("fishing_"):
        return "fish"
    if key.startswith("gathering_"):
        return "forage"
    defn = config.SHOP_ITEM_DEFS.get(key)
    if defn and defn.get("category") in config.ITEM_CATEGORIES:
        return defn["category"]
    return "other"
def _display_name_for_key(key, defn=None):
    if key.startswith("fishing_"):
        t = key.split("_", 1)[1]
        return config.FISHING_ITEMS.get(t, {}).get("name", key)
    if key.startswith("gathering_"):
        t = key.split("_", 1)[1]
        return config.GATHER_ITEMS.get(t, {}).get("name", key)
    if defn and defn.get("name"):
        return defn["name"]
    return key.replace("_", " ").title()
class ShopManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "shop.json")
    def _maybe_refresh(self):
        d = _shared_read(self._p(), default={"last_refresh": 0, "items": {}})
        if now_ts() - d.get("last_refresh", 0) >= config.SHOP_REFRESH_INTERVAL:
            self._refresh()
    def _refresh(self):
        keys = list(config.SHOP_ITEM_DEFS.keys())
        random.shuffle(keys)
        items = {}
        for idx, k in enumerate(keys[:config.SHOP_ITEMS_COUNT], 1):
            it = config.SHOP_ITEM_DEFS[k]
            bp = it.get("base_price", 50)
            price = max(5, int(bp * random.uniform(0.9, 1.1)))
            e = {"key": k, "id": it.get("id", ""), "order": idx, "price": price, "stock": random.randint(1, 5)}
            if it.get("category") == "potion":
                lvl = random.randint(1, 5)
                e["level"] = lvl
                e["price"] = int(price * (1 + 0.5 * (lvl - 1)))
            items[k] = e
        def mut(d):
            d["items"] = items
            d["last_refresh"] = now_ts()
        _shared_update(self._p(), {"last_refresh": 0, "items": {}}, mut)
    def get_items(self):
        self._maybe_refresh()
        return _shared_read(self._p(), default={"items": {}}).get("items", {})
    def get_by_order(self, n):
        for k, v in self.get_items().items():
            if v.get("order") == n:
                return k, v
        return None
    def reduce_stock(self, key, qty):
        def mut(d):
            it = d.setdefault("items", {}).get(key)
            if it:
                it["stock"] = max(0, it.get("stock", 1) - qty)
        _shared_update(self._p(), {"last_refresh": 0, "items": {}}, mut)
    def next_refresh(self):
        d = _shared_read(self._p(), default={"last_refresh": 0})
        return max(0, config.SHOP_REFRESH_INTERVAL - (now_ts() - d.get("last_refresh", 0)))
class GameShopManager:
    def list_items(self):
        items = []
        idx = 1
        for lv in range(1, 6):
            items.append({"idx": idx, "type": "rod", "level": lv, "price": config.ROD_PRICES[lv],
                          "name": f"Fishing Rod Lv{lv}", "emoji": "🎣",
                          "desc": f"+{int(config.ROD_RARE_BOOST[lv] * 100)}% rare"})
            idx += 1
        for lv in range(1, 6):
            items.append({"idx": idx, "type": "basket", "level": lv, "price": config.BASKET_PRICES[lv],
                          "name": f"Basket Lv{lv}", "emoji": "🧺",
                          "desc": f"+{int(config.BASKET_BONUS[lv] * 100)}% bonus"})
            idx += 1
        return items
    def get_by_order(self, n):
        for it in self.list_items():
            if it["idx"] == n:
                return it
        return None
def handle_shop(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    items = shop.get_items()
    if not items:
        safe_reply(client, f"{config.SYM_NOTE} Kosong.", message, cj)
        return
    e = user_store.get_economy(sender)
    is_prem = user_store.get_profile(sender).get("premium", False)
    nr = shop.next_refresh()
    h, m = divmod(int(nr) // 60, 60)
    lines = [f"{box_title('SHOP', 22)}",
             f"{config.SYM_BULLET} Refresh: *{h}j {m}m*",
             f"{config.SYM_BULLET} Token: *{e.get('tokens', 0)}/{config.TOKEN_CAP}*",
             f"{config.SYM_BULLET} Status: {'Premium' if is_prem else 'Regular'}",
             hline(22)]
    for key, it in sorted(items.items(), key=lambda kv: kv[1].get("order", 999)):
        defn = config.SHOP_ITEM_DEFS.get(key, {})
        num = it.get("order", "?")
        em = defn.get("emoji", "❖")
        name = defn.get("name", key)
        lvl = it.get("level")
        lvl_str = f" {build_roman(lvl)}" if lvl else ""
        price = it["price"]
        pp = int(price * 0.8) if is_prem else price
        lines.append(f"`{num}.` {em} *{name}{lvl_str}*")
        lines.append(f"  {config.SYM_DOT} {pp} {config.SYM_DOT} stock `{it['stock']}`")
    lines.append(f"{hline(22)}")
    lines.append(f"{config.SYM_ARROW} `/shop buy <nomor>`")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/buy')
def handle_buy(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").split()
    if not parts or not parts[0].isdigit():
        safe_reply(client, "`/shop buy <nomor>`", message, cj)
        return
    found = shop.get_by_order(int(parts[0]))
    if not found:
        safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
        return
    key, it = found
    if it["stock"] <= 0:
        safe_reply(client, f"{config.SYM_CROSS} Habis.", message, cj)
        return
    defn = config.SHOP_ITEM_DEFS.get(key, {})
    level = it.get("level", 1)
    total = it["price"]
    if user_store.get_profile(sender).get("premium"):
        total = int(total * 0.8)
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, total, source="shop_buy")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang ({rem}).", message, cj)
            return
    shop.reduce_stock(key, 1)
    user_store.add_item(sender, key, qty=1, level=level, source="shop_buy")
    safe_reply(client, f"{config.SYM_CHECK} {defn.get('emoji', '❖')} {defn.get('name', key)} {config.SYM_DOT} -{total}", message, cj)
@register('/shop')
def handle_shop_dispatch(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").strip().split()
    if parts and parts[0].lower() == "buy":
        return handle_buy(client, message, cj, chat, sender, " ".join(parts[1:]), ctx)
    return handle_shop(client, message, cj, chat, sender, args, ctx)
def _build_inventory_groups(sender):
    inv = user_store.get_inventory(sender)
    grouped = {cat: [] for cat in config.ITEM_CATEGORIES}
    for it in inv:
        key = it.get("key", "?")
        lvl = it.get("level", 1)
        qty = it.get("qty", 0)
        defn = config.SHOP_ITEM_DEFS.get(key, {})
        cat = _category_for_key(key)
        grouped.setdefault(cat, []).append((key, lvl, qty, defn))
    return grouped, inv
@register('/inventory')
def handle_inventory(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    grouped, inv = _build_inventory_groups(sender)
    if not inv:
        safe_reply(client, f"{config.SYM_NOTE} Inventory kosong.", message, cj)
        return
    total_qty = sum(it.get("qty", 0) for it in inv)
    lines = [f"{box_title('INVENTORY', 22)}",
             f"{config.SYM_BULLET} Item: *{len(inv)}* {config.SYM_DOT} Total: *{total_qty}*",
             hline(22)]
    for cat, lst in sorted(grouped.items(), key=lambda x: config.ITEM_CATEGORIES.get(x[0], {}).get("order", 99)):
        if not lst:
            continue
        ci = config.ITEM_CATEGORIES.get(cat, {"name": cat, "emoji": "❖"})
        lines.append(f"\n{ci['emoji']} *{ci['name']}*  `({len(lst)})`")
        for key, lvl, qty, defn in lst:
            em = defn.get("emoji", "❖")
            if key.startswith("fishing_"):
                em = config.FISHING_ITEMS.get(key.split("_", 1)[1], {}).get("emoji", "🐟")
            elif key.startswith("gathering_"):
                em = config.GATHER_ITEMS.get(key.split("_", 1)[1], {}).get("emoji", "🌿")
            name = _display_name_for_key(key, defn)
            lvl_str = f" Lv{lvl}" if lvl and lvl > 1 else ""
            lines.append(f"  {config.SYM_BULLET} {em} *{name}*{lvl_str} ×{qty}  `{key}`")
    lines.append(f"\n{hline(22)}")
    lines.append(f"{config.SYM_ARROW} `/use <key>` {config.SYM_DOT} `/sell <key> [qty]`")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/invcheck')
def handle_invcheck(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    inv_path = user_store.user_dir(sender) / "inventory.json"
    inv = atomic_json_read(inv_path, default=user_store._default_inventory())
    items = inv.setdefault("items", [])
    valid = []
    invalid = 0
    total = 0
    for it in items:
        key = str(it.get("key", "")).strip()
        qty = int(it.get("qty", 0) or 0)
        level = int(it.get("level", 1) or 1)
        if not key or qty <= 0 or level <= 0:
            invalid += 1
            continue
        it["qty"] = qty
        it["level"] = level
        valid.append(it)
        total += qty
    changed = invalid > 0 or valid != items
    if changed:
        inv["items"] = valid
        atomic_json_write(inv_path, inv)
        user_store.invalidate(sender)
    lines = [f"{box_title('INVENTORY CHECK', 22)}",
             f"{config.SYM_BULLET} File: `{'OK' if inv_path.exists() else 'CREATED'}`",
             f"{config.SYM_BULLET} Item stack: *{len(valid)}*",
             f"{config.SYM_BULLET} Total qty: *{total}*",
             f"{config.SYM_BULLET} Invalid removed: *{invalid}*",
             f"{config.SYM_CHECK} Inventory {'repaired' if changed else 'healthy'}"]
    safe_reply(client, "\n".join(lines), message, cj)
@register('/tas')
def handle_tas(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    grouped, inv = _build_inventory_groups(sender)
    if not inv:
        safe_reply(client, f"{config.SYM_NOTE} Inventory kosong.", message, cj)
        return
    total_qty = sum(it.get("qty", 0) for it in inv)
    lines = [f"{config.SYM_DIAMOND} *TAS* {config.SYM_DOT} {len(inv)} item {config.SYM_DOT} {total_qty} total"]
    for cat, lst in sorted(grouped.items(), key=lambda x: config.ITEM_CATEGORIES.get(x[0], {}).get("order", 99)):
        if not lst:
            continue
        ci = config.ITEM_CATEGORIES.get(cat, {"name": cat, "emoji": "❖"})
        qty_cat = sum(x[2] for x in lst)
        lines.append(f"{config.SYM_BULLET} {ci['emoji']} *{ci['name']}*  `({len(lst)}/{qty_cat})`")
        parts = []
        for key, lvl, qty, defn in lst[:6]:
            name = _display_name_for_key(key, defn)
            short = name.split()[0][:8]
            suffix = f"·L{lvl}" if lvl and lvl > 1 else ""
            parts.append(f"{short}{suffix}×{qty}")
        lines.append(f"  {config.SYM_DOT} " + "  ".join(parts) + ("  …" if len(lst) > 6 else ""))
    lines.append(f"\n{config.SYM_ARROW} `/inventory` untuk detail")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/use')
def handle_use(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    key = (args or "").strip().split()[0] if args else ""
    if not key:
        safe_reply(client, "`/use <key>`", message, cj)
        return
    base = key
    level = 1
    if "_" in key and key.rsplit("_", 1)[-1].isdigit():
        base = key.rsplit("_", 1)[0]
        level = int(key.rsplit("_", 1)[-1])
    if user_store.item_count(sender, base, level) <= 0:
        safe_reply(client, f"{config.SYM_CROSS} Tidak punya `{key}`.", message, cj)
        return
    defn = config.SHOP_ITEM_DEFS.get(base, {})
    cat = defn.get("category")
    if base == "reroll_cd":
        def mut(e):
            e["game_cooldowns"] = {}
        user_store.update_economy(sender, mut)
        user_store.remove_item(sender, base, 1, level, source="use")
        safe_reply(client, f"{config.SYM_CHECK} Cooldown reset!", message, cj)
        return
    if cat == "premium":
        days = defn.get("duration", config.PREMIUM_DURATION_DAYS)
        def mut(p):
            p["premium"] = True
            p["premium_expires"] = now_ts() + days * 86400
        user_store.update_profile(sender, mut)
        user_store.remove_item(sender, base, 1, level, source="use")
        safe_reply(client, f"{config.SYM_STAR} Premium {days} hari aktif!", message, cj)
        return
    if cat == "boost":
        mult = defn.get("mult", 2.0)
        dur = defn.get("duration", 3600)
        def mut(e):
            e.setdefault("active_boosts", {})[base] = {"mult": mult, "expires": now_ts() + dur}
        user_store.update_economy(sender, mut)
        user_store.remove_item(sender, base, 1, level, source="use")
        safe_reply(client, f"{config.SYM_STAR} {defn['name']} ×{mult}", message, cj)
        return
    if cat in ("potion", "misc"):
        lb = defn.get("luck_bonus", 0.0)
        dur = defn.get("duration", 3600)
        def mut(e):
            e.setdefault("active_boosts", {})[base] = {"mult": 1.0, "expires": now_ts() + dur, "luck_bonus": lb}
        user_store.update_economy(sender, mut)
        user_store.remove_item(sender, base, 1, level, source="use")
        label = f"Luck +{int(lb * 100)}%" if lb else "Boost"
        safe_reply(client, f"{config.SYM_SPARK} *{defn.get('name', base)}* aktif! ({label})", message, cj)
        return
    if cat == "lootbox":
        luck = get_luck(sender)
        roll = max(0.0, random.random() - luck)
        amt = random.randint(50, 200) if roll < 0.5 else (random.randint(200, 500) if roll < 0.85 else random.randint(500, 1500))
        add_tokens(sender, amt, source="lootbox")
        user_store.remove_item(sender, base, 1, level, source="use")
        safe_reply(client, f"{config.SYM_NOTE} +{amt} token", message, cj)
        return
    if cat == "nametag":
        parts = (args or "").split(None, 1)
        if len(parts) < 2:
            safe_reply(client, "`/use nametag <nama>`", message, cj)
            return
        new_name = parts[1].strip()[:MAX_NAME_LEN]
        if not re.match(r"^[a-zA-Z0-9_]+$", new_name):
            safe_reply(client, f"{config.SYM_CROSS} Format nama invalid.", message, cj)
            return
        def mut(p):
            p["name"] = new_name
        user_store.update_profile(sender, mut)
        identity_registry.register_user(sender, name=new_name)
        user_store.remove_item(sender, base, 1, level, source="use")
        safe_reply(client, f"{config.SYM_CHECK} Nama {config.SYM_ARROW} *{new_name}*", message, cj)
        return
    if cat is None and (base.startswith("fishing_") or base.startswith("gathering_")):
        safe_reply(client, f"{config.SYM_NOTE} Item ini tidak dipakai — `/sell {key}` untuk tukar jadi cash.", message, cj)
        return
    safe_reply(client, f"{config.SYM_CROSS} `{key}` tidak bisa dipakai.", message, cj)
@register('/sell')
def handle_sell(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").strip().split()
    if not parts:
        safe_reply(client, "`/sell <key> [qty]` atau `/sell all`", message, cj)
        return
    if parts[0].lower() == "all":
        tt = 0
        tc = 0
        inv_snapshot = list(user_store.get_inventory(sender))
        for it in inv_snapshot:
            key = it.get("key", "?")
            qty = it.get("qty", 0)
            lvl = it.get("level", 1)
            if qty <= 0:
                continue
            if key.startswith("fishing_"):
                t = key.split("_", 1)[1]
                v = config.FISHING_ITEMS.get(t, {}).get("sell", 5)
                tc += v * qty
                user_store.remove_item(sender, key, qty, lvl, source="sell_all")
            elif key.startswith("gathering_"):
                t = key.split("_", 1)[1]
                v = config.GATHER_ITEMS.get(t, {}).get("sell", 5)
                tc += v * qty
                user_store.remove_item(sender, key, qty, lvl, source="sell_all")
            else:
                defn = config.SHOP_ITEM_DEFS.get(key, {})
                if defn.get("category") in ("premium", "nametag"):
                    continue
                v = max(1, int(defn.get("base_price", 10) * 0.30))
                tt += v * qty
                user_store.remove_item(sender, key, qty, lvl, source="sell_all")
        if tt > 0:
            add_tokens(sender, tt, source="sell_all")
        if tc > 0:
            add_cash(sender, tc, source="sell_all")
        safe_reply(client, f"{config.SYM_CHECK} Sold! Token +{tt} {config.SYM_DOT} Cash +{tc}", message, cj)
        return
    full_key = parts[0]
    qty = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    have = user_store.item_count(sender, full_key, 1)
    if have <= 0:
        safe_reply(client, f"{config.SYM_CROSS} Tidak punya.", message, cj)
        return
    qty = min(qty, have)
    if full_key.startswith("fishing_"):
        t = full_key.split("_", 1)[1]
        v = config.FISHING_ITEMS.get(t, {}).get("sell", 5) * qty
        user_store.remove_item(sender, full_key, qty, 1, source="sell")
        add_cash(sender, v, source="sell")
        safe_reply(client, f"{config.SYM_CHECK} Sold {qty}× {config.SYM_ARROW} +{v} cash", message, cj)
        return
    if full_key.startswith("gathering_"):
        t = full_key.split("_", 1)[1]
        v = config.GATHER_ITEMS.get(t, {}).get("sell", 5) * qty
        user_store.remove_item(sender, full_key, qty, 1, source="sell")
        add_cash(sender, v, source="sell")
        safe_reply(client, f"{config.SYM_CHECK} Sold {qty}× {config.SYM_ARROW} +{v} cash", message, cj)
        return
    defn = config.SHOP_ITEM_DEFS.get(full_key, {})
    if defn.get("category") in ("premium", "nametag"):
        safe_reply(client, f"{config.SYM_CROSS} Tidak bisa dijual.", message, cj)
        return
    v = max(1, int(defn.get("base_price", 10) * 0.30)) * qty
    user_store.remove_item(sender, full_key, qty, 1, source="sell")
    add_tokens(sender, v, source="sell")
    safe_reply(client, f"{config.SYM_CHECK} Sold {qty}× {config.SYM_ARROW} +{v} token", message, cj)
shop = ShopManager()
@register('/gshop')
def handle_gshop(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    e = user_store.get_economy(sender)
    lines = [f"{box_title('GAME SHOP', 22)}",
             f"{config.SYM_BULLET} Cash: *{e.get('cash', 0)}*",
             hline(22)]
    for it in gshop.list_items():
        lines.append(f"`{it['idx']}.` {it['emoji']} *{it['name']}* {config.SYM_DOT} {it['price']}")
        lines.append(f"  {config.SYM_DOT} _{it['desc']}_")
    lines.append(f"\n{hline(22)}")
    lines.append(f"{config.SYM_ARROW} `/gbuy <nomor>`")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/gbuy')
def handle_gbuy(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    parts = (args or "").split()
    if not parts or not parts[0].isdigit():
        safe_reply(client, "`/gbuy <nomor>`", message, cj)
        return
    it = gshop.get_by_order(int(parts[0]))
    if not it:
        safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
        return
    p = user_store.get_profile(sender)
    g = p.get("fishing" if it["type"] == "rod" else "gathering", {})
    cur = g.get(f"{'rod' if it['type'] == 'rod' else 'basket'}_level", 1)
    if it["level"] != cur + 1:
        safe_reply(client, f"{config.SYM_CROSS} Butuh beli Lv{cur + 1} dulu.", message, cj)
        return
    ok, rem = deduct_cash(sender, it["price"], source="gbuy")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Cash kurang. Butuh {it['price']}, punya {rem}.", message, cj)
        return
    def mut(pp):
        gg = pp.setdefault("fishing" if it["type"] == "rod" else "gathering", {})
        gg[f"{'rod' if it['type'] == 'rod' else 'basket'}_level"] = it["level"]
    user_store.update_profile(sender, mut)
    log_activity(sender, "gbuy", {"type": it["type"], "level": it["level"], "cost": it["price"]})
    safe_reply(client, f"{config.SYM_CHECK} {it['emoji']} {it['name']} {config.SYM_DOT} -{it['price']}", message, cj)
gshop = GameShopManager()

from core.identity import title_manager

def _r2_itemmeta(uid):
    return atomic_json_read(Path(config.USER_DIR)/uid/"itemmeta.json",default={"equip":{},"names":{},"history":[]})
def _save_itemmeta(uid,d):
    atomic_json_write(Path(config.USER_DIR)/uid/"itemmeta.json",d); return d
def _r2_shop_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"]; a=(args or "").strip(); parts=a.split(); inv=user_store.get_inventory(sender)
    if op in ("shop","shoplist"):
        return handle_shop(client,message,cj,chat,sender,args,ctx)
    if op=="shopbuy": return handle_buy(client,message,cj,chat,sender,a,ctx)
    if op=="shopinfo":
        f=shop.get_by_order(int(parts[0])) if parts and parts[0].isdigit() else None; safe_reply(client,(f"🛒 {f[1]['key']} · {f[1]['price']} · stock {f[1]['stock']}" if f else "Gunakan `/shopinfo <nomor>`"),message,cj); return
    if op=="shoprefresh":
        shop._refresh(); safe_reply(client,"🔄 Shop di-refresh.",message,cj); return
    if op=="shoprandom":
        rows=list(shop.get_items().values()); it=random.choice(rows) if rows else None; safe_reply(client,f"🎲 {it['order']}. {it['key']} · {it['price']}" if it else "Shop kosong.",message,cj); return
    if op=="shopcategory":
        cat=(parts[0].lower() if parts else ""); rows=[(k,v) for k,v in shop.get_items().items() if config.SHOP_ITEM_DEFS.get(k,{}).get("category")==cat]; safe_reply(client,"🛒 "+cat+"\n"+"\n".join(f"▸ {k} · {v['price']}" for k,v in rows[:15]) or "Kategori kosong.",message,cj); return
    if op in ("dailyshop","premiumshop"):
        rows=list(shop.get_items().items()); rows=rows[:5] if op=="dailyshop" else [(k,v) for k,v in rows if user_store.get_profile(sender).get("premium")][:8]; safe_reply(client,"🛒\n"+"\n".join(f"▸ {k} · {int(v['price']*(.8 if op=='premiumshop' else 1))}" for k,v in rows),message,cj); return
    if op=="itemprice":
        k=parts[0] if parts else ""; it=config.SHOP_ITEM_DEFS.get(k); safe_reply(client,f"💵 {k} · {it.get('base_price')}" if it else "Item tidak ditemukan.",message,cj); return
    if op=="selllist": return handle_sell(client,message,cj,chat,sender,"",ctx)
    if op=="sellprice":
        k=parts[0] if parts else ""; it=config.SHOP_ITEM_DEFS.get(k); safe_reply(client,f"💰 {k} → {int(it.get('base_price',0)*.5)}" if it else "Item tidak ditemukan.",message,cj); return
    if op=="bundle":
        if not deduct_tokens(sender,200,"bundle"): safe_reply(client,"🪙 Butuh 200 token.",message,cj); return
        picks=random.sample(list(config.SHOP_ITEM_DEFS),min(3,len(config.SHOP_ITEM_DEFS)))
        for k in picks:user_store.add_item(sender,k,1,1,source="bundle")
        safe_reply(client,"🎁 Bundle: "+", ".join(picks),message,cj); return
    if op in ("lootbox","openbox"):
        if op=="lootbox":
            user_store.add_item(sender,"loot_box",1,1,source="shop");safe_reply(client,"🎁 Loot box ditambahkan.",message,cj);return
        if not user_store.remove_item(sender,"loot_box",1,1,"openbox"):safe_reply(client,"❌ Tidak punya loot box.",message,cj);return
        k=random.choice(list(config.SHOP_ITEM_DEFS));user_store.add_item(sender,k,random.randint(1,2),1,source="lootbox");safe_reply(client,f"🎁 Opened → {k}",message,cj);return
    meta=_r2_itemmeta(sender)
    if op in ("inventory","invlist"): return handle_inventory(client,message,cj,chat,sender,"",ctx)
    if op in ("itemsearch","itemcount","itemsort","collection","codex","consumables","materials","weapons","armor","accessories","capacity","cleanup"):
        rows=list(inv); q=a.lower()
        if op=="itemsearch":rows=[x for x in rows if q in x.get("key","").lower()]
        elif op=="itemsort":rows=sorted(rows,key=lambda x:x.get("key",""))
        elif op=="itemcount":safe_reply(client,f"🎒 Total {sum(x.get('qty',0) for x in rows)}",message,cj);return
        elif op=="capacity":safe_reply(client,f"🎒 Unique {len(rows)}/100",message,cj);return
        elif op=="cleanup":
            for x in rows[:]:
                if x.get("qty",0)<=0:user_store.remove_item(sender,x.get("key"),0,1,"cleanup")
        elif op in ("consumables","materials","weapons","armor","accessories"):
            keys={"consumables":("potion","boost","box"),"materials":("ore","crystal","shard"),"weapons":("sword","blade","bow","axe"),"armor":("armor","cloth"),"accessories":("ring","charm")}[op];rows=[x for x in rows if any(k in x.get("key","") for k in keys)]
        safe_reply(client,f"🎒 *{op.upper()}*\n"+"\n".join(f"▸ {x['key']} ×{x['qty']}" for x in rows[:20]) if rows else "🎒 Kosong.",message,cj);return
    if op=="iteminfo":
        k=parts[0] if parts else ""; n=user_store.item_count(sender,k); d=config.SHOP_ITEM_DEFS.get(k,{}); safe_reply(client,f"🎒 {k} ×{n} · {d.get('name',k)}",message,cj);return
    if op=="itemdrop":
        k=parts[0] if parts else ""; q=validate_number(parts[1],1,100000) if len(parts)>1 else 1; ok=user_store.remove_item(sender,k,q,1,"drop");safe_reply(client,"🗑️ Dibuang." if ok else "❌ Gagal.",message,cj);return
    if op=="itemuse": return handle_use(client,message,cj,chat,sender,a,ctx)
    if op in ("itemequip","itemunequip"):
        k=parts[0] if parts else ""; meta.setdefault("equip",{})[k if op=="itemequip" else "active"]=k if op=="itemequip" else None; _save_itemmeta(sender,meta); safe_reply(client,f"⚔️ {'Equip' if op=='itemequip' else 'Unequip'} {k}",message,cj); return
    if op=="itemrename":
        if len(parts)<2:safe_reply(client,"`/itemrename <key> <nama baru>`",message,cj);return
        meta.setdefault("names",{})[parts[0]]=" ".join(parts[1:])[:50];_save_itemmeta(sender,meta);safe_reply(client,f"📝 {parts[0]} → {meta['names'][parts[0]]}",message,cj);return
    if op=="nametag":
        name=validate_input(a,30);user_store.update_profile(sender,lambda p:p.__setitem__("item_nametag",name));safe_reply(client,f"🏷️ Nametag → {name}",message,cj);return
    if op=="booster":
        e=user_store.get_economy(sender); e.setdefault("active_boosts",{})["shop"]=now_ts()+3600; user_store.update_economy(sender,lambda x:x.update(e));safe_reply(client,"⚡ Shop booster aktif 1 jam.",message,cj);return
    if op=="shophistory": safe_reply(client,"📜\n"+"\n".join(str(x) for x in meta.get("history",[])[-15:]) or "Kosong.",message,cj);return
    if op=="discount": safe_reply(client,f"🏷️ Discount: *{20 if user_store.get_profile(sender).get('premium') else 0}%*",message,cj);return
register_feature_specs("shop",_r2_shop_runner,category="shop")
register_feature_specs("shop",_r2_shop_runner,category="inventory")
