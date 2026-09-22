# 🍂 CINNAMON R1F — FINAL PROJECT STRUCTURE

## 📁 Root Structure

```
cinnamon-r1f/
├── apps/                      # Applications
│   ├── bot/                   # Main WhatsApp Bot (NestJS + TypeScript)
│   │   ├── src/
│   │   │   ├── main.ts                    # Bootstrap
│   │   │   ├── app.module.ts              # Root module
│   │   │   ├── app.service.ts             # Root service
│   │   │   ├── config.ts                  # Configuration loader
│   │   │   │
│   │   │   ├── whatsapp/                  # WhatsApp Layer (Baileys Adapter)
│   │   │   │   ├── whatsapp.module.ts
│   │   │   │   ├── whatsapp.service.ts
│   │   │   │   ├── whatsapp.adapter.ts    # Baileys wrapper
│   │   │   │   ├── events.handler.ts      # Message events
│   │   │   │   └── media.downloader.ts    # WhatsApp media download
│   │   │   │
│   │   │   ├── commands/                  # Command Parser & Registry
│   │   │   │   ├── commands.module.ts
│   │   │   │   ├── commands.service.ts
│   │   │   │   ├── parser.ts              # Command parser
│   │   │   │   ├── registry.ts            # Feature registry
│   │   │   │   └── feature.contract.ts    # Feature definition
│   │   │   │
│   │   │   ├── account/                   # Account Management
│   │   │   │   ├── account.module.ts
│   │   │   │   ├── account.service.ts
│   │   │   │   ├── account.repository.ts
│   │   │   │   └── account.types.ts
│   │   │   │
│   │   │   ├── identity/                  # Identity Resolution (LID/PN)
│   │   │   │   ├── identity.module.ts
│   │   │   │   ├── identity.service.ts
│   │   │   │   ├── identity.resolver.ts   # LID/PN → Account mapping
│   │   │   │   └── recovery.service.ts    # Recovery codes
│   │   │   │
│   │   │   ├── permission/                # Permission Engine
│   │   │   │   ├── permission.module.ts
│   │   │   │   ├── permission.service.ts
│   │   │   │   ├── permission.evaluator.ts # can(account, perm, context)
│   │   │   │   └── rank.constants.ts      # USER, MO, OWNER
│   │   │   │
│   │   │   ├── profile/                   # Profile, Rank, Title
│   │   │   │   ├── profile.module.ts
│   │   │   │   ├── profile.service.ts
│   │   │   │   ├── title.service.ts
│   │   │   │   └── profile.ui.ts          # Profile display formatter
│   │   │   │
│   │   │   ├── economy/                   # Economy System
│   │   │   │   ├── economy.module.ts
│   │   │   │   ├── wallet.service.ts
│   │   │   │   ├── bank.service.ts
│   │   │   │   ├── transaction.service.ts # Ledger + rollback
│   │   │   │   ├── loan.service.ts
│   │   │   │   └── economy.types.ts
│   │   │   │
│   │   │   ├── inventory/                 # Inventory & Items
│   │   │   │   ├── inventory.module.ts
│   │   │   │   ├── inventory.service.ts
│   │   │   │   ├── items.service.ts
│   │   │   │   ├── equipment.service.ts
│   │   │   │   └── crafting.service.ts
│   │   │   │
│   │   │   ├── progression/               # Quest, Achievement, Season
│   │   │   │   ├── progression.module.ts
│   │   │   │   ├── quest.service.ts
│   │   │   │   ├── achievement.service.ts
│   │   │   │   ├── season.service.ts
│   │   │   │   └── event.engine.ts        # Event bus for progression
│   │   │   │
│   │   │   ├── reputation/                # Reputation System
│   │   │   │   ├── reputation.module.ts
│   │   │   │   └── reputation.service.ts
│   │   │   │
│   │   │   ├── rpg/                       # RPG Core
│   │   │   │   ├── rpg.module.ts
│   │   │   │   ├── rpg.service.ts
│   │   │   │   ├── stats.service.ts       # HP, ATK, DEF, CRIT, LUCK
│   │   │   │   ├── combat.service.ts      # Battle calculation
│   │   │   │   ├── dungeon.service.ts
│   │   │   │   ├── boss.service.ts
│   │   │   │   ├── skill-tree.service.ts
│   │   │   │   ├── pet.service.ts
│   │   │   │   └── rpg.engine.client.ts   # gRPC client to C# engine
│   │   │   │
│   │   │   ├── game/                      # Games (Slot, RPS, Quiz, etc.)
│   │   │   │   ├── game.module.ts
│   │   │   │   ├── game.service.ts
│   │   │   │   ├── session.manager.ts     # Game state machine
│   │   │   │   ├── games/
│   │   │   │   │   ├── slot.game.ts
│   │   │   │   │   ├── rps.game.ts
│   │   │   │   │   ├── hangman.game.ts
│   │   │   │   │   ├── scramble.game.ts
│   │   │   │   │   ├── trivia.game.ts
│   │   │   │   │   └── ... (50 games total)
│   │   │   │   └── tournament.service.ts
│   │   │   │
│   │   │   ├── fishing/                   # Fishing System
│   │   │   │   ├── fishing.module.ts
│   │   │   │   ├── fishing.service.ts
│   │   │   │   ├── collection.service.ts  # Fish collection/museum
│   │   │   │   └── fishing.types.ts
│   │   │   │
│   │   │   ├── mining/                    # Mining/Gathering
│   │   │   │   ├── mining.module.ts
│   │   │   │   └── mining.service.ts
│   │   │   │
│   │   │   ├── group/                     # Group Admin Features
│   │   │   │   ├── group.module.ts
│   │   │   │   ├── group.service.ts
│   │   │   │   ├── admin.commands.ts      # kick, add, del, open, close
│   │   │   │   └── group.context.ts       # Context-aware permissions
│   │   │   │
│   │   │   ├── mo/                        # Mini-Owner System
│   │   │   │   ├── mo.module.ts
│   │   │   │   ├── mo.service.ts
│   │   │   │   ├── mo.contract.ts         # MO contract management
│   │   │   │   └── mo.permissions.ts
│   │   │   │
│   │   │   ├── owner/                     # Owner Administration
│   │   │   │   ├── owner.module.ts
│   │   │   │   ├── owner.service.ts
│   │   │   │   ├── user.management.ts
│   │   │   │   ├── ban.system.ts
│   │   │   │   └── audit.log.ts
│   │   │   │
│   │   │   ├── media/                     # Media Processing
│   │   │   │   ├── media.module.ts
│   │   │   │   ├── media.service.ts
│   │   │   │   ├── sticker.service.ts
│   │   │   │   ├── image.processor.ts     # Sharp-based effects
│   │   │   │   ├── video.processor.ts     # FFmpeg wrapper
│   │   │   │   └── audio.processor.ts
│   │   │   │
│   │   │   ├── downloader/                # Network Downloader
│   │   │   │   ├── downloader.module.ts
│   │   │   │   ├── downloader.service.ts
│   │   │   │   ├── providers/
│   │   │   │   │   ├── youtube.provider.ts
│   │   │   │   │   ├── tiktok.provider.ts
│   │   │   │   │   ├── instagram.provider.ts
│   │   │   │   │   └── ... (8 providers)
│   │   │   │   └── queue.worker.ts        # Bounded worker queue
│   │   │   │
│   │   │   ├── utility/                   # Utility Commands
│   │   │   │   ├── utility.module.ts
│   │   │   │   ├── converter.service.ts   # PDF, image converters
│   │   │   │   ├── search.service.ts      # Wiki, news, weather
│   │   │   │   ├── qr.service.ts
│   │   │   │   └── tools.service.ts
│   │   │   │
│   │   │   ├── ui/                        # UI Formatters
│   │   │   │   ├── menu.ui.ts             # /m dashboard
│   │   │   │   ├── profile.ui.ts
│   │   │   │   ├── economy.ui.ts
│   │   │   │   └── rpg.ui.ts
│   │   │   │
│   │   │   └── events/                    # Event Bus
│   │   │       ├── events.module.ts
│   │   │       ├── event.bus.ts
│   │   │       └── event.handlers.ts
│   │   │
│   │   └── package.json
│   │
│   └── engine/                # C# RPG Engine (Optional, for heavy calc)
│       ├── Cinnamon.Engine.csproj
│       ├── Program.cs         # gRPC server
│       ├── CombatEngine.cs
│       ├── SkillEngine.cs
│       ├── DungeonEngine.cs
│       ├── LootEngine.cs
│       └── TournamentEngine.cs
│
├── db/                        # Database Layer
│   ├── schema.ts              # Drizzle schema (complete)
│   ├── connection.ts          # SQLite connection with WAL
│   ├── migrations/            # Migration files
│   └── seeders/               # Initial data (items, achievements, etc.)
│
├── proto/                     # Protobuf Contracts (TypeScript ↔ C#)
│   ├── cinnamon.proto         # RPG calculation contracts
│   └── generated/             # Auto-generated TS/CS files
│
├── tests/                     # Test Suites
│   ├── unit/
│   │   ├── account.test.ts
│   │   ├── identity.test.ts
│   │   ├── economy.test.ts
│   │   ├── permission.test.ts
│   │   ├── rpg-calc.test.ts
│   │   └── game-state.test.ts
│   │
│   ├── integration/
│   │   ├── register-login.test.ts
│   │   ├── lid-pn-resolution.test.ts
│   │   ├── recovery-flow.test.ts
│   │   ├── economy-rollback.test.ts
│   │   ├── group-permission.test.ts
│   │   └── mo-expiry.test.ts
│   │
│   ├── artifact/
│   │   ├── image-blur.test.ts
│   │   ├── converter.test.ts
│   │   └── downloader.test.ts
│   │
│   └── fixtures/
│       ├── v53-data/          # Legacy v53 JSON for migration test
│       └── test-images/
│
├── data/                      # Runtime Data (gitignored)
│   ├── cinnamon.db            # SQLite database
│   ├── cinnamon.db-wal
│   ├── cinnamon.db-shm
│   ├── backups/
│   │   ├── daily/
│   │   └── weekly/
│   └── wa-auth/               # Baileys auth (gitignored)
│
├── media_inbox/               # Temporary media workspace (gitignored)
├── logs/                      # Application logs (gitignored)
│
├── .env.example               # Environment template
├── .gitignore
├── nest-cli.json              # NestJS configuration
├── tsconfig.json              # TypeScript strict config
├── drizzle.config.ts          # Drizzle ORM config
├── vitest.config.ts           # Vitest test config
├── package.json               # Root package.json (monorepo)
├── pnpm-workspace.yaml        # PNPM workspace (or yarn.workspaces)
│
├── README.md                  # Getting started guide
├── ARCHITECTURE.md            # Architecture deep-dive
├── MIGRATION.md               # v53 → R1F migration guide
├── SECURITY.md                # Security practices
└── FEATURE_MANIFEST.md        # 500 features checklist
```

