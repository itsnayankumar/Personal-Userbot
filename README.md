⚡ Pro Max Userbot Engine (v2.0)
An ultra-lightweight, highly aggressive Telegram Userbot built on Pyrogram and deployed via Render Docker. Engineered for zero API bans, maximum server efficiency, and total chat dominance. Includes a secure Flask web dashboard for remote control.
🕵️‍♂️ Surveillance & Reconnaissance
 * .info — Reply to any user. Dumps their Permanent ID, Data Center (DC), and Restriction Status.
 * .sniper add [word] — Silently monitors all your group chats. If someone mentions the keyword, the message is instantly forwarded to your Log Channel.
 * .sniper rm [word] / .sniper list — Manage your active sniper targets.
 * (Passive) Auto View-Once Bypass — Intercepts disappearing photos/videos sent to your PMs and permanently saves them to your Log Channel before the timer expires.
 * (Passive) Ghost Logger — Caches your private messages. If the other person deletes a message for both of you, the bot instantly recovers the text/media and sends it to your Log Channel.
🥷 Identity Theft & Chaos
 * .steal — Reply to a user. Instantly clones their Profile Picture, First Name, Last Name, and Bio, applying it to your account.
 * .revert — Drops the disguise and restores your original profile data and picture.
 * .fq [fake text] — (Forged Quote) Reply to a user. Generates a completely authentic-looking forwarded message block making it look like they said whatever you typed.
 * .mock — Reply to a message. Converts their text into alternating "sPoNgEbOb cAsE" with a clown emoji to mock them instantly.
 * .d [seconds] [message] — Sends a text message with a live ticking countdown that self-destructs for everyone when it hits zero.
 * .ghost [typing/recording/video] [seconds] — Spams a fake chat action at the top of their screen (e.g., .ghost typing 60) without you touching the keyboard.
🗄️ Data Management & Backup
 * .backup [number] — (e.g., .backup 500) Silently exports the last 500 messages of a chat (with timestamps and names) into a .txt file and uploads it to your Log Channel.
 * .tg — Reply to a massive wall of text. Compiles the text into a clean, formatted Telegraph web page and returns the URL. Bypasses Telegram's 4,096 character limit.
 * .clean — Reply to a messy or shortened URL (like bit.ly). Bypasses trackers and returns the clean, direct destination link.
 * .ocr — Reply to an image. Scans the photo using Tesseract OCR and extracts all readable text.
 * .tr [lang code] — Translates the replied-to message (defaults to English).
 * .q — Reply to a message to instantly generate a custom quote sticker.
🎬 Media, Audio & Leeching
 * .dl — Reply to "Restricted / Cannot Forward" media. Bypasses Telegram restrictions, securely downloads it to the Render server, and uploads it to your Log Channel. (Includes auto-disk-wipe to prevent server crashes).
 * .mp3 — Reply to a video file. Uses server-side FFmpeg to rip the raw audio track and upload it as an MP3.
 * .gif — Reply to a video file. Strips the audio and converts it into a native, looping Telegram GIF.
 * .vt — (Voice Transcriber) Reply to a voice note. Natively processes the audio and replies with the transcribed text.
 * .lkm [link] — Silently auto-forwards a movie link to the leech bot with -ff fix settings.
 * .lks [link] — Silently auto-forwards a TV series link to the leech bot with -e -ff fix settings.
💻 Developer & Server Controls
 * .eval [python code] — Executes raw Python code natively inside the chat and prints the terminal output.
 * .sys — Displays the live Server Health Matrix (CPU, RAM, and Disk space of the Render container).
 * .purge — Reply to one of your own messages. Instantly deletes all of your messages from that point downwards (batch-chunked to prevent API bans).
 * .ping — Checks bot latency and Render server responsiveness.
 * .scraped — Manually increments your Stremio library update counter on the web dashboard.
🚶 Evergreen Status Toggles
 * .afk [reason] — Activates AFK mode. Auto-replies to DMs with your reason.
 * .code [reason] — Activates Code Flow state. Mutes distractions and informs PMs you are coding.
 * (Passive) Auto-Wake — Sending a normal text message (without a command prefix like .) automatically turns off AFK/Code mode.
🌐 Flask Web Dashboard
Accessible via your Render URL. Requires the DASH_PASSWORD environmental variable to unlock.
Features live uptime tracking, Stremio scrape counters, and one-click remote toggle switches for your AFK and Code Flow protocols.
