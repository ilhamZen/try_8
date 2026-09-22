"""Economy, mining, stock market, and progression primitives."""
import logging
import os
import random
import threading
import time
import config
from core.storage import _shared_read, _shared_update, buyer_store, user_store
from core.utils import (_is_owner_by_number, log_activity, now_ts, shutdown_event)
def get_rank_tier(level):
    for mn, mx, em, nm in config.RANK_TIERS:
        if mn <= level <= mx:
            return {"emoji": em, "name": nm}
    return {"emoji": "🥚", "name": "Mortal"}
def get_rank_display(level):
    t = get_rank_tier(level)
    return f"{t['emoji']} {t['name']}"
def xp_for_level(lv):
    return 0 if lv <= 1 else 100 * (lv * (lv - 1)) // 2
def level_from_xp(xp):
    lv = 1
    while xp_for_level(lv + 1) <= xp and lv < 1000:
        lv += 1
    return lv
def get_luck(uid):
    if _is_owner_by_number(uid):
        return 0.5
    e = user_store.get_economy(uid)
    ab = e.get("active_boosts", {})
    total = 0.0
    n = now_ts()
    for k, v in list(ab.items()):
        if n > v.get("expires", 0):
            continue
        total += v.get("luck_bonus", 0.0)
    p = user_store.get_profile(uid)
    total += p.get("fishing", {}).get("prestige", 0) * 0.05
    total += p.get("gathering", {}).get("prestige", 0) * 0.05
    return min(1.0, total)
def get_boost_mult(uid):
    if _is_owner_by_number(uid):
        return 99.0
    e = user_store.get_economy(uid)
    base = e.get("boost_multiplier", 1.0)
    for k, v in e.get("active_boosts", {}).items():
        if now_ts() > v.get("expires", 0):
            continue
        base = max(base, v.get("mult", 1.0))
    return base
def get_tokens(uid):
    if _is_owner_by_number(uid):
        return 999_999_999
    return user_store.get_economy(uid).get("tokens", 0)
def add_tokens(uid, amount, source=None):
    if _is_owner_by_number(uid):
        return 999_999_999
    def mut(e):
        cur = e.get("tokens", 0)
        e["tokens"] = min(config.TOKEN_CAP, cur + amount)
    user_store.update_economy(uid, mut)
    if amount > 0:
        log_activity(uid, "tokens_add", {"amount": amount, "source": source or "unknown"})
    return get_tokens(uid)
def deduct_tokens(uid, amount, source=None):
    if _is_owner_by_number(uid):
        return True, 999_999_999
    r = {"ok": False, "rem": 0}
    def mut(e):
        cur = e.get("tokens", 0)
        if cur < amount:
            r["rem"] = cur
            return
        e["tokens"] = cur - amount
        r["ok"] = True
        r["rem"] = e["tokens"]
    user_store.update_economy(uid, mut)
    if r["ok"] and amount > 0:
        log_activity(uid, "tokens_deduct", {"amount": amount, "source": source or "unknown"})
    return r["ok"], r["rem"]
def get_cash(uid):
    if _is_owner_by_number(uid):
        return 999_999_999
    return user_store.get_economy(uid).get("cash", 0)
def add_cash(uid, amount, source=None):
    if _is_owner_by_number(uid):
        return 999_999_999
    def mut(e):
        e["cash"] = e.get("cash", 0) + amount
    user_store.update_economy(uid, mut)
    if amount > 0:
        log_activity(uid, "cash_add", {"amount": amount, "source": source or "unknown"})
    return get_cash(uid)
def deduct_cash(uid, amount, source=None):
    if _is_owner_by_number(uid):
        return True, 999_999_999
    r = {"ok": False, "rem": 0}
    def mut(e):
        cur = e.get("cash", 0)
        if cur < amount:
            r["rem"] = cur
            return
        e["cash"] = cur - amount
        r["ok"] = True
        r["rem"] = e["cash"]
    user_store.update_economy(uid, mut)
    if r["ok"] and amount > 0:
        log_activity(uid, "cash_deduct", {"amount": amount, "source": source or "unknown"})
    return r["ok"], r["rem"]
def miner_level_for(uid):
    if _is_owner_by_number(uid):
        return 10
    p = user_store.get_profile(uid)
    total = p.get("total_mined", 0)
    lvl = 1
    for i, t in enumerate(config.MINER_LEVEL_THRESHOLDS):
        if total >= t:
            lvl = i + 1
    if p.get("premium"):
        lvl = min(10, lvl + 1)
    if buyer_store.is_buyer(uid):
        lvl = min(10, lvl + 1)
    return lvl
