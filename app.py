import os, sys, io, time, asyncio, threading, math, re, urllib.parse, shutil, json
import pytesseract, psutil, requests
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image
from deep_translator import GoogleTranslator
from flask import Flask, render_template_string, redirect, request, session
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from config import Config

# --- 1. GLOBAL STATE & CACHE ---
bot_state = {
    "start_time": time.time(),
    "stremio_scrapes": 0,
    "afk_general": False,
    "focus_coding": False,
    "status_message": "",
    "sniper_keywords": [],
    "original_profile": {}
}

message_cache = {}
log_lock = asyncio.Lock()

# --- 2. SECURE WEB SERVER ---
web_app = Flask(__name__)
web_app.secret_key = Config.FLASK_SECRET

LOGIN_HTML = """
<!DOCTYPE html><html><head><title>Login Access</title>
<style>
    body { background-color: #0d1117; color: #58a6ff; font-family: monospace; text-align: center; padding-top: 100px; }
    input { padding: 10px; border-radius: 5px; border: 1px solid #30363d; background: #161b22; color: #c9d1d9; }
    button { padding: 10px 20px; background: #238636; color: white; border: none; border-radius: 5px; cursor: pointer; }
</style></head>
<body>
    <h2>🔒 Restricted Area</h2>
    <form method="POST">
        <input type="password" name="password" placeholder="Enter Password" required>
        <button type="submit">Unlock</button>
    </form>
    <p style="color: red;">{{ error }}</p>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html><html><head><title>Pro Max Command</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body { background-color: #0d1117; color: #c9d1d9; font-family: 'Courier New', monospace; padding: 20px; }
    .container { max-width: 700px; margin: auto; background: #161b22; padding: 25px; border-radius: 10px; border: 1px solid #30363d; box-shadow: 0 0 15px rgba(88, 166, 255, 0.2); }
    h1 { color: #58a6ff; text-align: center; border-bottom: 1px solid #30363d; padding-bottom: 10px;}
    .stat-box { display: flex; justify-content: space-between; background: #21262d; padding: 15px; margin-bottom: 10px; border-radius: 5px; font-weight: bold; font-size: 1.1em;}
    .val { color: #3fb950; }
    .btn { display: block; width: 100%; padding: 15px; margin-top: 15px; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; transition: 0.2s;}
    .btn-on { background-color: #da3633; color: white; border: none; }
    .btn-off { background-color: #238636; color: white; border: none; }
    .logout { background-color: #30363d; margin-top: 30px; }
</style></head>
<body>
    <div class="container">
        <h1>⚡ Pro Max Command Center</h1>
        <div class="stat-box"><span>Server Uptime:</span> <span class="val">{{ uptime }} hrs</span></div>
        <div class="stat-box"><span>Stremio Library Scrapes:</span> <span class="val">{{ state.stremio_scrapes }}</span></div>
        {% if state.focus_coding %}<a href="/toggle/code" class="btn btn-on">💻 Code Flow: ACTIVE (Disable)</a>
        {% else %}<a href="/toggle/code" class="btn btn-off">💻 Code Flow: OFFLINE (Enable)</a>{% endif %}
        {% if state.afk_general %}<a href="/toggle/afk" class="btn btn-on">🚶 AFK: ACTIVE (Disable)</a>
        {% else %}<a href="/toggle/afk" class="btn btn-off">🚶 AFK: OFFLINE (Enable)</a>{% endif %}
        <a href="/logout" class="btn logout">🚪 Secure Logout</a>
    </div>
</body></html>
"""

@web_app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        if request.form['password'] == Config.DASH_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        else: error = "Intruder Alert. Incorrect Password."
    return render_template_string(LOGIN_HTML, error=error)

@web_app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@web_app.route('/')
def dashboard():
    if not session.get('logged_in'): return redirect('/login')
    uptime_hrs = round((time.time() - bot_state["start_time"]) / 3600, 2)
    return render_template_string(DASHBOARD_HTML, state=bot_state, uptime=uptime_hrs)

@web_app.route('/toggle/<feature>')
def toggle(feature):
    if not session.get('logged_in'): return redirect('/login')
    if feature == "code":
        bot_state["focus_coding"] = not bot_state["focus_coding"]
        bot_state["afk_general"] = False
        bot_state["status_message"] = "Currently in deep coding flow. Do not disturb."
    elif feature == "afk":
        bot_state["afk_general"] = not bot_state["afk_general"]
        bot_state["focus_coding"] = False
        bot_state["status_message"] = "Currently AFK. Might be slow to reply."
    return redirect('/')

def run_flask():
    web_app.run(host="0.0.0.0", port=Config.PORT)

bot = Client("my_userbot", session_string=Config.SESSION_STRING, api_id=Config.API_ID, api_hash=Config.API_HASH)

