# CINNAMON R1F × R2 — MERGED PROJECT PLANNING

## Executive Summary

Dokumen ini adalah hasil analisis dan planning untuk menggabungkan:
- **Cinnamon R1F**: Arsitektur TypeScript + C#, account permanence, 500 fitur nyata
- **Cinnamon R2**: Implementasi Python/Neonize dengan 500 feature systems terstruktur
- **Best Features**: Fitur terbaik dari bots WhatsApp populer (games-wabot, Hitori-MD, dll)

**Target**: Membangun ekosistem bot WhatsApp yang cohesive, scalable, dan benar-benar berfungsi.

---

# 1. ANALISIS FITUR POPULER DARI COMMUNITY

Berdasarkan riset repository WhatsApp bot populer (238+ stars untuk games-wabot, 176+ stars untuk zimbot, dll):

## 1.1 RPG & Adventure Systems (HIGH PRIORITY)

### Dari games-wabot:
```javascript
// Adventure System
- /adventure, /petualang, /berpetualang, /mulung, /work
  → Cooldown 5 menit, health requirement, random rewards
  → Drops: exp, money, potion, diamond, crates, sampah
  → Location-based: Jepang, Korea, Bali, Amerika, Mars, dll

// Hunt System  
- /hunt
  → Monster scaling by area (1-13)
  → Monster types: Goblin, Slime, Wolf, Dragon, dll
  → Combat calculation: sword + armor - monster_def
  → Death penalty: level down, health reset

// Fishing System
- /mancing
  → Cooldown ~8 menit
  → 12 jenis ikan/sea creature:
    🐋 🐳 🦈 🐙 🐡 🐬 🐟 🐠 🦞 🦀 🦑 🦐
  → Random quantity per type

// Inventory & Shop
- /inv, /shop
  → Equipment: sword, armor
  → Consumables: potion
  → Materials: diamond, sampah
  → Crates: common, uncommon, mythic, legendary
```

### Lessons Learned:
✅ Simple cooldown system works well
✅ Health/energy mechanic adds strategy
✅ Random loot creates excitement
✅ Visual emoji representation is engaging
❌ Health system too punishing (death = level loss)
❌ No deterministic combat (pure RNG)

---

## 1.2 Game Systems (HIGH PRIORITY)

### Popular Games Identified:

```javascript
Slots Machine:
- /slots [amount]
  → 3x3 grid dengan fruits emoji
  → Jackpot conditions: 9 match, middle row match
  → Simple but addictive

Tic-Tac-Toe:
- /ttt, /tictactoe
  → Player vs Player
  → Button-based interaction
  → Turn tracking

Quiz Games:
- /tebakgambar, /tebaklagu
- /siapakahaku, /caklontong
- /family100
  → Answer-based with hints
  → Timer system
  → Point rewards

Math Challenge:
- /math [difficulty]
  → Quick calculation
  → Score tracking

Casino Games:
- /judi, /rps (rock-paper-scissors)
- /dice, /coinflip
```

### Recommendation for R1F×R2:
✅ Keep simple games (slots, rps, dice)
✅ Add skill-based games (trivia, math)
✅ Implement proper state machine
✅ Use session-based gameplay
❌ Avoid pure gambling without limits

---

## 1.3 Economy Systems (MEDIUM-HIGH PRIORITY)

### From Analyzed Bots:
```javascript
Daily Rewards:
- /daily, /claim
  → Base money + random bonus
  → Streak system (weekly/monthly)

Work System:
- /work, /nguli
  → Cooldown-based
  → Random wage
  → Job titles unlockable

Transaction System:
- /transfer, /pay @user amount
- /buy, /sell item
- /bank deposit/withdraw
```

### Missing in Community Bots:
❌ No transaction ledger/audit trail
❌ No rollback mechanism
❌ No inflation control
❌ No meaningful item sinks

### R1F×R2 Improvement:
✅ Transaction ledger with audit
✅ Rollback on failure
✅ Item crafting = money sink
✅ Repair/maintenance costs
✅ Tax on high-value trades

---

## 1.4 Social & Group Features (MEDIUM PRIORITY)

### Most Used Group Commands:
```javascript
Moderation:
- /kick, /add, /promote, /demote
- /del (delete message)
- /close, /open (group settings)
- /antilink, /antispam, /antitoxic

Engagement:
- /profile, /leaderboard
- /afk (away from keyboard)
- /tagme, /everyone
- /vote (poll system)

Fun:
- /hornycard, /simpcard
- /how [text]
- /zodiac sign
- /couple tagging
```

### Key Insight:
Group features drive retention BUT require proper permission system.

---

## 1.5 Media & Downloader (MEDIUM PRIORITY)

### Top Download Requests:
```javascript
Video:
- YouTube (audio + video)
- TikTok (with/without watermark)
- Instagram Reels/Stories
- Facebook Video

Audio:
- Spotify track download
- SoundCloud
- YouTube Music

Image:
- Pinterest
- Google Images
- Anime wallpapers

Tools:
- Sticker maker
- Text-to-image
- Photo effects (blur, sharpen, etc.)
```

