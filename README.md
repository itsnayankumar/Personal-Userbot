# ⚡ Pro Max Telegram Userbot
# ⚡ Evergreen Pro Max Userbot

A highly customized, 24/7 Telegram userbot featuring a real-time web dashboard. Built with Pyrogram and Flask, ready for Render deployment.
A highly customized, 24/7 Telegram userbot featuring a secure web dashboard, server monitoring, and advanced background utilities. Built for Render and VPS environments.

## Features
- **Live Web Dashboard:** Real-time stats and single-click toggles.
- **Deep Focus Mode:** Auto-replies and mutes for heavy study sessions.
- **AFK Gaming Mode:** Instantly lets people know when you're in a ranked match.
- **Library Tracker:** Commands to instantly count scraped files.
- **Custom Shortcuts:** `.lk` instantly formats and pushes links to leech bots.
- **Ghost Purge:** Instantly clean up chat histories via `.purge`.
- **Secure Web Dashboard:** Password-protected panel for toggling modes.
- **Code Flow State:** Instantly blocks distractions with auto-replies while coding.
- **Ghost Logger (Anti-Delete):** Silently intercepts and caches private deleted messages, safely forwarding them to a private log channel with flood-wait protection.
- **Server Health Matrix (`.sys`):** Live terminal readouts for CPU, RAM, and Disk space.
- **Voice Note Whisperer (`.vt`):** Background FFmpeg engine to download and transcribe `.ogg` voice notes.
- **Stremio Pipeline (`.lkm` / `.lks`):** Instantly structures links and forwards them silently to your leech bot without opening the PM.
- **Python Terminal (`.eval`):** Run raw Python code directly inside any Telegram chat.

## Setup on Render
1. Fork or push this repository to GitHub.
2. Create a new Web Service on Render and connect the repo.
3. Set the Build Command: `pip install -r requirements.txt`
4. Set the Start Command: `python app.py`
5. Add `API_ID`, `API_HASH`, and `SESSION_STRING` to the Environment Variables.
## Deployment Requirements
Make sure to add `LOG_CHANNEL_ID` to your environment variables before deploying!
### 🧠 AI & Utilities
* **🌐 Flask Web Dashboard:** A live, secure HTML dashboard tracking uptime, scrape stats, and active AFK toggles.
* **🔓 Restricted Content Downloader (`.dl`):** Bypasses Telegram channel restrictions, downloads blocked media, and uploads it safely to your personal cloud.
* **🖥️ System Matrix (`.sys`):** Live monitoring of CPU, RAM, and Disk space via `psutil`.

## ⚙️ Quick Setup

1. Configure your API IDs and database variables in `config.py`.
2. Install the necessary Python dependencies:
   ```bash
   pip install pyrogram tgcrypto flask psutil speechrecognition pydub pillow deep-translator pytesseract requests aiohttp beautifulsoup4
