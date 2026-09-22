import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

// ============================================
// ACCOUNT & IDENTITY
// ============================================

export const accounts = sqliteTable('accounts', {
  id: text('id').primaryKey(), // UUID immutable
  passwordHash: text('password_hash').notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
  lastLoginAt: text('last_login_at'),
  status: text('status').notNull().default('active'), // active, banned, suspended
});

export const identities = sqliteTable('identities', {
  id: text('id').primaryKey(), // UUID
  accountId: text('account_id').notNull().references(() => accounts.id),
  type: text('type').notNull(), // whatsapp:lid, whatsapp:pn, whatsapp:old
  identifier: text('identifier').notNull(), // actual LID/PN value
  isPrimary: integer('is_primary', { mode: 'boolean' }).notNull().default(false),
  linkedAt: text('linked_at').notNull(),
  verifiedAt: text('verified_at'),
});

export const recoveryCodes = sqliteTable('recovery_codes', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  codeHash: text('code_hash').notNull(),
  used: integer('used', { mode: 'boolean' }).notNull().default(false),
  usedAt: text('used_at'),
  createdAt: text('created_at').notNull(),
});

// ============================================
// PROFILE & RANK
// ============================================

export const profiles = sqliteTable('profiles', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  displayName: text('display_name'),
  rank: text('rank').notNull().default('user'), // user, mini_owner, owner
  titleId: text('title_id'), // currently equipped title
  level: integer('level').notNull().default(1),
  xp: integer('xp').notNull().default(0),
  reputation: integer('reputation').notNull().default(0), // 0-1000
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
});

export const titles = sqliteTable('titles', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  description: text('description'),
  rarity: text('rarity').notNull().default('common'),
  unlockRequirement: text('unlock_requirement'), // achievement_id or other condition
});

export const accountTitles = sqliteTable('account_titles', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  titleId: text('title_id').notNull().references(() => titles.id),
  unlockedAt: text('unlocked_at').notNull(),
  isEquipped: integer('is_equipped', { mode: 'boolean' }).notNull().default(false),
});

// ============================================
// ECONOMY
// ============================================

export const wallets = sqliteTable('wallets', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  balance: integer('balance').notNull().default(0),
  bankBalance: integer('bank_balance').notNull().default(0),
  updatedAt: text('updated_at').notNull(),
});

export const transactions = sqliteTable('transactions', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  type: text('type').notNull(), // credit, debit
  amount: integer('amount').notNull(),
  balanceBefore: integer('balance_before').notNull(),
  balanceAfter: integer('balance_after').notNull(),
  source: text('source').notNull(), // daily, work, shop, trade, etc.
  reference: text('reference'), // game_id, item_id, etc.
  createdAt: text('created_at').notNull(),
});

// ============================================
// INVENTORY & ITEMS
// ============================================

export const items = sqliteTable('items', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  type: text('type').notNull(), // weapon, armor, accessory, consumable, material, collectible, cosmetic
  rarity: text('rarity').notNull().default('common'),
  stackLimit: integer('stack_limit').notNull().default(1),
  sellPrice: integer('sell_price').notNull().default(0),
  effects: text('effects'), // JSON string
  metadata: text('metadata'), // JSON string
});

export const inventory = sqliteTable('inventory', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  itemId: text('item_id').notNull().references(() => items.id),
  quantity: integer('quantity').notNull().default(1),
  acquiredAt: text('acquired_at').notNull(),
  metadata: text('metadata'), // JSON for equipment stats, etc.
});

// ============================================
// PROGRESSION: QUEST, ACHIEVEMENT, SEASON
// ============================================

export const quests = sqliteTable('quests', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  description: text('description'),
  type: text('type').notNull(), // daily, weekly, story
  objective: text('objective').notNull(), // JSON: { type: 'kill', target: 'boss_x', count: 5 }
  rewardXp: integer('reward_xp').notNull().default(0),
  rewardCash: integer('reward_cash').notNull().default(0),
  rewardItemId: text('reward_item_id'),
  rewardItemQuantity: integer('reward_item_quantity').default(1),
});

export const accountQuests = sqliteTable('account_quests', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  questId: text('quest_id').notNull().references(() => quests.id),
  progress: integer('progress').notNull().default(0),
  completed: integer('completed', { mode: 'boolean' }).notNull().default(false),
  claimedAt: text('claimed_at'),
  expiresAt: text('expires_at'),
  startedAt: text('started_at').notNull(),
});

export const achievements = sqliteTable('achievements', {
  id: text('id').primaryKey(),
  namespace: text('namespace').notNull(), // universal, game, fishing, mining, etc.
  name: text('name').notNull(),
  description: text('description'),
  requirement: text('requirement').notNull(), // JSON condition
  rewardXp: integer('reward_xp').notNull().default(0),
  rewardCash: integer('reward_cash').notNull().default(0),
  rewardTitleId: text('reward_title_id'),
});

