# CINNAMON R1F — MASTER BACKUP PROMPT
## Release 1 Finale — Final Product Blueprint, Architecture, Rules, Ideas, and Implementation Contract

> STATUS: FINAL PLANNING / MASTER CONTEXT
>
> Dokumen ini adalah backup konteks dan keputusan desain proyek Cinnamon yang telah dibahas.
> Gunakan dokumen ini sebagai sumber konteks utama ketika pekerjaan dilanjutkan di sesi baru.
>
> PENTING: Jangan kembali ke pola lama yang mengejar jumlah command/registry. Prioritas utama adalah fitur yang benar-benar berfungsi, account yang permanen, state yang konsisten, UX WhatsApp yang rapi, dan sistem yang saling terhubung.

---

# 0. IDENTITAS PROYEK

Nama: Cinnamon

Release: R1F = Release 1 Finale

Tujuan utama:
Membuat bot WhatsApp yang terasa seperti satu ekosistem permainan + utility + group assistant, bukan kumpulan command acak.

Target feature:
500 fitur nyata.

Bukan:
- 5.000 placeholder
- ribuan alias yang hanya menghasilkan string
- command yang terdaftar tetapi tidak mempunyai implementasi
- generic runner yang berpura-pura menjadi fitur

Alias hanya bagian dari UX.

Target akhir kira-kira:
- 500 feature leaves nyata
- setiap feature dapat mempunyai 3–8 alias natural
- command naming pendek dan manusiawi
- tidak memakai command internal seperti /r2-fishing-fishing

---

# 1. MASALAH YANG HARUS DIBERESKAN

Versi v53 memiliki beberapa masalah besar:

1. Register berhasil tetapi /whoami dapat mengatakan belum login.
2. Sender WhatsApp dapat datang sebagai LID atau PN.
3. Folder user dapat dibuat berdasarkan satu identity lalu lookup menggunakan identity lain.
4. State tersebar ke banyak file JSON.
5. Permission/rank bercampur dengan logic handler.
6. Banyak command hanya terdaftar tanpa implementation yang benar-benar sesuai nama.
7. /m all membuat UX berantakan.
8. Media/file operation dapat gagal jika directory belum tersedia.
9. Game state mudah bercampur antar-session.
10. Tidak ada feature readiness gate yang ketat.
11. Command registry dipakai sebagai pengganti bukti bahwa fitur bekerja.
12. Arsitektur lama terlalu bergantung pada Python single-file.

---

# 2. PRINSIP UTAMA R1F

Urutan prioritas:

ACCOUNT
↓
IDENTITY
↓
PERMISSION
↓
STATE
↓
FEATURE CONTRACT
↓
DOMAIN ENGINE
↓
PROGRESSION
↓
UI

Aturan emas:
Sebuah feature hanya boleh masuk production registry jika implementation + test + output/state contract sudah lulus.

Registry bukan bukti fitur bekerja.

---

# 3. STACK FINAL

## Bahasa

### TypeScript
Bahasa utama.

Digunakan untuk:
- WhatsApp orchestration
- command parser
- account
- identity
- permission
- profile
- rank
- title
- economy
- inventory
- quest
- achievement
- season
- reputation
- games orchestration
- RPG orchestration
- group
- Mini-Owner
- Owner
- media orchestration
- downloader orchestration
- utility
- DB access
- event bus
- queue
- caching

### C# / .NET 10
Digunakan sebagai native RPG/game calculation engine.

C# TIDAK:
- menyimpan database Cinnamon
- mengubah economy
- menulis inventory
- mengelola account
- mengelola WhatsApp

C# hanya:
request → calculation → result

Contoh:
- damage
- critical
- skill calculation
- loot roll
- dungeon calculation
- boss calculation
- tournament score
- deterministic combat

---

# 4. KENAPA TYPESCRIPT + C#

Tujuan:
- satu app layer yang rapi
- strongly typed
- lebih mudah membuat contract antar-domain
- C# cocok untuk engine CPU
- tidak menggunakan Python
- tidak menggunakan Go
- tidak menggunakan Rust

### IPC

Gunakan:
**gRPC + Protobuf**

Untuk komunikasi lokal:
**Unix Domain Socket (UDS)**

Model:

Node.js / TypeScript
    |
    | Protobuf
    | gRPC / UDS
    v
C# RPG Engine
    |
    v
BattleResult

C# tetap stateless terhadap database.

---

# 5. RUNTIME

Target runtime:
Node.js 24 LTS

Aplikasi:
NestJS standalone