### Technical Requirements:
✅ yt-dlp integration
✅ FFmpeg for processing
✅ Sharp for image manipulation
✅ Rate limiting to prevent abuse
✅ Cache results

---

## 1.6 Utility & Tools (LOW-MEDIUM PRIORITY)

### Useful Utilities:
```javascript
Converters:
- PDF ↔ Images
- Word ↔ PDF
- Excel operations
- Base64 encode/decode

Search:
- Google search
- Wikipedia
- GitHub repo search
- Lyrics finder

Info:
- Weather
- Currency exchange
- Crypto prices
- Server status
```

---

# 2. R1F × R2 MERGED ARCHITECTURE

## 2.1 Technology Stack Decision

| Component | R1F Spec | R2 Implementation | Final Decision |
|-----------|----------|-------------------|----------------|
| Main Language | TypeScript | Python | **TypeScript** |
| WhatsApp Lib | Baileys | Neonize | **Baileys** (better support) |
| RPG Engine | C# + gRPC | Go + ctypes | **TypeScript native** (simpler) |
| Database | SQLite + Drizzle | JSON files | **SQLite + Drizzle** |
| Build Tool | NestJS | Plain Python | **NestJS** (structure) |
| Testing | Vitest | Manual | **Vitest + Integration** |

### Rationale:
- TypeScript memberikan type safety untuk complex systems
- Baileys memiliki community lebih besar dan dokumentasi lengkap
- SQLite cukup untuk single-instance deployment
- NestJS memberikan structure tanpa over-engineering

---

## 2.2 Project Structure Merged

```
cinnamon-r1f-r2/
│
├── apps/
│   ├── bot/                      # Main application
│   │   ├── src/
│   │   │   ├── main.ts           # Entry point
│   │   │   ├── app.module.ts     # NestJS module
│   │   │   │
│   │   │   ├── whatsapp/         # WhatsApp layer
│   │   │   │   ├── adapter.ts    # Baileys wrapper
│   │   │   │   ├── events.ts     # Message handlers
│   │   │   │   └── media.ts      # Media download/send
│   │   │   │
│   │   │   ├── core/             # Core systems
│   │   │   │   ├── account.ts    # Account management
│   │   │   │   ├── identity.ts   # LID/PN resolution
│   │   │   │   ├── permission.ts # Permission engine
│   │   │   │   ├── profile.ts    # Profile + Rank + Title
│   │   │   │   └── economy.ts    # Wallet + Bank + Ledger
│   │   │   │
│   │   │   ├── domains/          # Feature domains
│   │   │   │   ├── inventory/
│   │   │   │   │   ├── items.ts
│   │   │   │   │   ├── shop.ts
│   │   │   │   │   └── crafting.ts
│   │   │   │   │
│   │   │   │   ├── rpg/
│   │   │   │   │   ├── stats.ts
│   │   │   │   │   ├── combat.ts
│   │   │   │   │   ├── dungeon.ts
│   │   │   │   │   ├── boss.ts
│   │   │   │   │   └── skills.ts
│   │   │   │   │
│   │   │   │   ├── games/
│   │   │   │   │   ├── slots.ts
│   │   │   │   │   ├── rps.ts
│   │   │   │   │   ├── tictactoe.ts
│   │   │   │   │   ├── trivia.ts
│   │   │   │   │   └── tournament.ts
│   │   │   │   │
│   │   │   │   ├── fishing/
│   │   │   │   │   ├── fishing.ts
│   │   │   │   │   ├── collection.ts
│   │   │   │   │   └── aquarium.ts
│   │   │   │   │
│   │   │   │   ├── mining/
│   │   │   │   │   ├── mining.ts
│   │   │   │   │   └── smelting.ts
│   │   │   │   │
│   │   │   │   ├── progression/
│   │   │   │   │   ├── daily.ts
│   │   │   │   │   ├── quest.ts
│   │   │   │   │   ├── achievement.ts
│   │   │   │   │   ├── season.ts
│   │   │   │   │   └── reputation.ts
│   │   │   │   │
│   │   │   │   ├── group/
│   │   │   │   │   ├── admin.ts
│   │   │   │   │   ├── moderation.ts
│   │   │   │   │   ├── mo.ts (Mini-Owner)
│   │   │   │   │   └── events.ts
│   │   │   │   │
│   │   │   │   ├── media/
│   │   │   │   │   ├── downloader.ts
│   │   │   │   │   ├── image.ts
│   │   │   │   │   ├── video.ts
│   │   │   │   │   └── sticker.ts
│   │   │   │   │
│   │   │   │   └── utility/
│   │   │   │       ├── converter.ts
│   │   │   │       ├── search.ts
│   │   │   │       └── tools.ts
│   │   │   │
│   │   │   ├── ui/               # UX components
│   │   │   │   ├── menu.ts       # /m dashboard
│   │   │   │   ├── profile-card.ts
│   │   │   │   └── formatters.ts
│   │   │   │
│   │   │   └── shared/           # Shared utilities
│   │   │       ├── database.ts
│   │   │       ├── event-bus.ts
│   │   │       ├── queue.ts
│   │   │       └── logger.ts
│   │   │
│   │   └── package.json
│   │
│   └── engine/                   # Optional native engine
│       ├── Program.cs            # C# RPG calculator
│       ├── CombatEngine.cs
│       └── Cinnamon.Engine.csproj
│
├── db/
│   ├── schema.ts                 # Drizzle schema
│   ├── connection.ts             # SQLite setup
│   └── migrations/
│
├── proto/                        # gRPC contracts (if using C#)
│   └── cinnamon.proto
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── data/                         # Runtime data (gitignored)
│   ├── cinnamon.db
│   ├── backups/
│   └── wa-auth/
│
├── package.json
├── tsconfig.json
├── nest-cli.json
├── drizzle.config.ts
├── vitest.config.ts
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── FEATURE_MANIFEST.md
└── MIGRATION.md
```