async def auto_delete(message, delay=10):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def progress_tracker(current, total, message, action, start_time):
    now = time.time()
    diff = now - start_time
    if getattr(message, "last_edit_time", 0) + 5 < now or current == total:
        message.last_edit_time = now
        percent = round(current * 100 / total, 1) if total else 0
        speed = round((current / diff) / (1024 * 1024), 2) if diff > 0 else 0
        current_mb = round(current / (1024 * 1024), 2)
        total_mb = round(total / (1024 * 1024), 2)
        bar = "█" * int(percent / 10) + "▒" * (10 - int(percent / 10))
        text = f"⏳ **{action}...**\n[{bar}] `{percent}%`\n📦 **Size:** `{current_mb} / {total_mb} MB`\n🚀 **Speed:** `{speed} MB/s`"
        async def safe_edit():
            try: await message.edit_text(text)
            except: pass
        asyncio.create_task(safe_edit())

# =================================================================
# 🥷 VOLUME 2: IDENTITY THEFT & FORGERY
# =================================================================

@bot.on_message(filters.me & filters.command("steal", prefixes="."))
async def steal_identity(client, message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        msg = await message.edit_text("⚠️ Reply to a user to steal their identity.")
        return asyncio.create_task(auto_delete(msg))
        
    msg = await message.edit_text("🥷 Acquiring target identity...")
    target = message.reply_to_message.from_user
    
    # Backup original identity
    me = await client.get_me()
    bot_state["original_profile"] = {
        "first_name": me.first_name,
        "last_name": me.last_name or "",
        "bio": (await client.get_chat(me.id)).bio or ""
    }
    
    # Apply stolen text data
    await client.update_profile(first_name=target.first_name, last_name=target.last_name or "", bio="Identity temporarily acquired.")
    
    # Steal profile picture
    try:
        async for photo in client.get_chat_photos(target.id, limit=1):
            pfp_path = await client.download_media(photo.file_id)
            await client.set_profile_photo(photo=pfp_path)
            os.remove(pfp_path)
            break
    except: pass
    
    await msg.edit_text(f"🎭 **Identity Stolen:** `{target.first_name}`")
    asyncio.create_task(auto_delete(msg, 5))

@bot.on_message(filters.me & filters.command("revert", prefixes="."))
async def revert_identity(client, message):
    msg = await message.edit_text("🔄 Restoring original identity...")
    if "original_profile" in bot_state and bot_state["original_profile"]:
        p = bot_state["original_profile"]
        await client.update_profile(first_name=p["first_name"], last_name=p["last_name"], bio=p["bio"])
    
    # Delete the current (stolen) photo to reveal your real one underneath
    try:
        async for photo in client.get_chat_photos("me", limit=1):
            await client.delete_profile_photos(photo.file_id)
            break
    except: pass
    
    await msg.edit_text("✅ Identity restored successfully.")
    asyncio.create_task(auto_delete(msg, 5))

@bot.on_message(filters.me & filters.command("fq", prefixes="."))
async def forged_quote(client, message):
    if not message.reply_to_message or len(message.command) < 2:
        msg = await message.edit_text("⚠️ Reply to a user with `.fq [fake text]`")
        return asyncio.create_task(auto_delete(msg))
        
    target = message.reply_to_message.from_user
    fake_text = message.text.split(" ", 1)[1]
    name = target.first_name if target else "Unknown User"
    
    # Generates a convincing fake forward block
    await message.edit_text(f"👤 **{name}**\n💬 `{fake_text}`\n\n*(Sent via {name}'s device)*")

@bot.on_message(filters.me & filters.command("mock", prefixes="."))
async def mock_spongebob(client, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        msg = await message.edit_text("⚠️ Reply to a text message.")
        return asyncio.create_task(auto_delete(msg))
        
    text = message.reply_to_message.text
    mocked = "".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)])
    await message.edit_text(f"{mocked} 🤡")

# =================================================================
# 🗄️ VOLUME 2: BACKUPS & TELEGRAPH
# =================================================================

@bot.on_message(filters.me & filters.command("backup", prefixes="."))
async def stealth_backup(client, message):
    limit = int(message.command[1]) if len(message.command) > 1 else 100
    msg = await message.edit_text(f"📥 Silently backing up the last {limit} messages...")
    
    text_data = f"Backup of {message.chat.title or message.chat.id}\n{'='*40}\n\n"
    
    async for m in client.get_chat_history(message.chat.id, limit=limit):
        sender = m.from_user.first_name if m.from_user else "Unknown"
        time_str = m.date.strftime('%Y-%m-%d %H:%M:%S') if m.date else "Unknown Time"
        content = m.text or m.caption or f"[Media File: {m.media}]"
        text_data = f"[{time_str}] {sender}: {content}\n" + text_data
        
    file_name = f"backup_{message.chat.id}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(text_data)
        
    await client.send_document(
        Config.LOG_CHANNEL_ID, 
        file_name, 
        caption=f"🗄️ **Stealth Backup Complete**\n🏢 Chat: `{message.chat.title or 'Private'}`\n📜 Messages: `{limit}`"
    )
    os.remove(file_name)
    await msg.edit_text("✅ Backup safely delivered to Log Channel.")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("tg", prefixes="."))
