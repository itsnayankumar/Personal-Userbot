import os, sys, io, time, asyncio, threading, math
import pytesseract, psutil
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image
from deep_translator import GoogleTranslator
from flask import Flask, render_template_string, redirect, request, session
from pyrogram import Client, filters
from config import Config

# --- 1. GLOBAL STATE & CACHE ---
bot_state = {
    "start_time": time.time(),
    "stremio_scrapes": 0,
    "afk_general": False,
    "focus_coding": False,
    "status_message": "",
    "sniper_keywords": []
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
        
        <h3>📊 System Status</h3>
        <div class="stat-box"><span>Server Uptime:</span> <span class="val">{{ uptime }} hrs</span></div>
        <div class="stat-box"><span>Stremio Library Scrapes:</span> <span class="val">{{ state.stremio_scrapes }}</span></div>

        <h3>🕹️ Active Protocols</h3>
        {% if state.focus_coding %}
            <a href="/toggle/code" class="btn btn-on">💻 Code Flow State: ACTIVE (Disable)</a>
        {% else %}
            <a href="/toggle/code" class="btn btn-off">💻 Code Flow State: OFFLINE (Enable)</a>
        {% endif %}

        {% if state.afk_general %}
            <a href="/toggle/afk" class="btn btn-on">🚶 General AFK: ACTIVE (Disable)</a>
        {% else %}
            <a href="/toggle/afk" class="btn btn-off">🚶 General AFK: OFFLINE (Enable)</a>
        {% endif %}
        
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
        else:
            error = "Intruder Alert. Incorrect Password."
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
        bot_state["status_message"] = "Currently in deep coding flow. Do not disturb, will reply later."
    elif feature == "afk":
        bot_state["afk_general"] = not bot_state["afk_general"]
        bot_state["focus_coding"] = False
        bot_state["status_message"] = "Currently AFK. Might be slow to reply."
    return redirect('/')

def run_flask():
    web_app.run(host="0.0.0.0", port=Config.PORT)

# --- 3. TELEGRAM USERBOT ---
bot = Client("my_userbot", session_string=Config.SESSION_STRING, api_id=Config.API_ID, api_hash=Config.API_HASH)

# --- HELPER: SMART PROGRESS TRACKER ---
async def progress_tracker(current, total, message, action, start_time):
    now = time.time()
    diff = now - start_time
    if getattr(message, "last_edit_time", 0) + 3 < now or current == total:
        message.last_edit_time = now
        percent = round(current * 100 / total, 1) if total else 0
        speed = round((current / diff) / (1024 * 1024), 2) if diff > 0 else 0
        current_mb = round(current / (1024 * 1024), 2)
        total_mb = round(total / (1024 * 1024), 2)
        filled = int(percent / 10)
        bar = "█" * filled + "▒" * (10 - filled)
        
        text = (
            f"⏳ **{action}...**\n"
            f"[{bar}] `{percent}%`\n"
            f"📦 **Size:** `{current_mb} MB / {total_mb} MB`\n"
            f"🚀 **Speed:** `{speed} MB/s`"
        )
        try:
            await message.edit_text(text)
        except Exception:
            pass

# --- AUTO VIEW-ONCE BYPASS ---
@bot.on_message(filters.private & ~filters.me & (filters.photo | filters.video | filters.animation), group=3)
async def auto_view_once(client, message):
    media = message.photo or message.video or message.animation
    if getattr(media, "ttl_seconds", None):
        file_path = None
        sender = message.from_user.first_name if message.from_user else "Unknown"
        try:
            file_path = await message.download()
            caption = f"🚨 **AUTO-INTERCEPT: View-Once Media**\n👤 **Target:** {sender}\n⏳ **Timer:** `{media.ttl_seconds}s`"
            if message.photo:
                await client.send_photo(Config.LOG_CHANNEL_ID, file_path, caption=caption)
            else:
                await client.send_video(Config.LOG_CHANNEL_ID, file_path, caption=caption)
        except Exception as e:
            await client.send_message(Config.LOG_CHANNEL_ID, f"❌ Failed to intercept view-once: {str(e)}")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

# --- THE KEYWORD SNIPER ---
@bot.on_message(filters.me & filters.command("sniper", prefixes="."))
async def sniper_control(client, message):
    if len(message.command) < 2:
        return await message.edit_text("🎯 **Sniper:**\n`.sniper add [word]`\n`.sniper rm [word]`\n`.sniper list`")
    action = message.command[1].lower()
    if action == "add" and len(message.command) > 2:
        word = message.text.split(" ", 2)[2].lower()
        if word not in bot_state["sniper_keywords"]: bot_state["sniper_keywords"].append(word)
        await message.edit_text(f"🎯 **Sniper:** Added `{word}`")
    elif action == "rm" and len(message.command) > 2:
        word = message.text.split(" ", 2)[2].lower()
        if word in bot_state["sniper_keywords"]: bot_state["sniper_keywords"].remove(word)
        await message.edit_text(f"🎯 **Sniper:** Removed `{word}`")
    elif action == "list":
        words = ", ".join(bot_state["sniper_keywords"]) or "No targets set."
        await message.edit_text(f"🎯 **Active Sniper Targets:**\n`{words}`")

@bot.on_message(filters.group & filters.text & ~filters.me, group=4)
async def sniper_listener(client, message):
    if not bot_state["sniper_keywords"]: return
    text_lower = message.text.lower()
    for kw in bot_state["sniper_keywords"]:
        if kw in text_lower:
            sender = message.from_user.first_name if message.from_user else "Unknown"
            link = message.link if message.link else "No Link"
            alert = f"🎯 **SNIPER HIT: `{kw}`**\n🏢 **Group:** {message.chat.title}\n👤 **User:** {sender}\n\n💬 `{message.text}`\n\n🔗 [Jump]({link})"
            try:
                await client.send_message(Config.LOG_CHANNEL_ID, alert, disable_web_page_preview=True)
            except Exception: pass
            break

# --- GHOST LOGGER (Safe Mode) ---
@bot.on_message(filters.private & filters.text, group=-1)
async def cache_pms(client, message):
    if message.from_user and not message.from_user.is_self:
        message_cache[message.id] = {
            "text": message.text, "from_user": message.from_user.first_name, "time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if len(message_cache) > 150: message_cache.pop(next(iter(message_cache)))

@bot.on_deleted_messages(filters.private)
async def log_deleted(client, messages):
    async with log_lock:
        for msg in messages:
            if msg.id in message_cache:
                c = message_cache[msg.id]
                try:
                    await client.send_message(Config.LOG_CHANNEL_ID, f"👻 **DELETED PM**\n👤 **From:** {c['from_user']}\n⏰ **At:** {c['time']}\n\n💬 `{c['text']}`")
                except Exception: pass
                await asyncio.sleep(1.5)

# --- RESTRICTED CONTENT SAVER (.dl) ---
@bot.on_message(filters.me & filters.command("dl", prefixes="."))
async def save_restricted(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.edit_text("⚠️ Reply to restricted media with `.dl`")
    
    status_msg = await message.edit_text("📥 Initializing download...")
    start_time = time.time()
    try:
        file_path = await message.reply_to_message.download(progress=progress_tracker, progress_args=(status_msg, "Downloading", start_time))
        if not file_path: return await status_msg.edit_text("❌ Failed to download.")
        
        await status_msg.edit_text("📤 Uploading to Log Channel...")
        start_time, status_msg.last_edit_time = time.time(), 0
        
        await client.send_document(
            chat_id=Config.LOG_CHANNEL_ID, document=file_path, caption="🔓 **Restricted File Unlocked**",
            progress=progress_tracker, progress_args=(status_msg, "Uploading", start_time)
        )
        await status_msg.edit_text("✅ **Success!** Saved in Log Channel.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            os.remove(file_path)

# --- SYSTEM HEALTH (.sys) ---
@bot.on_message(filters.me & filters.command("sys", prefixes="."))
async def system_health(client, message):
    await message.edit_text(
        f"🖥 **Server Health Matrix**\n\n"
        f"🧠 **CPU:** `{psutil.cpu_percent(interval=0.5)}%`\n"
        f"💽 **RAM:** `{psutil.virtual_memory().percent}%`\n"
        f"💾 **Disk:** `{psutil.disk_usage('/').percent}%`\n\n🛡 **System:** `Render Docker`"
    )

# --- VOICE NOTE WHISPERER (.vt) ---
@bot.on_message(filters.me & filters.command("vt", prefixes="."))
async def transcribe_voice(client, message):
    if not message.reply_to_message or not message.reply_to_message.voice:
        return await message.edit_text("⚠️ Reply to a voice note with `.vt`")
    await message.edit_text("🎙️ Processing...")
    file_path = await message.reply_to_message.download()
    try:
        wav_path = file_path + ".wav"
        AudioSegment.from_file(file_path).export(wav_path, format="wav")
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            text = r.recognize_google(r.record(source))
        await message.edit_text(f"📝 **Transcription:**\n\n`{text}`")
    except Exception as e:
        await message.edit_text(f"❌ Transcription failed: {str(e)}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if 'wav_path' in locals() and os.path.exists(wav_path): os.remove(wav_path)

# --- EVERGREEN TOGGLES ---
@bot.on_message(filters.me & filters.command("afk", prefixes="."))
async def go_afk(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently AFK. Might be slow to reply."
    bot_state["afk_general"], bot_state["focus_coding"], bot_state["status_message"] = True, False, reason
    await message.edit_text(f"🚶 **AFK Mode ON:** {reason}")

@bot.on_message(filters.me & filters.command("code", prefixes="."))
async def go_code(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently in deep coding flow. Do not disturb."
    bot_state["focus_coding"], bot_state["afk_general"], bot_state["status_message"] = True, False, reason
    await message.edit_text(f"💻 **Code Flow Mode ON:** {reason}")

@bot.on_message(filters.private & ~filters.me, group=1)
async def auto_reply(client, message):
    if bot_state["focus_coding"]: await message.reply_text(f"💻 **Auto-Reply:**\n{bot_state['status_message']}")
    elif bot_state["afk_general"]: await message.reply_text(f"🚶 **Auto-Reply:**\n{bot_state['status_message']}")

@bot.on_message(filters.me, group=2)
async def auto_turn_off(client, message):
    text = message.text or message.caption or ""
    if (bot_state["focus_coding"] or bot_state["afk_general"]) and not text.startswith((".", "/")):
        bot_state["focus_coding"] = bot_state["afk_general"] = False
        notif = await client.send_message(message.chat.id, "Welcome back! Status is now **OFF**.")
        await asyncio.sleep(3)
        await notif.delete()

# --- TARGET SHORTCUTS ---
TARGET_BOT = "@NxSFW_3Bot"

@bot.on_message(filters.me & filters.command("lkm", prefixes="."))
async def leech_movie(client, message):
    if len(message.command) > 1:
        await message.delete()
        await client.send_message(TARGET_BOT, f"/l2 {message.text.split(' ', 1)[1]} -ff fix")
    else: await message.edit_text("⚠️ Usage: `.lkm [link]`")

@bot.on_message(filters.me & filters.command("lks", prefixes="."))
async def leech_series(client, message):
    if len(message.command) > 1:
        await message.delete()
        await client.send_message(TARGET_BOT, f"/l2 {message.text.split(' ', 1)[1]} -e -ff fix")
    else: await message.edit_text("⚠️ Usage: `.lks [link]`")

# --- UTILITIES ---
@bot.on_message(filters.me & filters.command("scraped", prefixes="."))
async def count_scrape(client, message):
    bot_state["stremio_scrapes"] += 1
    await message.edit_text(f"✅ Library updated. Scrapes: {bot_state['stremio_scrapes']}")

@bot.on_message(filters.me & filters.command("purge", prefixes="."))
async def ghost_purge(client, message):
    if not message.reply_to_message: return await message.edit_text("⚠️ Reply to a message to purge.")
    start_id = message.reply_to_message.id
    msgs = [m.id async for m in client.get_chat_history(message.chat.id) if m.id >= start_id and m.from_user and m.from_user.is_self]
    if msgs: 
        await message.edit_text("🧹 Purging my messages...")
        await client.delete_messages(message.chat.id, msgs)

@bot.on_message(filters.me & filters.command("ping", prefixes="."))
async def animated_ping(client, message):
    start = time.time()
    for f in ["Pinging... ⬛️⬜️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬛️"]:
        await message.edit_text(f)
        await asyncio.sleep(0.1)
    await message.edit_text(f"🚀 **Userbot Online!**\n⚡️ **Latency:** `{round((time.time() - start) * 1000)}ms`\n🛡 **System:** `Render`")

@bot.on_message(filters.me & filters.command("tr", prefixes="."))
async def translate_text(client, message):
    if not message.reply_to_message or not message.reply_to_message.text: return await message.edit_text("⚠️ Reply to a text.")
    target_lang = message.command[1] if len(message.command) > 1 else "en"
    await message.edit_text("🔄 Translating...")
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(message.reply_to_message.text)
        await message.edit_text(f"🌍 **Translation ({target_lang}):**\n`{translated}`")
    except Exception as e: await message.edit_text(f"❌ Error: {e}")

@bot.on_message(filters.me & filters.command("q", prefixes="."))
async def quote_maker(client, message):
    if not message.reply_to_message: return await message.edit_text("⚠️ Reply to a message.")
    await message.edit_text("🎨 Generating sticker...")
    await message.reply_to_message.forward("@QuotLyBot")
    await asyncio.sleep(3)
    async for sticker in client.get_chat_history("@QuotLyBot", limit=1):
        if sticker.sticker:
            await client.send_sticker(message.chat.id, sticker.sticker.file_id)
            await message.delete()
            break

@bot.on_message(filters.me & filters.command("ocr", prefixes="."))
async def extract_text_from_image(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo: return await message.edit_text("⚠️ Reply to an image.")
    await message.edit_text("👁️ Scanning document...")
    file_path = await message.reply_to_message.download()
    try:
        extracted = pytesseract.image_to_string(Image.open(file_path))
        if not extracted.strip(): await message.edit_text("❌ No text found.")
        else: await message.edit_text(f"📝 **Extracted:**\n\n`{extracted}`")
    finally: os.remove(file_path)

@bot.on_message(filters.me & filters.command("eval", prefixes="."))
async def live_eval(client, message):
    if len(message.command) < 2: return await message.edit_text("⚠️ Provide code.")
    code = message.text.split(" ", 1)[1]
    await message.edit_text("⚙️ Executing...")
    old_stdout, sys.stdout = sys.stdout, io.StringIO()
    try:
        exec(code)
        output = sys.stdout.getvalue()
    except Exception as e: output = str(e)
    finally: sys.stdout = old_stdout
    await message.edit_text(f"💻 **Input:**\n`{code}`\n\n📤 **Output:**\n`{output or 'Success (No Output)'}`")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🔒 Pro Max Server Engine Online!")
    bot.run()