---

## 2.3 Database Schema Design

### Core Tables:

```sql
-- Account (permanent identity)
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,              -- UUID immutable
  created_at INTEGER NOT NULL,
  password_hash TEXT,               -- Argon2id
  recovery_codes_hash TEXT[],
  last_login_at INTEGER
);

-- Identity links (LID, PN, etc.)
CREATE TABLE identities (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  type TEXT NOT NULL,               -- 'whatsapp:lid', 'whatsapp:pn'
  identifier TEXT NOT NULL,         -- Actual LID/PN value
  verified BOOLEAN DEFAULT false,
  created_at INTEGER NOT NULL,
  UNIQUE(type, identifier)
);

-- Profiles
CREATE TABLE profiles (
  account_id TEXT PRIMARY KEY REFERENCES accounts(id),
  display_name TEXT,
  rank TEXT DEFAULT 'USER',         -- USER, MINI_OWNER, OWNER
  title_active TEXT,                -- Currently equipped title
  level INTEGER DEFAULT 1,
  xp INTEGER DEFAULT 0,
  healt INTEGER DEFAULT 100,        -- RPG health
  energy INTEGER DEFAULT 100,       -- Daily energy
  created_at INTEGER NOT NULL
);

-- Economy
CREATE TABLE wallets (
  account_id TEXT PRIMARY KEY REFERENCES accounts(id),
  balance INTEGER DEFAULT 0,
  bank_balance INTEGER DEFAULT 0,
  last_daily_at INTEGER,
  streak_days INTEGER DEFAULT 0
);

-- Transaction Ledger
CREATE TABLE transactions (
  id TEXT PRIMARY KEY,              -- UUID
  account_id TEXT NOT NULL REFERENCES accounts(id),
  type TEXT NOT NULL,               -- 'earn', 'spend', 'transfer', 'refund'
  amount INTEGER NOT NULL,
  balance_before INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  source TEXT NOT NULL,             -- 'daily', 'work', 'shop', etc.
  reference TEXT,                   -- Related entity ID
  created_at INTEGER NOT NULL
);

-- Inventory
CREATE TABLE inventory (
  account_id TEXT NOT NULL REFERENCES accounts(id),
  item_id TEXT NOT NULL,
  quantity INTEGER DEFAULT 1,
  metadata TEXT,                    -- JSON for special properties
  acquired_at INTEGER NOT NULL,
  PRIMARY KEY (account_id, item_id)
);

-- Items Definition
CREATE TABLE items (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,               -- 'weapon', 'armor', 'consumable', etc.
  rarity TEXT NOT NULL,             -- COMMON to MYTHIC
  base_price INTEGER DEFAULT 0,
  sell_price INTEGER DEFAULT 0,
  effects TEXT,                     -- JSON stat bonuses
  stack_limit INTEGER DEFAULT 999
);

-- RPG Stats
CREATE TABLE rpg_stats (
  account_id TEXT PRIMARY KEY REFERENCES accounts(id),
  class TEXT DEFAULT 'warrior',     -- warrior, rogue, mage
  attack INTEGER DEFAULT 10,
  defense INTEGER DEFAULT 5,
  crit_chance REAL DEFAULT 0.05,
  luck INTEGER DEFAULT 10,
  skill_points INTEGER DEFAULT 0,
  unlocked_skills TEXT[]            -- Array of skill IDs
);

-- Achievements
CREATE TABLE achievements (
  account_id TEXT NOT NULL REFERENCES accounts(id),
  achievement_id TEXT NOT NULL,
  completed_at INTEGER,
  progress INTEGER DEFAULT 0,
  target INTEGER NOT NULL,
  PRIMARY KEY (account_id, achievement_id)
);

-- Season Progress
CREATE TABLE seasons (
  account_id TEXT NOT NULL REFERENCES accounts(id),
  season_id TEXT NOT NULL,
  tier INTEGER DEFAULT 1,
  points INTEGER DEFAULT 0,
  claimed_rewards TEXT[],           -- Array of reward IDs
  PRIMARY KEY (account_id, season_id)
);

-- Group Context
CREATE TABLE group_members (
  group_id TEXT NOT NULL,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  role TEXT DEFAULT 'member',       -- member, admin, mo, owner
  permissions TEXT[],               -- Custom permission nodes
  joined_at INTEGER NOT NULL,
  PRIMARY KEY (group_id, account_id)
);

-- Mini-Owner Contracts
CREATE TABLE mo_contracts (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  group_id TEXT NOT NULL,
  plan TEXT NOT NULL,               -- 'basic', 'premium'
  started_at INTEGER NOT NULL,
  expires_at INTEGER,
  permissions TEXT[],
  active BOOLEAN DEFAULT true
);
```