NestJS dipakai sebagai application structure + dependency injection, bukan sebagai REST API besar.

Tidak perlu:
- GraphQL
- public REST API
- microservice network
- Kubernetes
- Redis
- Kafka
- RabbitMQ

untuk R1F single-host.

---

# 6. WHATSAPP LAYER

Gunakan:
Baileys

Namun jangan menyebarkan API Baileys ke seluruh project.

Buat adapter:

Baileys
  ↓
WhatsAppAdapter
  ↓
Application

Hanya adapter yang mengetahui:
- socket
- events
- sendMessage
- group metadata
- participants
- media download
- delete message
- group settings
- LID/PN information

Jika API Baileys berubah, perubahan terkonsentrasi di adapter.

Dependency version harus dipin melalui lockfile.

Tidak boleh memakai floating version untuk dependency kritis.

---

# 7. ACCOUNT PERMANEN — PRIORITAS ABSOLUT

Jangan gunakan:
- nomor WhatsApp sebagai primary account id
- JID sebagai primary account id
- LID sebagai primary account id
- username sebagai primary account id
- nama folder sebagai primary account id

Gunakan:
account_id = immutable UUID

Contoh model:

ACCOUNT
id = immutable UUID

IDENTITIES
├── whatsapp:pn:628xxxx → account_id
├── whatsapp:lid:12345 → account_id
└── whatsapp:old:... → account_id

Satu account dapat memiliki banyak identity.

---

# 8. ACCOUNT ≠ IDENTITY

Identity hanyalah alamat/channel yang bisa berubah.
Account adalah identitas Cinnamon yang permanen.

Model:

WhatsApp LID
     ↓
identity link
     ↓
Cinnamon Account UUID
     ↓
all user state

Kalau LID berubah ke PN:
LID → PN → SAME ACCOUNT

Jangan membuat account baru.

---

# 9. ACCOUNT RECOVERY

Account harus dapat dipertahankan ketika:
- device berubah
- PN berubah
- identity mapping berubah
- session WhatsApp berubah

Gunakan:
password + recovery codes

Password:
Argon2id

Recovery code:
- random
- one-time
- hashed di database
- dicabut setelah dipakai

Flow:
/register
↓
account created
↓
account_id
↓
credentials
↓
recovery codes

Recovery:
/recover
↓
verify account
↓
verify recovery code
↓
link new identity
↓
preserve all state

---

# 10. ACCOUNT TEST WAJIB

Harus lulus:

register
↓
Account A

logout
↓
login
↓
Account A

LID
↓
PN
↓
Account A

device baru
↓
login/recovery
↓
Account A

old inventory
old cash
old XP
old achievements
old title
old RPG
↓
STILL EXISTS

Jika account persistence gagal:
R1F belum selesai.

---

# 11. LID / PN

Gunakan official/real mapping informasi WhatsApp jika tersedia.

Buat:
WhatsAppIdentityResolver

Output akhirnya:
canonical account_id

Jangan lagi:
- heuristik suffix nomor untuk otomatis merge account
- startswith sebagai bukti ownership
- endswith sebagai bukti ownership
- merge otomatis ketika dua account berbeda bentrok

Jika:
LID → Account A
PN → Account B

maka:
IDENTITY_CONFLICT

Bukan auto-merge.

Recovery/authentication diperlukan.

---

# 12. USER / MINI-OWNER / OWNER

Rank adalah status global.

USER
  ↓ inherit
MINI_OWNER
  ↓ inherit
OWNER

## USER
Mendapat:
- economy
- games
- RPG
- inventory
- quests
- achievements
- titles
- season
- reputation
- fishing
- miner
- events
- media
- utilities
- social
- group features yang diizinkan context

## MINI-OWNER (MO)
USER + permission MO untuk group yang dikelola/disewa.

Contoh:
- group config
- security
- moderation
- welcome
- goodbye
- group stats
- automation
- billing/config untuk group yang menjadi tanggung jawab

## OWNER
Memiliki seluruh kemampuan USER + MO + global administration.

---

# 13. GROUP ADMIN ≠ RANK

Seseorang bisa:

Global rank:
USER

Group A:
ADMIN

Group B:
MEMBER

Group role menggunakan context:
group=<group_jid>

Contoh permission:
group.kick
group.add
group.delete
group.open
group.close
group.everyone
group.remind

Permission hanya berlaku di context group tempat user benar-benar admin.

---

# 14. PERMISSION ENGINE

