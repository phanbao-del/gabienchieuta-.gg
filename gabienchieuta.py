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

# --- 1. TẠO WEB SERVER ĐỂ TREO 24/24 ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CẤU HÌNH BIẾN MÔI TRƯỜNG (LẤY TỪ RENDER) ---
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
        intents.message_content = True  # Quan trọng để đọc tin nhắn chat
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Đã đồng bộ Slash Commands!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🚀 Bot đã sẵn sàng: {bot.user.name}")

# --- 3. TỰ ĐỘNG CHAT AI KHI NHẮN TIN (KHÔNG CẦN /CHAT) ---
@bot.event
async def on_message(message):
    if message.author == bot.user or message.mention_everyone:
        return

    # Chỉ trả lời khi được mention hoặc nhắn trong kênh (có thể bỏ điều kiện này nếu muốn bot rep mọi lúc)
    if not message.content.startswith('!'): # Tránh trùng với lệnh prefix nếu có
        user_id = message.author.id
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])
        
        async with message.channel.typing():
            try:
                response = chat_sessions[user_id].send_message(message.content)
                await message.reply(response.text[:1900])
            except:
                pass # Bỏ qua nếu lỗi AI

    await bot.process_commands(message)

# --- 4. LỆNH PHÁT NHẠC (/play) ---
@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Bạn phải vào Voice Channel trước!")
    
    await interaction.response.defer()
    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']
        
        if vc.is_playing(): vc.stop()
        
        # Sử dụng FFmpeg để phát nhạc
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        await interaction.followup.send(f"🎵 Đang phát: **{info['title']}**")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Không lấy được nhạc, thử bài khác nha!")

# --- 5. LỆNH DỪNG NHẠC (/stop) ---
@bot.tree.command(name="stop", description="Dừng nhạc và thoát Voice")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Đã ngắt kết nối!")
    else:
        await interaction.response.send_message("Bot có ở trong kênh nào đâu?")

# --- CHẠY BOT ---
if __name__ == "__main__":
    keep_alive()
    bot.run(DISCORD_TOKEN)