---

# 3. FEATURE ALLOCATION — 500 FEATURES

Berdasarkan kombinasi R1F blueprint, R2 implementation, dan best practices dari community:

## 3.1 Account & Identity (25 features)

```
account.register          → Register new account
account.login             → Login with credentials
account.logout            → Logout current session
account.whoami            → Check current account
account.recover           → Recovery with codes
account.link-lid          → Link LID identity
account.link-pn           → Link PN identity
account.unlink            → Remove identity link
account.list-identities   → Show all linked identities
account.change-password   → Update password
account.gen-recovery      → Generate new recovery codes
account.verify            → Verify identity
account.delete            → Delete account (with confirmation)
account.export-data       → Export personal data
identity.resolve          → Resolve LID/PN to account
identity.conflict-check   → Check identity conflicts
identity.merge-request    → Request account merge
identity.history          → Show identity change log
guest.browse              → Browse public features
guest.limit-check         → Check guest limitations
session.create            → Create new session
session.refresh           → Refresh session token
session.revoke            → Revoke specific session
session.list-active       → List all active sessions
security.audit-log        → View security events
```

## 3.2 Profile, Rank & Title (15 features)

```
profile.view              → View own profile
profile.view-other        → View other's profile
profile.edit              → Edit display name
profile.stats             → Detailed statistics
rank.info                 → Rank information
rank.promote              → Promote user (owner only)
rank.demote               → Demote user (owner only)
title.list                → List all available titles
title.equip               → Equip a title
title.unequip             → Unequip current title
title.preview             → Preview title appearance
title.unlock-condition    → Check title unlock requirements
badge.show                → Show earned badges
badge.hide                → Hide specific badge
reputation.view           → View reputation score
```

## 3.3 Economy (30 features)

```
eco.balance               → Check wallet balance
eco.bank                  → Check bank balance
eco.deposit               → Deposit to bank
eco.withdraw              → Withdraw from bank
eco.daily                 → Claim daily reward
eco.weekly                → Claim weekly reward
eco.monthly               → Claim monthly reward
eco.work                  → Work for money
eco.quit-job              → Quit current job
eco.job-list              → Available jobs
eco.transfer              → Transfer money
eco.pay                   → Pay another user
eco.request               → Request payment
eco.invoice               → Create invoice
eco.history               → Transaction history
eco.ledger                → Full ledger view (owner)
eco.loan                  → Take a loan
eco.repay-loan            → Repay loan
eco.invest                → Investment options
eco.stock-buy             → Buy stocks
eco.stock-sell            → Sell stocks
eco.market-view           → Market overview
eco.auction-create        → Create auction
eco.auction-bid           → Place bid
eco.auction-cancel        → Cancel auction
eco.insurance-buy         → Buy insurance
eco.insurance-claim       → Claim insurance
eco.tax-pay               → Pay taxes
eco.tax-view              → View tax obligations
eco.donation              → Donate to bot/project
```

## 3.4 Inventory & Items (18 features)

```
inv.view                  → View inventory
inv.sort                  → Sort inventory
inv.filter                → Filter by type/rarity
inv.use                   → Use an item
inv.equip                 → Equip item
inv.unequip               → Unequip item
inv.give                  → Give item to user
inv.sell                  → Sell item
inv.trash                 → Discard item
item.info                 → Item details
item.compare              → Compare two items
item.enchant              → Enchant equipment
item.upgrade              → Upgrade item level
item.repair               → Repair durability
item.reforge              → Reforge stats
item.combine              → Combine items
item.unlock-box           → Open crate/box
item.collection           → View collection progress
```

## 3.5 Shop & Market (14 features)

```
shop.list                 → List shop items
shop.buy                  → Buy item
shop.sell                 → Sell to shop
shop.search               → Search shop
shop.category             → Browse categories
shop.discount             → View discounts
shop.restock              → Restock notification
market.browse             → Browse player market
market.search             → Search market
market.create-listing     → Create listing
market.cancel-listing     → Cancel listing
market.purchase           → Purchase from market
market.my-listings        → View my listings
market.price-history      → Price trends
```

## 3.6 Daily & Quest (22 features)

```
daily.claim               → Claim daily reward
daily.streak              → View streak info
daily.bonus               → Streak bonus
quest.list                → List available quests
quest.accept              → Accept quest
quest.abandon             → Abandon quest
quest.progress            → Quest progress
quest.complete            → Claim completion
quest.daily               → Daily quests
quest.weekly              → Weekly quests
quest.seasonal            → Seasonal quests
quest.chain               → Chain quests
quest.hint                → Get quest hint
quest.skip                → Skip quest (penalty)
quest.track               → Track active quest
quest.share               → Share quest with group
achievement.list          → List achievements
achievement.progress      → Achievement progress
achievement.claim         → Claim achievement reward
achievement.universal     → Universal achievements
achievement.game          → Game-specific achievements
achievement.hidden        → Hidden achievements
```

