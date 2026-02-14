import os
import threading
import time
import asyncio
from flask import Flask, render_template_string, redirect
from pyrogram import Client, filters
from config import Config

# --- 1. Global State Database ---
bot_state = {
    "start_time": time.time(),
    "stremio_scrapes": 0,
    "afk_mlbb": False,
    "study_mode_hsc": False,
    "status_message": ""
}

# --- 2. Web Server (The Ultra Dashboard) ---
web_app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Userbot Control Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: 'Courier New', Courier, monospace; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; }
        h1 { color: #58a6ff; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 10px;}
        .stat-box { display: flex; justify-content: space-between; background: #21262d; padding: 15px; margin-bottom: 10px; border-radius: 5px; font-weight: bold; }
        .val { color: #3fb950; }
        .btn { display: block; width: 100%; padding: 15px; margin-top: 15px; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; transition: 0.2s;}
        .btn-on { background-color: #da3633; color: white; border: none; }
        .btn-off { background-color: #238636; color: white; border: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ Bot Control Center</h1>
        
        <h3>📊 Live Stats</h3>
        <div class="stat-box"><span>Uptime:</span> <span class="val">{{ uptime }} hrs</span></div>
        <div class="stat-box"><span>Stremio Files Scraped:</span> <span class="val">{{ state.stremio_scrapes }}</span></div>

        <h3>🕹️ Quick Toggles</h3>
        {% if state.study_mode_hsc %}
            <a href="/toggle/study" class="btn btn-on">📚 HSC Study Mode: ON (Click to Disable)</a>
        {% else %}
            <a href="/toggle/study" class="btn btn-off">📚 HSC Study Mode: OFF (Click to Enable)</a>
        {% endif %}

        {% if state.afk_mlbb %}
            <a href="/toggle/afk" class="btn btn-on">🎮 MLBB AFK: ON (Click to Disable)</a>
        {% else %}
            <a href="/toggle/afk" class="btn btn-off">🎮 MLBB AFK: OFF (Click to Enable)</a>
        {% endif %}
    </div>
</body>
</html>
"""

@web_app.route('/')
def dashboard():
    uptime_hrs = round((time.time() - bot_state["start_time"]) / 3600, 2)
    return render_template_string(HTML_TEMPLATE, state=bot_state, uptime=uptime_hrs)

@web_app.route('/toggle/<feature>')
def toggle(feature):
    if feature == "study":
        bot_state["study_mode_hsc"] = not bot_state["study_mode_hsc"]
        bot_state["afk_mlbb"] = False
        bot_state["status_message"] = "Currently focused on HSC board prep, will reply in a bit."
    elif feature == "afk":
        bot_state["afk_mlbb"] = not bot_state["afk_mlbb"]
        bot_state["study_mode_hsc"] = False
        bot_state["status_message"] = "In a Mobile Legends ranked match right now, might be slow to reply."
    return redirect('/')

def run_flask():
    web_app.run(host="0.0.0.0", port=Config.PORT)

# --- 3. Telegram Userbot ---
bot = Client("my_userbot", session_string=Config.SESSION_STRING, api_id=Config.API_ID, api_hash=Config.API_HASH)

# 1. AFK & Study Toggles via Telegram
@bot.on_message(filters.me & filters.command("afk", prefixes="."))
async def go_afk(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "In a Mobile Legends ranked match right now, might be slow to reply."
    bot_state["afk_mlbb"] = True
    bot_state["study_mode_hsc"] = False
    bot_state["status_message"] = reason
    await message.edit_text(f"🎮 **AFK Mode ON:** {reason}")

@bot.on_message(filters.me & filters.command("study", prefixes="."))
async def go_study(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently focused on HSC board prep, will reply in a bit."
    bot_state["study_mode_hsc"] = True
    bot_state["afk_mlbb"] = False
    bot_state["status_message"] = reason
    await message.edit_text(f"📚 **Study Mode ON:** {reason}")

# 2. Auto-Reply Logic
@bot.on_message(filters.private & ~filters.me, group=1)
async def auto_reply(client, message):
    if bot_state["study_mode_hsc"]:
        await message.reply_text(f"📚 **Auto-Reply:**\n{bot_state['status_message']}")
    elif bot_state["afk_mlbb"]:
        await message.reply_text(f"🎮 **Auto-Reply:**\n{bot_state['status_message']}")

# 3. Auto-Turn Off Status
@bot.on_message(filters.me, group=2)
async def auto_turn_off(client, message):
    text = message.text or message.caption or ""
    # Don't turn off if the user is just running another command
    if (bot_state["study_mode_hsc"] or bot_state["afk_mlbb"]) and not text.startswith((".", "/")):
        bot_state["study_mode_hsc"] = False
        bot_state["afk_mlbb"] = False
        notif = await client.send_message(message.chat.id, "Welcome back! AFK/Study Mode is now **OFF**.")
        await asyncio.sleep(3)
        await notif.delete()

# 4. Leech Bot Shortcut
@bot.on_message(filters.me & filters.command("lk", prefixes="."))
async def leech_shortcut(client, message):
    if len(message.command) > 1:
        link = message.text.split(" ", 1)[1]
        await message.delete()
        await client.send_message(message.chat.id, f"/leech2 {link} -ff fix")
    else:
        await message.edit_text("⚠️ You forgot the link! Usage: `.lk [link]`")

# 5. Stremio Scrape Counter Update
@bot.on_message(filters.me & filters.command("scraped", prefixes="."))
async def count_scrape(client, message):
    bot_state["stremio_scrapes"] += 1
    await message.edit_text(f"✅ Library updated. Total Scrapes: {bot_state['stremio_scrapes']}")

# 6. Ghost Purge
@bot.on_message(filters.me & filters.command("purge", prefixes="."))
async def ghost_purge(client, message):
    if not message.reply_to_message:
        await message.edit_text("⚠️ Reply to a message to purge.")
        return
    start_id = message.reply_to_message.id
    msgs = []
    await message.edit_text("🧹 Purging my messages...")
    async for msg in client.get_chat_history(message.chat.id):
        if msg.id < start_id: break
        if msg.from_user and msg.from_user.is_self: msgs.append(msg.id)
    if msgs: await client.delete_messages(message.chat.id, msgs)

# 7. Animated Ping
@bot.on_message(filters.me & filters.command("ping", prefixes="."))
async def animated_ping(client, message):
    start = time.time()
    for frame in ["Pinging... ⬛️⬜️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬛️"]:
        await message.edit_text(frame)
        await asyncio.sleep(0.1)
    speed = round((time.time() - start) * 1000)
    await message.edit_text(f"🚀 **Userbot Online!**\n⚡️ **Latency:** `{speed}ms`\n🛡 **System:** `Render`")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Pro Max Dashboard & Userbot starting...")
    bot.run()
