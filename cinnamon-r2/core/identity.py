"""Persistent WhatsApp LID/PN identity resolution."""
import logging
import os
import re
import sqlite3
import threading
import time
import shutil
from pathlib import Path
import config
from core.storage import atomic_json_read, atomic_json_write
from core.utils import (_bare_lid, _digits_match, _is_lid, _is_pn, _stable_key, _strip_device, log_activity, now_ts, safe_jid_str)
class IdentityRegistry:
    """
    Persistent identity registry.
    Stores:
      - users: {canonical_uid: {name, aliases, registered_at, last_seen}}
      - lid_to_pn: {lid: pn}
      - pn_to_lid: {pn: lid}
      - name_index: {name_lower: canonical_uid}
      - raw_to_canonical: {stable_key: canonical_uid}  ← v52 NEW
    """
    def __init__(self):
        self._path = os.path.join(config.SHARED_DIR, "identity.json")
        self._lock = threading.RLock()
        self._cache = None
        self._cache_ts = 0
        self._ttl = 2.0
    def _empty(self):
        return {"users": {}, "lid_to_pn": {}, "pn_to_lid": {},
                "name_index": {}, "raw_to_canonical": {}}
    def _load(self):
        with self._lock:
            now = time.time()
            if self._cache and now - self._cache_ts < self._ttl:
                return self._cache
            data = atomic_json_read(self._path, default=self._empty())
            for k in ("users", "lid_to_pn", "pn_to_lid", "name_index", "raw_to_canonical"):
                data.setdefault(k, {})
            self._cache = data
            self._cache_ts = now
            return data
    def _save(self, data):
        atomic_json_write(self._path, data)
        self._cache = data
        self._cache_ts = time.time()
    def invalidate(self):
        with self._lock:
            self._cache = None
    def link_lid_pn(self, lid, pn):
        if not lid or not pn:
            return
        lid = _strip_device(lid)
        pn = _strip_device(pn)
        if not _is_lid(lid) and not _is_pn(pn):
            return
        with self._lock:
            data = self._load()
            data["lid_to_pn"][lid] = pn
            data["pn_to_lid"][pn] = lid
            bare = _bare_lid(lid)
            if bare and bare != lid:
                data["lid_to_pn"][bare] = pn
            self._save(data)
    def resolve_lid_to_pn(self, lid):
        if not lid:
            return None
        lid = _strip_device(lid)
        bare = _bare_lid(lid)
        with self._lock:
            data = self._load()
            if lid in data["lid_to_pn"]:
                return data["lid_to_pn"][lid]
            if bare in data["lid_to_pn"]:
                return data["lid_to_pn"][bare]
            for k, v in data["lid_to_pn"].items():
                if _bare_lid(k) == bare:
                    return v
        return None
    def resolve_pn_to_lid(self, pn):
        if not pn:
            return None
        pn = _strip_device(pn)
        with self._lock:
            data = self._load()
            return data["pn_to_lid"].get(pn)
    def register_user(self, uid, name=None, aliases=None):
        if not uid:
            return
        uid = _strip_device(uid)
        with self._lock:
            data = self._load()
            u = data["users"].setdefault(uid, {
                "aliases": [], "name": None,
                "registered_at": now_ts(), "last_seen": now_ts()
            })
            if name:
                u["name"] = name
                data["name_index"][name.lower()] = uid
            if aliases:
                for a in aliases:
                    a = _strip_device(a)
                    if a and a not in u["aliases"]:
                        u["aliases"].append(a)
            u["last_seen"] = now_ts()
            self._save(data)
    def find_uid_by_alias(self, alias):
        if not alias:
            return None
        alias_s = _strip_device(alias)
        with self._lock:
            data = self._load()
            if alias_s in data["users"]:
                return alias_s
            for uid, u in data["users"].items():
                if alias_s in u.get("aliases", []):
                    return uid
            for uid in data["users"].keys():
                if _digits_match(uid, alias_s):
                    return uid
        return None
    def find_uid_by_name(self, name):
        if not name:
            return None
        with self._lock:
            data = self._load()
            return data["name_index"].get(name.lower())
    def add_alias(self, uid, alias):
        if not uid or not alias:
            return
        uid = _strip_device(uid)
        alias = _strip_device(alias)
        with self._lock:
            data = self._load()
            u = data["users"].setdefault(uid, {
                "aliases": [], "name": None,
                "registered_at": now_ts(), "last_seen": now_ts()
            })
            if alias not in u["aliases"]:
                u["aliases"].append(alias)
            self._save(data)
    def get_user(self, uid):
        with self._lock:
            data = self._load()
            return data["users"].get(_strip_device(uid))
    def all_users(self):
        with self._lock:
            data = self._load()
            return dict(data["users"])
    def set_session_canonical(self, stable_key, canonical_uid):
        if not stable_key or not canonical_uid:
            return
        stable_key = _stable_key(stable_key)
        canonical_uid = _strip_device(canonical_uid)
        with self._lock:
            data = self._load()
            data["raw_to_canonical"][stable_key] = canonical_uid
            self._save(data)
    def get_session_canonical(self, stable_key):
        if not stable_key:
            return None
        stable_key = _stable_key(stable_key)
        with self._lock:
            data = self._load()
            return data["raw_to_canonical"].get(stable_key)
    def clear_session_canonical(self, stable_key):
        if not stable_key:
            return
        stable_key = _stable_key(stable_key)
        with self._lock:
            data = self._load()
            data["raw_to_canonical"].pop(stable_key, None)
            self._save(data)