Terinspirasi pola LuckPerms:
- permission nodes
- group inheritance
- contexts
- temporary permissions
- precedence/weight sebagai konsep

API utama:
can(accountId, permission, context)

Contoh:
can(accountId, "group.kick", { groupId })

Jangan menyebarkan if (isOwner), if (isAdmin), if (isMO) ke semua handler.

Semua harus melewati permission engine.

---

# 15. TITLE ≠ RANK

## Rank
Menentukan permission/authority.

USER
MINI_OWNER
OWNER

## Title
Kosmetik.

Contoh:
- 「Dungeon Master」
- 「Mythic Hunter」
- 「Abyss Angler」
- 「Cinnamon Veteran」
- 「Lucky」

Title:
- tidak menambah ATK
- tidak menambah DEF
- tidak menambah Luck
- tidak memberi permission
- hanya display

Satu account hanya satu title aktif.

---

# 16. PROFILE

Profile menampilkan rank, title, level, dan economy secara jelas.

Contoh:

╭──────── PROFILE ────────╮
│ 👤 Ardan               │
│ 👑 USER                │
│ 🏷️ 「Dungeon Master」    │
│ ⭐ Lv.24               │
│ 💰 45.200              │
│ 🪙 1.840               │
╰─────────────────────────╯

---

# 17. /m FINAL UX

/m BUKAN daftar 500 command.

User melihat dashboard kategori prioritas.

Contoh:

╭──────── CINNAMON ────────╮
│ 👤 Ardan                │
│ 👤 USER                 │
│ 🏷️ 「Mythic Hunter」      │
│ ⭐ Lv.24                │
│                         │
│ 💰 /eco                │
│ 🎮 /game               │
│ ⚔️ /rpg                │
│ 🎒 /item               │
│ 📜 /quest              │
│ 🌙 /season             │
│ 🏆 /ach                │
│ ⭐ /rep                │
│ 🎣 /fish               │
│ 🔨 /craft              │
│ 🎁 /event              │
│ 👥 /group              │
│                         │
│ /m <kategori>           │
╰──────────────────────────╯

Tidak menggunakan /m all.

Submenu:
/m eco
/m game
/m rpg
/m item
/m quest
/m season
/m ach
/m rep
/m fish
/m craft
/m event
/m group
/m media
/m tools

Search:
/m find dungeon
/m find fishing
/m find bank

---

# 18. USER / MO / OWNER MENU

## USER
Prioritas:
/eco
/game
/rpg
/item
/quest
/season
/ach
/rep
/fish
/craft
/event
/group
/media
/tools

## MO
Tetap mendapatkan menu USER.
Tambahan:
/mo groups
/mo config
/mo security
/mo stats
/mo billing

## OWNER
Tetap mendapatkan USER + MO.
Tambahan:
/owner
/users
/buyer
/ban
/token
/premium
/toggle
/backup
/system

---

# 19. GROUP ADMIN

Group admin bukan rank global.

Command dasar:
/kick <tag>
/add <nomor>
/del
/open
/close
/everyone
/groupid
/remind

/del:
reply message → /del → permission check → WhatsApp delete

/kick:
/kick @user → permission → participant remove

/add:
/add <nomor> → permission → participant add

/close:
/close → group setting announcement

/open:
/open → group setting not_announcement

---

# 20. ECONOMY

Economy menjadi backbone.

Domain:
wallet
bank
transactions
loan
investment
market
stock
auction
insurance
tax
gift
marriage

Semua transaksi melalui satu transaction layer.

Flow:
BEGIN
↓
validate
↓
mutate
↓
ledger
↓
achievement hook
↓
season hook
↓
COMMIT

Jika gagal:
ROLLBACK

Tidak boleh terjadi money deducted + item missing.

---

# 21. TRANSACTION LEDGER

Catat:
transaction_id
account_id
type
amount
balance_before
balance_after
source
reference
created_at

Mudah diaudit Owner.

---

# 22. INVENTORY

Inventory bukan gudang mati.

Item harus berguna:
weapon
armor
accessory
consumable
material
collectible
cosmetic

Action:
buy
sell
use
equip
unequip
craft
trade
give
collect

---

# 23. ITEM SYSTEM

Model:
item_id
name
type
rarity
stack_limit
sell_price
effects
metadata

Rarity:
COMMON
UNCOMMON
RARE
EPIC
LEGENDARY
MYTHIC

---

# 24. DAILY + QUEST

/daily tidak berdiri sendiri.

Flow:
/daily
↓
reward
↓
XP
↓
streak
↓
quest progress
↓
season progress
↓
achievement event