## 3.7 Season Pass (16 features)

```
season.info               → Current season info
season.progress           → Season progress
season.tier               → Current tier
season.rewards            → View all rewards
season.claim              → Claim tier reward
season.claim-all          → Claim all available
season.missions           → Season missions
season.premium            → Premium pass info
season.leaderboard        → Season leaderboard
season.history            → Past seasons
season.preview            → Next season preview
season.buy-pass           → Buy season pass
season.gift-pass          → Gift pass to friend
season.challenge          → Season challenges
season.event              → Seasonal events
season.exclusive          → Exclusive rewards
```

## 3.8 Achievement System (18 features)

```
ach.list                  → List all achievements
ach.universal             → Universal category
ach.slot                  → Slot achievements
ach.dungeon               → Dungeon achievements
ach.fishing               → Fishing achievements
ach.mining                → Mining achievements
ach.combat                → Combat achievements
ach.social                → Social achievements
ach.economy               → Economy achievements
ach.collection            → Collection achievements
ach.event                 → Event achievements
ach.hidden                → Hidden achievements
ach.progress              → Incomplete achievements
ach.completed             → Completed achievements
ach.rare                  → Rare achievements
ach.global-rank           → Global achievement rank
ach.group-rank            → Group achievement rank
ach.reward-history        → Reward claim history
```

## 3.9 Reputation (10 features)

```
rep.view                  → View reputation
rep.gift                  → Gift reputation
rep.receive               → Received reputation
rep.history               → Reputation history
rep.leaderboard           → Reputation leaderboard
rep.tier                  → Reputation tier info
rep.benefits              → Tier benefits
rep.decay                 → Decay information
rep.restore               → Restore reputation
rep.block                 → Block reputation gifts
```

## 3.10 Games (50 features)

### Casino & Luck (10)
```
game.slots                → Slot machine
game.slots-double         → Double or nothing
game.dice                 → Roll dice
game.dice-bet             → Bet on dice
game.coinflip             → Flip coin
game.coinflip-bet         → Bet on coinflip
game.rps                  → Rock Paper Scissors
game.rps-bet              → Bet RPS
game.roulette             → Roulette wheel
game.roulette-bet         → Bet roulette
```

### Skill Games (15)
```
game.trivia               → Trivia quiz
game.trivia-category      → Category selection
game.math                 → Math challenge
game.math-hard            → Hard mode
game.memory               → Memory game
game.pattern              → Pattern recall
game.quick-calc           → Quick calculation
game.word-scramble        → Word scramble
game.guess-number         → Guess the number
game.high-low             → Higher or lower
game.blackjack            → Blackjack
game.blackjack-bet        → Bet blackjack
game.poker-hand           → Poker hand ranking
game.baccarat             → Baccarat
game.craps                → Craps dice
```

### Puzzle Games (10)
```
game.tictactoe            → Tic Tac Toe
game.tictactoe-pvp        → PvP mode
game.connect4             → Connect Four
game.reversi              → Reversi/Othello
game.checkers             → Checkers
game.sudoku               → Sudoku
game.sudoku-easy          → Easy difficulty
game.sudoku-hard          → Hard difficulty
game.minesweeper          → Minesweeper
game.crossword            → Crossword
```

### Word Games (10)
```
game.hangman              → Hangman
game.hangman-category     → Category mode
game.wordle               → Wordle clone
game.wordle-custom        → Custom word
game.scrabble             → Scrabble-like
game.boggle               → Boggle
game.anagram              → Anagram solver
game.spelling-bee         → Spelling bee
game.vocabulary           → Vocabulary test
game.idiom-guess          → Idiom guessing
```

### Reaction Games (5)
```
game.reaction             → Reaction time test
game.whack-a-mole         → Whack a mole
game.tap-speed            → Tap speed test
game.reflex               → Reflex training
game.focus                → Focus challenge
```

## 3.11 RPG Core (25 features)

```
rpg.profile               → RPG profile
rpg.stats                 → Detailed stats
rpg.class                 → View/change class
rpg.class-warrior         → Warrior class
rpg.class-rogue           → Rogue class
rpg.class-mage            → Mage class
rpg.equipment             → View equipment
rpg.weapon                → Weapon info
rpg.armor                 → Armor info
rpg.accessory             → Accessory info
rpg.combat                → Start combat
rpg.attack                → Attack command
rpg.defend                → Defend command
rpg.skill-use             → Use skill
rpg.flee                  → Flee from combat
rpg.loot                  → View loot
rpg.hp-potion             → Use HP potion
rpg.mp-potion             → Use MP potion
rpg.resurrect             → Resurrect after death
rpg.revive-other          → Revive teammate
rpg.party-create          → Create party
rpg.party-invite          → Invite to party
rpg.party-leave           → Leave party
rpg.party-kick            → Kick from party
rpg.party-join            → Join party request
```

## 3.12 RPG Content (20 features)

