# CINNAMON R2 — 500 Feature Systems

Cinnamon adalah bot WhatsApp berbasis Neonize dengan pendekatan **account-first**, permission context, progression, games/RPG, economy, inventory, achievements, group tools, media, dan utility.

## Desain utama

```text
ACCOUNT
  ↓
PERMISSION / CONTEXT
  ↓
PROFILE · RANK · TITLE
  ↓
ECONOMY · INVENTORY · ITEMS
  ↓
QUEST · GAME · RPG
  ↓
ACHIEVEMENT · EVENT
  ↓
GROUP · MINI-OWNER · OWNER
```

### Rank dan Title

Rank adalah status/otoritas:

```text
USER
  ↓ inherit
MINI-OWNER
  ↓ inherit
OWNER
```

Title hanya kosmetik/pajangan. Satu akun memiliki banyak title yang dapat dibuka, tetapi hanya **satu title aktif**. Title tidak memberikan permission.

### Context permission

Group admin bukan rank global. Permission administrasi dapat berlaku pada grup tertentu, misalnya:

```text
group.kick
group.add
group.delete
group.open
group.close
```

dengan context `group=<jid>`.

## Menu UX

`/m` adalah dashboard kategori dan **tidak menampilkan seluruh command**.

Contoh shortcut:

```text
/m
/eco
/game
/rpg
/inv
/quest
/ach
/fish
/mine
/market
/group
/mo
```

Pencarian fitur:

```text
/m find dungeon
/m find pdf
/m find stock
```

Kategori memiliki pagination, sehingga chat tidak dibanjiri ribuan command.

## 500 feature systems

Project memiliki tepat **500 feature leaves**, dibagi menjadi 25 kategori × 20 feature.

Kategori utama:

```text
account
access
economy
games
rpg
progression
inventory
quest
achievement
event
fishing
mining
market
shop
group
moderation
mo
owner
media
image
videoaudio
converter
utility
search
funtext
```

Setiap feature memiliki 5 alias terdaftar, sehingga registry berisi 2.500 alias R2 ditambah command legacy v53.

## Fitur account

Guest hanya dapat menggunakan command publik seperti register/login/whoami/help/menu/ping.

Setelah login, user memiliki state canonical yang sama untuk:

```text
profile
identity
inventory
economy
quest
achievement
RPG
games
fishing
miner
stats
```

LID/PN disatukan oleh `SessionIdentityManager` sehingga register memakai LID dan pesan berikutnya memakai PN tetap menuju akun yang sama.

## Game & RPG

RPG sengaja sederhana:

```text
HP · ATK · DEF · CRIT · LUCK
weapon · armor · accessory
common → uncommon → rare → epic → legendary → mythic
```

Content:

```text
hunt · combat · dungeon · boss · raid
skills · skill tree · gacha
craft · forge · enchant · upgrade
pet · party · guild · pvp · loot
```

Skill tree memengaruhi stat combat, bukan sekadar tampilan.

### Native CPU engine

`rpg_engine.go` adalah optional native engine Go untuk formula damage CPU-heavy. Python memanggilnya memakai `ctypes` jika `librpg_engine.so`/`.dylib` tersedia; jika tidak, engine memiliki fallback Python.

Bangun Linux x86_64:

```bash
go build -buildmode=c-shared -o librpg_engine.so rpg_engine.go
```

## Media dan converter

Media downloader memakai `yt-dlp.YoutubeDL().extract_info(..., download=True)`.

Image processing memakai Pillow.

Video/audio memakai FFmpeg.

Converter memakai library lokal seperti PyMuPDF, python-docx, openpyxl, reportlab, qrcode, dan OpenCV untuk branch yang sesuai.

## Group tools

Admin grup dapat menggunakan:

```text
/kick <tag>
/add <nomor>
/del        # reply message
/open
/close
/everyone
/remind
/groupid
```

`/del` menggunakan `client.revoke_message(...)` Neonize bila tersedia. Neonize juga menyediakan `pin_message`, group participant management, dan group announcement/lock methods di client API. citehttps://github.com/krypton-byte/neonize/blob/master/docs/api-reference/client.md

## Achievement

Ada dua namespace:

```text
/ach universal
/ach slot
/ach dungeon
/ach fishing
/ach mining
```

Universal achievement berlaku di seluruh Cinnamon. Game achievement terikat pada game/domain tertentu. Achievement dapat membuka title kosmetik.

## Dependencies

Python:

```text
neonize
APScheduler
pytz
httpx
Pillow
qrcode
gTTS
yt-dlp
psutil
PyMuPDF
python-docx
openpyxl
reportlab
opencv-python-headless
```

FFmpeg adalah dependency sistem untuk media.

Tidak ada dependency AI/LLM.

## Runtime data

Data runtime tidak di-commit:

```text
data/
wa_session.db
media_inbox/
tiktok_downloads/
ytm_downloads/
```

## Verifikasi

Jalankan dari root project:

```bash
find . -name "*.py" -not -path "./.git/*" -not -path "*/__pycache__/*" | sort
find . -name "*.py" -not -path "./.git/*" | wc -l
python -m compileall -q .
python -c "import main; print('main OK')"
python -c "import handlers; handlers.load_all(); print(f'{handlers.count_commands()} commands')"
wc -l main.py
```

Acceptance verification yang tersimpan untuk build ini mencakup compile/import smoke checks dan fixture tests tertentu; live WhatsApp/network execution belum menjadi bukti untuk seluruh 500 feature.

## Catatan runtime

Live WhatsApp membutuhkan instalasi Neonize dan session database yang valid. Live network downloader/API membutuhkan koneksi internet. Sandbox build tidak dijadikan bukti live WhatsApp/network production.
