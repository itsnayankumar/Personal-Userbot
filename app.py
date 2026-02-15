import os, sys, io, time, asyncio, threading, math, re, urllib.parse, gc
import pytesseract, psutil, requests, aiohttp
import speech_recognition as sr
from bs4 import BeautifulSoup
from pydub import AudioSegment
from PIL import Image
from deep_translator import GoogleTranslator
from flask import Flask, render_template_string, redirect, request, session
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatAction
from config import Config

# --- 1. GLOBAL STATE & CACHE ---
bot_state = {
    "start_time": time.time(),
    "stremio_scrapes": 0,
    "afk_general": False,
    "focus_coding": False,
    "focus_study": False,
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
        
        {% if state.focus_study %}
            <a href="/toggle/study" class="btn btn-on">📚 Study Mode: ACTIVE (Disable)</a>
        {% else %}
            <a href="/toggle/study" class="btn btn-off">📚 Study Mode: OFFLINE (Enable)</a>
        {% endif %}
        
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
        bot_state["afk_general"] = bot_state["focus_study"] = False
        bot_state["status_message"] = "Currently in deep coding flow. Do not disturb, will reply later."
    elif feature == "afk":
        bot_state["afk_general"] = not bot_state["afk_general"]
        bot_state["focus_coding"] = bot_state["focus_study"] = False
        bot_state["status_message"] = "Currently AFK. Might be slow to reply."
    elif feature == "study":
        bot_state["focus_study"] = not bot_state["focus_study"]
        bot_state["focus_coding"] = bot_state["afk_general"] = False
        bot_state["status_message"] = "Currently studying. Notifications muted, will reply later."
    return redirect('/')

def run_flask():
    web_app.run(host="0.0.0.0", port=Config.PORT)

# --- 3. TELEGRAM USERBOT ---
bot = Client("my_userbot", session_string=Config.SESSION_STRING, api_id=Config.API_ID, api_hash=Config.API_HASH)

async def auto_delete(message, delay=10):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def progress_tracker(current, total, message, action, start_time):
    now = time.time()
    diff = now - start_time
    if getattr(message, "last_edit_time", 0) + 3 < now or current == total:
        message.last_edit_time = now
        percent = round(current * 100 / total, 1) if total else 0
        speed = round((current / diff) / (1024 * 1024), 2) if diff > 0 else 0
        current_mb = round(current / (1024 * 1024), 2)
        total_mb = round(total / (1024 * 1024), 2)
        bar = "█" * int(percent / 10) + "▒" * (10 - int(percent / 10))
        try:
            await message.edit_text(f"⏳ **{action}...**\n[{bar}] `{percent}%`\n📦 **Size:** `{current_mb} MB / {total_mb} MB`\n🚀 **Speed:** `{speed} MB/s`")
        except: pass

# =================================================================
# 🎬 4KHDHUB ZERO-DISK AUTO-SCRAPER
# =================================================================
HUB_SITE_URL = "https://4khdhub.dad"
HUB_CHECK_INTERVAL = 600
TRACKER_FILE = "last_movie.txt"
TMDB_API_KEY = "238a4641f974e0dfce6d690634ff68ce"

def get_last_sent():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_sent(link):
    with open(TRACKER_FILE, "w") as f:
        f.write(link)

async def fetch_home_latest():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(HUB_SITE_URL) as response:
                html = await response.text()
                
        soup = BeautifulSoup(html, "html.parser")
        latest_card = soup.find("a", class_="movie-card")
        
        if not latest_card: return None
            
        return {
            "link": HUB_SITE_URL + latest_card.get("href"),
            "title": latest_card.find("h3", class_="movie-card-title").text.strip(),
            "image": latest_card.find("img")["src"]
        }
    except Exception as e:
        print(f"Home Scrape Error: {e}")
        return None

async def fetch_download_links(movie_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(movie_url) as response:
                html = await response.text()
                
        soup = BeautifulSoup(html, "html.parser")
        
        filename_tag = soup.find(class_=lambda c: c and ('file-title' in c or 'filename' in c))
        filename = filename_tag.text.strip() if filename_tag else "Unknown.Filename.mkv"
        
        hubcloud_tag = soup.find(lambda tag: tag.name == "a" and "HubCloud" in tag.text)
        hubdrive_tag = soup.find(lambda tag: tag.name == "a" and "HubDrive" in tag.text)
        
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB))', soup.get_text())
        file_size = size_match.group(1) if size_match else "Unknown Size"
        
        del html
        del soup
        
        return {
            "filename": filename,
            "size": file_size,
            "hubcloud": hubcloud_tag.get("href") if hubcloud_tag else None,
            "hubdrive": hubdrive_tag.get("href") if hubdrive_tag else None
        }
    except Exception as e:
        print(f"Inner Page Scrape Error: {e}")
        return None