```
rpg.hunt                  → Hunt monsters
rpg.hunt-area1            → Area 1 monsters
rpg.hunt-area2            → Area 2 monsters
rpg.hunt-area3            → Area 3 monsters
rpg.dungeon               → Enter dungeon
rpg.dungeon-easy          → Easy dungeon
rpg.dungeon-medium        → Medium dungeon
rpg.dungeon-hard          → Hard dungeon
rpg.boss                  → Boss raid
rpg.boss-weekly           → Weekly boss
rpg.boss-event            → Event boss
rpg.raid                  → Group raid
rpg.raid-join             → Join raid
rpg.raid-status           → Raid status
rpg.explore               → Explore area
rpg.explore-forest        → Forest exploration
rpg.explore-cave          → Cave exploration
rpg.explore-ruins         → Ruins exploration
rpg.quest-rpg             → RPG-specific quests
rpg.arena                 → PvP arena
```

## 3.13 Skills & Equipment (22 features)

```
skill.tree                → View skill tree
skill.learn               → Learn skill
skill.upgrade             → Upgrade skill
skill.reset               → Reset skills
skill.combat-power        → Power skill I
skill.combat-power2       → Power skill II
skill.combat-crit         → Critical skill
skill.combat-crit2        → Critical II
skill.defense-vitality    → Vitality skill
skill.defense-vitality2   → Vitality II
skill.defense-armor       → Armor skill
skill.luck-fortune        → Fortune skill
skill.luck-fortune2       → Fortune II
skill.luck-hunter         → Rare Hunter
skill.passive-list        → List passive skills
skill.active-list         → List active skills
equip.weapon-sword        → Sword weapons
equip.weapon-axe          → Axe weapons
equip.weapon-spear        → Spear weapons
equip.weapon-bow          → Bow weapons
equip.weapon-staff        → Staff weapons
equip.armor-cloth         → Cloth armor
```

## 3.14 Fishing (18 features)

```
fish.start                → Start fishing
fish.cast                 → Cast line
fish.wait                 → Wait for bite
fish.catch                → Catch fish
fish.inventory            → Fish inventory
fish.sell                 → Sell fish
fish.sell-all             → Sell all fish
fish.cook                 → Cook fish
fish.aquarium             → View aquarium
fish.aquarium-add         → Add to aquarium
fish.aquarium-remove      → Remove from aquarium
fish.collection           → Fish collection
fish.collection-complete  → Completion rewards
fish.tournament           → Fishing tournament
fish.tournament-join      → Join tournament
fish.bait-buy             → Buy bait
fish.bait-use             → Use special bait
fish.legendary            → Legendary fish info
```

## 3.15 Mining (18 features)

```
mine.start                → Start mining
mine.pickaxe              → Pickaxe info
mine.pickaxe-upgrade      → Upgrade pickaxe
mine.ore-copper           → Copper ore
mine.ore-iron             → Iron ore
mine.ore-gold             → Gold ore
mine.ore-diamond          → Diamond ore
mine.ore-emerald          → Emerald ore
mine.ore-ruby             → Ruby ore
mine.ore-sapphire         → Sapphire ore
mine.gem-cut              → Cut gems
mine.gem-sell             → Sell gems
mine.smelt                → Smelt ores
mine.smelt-bar            → Create bars
mine.deep-mine            → Deep mining
mine.cave-explore         → Cave exploration
mine.tunnel               → Tunnel digging
mine.treasure             → Treasure hunting
```

## 3.16 Crafting & Professions (15 features)

```
craft.menu                → Crafting menu
craft.recipe              → View recipe
craft.craft               → Craft item
craft.chef-cook           → Chef profession
craft.chef-recipe         → Chef recipes
craft.alchemist-potion    → Alchemist potions
craft.alchemist-brew      → Brewing
craft.blacksmith-forge    → Blacksmith forging
craft.blacksmith-temper   → Tempering
craft.profession-level    → Profession level
craft.profession-xp       → Profession XP
craft.mastery             → Mastery rewards
craft.custom              → Custom crafting
craft.batch               → Batch crafting
craft.auto                → Auto-craft setup
```

## 3.17 Collection & Museum (10 features)

```
collection.view           → View all collections
collection.fish           → Fish collection
collection.ore            → Ore collection
collection.gems           → Gem collection
collection.items          → Item collection
collection.achievements   → Achievement collection
collection.titles         → Title collection
collection.completion     → Completion percentage
collection.reward-claim   → Claim collection rewards
collection.showcase       → Public showcase
```

## 3.18 Tournament (8 features)

```
tournament.list           → Active tournaments
tournament.join           → Join tournament
tournament.leave          → Leave tournament
tournament.status         → Tournament status
tournament.rules          → Tournament rules
tournament.prizes         → Prize pool
tournament.history        → Past tournaments
tournament.rank           → Tournament ranking
```

## 3.19 Bounty & PvP (6 features)

```
bounty.create             → Create bounty
bounty.view               → View bounties
bounty.accept             → Accept bounty
bounty.complete           → Complete bounty
bounty.claim              → Claim reward
bounty.history            → Bounty history
```

## 3.20 Events (8 features)

```
event.list                → Active events
event.join                → Join event
event.progress            → Event progress
event.reward              → Event rewards
event.daily               → Daily event
event.weekly              → Weekly event
event.special             → Special events
event.archive             → Past events
```

## 3.21 Group Admin (18 features)

