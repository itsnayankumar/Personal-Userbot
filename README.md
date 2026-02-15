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

### 🧠 AI & Utilities
* **🌐 Flask Web Dashboard:** A live, secure HTML dashboard tracking uptime, scrape stats, and active AFK toggles.
* **🔓 Restricted Content Downloader (`.dl`):** Bypasses Telegram channel restrictions, downloads blocked media, and uploads it safely to your personal cloud.
* **🖥️ System Matrix (`.sys`):** Live monitoring of CPU, RAM, and Disk space via `psutil`.

## ⚙️ Quick Setup

1. Configure your API IDs and database variables in `config.py`.
2. Install the necessary Python dependencies:
   ```bash
   pip install pyrogram tgcrypto flask psutil speechrecognition pydub pillow deep-translator pytesseract requests aiohttp beautifulsoup4
