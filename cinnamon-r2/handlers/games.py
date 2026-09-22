from handlers import register, register_feature_specs
from handlers.auth import require_login, require_paid_cooldown
import config
from config import RPSBET_MAX, RPSBET_MIN, SLOT_BET_MAX, SLOT_BET_MIN, SLOT_COOLDOWN
import json
import logging
import random
import re
import time
from pathlib import Path
import ctypes
from core.utils import box_title, now_ts, validate_number
from core.storage import user_store
from core.economy import achievement_manager, add_tokens, deduct_tokens, get_luck
from core.send import safe_reply
from core.economy import get_luck, get_tokens, deduct_tokens, add_tokens, get_cash, add_cash, deduct_cash, achievement_manager
from core.storage import buyer_store
from core.storage import user_store, event_manager
@register('/slot')
def game_slot(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    parts = (args or "").split()
    if not parts:
        safe_reply(client, f"{config.SYM_BULLET} `/slot <bet>` ({SLOT_BET_MIN}-{SLOT_BET_MAX})", message, cj)
        return
    bet = validate_number(parts[0], SLOT_BET_MIN, SLOT_BET_MAX)
    if not bet:
        safe_reply(client, f"{config.SYM_CROSS} {SLOT_BET_MIN}-{SLOT_BET_MAX}.", message, cj)
        return
    e = user_store.get_economy(sender)
    cd = e.get("game_cooldowns", {}).get("slot", 0)
    if now_ts() - cd < SLOT_COOLDOWN and not ctx["is_owner"]:
        safe_reply(client, f"{config.SYM_RING} {int(SLOT_COOLDOWN - (now_ts() - cd))}s", message, cj)
        return
    if not ctx["is_owner"]:
        ok, rem = deduct_tokens(sender, bet, source="slot_bet")
        if not ok:
            safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
            return
    def mut(ee):
        ee.setdefault("game_cooldowns", {})["slot"] = now_ts()
    user_store.update_economy(sender, mut)
    luck = get_luck(sender)
    w = list(config.SLOT_WEIGHTS)
    if luck > 0:
        for i in (4, 5, 6):
            w[i] *= (1 + luck * 3)
    r1 = random.choices(config.SLOT_SYMBOLS, weights=w, k=1)[0]
    r2 = random.choices(config.SLOT_SYMBOLS, weights=w, k=1)[0]
    r3 = random.choices(config.SLOT_SYMBOLS, weights=w, k=1)[0]
    reel = f"┌─────────────┐\n│ {r1} {r2} {r3} │\n└─────────────┘"
    mult = 0
    if r1 == r2 == r3:
        mult = config.SLOT_TIER.get(r1, 0)
    elif r1 == r2 or r2 == r3 or r1 == r3:
        mult = 1.5
    win = int(bet * mult)
    net = win - bet
    if win > 0 and not ctx["is_owner"]:
        add_tokens(sender, win, source="slot_win")
    msg = f"{box_title('SLOT', 22)}\n`{reel}`\n{config.SYM_BULLET} Bet `{bet}` {config.SYM_DOT} Mult `{mult}`\n"
    msg += f"{config.SYM_CHECK if net > 0 else (config.SYM_CROSS if net < 0 else config.SYM_DOT)} {net:+d}"
    if r1 == r2 == r3 == "💎":
        achievement_manager.grant(sender, "slot_jackpot")
    safe_reply(client, msg, message, cj)
    achievement_manager.check_all(sender)
@register('/captcha')
def game_captcha(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    w = random.choice(WORDS)
    broken = "".join(c if random.random() < 0.5 else random.choice("!@#") for c in w)
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": w, "started": now_ts(), "timeout": 30, "game_id": "captcha"}
    safe_reply(client, f"{config.SYM_NOTE} `{broken}` {config.SYM_ARROW} `/jawab`", message, cj)
@register('/math')
def game_math(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    a, b = random.randint(2, 30), random.randint(2, 20)
    op = random.choice(["+", "-", "*"])
    ans = eval(f"{a} {op} {b}")
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": str(ans), "started": now_ts(), "timeout": 20, "game_id": "math"}
    safe_reply(client, f"{config.SYM_NOTE} `{a} {op} {b}` {config.SYM_DOT} 20s", message, cj)
@register('/scramble')
def game_scramble(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    w = random.choice(WORDS)
    ls = list(w)
    random.shuffle(ls)
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": w, "started": now_ts(), "timeout": 25, "game_id": "scramble"}
    safe_reply(client, f"{config.SYM_NOTE} `{''.join(ls)}`", message, cj)
@register('/trivia')
def game_trivia(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    q, ans = random.choice(TRIVIA)
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": ans[0], "answers": ans, "started": now_ts(), "timeout": 25, "game_id": "trivia"}
    safe_reply(client, f"{config.SYM_NOTE} {q}", message, cj)
@register('/rps')
def game_rps(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    c = (args or "").strip().lower()
    mp = {"b": "batu", "g": "gunting", "k": "kertas"}
    if c not in mp:
        safe_reply(client, "`/rps b|g|k`", message, cj)
        return
    pl = mp[c]
    bt = random.choice(["batu", "gunting", "kertas"])
    em = {"batu": "✊", "gunting": "✌️", "kertas": "✋"}
    be = {"batu": "gunting", "gunting": "kertas", "kertas": "batu"}
    if pl == bt:
        res, won = config.SYM_DOT + " SERI", None
    elif be[pl] == bt:
        res, won = config.SYM_CHECK + " MENANG", True
    else:
        res, won = config.SYM_CROSS + " KALAH", False
    tok = 16 if won else (1 if won is False else 4)
    add_tokens(sender, tok, source="rps")
    safe_reply(client, f"{em[pl]} vs {em[bt]} {config.SYM_DOT} {res} +{tok}", message, cj)
@register('/tebakangka')
def game_tebakangka(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    t = random.randint(1, 100)
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": str(t), "started": now_ts(), "timeout": 60, "hint_lo": 1, "hint_hi": 100, "tries": 0, "game_id": "tebakangka"}
    safe_reply(client, f"{config.SYM_NOTE} TEBAK 1-100 {config.SYM_ARROW} `/jawab`", message, cj)
@register('/rpsbet')
def game_rpsbet(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if not require_paid_cooldown(client, message, cj, sender, ctx):
        return
    parts = (args or "").split()
    if len(parts) < 2:
        safe_reply(client, "`/rpsbet <b|g|k> <n>`", message, cj)
        return
    mp = {"b": "batu", "g": "gunting", "k": "kertas"}
    if parts[0].lower() not in mp:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    bet = validate_number(parts[1], RPSBET_MIN, RPSBET_MAX)
    if not bet:
        safe_reply(client, config.SYM_CROSS, message, cj)
        return
    ok, rem = deduct_tokens(sender, bet, source="rpsbet")
    if not ok:
        safe_reply(client, f"{config.SYM_CROSS} Token kurang.", message, cj)
        return
    pl = mp[parts[0].lower()]
    bt = random.choice(["batu", "gunting", "kertas"])
    em = {"batu": "✊", "gunting": "✌️", "kertas": "✋"}
    be = {"batu": "gunting", "gunting": "kertas", "kertas": "batu"}
    if pl == bt:
        add_tokens(sender, bet, source="rpsbet_refund")
        safe_reply(client, f"{em[pl]} vs {em[bt]} {config.SYM_DOT} SERI", message, cj)
    elif be[pl] == bt:
        add_tokens(sender, bet * 2, source="rpsbet_win")
        safe_reply(client, f"{em[pl]} vs {em[bt]} {config.SYM_DOT} +{bet}", message, cj)
    else:
        safe_reply(client, f"{em[pl]} vs {em[bt]} {config.SYM_DOT} -{bet}", message, cj)
@register('/nguess')
def game_nguess(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    t = random.randint(1, 100)
    games_state["captchas"].setdefault(chat, {})[sender] = {"answer": str(t), "started": now_ts(), "timeout": 60, "hint_lo": 1, "hint_hi": 100, "tries": 0, "game_id": "nguess"}
    safe_reply(client, f"{config.SYM_NOTE} NUMBER GUESS 1-100 {config.SYM_ARROW} `/jawab`", message, cj)
@register('/wordchain')
def game_wordchain(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    s = random.choice(WORDS)
    games_state["wordchain"][chat] = {"current": s, "used": {s}, "started": now_ts(), "timeout": 30, "player": sender, "chain": 0}
    safe_reply(client, f"{config.SYM_NOTE} Kata: *{s}* {config.SYM_ARROW} `/jawab` diawali `{s[-1]}`", message, cj)
@register('/memory')
def game_memory(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    if chat in games_state["memory"]:
        safe_reply(client, f"{config.SYM_NOTE} Aktif.", message, cj)
        return
    pairs = ["🍎", "🍌", "🍇", "🍉", "🍓", "🍒", "🥝", "🍍"]
    cards = pairs * 2
    random.shuffle(cards)
    games_state["memory"][chat] = {"cards": cards, "matched": set(), "player": sender, "tries": 0}
    safe_reply(client, f"{config.SYM_NOTE} MEMORY {config.SYM_ARROW} `/jawab <1-16> <1-16>`", message, cj)
@register('/jawab')
def dispatch_jawab(client, message, cj, chat, sender, args, ctx):
    st = games_state["captchas"].get(chat, {}).get(sender)
    if st:
        if now_ts() - st["started"] > st["timeout"]:
            del games_state["captchas"][chat][sender]
            safe_reply(client, f"{config.SYM_RING} Habis! {st['answer']}", message, cj)
            return
        a = (args or "").strip()
        if st.get("game_id") in ("tebakangka", "nguess"):
            try:
                g = int(a)
            except ValueError:
                safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
                return
            t = int(st["answer"])
            if g == t:
                del games_state["captchas"][chat][sender]
                add_tokens(sender, 20, source="game")
                safe_reply(client, f"{config.SYM_CHECK} {t} +20", message, cj)
            elif g < t:
                st["hint_lo"] = max(st["hint_lo"], g)
                safe_reply(client, f"▲ {st['hint_lo']}-{st['hint_hi']}", message, cj)
            else:
                st["hint_hi"] = min(st["hint_hi"], g)
                safe_reply(client, f"▼ {st['hint_lo']}-{st['hint_hi']}", message, cj)
            return
        cl = st.get("answers", [st["answer"]])
        if any(x.lower() == a.lower() for x in cl):
            del games_state["captchas"][chat][sender]
            add_tokens(sender, 15, source="game")
            safe_reply(client, f"{config.SYM_CHECK} +15", message, cj)
        else:
            safe_reply(client, f"{config.SYM_CROSS} Salah.", message, cj)
        return
    wst = games_state["wordchain"].get(chat)
    if wst and wst.get("player") == sender:
        if now_ts() - wst["started"] > wst["timeout"]:
            games_state["wordchain"].pop(chat, None)
            safe_reply(client, f"{config.SYM_RING} Habis!", message, cj)
            return
        w = (args or "").strip().lower()
        if len(w) < 3:
            safe_reply(client, f"{config.SYM_CROSS} Min 3.", message, cj)
            return
        if w[0] != wst["current"][-1]:
            safe_reply(client, f"{config.SYM_CROSS} Harus `{wst['current'][-1]}`", message, cj)
            return
        if w in wst["used"]:
            safe_reply(client, f"{config.SYM_CROSS} Dipakai.", message, cj)
            return
        wst["used"].add(w)
        wst["current"] = w
        wst["chain"] += 1
        wst["started"] = now_ts()
        if wst["chain"] >= 5:
            add_tokens(sender, 25, source="game")
            games_state["wordchain"].pop(chat, None)
            safe_reply(client, f"{config.SYM_STAR} +25", message, cj)
        else:
            safe_reply(client, f"{config.SYM_CHECK} {wst['chain']}/5 {config.SYM_DOT} `{w}` {config.SYM_ARROW} `{w[-1]}...`", message, cj)
        return
    mst = games_state["memory"].get(chat)
    if mst and mst.get("player") == sender:
        ns = (args or "").split()
        if len(ns) != 2:
            safe_reply(client, "`/jawab <1-16> <1-16>`", message, cj)
            return
        try:
            a, b = int(ns[0]) - 1, int(ns[1]) - 1
        except ValueError:
            safe_reply(client, f"{config.SYM_CROSS} Angka.", message, cj)
            return
        if a == b or a < 0 or b < 0 or a > 15 or b > 15:
            safe_reply(client, f"{config.SYM_CROSS} Invalid.", message, cj)
            return
        if a in mst["matched"] or b in mst["matched"]:
            safe_reply(client, f"{config.SYM_CROSS} Sudah match.", message, cj)
            return
        mst["tries"] += 1
        ca, cb = mst["cards"][a], mst["cards"][b]
        if ca == cb:
            mst["matched"].add(a)
            mst["matched"].add(b)
            if len(mst["matched"]) >= 16:
                rw = max(10, 40 - mst["tries"] * 2)
                add_tokens(sender, rw, source="game")
                games_state["memory"].pop(chat, None)
                safe_reply(client, f"{config.SYM_STAR} +{rw}", message, cj)
            else:
                safe_reply(client, f"{config.SYM_CHECK} MATCH {ca} {config.SYM_DOT} {len(mst['matched']) // 2}/8", message, cj)
        else:
            safe_reply(client, f"{config.SYM_CROSS} {ca} vs {cb}", message, cj)
        return
    safe_reply(client, f"{config.SYM_CROSS} Tidak ada soal.", message, cj)
@register('/exit')
def handle_exit(client, message, cj, chat, sender, args, ctx):
    games_state["captchas"].get(chat, {}).pop(sender, None)
    games_state["memory"].pop(chat, None)
    games_state["wordchain"].pop(chat, None)
    safe_reply(client, f"{config.SYM_CHECK} Keluar.", message, cj)
WORDS = ["kucing", "anjing", "rumah", "sekolah", "mobil", "motor", "bunga", "pohon", "buku", "pensil"]
TRIVIA = [("Ibu kota Indonesia?", ["jakarta"]), ("Planet terdekat matahari?", ["merkurius"]), ("2+2x2?", ["6", "enam"]), ("Hewan terbesar?", ["paus"])]
EIGHT_BALL = ["Ya.", "Tidak.", "Mungkin.", "Tanya lagi.", "Pasti.", "Tidak bisa dipastikan."]
games_state = {"captchas": {}, "memory": {}, "wordchain": {}}

from core.storage import atomic_json_read, atomic_json_write, user_store
from core.economy import add_cash, add_tokens, deduct_cash, get_cash, xp_for_level
from core.identity import title_manager, permission_manager
import hashlib
import itertools

_R2_GAME_PATH=Path(config.SHARED_DIR)/"r2_games.json"
_R2_RPG_PATH=lambda uid: Path(config.USER_DIR)/uid/"rpg.json"
_NATIVE_RPG=None
def _native_damage(atk,defense,crit,luck):
    global _NATIVE_RPG
    if _NATIVE_RPG is None:
        for lib in (Path(__file__).resolve().parents[1]/"librpg_engine.so",Path(__file__).resolve().parents[1]/"librpg_engine.dylib"):
            try:
                x=ctypes.CDLL(str(lib)); x.CinnamonDamage.argtypes=[ctypes.c_double]*4+[ctypes.c_uint64]; x.CinnamonDamage.restype=ctypes.c_int; _NATIVE_RPG=x; break
            except OSError: pass
    if _NATIVE_RPG is None: return None
    try: return int(_NATIVE_RPG.CinnamonDamage(atk,defense,crit,luck,int(time.time_ns())))
    except Exception: return None
_R2_RPG_DEFAULT={"level":1,"xp":0,"hp":100,"max_hp":100,"mana":30,"max_mana":30,"atk":12,"def":6,"crit":0.05,"luck":0.02,"skillpoints":0,"skills":{},"equipment":{"weapon":"Rusty Sword","armor":"Cloth","accessory":"None"},"gold":0,"pet":None,"guild":None,"party":[],"gacha_pity":0,"dungeon_floor":0,"wins":0,"losses":0,"raid_damage":0}

def _game_state(): return atomic_json_read(_R2_GAME_PATH,default={"games":{},"boards":{},"events":{}})
def _save_game_state(d): _R2_GAME_PATH.parent.mkdir(parents=True,exist_ok=True); atomic_json_write(_R2_GAME_PATH,d)
def _rpg(uid):
    path=_R2_RPG_PATH(uid); d=atomic_json_read(path,default=_R2_RPG_DEFAULT); d={**_R2_RPG_DEFAULT,**d};
    for k,v in _R2_RPG_DEFAULT.items():
        if isinstance(v,dict): d[k]={**v,**d.get(k,{})}
    path.parent.mkdir(parents=True,exist_ok=True); return d

def _save_rpg(uid,d):
    path=_R2_RPG_PATH(uid); path.parent.mkdir(parents=True,exist_ok=True); atomic_json_write(path,d)

def _level_gain(uid,xp):
    r=_rpg(uid); old=r['level']; r['xp']+=xp
    while r['xp']>=100*r['level'] and r['level']<100:
        r['xp']-=100*r['level']; r['level']+=1; r['max_hp']+=10; r['hp']=r['max_hp']; r['atk']+=2; r['def']+=1; r['skillpoints']+=1
    _save_rpg(uid,r); return old,r['level']

def _game_key(chat,uid): return f"{chat or uid}:{uid}"
def _game_state_get(chat,uid):
    return _game_state().setdefault("games",{}).setdefault(_game_key(chat,uid),{})
def _game_win(uid):
    r=_rpg(uid); r["wins"]+=1; r["r2_streak"]=r.get("r2_streak",0)+1; _save_rpg(uid,r); return r
def _game_loss(uid):
    r=_rpg(uid); r["losses"]+=1; r["r2_streak"]=0; _save_rpg(uid,r); return r
def _line(cells,n,m):
    return any(all(cells.get(f"{r},{c}")==m for c in range(n)) for r in range(n)) or any(all(cells.get(f"{r},{c}")==m for r in range(n)) for c in range(n)) or all(cells.get(f"{i},{i}")==m for i in range(n)) or all(cells.get(f"{i},{n-1-i}")==m for i in range(n))
def _board(client,message,cj,chat,uid,args,n,kind):
    st=_game_state(); key=f"{chat or uid}:{uid}:{kind}"; b=st.setdefault("boards",{}).setdefault(key,{"size":n,"turn":uid,"cells":{}}); parts=args.split()
    if b["turn"] not in (uid,"done"): safe_reply(client,"⏳ Bukan giliranmu.",message,cj); return
    if not parts: safe_reply(client,f"🎮 `/{kind} <row> <col>`",message,cj); return
    try: r,c=map(int,parts[:2]); r-=1;c-=1
    except Exception: safe_reply(client,"Format baris kolom.",message,cj); return
    pos=f"{r},{c}"
    if not (0<=r<n and 0<=c<n) or pos in b["cells"] or b["turn"]=="done": safe_reply(client,"Posisi tidak valid.",message,cj); return
    b["cells"][pos]="X"
    if _line(b["cells"],n,"X"): _game_win(uid);b["turn"]="done";_save_game_state(st);safe_reply(client,"🏆 Menang!",message,cj);return
    empty=[(rr,cc) for rr in range(n) for cc in range(n) if f"{rr},{cc}" not in b["cells"]]
    if not empty: b["turn"]="done";_save_game_state(st);safe_reply(client,"🤝 Draw.",message,cj);return
    rr,cc=random.choice(empty);b["cells"][f"{rr},{cc}"]="O"
    if _line(b["cells"],n,"O"): _game_loss(uid);b["turn"]="done";_save_game_state(st);safe_reply(client,"🤖 CPU menang.",message,cj);return
    _save_game_state(st);safe_reply(client,"🎮\n"+"\n".join(" ".join(b["cells"].get(f"{rr},{cc}","·") for cc in range(n)) for rr in range(n)),message,cj)
def _r2_game_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"]; a=(args or "").strip(); p=a.split(); st=_game_state(); key=_game_key(chat,sender); gs=st.setdefault("games",{}).get(key,{})
    if op=="slot": return handle_slot(client,message,cj,chat,sender,a,ctx)
    if op=="rps": return handle_rps(client,message,cj,chat,sender,a or "b",ctx)
    if op=="dice": n=random.randint(1,6);add_tokens(sender,1,"r2-dice");safe_reply(client,f"🎲 *{n}* · +1 token",message,cj);return n
    if op=="coinflip": n=random.choice(["HEADS","TAILS"]);safe_reply(client,f"🪙 *{n}*",message,cj);return n
    if op=="guessnumber":
        if not gs.get("guess"): gs={"guess":random.randint(1,100),"tries":0};st["games"][key]=gs;_save_game_state(st);safe_reply(client,"🎯 Tebak 1–100.",message,cj);return
        try:n=int(p[0])
        except Exception:safe_reply(client,"Masukkan angka.",message,cj);return
        gs["tries"]+=1
        if n==gs["guess"]:
            rw=max(5,40-gs["tries"]*4);add_tokens(sender,rw,"guess");st["games"].pop(key,None);_game_win(sender);safe_reply(client,f"✅ Benar! +{rw}",message,cj)
        else:safe_reply(client,"⬆️ Kecil." if n<gs["guess"] else "⬇️ Besar.",message,cj)
        _save_game_state(st);return
    if op=="mathquiz":
        if "math" not in gs:
            x,y=random.randint(2,30),random.randint(2,30);st["games"][key]={"math":x*y};_save_game_state(st);safe_reply(client,f"🧮 {x} × {y} = ?",message,cj);return
        try:n=int(p[0])
        except Exception:safe_reply(client,"Jawab angka.",message,cj);return
        ans=gs["math"];st["games"].pop(key,None);_save_game_state(st);ok=n==ans;_game_win(sender) if ok else _game_loss(sender);add_tokens(sender,20 if ok else 0,"mathquiz");safe_reply(client,"✅ Benar +20" if ok else f"❌ {ans}",message,cj);return
    if op in ("scramble","hangman","trivia","wordchain"):
        if op=="scramble":
            if gs.get("word") and a:
                w=gs["word"];ok=a.lower()==w;st["games"].pop(key,None);_game_win(sender) if ok else _game_loss(sender);_save_game_state(st);safe_reply(client,"✅ Benar!" if ok else f"❌ {w}",message,cj);return
            w=random.choice(WORDS);st["games"][key]={"word":w};_save_game_state(st);safe_reply(client,"🔤 `"+"".join(random.sample(w,len(w)))+"`",message,cj);return
        if op=="hangman":
            if gs.get("word") and a:
                w=gs["word"];used=gs.setdefault("used",[]);ch=a.lower()[0];used.append(ch) if ch not in used else None;shown=" ".join(c if c in used else "_" for c in w);done=a.lower()==w or "_" not in shown.replace(" ","");
                if done:st["games"].pop(key,None);_game_win(sender);safe_reply(client,f"✅ {w}",message,cj)
                else:_save_game_state(st);safe_reply(client,f"🪢 {shown}",message,cj)
                return
            w=random.choice(WORDS);st["games"][key]={"word":w,"used":[]};_save_game_state(st);safe_reply(client,"🪢 "+" ".join("_" for _ in w),message,cj);return
        if op=="trivia":
            if gs.get("answers") and a:
                ok=a.lower() in gs["answers"];st["games"].pop(key,None);_game_win(sender) if ok else _game_loss(sender);_save_game_state(st);add_tokens(sender,15 if ok else 0,"trivia");safe_reply(client,"✅ Benar! +15" if ok else f"❌ {gs['answers'].split('|')[0]}",message,cj);return
            q,ans=random.choice(TRIVIA);st["games"][key]={"answers":"|".join(x.lower() for x in ans)};_save_game_state(st);safe_reply(client,f"❓ {q}",message,cj);return
        if op=="wordchain":
            if gs.get("wordchain") and a:
                prev=gs["wordchain"];w=a.lower().split()[0];ok=w.isalpha() and w[0]==prev[-1] and w not in gs.get("used",[])
                if ok:gs["wordchain"]=w;gs.setdefault("used",[]).append(w);gs["score"]=gs.get("score",0)+1;_save_game_state(st);safe_reply(client,f"✅ {w} · {gs['score']}",message,cj)
                else:_game_loss(sender);st["games"].pop(key,None);_save_game_state(st);safe_reply(client,"❌ Chain berakhir.",message,cj)
                return
            w=a.lower() if a else random.choice(WORDS);st["games"][key]={"wordchain":w,"used":[w],"score":0};_save_game_state(st);safe_reply(client,f"🔗 `{w}` → `{w[-1]}`",message,cj);return
    if op=="memory": return handle_memory_start(client,message,cj,chat,sender,ctx)
    if op in ("tictactoe","connect4","reversi"): return _board(client,message,cj,chat,sender,a,3 if op=="tictactoe" else 4,op)
    if op=="sudoku":
        puzzle=[[1,0,3,0],[0,4,0,2],[2,0,4,0],[0,3,0,1]];safe_reply(client,"🧩 4×4\n"+"\n".join(" ".join(str(x) if x else "·" for x in row) for row in puzzle),message,cj);return puzzle
    if op=="lottery":
        if not deduct_tokens(sender,10,"lottery"):safe_reply(client,"🎟️ Butuh 10 token.",message,cj);return
        t=random.randint(100000,999999);pr=5000 if t%100==0 else 500 if t%10==7 else 0;add_cash(sender,pr,"lottery");safe_reply(client,f"🎟️ `{t}` · +{pr} cash",message,cj);return
    if op=="typing": n=len(a);add_tokens(sender,max(1,n//20),"typing");safe_reply(client,f"⌨️ {n} chars",message,cj);return
    if op=="reaction":
        try:ms=float(p[0]) if p else 250
        except Exception:ms=250
        score=max(1,1000-int(ms));add_tokens(sender,max(1,score//100),"reaction");safe_reply(client,f"⚡ {ms:.0f}ms · {score}",message,cj);return
    if op=="flagquiz":
        flags={"🇮🇩":"indonesia","🇯🇵":"japan","🇺🇸":"united states","🇧🇷":"brazil","🇩🇪":"germany"}; target=gs.get("flag")
        if target and a: ok=a.lower()==target;st["games"].pop(key,None);_game_win(sender) if ok else _game_loss(sender);_save_game_state(st);safe_reply(client,"✅ Benar!" if ok else f"❌ {target}",message,cj);return
        fl=random.choice(list(flags));st["games"][key]={"flag":flags[fl]};_save_game_state(st);safe_reply(client,f"🚩 {fl}",message,cj);return
    if op=="truefalse":
        facts=[("Bumi mengelilingi Matahari.",True),("Air mendidih 50°C.",False)];tf=gs.get("tf")
        if tf is not None and p: ok=(p[0].lower() in ("true","t","benar","1"))==tf;st["games"].pop(key,None);_game_win(sender) if ok else _game_loss(sender);_save_game_state(st);safe_reply(client,"✅ Benar!" if ok else "❌ Salah.",message,cj);return
        q,v=random.choice(facts);st["games"][key]={"tf":v};_save_game_state(st);safe_reply(client,q+" TRUE/FALSE?",message,cj);return
    if op=="score":r=_rpg(sender);safe_reply(client,f"🎮 Wins {r['wins']} · Losses {r['losses']}",message,cj);return
    if op=="streak":safe_reply(client,f"🔥 { _rpg(sender).get('r2_streak',0)}",message,cj);return
    if op=="leaderboard":
        rows=[];root=Path(config.USER_DIR)
        for d in root.iterdir() if root.exists() else []:
            if d.is_dir(): rows.append((_rpg(d.name)['wins'],d.name))
        rows.sort(reverse=True);safe_reply(client,"🏆\n"+"\n".join(f"{i+1}. {u} · {w}" for i,(w,u) in enumerate(rows[:10])),message,cj);return
    if op=="gamehelp":safe_reply(client,"🎮 slot rps guessnumber mathquiz scramble hangman trivia wordchain tictactoe connect4 sudoku",message,cj)
def _board_reset(): return None
def _rpg_enemy(op,floor=1): return {"hunt":(30+floor*2,8+floor//4),"combat":(45+floor*3,11+floor//3),"dungeon":(55+floor*8,12+floor),"boss":(100+floor*15,16+floor),"raid":(220+floor*20,22+floor)}[op]
def _r2_rpg_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"];r=_rpg(sender);a=(args or "").split()
    if op=="rpgprofile":safe_reply(client,f"⚔️ Lv.{r['level']} XP {r['xp']}\n❤️ {r['hp']}/{r['max_hp']} · ⚔️ {r['atk']} · 🛡️ {r['def']}\n🎯 {r['crit']:.0%} · 🍀 {r['luck']:.0%}",message,cj);return
    if op in ("hunt","combat","dungeon","boss","raid"):
        floor=max(1,int(r.get("dungeon_floor",0))+1) if op=="dungeon" else max(1,r.get("battle",{}).get("floor",1));b=r.get("battle") or {};b={"op":op,"hp":_rpg_enemy(op,floor)[0],"floor":floor} if b.get("op")!=op else b;_,epow=_rpg_enemy(op,b["floor"]);dmg=_native_damage(r["atk"],epow//2,r["crit"],r["luck"]) or max(1,r["atk"]+random.randint(-2,5)-epow//2);taken=max(1,epow-r["def"]//2);b["hp"]-=dmg;r["hp"]-=taken
        if r["hp"]<=0:r["hp"]=r["max_hp"];_game_loss(sender);r.pop("battle",None);_save_rpg(sender,r);safe_reply(client,"💀 Kalah.",message,cj);return
        if b["hp"]<=0:
            xp=random.randint(15,30)+b["floor"];cash=random.randint(40,160)*(2 if op in ("boss","raid") else 1);r.pop("battle",None);r["wins"]+=1;r["r2_streak"]=r.get("r2_streak",0)+1
            if op=="dungeon":r["dungeon_floor"]=b["floor"]
            _save_rpg(sender,r);_level_gain(sender,xp);add_cash(sender,cash,f"r2-{op}");user_store.add_item(sender,"monster_shard",1,1,source=op);safe_reply(client,f"🏆 {op} clear · +{xp} XP · +{cash} cash",message,cj);return
        r["battle"]=b;_save_rpg(sender,r);safe_reply(client,f"⚔️ {op}: {dmg} dmg · enemy {b['hp']} · hp {r['hp']}",message,cj);return
    if op=="gacha":
        if not deduct_cash(sender,100,"gacha"):safe_reply(client,"💰 Butuh 100 cash.",message,cj);return
        r["gacha_pity"]+=1;leg=r["gacha_pity"]>=10;item="Dragon Blade" if leg else random.choice(["Moon Blade","Steel Axe","Hunter Bow"]);r["gacha_pity"]=0 if leg else r["gacha_pity"];_save_rpg(sender,r);user_store.add_item(sender,item.lower().replace(" ","_"),1,1,source="gacha");safe_reply(client,f"🎴 {'LEGENDARY' if leg else 'RARE'} · {item} · pity {r['gacha_pity']}/10",message,cj);return
    if op=="pity":safe_reply(client,f"🎴 Pity {r['gacha_pity']}/10",message,cj);return
    if op in ("gear","weapon","armor","accessory"):
        k=op if op in r["equipment"] else "weapon";safe_reply(client,f"🎒 {k}: {r['equipment'][k]}",message,cj);return
    if op in ("craft","forge","enchant","upgrade"):
        cost={"craft":50,"forge":80,"enchant":120,"upgrade":150}[op]
        if not deduct_cash(sender,cost,op):safe_reply(client,f"💰 Butuh {cost}.",message,cj);return
        r["atk"]+=2 if op!="enchant" else 1;r["def"]+=1 if op in ("forge","upgrade") else 0;_save_rpg(sender,r);safe_reply(client,f"🔧 {op} OK · ATK {r['atk']} DEF {r['def']}",message,cj);return
    if op=="pet":r["pet"]=a[0] if a else (r.get("pet") or "Fox");_save_rpg(sender,r);safe_reply(client,f"🐾 {r['pet']}",message,cj);return
    if op=="party":r["party"]=list(dict.fromkeys([sender]+a[:4]));_save_rpg(sender,r);safe_reply(client,"🤝 Party\n"+"\n".join(r["party"]),message,cj);return
    if op=="guild":r["guild"]=(args or "").strip() or r.get("guild") or "Cinnamon Guild";_save_rpg(sender,r);safe_reply(client,f"🏰 {r['guild']}",message,cj);return
    if op=="pvp":
        target=a[0] if a else "";tr=_rpg(target) if target and user_store.user_exists(target) else None
        if not tr:safe_reply(client,"⚔️ `/pvp <uid>`",message,cj);return
        m=r["atk"]*2+r["def"]+r["level"]+random.randint(0,20);o=tr["atk"]*2+tr["def"]+tr["level"]+random.randint(0,20);ok=m>=o;_game_win(sender) if ok else _game_loss(sender);add_cash(sender,100 if ok else 0,"pvp");safe_reply(client,"🏆 Menang +100 cash" if ok else "💀 Kalah PvP",message,cj);return
    if op=="loot":k=random.choice(["monster_shard","iron_ore","rare_gem"]);q=random.randint(1,3);user_store.add_item(sender,k,q,1,source="loot");safe_reply(client,f"🎁 {k} ×{q}",message,cj)
def _r2_progression_runner(client,message,cj,chat,sender,args,ctx,spec):
    if not require_login(client,message,cj,sender,ctx): return
    op=spec["operation"];r=_rpg(sender);nodes={"power1":("atk",2,None),"power2":("atk",4,"power1"),"guard1":("def",2,None),"guard2":("def",4,"guard1"),"crit1":("crit",.02,None),"luck1":("luck",.01,None),"luck2":("luck",.02,"luck1")}
    if op=="level":safe_reply(client,f"⭐ RPG Level {r['level']}",message,cj);return
    if op=="rank":safe_reply(client,f"👑 {permission_manager.role(sender).upper()}",message,cj);return
    if op=="xp":safe_reply(client,f"✨ RPG XP {r['xp']}",message,cj);return
    if op=="nextlevel":safe_reply(client,f"⏭️ Need {100*r['level']} XP",message,cj);return
    if op=="progress":safe_reply(client,f"📈 Lv {r['level']} · XP {r['xp']} · SP {r['skillpoints']}",message,cj);return
    vals={"power":r['atk']+r['def'],"attack":r['atk'],"defense":r['def'],"crit":r['crit'],"luck":r['luck'],"combatpower":r['atk']*2+r['def']+r['level']*5,"rating":r['wins']*10-r['losses']*4}
    if op in vals:safe_reply(client,f"📊 {op}: {vals[op]}",message,cj);return
    if op=="skillpoints":safe_reply(client,f"✨ {r['skillpoints']}",message,cj);return
    if op in ("skill","skilltree"):
        if not args or args.lower()=="list":safe_reply(client,"🌳\n"+"\n".join(f"▸ {k} prereq={v[2] or '-'}" for k,v in nodes.items()),message,cj);return
        k=args.lower().split()[0];n=nodes.get(k)
        if not n or r["skillpoints"]<1 or (n[2] and not r["skills"].get(n[2])):safe_reply(client,"❌ Skill point/prerequisite kurang.",message,cj);return
        stat,val,_=n;r[stat]+=val;r["skillpoints"]-=1;r["skills"][k]=r["skills"].get(k,0)+1;_save_rpg(sender,r);safe_reply(client,f"✅ {k}",message,cj);return
    if op=="unlock":safe_reply(client,"🔓 "+", ".join(["games"]+[x for x,l in (("dungeon",5),("gacha",8),("boss",10),("raid",15)) if r["level"]>=l]),message,cj);return
    if op=="milestone":safe_reply(client,f"🏁 Wins {r['wins']} · Floor {r.get('dungeon_floor',0)}",message,cj);return
    if op=="streak":safe_reply(client,f"🔥 {r.get('r2_streak',0)}",message,cj);return
    if op=="mastery":safe_reply(client,f"🏅 {min(100,r['wins']*2)}%",message,cj);return
    if op=="prestige":
        if r["level"]<20:safe_reply(client,"⭐ Butuh Lv.20",message,cj);return
        r["level"]=1;r["xp"]=0;r["prestige"]=r.get("prestige",0)+1;r["atk"]+=5;r["def"]+=3;_save_rpg(sender,r);safe_reply(client,f"🌟 Prestige {r['prestige']}",message,cj)
register_feature_specs("games",_r2_game_runner,category="games")
register_feature_specs("games",_r2_rpg_runner,category="rpg")
register_feature_specs("games",_r2_progression_runner,category="progression")