---

## 🔑 Key Design Decisions

### 1. **No Python Orchestration**
- Semua logic dalam TypeScript
- C# hanya untuk RPG calculation engine (optional, via gRPC)
- Tidak ada dependency ke Python runtime

### 2. **Monorepo Structure**
- `apps/bot` = Main application
- `apps/engine` = C# RPG engine (optional)
- Shared dependencies via workspace

### 3. **Database First**
- SQLite dengan Drizzle ORM
- WAL mode enabled untuk performance
- Transaction support untuk rollback
- Idempotency keys untuk prevent double-spend

### 4. **Feature Modules**
Setiap domain punya module sendiri:
- Module → Service → Repository pattern
- Dependency injection via NestJS
- Easy to test in isolation

### 5. **Command Registry**
- Feature contract sebelum registration
- Test required sebelum READY status
- Aliases terpisah dari implementation

### 6. **WhatsApp Adapter**
- Baileys di-isolate dalam adapter
- Jika Baileys berubah, hanya adapter yang perlu update
- Application layer tidak tahu tentang Baileys API

### 7. **Permission Engine**
- Centralized `can(accountId, permission, context)`
- No scattered `if (isOwner)` checks
- Context-aware (group-specific permissions)

### 8. **Event Bus**
- Achievement, Season, Reputation listen to events
- Single event can trigger multiple systems
- Decoupled architecture