Satu aktivitas dapat memajukan banyak sistem.

---

# 25. ACHIEVEMENT

Dua namespace:
universal.*
game.*

Universal:
universal.first_login
universal.veteran
universal.collector
universal.social
universal.rich
universal.completionist

Game-specific:
game.slot.jackpot
game.dungeon.boss
game.fishing.mythic
game.sudoku.master

Command:
/ach
/ach universal
/ach slot
/ach dungeon
/ach fishing

---

# 26. ACHIEVEMENT EVENT ENGINE

Jangan scanning database setiap /ach.

Event:
game.win
daily.claimed
boss.defeated
fish.caught
item.crafted
quest.completed
group.helped

Event dapat diproses oleh:
- achievement
- season
- reputation
- statistics

---

# 27. TITLE REWARD

Achievement dapat unlock title.

Contoh:
Achievement: Jackpot
Reward: XP + cash + title 「High Roller」

/title
/title equip highroller

Title tetap kosmetik.

---

# 28. REPUTATION

Skala 0–1000.

Positif:
gift
party
help
trade success
event assist

Negatif:
spam
moderation violation

Tier:
Unknown
Friendly
Trusted
Honored
Respected
Legendary

Reputation bukan permission engine.

---

# 29. SEASON PASS

Fase awal: 30 hari.

Progress dari:
- daily
- weekly quest
- games
- fishing
- RPG
- event
- tournament
- collection
- reputation objective

Contoh:

╭──── CINNAMON SEASON 01 ────╮
│ 🌙 NIGHTFALL              │
│ Tier 17 / 30              │
│ ████████████░░            │
│                           │
│ ✓ Daily complete          │
│ ✓ Win 2 games             │
│ □ Catch 3 rare fish       │
│                           │
│ Next:                     │
│ 🪙 250 token              │
╰─────────────────────────────╯

Reward:
- cash
- token
- item
- cosmetic/title

---

# 30. RPG

RPG harus sederhana, cepat, tetapi punya progression.

Core stats:
HP
ATK
DEF
CRIT
LUCK

Classes:
Warrior
Rogue
Mage

Equipment:
weapon
armor
accessory

Rarity:
common
uncommon
rare
epic
legendary
mythic

---

# 31. RPG CONTENT

Urutan:
player
↓
stats
↓
equipment
↓
combat
↓
loot
↓
dungeon
↓
boss
↓
skill tree
↓
crafting
↓
pet
↓
party
↓
guild

---

# 32. SKILL TREE

Versi awal 12–20 node.

⚔️ COMBAT
├── Power I
├── Power II
├── Critical I
└── Critical II

🛡️ DEFENSE
├── Vitality I
├── Vitality II
└── Armor I

🍀 LUCK
├── Fortune I
├── Fortune II
└── Rare Hunter

Node:
skill_id
cost
prerequisite
effect
level

Skill effect harus benar-benar memengaruhi combat.

---

# 33. RPG DETERMINISTIC

Gunakan seed.

input + seed = deterministic result

Tujuan:
- testable
- reproducible
- debugging
- fair

C# engine menghitung.
TypeScript menyimpan.

---

# 34. C# RPG ENGINE

API kecil:
CalculateBattle
CalculateSkill
GenerateLoot
CalculateDungeon
ScoreTournament

Input:
player stats
enemy stats
equipment
skill
seed

Output:
damage
critical
player_hp
enemy_hp
loot
reward

Tidak ada database write dari C#.

---

# 35. GAME ENGINE

Setiap game memiliki:
GameDefinition
GameState
GameRules
GameResult

Session states:
IDLE
ACTIVE
WAITING_INPUT
RESOLVED
REWARD
CLOSED

Contoh games:
- slot
- rps
- hangman
- scramble
- memory
- trivia
- math quiz
- tic-tac-toe
- connect four
- reversi
- sudoku
- checkers
- chess-like simplified modes

Tidak menggunakan generic game response sebagai pengganti logic.

---

# 36. COLLECTION / MUSEUM

Inventory = apa yang dimiliki sekarang.
Collection = apa yang pernah ditemukan.

Contoh:

🐟 FISHING COLLECTION
4/6

✅ Old Shoe
✅ Small Fish
✅ Salmon
✅ Tuna
🔒 Legend Tuna
🔒 Golden Fish

Completion reward:
- XP
- cash
- season XP
- cosmetic/title

---

# 37. CRAFTING

Hanya 3 profession awal:
Chef
Alchemist
Blacksmith

