import os, sys, io, time, asyncio, threading
import pytesseract, psutil, requests
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image
from deep_translator import GoogleTranslator
from flask import Flask, render_template_string, redirect, request, session
from pyrogram import Client, filters
from config import Config

# --- 1. Global State ---
bot_state = {
    "start_time": time.time(),
    "stremio_scrapes": 0,
    "afk_general": False,
    "focus_coding": False,
    "status_message": ""
}

# --- Ghost Logger Cache & Safety Lock ---
message_cache = {}
log_lock = asyncio.Lock()

# --- 2. Secure Web Server ---
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

# --- 3. Telegram Userbot ---
bot = Client("my_userbot", session_string=Config.SESSION_STRING, api_id=Config.API_ID, api_hash=Config.API_HASH)

# --- GHOST LOGGER MODULE (Safe Mode) ---
@bot.on_message(filters.private & filters.text, group=-1)
async def cache_pms(client, message):
    if message.from_user and not message.from_user.is_self:
        message_cache[message.id] = {
            "text": message.text,
            "from_user": message.from_user.first_name,
            "time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if len(message_cache) > 150: # Keeps memory usage extremely low
            message_cache.pop(next(iter(message_cache)))

@bot.on_deleted_messages(filters.private)
async def log_deleted(client, messages):
    async with log_lock:
        for msg in messages:
            if msg.id in message_cache:
                cached = message_cache[msg.id]
                log_text = (
                    f"👻 **DELETED PM INTERCEPTED**\n"
                    f"👤 **From:** {cached['from_user']}\n"
                    f"⏰ **Sent at:** {cached['time']}\n\n"
                    f"💬 `{cached['text']}`"
                )
                try:
                    await client.send_message(Config.LOG_CHANNEL_ID, log_text)
                except Exception:
                    pass
                await asyncio.sleep(1.5) # SAFETY PAUSE: 1.5s delay to prevent flood bans

# --- SYSTEM HEALTH MODULE ---
@bot.on_message(filters.me & filters.command("sys", prefixes="."))
async def system_health(client, message):
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    stats = (
        f"🖥 **Server Health Matrix**\n\n"
        f"🧠 **CPU Usage:** `{cpu}%`\n"
        f"💽 **RAM Usage:** `{ram}%`\n"
        f"💾 **Disk Usage:** `{disk}%`\n\n"
        f"🛡 **System:** `Render Docker`"
    )
    await message.edit_text(stats)

# --- VOICE NOTE WHISPERER ---
@bot.on_message(filters.me & filters.command("vt", prefixes="."))
async def transcribe_voice(client, message):
    if not message.reply_to_message or not message.reply_to_message.voice:
        return await message.edit_text("⚠️ Reply to a voice note with `.vt`")
    
    await message.edit_text("🎙️ Processing audio...")
    file_path = await message.reply_to_message.download()
    
    await message.edit_text("⚙️ Transcribing via Deep Speech...")
    try:
        wav_path = file_path + ".wav"
        # FFmpeg handles this perfectly in the Docker container
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_path, format="wav")
        
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
            
        await message.edit_text(f"📝 **Transcription:**\n\n`{text}`")
    except Exception as e:
        await message.edit_text(f"❌ Transcription failed: {str(e)}")
    finally:
        # Clean up files so the server doesn't bloat
        if os.path.exists(file_path): os.remove(file_path)
        if 'wav_path' in locals() and os.path.exists(wav_path): os.remove(wav_path)

# --- EVERGREEN TOGGLES & AUTOMATION ---
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
    if bot_state["focus_coding"]:
        await message.reply_text(f"💻 **Auto-Reply:**\n{bot_state['status_message']}")
    elif bot_state["afk_general"]:
        await message.reply_text(f"🚶 **Auto-Reply:**\n{bot_state['status_message']}")

@bot.on_message(filters.me, group=2)
async def auto_turn_off(client, message):
    text = message.text or message.caption or ""
    if (bot_state["focus_coding"] or bot_state["afk_general"]) and not text.startswith((".", "/")):
        bot_state["focus_coding"], bot_state["afk_general"] = False, False
        notif = await client.send_message(message.chat.id, "Welcome back! Status is now **OFF**.")
        await asyncio.sleep(3)
        await notif.delete()

TARGET_BOT = "@NxSFW_3Bot"

@bot.on_message(filters.me & filters.command("lkm", prefixes="."))
async def leech_movie(client, message):
    if len(message.command) > 1:
        link = message.text.split(" ", 1)[1]
        await message.delete()
        await client.send_message(TARGET_BOT, f"/l2 {link} -ff fix")
    else: await message.edit_text("⚠️ Usage: `.lkm [link]`")

@bot.on_message(filters.me & filters.command("lks", prefixes="."))
async def leech_series(client, message):
    if len(message.command) > 1:
        link = message.text.split(" ", 1)[1]
        await message.delete()
        await client.send_message(TARGET_BOT, f"/l2 {link} -e -ff fix")
    else: await message.edit_text("⚠️ Usage: `.lks [link]`")

@bot.on_message(filters.me & filters.command("scraped", prefixes="."))
async def count_scrape(client, message):
    bot_state["stremio_scrapes"] += 1
    await message.edit_text(f"✅ Library updated. Scrapes: {bot_state['stremio_scrapes']}")

@bot.on_message(filters.me & filters.command("purge", prefixes="."))
async def ghost_purge(client, message):
    if not message.reply_to_message: return await message.edit_text("⚠️ Reply to a message to purge.")
    start_id = message.reply_to_message.id
    msgs = [msg.id async for msg in client.get_chat_history(message.chat.id) if msg.id >= start_id and msg.from_user and msg.from_user.is_self]
    if msgs: 
        await message.edit_text("🧹 Purging my messages...")
        await client.delete_messages(message.chat.id, msgs)

@bot.on_message(filters.me & filters.command("ping", prefixes="."))
async def animated_ping(client, message):
    start = time.time()
    for frame in ["Pinging... ⬛️⬜️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬛️"]:
        await message.edit_text(frame)
        await asyncio.sleep(0.1)
    await message.edit_text(f"🚀 **Userbot Online!**\n⚡️ **Latency:** `{round((time.time() - start) * 1000)}ms`\n🛡 **System:** `Render`")

@bot.on_message(filters.me & filters.command("tr", prefixes="."))
async def translate_text(client, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.edit_text("⚠️ Reply to a text message.")
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
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.edit_text("⚠️ Reply to an image with `.ocr`")
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
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    try:
        exec(code)
        output = redirected_output.getvalue()
    except Exception as e: output = str(e)
    finally: sys.stdout = old_stdout
    if not output: output = "Success (No Output)"
    await message.edit_text(f"💻 **Input:**\n`{code}`\n\n📤 **Output:**\n`{output}`")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🔒 Pro Max Server Engine Online!")
    bot.run()
