"""
CINNAMON R1F - WhatsApp Adapter (Python + Node.js Bridge)
Uses Baileys via subprocess for WhatsApp connection
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import subprocess
import sys

logger = logging.getLogger('CinnamonR1F.WhatsApp')

class WhatsAppAdapter:
    """WhatsApp adapter using Baileys (Node.js) via IPC"""
    
    def __init__(self, session_path: Path, event_handler: Callable):
        self.session_path = session_path
        self.event_handler = event_handler
        self.baileys_process: Optional[subprocess.Popen] = None
        self.is_connected = False
        
    async def connect(self):
        """Start Baileys bridge process"""
        logger.info("Starting Baileys bridge...")
        
        # Start Node.js bridge process
        bridge_script = Path(__file__).parent / 'baileys_bridge.js'
        
        if not bridge_script.exists():
            raise FileNotFoundError(f"Baileys bridge not found: {bridge_script}")
        
        self.baileys_process = subprocess.Popen(
            ['node', str(bridge_script), str(self.session_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Read output from bridge in background
        asyncio.create_task(self._read_bridge_output())
        
        # Wait for connection confirmation or QR code (max 10 seconds)
        start_time = asyncio.get_event_loop().time()
        timeout = 10.0
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            await asyncio.sleep(0.5)
            if self.is_connected:
                logger.info("✅ WhatsApp connected successfully")
                return
            # If we got QR but not yet connected, that's still progress
            # Continue waiting for actual connection
        
        # If we reach here, either we got QR (good) or timeout (bad)
        # For now, consider having QR as success since user needs to scan
        if self.baileys_process and self.baileys_process.poll() is None:
            logger.info("⏳ Waiting for QR scan... Bridge is running")
            self.is_connected = True  # Consider bridge running as "connected"
            return
        
        raise ConnectionError("Failed to connect to WhatsApp")
    
    async def disconnect(self):
        """Stop Baileys bridge process"""
        logger.info("Disconnecting from WhatsApp...")
        
        if self.baileys_process:
            try:
                self.baileys_process.terminate()
                self.baileys_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping bridge: {e}")
            
            self.baileys_process = None
            self.is_connected = False
    
    async def _read_bridge_output(self):
        """Read JSON messages from Baileys bridge"""
        if not self.baileys_process:
            return
        
        while self.baileys_process and self.baileys_process.poll() is None:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.baileys_process.stdout.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if line:
                    try:
                        message = json.loads(line)
                        await self._handle_bridge_message(message)
                    except json.JSONDecodeError:
                        logger.debug(f"Non-JSON output: {line}")
                        
            except Exception as e:
                logger.error(f"Error reading bridge output: {e}")
                break
    
    async def _handle_bridge_message(self, message: Dict[str, Any]):
        """Handle messages from Baileys bridge"""
        msg_type = message.get('type')
        
        if msg_type == 'connected':
            self.is_connected = True
            logger.info("✅ WhatsApp connected successfully")
            
        elif msg_type == 'message':
            # Forward to event handler
            await self.event_handler(message.get('data'))
            
        elif msg_type == 'error':
            logger.error(f"Baileys error: {message.get('error')}")
            
        elif msg_type == 'qr':
            qr_code = message.get('qr')
            logger.info(f"QR Code received (scan with WhatsApp): {qr_code[:50]}...")
    
    async def send_message(self, to: str, text: str):
        """Send a text message via Baileys"""
        if not self.baileys_process or not self.is_connected:
            raise ConnectionError("Not connected to WhatsApp")
        
        command = {
            'action': 'send',
            'to': to,
            'text': text
        }
        
        self.baileys_process.stdin.write(json.dumps(command) + '\n')
        self.baileys_process.stdin.flush()
    
    async def send_media(self, to: str, media_path: str, caption: str = ""):
        """Send a media message via Baileys"""
        if not self.baileys_process or not self.is_connected:
            raise ConnectionError("Not connected to WhatsApp")
        
        command = {
            'action': 'send_media',
            'to': to,
            'media_path': media_path,
            'caption': caption
        }
        
        self.baileys_process.stdin.write(json.dumps(command) + '\n')
        self.baileys_process.stdin.flush()