async def hub_monitor(client: Client):
    await asyncio.sleep(10)
    print("🍿 4KHDHub Auto-Poster Started!")
    
    while True:
        try:
            latest = await fetch_home_latest()
            if latest:
                last_sent = get_last_sent()
                if latest["link"] != last_sent:
                    details = await fetch_download_links(latest["link"])
                    
                    if details:
                        caption = (
                            f"🎬 **{latest['title']}**\n\n"
                            f"📦 **Size:** `{details['size']}`\n"
                            f"📄 **File:** `{details['filename']}`\n\n"
                        )
                        if details['hubcloud']: caption += f"☁️ **HubCloud:** [Download Here]({details['hubcloud']})\n"
                        if details['hubdrive']: caption += f"🚀 **HubDrive:** [Download Here]({details['hubdrive']})\n"
                        caption += f"\n🌐 **Source:** [4KHDHub]({latest['link']})"
                        
                        await client.send_photo(Config.LOG_CHANNEL_ID, photo=latest["image"], caption=caption)
                        save_last_sent(latest["link"])
            gc.collect()
        except Exception as e:
            print(f"Monitor Loop Error: {e}")
        await asyncio.sleep(HUB_CHECK_INTERVAL)

# =================================================================
# 🔍 SEARCH, TMDB & SCRAPING TOOLS
# =================================================================

@bot.on_message(filters.me & filters.command("dll", prefixes="."))
async def search_and_scrape(client, message):
    if len(message.command) < 2:
        msg = await message.edit_text("⚠️ Usage: `.dll [movie/show name]`")
        return asyncio.create_task(auto_delete(msg))
        
    query = message.text.split(" ", 1)[1]
    status_msg = await message.edit_text(f"🔍 Searching for `{query}` on 4KHDHub...")
    search_url = f"{HUB_SITE_URL}/?s={urllib.parse.quote(query)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                html = await response.text()
                
        soup = BeautifulSoup(html, "html.parser")
        results = soup.find_all("a", class_="movie-card")
        
        if not results:
            msg = await status_msg.edit_text(f"❌ No results found for `{query}`.")
            return asyncio.create_task(auto_delete(msg))
            
        max_results = min(len(results), 10)
        await status_msg.edit_text(f"✅ Found {len(results)} results! Fetching links for the top {max_results}...\n\n(Sending 1/sec to avoid limits 🛡️)")
        
        for card in results[:max_results]:
            title = card.find("h3", class_="movie-card-title").text.strip()
            link = HUB_SITE_URL + card.get("href")
            details = await fetch_download_links(link)
            
            if details:
                caption = (
                    f"🎬 **{title}**\n\n"
                    f"📦 **Size:** `{details['size']}`\n"
                    f"📄 **File:** `{details['filename']}`\n\n"
                )
                if details['hubcloud']: caption += f"☁️ **HubCloud:** [Download Here]({details['hubcloud']})\n"
                if details['hubdrive']: caption += f"🚀 **HubDrive:** [Download Here]({details['hubdrive']})\n"
                caption += f"\n🌐 **Source:** [4KHDHub]({link})"
                
                img_tag = card.find("img")
                img_url = img_tag["src"] if img_tag else None
                
                if img_url: await client.send_photo(message.chat.id, photo=img_url, caption=caption)
                else: await client.send_message(message.chat.id, caption, disable_web_page_preview=True)
                    
            await asyncio.sleep(1.5) 
            
        await status_msg.delete() 
        gc.collect()
    except Exception as e:
        msg = await status_msg.edit_text(f"❌ Search Error: {str(e)}")
        asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("order", prefixes="."))