identity_registry = IdentityRegistry()
class SessionIdentityManager:
    """
    Resolves raw sender → canonical UID with caching + auto-heal.
    Priority:
      1. identity_registry.raw_to_canonical (fastest, persistent)
      2. identity_registry.find_uid_by_alias
      3. session.db whatsmeow_lid_map
      4. message alt (SenderAlt / ParticipantAlt)
      5. folder scan by name/alias
      6. fallback raw
    """
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
        self._ttl = 10.0
    def _cached(self, key):
        with self._lock:
            c = self._cache.get(key)
            if c and time.time() - c["ts"] < self._ttl:
                return c
        return None
    def _set(self, key, uid, method):
        with self._lock:
            self._cache[key] = {"uid": uid, "method": method, "ts": time.time()}
    def _auto_merge(self, canonical_uid, alias_uid):
        """Move legacy/fragmented user state into the canonical folder when both exist."""
        if not canonical_uid or not alias_uid:
            return
        canonical_uid = _strip_device(canonical_uid)
        alias_uid = _strip_device(alias_uid)
        if canonical_uid == alias_uid:
            return
        try:
            merge_fn = globals().get("merge_fragmented_folders")
            if callable(merge_fn):
                ok, detail = merge_fn(canonical_uid, alias_uid)
                if ok:
                    logging.info(f"[IDENTITY] auto-merged {alias_uid} -> {canonical_uid}: {detail}")
        except Exception as e:
            logging.debug(f"[IDENTITY] auto-merge {alias_uid}->{canonical_uid}: {e}")
    def resolve(self, raw_sender, client=None, alt=None):
        raw = _strip_device(raw_sender)
        stable = _stable_key(raw)
        c = self._cached(stable)
        if c:
            return c["uid"], c["method"]
        mapped = identity_registry.get_session_canonical(stable)
        if mapped:
            self._set(stable, mapped, "session-map")
            return mapped, "session-map"
        alias_uid = identity_registry.find_uid_by_alias(raw)
        if alias_uid:
            identity_registry.set_session_canonical(stable, alias_uid)
            self._auto_merge(alias_uid, raw)
            self._set(stable, alias_uid, "alias")
            return alias_uid, "alias"
        if _is_pn(raw):
            identity_registry.set_session_canonical(stable, raw)
            self._set(stable, raw, "pn")
            return raw, "pn"
        if _is_lid(raw):
            pn = identity_registry.resolve_lid_to_pn(raw)
            if pn:
                identity_registry.set_session_canonical(stable, pn)
                identity_registry.add_alias(pn, raw)
                self._auto_merge(pn, raw)
                self._set(stable, pn, "identity-lid")
                return pn, "identity-lid"
            session_map = _session_lid_map()
            for k, v in session_map.items():
                if _strip_device(k) == raw or _bare_lid(k) == _bare_lid(raw):
                    pn = _strip_device(v)
                    if pn and _is_pn(pn):
                        identity_registry.link_lid_pn(raw, pn)
                        identity_registry.set_session_canonical(stable, pn)
                        identity_registry.add_alias(pn, raw)
                        self._auto_merge(pn, raw)
                        self._set(stable, pn, "session-db")
                        return pn, "session-db"
                    elif pn and pn.isdigit():
                        pn_full = f"{pn}@s.whatsapp.net"
                        identity_registry.link_lid_pn(raw, pn_full)
                        identity_registry.set_session_canonical(stable, pn_full)
                        identity_registry.add_alias(pn_full, raw)
                        self._auto_merge(pn_full, raw)
                        self._set(stable, pn_full, "session-db-digits")
                        return pn_full, "session-db-digits"
            if alt:
                alt_s = _strip_device(str(alt))
                if _is_pn(alt_s):
                    identity_registry.link_lid_pn(raw, alt_s)
                    identity_registry.set_session_canonical(stable, alt_s)
                    identity_registry.add_alias(alt_s, raw)
                    self._auto_merge(alt_s, raw)
                    self._set(stable, alt_s, "alt-pn")
                    return alt_s, "alt-pn"
                if alt_s and alt_s.isdigit():
                    alt_full = f"{alt_s}@s.whatsapp.net"
                    identity_registry.link_lid_pn(raw, alt_full)
                    identity_registry.set_session_canonical(stable, alt_full)
                    identity_registry.add_alias(alt_full, raw)
                    self._auto_merge(alt_full, raw)
                    self._set(stable, alt_full, "alt-digits")
                    return alt_full, "alt-digits"
            if client:
                fn = getattr(client, "get_pn_from_lid", None)
                if callable(fn):
                    try:
                        res = fn(raw)
                        if res:
                            pn = _strip_device(str(res))
                            if "@" not in pn and pn.isdigit():
                                pn = f"{pn}@s.whatsapp.net"
                            if _is_pn(pn):
                                identity_registry.link_lid_pn(raw, pn)
                                identity_registry.set_session_canonical(stable, pn)
                                identity_registry.add_alias(pn, raw)
                                self._auto_merge(pn, raw)
                                self._set(stable, pn, "client-method")
                                return pn, "client-method"
                    except Exception:
                        pass
            for ud in Path(config.USER_DIR).iterdir():
                if not ud.is_dir():
                    continue
                p = atomic_json_read(ud / "profile.json", default={})
                if raw in (p.get("aliases") or []):
                    identity_registry.set_session_canonical(stable, ud.name)
                    self._auto_merge(ud.name, raw)
                    self._set(stable, ud.name, "folder-alias")
                    return ud.name, "folder-alias"
            identity_registry.set_session_canonical(stable, raw)
            self._set(stable, raw, "unresolved-lid")
            return raw, "unresolved-lid"
        return raw, "unknown"