export const accountAchievements = sqliteTable('account_achievements', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  achievementId: text('achievement_id').notNull().references(() => achievements.id),
  completedAt: text('completed_at').notNull(),
  claimedAt: text('claimed_at'),
});

export const seasons = sqliteTable('seasons', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  startDate: text('start_date').notNull(),
  endDate: text('end_date').notNull(),
  isActive: integer('is_active', { mode: 'boolean' }).notNull().default(false),
});

export const seasonProgress = sqliteTable('season_progress', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  seasonId: text('season_id').notNull().references(() => seasons.id),
  tier: integer('tier').notNull().default(1),
  progress: integer('progress').notNull().default(0),
  maxProgress: integer('max_progress').notNull(),
});

// ============================================
// RPG
// ============================================

export const rpgProfiles = sqliteTable('rpg_profiles', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  class: text('class').notNull().default('warrior'), // warrior, rogue, mage
  hp: integer('hp').notNull().default(100),
  maxHp: integer('max_hp').notNull().default(100),
  atk: integer('atk').notNull().default(10),
  def: integer('def').notNull().default(5),
  crit: integer('crit').notNull().default(5),
  luck: integer('luck').notNull().default(5),
  weaponId: text('weapon_id'),
  armorId: text('armor_id'),
  accessoryId: text('accessory_id'),
  updatedAt: text('updated_at').notNull(),
});

export const skills = sqliteTable('skills', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  category: text('category').notNull(), // combat, defense, luck
  tier: text('tier').notNull().default('I'), // I, II, III
  prerequisiteSkillId: text('prerequisite_skill_id'),
  cost: integer('cost').notNull(),
  effect: text('effect').notNull(), // JSON: { type: 'atk_bonus', value: 5 }
});

export const accountSkills = sqliteTable('account_skills', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  skillId: text('skill_id').notNull().references(() => skills.id),
  level: integer('level').notNull().default(1),
  unlockedAt: text('unlocked_at').notNull(),
});

// ============================================
// GAMES
// ============================================

export const games = sqliteTable('games', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  type: text('type').notNull(), // slot, rps, hangman, etc.
  minBet: integer('min_bet').notNull().default(0),
  maxBet: integer('max_bet').notNull().default(10000),
  enabled: integer('enabled', { mode: 'boolean' }).notNull().default(true),
});

export const gameSessions = sqliteTable('game_sessions', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  gameId: text('game_id').notNull().references(() => games.id),
  groupId: text('group_id'), // for group games
  state: text('state').notNull().default('idle'), // idle, active, waiting_input, resolved, reward, closed
  betAmount: integer('bet_amount').notNull().default(0),
  gameState: text('game_state'), // JSON game-specific state
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
  completedAt: text('completed_at'),
});

export const gameResults = sqliteTable('game_results', {
  id: text('id').primaryKey(),
  sessionId: text('session_id').notNull().references(() => gameSessions.id),
  accountId: text('account_id').notNull().references(() => accounts.id),
  result: text('result').notNull(), // win, lose, draw
  reward: integer('reward').notNull().default(0),
  createdAt: text('created_at').notNull(),
});

// ============================================
// GROUP & PERMISSIONS
// ============================================

export const groups = sqliteTable('groups', {
  id: text('id').primaryKey(), // group JID
  name: text('name'),
  settings: text('settings'), // JSON: { announcements, locked, etc. }
  createdAt: text('created_at').notNull(),
});

export const groupPermissions = sqliteTable('group_permissions', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  groupId: text('group_id').notNull().references(() => groups.id),
  permission: text('permission').notNull(), // group.kick, group.add, etc.
  grantedBy: text('granted_by').notNull(),
  grantedAt: text('granted_at').notNull(),
  expiresAt: text('expires_at'),
});

export const miniOwners = sqliteTable('mini_owners', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  groupId: text('group_id').notNull().references(() => groups.id),
  plan: text('plan').notNull(), // basic, premium, etc.
  startedAt: text('started_at').notNull(),
  expiresAt: text('expires_at'),
  permissions: text('permissions'), // JSON array of permission nodes
});

// ============================================
// EVENTS & LOGS
// ============================================

export const eventLog = sqliteTable('event_log', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  eventType: text('event_type').notNull(), // game.win, daily.claimed, boss.defeated, etc.
  eventData: text('event_data'), // JSON payload
  processedAt: text('processed_at').notNull(),
  createdAt: text('created_at').notNull(),
});

export const idempotencyKeys = sqliteTable('idempotency_keys', {
  id: text('id').primaryKey(),
  key: text('key').notNull().unique(),
  accountId: text('account_id').notNull().references(() => accounts.id),
  operation: text('operation').notNull(),
  result: text('result'), // JSON result
  createdAt: text('created_at').notNull(),
  expiresAt: text('expires_at').notNull(),
});