async def fetch_watch_order(client, message):
    if len(message.command) < 2:
        msg = await message.edit_text("⚠️ Usage: `.order [franchise name]`")
        return asyncio.create_task(auto_delete(msg))
        
    query = message.text.split(" ", 1)[1]
    await message.edit_text(f"🔍 Accessing TMDB for `{query}` timeline...")
    
    try:
        async with aiohttp.ClientSession() as session:
            search_url = f"https://api.themoviedb.org/3/search/collection?api_key={TMDB_API_KEY}&query={urllib.parse.quote(query)}"
            async with session.get(search_url) as resp:
                data = await resp.json()
                
            if not data.get("results"):
                msg = await message.edit_text(f"❌ No franchise collection found for `{query}`.")
                return asyncio.create_task(auto_delete(msg))
                
            collection_id = data["results"][0]["id"]
            collection_name = data["results"][0]["name"]
            
            details_url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={TMDB_API_KEY}"
            async with session.get(details_url) as resp:
                details = await resp.json()
            
            parts = details.get("parts", [])
            parts = sorted([p for p in parts if p.get("release_date")], key=lambda x: x["release_date"])
            
            text = f"🍿 **{collection_name} - Watch Order:**\n\n"
            for i, part in enumerate(parts, 1):
                year = part['release_date'][:4]
                text += f"**{i}.** {part['title']} ({year})\n"
            
            await message.edit_text(text)
    except Exception as e:
        msg = await message.edit_text(f"❌ TMDB Fetch Error: {str(e)}")
        asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("rn", prefixes="."))
async def smart_renamer(client, message):
    if len(message.command) < 2:
        msg = await message.edit_text("⚠️ Usage: `.rn [messy_filename]`")
        return asyncio.create_task(auto_delete(msg))
        
    raw_name = message.text.split(" ", 1)[1]
    if "Jimmy.Fallon" in raw_name:
        match = re.search(r'Jimmy\.Fallon\.\d{4}\.\d{2}\.\d{2}\.(.*?)\.\d{3,4}p', raw_name)
        guest = match.group(1).replace(".", " ") if match else "Guest"
        clean_name = f"The.Tonight.Show.Starring.Jimmy.Fallon.S13E36.{guest.replace(' ', '.')}.1080p.WEB-DL.DUAL.DDP5.1.Atmos.H.264-Nkt.mkv"
    else:
        clean_name = raw_name.replace(" ", ".").replace("%20", ".")
        clean_name = re.sub(r'[^A-Za-z0-9\-\.]', '', clean_name)
        clean_name = re.sub(r'\.{2,}', '.', clean_name)
        
    await message.edit_text(f"✨ **Clean Release Name:**\n\n`{clean_name}`")

# =================================================================
# 🛡️ SURVEILLANCE & LOGGING
# =================================================================

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
        except Exception as e: await client.send_message(Config.LOG_CHANNEL_ID, f"❌ Failed to intercept: {str(e)}")
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
# ⚙️ SYSTEM & UTILITIES 
# =================================================================

@bot.on_message(filters.me & filters.command("dl", prefixes="."))
async def save_restricted(client, message):
    if not message.reply_to_message or not message.reply_to_message.media:
        msg = await message.edit_text("⚠️ Reply to restricted media with `.dl`")
        return asyncio.create_task(auto_delete(msg))
    
    status_msg = await message.edit_text("📥 Initializing download...")
    start_time = time.time()
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
        if 'file_path' in locals() and file_path and os.path.exists(file_path): os.remove(file_path)