```
group.kick                → Kick member
group.add                 → Add member
group.promote             → Promote to admin
group.demote              → Demote from admin
group.remove              → Remove member
group.del-msg             → Delete message
group.open                → Open group
group.close               → Close group
group.lock                → Lock group settings
group.unlock              → Unlock settings
group.everyone            → Tag everyone
group.tag-admins          → Tag admins
group.info                → Group info
group.settings            → Group settings
group.invite-link         → Get invite link
group.revoke-link         → Revoke invite link
group.desc-set            → Set description
group.subject-set         → Set subject
```

## 3.22 Security & Moderation (12 features)

```
mod.antilink              → Anti-link toggle
mod.antispam              → Anti-spam toggle
mod.antitoxic             → Anti-toxic toggle
mod.ban-user              → Ban user
mod.unban-user            → Unban user
mod.ban-list              → Ban list
mod.warn                  → Warn user
mod.unwarn                → Remove warning
mod.warnings              → View warnings
mod.mute                  → Mute user
mod.unmute                → Unmute user
mod.audit                 → Moderation audit
```

## 3.23 Mini-Owner (10 features)

```
mo.groups                 → Managed groups
mo.config                 → Group configuration
mo.security               → Security settings
mo.stats                  → Group statistics
mo.billing                → Billing info
mo.renew                  → Renew contract
mo.upgrade                → Upgrade plan
mo.permissions            → Permission settings
mo.delegate               → Delegate access
mo.reports                → Group reports
```

## 3.24 Owner (7 features)

```
owner.dashboard           → Owner dashboard
owner.users               → User management
owner.broadcast           → Broadcast message
owner.backup              → Create backup
owner.restore             → Restore backup
owner.system              → System status
owner.logs                → System logs
```

## 3.25 Mail (4 features)

```
mail.send                 → Send mail
mail.inbox                → View inbox
mail.read                 → Read mail
mail.attach               → Attach item/money
```

## 3.26 Media & Sticker (10 features)

```
media.sticker             → Create sticker
media.sticker-crop        → Cropped sticker
media.sticker-circle      → Circle sticker
media.sticker-animated    → Animated sticker
media.quote               → Quote message
media.meme                → Meme generator
media.cartoon             → Cartoon effect
media.sketch              → Sketch effect
media.pixelate            → Pixelate effect
media.ascii               → ASCII art
```

## 3.27 Downloader (8 features)

```
down.yt-video             → YouTube video
down.yt-audio             → YouTube audio
down.yt-shorts            → YouTube Shorts
down.tiktok               → TikTok video
down.tiktok-nowm          → TikTok no watermark
down.instagram            → Instagram post
down.instagram-story      → Instagram story
down.facebook             → Facebook video
```

## 3.28 Image Processing (10 features)

```
img.blur                  → Blur image
img.sharpen               → Sharpen image
img.grayscale             → Grayscale
img.contrast              → Adjust contrast
img.brightness            → Adjust brightness
img.sepia                 → Sepia tone
img.invert                → Invert colors
img.rotate                → Rotate image
img.resize                → Resize image
img.watermark             → Add watermark
```

## 3.29 Video & Audio (8 features)

```
vid.trim                  → Trim video
vid.merge                 → Merge videos
vid.compress              → Compress video
vid.extract-audio         → Extract audio
vid.gif                   → Convert to GIF
vid.reverse               → Reverse video
aud.trim                  → Trim audio
aud.merge                 → Merge audio
```

## 3.30 Document Converter (6 features)

```
doc.pdf2img               → PDF to images
doc.img2pdf               → Images to PDF
doc.docx2pdf              → DOCX to PDF
doc.pdf2docx              → PDF to DOCX
doc.xlsx2csv              → Excel to CSV
doc.csv2xlsx              → CSV to Excel
```

## 3.31 Utility & Search (16 features)

```
util.weather              → Weather info
util.currency             → Currency converter
util.crypto               → Crypto prices
util.time                 → World time
util.translate            → Translate text
util.dict                 → Dictionary lookup
util.wiki                 → Wikipedia search
util.google               → Google search
util.github               → GitHub search
util.lyrics               → Song lyrics
util.qrcode-gen           → Generate QR code
util.qrcode-read          → Read QR code
util.base64-enc           → Base64 encode
util.base64-dec           → Base64 decode
util.calc                 → Calculator
util.unit-convert         → Unit conversion
```

---

# 4. IMPLEMENTATION ROADMAP

## Phase 1: Foundation (Week 1-2)
- [ ] Setup project structure
- [ ] Database schema + migrations
- [ ] Account system (register, login, recovery)
- [ ] Identity resolution (LID/PN)
- [ ] WhatsApp adapter (Baileys)
- [ ] Basic permission engine

## Phase 2: Core Systems (Week 3-4)
- [ ] Profile + Rank + Title
- [ ] Economy (wallet, bank, transactions)
- [ ] Inventory + Items
- [ ] Shop system
- [ ] Daily rewards + Quest basics

## Phase 3: Games & RPG (Week 5-7)
- [ ] Simple games (slots, rps, dice)
- [ ] RPG stats + Combat
- [ ] Fishing system
- [ ] Mining system
- [ ] Skill tree basics