session_identity = SessionIdentityManager()
def _find_session_db():
    candidates = [
        config.DB_FILE,
        os.path.join(os.getcwd(), "session.db"),
        os.path.join(os.getcwd(), "whatsapp.db"),
        os.path.join(os.getcwd(), "bot.db"),
        os.path.expanduser("~/.wacli/session.db"),
        os.environ.get("NEONIZE_DB", ""),
        os.environ.get("DB_PATH", ""),
    ]
    for p in candidates:
        if p and os.path.exists(p) and os.path.isfile(p):
            return p
    return None
def _read_session_lid_map():
    db = _find_session_db()
    if not db:
        return {}
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        out = {}
        for row in conn.execute("SELECT lid, pn FROM whatsmeow_lid_map"):
            lid = str(row[0]).strip()
            pn = str(row[1]).strip()
            if lid and pn:
                out[lid] = pn
        conn.close()
        return out
    except Exception as e:
        logging.debug(f"[SESSION_DB] {e}")
        return {}
_SESSION_LID_CACHE = {"data": {}, "ts": 0, "ttl": 30}
def _session_lid_map():
    now = time.time()
    if now - _SESSION_LID_CACHE["ts"] < _SESSION_LID_CACHE["ttl"] and _SESSION_LID_CACHE["data"]:
        return _SESSION_LID_CACHE["data"]
    data = _read_session_lid_map()
    _SESSION_LID_CACHE["data"] = data
    _SESSION_LID_CACHE["ts"] = now
    for lid, pn in data.items():
        try:
            if _is_lid(lid) and pn:
                pn_full = pn if "@" in pn else f"{pn}@s.whatsapp.net"
                identity_registry.link_lid_pn(lid, pn_full)
        except Exception:
            pass
    return data
def register_jid_pair(message):
    try:
        src = message.Info.MessageSource
    except Exception:
        return
    pairs = (
        ("Sender", "SenderAlt"), ("SenderAlt", "Sender"),
        ("Participant", "ParticipantAlt"), ("ParticipantAlt", "Participant"),
        ("Recipient", "RecipientAlt"), ("RecipientAlt", "Recipient"),
    )
    for a_a, b_a in pairs:
        a = getattr(src, a_a, None)
        b = getattr(src, b_a, None)
        if a is None or b is None:
            continue
        s_a = _strip_device(a)
        s_b = _strip_device(b)
        if _is_lid(s_a) and _is_pn(s_b):
            identity_registry.link_lid_pn(s_a, s_b)
        elif _is_lid(s_b) and _is_pn(s_a):
            identity_registry.link_lid_pn(s_b, s_a)