class MiningSession:
    def __init__(self, uid, dur=config.MINER_MAX_DURATION):
        self.uid = uid
        self.duration = dur
        self.started = now_ts()
        self.stop_event = threading.Event()
        self.thread = None
        self.collected = {}
        self.total_yield = 0
        self.level = miner_level_for(uid)
        cfg = config.MINER_LEVELS.get(self.level, config.MINER_LEVELS[1])
        self.interval = cfg["interval"]
        self.items_min = cfg["items_min"]
        self.items_max = cfg["items_max"]
        self.bonus_chance = cfg["bonus_chance"]
        self.high_tier_chance = cfg["high_tier_chance"]
        self.max_items = cfg["max_items"]
    def is_alive(self):
        return self.thread and self.thread.is_alive() and not self.stop_event.is_set()
    def elapsed(self):
        return now_ts() - self.started
    def progress_pct(self):
        return min(100.0, self.elapsed() / self.duration * 100) if self.duration > 0 else 100
    def _run(self):
        try:
            while not self.stop_event.is_set():
                if shutdown_event.is_set():
                    break
                if self.elapsed() >= self.duration or self.total_yield >= self.max_items:
                    break
                for _ in range(int(self.interval * 10)):
                    if self.stop_event.is_set() or shutdown_event.is_set():
                        break
                    time.sleep(0.1)
                if self.stop_event.is_set() or shutdown_event.is_set():
                    break
                luck = get_luck(self.uid)
                bonus = 1 if (luck > 0 and random.random() < min(0.5, luck)) or \
                             (self.bonus_chance > 0 and random.random() < self.bonus_chance) else 0
                n = random.randint(self.items_min, self.items_max) + bonus
                for _ in range(n):
                    if self.total_yield >= self.max_items:
                        break
                    candidates = [k for k, d in config.SHOP_ITEM_DEFS.items()
                                  if d.get("category", "") not in ("premium", "nametag")]
                    if not candidates:
                        break
                    item = random.choice(candidates)
                    defn = config.SHOP_ITEM_DEFS.get(item, {})
                    lvl = 1
                    if defn.get("category") == "potion":
                        lvl = random.randint(3, 6) if random.random() < min(0.8, self.high_tier_chance + luck) else random.randint(1, 2)
                    user_store.add_item(self.uid, item, qty=1, level=lvl, source="miner")
                    fk = f"{item}_{lvl}" if lvl > 1 else item
                    self.collected[fk] = self.collected.get(fk, 0) + 1
                    self.total_yield += 1
            event_manager.progress(self.uid, "mine", self.total_yield)
        except Exception as e:
            logging.error(f"[MINER] {e}")
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    def stop(self):
        self.stop_event.set()
class MinerManager:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.RLock()
    def is_mining(self, uid):
        with self.lock:
            s = self.sessions.get(uid)
            if not s:
                return False
            if not s.is_alive():
                self.sessions.pop(uid, None)
                return False
            return True
    def start(self, uid):
        with self.lock:
            if self.is_mining(uid):
                return False, "Sedang mining!"
            self.sessions.pop(uid, None)
            s = MiningSession(uid)
            self.sessions[uid] = s
            s.start()
            return True, "OK"
    def stop(self, uid):
        with self.lock:
            s = self.sessions.get(uid)
            if not s:
                return False, None
            s.stop()
            if s.thread:
                s.thread.join(timeout=2.0)
            self.sessions.pop(uid, None)
            return True, s
    def stop_all(self):
        with self.lock:
            for uid in list(self.sessions.keys()):
                try:
                    self.stop(uid)
                except Exception:
                    pass
    def get_status(self, uid):
        with self.lock:
            s = self.sessions.get(uid)
            if not s:
                return None
            if not s.is_alive():
                self.sessions.pop(uid, None)
                return None
            return s
