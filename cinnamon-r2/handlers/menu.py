from handlers import register, COMMANDS
from handlers.auth import require_login
from handlers.event import handle_event
from handlers.owner import handle_owner_help
import config
import logging
import time
from core.utils import box_bottom, box_title, hline
from core.storage import user_store, buyer_store
from core.identity import title_manager
from core.economy import get_luck
from core.send import safe_reply
def build_root_menu(uid, is_owner, is_buyer, is_admin=False):
    p=user_store.get_profile(uid); e=user_store.get_economy(uid); name=p.get('name') or 'Guest'
    role='OWNER' if is_owner else ('MINI-OWNER' if is_buyer else 'USER')
    title=title_manager.active(uid) if 'title_manager' in globals() else p.get('title')
    rows=[f'{config.SYM_STAR} *CINNAMON R2*',f'{box_title("PROFILE",26)}',f'👤 *{name}*',f'👑 Rank: *{role}*',f'🏷️ Title: *{title or "—"}*',f'⭐ Lv {p.get("level",1)} · 💰 {e.get("cash",0)} · 🪙 {e.get("tokens",0)}',f'{box_bottom(26)}',f'{config.SYM_DIAMOND} *PRIORITAS*']
    keys=['economy','games','rpg','inventory','quest','achievement','event','fishing','mining','market','shop','group','media','image','converter','utility','search','funtext']
    if is_admin: keys.insert(11,'moderation')
    if is_buyer: keys.insert(0,'mo')
    if is_owner: keys.insert(0,'owner')
    seen=set()
    for k in keys:
        if k in seen or k not in config.R2_CATEGORY_TREE: continue
        seen.add(k); title_k,emoji,_,_=config.R2_CATEGORY_TREE[k]; rows.append(f'{emoji} `/{config.R2_CATEGORY_SHORTCUTS.get(k,k)}` · {title_k}')
    rows += [f'{hline(26)}',f'{config.SYM_ARROW} `/m <kategori>` · `/m find <kata>`']
    return '\n'.join(rows)

