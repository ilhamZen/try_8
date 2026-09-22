"""JSON-backed persistence stores used by CINNAMON v53."""
import json, hashlib, logging, os, re, secrets, shutil, tempfile, threading, time
from pathlib import Path
import config
from core.utils import (_digits_match, _is_owner_by_number, _strip_device, log_activity, now_ts)
def _identity_registry(): from core.identity import identity_registry; return identity_registry
def _owner_uid():
    from handlers.auth import owner_uid
    return owner_uid()
_shared_locks = {}
_shared_locks_lock = threading.Lock()
def atomic_json_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except Exception as e:
        logging.error(f"[ATOMIC] {path}: {e}")
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        return False
def atomic_json_read(path, default=None):
    path = Path(path)
    if not path.exists():
        return dict(default) if default else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(default) if default else {}
def _get_shared_lock(name):
    with _shared_locks_lock:
        if name not in _shared_locks:
            _shared_locks[name] = threading.RLock()
        return _shared_locks[name]
def _shared_update(path, default, mutator):
    name = os.path.basename(path)
    lock = _get_shared_lock(name)
    with lock:
        data = atomic_json_read(path, default=default)
        mutator(data)
        atomic_json_write(path, data)
        return data
def _shared_read(path, default=None):
    return atomic_json_read(path, default=default)
def load_owner_registry():
    data = _shared_read(config.OWNER_REGISTRY_PATH, default={"owners": []})
    return set(data.get("owners", []))
def save_owner_registry(owners_set):
    def mut(d):
        d["owners"] = list(owners_set)
    _shared_update(config.OWNER_REGISTRY_PATH, {"owners": []}, mut)
def is_registered_owner(uid_or_jid):
    reg = load_owner_registry()
    if not reg:
        return False
    for oid in reg:
        if _digits_match(uid_or_jid, oid):
            return True
    return False
def add_owner_registry(uid):
    reg = load_owner_registry()
    reg.add(uid)
    save_owner_registry(reg)
def remove_owner_registry(uid):
    reg = load_owner_registry()
    to_remove = [o for o in reg if _digits_match(uid, o)]
    for o in to_remove:
        reg.discard(o)
    save_owner_registry(reg)
def load_owner_number():
    data = _shared_read(config.OWNER_CONFIG_PATH, default={"number": ""})
    saved = data.get("number", "")
    if saved and re.sub(r"\D", "", saved):
        config.OWNER_NUMBER_DIGITS = re.sub(r"\D", "", saved)
def save_owner_number(num):
    def mut(d):
        d["number"] = num
    _shared_update(config.OWNER_CONFIG_PATH, {}, mut)
