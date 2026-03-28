import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import yt_dlp
import random
import asyncio
import os
from flask import Flask
from threading import Thread

# --- 1. CẤU HÌNH WEB SERVER ĐỂ RENDER KHÔNG BÁO LỖI PORT ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Lấy cổng từ Render, nếu không có thì mặc định là 8080
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. LẤY MÃ TỪ ENVIRONMENT VARIABLES ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

# Cấu hình AI Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
chat_sessions = {}

# Cấu hình Nhạc
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Đã đồng bộ Slash Commands!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🚀 Bot đã sẵn sàng: {bot.user.name}")

# --- 3. TỰ ĐỘNG CHAT AI (NHẮN TIN LÀ REP) ---
@bot.event
async def on_message(message):
    if message.author == bot.user or message.mention_everyone:
        return

    # Nếu không phải lệnh bắt đầu bằng '!', bot sẽ chat AI
    if not message.content.startswith('!'):
        user_id = message.author.id
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])
        
        async with message.channel.typing():
            try:
                response = chat_sessions[user_id].send_message(message.content)
                # Cắt bớt nếu tin nhắn quá dài (>2000 ký tự)
                await message.reply(response.text[:1900])
            except:
                pass 

    await bot.process_commands(message)

# --- 4. LỆNH PHÁT NHẠC (/play) ---
@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Vào Voice Channel trước đã!")
    
    await interaction.response.defer()
    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']
        
        if vc.is_playing(): vc.stop()
        
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        await interaction.followup.send(f"🎵 Đang phát: **{info['title']}**")
    except:
        await interaction.followup.send(f"⚠️ Lỗi nhạc rồi, thử bài khác nha!")

# --- 5. LỆNH DỪNG NHẠC (/stop) ---
@bot.tree.command(name="stop", description="Dừng nhạc và thoát Voice")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Bye bye!")
    else:
        await interaction.response.send_message("Tui có ở trong kênh nào đâu?")

# --- CHẠY BOT ---
if __name__ == "__main__":
    keep_alive() # Quan trọng để Render không tắt bot
    bot.run(DISCORD_TOKEN)
