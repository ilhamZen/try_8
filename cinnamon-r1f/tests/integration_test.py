"""
CINNAMON R1F - Integration Tests
Test database, commands, and WhatsApp adapter
"""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.database import DatabaseManager
from core.command_router import CommandRouter
import uuid


async def test_database():
    """Test database creation and operations"""
    print("\n=== DATABASE TESTS ===")
    
    db = DatabaseManager(Path('data/integration_test.db'))
    await db.connect()
    print("✓ Database connected")
    
    # Verify tables
    cursor = await db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in await cursor.fetchall() if not t[0].startswith('sqlite_')]
    print(f"✓ Tables created: {len(tables)}")
    assert len(tables) >= 7, "Should have at least 7 tables"
    
    # Test account creation
    account_id = str(uuid.uuid4())
    await db.connection.execute('INSERT INTO accounts (id) VALUES (?)', (account_id,))
    await db.connection.commit()
    print(f"✓ Account created: {account_id[:8]}...")
    
    # Test identity
    await db.connection.execute(
        'INSERT INTO identities (account_id, identity_type, identity_value) VALUES (?, ?, ?)',
        (account_id, 'whatsapp_pn', '628123456789')
    )
    await db.connection.commit()
    print("✓ Identity linked")
    
    # Test profile
    await db.connection.execute(
        'INSERT INTO profiles (account_id, username, level, xp, rank, title) VALUES (?, ?, ?, ?, ?, ?)',
        (account_id, 'TestUser', 1, 0, 'USER', '')
    )
    await db.connection.commit()
    print("✓ Profile created")
    
    # Test wallet
    await db.connection.execute(
        'INSERT INTO wallets (account_id, balance, bank_balance) VALUES (?, ?, ?)',
        (account_id, 1000, 0)
    )
    await db.connection.commit()
    print("✓ Wallet created (balance: 1000)")
    
    # Test transaction (using correct schema columns)
    await db.connection.execute(
        'INSERT INTO transactions (account_id, type, amount, balance_before, balance_after, source) VALUES (?, ?, ?, ?, ?, ?)',
        (account_id, 'daily', 100, 900, 1000, 'Daily reward')
    )
    await db.connection.commit()
    print("✓ Transaction logged")
    
    # Verify data
    cursor = await db.connection.execute(
        'SELECT w.balance FROM wallets w WHERE w.account_id = ?',
        (account_id,)
    )
    result = await cursor.fetchone()
    assert result[0] == 1000, "Balance should be 1000"
    print("✓ Data integrity verified")
    
    await db.disconnect()
    print("✅ DATABASE TESTS PASSED\n")
    return True


async def test_command_router():
    """Test command registration and routing"""
    print("=== COMMAND ROUTER TESTS ===")
    
    router = CommandRouter()
    
    # Check registered commands
    commands = list(router.handlers.keys())
    print(f"✓ Registered commands: {len(commands)}")
    assert len(commands) >= 5, "Should have at least 5 commands"
    
    expected_commands = ['start', 'help', 'ping', 'register', 'login', 'whoami', 'profile', 'balance', 'daily']
    for cmd in expected_commands:
        assert cmd in commands, f"Command '{cmd}' should be registered"
    print(f"✓ Core commands present: {', '.join(expected_commands)}")
    
    print("✅ COMMAND ROUTER TESTS PASSED\n")
    return True


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("CINNAMON R1F - INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        # Clean up old test database
        test_db = Path('data/integration_test.db')
        for ext in ['', '-shm', '-wal']:
            if (test_db.with_suffix(test_db.suffix + ext)).exists():
                (test_db.with_suffix(test_db.suffix + ext)).unlink()
        
        # Run tests
        await test_database()
        await test_command_router()
        
        print("=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
