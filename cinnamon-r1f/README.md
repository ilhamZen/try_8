# 🍂 CINNAMON R1F - Release 1 Finale

WhatsApp Bot Ecosystem dengan Python Orchestrator + Node.js Baileys Bridge

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (untuk Baileys bridge)
npm install
```

### 2. Jalankan Bot

```bash
python orkestrator.py
```

Bot akan:
- Membuat database SQLite otomatis
- Menampilkan QR code untuk scan WhatsApp
- Mulai mendengarkan pesan

## 📁 Struktur Project

```
cinnamon-r1f/
├── orkestrator.py          # Main Python orchestrator
├── package.json            # Node.js dependencies
├── requirements.txt        # Python dependencies
├── src/
│   ├── adapters/
│   │   ├── whatsapp_adapter.py    # Python WhatsApp adapter
│   │   └── baileys_bridge.js      # Node.js Baileys bridge
│   ├── core/
│   │   ├── database.py            # SQLite database manager
│   │   └── command_router.py      # Command routing system
│   └── utils/
└── data/
    ├── sessions/           # WhatsApp session files
    ├── backups/            # Database backups
    ├── media/              # Media files
    └── cinnamon.db         # SQLite database
```

## 🔧 Arsitektur

```
┌─────────────────┐
│   Python        │
│  Orchestrator   │
│                 │
│  - Database     │
│  - Commands     │
│  - Features     │
└────────┬────────┘
         │ IPC (stdin/stdout)
         │ JSON messages
┌────────▼────────┐
│  Node.js        │
│  Baileys Bridge │
│                 │
│  - WhatsApp     │
│  - Messages     │
│  - Media        │
└────────┬────────┘
         │
┌────────▼────────┐
│   WhatsApp      │
│   Servers       │
└─────────────────┘
```

## 📝 Commands Tersedia

- `/start` - Mulai bot
- `/help` - Tampilkan bantuan
- `/ping` - Cek status bot
- `/register` - Buat akun baru
- `/login` - Login ke akun
- `/whoami` - Lihat akun saat ini
- `/profile` - Lihat profil
- `/balance` - Cek saldo
- `/daily` - Klaim reward harian

## 🎯 Fitur Utama (Coming Soon)

- ✅ Account permanence dengan UUID
- ✅ Identity linking (LID/PN)
- ✅ Transaction ledger dengan audit trail
- 🔄 Economy system
- 🔄 RPG engine
- 🔄 Games collection
- 🔄 Group admin tools
- 🔄 Media processing

## 📄 License

Apache 2.0
