# 🍂 CINNAMON UNIFIED — README

## WhatsApp Bot Ecosystem — R1F Finale

**TypeScript + NestJS + SQLite + Baileys + Optional C# RPG Engine**

---

## 🚀 Quick Start

### Prerequisites

- Node.js 24+ 
- pnpm 9+
- .NET 10 (optional, for C# RPG engine)
- FFmpeg (for media processing)
- Git

### Installation

```bash
cd cinnamon-unified

# Install dependencies
pnpm install

# Copy environment file
cp .env.example .env

# Generate database migrations
pnpm db:generate
pnpm db:migrate

# Seed initial data
pnpm db:seed

# Start development
pnpm dev
```

### Production Build

```bash
pnpm build
pnpm start
```

---

## 📁 Project Structure

```
cinnamon-unified/
├── apps/
│   ├── bot/           # Main WhatsApp bot (TypeScript + NestJS)
│   └── engine/        # C# RPG calculation engine (optional)
├── db/
│   ├── schema.ts      # Database schema (Drizzle ORM)
│   ├── migrations/    # Auto-generated migrations
│   └── seeders/       # Initial data seeding
├── proto/             # Protobuf contracts (TS ↔ C#)
├── tests/             # Test suites
│   ├── unit/
│   ├── integration/
│   └── artifact/
├── data/              # Runtime data (SQLite DB, backups)
├── scripts/           # Utility scripts (backup, migration)
└── configs/           # Configuration files
```

---

## 🎯 Key Features

### Account System
- ✅ Permanent UUID-based accounts
- ✅ Multiple identity links (LID, PN)
- ✅ Recovery codes for account restoration
- ✅ Password hashing with Argon2id

### Economy
- ✅ Wallet & Bank system
- ✅ Transaction ledger with audit trail
- ✅ Rollback on failure
- ✅ Shop, market, auction

### RPG
- ✅ Stats: HP, ATK, DEF, CRIT, LUCK
- ✅ Classes: Warrior, Rogue, Mage
- ✅ Equipment: Weapon, Armor, Accessory
- ✅ Skills tree with prerequisites
- ✅ Dungeons & Boss battles
- ✅ Deterministic combat (seed-based)

### Games (50+)
- Casino: Slot, Roulette, Dice
- Skill: RPS, Hangman, Scramble, Trivia
- Puzzle: Sudoku, Memory, Math Quiz
- Board: Tic-Tac-Toe, Connect Four, Reversi

### Progression
- ✅ Achievement system (universal + game-specific)
- ✅ Quest system (daily, weekly, story)
- ✅ Season pass (30-day cycles)
- ✅ Reputation system (0-1000)

### Group Features
- ✅ Admin commands: kick, add, delete, open/close
- ✅ Mini-Owner contracts (group leasing)
- ✅ Context-aware permissions
- ✅ World events (group raids)

### Media
- ✅ Image processing (Sharp): blur, sharpen, effects
- ✅ Video/Audio (FFmpeg): trim, convert, extract
- ✅ Sticker maker
- ✅ Downloader providers: YouTube, TikTok, Instagram

---

## 🔐 Security

- Password hashing: **Argon2id**
- Recovery codes: **Hashed, one-time use**
- Environment variables: **Never commit `.env`**
- Database backups: **Encrypted at rest**
- Audit logs: **All owner actions logged**
- Rate limiting: **Per-user, per-command**
- SQL injection prevention: **Drizzle ORM**

---

## 🧪 Testing

```bash
# All tests
pnpm test

# Unit tests only
pnpm test:unit

# Integration tests only
pnpm test:integration

# Artifact tests (media processing)
pnpm test:artifact

# With coverage
pnpm test -- --coverage
```

---

## 🗄️ Database

**SQLite** with **Drizzle ORM**

```bash
# Generate new migration
pnpm db:generate

# Run migrations
pnpm db:migrate

# Seed initial data
pnpm db:seed
```

### Backup

```bash
# Create backup
pnpm backup:create

# Restore from backup
pnpm backup:restore
```

---

## 🎮 C# RPG Engine (Optional)

For heavy CPU calculations, use the optional C# engine:

```bash
# Build engine
pnpm engine:build

# Run engine (gRPC server)
pnpm engine:run

# Test engine
pnpm engine:test
```

Enable in `.env`:
```
RPG_ENGINE_ENABLED=true
```

---

## 🔄 Migration from v53/R2

```bash
# Backup your v53 data first!
cp -r /path/to/v53/data /backup/location

# Run migration script
pnpm migrate:v53 --source=/path/to/v53/data

# Verify migration
pnpm health:check
```

See `MIGRATION.md` for detailed instructions.

---

## 📊 Performance Targets

| Operation | Target |
|-----------|--------|
| Balance check | <50ms |
| Daily claim | <100ms |
| Game (local) | <150ms |
| RPG combat | <200ms |
| Image blur | <500ms |
| DB transaction | <50ms |

---

## 🛠️ Development

### Add New Feature

1. Create module in `apps/bot/src/<feature>/`
2. Define feature contract in `commands/registry.ts`
3. Write tests in `tests/unit/<feature>.test.ts`
4. Update `FEATURE_MANIFEST.md`

### Add New Command

```typescript
// apps/bot/src/commands/registry.ts
defineFeature({
  id: "game.slot",
  aliases: ["slot", "slots", "spin"],
  kind: "action",
  requiresLogin: true,
  permission: "user.games.casino",
  handler: handleSlot,
  test: "game.slot"
});
```

### Add New Item

```typescript
// db/seeders/items.seeder.ts
{
  id: "sword_iron",
  name: "Iron Sword",
  type: "weapon",
  rarity: "uncommon",
  sellPrice: 150,
  effects: { atk: 5 }
}
```

---

## 📝 Documentation

- `ARCHITECTURE.md` — Deep dive into architecture
- `MIGRATION.md` — Migration guide from v53/R2
- `SECURITY.md` — Security practices
- `FEATURE_MANIFEST.md` — 500 features checklist
- `CINNAMON_R1F_FINAL_STRUCTURE.md` — Complete structure reference

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

Proprietary — All rights reserved

---

## 👑 Owner

**Nyx1024** — Original creator and maintainer

---

## 🙏 Acknowledgments

- Baileys team for WhatsApp library
- NestJS team for framework
- Drizzle ORM team for database tools
- Community contributors and testers

---

**Built with ❤️ using TypeScript, NestJS, and a lot of coffee ☕**