---

## 🚀 Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. ✅ Project structure setup
2. ✅ Database schema + migrations
3. ✅ Account + Identity system
4. ✅ Permission engine
5. ✅ Profile + Rank + Title

### Phase 2: Core Economy (Week 3-4)
6. ✅ Wallet + Bank
7. ✅ Transaction ledger with rollback
8. ✅ Inventory + Items
9. ✅ Shop system

### Phase 3: Games & RPG (Week 5-7)
10. ✅ Game engine + state machine
11. ✅ 10 core games (slot, rps, trivia, etc.)
12. ✅ RPG stats + combat
13. ✅ Dungeon + Boss
14. ⏳ C# engine integration (optional)

### Phase 4: Progression (Week 8-9)
15. ✅ Achievement system
16. ✅ Quest system
17. ✅ Season pass
18. ✅ Reputation

### Phase 5: Group & Social (Week 10-11)
19. ✅ Group admin commands
20. ✅ Mini-Owner contracts
21. ✅ Owner administration
22. ✅ Mail system

### Phase 6: Media & Utility (Week 12-13)
23. ✅ Image processing (Sharp)
24. ✅ Video/Audio (FFmpeg)
25. ✅ Sticker maker
26. ✅ Downloader providers
27. ✅ Utility commands

### Phase 7: Polish & Testing (Week 14-15)
28. ✅ Full integration tests
29. ✅ Performance optimization
30. ✅ Error handling + logging
31. ✅ Documentation