class UserDataStore:
    def __init__(self):
        self._locks = {}
        self._locks_lock = threading.Lock()
        self._cache = {}
        self._cache_ttl = 2.0
    def _get_lock(self, uid):
        with self._locks_lock:
            if uid not in self._locks:
                self._locks[uid] = threading.RLock()
            return self._locks[uid]
    def user_dir(self, uid):
        return Path(config.USER_DIR) / uid
    def user_exists(self, uid):
        return self.user_dir(uid).exists()
    def _default_profile(self):
        r={"_schema":3,"name":None,"password_hash":None,"password_salt":None,"registered_at":0,"last_login":0,"logged_in":False,"title":config.GUEST_TITLE,"level":1,"xp":0,"last_xp":0,"premium":False,"premium_expires":0,"bot_disabled":False,"aliases":[],"married_to":None,"sticker_level":3,"total_mined":0,"is_buyer":False,"holdings":{}}
        r["fishing"]={"level":1,"prestige":0,"total_catch":0,"rarity_count":{"common":0,"uncommon":0,"rare":0,"epic":0,"legend":0,"mythic":0},"rod_level":1,"quests_done":[]}
        r["gathering"]={"level":1,"prestige":0,"total_gather":0,"rarity_count":{"common":0,"uncommon":0,"rare":0,"epic":0,"legend":0,"mythic":0},"basket_level":1,"quests_done":[]}; return r
    def _default_inventory(self):
        return {"_schema": 3, "items": []}
    def _default_economy(self):
        return {"_schema":3,"tokens":config.TOKEN_USER_BARU,"cash":0,"daily_last":0,"daily_streak":0,"work_last":0,"rob_last":0,"dailybox_last":0,"active_boosts":{},"game_cooldowns":{},"boost_multiplier":1.0,"boost_expires":0,"fishing_last":0,"gathering_last":0,"fishing_today":0,"gathering_today":0}
    def _default_quest(self):
        return {"_schema": 3, "date": "", "quests": {}, "streak": 0}
    def _cache_get(self, uid):
        c = self._cache.get(uid)
        if c and time.time() - c["ts"] < self._cache_ttl:
            return c
        return None
    def _cache_set(self, uid, data): data["ts"]=time.time(); self._cache[uid]=data
    def invalidate(self, uid): self._cache.pop(uid, None)
    def load_all(self, uid):
        cached = self._cache_get(uid)
        if cached:
            return cached
        with self._get_lock(uid):
            d = self.user_dir(uid)
            data = {"profile":atomic_json_read(d/"profile.json",default=self._default_profile()),"inventory":atomic_json_read(d/"inventory.json",default=self._default_inventory()),"economy":atomic_json_read(d/"economy.json",default=self._default_economy()),"quest":atomic_json_read(d/"quest.json",default=self._default_quest())}
            self._cache_set(uid, data)
            return data
    def get_profile(self, uid):
        return dict(self.load_all(uid)["profile"])
    def get_inventory(self, uid):
        return list(self.load_all(uid)["inventory"].get("items", []))
    def get_economy(self, uid):
        return dict(self.load_all(uid)["economy"])
    def _write_section(self, uid, sec, data):
        p = self.user_dir(uid) / f"{sec}.json"
        ok = atomic_json_write(p, data)
        self.invalidate(uid)
        return ok
    def update_profile(self, uid, mut):
        with self._get_lock(uid):
            self.invalidate(uid)
            p = self.get_profile(uid)
            mut(p)
            self._write_section(uid, "profile", p)
    def update_economy(self, uid, mut):
        with self._get_lock(uid):
            self.invalidate(uid)
            e = atomic_json_read(self.user_dir(uid) / "economy.json", default=self._default_economy())
            mut(e)
            self._write_section(uid, "economy", e)
    def add_item(self, uid, key, qty=1, level=1, source=None):
        try:
            qty = int(qty)
            level = int(level)
        except (TypeError, ValueError):
            return False
        if qty <= 0 or level <= 0 or not uid or not key:
            return False
        self.user_dir(uid).mkdir(parents=True, exist_ok=True)
        with self._get_lock(uid):
            self.invalidate(uid)
            inv = atomic_json_read(self.user_dir(uid) / "inventory.json", default=self._default_inventory())
            items = inv.setdefault("items", [])
            found = None
            for it in items:
                if it.get("key") == key and it.get("level", 1) == level:
                    found = it
                    break
            if found:
                found["qty"] = found.get("qty", 0) + qty
            else:
                items.append({"key": key, "level": level, "qty": qty})
            ok = atomic_json_write(self.user_dir(uid) / "inventory.json", inv)
            self.invalidate(uid)
            if ok:
                log_activity(uid, "item_add", {"key": key, "qty": qty, "level": level, "source": source or "unknown"})
            return ok
    def remove_item(self, uid, key, qty=1, level=1, source=None):
        if _is_owner_by_number(uid):
            return True
        result = {"ok": False}
        with self._get_lock(uid):
            self.invalidate(uid)
            inv = atomic_json_read(self.user_dir(uid) / "inventory.json", default=self._default_inventory())
            items = inv.setdefault("items", [])
            for i, it in enumerate(items):
                if it.get("key") == key and it.get("level", 1) == level:
                    if it.get("qty", 0) < qty:
                        return False
                    it["qty"] -= qty
                    if it["qty"] <= 0:
                        items.pop(i)
                    result["ok"] = True
                    break
            if result["ok"]:
                atomic_json_write(self.user_dir(uid) / "inventory.json", inv)
                self.invalidate(uid)
                log_activity(uid, "item_remove", {"key": key, "qty": qty, "level": level, "source": source or "unknown"})
            return result["ok"]
    def item_count(self, uid, key, level=1):
        inv = atomic_json_read(self.user_dir(uid) / "inventory.json", default=self._default_inventory())
        for it in inv.get("items", []):
            if it.get("key") == key and it.get("level", 1) == level:
                return it.get("qty", 0)
        return 0
    def create_user(self, uid, name, ph, salt):
        d = self.user_dir(uid)
        d.mkdir(parents=True, exist_ok=True)
        p = self._default_profile()
        p["name"] = name
        p["password_hash"] = ph
        p["password_salt"] = salt
        p["registered_at"] = now_ts()
        p["last_login"] = now_ts()
        p["logged_in"] = True
        p["title"] = config.REGISTER_TITLE
        atomic_json_write(d / "profile.json", p)
        atomic_json_write(d / "inventory.json", self._default_inventory())
        atomic_json_write(d / "economy.json", self._default_economy())
        atomic_json_write(d / "quest.json", self._default_quest())
        self.invalidate(uid)
        if name:
            _identity_registry().register_user(uid, name=name)
        log_activity(uid, "register", {"name": name})
        return True
    def delete_user(self, uid):
        try:
            shutil.rmtree(self.user_dir(uid))
        except Exception:
            pass
        self.invalidate(uid)
    def register_alias(self, primary_uid, alias_uid):
        if not primary_uid or not alias_uid or primary_uid == alias_uid:
            return
        with self._get_lock(primary_uid):
            self.invalidate(primary_uid)
            p = self.get_profile(primary_uid)
            aliases = p.setdefault("aliases", [])
            if alias_uid not in aliases:
                aliases.append(alias_uid)
            self._write_section(primary_uid, "profile", p)
        _identity_registry().add_alias(primary_uid, alias_uid)
    def find_by_alias(self, alias_uid):
        if not alias_uid:
            return None
        r = _identity_registry().find_uid_by_alias(alias_uid)
        if r and self.user_exists(r):
            return r
        for ud in Path(config.USER_DIR).iterdir():
            if not ud.is_dir():
                continue
            p = atomic_json_read(ud / "profile.json", default={})
            if alias_uid in (p.get("aliases", []) or []):
                return ud.name
            if (p.get("name") or "").lower() == str(alias_uid).lower():
                return ud.name
        return None
    def find_by_name(self, name):
        """★ v52: name lookup via identity_registry + folder scan."""
        if not name:
            return None
        r = _identity_registry().find_uid_by_name(name)
        if r and self.user_exists(r):
            return r
        target = name.lower()
        for ud in Path(config.USER_DIR).iterdir():
            if not ud.is_dir():
                continue
            p = atomic_json_read(ud / "profile.json", default={})
            if (p.get("name") or "").lower() == target:
                return ud.name
        return None
    def find_by_any(self, *candidates):
        """★ v52: try each candidate as UID / alias / name."""
        for c in candidates:
            if not c:
                continue
            c_s = _strip_device(c)
            if not c_s:
                continue
            if self.user_exists(c_s):
                return c_s
            r = self.find_by_alias(c_s)
            if r:
                return r
            r = self.find_by_name(c_s)
            if r:
                return r
            for ud in Path(config.USER_DIR).iterdir():
                if not ud.is_dir():
                    continue
                if _digits_match(ud.name, c_s):
                    return ud.name
        return None