@register('/m')
@register('/help')
@register('/menu')
@register('/')
@register('/?')
def handle_menu(client, message, cj, chat, sender, args, ctx):
    a = (args or "").strip().lower()
    if not a:
        safe_reply(client, build_root_menu(sender, ctx["is_owner"], ctx["is_buyer"], ctx.get("is_admin",False)), message, cj)
        return
    if a in ("sticker", "stiker", "1"):
        safe_reply(client,
            f"{box_title('STICKER', 22)}\n"
            f"{config.SYM_BULLET} `/stc` (reply img) {config.SYM_ARROW} polosan\n"
            f"{config.SYM_BULLET} `/stc brat <teks>`\n"
            f"{config.SYM_BULLET} `/stc vbrat <teks>`\n"
            f"{config.SYM_BULLET} Reply img {config.SYM_ARROW} `/stc up <teks>`\n"
            f"{config.SYM_BULLET} Reply img {config.SYM_ARROW} `/stc down <teks>`\n"
            f"{config.SYM_BULLET} Reply sticker {config.SYM_ARROW} `/toimg`\n"
            f"{config.SYM_BULLET} Reply video {config.SYM_ARROW} `/tovn`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("dl", "download", "2"):
        safe_reply(client,
            f"{box_title('DOWNLOAD', 22)}\n"
            f"{config.SYM_BULLET} `/dl mp4 <url>`\n"
            f"{config.SYM_BULLET} `/dl mp3 <url>`\n"
            f"{config.SYM_BULLET} `/tdown <url>`\n"
            f"{config.SYM_BULLET} `/tdown mp3 <url>`\n"
            f"{config.SYM_BULLET} `/ytm <judul>`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("shop", "3"):
        safe_reply(client,
            f"{box_title('SHOP', 22)}\n"
            f"{config.SYM_BULLET} `/shop` {config.SYM_DOT} `/shop buy <n>`\n"
            f"{config.SYM_BULLET} `/inventory` (detail)\n"
            f"{config.SYM_BULLET} `/tas` (ringkas)\n"
            f"{config.SYM_BULLET} `/use <key>` {config.SYM_DOT} `/sell <key>`\n"
            f"{config.SYM_BULLET} `/gshop` {config.SYM_DOT} `/gbuy <n>`\n"
            f"{config.SYM_BULLET} Buyer {config.SYM_ARROW} `/miniowner`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("eco", "ekonomi", "4"):
        safe_reply(client,
            f"{box_title('EKONOMI', 22)}\n"
            f"{config.SYM_BULLET} `/balance` `/daily` `/work`\n"
            f"{config.SYM_BULLET} `/rob <user>` `/dailybox`\n"
            f"{config.SYM_BULLET} `/miner start|stop|status`\n"
            f"{config.SYM_BULLET} `/stock` `/stock buy <n> <q>`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("games", "game", "5"):
        safe_reply(client,
            f"{box_title('GAMES', 22)}\n"
            f"{config.SYM_BULLET} `/slot <bet>` `/rps b|g|k`\n"
            f"{config.SYM_BULLET} `/rpsbet <b|g|k> <bet>`\n"
            f"{config.SYM_BULLET} `/captcha` `/math` `/scramble`\n"
            f"{config.SYM_BULLET} `/trivia` `/tebakangka` `/nguess`\n"
            f"{config.SYM_BULLET} `/wordchain` `/memory`\n"
            f"{config.SYM_BULLET} `/jawab <jawaban>` `/exit`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("fun", "6"):
        safe_reply(client,
            f"{box_title('FUN', 22)}\n"
            f"{config.SYM_BULLET} `/joke` `/quote` `/fact`\n"
            f"{config.SYM_BULLET} `/8ball <q>` `/truth` `/dare`\n"
            f"{config.SYM_BULLET} `/rate` `/gay` `/jodoh`\n"
            f"{config.SYM_BULLET} `/dice` `/roll` `/say <teks>`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("social", "sosial", "7"):
        safe_reply(client,
            f"{box_title('SOSIAL', 22)}\n"
            f"{config.SYM_BULLET} `/marry <user>` `/divorce`\n"
            f"{config.SYM_BULLET} `/gift token <u> <n>`\n"
            f"{config.SYM_BULLET} `/gift item <u> <k> <q>`\n"
            f"{config.SYM_BULLET} `/achievements`\n"
            f"{config.SYM_BULLET} `/whoami` `/activity` `/fixme`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("tools", "8"):
        safe_reply(client,
            f"{box_title('TOOLS', 22)}\n"
            f"{config.SYM_BULLET} `/cuaca` `/gempa` `/libur`\n"
            f"{config.SYM_BULLET} `/news` `/buku` `/resep`\n"
            f"{config.SYM_BULLET} `/translate` `/currency`\n"
            f"{config.SYM_BULLET} `/ip` `/short` `/ss`\n"
            f"{config.SYM_BULLET} `/crypto` `/country`\n"
            f"{config.SYM_BULLET} `/pokemon` `/anime`\n"
            f"{config.SYM_BULLET} `/qr` `/tts` `/wiki`\n"
            f"{config.SYM_BULLET} `/define` `/kalkulator`\n"
            f"{config.SYM_BULLET} `/encode` `/decode`\n"
            f"{config.SYM_BULLET} `/pw` `/nama` `/info`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a in ("me", "profil", "9"):
        handle_me(client, message, cj, chat, sender, "", ctx)
        return
    if a in ("event", "0"):
        handle_event(client, message, cj, chat, sender, "", ctx)
        return
    if a == "owner" and ctx["is_owner"]:
        handle_owner_help(client, message, cj)
        return
    if a == "buyer" and ctx["is_buyer"]:
        safe_reply(client,
            f"{box_title('BUYER', 22)}\n"
            f"{config.SYM_BULLET} `/bindgroup`\n"
            f"{config.SYM_BULLET} `/mygroups`\n"
            f"{config.SYM_BULLET} `/myself on|off`\n"
            f"{box_bottom(22)}", message, cj)
        return
    if a == "all" or a.startswith("all "):
        safe_reply(client, "📚 Gunakan `/m <kategori>` supaya menu tetap ringkas.", message, cj)
        return
    parts=a.split(); cat=parts[0] if parts else a; cat=next((k for k,v in config.R2_CATEGORY_SHORTCUTS.items() if v==cat),cat)
    if cat in config.R2_CATEGORY_TREE:
        page=max(0,int(parts[1])-1) if len(parts)>1 and parts[1].isdigit() else 0
        title_k,emoji,_,_=config.R2_CATEGORY_TREE[cat]; specs=config.R2_FEATURES_BY_CATEGORY.get(cat,[])
        chunk=specs[page*12:(page+1)*12]; maxp=max(1,(len(specs)+11)//12)
        lines=[f"{box_title(emoji+' '+title_k.upper(),28)}",f"Page *{page+1}/{maxp}* · *{len(specs)} fitur*",""]
        lines += [f"{config.SYM_BULLET} `{sp['aliases'][0]}`" for sp in chunk]
        lines += ["",f"{config.SYM_ARROW} `/m {cat} {page+2 if page+1<maxp else 1}`",box_bottom(28)]
        safe_reply(client,'\n'.join(lines),message,cj); return
    if a.startswith("find "):
        term = a[5:].strip()
        safe_reply(client, _command_search(term), message, cj)
        return
    safe_reply(client, build_root_menu(sender, ctx["is_owner"], ctx["is_buyer"], ctx.get("is_admin",False)), message, cj)

def _command_browser_page(page=0, page_size=40):
    cmds = sorted(COMMANDS)
    total = len(cmds)
    max_page = max(1, (total + page_size - 1) // page_size)
    page = min(max(page, 0), max_page - 1)
    chunk = cmds[page * page_size:(page + 1) * page_size]
    lines = [
        f"{box_title('COMMAND TREE', 26)}",
        f"{config.SYM_BULLET} Page *{page + 1}/{max_page}* {config.SYM_DOT} {total} commands",
        f"{config.SYM_BULLET} Gunakan `/m all 2` untuk halaman berikutnya",
        "",
    ]
    for i in range(0, len(chunk), 4):
        lines.append("  ".join(f"`{c}`" for c in chunk[i:i+4]))
    lines += ["", f"{config.SYM_ARROW} `/m find <kata>` untuk pencarian", box_bottom(26)]
    return "\n".join(lines)

def _command_search(term):
    q=(term or '').strip().lower()
    if not q: return f"{box_title('SEARCH',26)}\n{config.SYM_CROSS} Masukkan kata.\n{box_bottom(26)}"
    hits=[]
    for sp in config.R2_FEATURES:
        if q in sp['operation'].lower() or q in sp['title'].lower(): hits.append((sp['category'],sp['aliases'][0]))
    lines=[f"{box_title('FEATURE SEARCH',28)}",f"Query: *{q}*",""]+[f"▸ `{cmd}` · {cat}" for cat,cmd in hits[:30]]
    if not hits: lines.append('Tidak ditemukan.')
    lines += ['',box_bottom(28)]
    return '\n'.join(lines)

@register('/eco')
def handle_cat_eco(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'economy')

@register('/game')
def handle_cat_game(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'games')

@register('/rpg')
def handle_cat_rpg(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'rpg')

@register('/inv')
def handle_cat_inv(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'inventory')

@register('/quest')
def handle_cat_quest(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'quest')

@register('/ach')
def handle_cat_ach(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'achievement')

@register('/fish')
def handle_cat_fish(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'fishing')

@register('/mine')
def handle_cat_mine(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'mining')

@register('/market')
def handle_cat_market(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'market')

@register('/group')
def handle_cat_group(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'group')

@register('/mod')
def handle_cat_mod(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'moderation')

@register('/mo')
def handle_cat_mo(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'mo')

@register('/media')
def handle_cat_media(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'media')

@register('/image')
def handle_cat_image(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'image')

@register('/convert')
def handle_cat_convert(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'converter')

@register('/tools')
def handle_cat_tools(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'utility')

@register('/search')
def handle_cat_search(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'search')

@register('/fun')
def handle_cat_fun(client,message,cj,chat,sender,args,ctx): return _show_category(client,message,cj,chat,sender,args,ctx,'funtext')

def _show_category(client,message,cj,chat,sender,args,ctx,cat):
    if cat not in config.R2_CATEGORY_TREE: safe_reply(client,"Kategori tidak ditemukan.",message,cj); return
    a=(args or "").strip().split(); page=max(0,int(a[0])-1) if a and a[0].isdigit() else 0; title_k,emoji,_,_=config.R2_CATEGORY_TREE[cat]; specs=config.R2_FEATURES_BY_CATEGORY.get(cat,[]); maxp=max(1,(len(specs)+11)//12); page=min(page,maxp-1); chunk=specs[page*12:(page+1)*12]
    lines=[f"{box_title(emoji+' '+title_k.upper(),28)}",f"Page *{page+1}/{maxp}* · *{len(specs)} fitur*",""]+[f"{config.SYM_BULLET} `{x['aliases'][0]}`" for x in chunk]+["",f"{config.SYM_ARROW} `/{config.R2_CATEGORY_SHORTCUTS.get(cat,cat)} {page+2 if page+1<maxp else 1}`",box_bottom(28)]
    safe_reply(client,"\n".join(lines),message,cj)

def handle_me(client, message, cj, chat, sender, args, ctx):
    if not require_login(client, message, cj, sender, ctx):
        return
    p = user_store.get_profile(sender)
    e = user_store.get_economy(sender)
    name = p.get("name") or "Guest"
    lv = p.get("level", 1)
    safe_reply(client,
        f"{box_title('PROFIL', 22)}\n"
        f"{config.SYM_BULLET} Nama: *{name}*\n"
        f"{config.SYM_BULLET} Account Rank: *{('OWNER' if ctx.get('is_owner') else 'MINI-OWNER' if ctx.get('is_buyer') else 'USER')}*\n"
        f"{config.SYM_BULLET} Title: *{title_manager.active(sender) or p.get('title') or '—'}*\n"
        f"{config.SYM_BULLET} Level: *{lv}*\n"
        f"{config.SYM_BULLET} Token: *{e.get('tokens', 0)}/{config.TOKEN_CAP}*\n"
        f"{config.SYM_BULLET} Cash: *{e.get('cash', 0)}*\n"
        f"{config.SYM_BULLET} Luck: *+{int(get_luck(sender) * 100)}%*\n"
        f"{config.SYM_BULLET} Marriage: {'aktif' if p.get('married_to') else 'belum'}\n"
        f"{box_bottom(22)}",
        message, cj)