Chef → food/buff
Alchemist → potion
Blacksmith → weapon/equipment

Profession:
level 1–10
recipe list
profession XP
mastery

---

# 38. BOUNTY

Bounty hanya untuk game/PvP yang mendukung.

/bounty @user 500

500 dikunci sebagai escrow.

Target kalah:
winner +500

Expire:
refund

Anti-abuse:
- no self-bounty
- minimum
- cooldown
- expiry
- transaction log
- anti farming

---

# 39. TOURNAMENT

Satu tournament engine.

Cycle contoh:
Week 1 → Tic-Tac-Toe
Week 2 → RPS
Week 3 → Fishing
Week 4 → Dungeon

Reward:
1st / 2nd / 3rd

Winner dapat:
- currency
- item
- season progress
- title/cosmetic

---

# 40. GROUP WORLD EVENT

Contoh:

╭──── WORLD EVENT ─────╮
│ 🌑 NIGHT RAID       │
│ Boss: Shadow Tyrant │
│ HP: ████████░░      │
│                     │
│ /raid hit           │
│ /raid skill         │
│ /raid status        │
╰─────────────────────╯

Beberapa anggota grup menyerang boss yang sama.

Reward:
- damage
- participation
- kill
- loot
- XP
- achievement
- season XP

---

# 41. MINI-OWNER

MO adalah contract per group.

Model:
account_id
group_id
started_at
expires_at
plan
permissions

Jika expired:
MO permission revoked

Rank user tidak berubah.

---

# 42. MAIL RINGAN

/mail @user
/mailbox

Bisa:
- text
- token
- item

Tidak perlu COD/tracking/scheduled mail untuk fase awal.

---

# 43. SYSTEM YANG DITUNDA

Jangan memasukkan kompleksitas berikut ke core R1F:
- full Mount system
- full Guild War / Territory
- faction diplomacy kompleks
- full Mailbox GUI/COD
- MMO-scale race/class ecosystem
- 20 profession
- terlalu banyak stat RPG

Guild sederhana boleh:
guild
members
level
bank
weekly score
quest

Guild War menyusul.

---

# 44. MEDIA PIPELINE

Semua file processing:

input
↓
validate
↓
temporary workspace
↓
process
↓
verify output
↓
send
↓
cleanup

Gunakan ensureDir/ensure_media_dirs agar directory runtime selalu tersedia.

---

# 45. IMAGE

Gunakan Sharp.

Contoh:
- blur
- sharpen
- grayscale
- contrast
- brightness
- sepia
- negate/invert
- rotate
- resize
- crop
- watermark
- posterize
- edge
- vignette
- noise
- lainnya yang nyata dan teruji

---

# 46. VIDEO / AUDIO

Gunakan:
FFmpeg + ffprobe

FFmpeg:
- trim
- merge
- convert
- extract
- audio
- sticker
- gif
- compression

ffprobe:
- validate output
- detect duration
- detect codec
- detect format

---

# 47. DOWNLOADER

Downloader adalah network-heavy feature.

Gunakan adapter/provider yang memang ada untuk platform.

Contoh:
- YouTube
- TikTok
- Instagram
- Reddit
- Vimeo
- Dailymotion
- Twitch
- dll.

Provider hanya masuk registry jika:
adapter exists
+ input test passes
+ output exists
+ output verifies

Tidak ada fake downloader.

---

# 48. LOCAL-FIRST NETWORK DESIGN

Local:
- economy
- RPG
- games
- inventory
- achievements
- quests
- titles
- reputation
- season
- fishing
- miner
- image
- text
- QR
- converters

Network:
- downloader
- search
- weather
- news
- wiki
- translate
- stock
- crypto

Network feature:
- timeout
- limited retry
- cache
- connection reuse
- size limits
- rate limit

---

# 49. PERFORMANCE

Koneksi 30 Mbps bukan satu-satunya ukuran performa.

Yang dikendalikan:
- CPU
- RAM
- disk I/O
- concurrency
- network request count

Fast path:
balance
daily
game
rpg
inventory
profile
achievement
permission

Heavy path:
download
image
video
audio
PDF

Heavy path masuk bounded worker queue.

Satu user tidak boleh menjalankan banyak pekerjaan berat sekaligus.

---

# 50. EVENT LOOP

Message handling:

receive
↓
deduplicate
↓
resolve identity
↓
parse
↓
permission
↓
dispatch

Jangan melakukan FFmpeg/download lama di event handler.

---

# 51. IDEMPOTENCY