## Phase 4: Progression (Week 8-9)
- [ ] Achievement system
- [ ] Season pass
- [ ] Reputation
- [ ] Collection/Museum

## Phase 5: Group & Social (Week 10-11)
- [ ] Group admin commands
- [ ] Mini-Owner contracts
- [ ] Moderation tools
- [ ] Mail system

## Phase 6: Media & Utility (Week 12-13)
- [ ] Image processing
- [ ] Video/Audio tools
- [ ] Document converters
- [ ] Downloader adapters
- [ ] Search utilities

## Phase 7: Polish & Testing (Week 14-15)
- [ ] UI/UX improvements
- [ ] Menu system (/m dashboard)
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation

## Phase 8: Migration & Launch (Week 16)
- [ ] Legacy v53/R2 migration
- [ ] Backup/restore testing
- [ ] Production deployment
- [ ] Monitoring setup

---

# 5. SUCCESS METRICS

## Technical Metrics
- ✅ Account persistence: 100% (no data loss on LID/PN change)
- ✅ Transaction integrity: 100% (rollback on failure)
- ✅ Command latency: <200ms for local operations
- ✅ Uptime: >99% for single-instance deployment

## Feature Metrics
- ✅ 500 features implemented and tested
- ✅ Each feature has 3-8 natural aliases
- ✅ No placeholder/fake implementations
- ✅ All features pass acceptance tests

## User Experience Metrics
- ✅ /m menu loads in <1 second
- ✅ Profile displays all relevant info clearly
- ✅ Error messages are helpful and actionable
- ✅ Recovery flow completes in <5 minutes

---

# 6. LESSONS FROM COMMUNITY BOTS

## What to Keep ✅
1. **Simple cooldown systems** - Easy to understand
2. **Emoji-rich responses** - Visually engaging
3. **Random loot/rewards** - Creates excitement
4. **Streak bonuses** - Encourages daily play
5. **Leaderboards** - Competitive element
6. **Collection mechanics** - Completionist appeal
7. **Group events** - Social engagement

## What to Improve 🔧
1. **Add transaction ledger** - Audit trail missing in most bots
2. **Implement rollback** - Prevent economy corruption
3. **Deterministic RNG** - Use seeds for reproducibility
4. **Better death penalty** - Not too harsh, not too lenient
5. **Meaningful choices** - Class/skill decisions matter
6. **Item sinks** - Prevent inflation
7. **Permission granularity** - Context-aware permissions

## What to Avoid ❌
1. Pure gambling without limits
2. Pay-to-win mechanics
3. Overly complex crafting trees
4. Grind-heavy progression
5. Features that require constant maintenance
6. Dependencies on unstable APIs
7. Hardcoded values (use configuration)

---

# 7. NEXT STEPS

1. **Review this document** - Ensure all stakeholders agree on direction
2. **Finalize feature priorities** - Adjust based on team capacity
3. **Setup development environment** - Install dependencies
4. **Create initial commit** - Project structure + database schema
5. **Begin Phase 1 implementation** - Account + Identity systems

---

## Appendix A: Feature Readiness Gate

Before any feature is marked READY:

```typescript
interface FeatureContract {
  id: string;                   // Unique feature ID
  aliases: string[];            // Natural aliases
  kind: 'READONLY' | 'ACTION' | 'ARTIFACT' | 'ADMIN';
  requiresLogin: boolean;
  permission: string;
  handler: Function;
  test: string;                 // Test suite name
  
  // Contract validation
  inputValidation: boolean;     // Validates user input
  outputContract: boolean;      // Produces expected output
  stateMutation: boolean;       // Updates state correctly
  errorHandling: boolean;       // Graceful error handling
  idempotency: boolean;         // Safe to retry
}
```

## Appendix B: Command Naming Guidelines

Good:
- `/eco` - Short, clear
- `/rpg` - Obvious purpose
- `/fish` - Natural verb
- `/inv` - Common abbreviation

Bad:
- `/r2-fishing-fishing` - Internal structure exposed
- `/economy-wallet-balance-check` - Too verbose
- `/feature-runner-game-slots` - Framework leak

## Appendix C: Testing Checklist

```markdown
## Unit Tests
- [ ] Damage calculation
- [ ] Crit chance
- [ ] Skill prerequisites
- [ ] Economy transactions
- [ ] Inventory operations
- [ ] Achievement triggers
- [ ] Permission checks

## Integration Tests
- [ ] Register → Login → Logout
- [ ] LID ↔ PN identity switch
- [ ] Recovery flow
- [ ] Daily → Quest → Achievement chain
- [ ] Buy → Inventory → Equip
- [ ] Fish → Collection → Reward
- [ ] Group admin permissions

## Artifact Tests
- [ ] Output file exists
- [ ] File size > 0
- [ ] Valid format (PNG, MP4, etc.)
- [ ] File readable
- [ ] Cleanup after send

## Regression Tests
- [ ] Legacy data migration
- [ ] Account preservation
- [ ] Economy unchanged
- [ ] Inventory intact
- [ ] Progression maintained
```

---

**Document Version:** 1.0  
**Created:** 2025  
**Status:** Planning Phase  
**Next Review:** After Phase 1 completion

