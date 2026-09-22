import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const DATA_DIR = join(process.cwd(), 'data');

// Ensure data directory exists
if (!existsSync(DATA_DIR)) {
  mkdirSync(DATA_DIR, { recursive: true });
}

const DB_PATH = join(DATA_DIR, 'cinnamon.db');

// Create database connection with optimal settings for durability
const sqlite = new Database(DB_PATH);

// Enable WAL mode for better concurrency
sqlite.pragma('journal_mode = WAL');

// Enable foreign keys
sqlite.pragma('foreign_keys = ON');

// Set busy timeout to handle concurrent access
sqlite.pragma('busy_timeout = 5000');

// Synchronous mode for durability (can adjust to NORMAL for performance)
sqlite.pragma('synchronous = FULL');

export const db = drizzle(sqlite, { schema });

export function getDb() {
  return db;
}

export function getSqlite() {
  return sqlite;
}

export function closeDb() {
  sqlite.close();
}

export function runMigrations() {
  // Migrations are handled by drizzle-kit
  // This function can be used for manual migration if needed
  console.log('Database initialized at', DB_PATH);
}

// Initialize tables based on schema
export function initializeTables() {
  const sqlStatements = [
    `CREATE TABLE IF NOT EXISTS accounts (
      id TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_login_at TEXT,
      status TEXT NOT NULL DEFAULT 'active'
    )`,
    
    `CREATE TABLE IF NOT EXISTS identities (
      id TEXT PRIMARY KEY,
      account_id TEXT NOT NULL REFERENCES accounts(id),
      type TEXT NOT NULL,
      identifier TEXT NOT NULL,
      is_primary INTEGER NOT NULL DEFAULT 0,
      linked_at TEXT NOT NULL,
      verified_at TEXT
    )`,
    
    `CREATE TABLE IF NOT EXISTS recovery_codes (
      id TEXT PRIMARY KEY,
      account_id TEXT NOT NULL REFERENCES accounts(id),
      code_hash TEXT NOT NULL,
      used INTEGER NOT NULL DEFAULT 0,
      used_at TEXT,
      created_at TEXT NOT NULL
    )`,
    
    `CREATE TABLE IF NOT EXISTS profiles (
      id TEXT PRIMARY KEY,
      account_id TEXT NOT NULL REFERENCES accounts(id),
      display_name TEXT,
      rank TEXT NOT NULL DEFAULT 'user',
      title_id TEXT,
      level INTEGER NOT NULL DEFAULT 1,
      xp INTEGER NOT NULL DEFAULT 0,
      reputation INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )`,
    
    `CREATE TABLE IF NOT EXISTS wallets (
      id TEXT PRIMARY KEY,
      account_id TEXT NOT NULL REFERENCES accounts(id),
      balance INTEGER NOT NULL DEFAULT 0,
      bank_balance INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL
    )`,
    
    `CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)`,
    `CREATE INDEX IF NOT EXISTS idx_identities_account_id ON identities(account_id)`,
    `CREATE INDEX IF NOT EXISTS idx_identities_identifier ON identities(identifier)`,
    `CREATE INDEX IF NOT EXISTS idx_profiles_account_id ON profiles(account_id)`,
    `CREATE INDEX IF NOT EXISTS idx_wallets_account_id ON wallets(account_id)`,
  ];

  for (const stmt of sqlStatements) {
    sqlite.exec(stmt);
  }

  console.log('Tables initialized successfully');
}
