from handlers import register, register_feature_specs
from handlers.auth import owner_uid
from handlers.buyer import _owner_buyer_router
from handlers.event import airdrop
from handlers.fishing import check_game_quests
import config, json, os, random, re, subprocess, sys, time
from core.utils import _stable_key, box_bottom, box_title, hline, now_ts, short_name, shutdown_event, validate_input, validate_number
from core.storage import add_owner_registry, ban_manager, buyer_store, feature_toggle, is_registered_owner, load_owner_registry, owner_store, remove_owner_registry, save_owner_number, user_store
from core.identity import _SESSION_LID_CACHE, _find_session_db, _read_session_lid_map, _session_lid_map, identity_registry, merge_fragmented_folders, session_identity
from core.economy import add_cash, add_tokens, xp_for_level
from core.send import _ensure_jid_obj, safe_reply
def handle_owner_help(client, message, cj):
    safe_reply(client,
        f"{box_title('OWNER PANEL', 22)}\n"
        f"{config.SYM_BULLET} `/myuid` `/setowner <n>`\n"
        f"{config.SYM_BULLET} `/addowner` `/delowner` `/listowner`\n"
        f"{config.SYM_BULLET} `/ban` `/unban` `/banip` `/banlist`\n"
        f"{config.SYM_BULLET} `/addtoken` `/settoken`\n"
        f"{config.SYM_BULLET} `/addprem` `/delprem` `/setlevel`\n"
        f"{config.SYM_BULLET} `/owner addcash|setcash`\n"
        f"{config.SYM_BULLET} `/owner addxp|setxp|resetgame`\n"
        f"{config.SYM_BULLET} `/owner airdrop now|here|set`\n"
        f"{config.SYM_BULLET} `/owner identity` (list registry)\n"
        f"{config.SYM_BULLET} `/owner scan` (scan session db)\n"
        f"{config.SYM_BULLET} `/owner merge <canonical> <alias>`\n"
        f"        `/owner buyer info|extend|groups|revoke`\n"
        f"{config.SYM_BULLET} `/self` `/public` `/restart`\n"
        f"{config.SYM_BULLET} `/broadcast` `/health` `/ownerpanel`\n"
        f"{config.SYM_BULLET} `/toggle <role> <feat>`\n"
        f"{config.SYM_BULLET} `/eval` `/shell`\n"
        f"{box_bottom(22)}", message, cj)
@register('/myuid')
def handle_myuid(client, message, cj, chat, sender, args, ctx):
    ids = {}
    try:
        src = message.Info.MessageSource
        for attr in ("Sender", "SenderAlt", "Recipient", "RecipientAlt", "Participant", "ParticipantAlt", "Chat"):
            val = getattr(src, attr, None)
            if val is not None:
                ids[attr] = str(val)
    except Exception as e:
        ids["error"] = str(e)
    try:
        if client.me:
            ids["BotJID"] = str(client.me.JID)
            ids["BotLID"] = str(getattr(client.me, "LID", "") or "(none)")
    except Exception:
        pass
    sdb = _find_session_db()
    lid_count = len(_session_lid_map())
    lines = [f"{box_title('MY UID DEBUG', 22)}"]
    for k, v in ids.items():
        s = re.sub(r":\d+@", "@", str(v))
        d = re.sub(r"\D", "", s)
        lines.append(f"{config.SYM_BULLET} {k}: `{v}`")
        lines.append(f"  {config.SYM_DOT} digits: `{d}`")
    lines.append(hline(22))
    lines.append(f"{config.SYM_BULLET} Owner: `{config.OWNER_NUMBER_DIGITS}`")
    lines.append(f"{config.SYM_BULLET} Session DB: `{short_name(str(sdb), 30) if sdb else 'NOT FOUND'}`")
    lines.append(f"{config.SYM_BULLET} LID map entries: *{lid_count}*")
    lines.append(f"{config.SYM_BULLET} Raw: `{ctx.get('raw_sender', '?')}`")
    lines.append(f"{config.SYM_BULLET} Stable: `{short_name(_stable_key(ctx.get('raw_sender', '')), 22)}`")
    lines.append(f"{config.SYM_BULLET} Canonical: `{sender}`")
    lines.append(f"{config.SYM_BULLET} Method: `{ctx.get('uid_method', '?')}`")
    reg = load_owner_registry()
    lines.append(f"{config.SYM_BULLET} Registry owners: *{len(reg)}*")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/setowner', scope='owner')
