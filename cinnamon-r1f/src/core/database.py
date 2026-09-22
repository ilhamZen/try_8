"""
CINNAMON R1F - Database Manager
SQLite database with async support via aiosqlite
"""

import aiosqlite
from pathlib import Path
from typing import Optional, Any, List, Dict
import logging

logger = logging.getLogger('CinnamonR1F.Database')

class DatabaseManager:
    """Async SQLite database manager"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        
    async def connect(self):
        """Establish database connection"""
        self.connection = await aiosqlite.connect(str(self.db_path))
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute("PRAGMA foreign_keys=ON")
        await self.connection.commit()
        await self._create_tables()
        logger.info(f"Database connected: {self.db_path}")
    
    async def disconnect(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database disconnected")
    
    async def _create_tables(self):
        """Create core tables if they don't exist"""
        await self.connection.executescript("""
            -- Accounts table (permanent UUID)
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_hash TEXT,
                recovery_codes_hash TEXT
            );
            
            -- Identities table (LID/PN links)
            CREATE TABLE IF NOT EXISTS identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                identity_type TEXT NOT NULL,
                identity_value TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- Profiles table
            CREATE TABLE IF NOT EXISTS profiles (
                account_id TEXT PRIMARY KEY,
                username TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                rank TEXT DEFAULT 'USER',
                title TEXT,
                reputation INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- Wallets table (economy)
            CREATE TABLE IF NOT EXISTS wallets (
                account_id TEXT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                bank_balance INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- Transactions ledger (audit trail)
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                balance_before INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                source TEXT,
                reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- Inventory table
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                metadata TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- RPG Stats table
            CREATE TABLE IF NOT EXISTS rpg_stats (
                account_id TEXT PRIMARY KEY,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                defense INTEGER DEFAULT 5,
                crit_chance REAL DEFAULT 0.05,
                luck INTEGER DEFAULT 10,
                class TEXT DEFAULT 'Warrior',
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_identities_account ON identities(account_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_inventory_account ON inventory(account_id);
        """)
        await self.connection.commit()
        logger.info("✓ Database tables created")
    
    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a single query"""
        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one row"""
        self.connection.row_factory = aiosqlite.Row
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        self.connection.row_factory = aiosqlite.Row
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def begin_transaction(self):
        """Begin a transaction"""
        await self.connection.execute("BEGIN")
    
    async def commit(self):
        """Commit transaction"""
        await self.connection.commit()
    
    async def rollback(self):
        """Rollback transaction"""
        await self.connection.rollback()