@bot.on_message(filters.me & filters.command("ping", prefixes="."))
async def animated_ping(client, message):
    start = time.time()
    for f in ["Pinging... ⬛️⬜️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬜️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬜️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬜️", "Pinging... ⬛️⬛️⬛️⬛️⬛️"]:
        try:
            await message.edit_text(f)
            await asyncio.sleep(0.1)
        except: pass
    msg = await message.edit_text(f"🚀 **Userbot Online!**\n⚡️ **Latency:** `{round((time.time() - start) * 1000)}ms`\n🛡 **System:** `Render`")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("sys", prefixes="."))
async def system_health(client, message):
    msg = await message.edit_text(f"🖥 **Server Health Matrix**\n\n🧠 **CPU:** `{psutil.cpu_percent(interval=0.5)}%`\n💽 **RAM:** `{psutil.virtual_memory().percent}%`\n💾 **Disk:** `{psutil.disk_usage('/').percent}%`")
    asyncio.create_task(auto_delete(msg))

# =================================================================
# 🎭 CHAT FLEX & AFK MODES
# =================================================================

@bot.on_message(filters.me & filters.command("d", prefixes="."))
async def self_destruct_nuke(client, message):
    if len(message.command) < 3:
        msg = await message.edit_text("⚠️ Usage: `.d [seconds] [message]`")
        return asyncio.create_task(auto_delete(msg))
    try:
        sec = min(int(message.command[1]), 60)
        text = message.text.split(" ", 2)[2]
    except:
        msg = await message.edit_text("⚠️ Invalid time format. Use: `.d 15 My message`")
        return asyncio.create_task(auto_delete(msg))
        
    for i in range(sec, 0, -1):
        try:
            await message.edit_text(f"{text}\n\n⏳ `{i}s`")
            await asyncio.sleep(1)
        except: pass
    await message.delete()

@bot.on_message(filters.me & filters.command("afk", prefixes="."))
async def go_afk(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently AFK. Might be slow to reply."
    bot_state["afk_general"], bot_state["focus_coding"], bot_state["focus_study"], bot_state["status_message"] = True, False, False, reason
    msg = await message.edit_text(f"🚶 **AFK Mode ON:** {reason}")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("code", prefixes="."))
async def go_code(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently in deep coding flow. Do not disturb."
    bot_state["focus_coding"], bot_state["afk_general"], bot_state["focus_study"], bot_state["status_message"] = True, False, False, reason
    msg = await message.edit_text(f"💻 **Code Flow Mode ON:** {reason}")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.me & filters.command("study", prefixes="."))
async def go_study(client, message):
    reason = message.text.split(" ", 1)[1] if len(message.command) > 1 else "Currently studying. Notifications muted."
    bot_state["focus_study"], bot_state["afk_general"], bot_state["focus_coding"], bot_state["status_message"] = True, False, False, reason
    msg = await message.edit_text(f"📚 **Study Mode ON:** {reason}")
    asyncio.create_task(auto_delete(msg))

@bot.on_message(filters.private & ~filters.me, group=1)
async def auto_reply(client, message):
    if bot_state["focus_coding"]: await message.reply_text(f"💻 **Auto-Reply:**\n{bot_state['status_message']}")
    elif bot_state["focus_study"]: await message.reply_text(f"📚 **Auto-Reply:**\n{bot_state['status_message']}")
    elif bot_state["afk_general"]: await message.reply_text(f"🚶 **Auto-Reply:**\n{bot_state['status_message']}")

@bot.on_message(filters.me, group=2)
async def auto_turn_off(client, message):
    text = message.text or message.caption or ""
    if (bot_state["focus_coding"] or bot_state["afk_general"] or bot_state["focus_study"]) and not text.startswith((".", "/")):
        bot_state["focus_coding"] = bot_state["afk_general"] = bot_state["focus_study"] = False
        notif = await client.send_message(message.chat.id, "Welcome back! Status is now **OFF**.")
        asyncio.create_task(auto_delete(notif, 3))

# =================================================================
# 🚀 LAUNCH SEQUENCE
# =================================================================

async def start_services():
    await bot.start()
    asyncio.create_task(hub_monitor(bot))
    await idle()
    await bot.stop()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🔒 Pro Max Server Engine Online!")
    bot.run(start_services())