def merge_fragmented_folders(canonical_uid, alias_uid):
    if not canonical_uid or not alias_uid or canonical_uid == alias_uid:
        return False, "invalid"
    src = Path(config.USER_DIR) / alias_uid
    dst = Path(config.USER_DIR) / canonical_uid
    if not src.exists():
        return False, "src_not_found"
    if not dst.exists():
        try:
            src.rename(dst)
            identity_registry.add_alias(canonical_uid, alias_uid)
            return True, "renamed"
        except Exception as e:
            return False, f"rename_fail:{e}"
    if not src.is_dir() or not dst.is_dir():
        return False, "not_dir"
    merged = {"items": 0, "tokens": 0, "cash": 0}
    try:
        src_inv = atomic_json_read(src / "inventory.json", default={"items": []})
        dst_inv = atomic_json_read(dst / "inventory.json", default={"items": []})
        dst_items = dst_inv.setdefault("items", [])
        for sit in src_inv.get("items", []):
            key = sit.get("key")
            lvl = sit.get("level", 1)
            qty = sit.get("qty", 0)
            if not key or qty <= 0:
                continue
            found = False
            for dit in dst_items:
                if dit.get("key") == key and dit.get("level", 1) == lvl:
                    dit["qty"] = dit.get("qty", 0) + qty
                    found = True
                    break
            if not found:
                dst_items.append({"key": key, "level": lvl, "qty": qty})
            merged["items"] += qty
        atomic_json_write(dst / "inventory.json", dst_inv)
    except Exception as e:
        logging.warning(f"[MERGE inv] {e}")
    try:
        src_eco = atomic_json_read(src / "economy.json", default={})
        dst_eco = atomic_json_read(dst / "economy.json", default={})
        for k in ("tokens", "cash"):
            v = src_eco.get(k, 0)
            if v:
                dst_eco[k] = dst_eco.get(k, 0) + v
                merged[k] = v
        for k in ("daily_last", "work_last", "rob_last", "dailybox_last",
                  "fishing_last", "gathering_last"):
            sv = src_eco.get(k, 0)
            dv = dst_eco.get(k, 0)
            if sv and dv:
                dst_eco[k] = min(sv, dv)
            elif sv:
                dst_eco[k] = sv
        for k in ("fishing_today", "gathering_today", "daily_streak"):
            sv = src_eco.get(k, 0)
            dv = dst_eco.get(k, 0)
            if sv:
                dst_eco[k] = max(dv, sv)
        atomic_json_write(dst / "economy.json", dst_eco)
    except Exception as e:
        logging.warning(f"[MERGE eco] {e}")
    try:
        src_p = atomic_json_read(src / "profile.json", default={})
        dst_p = atomic_json_read(dst / "profile.json", default={})
        aliases = dst_p.setdefault("aliases", [])
        if alias_uid not in aliases:
            aliases.append(alias_uid)
        for a in src_p.get("aliases", []) or []:
            if a not in aliases:
                aliases.append(a)
        if (src_p.get("level", 1) or 1) > (dst_p.get("level", 1) or 1):
            dst_p["level"] = src_p["level"]
            dst_p["xp"] = max(dst_p.get("xp", 0), src_p.get("xp", 0))
        if src_p.get("premium") and not dst_p.get("premium"):
            dst_p["premium"] = True
            dst_p["premium_expires"] = max(dst_p.get("premium_expires", 0),
                                            src_p.get("premium_expires", 0))
        for game in ("fishing", "gathering"):
            sg = src_p.get(game, {}) or {}
            dg = dst_p.setdefault(game, {})
            if (sg.get("level", 1) or 1) > (dg.get("level", 1) or 1):
                dg["level"] = sg["level"]
            dg["prestige"] = max(dg.get("prestige", 0), sg.get("prestige", 0))
            k = "total_catch" if game == "fishing" else "total_gather"
            dg[k] = dg.get(k, 0) + sg.get(k, 0)
            src_rc = sg.get("rarity_count", {}) or {}
            dst_rc = dg.setdefault("rarity_count",
                {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legend": 0, "mythic": 0})
            for t in dst_rc:
                dst_rc[t] = dst_rc.get(t, 0) + src_rc.get(t, 0)
            for lk in ("rod_level", "basket_level"):
                dg[lk] = max(dg.get(lk, 1), sg.get(lk, 1))
        atomic_json_write(dst / "profile.json", dst_p)
    except Exception as e:
        logging.warning(f"[MERGE prof] {e}")
    try:
        shutil.rmtree(src)
    except Exception as e:
        logging.warning(f"[MERGE rm] {e}")
    identity_registry.add_alias(canonical_uid, alias_uid)
    log_activity(canonical_uid, "merge", {"from": alias_uid, "merged": merged})
    return True, merged

class PermissionManager:
    """Small LuckPerms-inspired node/group/context engine for Cinnamon."""
    INHERIT = {"owner": ("owner", "mo", "user"), "mo": ("mo", "user"), "user": ("user",)}
    def __init__(self):
        self._path = os.path.join(config.SHARED_DIR, "permissions.json")
        self._lock = threading.RLock()
    def _load(self):
        return atomic_json_read(self._path, default={"roles": {}, "nodes": {}, "groups": {}})
    def _save(self, data):
        return atomic_json_write(self._path, data)
    def role(self, uid):
        try:
            from core.storage import is_registered_owner
            if is_registered_owner(uid) or _digits_match(uid, config.OWNER_NUMBER_DIGITS):
                return "owner"
        except Exception:
            pass
        d = self._load(); r = d.get("roles", {}).get(_strip_device(uid), "user")
        return r if r in self.INHERIT else "user"
    def set_role(self, uid, role):
        if role not in self.INHERIT or not uid: return False
        d = self._load(); d.setdefault("roles", {})[_strip_device(uid)] = role; return self._save(d)
    def grant(self, uid, node, context=None, expires=0):
        d = self._load(); u = d.setdefault("nodes", {}).setdefault(_strip_device(uid), {})
        key = f"{context or '*'}::{node}"; u[key] = {"expires": float(expires or 0)}; return self._save(d)
    def revoke(self, uid, node, context=None):
        d = self._load(); u = d.setdefault("nodes", {}).setdefault(_strip_device(uid), {})
        u.pop(f"{context or '*'}::{node}", None); return self._save(d)
    def grant_group_role(self, uid, group_jid, role="admin", expires=0):
        if role not in ("admin", "mo"): return False
        d = self._load(); g = d.setdefault("groups", {}).setdefault(safe_jid_str(group_jid), {})
        g[_strip_device(uid)] = {"role": role, "expires": float(expires or 0)}; return self._save(d)
    def revoke_group_role(self, uid, group_jid):
        d = self._load(); g = d.setdefault("groups", {}).setdefault(safe_jid_str(group_jid), {})
        g.pop(_strip_device(uid), None); return self._save(d)
    def group_role(self, uid, group_jid):
        d = self._load(); rec = d.get("groups", {}).get(safe_jid_str(group_jid), {}).get(_strip_device(uid))
        if not rec: return None
        if rec.get("expires") and now_ts() >= rec["expires"]: return None
        return rec.get("role")
    def has(self, uid, node, group_jid=None):
        role = self.role(uid)
        implied = self.INHERIT.get(role, ("user",))
        if node.startswith("owner.") and "owner" in implied: return True
        if node.startswith("mo.") and role in ("owner", "mo"): return True
        if node.startswith("user."): return True
        if group_jid and node.startswith("group."):
            gr = self.group_role(uid, group_jid)
            return gr in ("admin", "mo") or role in ("owner", "mo")
        d = self._load(); rec = d.get("nodes", {}).get(_strip_device(uid), {})
        for ctx in (safe_jid_str(group_jid) if group_jid else "*", "*"):
            x = rec.get(f"{ctx}::{node}")
            if x and (not x.get("expires") or now_ts() < x["expires"]): return True
        return False


class TitleManager:
    """Cosmetic-only titles; never consulted by PermissionManager."""
    def __init__(self):
        self._path = os.path.join(config.SHARED_DIR, "titles.json")
        self._lock = threading.RLock()
    def _load(self):
        return atomic_json_read(self._path, default={"users": {}})
    def list(self, uid):
        return list(self._load().get("users", {}).get(_strip_device(uid), {}).get("unlocked", []))
    def active(self, uid):
        return self._load().get("users", {}).get(_strip_device(uid), {}).get("active")
    def unlock(self, uid, title):
        d = self._load(); u = d.setdefault("users", {}).setdefault(_strip_device(uid), {"unlocked": [], "active": None})
        if title not in u["unlocked"]: u["unlocked"].append(title)
        if not u.get("active"): u["active"] = title
        return atomic_json_write(self._path, d)
    def equip(self, uid, title):
        d = self._load(); u = d.setdefault("users", {}).setdefault(_strip_device(uid), {"unlocked": [], "active": None})
        if title not in u.get("unlocked", []): return False
        u["active"] = title; return atomic_json_write(self._path, d)

permission_manager = PermissionManager()
title_manager = TitleManager()