async def telegraph_publish(client, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        msg = await message.edit_text("⚠️ Reply to a massive text block.")
        return asyncio.create_task(auto_delete(msg))
        
    msg = await message.edit_text("🌐 Compiling to Telegraph...")
    try:
        # Create anonymous account on the fly
        r = requests.get('https://api.telegra.ph/createAccount?short_name=ProMax&author_name=ServerAdmin')
        token = r.json()['result']['access_token']
        
        # Publish page
        content = [{"tag":"p", "children":[message.reply_to_message.text.replace("\n", "<br>")]}]
        post = requests.post(f'https://api.telegra.ph/createPage?access_token={token}&title=Terminal+Dump&return_content=false', json={'content': content})
        url = post.json()['result']['url']
        
        await msg.edit_text(f"✅ **Text Published!**\n🔗 [Read Full Document]({url})", disable_web_page_preview=True)
    except Exception as e:
        await msg.edit_text(f"❌ Failed to publish: {str(e)}")
        asyncio.create_task(auto_delete(msg, 10))

# =================================================================
# 🛡️ VOLUME 1: CORE SURVEILLANCE & LOGGING
# =================================================================

@bot.on_message(filters.me & filters.command("info", prefixes="."))
async def deep_inspector(client, message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target: 
        msg = await message.edit_text("⚠️ Cannot fetch info.")
        return asyncio.create_task(auto_delete(msg))
    dc_id = target.dc_id or "Unknown"
    status = "Restricted" if target.is_restricted else "Clean"
    bot_status = "Yes" if target.is_bot else "No"
    
    text = f"🕵️ **Deep Look Inspector**\n\n👤 **Name:** {target.first_name}\n🆔 **Permanent ID:** `{target.id}`\n🌐 **Data Center:** `DC {dc_id}`\n🤖 **Is Bot:** `{bot_status}`\n🛡️ **Status:** `{status}`\n🔗 **Profile:** [Link](tg://user?id={target.id})"
    msg = await message.edit_text(text)
    asyncio.create_task(auto_delete(msg, 20))

@bot.on_message(filters.private & ~filters.me & (filters.photo | filters.video | filters.animation), group=3)
async def auto_view_once(client, message):
    media = message.photo or message.video or message.animation
    if getattr(media, "ttl_seconds", None):
        file_path = None
        user = message.from_user
        user_tag = f"[{user.first_name}](tg://user?id={user.id})" if user else "Unknown"
        try:
            file_path = await message.download()
            caption = f"🚨 **AUTO-INTERCEPT: View-Once Media**\n👤 **From:** {user_tag}\n⏳ **Timer:** `{media.ttl_seconds}s`"
            if message.photo: await client.send_photo(Config.LOG_CHANNEL_ID, file_path, caption=caption)
            else: await client.send_video(Config.LOG_CHANNEL_ID, file_path, caption=caption)
        except: pass
        finally:
            if file_path and os.path.exists(file_path): os.remove(file_path)

@bot.on_message(filters.me & filters.command("sniper", prefixes="."))
async def sniper_control(client, message):
    if len(message.command) < 2:
        msg = await message.edit_text("🎯 **Sniper:**\n`.sniper add [word]`\n`.sniper rm [word]`\n`.sniper list`")
        return asyncio.create_task(auto_delete(msg))
    action = message.command[1].lower()
    if action == "add" and len(message.command) > 2:
        word = message.text.split(" ", 2)[2].lower()
        if word not in bot_state["sniper_keywords"]: bot_state["sniper_keywords"].append(word)
        msg = await message.edit_text(f"🎯 **Sniper:** Added `{word}`")
    elif action == "rm" and len(message.command) > 2:
        word = message.text.split(" ", 2)[2].lower()
        if word in bot_state["sniper_keywords"]: bot_state["sniper_keywords"].remove(word)
        msg = await message.edit_text(f"🎯 **Sniper:** Removed `{word}`")
    elif action == "list":
        words = ", ".join(bot_state["sniper_keywords"]) or "No targets set."
        msg = await message.edit_text(f"🎯 **Active Sniper Targets:**\n`{words}`")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.group & filters.text & ~filters.me, group=4)
async def sniper_listener(client, message):
    if not bot_state["sniper_keywords"]: return
    text_lower = message.text.lower()
    for kw in bot_state["sniper_keywords"]:
        if kw in text_lower:
            user = message.from_user
            user_tag = f"[{user.first_name}](tg://user?id={user.id})" if user else "Unknown"
            link = message.link if message.link else "No Link"
            try: await client.send_message(Config.LOG_CHANNEL_ID, f"🎯 **SNIPER HIT: `{kw}`**\n🏢 **Group:** {message.chat.title}\n👤 **User:** {user_tag}\n\n💬 `{message.text}`\n\n🔗 [Jump]({link})", disable_web_page_preview=True)
            except: pass
            break

@bot.on_message(filters.private & ~filters.me, group=-1)
async def cache_pms(client, message):
    if message.from_user:
        content = message.text or message.caption or f"[{message.media.value} Media]" if message.media else "[Unsupported]"
        message_cache[message.id] = {"content": content, "user_name": message.from_user.first_name, "user_id": message.from_user.id, "time": time.strftime('%Y-%m-%d %H:%M:%S')}
        if len(message_cache) > 200: message_cache.pop(next(iter(message_cache)))

@bot.on_deleted_messages(filters.private)
async def log_deleted(client, messages):
    async with log_lock:
        for msg in messages:
            if msg.id in message_cache:
                c = message_cache[msg.id]
                try: await client.send_message(Config.LOG_CHANNEL_ID, f"👻 **DELETED MESSAGE**\n👤 **From:** [{c['user_name']}](tg://user?id={c['user_id']})\n⏰ **Sent At:** {c['time']}\n\n💬 `{c['content']}`")
                except: pass
                await asyncio.sleep(1.5)

# =================================================================
# 🎬 VOLUME 1: MEDIA, LEECHING & UTILITIES
# =================================================================

@bot.on_message(filters.me & filters.command("dl", prefixes="."))
async def save_restricted(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        msg = await message.edit_text("⚠️ Reply to restricted media with `.dl`")
        return asyncio.create_task(auto_delete(msg))
    
    if os.path.exists("downloads"):
        try: shutil.rmtree("downloads")
        except: pass
        
    status_msg = await message.edit_text("📥 Initializing secure download...")
    start_time = time.time()
    file_path = None
    
    try:
        file_path = await message.reply_to_message.download(progress=progress_tracker, progress_args=(status_msg, "Downloading", start_time))
        if not file_path: 
            msg = await status_msg.edit_text("❌ Failed to download.")
            return asyncio.create_task(auto_delete(msg))
        
        await status_msg.edit_text("📤 Uploading to Log Channel...")
        start_time, status_msg.last_edit_time = time.time(), 0
        await client.send_document(
            chat_id=Config.LOG_CHANNEL_ID, document=file_path, caption="🔓 **Restricted File Unlocked**",
            progress=progress_tracker, progress_args=(status_msg, "Uploading", start_time)
        )
        msg = await status_msg.edit_text("✅ **Success!** Saved in Log Channel.")
        asyncio.create_task(auto_delete(msg))
    except Exception as e:
        msg = await status_msg.edit_text(f"❌ Error: {str(e)}")
        asyncio.create_task(auto_delete(msg))
    finally:
        if 'file_path' in locals() and file_path and os.path.exists(file_path): 
            try: os.remove(file_path)
            except: pass
        if os.path.exists("downloads"):
            try: shutil.rmtree("downloads")
            except: pass

@bot.on_message(filters.me & filters.command("clean", prefixes="."))
async def clean_url(client, message):
    text = message.text.split(" ", 1)[1] if len(message.command) > 1 else (message.reply_to_message.text if message.reply_to_message else "")
    urls = re.findall(r'(https?://[^\s]+)', text)
    if not urls:
        msg = await message.edit_text("⚠️ No URLs found.")
        return asyncio.create_task(auto_delete(msg))
    await message.edit_text("🔗 Unshortening...")
    try:
        res = requests.get(urls[0], allow_redirects=True, timeout=10)
        parsed = urllib.parse.urlparse(res.url)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        msg = await message.edit_text(f"✅ **Clean Link:**\n`{clean}`")
    except Exception as e: msg = await message.edit_text(f"❌ Failed: {str(e)}")
    asyncio.create_task(auto_delete(msg, 15))

@bot.on_message(filters.me & filters.command("sys", prefixes="."))
async def system_health(client, message):
    msg = await message.edit_text(f"🖥 **Server Health Matrix**\n\n🧠 **CPU:** `{psutil.cpu_percent(interval=0.5)}%`\n💽 **RAM:** `{psutil.virtual_memory().percent}%`\n💾 **Disk:** `{psutil.disk_usage('/').percent}%`\n\n🛡 **System:** `Render Docker`")
    asyncio.create_task(auto_delete(msg))

@bot.on_me
