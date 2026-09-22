"""CINNAMON v53 configuration and static tables."""
import os
import re
from pytz import timezone as pytz_timezone
DATA_DIR = "./data"
USER_DIR = os.path.join(DATA_DIR, "user")
OWNER_DIR = os.path.join(DATA_DIR, "owner-dat")
BUYER_DIR = os.path.join(DATA_DIR, "buyer-dat")
PENDING_DIR = os.path.join(DATA_DIR, "_pending")
SHARED_DIR = os.path.join(DATA_DIR, "_shared")
MEDIA_DIR = "./media_inbox"
TIKTOK_DIR = "./tiktok_downloads"
YTM_DIR = "./ytm_downloads"
DB_FILE = "./wa_session.db"
DEBUG_MODE = True
XP_MIN, XP_MAX, XP_COOLDOWN = 10, 15, 30
BRAT_SIZE = 512
STICKER_SIZE = 512
TOKEN_USER_BARU = 100
TOKEN_CAP = 2500
TOKEN_STC_POLOS = 2
TOKEN_STC_BRAT = 2
TOKEN_STC_VBRAT = 4
TOKEN_STC_UPDOWN = 3
TOKEN_STC_IMG2STK = 2
TOKEN_DL = 5
TOKEN_DL_MP3 = 4
TOKEN_TDOWN = 8
TOKEN_TDOWN_MP3 = 5
TOKEN_YTM = 8
DL_MAX_VIDEO_MB = 60
TOKEN_TTS = 3
TOKEN_QR = 2
TOKEN_WIKI = 2
TOKEN_DEFINE = 2
TOKEN_TRANSLATE = 3
TOKEN_CURRENCY = 2
TOKEN_IP_LOOKUP = 2
TOKEN_SCREENSHOT = 4
TOKEN_SHORT = 1
TOKEN_CRYPTO = 2
TOKEN_COUNTRY = 2
TOKEN_POKEMON = 2
TOKEN_ANIME = 3
TOKEN_CUACA = 2
TOKEN_GEMPA = 2
TOKEN_LIBUR = 1
TOKEN_NEWS = 2
TOKEN_BUKU = 2
TOKEN_RESEP = 2
DAILY_MIN, DAILY_MAX = 20, 50
WORK_MIN, WORK_MAX, WORK_COOLDOWN = 10, 30, 3600
REGISTER_BONUS_TOKENS = 150
REGISTER_TITLE = "[Early Access]"
GUEST_TITLE = "[none]"
MIN_NAME_LEN, MAX_NAME_LEN = 3, 20
MIN_PASSWORD_LEN = 6
SHOP_REFRESH_INTERVAL = 3600 * 6
SHOP_ITEMS_COUNT = 12
SESSION_TIMEOUT = 1800
OWNER_USERNAME = "Nyx1024"
OWNER_NUMBER_RAW = "+62 895-4266-61666"
OWNER_NUMBER_DIGITS = re.sub(r"\D", "", OWNER_NUMBER_RAW)
PREMIUM_DURATION_DAYS = 7
BOT_MODE = "public"
PENDING_TTL = 600
MAX_INPUT_LEN = 4096
PAID_COOLDOWN = 5
MAX_CONCURRENT_COMMANDS = 20
GROUP_OP_COOLDOWN = 10
PER_RECIPIENT_COOLDOWN = 30
BOT_DAILY_LIMIT = 1500
BOT_HOURLY_LIMIT = 200
BOT_MINUTE_LIMIT = 8
RATE_LIMIT_PER_USER = 20
BURST_FAIL_THRESHOLD = 5
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6
NIGHT_DELAY_MIN = 5.0
NIGHT_DELAY_MAX = 10.0
DAY_DELAY_MIN = 0.8
DAY_DELAY_MAX = 2.5
FISHING_COOLDOWN = 30
FISHING_COST = 2
FISHING_MAX_PER_DAY = 100
ROD_PRICES = {1: 500, 2: 1500, 3: 4000, 4: 10000, 5: 25000}
BASKET_PRICES = {1: 300, 2: 1000, 3: 3000, 4: 8000, 5: 20000}
ROD_RARE_BOOST = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}
BASKET_BONUS = {1: 0.10, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.50}
GAME_MAX_LEVEL = 20
PRESTIGE_MAX = 8
FISHING_ITEMS = {
    "common": {"name": "Old Shoe", "emoji": "👟", "sell": 5},
    "uncommon": {"name": "Small Fish", "emoji": "🐟", "sell": 15},
    "rare": {"name": "Salmon", "emoji": "🐠", "sell": 50},
    "epic": {"name": "Tuna", "emoji": "🐡", "sell": 150},
    "legend": {"name": "Legend Tuna", "emoji": "🦈", "sell": 500},
    "mythic": {"name": "Golden Fish", "emoji": "🐉", "sell": 2000},
}
GATHER_ITEMS = {
    "common": {"name": "Grass", "emoji": "🌿", "sell": 5},
    "uncommon": {"name": "Small Flower", "emoji": "🌸", "sell": 15},
    "rare": {"name": "Purple Mushroom", "emoji": "🍄", "sell": 50},
    "epic": {"name": "Ancient Herb", "emoji": "🌺", "sell": 150},
    "legend": {"name": "Earth Crystal", "emoji": "💎", "sell": 500},
    "mythic": {"name": "Primordial Root", "emoji": "🌳", "sell": 2000},
}
RARITY_BASE_WEIGHTS = {"common": 50, "uncommon": 25, "rare": 15, "epic": 7, "legend": 2.5, "mythic": 0.5}
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "⭐"]
SLOT_TIER = {"💎": 50, "7️⃣": 25, "⭐": 15, "🍇": 8, "🍊": 6, "🍋": 5, "🍒": 4}
SLOT_WEIGHTS = [40, 30, 20, 10, 1, 3, 8]
SLOT_BET_MIN, SLOT_BET_MAX, SLOT_COOLDOWN = 10, 2500, 5
ROB_COOLDOWN = 3600
ROB_SUCCESS_RATE = 0.20
ROB_MIN_STEAL_PCT, ROB_MAX_STEAL_PCT = 0.03, 0.10
ROB_FAIL_FINE = 0.15
MARRY_COST, MARRY_DIVORCE_COST = 500, 250
RPSBET_MIN, RPSBET_MAX = 10, 2500
BUYER_MAX_GROUPS = 3
BUYER_MAX_DAYS = 365
BUYER_DEFAULT_TRIAL_DAYS = 3
BUYER_DEFAULT_SERVICE_DAYS = 7
MINER_LEVELS = {
    1: {"interval": 12.0, "items_min": 1, "items_max": 1, "bonus_chance": 0.00, "high_tier_chance": 0.05, "max_items": 300},
    2: {"interval": 10.0, "items_min": 1, "items_max": 1, "bonus_chance": 0.05, "high_tier_chance": 0.10, "max_items": 320},
    3: {"interval": 9.0, "items_min": 1, "items_max": 1, "bonus_chance": 0.08, "high_tier_chance": 0.15, "max_items": 340},
    4: {"interval": 8.0, "items_min": 1, "items_max": 2, "bonus_chance": 0.10, "high_tier_chance": 0.20, "max_items": 360},
    5: {"interval": 7.0, "items_min": 1, "items_max": 2, "bonus_chance": 0.12, "high_tier_chance": 0.25, "max_items": 380},
    6: {"interval": 6.5, "items_min": 1, "items_max": 2, "bonus_chance": 0.14, "high_tier_chance": 0.30, "max_items": 400},
    7: {"interval": 6.0, "items_min": 1, "items_max": 2, "bonus_chance": 0.16, "high_tier_chance": 0.35, "max_items": 420},
    8: {"interval": 5.5, "items_min": 2, "items_max": 2, "bonus_chance": 0.18, "high_tier_chance": 0.40, "max_items": 450},
    9: {"interval": 5.0, "items_min": 2, "items_max": 2, "bonus_chance": 0.20, "high_tier_chance": 0.45, "max_items": 480},
    10: {"interval": 5.0, "items_min": 2, "items_max": 3, "bonus_chance": 0.25, "high_tier_chance": 0.50, "max_items": 500},
}
MINER_LEVEL_THRESHOLDS = [0, 100, 400, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
MINER_MAX_DURATION = 7200
STOCK_TICKERS = {
    "NYX": {"id": "STK001", "name": "Nyx Corp", "base_price": 100},
    "BTC": {"id": "STK002", "name": "ByteCoin", "base_price": 500},
    "ETH": {"id": "STK003", "name": "EtherCoin", "base_price": 300},
    "GLD": {"id": "STK004", "name": "GoldMine Inc", "base_price": 200},
    "SLV": {"id": "STK005", "name": "SilverCorp", "base_price": 50},
}
STOCK_VOLATILITY = 0.10
STOCK_MIN_PRICE, STOCK_MAX_PRICE = 10, 10000
STOCK_TRADE_FEE = 0.02
STOCK_UPDATE_INTERVAL = 30
FEATURE_CATEGORIES = ["games", "sticker", "download", "shop", "fun", "miner", "stock",
                      "gift", "utility", "social", "economy", "event", "fishing", "gathering"]
RANK_TIERS = [
    (1, 4, "🥚", "Mortal"), (5, 9, "🥉", "Bronze"), (10, 19, "🥈", "Silver"),
    (20, 29, "🥇", "Gold"), (30, 44, "💠", "Platinum"), (45, 59, "💎", "Diamond"),
    (60, 74, "🌟", "Hero"), (75, 89, "⚡", "Titan"), (90, 99, "🔥", "Olympian"),
    (100, 999, "👁️", "Ouranos"),
]
SYM_SEP      = "┊"
SYM_LINE     = "─"
SYM_HEAVY    = "━"
SYM_BULLET   = "▸"
SYM_STAR     = "✦"
SYM_DIAMOND  = "◈"
SYM_CHECK    = "✓"
SYM_CROSS    = "✗"
SYM_ARROW    = "❯"
SYM_DOT      = "·"
SYM_TOP_L    = "╭"
SYM_TOP_R    = "╮"
SYM_BOT_L    = "╰"
SYM_BOT_R    = "╯"
SYM_TITLE_L  = "「"
SYM_TITLE_R  = "」"
SYM_NOTE     = "❖"
SYM_SHIELD   = "⛨"
SYM_SPARK    = "✧"
SYM_RING     = "◉"
EVENT_TYPES = {
    "xp": {"name": "Kumpulkan XP", "unit": "XP"},
    "game": {"name": "Main game", "unit": "kali"},
    "mine": {"name": "Mining", "unit": "item"},
    "sell": {"name": "Jual", "unit": "item"},
    "gift": {"name": "Gift", "unit": "kali"},
    "slot_win": {"name": "Menang slot", "unit": "kali"},
    "daily": {"name": "Daily", "unit": "hari"},
    "fish": {"name": "Mancing", "unit": "kali"},
    "gather": {"name": "Mungut", "unit": "kali"},
}
SHOP_ITEM_DEFS = {
    "potion_luck": {"id": "ITM005", "name": "Lucky Potion", "emoji": "🍀", "desc": "Luck +15% 1j",
                    "base_price": 200, "duration": 3600, "category": "potion", "luck_bonus": 0.15},
    "boost_token_2x": {"id": "BST001", "name": "Token Boost 2x", "emoji": "💰", "desc": "Token ×2 1j",
                       "base_price": 80, "duration": 3600, "category": "boost", "mult": 2.0},
    "boost_token_3x": {"id": "BST002", "name": "Token Boost 3x", "emoji": "💎", "desc": "Token ×3 30m",
                       "base_price": 150, "duration": 1800, "category": "boost", "mult": 3.0},
    "boost_xp_2x": {"id": "BST003", "name": "XP Boost 2x", "emoji": "✨", "desc": "XP ×2 1j",
                    "base_price": 100, "duration": 3600, "category": "boost", "mult": 2.0},
    "premium_7d": {"id": "PRM001", "name": "Premium 7D", "emoji": "💎", "desc": "Premium 7 hari",
                   "base_price": 2500, "category": "premium", "duration": 7},
    "premium_30d": {"id": "PRM002", "name": "Premium 30D", "emoji": "💠", "desc": "Premium 30 hari",
                    "base_price": 8000, "category": "premium", "duration": 30},
    "nametag": {"id": "NMT001", "name": "Name Tag", "emoji": "📝", "desc": "Ganti nama",
                "base_price": 400, "category": "nametag"},
    "reroll_cd": {"id": "MSC001", "name": "Reroll CD", "emoji": "🎲", "desc": "Reset cooldown",
                  "base_price": 20, "category": "misc"},
    "lucky_charm": {"id": "MSC002", "name": "Lucky Charm", "emoji": "🍀", "desc": "Luck +15% 2j",
                    "base_price": 150, "duration": 7200, "category": "misc", "luck_bonus": 0.15},
    "big_clover": {"id": "MSC003", "name": "Big Clover", "emoji": "🍀✨", "desc": "Luck +25% 2j",
                   "base_price": 400, "duration": 7200, "category": "misc", "luck_bonus": 0.25},
    "lootbox_bronze": {"id": "BOX001", "name": "Bronze Box", "emoji": "📦", "desc": "Basic",
                       "base_price": 50, "category": "lootbox"},
    "lootbox_silver": {"id": "BOX002", "name": "Silver Box", "emoji": "📦", "desc": "Rare",
                       "base_price": 150, "category": "lootbox"},
    "lootbox_gold": {"id": "BOX003", "name": "Gold Box", "emoji": "🎁", "desc": "Epic",
                     "base_price": 400, "category": "lootbox"},
    "lootbox_diamond": {"id": "BOX004", "name": "Diamond Box", "emoji": "💠", "desc": "Legendary",
                        "base_price": 1000, "category": "lootbox"},
}
ITEM_CATEGORIES = {
    "potion":   {"name": "Potions",   "emoji": "🧪", "order": 1},
    "boost":    {"name": "Boosts",    "emoji": "💎", "order": 2},
    "premium":  {"name": "Premium",   "emoji": "💠", "order": 3},
    "nametag":  {"name": "Name Tags", "emoji": "📝", "order": 4},
    "misc":     {"name": "Misc",      "emoji": "🎲", "order": 5},
    "lootbox":  {"name": "Lootboxes", "emoji": "📦", "order": 6},
    "fish":     {"name": "Fish",      "emoji": "🐟", "order": 7},
    "forage":   {"name": "Forage",    "emoji": "🌿", "order": 8},
    "other":    {"name": "Other",     "emoji": "❖",  "order": 99},
}
UNIVERSAL_ACHIEVEMENTS = {
    "token_1k": {"name": "First Thousand", "desc": "1.000 token", "emoji": "💰", "title": "💰 Saver"},
    "token_2k": {"name": "Two Thousand", "desc": "2.000 token", "emoji": "💎", "title": "💎 Collector"},
    "token_max": {"name": "Max Cap", "desc": "2.500 token", "emoji": "🏦", "title": "🏦 Banker"},
    "fish_10": {"name": "Novice Fisher", "desc": "10 catch", "emoji": "🎣", "title": "🎣 Angler"},
    "fish_100": {"name": "Expert Fisher", "desc": "100 catch", "emoji": "🎣", "title": "🎣 Fisherman"},
    "fish_1000": {"name": "Master Fisher", "desc": "1.000 catch", "emoji": "🎣", "title": "🎣 King Fisher"},
    "fish_mythic": {"name": "Mythic Hunter", "desc": "1 mythic", "emoji": "🌟", "title": "🌟 Mythic"},
    "gather_10": {"name": "Novice Forager", "desc": "10 gather", "emoji": "🍄", "title": "🍄 Gatherer"},
    "gather_100": {"name": "Expert Forager", "desc": "100 gather", "emoji": "🍄", "title": "🍄 Forager"},
    "gather_1000": {"name": "Master Forager", "desc": "1.000 gather", "emoji": "🍄", "title": "🍄 Legendary"},
    "prestige_1": {"name": "First Prestige", "desc": "1x", "emoji": "⭐", "title": "⭐ Reborn"},
    "prestige_3": {"name": "Triple Prestige", "desc": "3x", "emoji": "🌟", "title": "🌟 Veteran"},
    "prestige_5": {"name": "Penta Prestige", "desc": "5x", "emoji": "💫", "title": "💫 Master"},
    "prestige_8": {"name": "Max Prestige", "desc": "8x", "emoji": "👑", "title": "👑 Ouranos Reborn"},
    "slot_100": {"name": "Slot Addict", "desc": "100x slot", "emoji": "🎰", "title": "🎰 Gambler"},
    "slot_jackpot": {"name": "Jackpot!", "desc": "3x 💎", "emoji": "💎", "title": "💎 Lucky"},
    "mine_1000": {"name": "Hard Miner", "desc": "1.000 mine", "emoji": "⛏️", "title": "⛏️ Miner"},
    "mine_10000": {"name": "Master Miner", "desc": "10.000 mine", "emoji": "⛏️", "title": "⛏️ Mining Legend"},
    "gift_50": {"name": "Generous", "desc": "50x gift", "emoji": "🎁", "title": "🎁 Giver"},
    "marry": {"name": "Taken", "desc": "Menikah", "emoji": "💍", "title": "💍 Taken"},
    "guild_leader": {"name": "Guild Master", "desc": "Bikin guild", "emoji": "🏰", "title": "🏰 Founder"},
    "all_rounder": {"name": "All Rounder", "desc": "10 ach lain", "emoji": "🌌", "title": "🌌 Omnipotent"},
}
COMMAND_CATEGORY = {
    "/slot": "games", "/captcha": "games", "/math": "games", "/scramble": "games",
    "/rps": "games", "/trivia": "games", "/tebakangka": "games", "/rpsbet": "games",
    "/nguess": "games", "/wordchain": "games", "/memory": "games",
    "/mancing": "fishing", "/fishing": "fishing",
    "/mungut": "gathering", "/gathering": "gathering",
    "/stc": "sticker", "/toimg": "sticker", "/tovn": "sticker",
    "/dl": "download", "/tdown": "download", "/ytm": "download",
    "/shop": "shop", "/buy": "shop", "/inventory": "shop", "/tas": "shop",
    "/invcheck": "shop",
    "/use": "shop", "/sell": "shop", "/gshop": "shop", "/gbuy": "shop",
    "/miner": "miner", "/stock": "stock", "/gift": "gift",
    "/miniowner": "shop", "/minipanel": "shop", "/buyerpanel": "shop",
    "/rob": "economy", "/daily": "economy", "/dailybox": "economy",
    "/work": "economy", "/balance": "economy",
    "/marry": "social", "/achievements": "social",
    "/joke": "fun", "/quote": "fun", "/fact": "fun", "/8ball": "fun",
    "/truth": "fun", "/dare": "fun", "/rate": "fun", "/gay": "fun",
    "/jodoh": "fun", "/say": "fun", "/dice": "fun", "/roll": "fun",
    "/translate": "utility", "/tr": "utility", "/cuaca": "utility",
    "/gempa": "utility", "/libur": "utility", "/news": "utility",
    "/buku": "utility", "/resep": "utility", "/ip": "utility",
    "/short": "utility", "/ss": "utility", "/screenshot": "utility",
    "/crypto": "utility", "/country": "utility", "/pokemon": "utility", "/anime": "utility",
    "/qr": "utility", "/tts": "utility", "/wiki": "utility",
    "/define": "utility", "/kalkulator": "utility", "/calc": "utility",
    "/encode": "utility", "/decode": "utility", "/pw": "utility", "/nama": "utility", "/info": "utility",
    "/event": "event", "/claimbox": "event",
}
WIB = pytz_timezone("Asia/Jakarta")
BOT_MODE = "public"
BUILD_TAG = "CINNAMON-R1-V2-BATCH1"
UI_REVISION = 2

R2_BUILD = "CINNAMON-R2-500"
R2_TARGET_FEATURES = 500
R2_ALIASES_PER_FEATURE = 5
R2_CATEGORY_TREE = {
    "account": ("Account", "👤", "auth", "profile whoami identity activity aliases login logout rename password title titlelist titleuse rank level xp stats session security recovery preferences"),
    "access": ("Access & Permission", "🔐", "auth", "permissions roles roleinfo group_role group_grant group_revoke context accesscheck inheritance mo_status owner_status admin_status premium_status feature_access permission_help set_mo revoke_mo set_admin revoke_admin"),
    "economy": ("Economy", "💰", "economy", "balance daily work rob dailybox bank deposit withdraw transfer loan repay invest portfolio interest budget networth tax gift cashflow ledger"),
    "games": ("Games", "🎮", "games", "slot rps dice coinflip guessnumber mathquiz scramble hangman trivia wordchain memory tictactoe connect4 reversi sudoku lottery typing reaction flagquiz truefalse"),
    "rpg": ("RPG", "⚔️", "games", "rpgprofile hunt combat dungeon boss raid gacha pity gear weapon armor accessory craft forge enchant upgrade pet party guild pvp loot"),
    "progression": ("Progression", "📈", "games", "level rank xp nextlevel progress power attack defense crit luck skillpoints skill skilltree unlock milestone streak mastery combatpower rating prestige"),
    "inventory": ("Inventory", "🎒", "shop", "inventory invlist itemsearch iteminfo itemcount itemsort itemdrop itemuse itemequip itemunequip itemrename collection codex consumables materials weapons armor accessories capacity cleanup"),
    "quest": ("Quest", "📜", "event", "quest quests dailyquest weeklyquest claimquest questprogress questinfo questreset questreward queststreak questlog objective contract bounty mission huntquest collectionquest economyquest gamequestboard"),
    "achievement": ("Achievement", "🏆", "auth", "achievement achievements universalach gameach slotach rpgach fishingach miningach economyach eventach collectach explorerach completionach achievementprogress achievementstats achievementreward achievementtitle achievementhelp achievementrecent achievementclaim"),
    "event": ("Events", "🎁", "event", "event events airdrop claimbox claimraid worldevent eventstatus eventjoin eventleave eventreward eventleaderboard eventhistory seasonal dailyfest jackpot meteor chest invasion lottery_event festival"),
    "fishing": ("Fishing", "🐟", "fishing", "fish fishing cast bait rod basket pond river lake rarefish epicfish legendfish mythicfish fishquest fishlevel fishprestige fishsell fishequip fishgear fishcollection"),
    "mining": ("Mining", "⛏️", "fishing", "mine miner minestart minestop minestatus minelevel mineprogress mineore minegold minediamond minecrystal mineloot mineboost mineinventory minestats minelogs minerdaily mineupgrade"),
    "market": ("Market", "📊", "economy", "market stocks stockquote stockbuy stocksell portfolio watchlist pricechart marketlist marketstatus marketopen marketclose tradehistory fees dividends volatility highlow volume marketnews mocktrade"),
    "shop": ("Shop", "🛒", "shop", "shop shoplist shopsearch shopbuy shopinfo shoprefresh shoprandom shopcategory dailyshop premiumshop itemprice selllist sellprice bundle lootbox openbox nametag booster shophistory discount"),
    "group": ("Group", "👥", "group", "groupid ginfo members everyone tagall kick add del open close remind welcome goodbye rules announce poll stats activity cleanup pin"),
    "moderation": ("Security & Moderation", "🛡️", "group", "antilink antispam antibadword antisticker antistatus antidelete antiedit mute unmute warn warnremove warnlist whitelist blacklist lock unlock scan audit modlog ratelimit"),
    "mo": ("Mini Owner", "🤝", "buyer", "mo mopanel mogroups moconfig mosecurity mostats mowelcome mogoodbye momoderation moperks mobilling moexpiry moschedule moautoresponse moevent moaccess morole motheme mohelp moaudit"),
    "owner": ("Owner", "👑", "buyer", "ownerpanel users buyers ban unban token premium toggle eval system health logs backup restore reload shutdown ownerstats owneraudit grant revoke maintenance"),
    "media": ("Media Downloader", "📥", "media", "tiktok youtube instagram facebook twitter reddit pinterest soundcloud spotify vimeo dailymotion twitch bilibili mediafire threads snapchat likee weibo line tumblr"),
    "image": ("Image Processing", "🖼️", "media", "blur sharpen contrast brightness sepia grayscale negate emboss edge pixelate mirror flip rotate crop resize watermark autocontrast posterize solarize contour"),
    "videoaudio": ("Video & Audio", "🎬", "media", "videoinfo trim crop speed slow fast reverse mute volume normalize gif extractaudio audioinfo audiotrim audiocut audiomerge pitch bass treble fadein"),
    "converter": ("Converter & Document", "📄", "utility", "pdf2docx docx2pdf pdf2img img2pdf png2jpg jpg2png png2webp webp2png avif2png csv2json json2csv csv2xlsx xlsx2csv md2html html2md base64encode base64decode qrgen qrscan fileinfo"),
    "utility": ("Utility", "🧰", "utility", "calculator percentage ratio average median mode gcd lcm primefactor fibonacci units length area volume weight temperature time date timestamp uuid password hash"),
    "search": ("Search & Information", "🔎", "utility", "google bing ddg imagesearch youtubesearch githubsearch wikipedia news weather dictionary translate currency crypto stockinfo package domain dns iplookup books anime pokemon"),
    "funtext": ("Fun & Text", "🎲", "utility", "joke quote fact truth dare roast compliment ship rate coin dice roll randomname randomcolor randomnumber randomword choose shuffle upper lower"),
}

def _build_r2_features():
    features=[]; gid=0
    occupied=set(COMMAND_CATEGORY)
    extras={"access":["node_list"],"mining":["mineclaim","mineauto"],"quest":["questaccept"]}
    for category,(title,emoji,handler,raw) in R2_CATEGORY_TREE.items():
        ops=(raw.split()+extras.get(category,[]))[:20]
        for op in ops:
            gid+=1
            base=f"/{op}"
            aliases=[]
            candidates=[base,f"/{category}-{op}",f"/{category}{op}",f"/r2-{category}-{op}",f"/{op}-cin"]
            for alias in candidates:
                if alias not in aliases:
                    aliases.append(alias)
            if base in occupied or len(aliases)<R2_ALIASES_PER_FEATURE:
                aliases[0]=f"/r2-{category}-{op}"
            for a in aliases:
                occupied.add(a)
            features.append({"id":gid,"category":category,"title":title,"emoji":emoji,"handler":handler,"operation":op,"aliases":tuple(aliases)})
    return tuple(features)

R2_CATEGORY_SHORTCUTS={"economy":"eco","games":"game","rpg":"rpg","inventory":"inv","quest":"quest","achievement":"ach","event":"event","fishing":"fish","mining":"mine","market":"market","shop":"shop","group":"group","moderation":"mod","mo":"mo","owner":"owner","media":"media","image":"image","converter":"convert","utility":"tools","search":"search","funtext":"fun"}
R2_FEATURES = _build_r2_features()
R2_FEATURES_BY_HANDLER = {}
for _f in R2_FEATURES:
    R2_FEATURES_BY_HANDLER.setdefault(_f["handler"], []).append(_f)
R2_FEATURES_BY_CATEGORY = {}
for _f in R2_FEATURES:
    R2_FEATURES_BY_CATEGORY.setdefault(_f["category"], []).append(_f)
R2_FEATURE_COUNT = len(R2_FEATURES)
FISHING_QUESTS = {}
GATHER_QUESTS = {}
for i in range(1, GAME_MAX_LEVEL + 1):
    m = 1.35 ** (i - 1)
    FISHING_QUESTS[i] = [
        {"type": "total", "target": int(round(5 * m)), "desc": f"Catch {int(round(5 * m))} fish"},
        {"type": "rare_plus", "target": int(round(3 * m)), "desc": f"Catch {int(round(3 * m))} Rare+"},
        {"type": "epic_plus", "target": int(round(1 * m)), "desc": f"Catch {int(round(1 * m))} Epic+"},
    ]
    GATHER_QUESTS[i] = [
        {"type": "total", "target": int(round(5 * m)), "desc": f"Gather {int(round(5 * m))} items"},
        {"type": "rare_plus", "target": int(round(3 * m)), "desc": f"Gather {int(round(3 * m))} Rare+"},
        {"type": "epic_plus", "target": int(round(1 * m)), "desc": f"Gather {int(round(1 * m))} Epic+"},
    ]
GAME_LEVEL_REWARDS = {i: 50 * i * i for i in range(1, GAME_MAX_LEVEL + 1)}
_sched_path = os.path.join(SHARED_DIR, "schedules.json")
OWNER_REGISTRY_PATH = os.path.join(SHARED_DIR, "owners.json")
OWNER_CONFIG_PATH = os.path.join(SHARED_DIR, "owner_config.json")