Message/operation ID wajib dipakai untuk transaksi yang tidak boleh double-apply.

Contoh /daily:
message_id = ABC

Jika event datang dua kali:
ABC
ABC

reward hanya diberikan satu kali.

Untuk economy, message_id/operation ID masuk idempotency table.

---

# 52. DATABASE AUDIT TRAIL

transactions mencatat:
transaction_id
account_id
type
amount
balance_before
balance_after
source
reference
created_at

Owner dapat mengaudit perubahan ekonomi.

---

# 53. DATABASE

Primary R1F state:
SQLite

Driver:
better-sqlite3

Schema layer:
Drizzle

Enable:
WAL
foreign_keys=ON
busy_timeout
synchronous durability-oriented

Transactions harus pendek.

Tidak ada direct SQL scattered di handler.

---

# 54. BACKUP

Karena account harus permanen:

data/
├── cinnamon.db
├── backups/
│   ├── daily/
│   └── weekly/
└── wa-auth/

Backup harus aman.

Jangan copy database aktif secara sembarangan.

Gunakan mekanisme SQLite backup/checkpoint yang aman.

---

# 55. BAILEYS AUTH VS USER ACCOUNT

Pisahkan:

## Bot WhatsApp auth
Untuk:
- QR
- Signal keys
- WhatsApp connection

## Cinnamon user session
Untuk:
- login
- permission
- account access
- recovery

Jangan campurkan.

---

# 56. FEATURE CONTRACT

Contoh:

defineFeature({
  id: "image.blur",
  aliases: ["blur", "blurimg", "softblur"],
  kind: "artifact",
  requiresLogin: true,
  permission: "user.media.image",
  handler: handleBlur,
  test: "image.blur"
})

Jenis:
READONLY
ACTION
ARTIFACT
ADMIN

---

# 57. FEATURE READINESS

Status:
DRAFT
IMPLEMENTED
TESTED
READY
DEPRECATED

Feature gagal test:
jangan register.

---

# 58. FEATURE CLASSIFICATION

READONLY:
/profile
/balance
/rpgprofile
/ach
/rank

ACTION:
/daily
/work
/cast
/pet
/buy
/equip
/attack

ARTIFACT:
/blur
/png2jpg
/pdf2img

ADMIN:
/kick
/add
/del
/close
/open

---

# 59. TESTING

## Unit
- damage
- crit
- skill prerequisite
- economy
- inventory
- achievement
- permission

## Integration
- register
- login
- LID/PN
- recovery
- daily
- buy
- craft
- game
- RPG
- achievement
- season
- group permissions

## Artifact
- output exists
- output size > 0
- mime/format valid
- file readable
- cleanup

## Regression
Legacy v53 data:
→ migrated
→ same account
→ same cash
→ same inventory
→ same progression

---

# 60. ACCOUNT ACCEPTANCE TEST

Wajib:
register
login
logout
LID ↔ PN
recovery
multi-device
identity conflict

Acceptance example:
LID → Account A
PN → Account A
Recovery → Account A
inventory/economy/RPG/achievement/title unchanged

---

# 61. ECONOMY ACCEPTANCE TEST

Contoh:
cash = 1000

/buy potion 100

cash = 900
inventory += potion
ledger += transaction
achievement updated if needed
season updated if needed

Jika item gagal:
cash harus tetap 1000.

---

# 62. RPG ACCEPTANCE TEST

player ATK = 20
enemy DEF = 10
seed = 123
skill = power_1

Hasil harus reproducible.

Skill effect harus terlihat pada calculation.

---

# 63. PERMISSION ACCEPTANCE TEST

USER
→ group.kick = DENY

GROUP ADMIN
→ group.kick = ALLOW

MO expired
→ mo.group.manage = DENY

OWNER
→ owner.system = ALLOW

---

# 64. MEDIA ACCEPTANCE TEST

input image
↓
blur
↓
file exists
↓
file readable
↓
valid PNG
↓
WhatsApp send

Converter:
input
↓
convert
↓
output exists
↓
output valid

---

# 65. GAME ANTI-ERROR

Setiap game punya state machine:

IDLE
↓
ACTIVE
↓
WAITING_INPUT
↓
RESOLVED
↓
REWARD
↓
CLOSED

Session key minimal:
account_id
game_id
session_id

Group games juga mencantumkan group_id.

---

# 66. 500 FEATURE ALLOCATION

