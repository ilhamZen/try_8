# Cinnamon R1F - WhatsApp Bot Ecosystem

## Release 1 Finale

Cinnamon R1F adalah bot WhatsApp yang dibangun dengan pendekatan **account-first**, menggunakan TypeScript + NestJS sebagai core, SQLite + Drizzle ORM untuk database, dan C#/.NET untuk RPG calculation engine.

## Architecture

```
ACCOUNT (UUID immutable)
  ↓
IDENTITY (LID/PN linked to account)
  ↓
PERMISSION (context-based)
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

## Tech Stack

### Backend
- **TypeScript** - Main application language
- **NestJS** - Application framework
- **SQLite + Drizzle ORM** - Database layer
- **Argon2** - Password hashing
- **Baileys** - WhatsApp adapter

### RPG Engine
- **C# / .NET 10** - Native calculation engine
- **gRPC + Protobuf** - IPC communication

### Media Processing
- **Sharp** - Image processing
- **FFmpeg** - Video/audio processing

## Project Structure

```
cinnamon-r1f/
├── apps/
│   ├── bot/              # Main bot application
│   │   └── src/
│   │       ├── account/
│   │       ├── identity/
│   │       ├── permission/
│   │       ├── profile/
│   │       ├── economy/
│   │       ├── inventory/
│   │       ├── rpg/
│   │       ├── game/
│   │       ├── group/
│   │       ├── media/
│   │       └── main.ts
│   └── engine/           # C# RPG engine
├── db/
│   ├── schema.ts
│   ├── connection.ts
│   └── migrations/
├── proto/
│   └── cinnamon.proto
├── tests/
│   ├── unit/
│   └── integration/
├── data/                 # Runtime data (gitignored)
├── package.json
├── tsconfig.json
└── drizzle.config.ts
```

## Key Features

### Account System
- Permanent UUID-based accounts
- Multiple identity links (LID, PN)
- Argon2id password hashing
- Recovery codes for account recovery
- LID/PN conflict detection (no auto-merge)

### Permission System
- Context-based permissions
- Rank inheritance: USER → MINI_OWNER → OWNER
- Group-specific permissions
- Mini-owner contracts per group

### Economy
- Wallet and bank system
- Transaction ledger with full audit trail
- Atomic transactions with rollback
- Transfer between accounts

### Profile
- Display name, rank, title
- Level and XP system
- Reputation (0-1000) with tiers
- Title system (cosmetic only)

## Getting Started

### Prerequisites
- Node.js 24 LTS
- .NET 10 SDK (for RPG engine)
- FFmpeg (for media processing)

### Installation

```bash
cd cinnamon-r1f
npm ci
npm run build
```

### Database Setup

```bash
npm run db:generate
npm run db:migrate
```

### Run Tests

```bash
npm test
```

### Start Application

```bash
npm start
```

## Development

### Add New Feature Module

1. Create module folder in `apps/bot/src/`
2. Create service with business logic
3. Create module for dependency injection
4. Import module in `app.module.ts`

### Database Schema Changes

1. Edit `db/schema.ts`
2. Generate migration: `npm run db:generate`
3. Apply migration: `npm run db:migrate`

### Proto Buffer Changes

1. Edit `proto/cinnamon.proto`
2. Generate: `npm run proto:generate`

## Testing Philosophy

- Unit tests for services
- Integration tests for database operations
- Account persistence tests (LID/PN/recovery)
- Economy transaction tests (rollback scenarios)
- Permission matrix tests

## Quality Gates

Before release, ensure:
- ✅ TypeScript strict compile passes
- ✅ All unit tests pass
- ✅ Database migrations work
- ✅ Foreign key checks pass
- ✅ No duplicate aliases
- ✅ Account persistence verified
- ✅ LID/PN handling tested
- ✅ Recovery flow tested

## Migration from v53

See `MIGRATION.md` for detailed migration guide from legacy JSON-based storage to SQLite database.

## Security Notes

- Never commit `.env` or `wa-auth/`
- Recovery codes shown only once
- Passwords hashed with Argon2id
- Transaction ledger for economy audit
- Idempotency keys for critical operations

## License

Private - Cinnamon Project
