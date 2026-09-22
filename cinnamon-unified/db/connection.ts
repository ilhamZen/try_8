import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import * as schema from './schema';
import { ensureDir } from 'fs/promises';
import { dirname } from 'path';

const DB_PATH = process.env.DATABASE_PATH || './data/cinnamon.db';

let db: ReturnType<typeof drizzle> | null = null;

export async function initDatabase(): Promise<ReturnType<typeof drizzle>> {
  if (db) return db;

  // Ensure directory exists
  await ensureDir(dirname(DB_PATH));

  const sqlite = new Database(DB_PATH);
  
  // Enable WAL mode for better performance
  sqlite.pragma('journal_mode = WAL');
  
  // Enable foreign keys
  sqlite.pragma('foreign_keys = ON');
  
  // Set busy timeout
  sqlite.pragma('busy_timeout = 5000');
  
  // Synchronous mode for durability
  sqlite.pragma('synchronous = NORMAL');

  db = drizzle(sqlite, { schema });
  
  return db;
}

export function getDatabase(): ReturnType<typeof drizzle> {
  if (!db) {
    throw new Error('Database not initialized. Call initDatabase() first.');
  }
  return db;
}

export function closeDatabase(): void {
  if (db) {
    const sqlite = (db as any).database as Database.Database;
    sqlite.close();
    db = null;
  }
}

export default { initDatabase, getDatabase, closeDatabase };