class OwnerDataStore:
    def __init__(self):
        self._lock = threading.RLock()
    def _dir(self, uid):
        return Path(config.OWNER_DIR) / uid
    def _path(self, uid):
        return self._dir(uid) / "owner_panel.json"
    def get(self, uid):
        with self._lock:
            if not self._path(uid).exists():
                return None
            return atomic_json_read(self._path(uid), default={})
    def ensure(self, uid, username=None):
        with self._lock:
            d = self._dir(uid)
            d.mkdir(parents=True, exist_ok=True)
            info = atomic_json_read(self._path(uid), default={})
            info.setdefault("_schema", 1)
            info.setdefault("uid", uid)
            info.setdefault("created_at", now_ts())
            info["last_seen"] = now_ts()
            if username:
                info["username"] = username
            info.setdefault("roles", ["owner"])
            atomic_json_write(self._path(uid), info)
            return info
    def audit(self, uid, action, detail=None):
        with self._lock:
            d = self._dir(uid)
            d.mkdir(parents=True, exist_ok=True)
            rec = {"ts": round(now_ts(), 2),
                   "when": datetime.now(config.WIB).strftime("%Y-%m-%d %H:%M:%S"),
                   "action": action}
            if detail is not None:
                rec["detail"] = detail
            with open(d / "audit.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
class BuyerStore:
    def __init__(self):
        self._lock = threading.RLock()
    def _dir(self, uid):
        return Path(config.BUYER_DIR) / uid
    def _path(self, uid):
        return self._dir(uid) / "buyer_info.json"
    def _audit_path(self, uid):
        return self._dir(uid) / "audit.log"
    def _defaults(self, uid, package="weekly", days=7, created_by=None):
        now = now_ts()
        return {
            "_schema": 2,
            "uid": uid,
            "package": package,
            "since": now,
            "expires": now + days * 86400 if days > 0 else 0,
            "duration_days": days,
            "duration_set_by": created_by or _owner_uid(),
            "bound_groups": [],
            "self_mode": False,
            "airdrop_hours": [8, 14, 20],
            "features": {
                "group_management": True,
                "reminder": True,
                "shop": True,
                "fishing": True,
                "gathering": True,
            },
        }
    def get(self, uid):
        with self._lock:
            path = self._path(uid)
            if not path.exists():
                return None
            info = atomic_json_read(path, default={})
            exp = info.get("expires", 0)
            if exp > 0 and now_ts() > exp:
                try:
                    shutil.rmtree(self._dir(uid))
                except Exception:
                    pass
                return None
            info.setdefault("_schema", 2)
            info.setdefault("duration_days", 0 if exp == 0 else max(1, round((exp - info.get("since", now_ts())) / 86400)))
            info.setdefault("duration_set_by", _owner_uid())
            info.setdefault("bound_groups", [])
            info.setdefault("self_mode", False)
            info.setdefault("airdrop_hours", [8, 14, 20])
            info.setdefault("features", {})
            return info
    def is_buyer(self, uid):
        return self.get(uid) is not None
    def create(self, uid, package="weekly", days=7, created_by=None):
        days = max(0, min(int(days), config.BUYER_MAX_DAYS))
        with self._lock:
            d = self._dir(uid)
            d.mkdir(parents=True, exist_ok=True)
            info = self._defaults(uid, package=package, days=days, created_by=created_by)
            atomic_json_write(self._path(uid), info)
            self._audit_unlocked(uid, "create", {"package": package, "days": days, "by": created_by or _owner_uid()})
            return info
    def update(self, uid, mut):
        with self._lock:
            info = atomic_json_read(self._path(uid), default={})
            if not info:
                return False
            mut(info)
            atomic_json_write(self._path(uid), info)
            return True
    def renew(self, uid, days, actor_uid=None, reason="renew"):
        days = int(days)
        if days <= 0 or days > config.BUYER_MAX_DAYS:
            return False, None
        with self._lock:
            info = self.get(uid)
            if not info:
                return False, None
            now = now_ts()
            base = max(now, info.get("expires", 0)) if info.get("expires", 0) else now
            info["expires"] = base + days * 86400
            info["duration_days"] = int(info.get("duration_days", 0) or 0) + days
            info["renewed_at"] = now
            info["duration_set_by"] = actor_uid or _owner_uid()
            atomic_json_write(self._path(uid), info)
            self._audit_unlocked(uid, reason, {"days": days, "by": actor_uid or _owner_uid(), "expires": info["expires"]})
            return True, info
    def set_expiry(self, uid, expires, actor_uid=None):
        with self._lock:
            info = self.get(uid)
            if not info:
                return False, None
            info["expires"] = max(0, float(expires))
            info["duration_set_by"] = actor_uid or _owner_uid()
            atomic_json_write(self._path(uid), info)
            self._audit_unlocked(uid, "set_expiry", {"by": actor_uid or _owner_uid(), "expires": info["expires"]})
            return True, info
    def remove_group(self, uid, group_jid):
        with self._lock:
            info = self.get(uid)
            if not info:
                return False
            groups = info.setdefault("bound_groups", [])
            before = len(groups)
            info["bound_groups"] = [g for g in groups if g != group_jid]
            atomic_json_write(self._path(uid), info)
            return len(info["bound_groups"]) != before
    def remaining_seconds(self, uid):
        info = self.get(uid)
        if not info:
            return 0
        exp = info.get("expires", 0)
        if not exp:
            return None
        return max(0, int(exp - now_ts()))
    def _audit_unlocked(self, uid, action, detail=None):
        d = self._dir(uid)
        d.mkdir(parents=True, exist_ok=True)
        rec = {"ts": round(now_ts(), 2),
               "when": datetime.now(config.WIB).strftime("%Y-%m-%d %H:%M:%S"),
               "action": action}
        if detail is not None:
            rec["detail"] = detail
        try:
            with open(self._audit_path(uid), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    def audit(self, uid, action, detail=None):
        with self._lock:
            self._audit_unlocked(uid, action, detail)
    def delete(self, uid, actor_uid=None):
        with self._lock:
            try:
                shutil.rmtree(self._dir(uid))
            except Exception:
                pass
            if actor_uid:
                log_activity(actor_uid, "buyer_delete", {"target": uid})
    def list_active(self):
        r = []
        for d in Path(config.BUYER_DIR).iterdir():
            if not d.is_dir():
                continue
            info = self.get(d.name)
            if info:
                r.append((d.name, info))
        return r
class GroupIDManager:
    def get_or_create(self, chat_jid):
        ck = safe_jid_str(chat_jid)
        if not ck:
            return "NYX-UNKNOWN"
        path = os.path.join(config.SHARED_DIR, "group_ids.json")
        r = {"gid": None}
        def mut(d):
            groups = d.setdefault("groups", {})
            by_id = d.setdefault("by_id", {})
            if ck in groups:
                r["gid"] = groups[ck]
                return
            for _ in range(10):
                gid = "NYX-" + secrets.token_hex(4).upper()
                if gid not in by_id:
                    groups[ck] = gid
                    by_id[gid] = ck
                    r["gid"] = gid
                    return
            gid = "NYX-" + hashlib.md5(ck.encode()).hexdigest()[:8].upper()
            groups[ck] = gid
            by_id[gid] = ck
            r["gid"] = gid
        _shared_update(path, {"groups": {}, "by_id": {}}, mut)
        return r["gid"] or "NYX-UNKNOWN"
class BanManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "bans.json")
    def is_user_banned(self, uid):
        return _shared_read(self._p(), default={"users": {}}).get("users", {}).get(uid)
    def is_ip_banned(self, ip):
        if not ip:
            return None
        return _shared_read(self._p(), default={"ips": {}}).get("ips", {}).get(ip)
    def ban_user(self, uid, reason=""):
        if _is_owner_by_number(uid):
            return False, "Tidak bisa ban owner"
        def mut(d):
            d.setdefault("users", {})[uid] = {"reason": reason or "-", "ts": now_ts()}
        _shared_update(self._p(), {"users": {}, "ips": {}}, mut)
        return True, f"{config.SYM_CHECK} Banned `{uid}`"
    def unban_user(self, uid):
        if not self.is_user_banned(uid):
            return False, "Tidak di-ban"
        def mut(d):
            d.setdefault("users", {}).pop(uid, None)
        _shared_update(self._p(), {"users": {}, "ips": {}}, mut)
        return True, f"{config.SYM_CHECK} Unbanned"
    def ban_ip(self, ip, reason=""):
        if not ip:
            return False, "IP kosong"
        def mut(d):
            d.setdefault("ips", {})[ip] = {"reason": reason or "-", "ts": now_ts()}
        _shared_update(self._p(), {"users": {}, "ips": {}}, mut)
        return True, f"{config.SYM_CHECK} Banned IP"
    def unban_ip(self, ip):
        if not self.is_ip_banned(ip):
            return False, "IP tidak di-ban"
        def mut(d):
            d.setdefault("ips", {}).pop(ip, None)
        _shared_update(self._p(), {"users": {}, "ips": {}}, mut)
        return True, f"{config.SYM_CHECK} Unbanned IP"
    def list_bans(self):
        d = _shared_read(self._p(), default={"users": {}, "ips": {}})
        return list(d.get("users", {}).items()), list(d.get("ips", {}).items())
user_store = UserDataStore()
owner_store = OwnerDataStore()
buyer_store = BuyerStore()
group_id_manager = GroupIDManager()
ban_manager = BanManager()
class FeatureToggleManager:
    def _p(self):
        return os.path.join(config.SHARED_DIR, "features.json")
    def is_enabled(self, role, feature):
        if role not in ("owner", "admin", "buyer", "user"):
            return True
        if feature not in config.FEATURE_CATEGORIES:
            return True
        return _shared_read(self._p(), default={}).get(role, {}).get(feature, True)
    def toggle(self, role, feature):
        if role not in ("owner", "admin", "buyer", "user"):
            return False, "Role invalid", False
        if feature not in config.FEATURE_CATEGORIES:
            return False, "Feature invalid", False
        ns = {"v": True}
        def mut(d):
            r = d.setdefault(role, {})
            cur = r.get(feature, True)
            new = not cur
            r[feature] = new
            ns["v"] = new
        _shared_update(self._p(), {}, mut)
        return True, f"*{role}* / `{feature}` {config.SYM_ARROW} {config.SYM_CHECK + ' ON' if ns['v'] else config.SYM_CROSS + ' OFF'}", ns["v"]
    def set_role(self, role, feature, state):
        if role not in ("owner", "admin", "buyer", "user"):
            return False, "Role invalid"
        if feature not in config.FEATURE_CATEGORIES:
            return False, "Feature invalid"
        def mut(d):
            d.setdefault(role, {})[feature] = state
        _shared_update(self._p(), {}, mut)
        return True, f"{config.SYM_CHECK} {role}/{feature} = {'ON' if state else 'OFF'}"
    def get_role_status(self, role):
        d = _shared_read(self._p(), default={}).get(role, {})
        return {f: d.get(f, True) for f in config.FEATURE_CATEGORIES}
feature_toggle = FeatureToggleManager()
def __getattr__(name):
    if name in {"PendingStore", "pending_store"}:
        from handlers.auth import PendingStore, pending_store
        return PendingStore if name == "PendingStore" else pending_store
    if name in {"EventManager", "event_manager"}:
        from handlers.event import EventManager, event_manager
        return EventManager if name == "EventManager" else event_manager
    if name in {"AchievementManager", "achievement_manager"}:
        from core.economy import AchievementManager, achievement_manager
        return AchievementManager if name == "AchievementManager" else achievement_manager
    raise AttributeError(name)