Account / Identity 25
Permission / Roles 20
Profile / Rank / Title 15
Economy 30
Inventory / Items 18
Shop / Market 14
Daily / Quest 22
Season 16
Achievement 18
Reputation 10
Games 50
RPG 65
Skills / Equipment / Pets 22
Fishing / Mining 18
Crafting / Professions 15
Collection 10
Tournament 8
Bounty 6
Events 8
Group Admin 18
Security / Moderation 12
Mini-Owner 10
Owner 7
Mail 4
Media / Sticker 10
Downloader 8
Image 10
Video / Audio 8
Document / Converter 6
Utility / Search / Info 16

TOTAL = 500

---

# 67. 500 FEATURE PHILOSOPHY

500 feature = 500 implementation/contract yang benar.

Bukan 500 aliases.

Contoh:
/blur
/blurimg
/softblur

= 1 feature: image.blur

Alias adalah UX.

---

# 68. COMMAND NAMING RULES

Command harus:
- pendek
- mudah diingat
- natural
- tidak mencerminkan struktur internal
- tidak menggunakan prefix versi/framework

Contoh baik:
/eco
/game
/rpg
/skill
/pet
/cast
/dungeon
/boss
/ach
/title
/season
/rep
/item
/fish
/mine
/craft

Contoh buruk:
/r2-fishing-fishing
/r2-feature-runner
/r2-rpg-combat

---

# 69. ERROR MESSAGE RULE

Development:
UnknownFeatureError

Production:
⚠️ Command belum tersedia.

Tetapi command belum tersedia tidak boleh didaftarkan ke production registry.

---

# 70. NO PLACEHOLDER RULE

Jangan pernah memakai:
- "feature X will process ..."
- "coming soon"
- "requires concrete argument"

untuk menyamarkan implementation yang belum ada.

Jika belum siap:
jangan register.

Jika feature memang membutuhkan input:
jelaskan input yang benar.

---

# 71. OUTPUT CONTRACT

Setiap feature harus mempunyai salah satu:
- text result
- state mutation
- artifact
- WhatsApp admin action

Jika feature action tidak menghasilkan salah satu di atas:
audit harus dilakukan.

---

# 72. COMMAND DISCOVERY

/m hanya kategori.

Pencarian:
/m find <keyword>

Pagination:
/m eco 2
/m game 3

Tidak ada /m all.

---

# 73. SECURITY

Password:
Argon2id.

Recovery:
hashed one-time codes.

Auth state:
jangan commit.

.env:
jangan commit.

wa-auth/:
jangan commit.

Database:
backup.

Owner action:
audit log.

Economy:
ledger + transaction.

Permission:
central evaluator.

---

# 74. OBSERVABILITY

Logging:
Pino

Log fields:
timestamp
level
account_id
command
group_id
duration
result
error_code

Jangan log:
- password
- recovery plaintext
- Signal private key
- sensitive auth secrets

---

# 75. PERFORMANCE METRICS

Track:
command latency
DB transaction latency
queue depth
media job duration
network timeout rate
RPG engine latency
error rate

Target:
- fast commands sekitar <100–200ms local typical
- heavy jobs asynchronous
- network bounded
- no event loop blocking

---

# 76. FINAL QUALITY GATE

Project hanya boleh disebut:
R1F READY

jika:
✅ npm ci
✅ TypeScript strict compile
✅ lint clean
✅ Vitest unit pass
✅ integration pass
✅ dotnet build
✅ dotnet test
✅ protobuf generation pass
✅ DB migration pass
✅ foreign_key_check pass
✅ no unregistered implementation
✅ no registered untested feature
✅ no duplicate alias
✅ account persistence pass
✅ LID/PN pass
✅ recovery pass
✅ permission matrix pass
✅ economy rollback pass
✅ RPG deterministic pass
✅ artifact test pass
✅ group admin pass
✅ MO expiry pass
✅ backup/restore pass
✅ v53 migration pass
✅ /m UX pass
✅ feature manifest pass

---

# 77. PRODUCTION TEST

Sebelum release final gunakan staging WhatsApp account + staging group.

Test real:
QR login
/register
/login
/whoami
/recover
/del
/kick
/add
/close
/open
/m
/eco
/game
/rpg
/ach
/season

Media:
/blur
converter
downloader

---

# 78. MIGRATION V53

Source v53:
- JSON user profiles
- economy
- inventory
- legacy identity

Migration:

v53 JSON
↓
legacy reader
↓
normalizer
↓
account creation
↓
identity link
↓
profile import
↓
economy import
↓
inventory import
↓
progression import
↓
verify
↓
mark migrated

