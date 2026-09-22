/**
 * CINNAMON R1F - Baileys Bridge (Node.js)
 * Connects Python orchestrator to WhatsApp via Baileys
 */

const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

// Get session path from command line
const sessionPath = process.argv[2] || './data/sessions';

// Ensure session directory exists
if (!fs.existsSync(sessionPath)) {
    fs.mkdirSync(sessionPath, { recursive: true });
}

let sock;
let isConnected = false;

// Read commands from stdin
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

process.stdin.setEncoding('utf8');

function sendToPython(message) {
    console.log(JSON.stringify(message));
}

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
    
    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false, // We'll send QR to Python
        browser: ['Cinnamon R1F', 'Chrome', '120.0.0']
    });
    
    sock.ev.on('creds.update', saveCreds);
    
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            // Send QR code to Python for display
            sendToPython({ type: 'qr', qr: qr });
        }
        
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            
            if (shouldReconnect) {
                sendToPython({ type: 'disconnected', reason: 'Connection closed, reconnecting...' });
                setTimeout(connectToWhatsApp, 1000);
            } else {
                sendToPython({ type: 'error', error: 'Logged out. Please scan QR again.' });
            }
        } else if (connection === 'open') {
            isConnected = true;
            sendToPython({ type: 'connected' });
        }
    });
    
    sock.ev.on('messages.upsert', async (m) => {
        const messages = m.messages;
        if (!messages.length) return;
        
        const msg = messages[0];
        if (!msg.message) return;
        
        // Extract message data
        const chatId = msg.key.remoteJid;
        const senderId = msg.key.participant || msg.key.remoteJid;
        const messageText = msg.message.conversation || 
                           msg.message.extendedTextMessage?.text || '';
        
        if (messageText) {
            sendToPython({
                type: 'message',
                data: {
                    chatId,
                    senderId,
                    text: messageText,
                    timestamp: msg.messageTimestamp,
                    isGroup: chatId.endsWith('@g.us')
                }
            });
        }
    });
}

// Handle commands from Python
process.stdin.on('data', async (data) => {
    try {
        const command = JSON.parse(data.trim());
        
        if (command.action === 'send' && sock && isConnected) {
            await sock.sendMessage(command.to, { text: command.text });
            sendToPython({ type: 'sent', id: command.to });
        } else if (command.action === 'send_media' && sock && isConnected) {
            const mediaBuffer = fs.readFileSync(command.media_path);
            await sock.sendMessage(command.to, { 
                image: mediaBuffer, 
                caption: command.caption 
            });
            sendToPython({ type: 'sent_media', id: command.to });
        }
    } catch (error) {
        sendToPython({ type: 'error', error: error.message });
    }
});

// Start connection
connectToWhatsApp().catch(error => {
    sendToPython({ type: 'error', error: error.message });
});
