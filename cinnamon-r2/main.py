import logging, os, random, signal, sys, threading, time, traceback
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv
import config, handlers
from core.economy import miner_manager, level_from_xp
from core.identity import identity_registry, session_identity, register_jid_pair, _read_session_lid_map, _SESSION_LID_CACHE, permission_manager, title_manager; from core.storage import buyer_store, group_id_manager, user_store, ban_manager, feature_toggle, add_owner_registry, load_owner_number, event_manager
from core.send import safe_reply, get_message_text; from core.utils import FFMPEG_AVAILABLE, PILLOW_AVAILABLE, YTDLP_AVAILABLE, shutdown_event, is_duplicate_message, health, rate_limiter, cmd_queue, now_ts, is_group_message, parse_command, safe_jid_str, _stable_key, ensure_media_dirs
logging.basicConfig(level=logging.DEBUG if config.DEBUG_MODE else logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"); [logging.getLogger(name).setLevel(logging.WARNING) for name in ("apscheduler", "apscheduler.executors.default", "apscheduler.scheduler")]
logging.getLogger("apscheduler.executors.default").propagate = False
for d in (config.DATA_DIR, config.USER_DIR, config.OWNER_DIR, config.BUYER_DIR, config.PENDING_DIR, config.SHARED_DIR): Path(d).mkdir(parents=True, exist_ok=True)
ensure_media_dirs()
scheduler = BackgroundScheduler(timezone=config.WIB, daemon=True); scheduler.start()
_thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cin-worker")
client = NewClient(config.DB_FILE); handlers.load_all()
def _signal_handler(signum, frame): logging.info(f"[SIGNAL] {signum} received"); shutdown_event.set()
def install_signal_handlers():
    try: signal.signal(signal.SIGINT, _signal_handler); signal.signal(signal.SIGTERM, _signal_handler)
    except Exception as e: logging.warning(f"[SIGNAL] {e}")
def _do_cleanup():
    with suppress(Exception): miner_manager.stop_all()
    with suppress(Exception): scheduler.shutdown(wait=False) if scheduler.running else None
    try: _thread_pool.shutdown(wait=False, cancel_futures=True)
    except TypeError: _thread_pool.shutdown(wait=False)
    except Exception: pass
@client.event(ConnectedEv)
def on_connected(c, _):
    logging.info(f"[v52] Connected: {c.me.JID}"); load_owner_number()
    try:
        smap=_read_session_lid_map(); _SESSION_LID_CACHE["data"]=smap; _SESSION_LID_CACHE["ts"]=time.time()
        for lid,pn in smap.items():
            if "@lid" in str(lid) and pn: identity_registry.link_lid_pn(lid, pn if "@" in pn else f"{pn}@s.whatsapp.net")
        logging.info(f"[v52] Session LID map: {len(smap)} entries")
    except Exception as e: logging.warning(f"[SESSION_DB] {e}")
    try: handlers.ensure_owner_profile(c)
    except Exception as e: logging.warning(f"[OWNER] {e}")
    if not shutdown_event.is_set():
        try: handlers.setup_scheduler(c, scheduler)
        except Exception as e: logging.warning(f"[SCHED] {e}")
@client.event(MessageEv)
def on_message(c, message: MessageEv):
    if shutdown_event.is_set(): return
    try: register_jid_pair(message)
    except Exception: pass
    sr=message.Info.MessageSource.Sender;
    if sr == c.me.JID: return
    try: msg_id=str(message.Info.ID)
    except Exception: msg_id=""
    if is_duplicate_message(msg_id): return
    health.on_message(); in_group,cjo,chat0=is_group_message(message); text=get_message_text(message); cmd,args=parse_command(text); chat=safe_jid_str(cjo) if cjo else ""; raw_sender=safe_jid_str(sr)
    alt_val=None
    with suppress(Exception): alt_val=next((str(v) for attr in ("SenderAlt","ParticipantAlt") if (v:=getattr(message.Info.MessageSource,attr,None))),None)
    sender,uid_method=session_identity.resolve(raw_sender,c,alt=alt_val)
    if sender != raw_sender and user_store.user_exists(sender):
        with suppress(Exception): user_store.register_alias(sender, raw_sender)
    if in_group and chat:
        with suppress(Exception): group_id_manager.get_or_create(chat)
    owner=handlers.detect_owner(message,c,sender)
    if owner:
        oid=handlers.owner_uid(); add_owner_registry(sender); add_owner_registry(raw_sender); identity_registry.set_session_canonical(_stable_key(raw_sender),oid); sender=oid
        if not user_store.user_exists(sender): user_store.create_user(sender,config.OWNER_USERNAME,"","")
        def fix_owner(p):
            if (p.get("name") or "") != config.OWNER_USERNAME: p["name"]=config.OWNER_USERNAME
            p.update({"premium":True,"logged_in":True,"title":"👑 Owner"})
        user_store.update_profile(sender,fix_owner)
    if not owner:
        ban=ban_manager.is_user_banned(sender)
        if ban:
            with suppress(Exception): safe_reply(c,f"{config.SYM_CROSS} Di-ban: _{ban.get('reason','-')}_",message,cjo)
            return
    if config.BOT_MODE=="self" and not owner: return
    is_buyer=buyer_store.is_buyer(sender)
    if not owner and is_buyer:
        with suppress(Exception):
            binfo=buyer_store.get(sender) or {}; deny=binfo.get("self_mode") and in_group and chat not in binfo.get("bound_groups",[])
            if deny: return
    is_admin=handlers.is_group_admin(c,cjo,raw_sender) if in_group else False
    ctx={"is_group":in_group,"is_owner":owner,"is_admin":is_admin,"is_buyer":is_buyer,"raw_sender":raw_sender,"uid_method":uid_method}
    if in_group and not cmd and not owner and user_store.user_exists(sender):
        p=user_store.get_profile(sender)
        if p.get("logged_in") and now_ts()-p.get("last_xp",0)>=config.XP_COOLDOWN:
            gain=random.randint(config.XP_MIN,config.XP_MAX); user_store.update_profile(sender,lambda pp:(pp.__setitem__("last_xp",now_ts()),pp.__setitem__("xp",pp.get("xp",0)+gain),pp.__setitem__("level",level_from_xp(pp["xp"])))) ; event_manager.progress(sender,"xp",random.randint(config.XP_MIN,config.XP_MAX))
    if cmd and cmd in handlers.COMMANDS:
        handler,scope=handlers.COMMANDS[cmd]
        if cmd=="/jawab": handler(c,message,cjo,chat,sender,args,ctx); return
        if handler is None: return
        if not owner and not rate_limiter.allow(sender): safe_reply(c,f"{config.SYM_RING} Terlalu cepat.",message,cjo); return
        if scope=="group" and not in_group: safe_reply(c,f"{config.SYM_NOTE} Grup only.",message,cjo); return
        if scope=="owner" and not owner: safe_reply(c,f"{config.SYM_CROSS} Owner only.",message,cjo); return
        if cmd in ("/bindgroup","/mygroups","/myself") and not is_buyer: safe_reply(c,f"{config.SYM_CROSS} Buyer only.",message,cjo); return
        if scope=="group" and in_group and cmd in ("/kick","/add","/everyone","/tagall","/open","/close") and not (owner or is_admin or is_buyer): safe_reply(c,f"{config.SYM_CROSS} Admin only.",message,cjo); return
        cat=config.COMMAND_CATEGORY.get(cmd)
        if cat and not owner:
            role="admin" if is_admin else ("buyer" if is_buyer else "user")
            if not feature_toggle.is_enabled(role,cat): safe_reply(c,f"{config.SYM_CROSS} Fitur *{cat}* OFF untuk {role}.",message,cjo); return
        if not owner:
            okq,qpos=cmd_queue.acquire(sender)
            if not okq: safe_reply(c,f"{config.SYM_RING} Sibuk, antrian #{qpos}.",message,cjo); return
            try: handler(c,message,cjo,chat,sender,args,ctx)
            except Exception as e: health.on_error(); logging.error(f"[CMD {cmd}] {e}"); logging.debug(traceback.format_exc()); safe_reply(c,f"{config.SYM_CROSS} Error: {str(e)[:100]}",message,cjo)
            finally: cmd_queue.release()
        else:
            try: handler(c,message,cjo,chat,sender,args,ctx)
            except Exception as e: health.on_error(); logging.error(f"[CMD {cmd}] {e}"); logging.debug(traceback.format_exc()); safe_reply(c,f"{config.SYM_CROSS} Error: {str(e)[:100]}",message,cjo)
        return
def _connect_worker():
    try: client.connect()
    except Exception as e: (logging.error(f"[CONNECT] {e}"), shutdown_event.set()) if not shutdown_event.is_set() else None
if __name__ == "__main__":
    install_signal_handlers(); print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n┃  ✦ CINNAMON v53 (Nyx1024) ✦  ┃\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"); print(f"Owner   : {config.OWNER_USERNAME} ({config.OWNER_NUMBER_RAW})"); print(f"Debug   : {'ON' if config.DEBUG_MODE else 'OFF'}"); print(f"Pillow  : {'ON' if PILLOW_AVAILABLE else 'OFF'}"); print(f"FFmpeg  : {'ON' if FFMPEG_AVAILABLE else 'OFF'}"); print(f"yt-dlp  : {'ON' if YTDLP_AVAILABLE else 'OFF'}"); print("━"*40); print("★ v52 ACCOUNT FIX: stable-key pending store\n★ v52 ACCOUNT FIX: register→confirm→login consistent\n★ v52 ACCOUNT FIX: SessionIdentityManager (canonical UID)\n★ v52 ACCOUNT FIX: identity registry fed by register_jid_pair\n★ v52 ACCOUNT FIX: auto-heal LID→PN + folder merge\n★ v52 ACCOUNT FIX: inventory/activity always use canonical UID\n★ v52: /whoami /fixme /activity show resolution path\n★ v52: /owner identity /scan /merge"); print("━"*40)
    threading.Thread(target=_connect_worker,name="wa-connect",daemon=True).start()
    try:
        while not shutdown_event.is_set(): shutdown_event.wait(timeout=1.0)
    except KeyboardInterrupt: shutdown_event.set()
    _do_cleanup(); logging.info("[EXIT] Bye.")
    try: os._exit(0)
    except Exception: sys.exit(0)