def handle_setowner(client, message, cj, chat, sender, args, ctx):
    if not (ctx["is_owner"] or is_registered_owner(sender)):
        safe_reply(client, f"{config.SYM_CROSS} Owner only.", message, cj)
        return
    nomor = re.sub(r"\D", "", args or "")
    if not nomor or len(nomor) < 10:
        safe_reply(client, "`/setowner <nomor>`", message, cj)
        return
    config.OWNER_NUMBER_DIGITS = nomor
    save_owner_number(nomor)
    oid = f"{nomor}@s.whatsapp.net"
    add_owner_registry(oid)
    if not user_store.user_exists(oid):
        user_store.create_user(oid, config.OWNER_USERNAME, "", "")
    def mut(p): p.update({"premium": True, "title": "👑 Owner", "logged_in": True, "name": config.OWNER_USERNAME})
    user_store.update_profile(oid, mut)
    identity_registry.register_user(oid, name=config.OWNER_USERNAME)
    safe_reply(client, f"{config.SYM_CHECK} Owner {config.SYM_ARROW} `{nomor}`", message, cj)
@register('/addowner', scope='owner')
def handle_addowner(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    nomor = re.sub(r"\D", "", args or "")
    if not nomor or len(nomor) < 10:
        safe_reply(client, "`/addowner <nomor>`", message, cj)
        return
    oid = f"{nomor}@s.whatsapp.net"
    add_owner_registry(oid)
    if not user_store.user_exists(oid):
        user_store.create_user(oid, f"owner_{nomor[-4:]}", "", "")
        def mut(p):
            p["premium"] = True
            p["logged_in"] = True
        user_store.update_profile(oid, mut)
    safe_reply(client, f"{config.SYM_CHECK} +Owner `{nomor}`", message, cj)
@register('/delowner', scope='owner')
def handle_delowner(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    nomor = re.sub(r"\D", "", args or "")
    if not nomor:
        safe_reply(client, "`/delowner <nomor>`", message, cj)
        return
    remove_owner_registry(nomor)
    safe_reply(client, f"{config.SYM_CHECK} -Owner `{nomor}`", message, cj)
@register('/listowner', scope='owner')
def handle_listowner(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    reg = load_owner_registry()
    lines = [f"{box_title('OWNERS', 22)}", f"total: *{len(reg)}*"]
    for o in reg:
        lines.append(f"{config.SYM_BULLET} `{o}`")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/owner', scope='owner')
def handle_owner_router(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").strip().split()
    if not parts:
        handle_owner_help(client, message, cj)
        return
    sub = parts[0].lower()
    rest = " ".join(parts[1:])
    if sub == "addcash": return _op_addcash(client, message, cj, chat, sender, rest, ctx)
    if sub == "setcash": return _op_setcash(client, message, cj, chat, sender, rest, ctx)
    if sub == "addxp": return _op_addxp(client, message, cj, chat, sender, rest, ctx)
    if sub == "setxp": return _op_setxp(client, message, cj, chat, sender, rest, ctx)
    if sub == "resetgame": return _op_resetgame(client, message, cj, chat, sender, rest, ctx)
    if sub == "airdrop": return _op_airdrop(client, message, cj, chat, sender, rest, ctx)
    if sub == "identity": return _op_identity(client, message, cj, chat, sender, rest, ctx)
    if sub == "scan": return _op_scan(client, message, cj, chat, sender, rest, ctx)
    if sub == "merge": return _op_merge(client, message, cj, chat, sender, rest, ctx)
    if sub == "buyer": return _owner_buyer_router(client, message, cj, chat, sender, rest, ctx)
    safe_reply(client, f"{config.SYM_CROSS} Subcommand invalid.", message, cj)
def _find_uid_by_name(name): return user_store.find_by_name(name)
def _resolve_uid(target):
    return owner_uid() if target.lower() == "self" else (_find_uid_by_name(target) or target)
def _op_addcash(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/owner addcash <u> <n>`", message, cj)
        return
    amt = validate_number(parts[1], 1, 10**9)
    if not amt:
        safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    add_cash(uid, amt, source="owner")
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} +{amt}", message, cj)
def _op_setcash(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/owner setcash <u> <n>`", message, cj)
        return
    amt = validate_number(parts[1], 0, 10**9)
    if amt is None:
        safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(e):
        e["cash"] = amt
    user_store.update_economy(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} = {amt}", message, cj)
def _op_addxp(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 3:
        safe_reply(client, "`/owner addxp <u> <game> <n>`", message, cj)
        return
    game = parts[1].lower()
    if game not in ("fishing", "gathering"):
        safe_reply(client, f"{config.SYM_CROSS} fishing|gathering", message, cj)
        return
    amt = validate_number(parts[2], 1, 10**6)
    if not amt:
        safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(p):
        g = p.setdefault(game, {})
        k = "total_catch" if game == "fishing" else "total_gather"
        g[k] = g.get(k, 0) + amt
    user_store.update_profile(uid, mut)
    check_game_quests(uid, game)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} {game} +{amt}", message, cj)
def _op_setxp(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 3:
        safe_reply(client, "`/owner setxp <u> <game> <n>`", message, cj)
        return
    game = parts[1].lower()
    if game not in ("fishing", "gathering"):
        return
    amt = validate_number(parts[2], 0, 10**6)
    if amt is None:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(p):
        g = p.setdefault(game, {})
        k = "total_catch" if game == "fishing" else "total_gather"
        g[k] = amt
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} {game} = {amt}", message, cj)
def _op_resetgame(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/owner resetgame <u> <game>`", message, cj)
        return
    game = parts[1].lower()
    if game not in ("fishing", "gathering"):
        return
    uid = _resolve_uid(parts[0])
    def mut(p):
        pr = p.get(game, {}).get("prestige", 0)
        new_g = {"level": 1, "prestige": pr,
                 "rarity_count": {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legend": 0, "mythic": 0},
                 "quests_done": []}
        if game == "fishing":
            new_g["total_catch"] = 0
            new_g["rod_level"] = 1
            new_g["basket_level"] = 1
        else:
            new_g["total_gather"] = 0
            new_g["basket_level"] = 1
            new_g["rod_level"] = 1
        p[game] = new_g
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} Reset {game} {parts[0]}", message, cj)
def _op_airdrop(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if not parts:
        cfg = airdrop.get_config()
        safe_reply(client,
            f"{box_title('AIRDROP', 22)}\n"
            f"{config.SYM_BULLET} Enabled: {cfg.get('enabled')}\n"
            f"{config.SYM_BULLET} Hours: {cfg.get('hours')}\n"
            f"\n{config.SYM_ARROW} `/owner airdrop now`\n"
            f"{config.SYM_ARROW} `/owner airdrop here`\n"
            f"{config.SYM_ARROW} `/owner airdrop set 8,14,20`", message, cj)
        return
    sub = parts[0].lower()
    if sub == "now":
        buyers = buyer_store.list_active()
        groups = []
        for uid, info in buyers:
            for g in info.get("bound_groups", []):
                if g not in groups:
                    groups.append(g)
        if not groups:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada grup ter-bind.", message, cj)
            return
        sent = airdrop.trigger_now(groups, client)
        safe_reply(client, f"{config.SYM_CHECK} {sent} grup.", message, cj)
        return
    if sub == "here":
        if not ctx["is_group"]:
            safe_reply(client, f"{config.SYM_CROSS} Grup only.", message, cj)
            return
        sent = airdrop.trigger_now([chat], client)
        safe_reply(client, f"{config.SYM_CHECK} {sent} grup.", message, cj)
        return
    if sub == "set" and len(parts) >= 2:
        try:
            hours = [int(h.strip()) for h in parts[1].split(",") if h.strip().isdigit()]
        except Exception:
            safe_reply(client, f"{config.SYM_CROSS} Format: 8,14,20", message, cj)
            return
        hours = [h for h in hours if 0 <= h <= 23]
        airdrop.set_hours(hours)
        safe_reply(client, f"{config.SYM_CHECK} Hours: {hours}", message, cj)
        return
    safe_reply(client, "`/owner airdrop`", message, cj)
def _op_identity(client, message, cj, chat, sender, args, ctx):
    users = identity_registry.all_users()
    total = len(users)
    lines = [f"{box_title('IDENTITY REGISTRY', 22)}",
             f"{config.SYM_BULLET} Total: *{total}*",f"{config.SYM_BULLET} LID map: *{len(_session_lid_map())}*",
             hline(22)]
    for uid, u in list(users.items())[:20]:
        nm = u.get("name") or "?"
        aliases = u.get("aliases", [])
        lines.append(f"{config.SYM_BULLET} *{nm}* `{short_name(uid, 20)}`")
        if aliases:
            lines.append(f"  {config.SYM_DOT} {len(aliases)} alias")
    if total > 20:
        lines.append(f"{config.SYM_DOT} … dan {total - 20} lainnya")
    safe_reply(client, "\n".join(lines), message, cj)
def _op_scan(client, message, cj, chat, sender, args, ctx):
    sdb = _find_session_db()
    if not sdb:
        safe_reply(client, f"{config.SYM_CROSS} Session DB tidak ditemukan.\nCari di: `{config.DB_FILE}`, `./session.db`, `~/.wacli/session.db`", message, cj)
        return
    try:
        lid_map = _read_session_lid_map()
        cached = 0
        for lid, pn in lid_map.items():
            if not identity_registry.resolve_lid_to_pn(lid):
                identity_registry.link_lid_pn(lid, pn)
                cached += 1
        _SESSION_LID_CACHE["data"] = lid_map
        _SESSION_LID_CACHE["ts"] = time.time()
        lines = [f"{box_title('SESSION SCAN', 22)}",
                 f"{config.SYM_BULLET} DB: `{short_name(sdb, 30)}`",
                 f"{config.SYM_BULLET} LID map: *{len(lid_map)}* entries",
                 f"{config.SYM_BULLET} New cached: *{cached}*",
                 hline(22)]
        for lid, pn in list(lid_map.items())[:8]:
            lines.append(f"{config.SYM_DOT} `{short_name(lid, 16)}` {config.SYM_ARROW} `{short_name(pn, 16)}`")
        safe_reply(client, "\n".join(lines), message, cj)
    except Exception as e:
        safe_reply(client, f"{config.SYM_CROSS} Error: {str(e)[:100]}", message, cj)
def _op_merge(client, message, cj, chat, sender, args, ctx):
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/owner merge <canonical_uid|name> <alias_uid>`", message, cj)
        return
    canonical = _resolve_uid(parts[0])
    alias = parts[1]
    ok, info = merge_fragmented_folders(canonical, alias)
    if ok:
        safe_reply(client, f"{config.SYM_CHECK} Merged `{alias}` {config.SYM_ARROW} `{canonical}`\n{info}", message, cj)
    else:
        safe_reply(client, f"{config.SYM_CROSS} Gagal: {info}", message, cj)
@register('/ban', scope='owner')
def handle_ban(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").strip().split(None, 1)
    if not parts:
        safe_reply(client, "`/ban <user> [alasan]`", message, cj)
        return
    target = parts[0][:50]
    reason = validate_input(parts[1] if len(parts) > 1 else "", 200)
    uid = _find_uid_by_name(target) or target
    ok, msg = ban_manager.ban_user(uid, reason)
    safe_reply(client, msg, message, cj)
@register('/unban', scope='owner')
def handle_unban(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    target = validate_input(args or "", 50)
    if not target:
        return
    uid = _find_uid_by_name(target) or target
    ok, msg = ban_manager.unban_user(uid)
    safe_reply(client, msg, message, cj)
@register('/banip', scope='owner')
def handle_banip(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").strip().split(None, 1)
    if not parts:
        return
    ok, msg = ban_manager.ban_ip(parts[0][:45], validate_input(parts[1] if len(parts) > 1 else "", 200))
    safe_reply(client, msg, message, cj)
@register('/unbanip', scope='owner')
def handle_unbanip(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    ip = validate_input(args or "", 45)
    if not ip:
        return
    ok, msg = ban_manager.unban_ip(ip)
    safe_reply(client, msg, message, cj)
@register('/banlist', scope='owner')
def handle_banlist(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    users, ips = ban_manager.list_bans()
    lines = [f"{box_title('BAN LIST', 22)}", f"Users ({len(users)})"]
    for uid, b in users[:15]:
        lines.append(f"{config.SYM_BULLET} `{short_name(uid, 18)}` {config.SYM_DOT} {b.get('reason', '-')}")
    lines.append(f"IPs ({len(ips)})")
    for ip, b in ips[:15]:
        lines.append(f"{config.SYM_BULLET} `{ip}` {config.SYM_DOT} {b.get('reason', '-')}")
    safe_reply(client, "\n".join(lines), message, cj)
@register('/toggle', scope='owner')
def handle_toggle(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").strip().split()
    if not parts:
        safe_reply(client, "`/toggle <role> <feature>`", message, cj)
        return
    role = parts[0].lower()
    if role not in ("owner", "admin", "buyer", "user"):
        safe_reply(client, f"{config.SYM_CROSS} Role.", message, cj)
        return
    if len(parts) == 1:
        st = feature_toggle.get_role_status(role)
        lines = [f"{box_title('TOGGLE ' + role, 22)}"]
        for f, e in st.items():
            lines.append(f"{config.SYM_CHECK if e else config.SYM_CROSS} `{f}`")
        safe_reply(client, "\n".join(lines), message, cj)
        return
    feature = parts[1].lower()
    if len(parts) == 2:
        ok, msg, _ = feature_toggle.toggle(role, feature)
        safe_reply(client, msg if ok else f"{config.SYM_CROSS} {msg}", message, cj)
        return
    state = parts[2].lower()
    if state not in ("on", "off"):
        safe_reply(client, f"{config.SYM_CROSS} on|off", message, cj)
        return
    ok, msg = feature_toggle.set_role(role, feature, state == "on")
    safe_reply(client, msg if ok else f"{config.SYM_CROSS} {msg}", message, cj)
@register('/addtoken', scope='owner')
def handle_addtoken(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/addtoken <u|self> <n>`", message, cj)
        return
    amt = validate_number(parts[1], 1, 10**9)
    if not amt:
        safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    add_tokens(uid, amt, source="owner")
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} +{amt}", message, cj)
@register('/settoken', scope='owner')
def handle_settoken(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/settoken <u|self> <n>`", message, cj)
        return
    amt = validate_number(parts[1], 0, config.TOKEN_CAP)
    if amt is None:
        safe_reply(client, f"{config.SYM_CROSS} 0-{config.TOKEN_CAP}.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(e):
        e["tokens"] = amt
    user_store.update_economy(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} = {amt}", message, cj)
@register('/addprem', scope='owner')
def handle_addprem(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, "`/addprem <u|self> [days]`", message, cj)
        return
    days = validate_number(parts[1], 1, 3650) if len(parts) > 1 else config.PREMIUM_DURATION_DAYS
    if not days:
        days = config.PREMIUM_DURATION_DAYS
    uid = _resolve_uid(parts[0])
    def mut(p):
        p["premium"] = True
        p["premium_expires"] = now_ts() + days * 86400
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_STAR} {parts[0]} premium {days}h", message, cj)
@register('/delprem', scope='owner')
def handle_delprem(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, "`/delprem <u>`", message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(p):
        p["premium"] = False
        p["premium_expires"] = 0
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} premium off", message, cj)
@register('/setlevel', scope='owner')
def handle_setlevel(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/setlevel <u|self> <n>`", message, cj)
        return
    lvl = validate_number(parts[1], 1, 1000)
    if not lvl:
        safe_reply(client, f"{config.SYM_CROSS} Level.", message, cj)
        return
    uid = _resolve_uid(parts[0])
    def mut(p):
        p["level"] = lvl
        p["xp"] = xp_for_level(lvl)
    user_store.update_profile(uid, mut)
    safe_reply(client, f"{config.SYM_CHECK} {parts[0]} Lv{lvl}", message, cj)
@register('/self', scope='owner')
def handle_self(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    config.BOT_MODE = "self"
    safe_reply(client, f"{config.SYM_SHIELD} SELF", message, cj)
@register('/public', scope='owner')
def handle_public(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    config.BOT_MODE = "public"
    safe_reply(client, f"{config.SYM_SHIELD} PUBLIC", message, cj)
@register('/restart', scope='owner')
def handle_restart(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    safe_reply(client, f"{config.SYM_RING} Restarting...", message, cj)
    time.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)
@register('/eval', scope='owner')
def handle_eval(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    code = (args or "").strip()[:2000]
    if not code:
        safe_reply(client, "`/eval <kode>`", message, cj)
        return
    try:
        from handlers.shop import shop
        r = eval(code, {"__builtins__": {"print": print, "len": len, "str": str, "int": int,
                                          "json": json, "random": random, "time": time},
                        "user_store": user_store, "identity_registry": identity_registry,
                        "session_identity": session_identity,
                        "session_lid_map": _session_lid_map,
                        "shop": shop, "ban_manager": ban_manager,
                        "now_ts": now_ts}, {})
        safe_reply(client, f"{config.SYM_CHECK} `{str(r)[:2000]}`", message, cj)
    except Exception as e:
        safe_reply(client, f"{config.SYM_CROSS} `{str(e)[:300]}`", message, cj)
@register('/shell', scope='owner')
def handle_shell(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    cmd = (args or "").strip()[:500]
    if not cmd:
        safe_reply(client, "`/shell <cmd>`", message, cj)
        return
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = ((r.stdout or "") + (r.stderr or ""))[:2000] or "(none)"
        safe_reply(client, f"{config.SYM_CHECK} `{out}`", message, cj)
    except Exception as e:
        safe_reply(client, f"{config.SYM_CROSS} {str(e)[:300]}", message, cj)
@register('/broadcast', scope='owner')
def handle_broadcast(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    txt = validate_input(args or "", 1000)
    if not txt:
        safe_reply(client, "`/broadcast <teks>`", message, cj)
        return
    try:
        groups = client.get_joined_groups()
        if not groups:
            safe_reply(client, f"{config.SYM_CROSS} Tidak ada grup.", message, cj)
            return
    except Exception as e:
        safe_reply(client, f"{config.SYM_CROSS} {str(e)[:100]}", message, cj)
        return
    ok = 0
    for g in groups:
        if shutdown_event.is_set():
            break
        jid = getattr(g, "JID", None) or getattr(g, "jid", None)
        if not jid:
            continue
        try:
            client.send_message(_ensure_jid_obj(jid), text=f"{config.SYM_STAR} {txt}")
            ok += 1
            time.sleep(0.5)
        except Exception:
            pass
    safe_reply(client, f"{config.SYM_CHECK} {ok} grup.", message, cj)
@register('/ownerpanel', scope='owner')
def handle_owner_panel(client, message, cj, chat, sender, args, ctx):
    if not ctx["is_owner"]:
        return
    owner_store.ensure(sender, config.OWNER_USERNAME)
    buyers = buyer_store.list_active()
    lines = [f"{box_title('OWNER PANEL', 22)}",
             f"{config.SYM_BULLET} Owner UID: `{sender}`",
             f"{config.SYM_BULLET} Buyers aktif: *{len(buyers)}*",
             f"{config.SYM_BULLET} Folder owner: `data/owner-dat/<uid>/`",
             f"{config.SYM_BULLET} Folder buyer: `data/buyer-dat/<uid>/`",
             hline(22),
             f"{config.SYM_ARROW} `/owner buyer info <u>`",
             f"{config.SYM_ARROW} `/owner buyer extend <u> <hari>`",
             f"{config.SYM_ARROW} `/owner buyer groups <u>`",
             f"{config.SYM_ARROW} `/addbuyer <u> [trial|weekly|plus] [days]`",
             f"{config.SYM_ARROW} `/listbuyer`",
             f"{config.SYM_ARROW} `/invcheck <bisa untuk semua user>`"]
    safe_reply(client, "\n".join(lines), message, cj)