### Phase 8: Migration & Launch (Week 16)
32. ✅ v53 → R1F migration
33. ✅ Backup/restore testing
34. ✅ Production deployment
35. ✅ Monitoring setup

---

## 📦 Dependencies Strategy

### Production
```json
{
  "@nestjs/common": "^11.0.0",
  "@nestjs/core": "^11.0.0",
  "reflect-metadata": "^0.2.2",
  "rxjs": "^7.8.1",
  
  // WhatsApp
  "baileys": "^6.7.0",        // PINNED VERSION
  
  // Database
  "better-sqlite3": "^11.6.0",
  "drizzle-orm": "^0.36.0",
  
  // Security
  "argon2": "^0.41.0",
  "uuid": "^11.0.0",
  
  // Media
  "sharp": "^0.33.5",
  "fluent-ffmpeg": "^2.1.3",
  
  // Logging
  "pino": "^9.5.0",
  
  // RPC (optional for C# engine)
  "@grpc/grpc-js": "^1.12.0",
  "@grpc/proto-loader": "^0.7.13"
}
```

### Development
```json
{
  "typescript": "^5.7.0",
  "ts-node": "^10.9.2",
  "vitest": "^2.1.0",
  "eslint": "^9.16.0",
  "drizzle-kit": "^0.28.0",
  "ts-proto": "^2.6.0"
}
```

### Version Pinning
- Lockfile WAJIB di-commit
- No floating versions untuk critical deps
- Baileys version harus stabil

---

## 🔐 Security Checklist

- [ ] Password hashing: Argon2id
- [ ] Recovery codes: hashed, one-time use
- [ ] Environment variables: never commit `.env`
- [ ] Auth sessions: separate from WhatsApp auth
- [ ] Database backups: encrypted at rest
- [ ] Audit logs: all owner actions logged
- [ ] Rate limiting: per-user, per-command
- [ ] Input validation: max length, sanitize
- [ ] SQL injection: prevented by Drizzle ORM
- [ ] XSS: escape user input in messages

---

## 📊 Performance Targets

| Operation | Target Latency |
|-----------|---------------|
| Balance check | <50ms |
| Daily claim | <100ms |
| Game (local) | <150ms |
| RPG combat | <200ms |
| Image blur | <500ms |
| Video download | async (queue) |
| DB transaction | <50ms |

### Concurrency Limits
- Max 20 concurrent heavy jobs
- Max 5 media jobs per user
- Rate limit: 20 commands/minute/user

---

## 🎯 Success Metrics

### Technical
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No TypeScript errors (strict mode)
- [ ] Lint clean
- [ ] DB foreign key checks pass
- [ ] Backup/restore works

### Functional
- [ ] Account persistence (LID↔PN↔Recovery)
- [ ] Economy rollback on failure
- [ ] Permission matrix correct
- [ ] RPG deterministic (same seed = same result)
- [ ] Game state machine correct

### User Experience
- [ ] `/m` shows clean dashboard
- [ ] No "coming soon" placeholders
- [ ] Error messages helpful
- [ ] Commands natural and short
- [ ] Profile display attractive

---

## 🔄 Migration from v53/R2

### Steps:
1. Read v53 JSON files
2. Create accounts with UUID
3. Link old identities (LID/PN)
4. Migrate profiles (XP, level, cash)
5. Migrate inventory
6. Migrate achievements
7. Verify data integrity
8. Mark as migrated
9. Keep backup of original JSON

### Rollback Plan:
- If migration fails → restore from backup
- If schema mismatch → run migration script
- If identity conflict → manual review

---

## 📝 Next Actions

1. **Setup Workspace**: Initialize monorepo with pnpm/yarn
2. **Install Dependencies**: `pnpm install`
3. **Generate Protobufs**: `pnpm proto:generate`
4. **Run Migrations**: `pnpm db:migrate`
5. **Seed Database**: Initial items, achievements, games
6. **Start Dev**: `pnpm dev`
7. **Run Tests**: `pnpm test`

Let's build! 🚀
