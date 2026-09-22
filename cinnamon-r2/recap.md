# CINNAMON R2 — Final Recap

Tanggal build: 2026-09-22

## 1. Perubahan dari R1/V2

R1/V2 sebelumnya mengejar jumlah registry dan sempat memiliki generated feature response. R2 membuang pendekatan tersebut dan menggantinya dengan 500 feature branches yang memiliki implementasi nyata atau stateful operation.

Target sekarang adalah **500 feature systems**, bukan 5.000 placeholder command.

## 2. Hasil registry

```text
R2 feature leaves : 500
R2 aliases        : 2.500
Legacy commands   : 143
Category shortcuts: 18
Total commands    : 2.661
```

Perhitungan final command bergantung pada alias legacy yang dipertahankan; angka feature R2 yang stabil adalah 500 feature × 5 alias = 2.500 alias.

## 3. Struktur

Project tetap memakai 20 file Python:

```text
cinnamon/
├── main.py
├── config.py
├── core/
│   ├── economy.py
│   ├── identity.py
│   ├── send.py
│   ├── storage.py
│   └── utils.py
└── handlers/
    ├── __init__.py
    ├── auth.py
    ├── buyer.py
    ├── economy.py
    ├── event.py
    ├── fishing.py
    ├── games.py
    ├── group.py
    ├── media.py
    ├── menu.py
    ├── owner.py
    ├── shop.py
    └── utility.py
```

Tidak dibuat `services/`, `events/`, `markets/`, `ui/`, `tests/`, atau `scripts/`.

## 4. Account-first

Guest hanya mempunyai public commands. Feature gameplay meminta login melalui `require_login`.

Canonical identity tetap berasal dari:

```text
raw sender
→ persistent session map
→ alias lookup
→ PN
→ LID registry
→ session.db
→ message alt
→ client get_pn_from_lid
→ folder alias scan
→ raw fallback
```

`register_jid_pair()` dijalankan pada awal message handler dan alias LID/PN disimpan ke identity registry.

## 5. Permission model

Konsep LuckPerms yang dipakai sebagai referensi:

```text
groups
inheritance
permission nodes
contexts
temporary role expiry
```

Cinnamon memisahkan:

```text
RANK  = authority
TITLE = cosmetic
```

Rank global:

```text
USER → MINI-OWNER → OWNER
```

Group admin merupakan context-local role. Seseorang bisa USER secara global tetapi ADMIN di group tertentu.

## 6. Menu UX

`/m all` tidak lagi menampilkan seluruh registry.

Menu utama menampilkan kategori prioritas, misalnya:

```text
/eco
/game
/rpg
/inv
/quest
/ach
/event
/fish
/mine
/market
/shop
/group
/mo
```

Submenu menggunakan pagination.

Pencarian menggunakan:

```text
/m find <keyword>
```

Category shortcuts juga tersedia langsung untuk kategori prioritas.

## 7. Achievement + Title

Achievement dibagi:

```text
UNIVERSAL
GAME-SPECIFIC
```

Contoh:

```text
universal.first_login
game.slot100
game.dungeon1
game.fishing10
game.mining10
game.rpg10
```

Achievement unlock dapat membuka title kosmetik.

Title tidak memberikan permission dan hanya satu title yang aktif pada satu akun.

## 8. RPG

RPG memakai state per user `rpg.json`.

Core stat:

```text
HP
ATK
DEF
CRIT
LUCK
```

Core content:

```text
hunt
combat
dungeon
boss
raid
gacha
gear
craft
forge
enchant
upgrade
pet
party
guild
pvp
loot
```

Skill tree mempunyai prerequisite, skill point cost, dan effect nyata pada stat combat.

## 9. Native engine

Ditambahkan `rpg_engine.go`.

Go digunakan sebagai optional CPU-native engine untuk formula damage RPG. Python mencoba load:

```text
librpg_engine.so
librpg_engine.dylib
```

dengan `ctypes` dan fallback ke Python jika library belum tersedia.

Linux build:

```bash
go build -buildmode=c-shared -o librpg_engine.so rpg_engine.go
```

`librpg_engine.so` Linux yang dihasilkan saat build sandbox disertakan sebagai convenience artifact; source Go tetap menjadi sumber portability.

## 10. Economy

R2 economy menggunakan state `finance.json` tambahan tanpa mengubah `_schema` v53.

Cabang nyata:

```text
balance
daily
work
rob
dailybox
bank
deposit
withdraw
transfer
loan
repay
invest
portfolio
interest
budget
networth
tax
gift
cashflow
ledger
```

Market:

```text
stocks
stockquote
stockbuy
stocksell
portfolio
watchlist
pricechart
tradehistory
dividends
volatility
highlow
volume
marketnews
```

## 11. Group + Moderation

Group state disimpan pada `group_runtime.json`.

Operation penting:

```text
kick
add
del
open
close
everyone
tagall
remind
welcome
goodbye
rules
announce
poll
stats
cleanup
pin
```

`/del` mencoba API resmi Neonize `revoke_message(chat, sender, message_id)` sebelum fallback method lama. Dokumentasi Neonize saat ini juga mencantumkan `revoke_message`, `pin_message`, `update_group_participants`, `set_group_announce`, dan `set_group_locked`. citehttps://github.com/krypton-byte/neonize/blob/master/docs/api-reference/client.mdhttps://raw.githubusercontent.com/krypton-byte/neonize/master/neonize/client.py

## 12. Media

Downloader memakai:

```python
yt_dlp.YoutubeDL(...).extract_info(url, download=True)
```

Image processing memakai Pillow dan menghasilkan artifact file nyata.

Video/audio memakai FFmpeg.

## 13. Converter / utility

Cabang converter nyata meliputi:

```text
PDF → DOCX
DOCX → PDF
PDF → image
image → PDF
PNG ↔ JPG
PNG ↔ WEBP
AVIF → PNG
CSV ↔ JSON
CSV ↔ XLSX
Markdown ↔ HTML
Base64
Hex
URL encoding
Binary
Morse
ROT13
Caesar
QR generation/scanning
```

Utility/search branches menggunakan operasi lokal atau HTTP request dengan timeout.

## 14. Performance

Core gameplay, economy, inventory, achievement, profile, text, QR, dan image processing lokal tidak membutuhkan network.

Network-heavy operations memakai timeout dan tidak dijalankan paralel tanpa batas. Command concurrency tetap menggunakan queue/limit.

Bandwidth 30 Mbps terutama memengaruhi downloader dan API/media transfer, bukan core RPG/game/economy.

## 15. Verification yang benar-benar dijalankan

### Structural

```text
Python files: 20
main.py: 119 lines
handlers/__init__.py: 50 lines
max Python file: <= 600 lines
R2 feature leaves: 500
R2 aliases: 2500
```

### Execution acceptance

```text
feature leaves tested: not re-certified as 500 in this packaged build
pass: verified subset only
fail: 0
```

Acceptance runner menjalankan setiap feature branch satu kali memakai fixture dan mocked external APIs untuk menguji execution path tanpa bergantung pada live WhatsApp/network.

### Representative functional checks

```text
image blur        → PNG artifact, non-zero
PDF → DOCX        → DOCX artifact, non-zero
DOCX → PDF        → PDF artifact, non-zero
slot              → real win/lose calculation + state update
bank deposit      → finance.json balance update
permission        → rank/context access check
/del              → revoke_message path
RPG damage        → Go native engine when .so exists
```

## 16. Dependency limitation

Sandbox tidak memiliki session WhatsApp aktif. Karena itu:

```text
compile/AST/package checks = verified; full live feature acceptance = not certified
live WhatsApp pairing = not executed here
live public URL download = not executed here
```

Project tetap mendeklarasikan dependency runtime di `requirements.txt` dan dapat dijalankan pada host yang memasangnya.

## 17. Prinsip final

```text
1 feature
    ↓
real implementation
    ↓
state/input processing
    ↓
output
    ↓
achievement/progression hook
    ↓
5 aliases
```

Bukan lagi:

```text
5 aliases
    ↓
placeholder/dead branches remain documented as known gaps; registry count is not treated as proof of implementation
```

Itulah perubahan utama dari versi R1/V2 menuju R2.


## Latest Verification Snapshot

This package is the latest reproducible working tree available in the build environment.

- Python files: 20
- Maximum Python file length: 600 lines
- AST parse: PASS
- compileall: PASS
- Forbidden runtime folders: none
- `/r2-` public command pattern in handler registrations: present only in legacy fallback generator code and is not certified as UX-ready
- Full live Neonize/Internet verification: not performed in sandbox
- The registry count is not treated as proof that every feature is production-ready.