Jangan mengubah schema lama secara sembarangan.
Jangan menghapus source legacy sebelum migration verified.

---

# 79. PERMANENCE MODEL

Definisi “permanent account” R1F:

Immutable Cinnamon Account UUID
+
Verified identity links
+
Recovery proof
+
Transactional database
+
Regular backups

Ini adalah permanence realistis secara teknis. Sistem tidak mengklaim dapat membuktikan identitas biologis manusia.

---

# 80. FINAL PROJECT ARCHITECTURE

cinnamon-r1f/
│
├── apps/
│   ├── bot/
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── app.module.ts
│   │   │   ├── config.ts
│   │   │   ├── whatsapp.ts
│   │   │   ├── commands.ts
│   │   │   ├── feature-registry.ts
│   │   │   ├── account.ts
│   │   │   ├── identity.ts
│   │   │   ├── permission.ts
│   │   │   ├── profile.ts
│   │   │   ├── economy.ts
│   │   │   ├── inventory.ts
│   │   │   ├── progression.ts
│   │   │   ├── quest.ts
│   │   │   ├── achievement.ts
│   │   │   ├── season.ts
│   │   │   ├── reputation.ts
│   │   │   ├── game.ts
│   │   │   ├── rpg.ts
│   │   │   ├── group.ts
│   │   │   ├── mo.ts
│   │   │   ├── owner.ts
│   │   │   ├── media.ts
│   │   │   ├── utility.ts
│   │   │   └── ui.ts
│   │   └── package.json
│   │
│   └── engine/
│       ├── Program.cs
│       ├── CombatEngine.cs
│       ├── SkillEngine.cs
│       ├── DungeonEngine.cs
│       ├── TournamentEngine.cs
│       └── Cinnamon.Engine.csproj
│
├── db/
│   ├── schema.ts
│   ├── connection.ts
│   └── migrations/
│
├── proto/
│   └── cinnamon.proto
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── data/
│
├── package.json
├── package-lock.json
├── tsconfig.json
├── nest-cli.json
├── drizzle.config.ts
├── vitest.config.ts
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── MIGRATION.md
├── SECURITY.md
└── .gitignore

---

# 81. IMPLEMENTATION ORDER

01 Account
02 Identity
03 Recovery
04 Permission
05 Profile
06 Rank
07 Title
08 Database transaction layer
09 Economy
10 Inventory
11 Items
12 Achievement
13 Quest
14 Season
15 Reputation
16 Game engine
17 RPG engine
18 Skill tree
19 Equipment
20 Pet
21 Fishing
22 Miner
23 Crafting
24 Collection
25 Tournament
26 Bounty
27 Events
28 Group admin
29 Mini-Owner
30 Owner
31 Media
32 Downloader
33 Utility
34 Performance
35 Migration
36 Full QA

---

# 82. FINAL MINDSET

Jangan berpikir:
“Bagaimana membuat 5.000 command?”

Pikirkan:
“Bagaimana membuat satu sistem Cinnamon yang membuat command berikutnya menjadi natural?”

Account membuat Economy mungkin.
Economy membuat Inventory berguna.
Inventory membuat RPG berguna.
RPG membuat Achievement berguna.
Achievement membuat Title berguna.
Season menghubungkan aktivitas.
Reputation menghubungkan perilaku sosial.
Group Event menghubungkan semua user.
MO menghubungkan bot dengan penyewa grup.
Owner mengelola sistem.
Media/Utility menjadi tool layer.

500 fitur kemudian adalah hasil alami dari ecosystem tersebut.

---

# 83. FINAL INSTRUCTION TO FUTURE CODER / AI

Mulai dari project state yang tersedia.

Baca:
- README
- ARCHITECTURE
- MIGRATION
- SECURITY
- schema
- feature manifest

sebelum mengubah code.

Audit existing implementation sebelum menambah feature.

Jika sebuah feature belum benar-benar implement:
jangan mendaftarkannya sebagai READY.

Jika test gagal:
fix implementation, bukan test.

Jika architecture issue ditemukan:
perbaiki fondasi, kemudian lanjutkan feature.

Gunakan implementation nyata.

Jangan mengganti implementation dengan return string.

Jangan menganggap alias = feature.

Jangan menganggap registry = working feature.

Jangan mengklaim release selesai tanpa acceptance test.

**Account permanence adalah prioritas tertinggi.**

**Feature quality lebih penting daripada jumlah command.**

**Cinnamon R1F adalah satu ecosystem, bukan kumpulan script.**
