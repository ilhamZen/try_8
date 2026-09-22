"""
CINNAMON R1F - Command Router
Routes incoming messages to appropriate feature handlers
"""

import logging
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger('CinnamonR1F.CommandRouter')

@dataclass
class MessageContext:
    """Context for incoming message"""
    chat_id: str
    sender_id: str
    text: str
    timestamp: int
    is_group: bool

class CommandRouter:
    """Routes commands to feature handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.features_loaded = False
        
    async def load_features(self):
        """Load all feature handlers"""
        logger.info("Loading feature handlers...")
        
        # Register core commands
        self.register_handler('start', self.handle_start)
        self.register_handler('help', self.handle_help)
        self.register_handler('ping', self.handle_ping)
        self.register_handler('register', self.handle_register)
        self.register_handler('login', self.handle_login)
        self.register_handler('whoami', self.handle_whoami)
        self.register_handler('profile', self.handle_profile)
        self.register_handler('balance', self.handle_balance)
        self.register_handler('daily', self.handle_daily)
        
        self.features_loaded = True
        logger.info(f"✓ Loaded {len(self.handlers)} command handlers")
    
    def register_handler(self, command: str, handler: Callable):
        """Register a command handler"""
        self.handlers[command.lower()] = handler
        logger.debug(f"Registered handler: /{command}")
    
    async def route(self, message_data: Dict[str, Any]):
        """Route message to appropriate handler"""
        if not self.features_loaded:
            logger.warning("Features not loaded yet")
            return
        
        try:
            # Parse message
            ctx = MessageContext(
                chat_id=message_data['chatId'],
                sender_id=message_data['senderId'],
                text=message_data['text'],
                timestamp=message_data['timestamp'],
                is_group=message_data.get('isGroup', False)
            )
            
            # Extract command
            if not ctx.text.startswith('/'):
                return  # Not a command
            
            parts = ctx.text[1:].strip().split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Find handler
            handler = self.handlers.get(command)
            
            if handler:
                logger.info(f"Executing command: /{command}")
                await handler(ctx, args)
            else:
                logger.warning(f"Unknown command: /{command}")
                # TODO: Send error message to user
                
        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
    
    # Core Command Handlers
    
    async def handle_start(self, ctx: MessageContext, args: list):
        """Handle /start command"""
        response = """
🍂 *CINNAMON R1F* - Release 1 Finale

Welcome! I'm your WhatsApp ecosystem bot.

Use /help to see available commands.
Use /register to create your account.
        """.strip()
        await self._send_message(ctx.chat_id, response)
    
    async def handle_help(self, ctx: MessageContext, args: list):
        """Handle /help command"""
        response = """
*Available Commands:*

*Core:*
/start - Start the bot
/help - Show this help
/ping - Check bot status

*Account:*
/register - Create new account
/login - Login to your account
/whoami - Show current account
/profile - View your profile

*Economy:*
/balance - Check your balance
/daily - Claim daily reward

More commands coming soon!
        """.strip()
        await self._send_message(ctx.chat_id, response)
    
    async def handle_ping(self, ctx: MessageContext, args: list):
        """Handle /ping command"""
        await self._send_message(ctx.chat_id, "🏓 Pong! Bot is online.")
    
    async def handle_register(self, ctx: MessageContext, args: list):
        """Handle /register command"""
        # TODO: Implement registration with database
        response = "🔧 Registration system under construction.\n\nThis will create your permanent account with UUID."
        await self._send_message(ctx.chat_id, response)
    
    async def handle_login(self, ctx: MessageContext, args: list):
        """Handle /login command"""
        response = "🔧 Login system under construction."
        await self._send_message(ctx.chat_id, response)
    
    async def handle_whoami(self, ctx: MessageContext, args: list):
        """Handle /whoami command"""
        response = "🔧 Identity resolution under construction.\n\nThis will show your linked account."
        await self._send_message(ctx.chat_id, response)
    
    async def handle_profile(self, ctx: MessageContext, args: list):
        """Handle /profile command"""
        response = "🔧 Profile viewer under construction."
        await self._send_message(ctx.chat_id, response)
    
    async def handle_balance(self, ctx: MessageContext, args: list):
        """Handle /balance command"""
        response = "🔧 Economy system under construction."
        await self._send_message(ctx.chat_id, response)
    
    async def handle_daily(self, ctx: MessageContext, args: list):
        """Handle /daily command"""
        response = "🔧 Daily rewards under construction."
        await self._send_message(ctx.chat_id, response)
    
    async def _send_message(self, chat_id: str, text: str):
        """Send message via WhatsApp adapter"""
        # This will be called by orchestrator
        logger.info(f"Sending to {chat_id}: {text[:50]}...")
        # TODO: Integrate with WhatsAppAdapter from orchestrator
