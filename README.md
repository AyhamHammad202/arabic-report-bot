# بوت تسليم تقارير مادة اللغة العربية
### Arabic Language Report Submission Telegram Bot

A production-ready Telegram bot built with **aiogram 3.x** and **aiosqlite** that collects Arabic language reports from students at two specific colleges and forwards them to the professor (admin) with full statistics and department browsing.

---

## 📁 Project Structure

```
Arabic/
├── main.py             # Entry point — starts the bot
├── config.py           # Env variables, college & department constants
├── database.py         # All async SQLite operations
├── keyboards.py        # Inline keyboard builders
├── states.py           # FSM state definitions
├── handlers/
│   ├── __init__.py     # Exports both routers
│   ├── student.py      # Student submission flow
│   └── admin.py        # Admin panel & commands
├── requirements.txt    # Python dependencies
├── .env.example        # Template — copy to .env and fill in
├── .gitignore
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram numeric user ID (get it from [@userinfobot](https://t.me/userinfobot))

### 2. Create a Virtual Environment (recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy the template
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux
```

Then open `.env` and fill in your values:
```env
BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMIN_ID=123456789
```

### 5. Run the Bot
```bash
python main.py
```

You should see:
```
2026-05-31 14:00:00 | INFO     | database | Database initialised at 'reports.db'.
2026-05-31 14:00:00 | INFO     | __main__ | Bot is starting up…
```

---

## 🤖 Bot Features

### Student Flow
| Step | Action |
|------|--------|
| `/start` | Bot greets student, asks for full name |
| Name input | Bot shows college selection keyboard |
| College selected | Bot shows department keyboard for that college |
| Department selected | Bot asks to upload PDF report |
| PDF uploaded | ✅ Saved to DB, student confirmed, admin notified |

### Admin Panel (`/admin`)
| Feature | Description |
|---------|-------------|
| 📊 الإحصائيات | Shows submission count per department and total |
| 📁 استعراض الأقسام | Browse any department and receive all its PDFs |

---

## 🔒 Security Notes

- The `.env` file is **never committed** (protected by `.gitignore`).
- Admin commands are protected by `ADMIN_ID` — any other user gets a rejection message.
- FSM states prevent students from skipping steps.

---

## 🛠 Customisation

- **Add more departments**: Edit the `DEPARTMENTS` dict in `config.py`.
- **Persistent FSM across restarts**: Replace `MemoryStorage()` in `main.py` with `RedisStorage`.
- **Production deployment**: Use `systemd`, `Docker`, or a cloud VM. Set a webhook instead of polling for better performance.
