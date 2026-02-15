# ⚡ Pro Max Userbot Engine

A powerful, multi-threaded Pyrogram Userbot integrated with an automated scraping daemon, Flask command center, and custom Python utilities designed to run efficiently on cloud servers.

## ✨ Core Features

### 🎬 Media & Scraping
* **🍿 4KHDHub Auto-Scraper:** Runs in the background (every 10 minutes) to check `4khdhub.dad` for the newest releases.
    * *Zero-Disk Technology:* Uses direct URLs and dynamic regex to fetch thumbnails and exact file sizes without saving anything to the server's disk, preserving strict bandwidth limits.
    * *RAM Efficient:* Employs manual Python Garbage Collection (`gc.collect()`) after scraping.
* **🔍 Interactive Directory Search (`.dll`):** Search the website directly from Telegram (`.dll [query]`). Automatically bypasses rate-limits with a built-in 1.5s delay brake, fetching direct HubCloud and HubDrive links for the top 10 results.
* **🎞️ TMDB Watch Order (`.order`):** Connects to the TMDB API to pull the perfect chronological watch order of any major franchise (e.g., `.order Spider-Man`).
* **📝 Smart Scene Renamer (`.rn`):** Formats messy media titles instantly via Regex without downloading the file. Tailored for automated naming standardization.

### 🎭 Status & AFK Modes
* **📚 Study Focus Mode (`.study [reason]`):** Enables hard-lock auto-replies to let people know you are hitting the books. Automatically disables when you type a normal message.
* **💻 Code Flow State (`.code [reason]`):** Dedicated "Do Not Disturb" mode for programming sessions.
* **🚶 General AFK (`.afk [reason]`):** Standard away message.
* **⏱️ Self-Destruct Timers (`.d [sec] [message]`):** Sends a message that counts down live before deleting itself.

### 🛡️ Surveillance & Security
* **👀 View-Once Interceptor:** Silently catches and downloads disappearing media sent to your PMs, bypassing the timer and forwarding them to your secure Log Channel.
* **👻 Ghost Tracker:** Automatically caches recent private messages and logs them if the other user attempts to delete or "unsends" them.
* **🎯 Keyword Sniper (`.sniper add [word]`):** Monitors all groups for specific keywords. If triggered, sends a direct link to the message to your Log Channel.
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
