#!/usr/bin/env python3
"""
CINNAMON R1F - Main Orchestrator
Release 1 Finale - WhatsApp Bot Ecosystem

This is the main entry point that orchestrates:
- WhatsApp connection (via Baileys adapter)
- Command routing
- Feature modules
- Database connections
- Event handling
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cinnamon.log')
    ]
)
logger = logging.getLogger('CinnamonR1F')

class CinnamonOrchestrator:
    """Main orchestrator for Cinnamon R1F bot"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / 'data'
        self.sessions_dir = self.data_dir / 'sessions'
        self.backups_dir = self.data_dir / 'backups'
        self.media_dir = self.data_dir / 'media'
        
        # Ensure directories exist
        self._ensure_directories()
        
        # State
        self.is_running = False
        self.whatsapp_adapter = None
        self.command_router = None
        self.database = None
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.data_dir, self.sessions_dir, 
                         self.backups_dir, self.media_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Directories initialized")
    
    async def initialize(self):
        """Initialize all core components"""
        logger.info("🍂 CINNAMON R1F - Initializing...")
        
        try:
            # Initialize database
            from src.core.database import DatabaseManager
            self.database = DatabaseManager(self.data_dir / 'cinnamon.db')
            await self.database.connect()
            logger.info("✓ Database connected")
            
            # Initialize WhatsApp adapter
            from src.adapters.whatsapp_adapter import WhatsAppAdapter
            self.whatsapp_adapter = WhatsAppAdapter(
                session_path=self.sessions_dir,
                event_handler=self.handle_message
            )
            logger.info("✓ WhatsApp adapter ready")
            
            # Initialize command router
            from src.core.command_router import CommandRouter
            self.command_router = CommandRouter()
            await self.command_router.load_features()
            logger.info("✓ Command router loaded")
            
            logger.info("✅ CINNAMON R1F initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    async def handle_message(self, message_data):
        """Handle incoming WhatsApp messages"""
        try:
            # Route message to appropriate handler
            await self.command_router.route(message_data)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def start(self):
        """Start the bot"""
        if not await self.initialize():
            logger.error("Failed to initialize. Exiting.")
            return
        
        self.is_running = True
        logger.info("🚀 Starting WhatsApp connection...")
        
        try:
            # Connect to WhatsApp
            await self.whatsapp_adapter.connect()
            logger.info("✅ BOT IS ONLINE AND READY")
            
            # Keep running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  Shutdown signal received")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down CINNAMON R1F...")
        self.is_running = False
        
        # Cleanup
        if self.whatsapp_adapter:
            await self.whatsapp_adapter.disconnect()
        
        if self.database:
            await self.database.disconnect()
        
        logger.info("✅ Shutdown complete. Goodbye!")

def main():
    """Main entry point"""
    orchestrator = CinnamonOrchestrator()
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(orchestrator.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == '__main__':
    main()
