# ⚡ Pro Max Telegram Userbot

A highly customized, 24/7 Telegram userbot featuring a real-time web dashboard. Built with Pyrogram and Flask, ready for Render deployment.

## Features
- **Live Web Dashboard:** Real-time stats and single-click toggles.
- **Deep Focus Mode:** Auto-replies and mutes for heavy study sessions.
- **AFK Gaming Mode:** Instantly lets people know when you're in a ranked match.
- **Library Tracker:** Commands to instantly count scraped files.
- **Custom Shortcuts:** `.lk` instantly formats and pushes links to leech bots.
- **Ghost Purge:** Instantly clean up chat histories via `.purge`.

## Setup on Render
1. Fork or push this repository to GitHub.
2. Create a new Web Service on Render and connect the repo.
3. Set the Build Command: `pip install -r requirements.txt`
4. Set the Start Command: `python app.py`
5. Add `API_ID`, `API_HASH`, and `SESSION_STRING` to the Environment Variables.