miner_manager = MinerManager()
class StockMarket:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "stock.json")
    def _init(self):
        def mut(d):
            s = d.setdefault("stocks", {})
            for t, cfg in config.STOCK_TICKERS.items():
                if t not in s:
                    s[t] = {"ticker": t, "id": cfg["id"], "name": cfg["name"],
                            "price": cfg["base_price"], "base_price": cfg["base_price"],
                            "last_update": now_ts(), "high": cfg["base_price"], "low": cfg["base_price"]}
            d.setdefault("global_flow", {})
        _shared_update(self._p(), {"stocks": {}, "global_flow": {}}, mut)
    def _update(self):
        def mut(d):
            s = d.setdefault("stocks", {})
            f = d.setdefault("global_flow", {})
            n = now_ts()
            for t, st in s.items():
                if n - st.get("last_update", n) < config.STOCK_UPDATE_INTERVAL:
                    continue
                ff = f.get(t, {"buys": 0, "sells": 0})
                demand = (ff.get("buys", 0) - ff.get("sells", 0)) * 0.05 / 100
                vol = random.uniform(-config.STOCK_VOLATILITY, config.STOCK_VOLATILITY)
                base = st.get("base_price", 100)
                cur = st.get("price", base)
                rev = (base - cur) / max(base, 1) * 0.05
                np = max(config.STOCK_MIN_PRICE, min(config.STOCK_MAX_PRICE, int(cur * (1 + vol + rev + demand))))
                st["price"] = np
                st["last_update"] = n
                st["high"] = max(st.get("high", np), np)
                st["low"] = min(st.get("low", np), np)
                ff["buys"] = int(ff.get("buys", 0) * 0.9)
                ff["sells"] = int(ff.get("sells", 0) * 0.9)
                f[t] = ff
        _shared_update(self._p(), {"stocks": {}, "global_flow": {}}, mut)
    def get_all(self):
        self._init()
        self._update()
        return _shared_read(self._p(), default={"stocks": {}}).get("stocks", {})
    def get_ordered(self):
        return sorted(self.get_all().items(), key=lambda kv: kv[1].get("id", ""))
    def get_by_order(self, n):
        o = self.get_ordered()
        return o[n - 1][1] if 1 <= n <= len(o) else None
    def buy(self, uid, ticker, qty):
        if _is_owner_by_number(uid):
            return True, f"Beli {qty}× {ticker}"
        s = self.get_all().get(ticker.upper())
        if not s:
            return False, "Ticker tidak ada"
        if qty <= 0:
            return False, "Qty > 0"
        price = s["price"]
        cost = int(price * qty * (1 + config.STOCK_TRADE_FEE))
        ok, rem = deduct_tokens(uid, cost, source="stock_buy")
        if not ok:
            return False, f"Token kurang ({rem})"
        def mut(p):
            h = p.setdefault("holdings", {})
            hh = h.setdefault(ticker, {"qty": 0, "avg_price": 0})
            oq = hh["qty"]
            oa = hh.get("avg_price", 0)
            nq = oq + qty
            hh["avg_price"] = int((oa * oq + price * qty) / nq) if nq > 0 else 0
            hh["qty"] = nq
        user_store.update_profile(uid, mut)
        log_activity(uid, "stock_buy", {"ticker": ticker, "qty": qty, "cost": cost})
        return True, f"Beli {qty}× {ticker} = {cost}"
    def sell(self, uid, ticker, qty):
        s = self.get_all().get(ticker.upper())
        if not s:
            return False, "Ticker tidak ada"
        p = user_store.get_profile(uid)
        h = p.get("holdings", {}).get(ticker, {})
        if h.get("qty", 0) < qty:
            return False, f"Tidak punya {qty}×"
        price = s["price"]
        gain = int(price * qty * (1 - config.STOCK_TRADE_FEE))
        def mut(pp):
            hh = pp.setdefault("holdings", {}).get(ticker, {})
            hh["qty"] = max(0, hh.get("qty", 0) - qty)
            if hh["qty"] <= 0:
                pp["holdings"].pop(ticker, None)
        user_store.update_profile(uid, mut)
        add_tokens(uid, gain, source="stock_sell")
        return True, f"Jual {qty}× {ticker} = +{gain}"
class AchievementManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "achievements.json")
    def get_user(self, uid):
        return dict(_shared_read(self._p(), default={"users": {}}).get("users", {}).get(uid, {}))
    def grant(self, uid, key):
        if key not in config.UNIVERSAL_ACHIEVEMENTS:
            return False, None
        r = {"new": False}
        def mut(d):
            u = d.setdefault("users", {}).setdefault(uid, {})
            if key not in u:
                u[key] = now_ts()
                r["new"] = True
        _shared_update(self._p(), {"users": {}}, mut)
        return (r["new"], config.UNIVERSAL_ACHIEVEMENTS[key]) if r["new"] else (False, None)
    def check_all(self, uid):
        p = user_store.get_profile(uid)
        e = user_store.get_economy(uid)
        tok = e.get("tokens", 0)
        fish = p.get("fishing", {})
        gath = p.get("gathering", {})
        ft = fish.get("total_catch", 0)
        gt = gath.get("total_gather", 0)
        fm = fish.get("rarity_count", {}).get("mythic", 0)
        pt = fish.get("prestige", 0) + gath.get("prestige", 0)
        mined = p.get("total_mined", 0)
        grants = []
        if tok >= 1000:
            grants.append("token_1k")
        if tok >= 2000:
            grants.append("token_2k")
        if tok >= config.TOKEN_CAP:
            grants.append("token_max")
        if ft >= 10:
            grants.append("fish_10")
        if ft >= 100:
            grants.append("fish_100")
        if ft >= 1000:
            grants.append("fish_1000")
        if fm >= 1:
            grants.append("fish_mythic")
        if gt >= 10:
            grants.append("gather_10")
        if gt >= 100:
            grants.append("gather_100")
        if gt >= 1000:
            grants.append("gather_1000")
        if pt >= 1:
            grants.append("prestige_1")
        if pt >= 3:
            grants.append("prestige_3")
        if pt >= 5:
            grants.append("prestige_5")
        if pt >= 8:
            grants.append("prestige_8")
        if mined >= 1000:
            grants.append("mine_1000")
        if mined >= 10000:
            grants.append("mine_10000")
        for k in grants:
            self.grant(uid, k)
achievement_manager = AchievementManager()
stock_market = StockMarket()
