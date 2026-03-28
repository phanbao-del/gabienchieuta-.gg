import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import yt_dlp
import random
import asyncio

# --- ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY ---
DISCORD_TOKEN = 'MTQ4NzM0Mjc1MDEwOTAwODAyMw.G_D9_a.36zxWf9Lw4TgZEkMGRp_df3uUHPffRlFg7VwvQ'
GEMINI_KEY = 'AIzaSyDxsImB4VKl45TfD4LhfPQruvw6Lov2sMc'

# Cấu hình AI Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
chat_sessions = {}

# Cấu hình Nhạc (YouTube)
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Đồng bộ hóa các lệnh gạch chéo (/) với Discord
        await self.tree.sync()
        print(f"✅ Đã đồng bộ Slash Commands!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🚀 Bot đã sẵn sàng: {bot.user.name}")
    print(f"🆔 ID Bot: {bot.user.id}")

# --- 1. LỆNH CHAT AI (CÓ NHỚ NGỮ CẢNH) ---
@bot.tree.command(name="chat", description="Trò chuyện thông minh với AI Gemini")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    user_id = interaction.user.id
    
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    
    try:
        response = chat_sessions[user_id].send_message(message)
        await interaction.followup.send(f"🤖 **Bot:** {response.text[:1900]}")
    except Exception as e:
        await interaction.followup.send("⚠️ Hệ thống AI đang bận hoặc lỗi Key, thử lại sau nhé!")

# --- 2. LỆNH PHÁT NHẠC (/play) ---
@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Bạn phải vào Voice Channel trước!")
    
    await interaction.response.defer()
    
    # Kết nối vào Voice Channel
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']
            title = info['title']

        vc.stop()
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        await interaction.followup.send(f"🎵 Đang phát: **{title}**")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Lỗi khi tải nhạc: {str(e)}")

# --- 3. LỆNH DỪNG NHẠC (/stop) ---
@bot.tree.command(name="stop", description="Dừng nhạc và thoát Voice")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Đã ngắt kết nối Voice!")
    else:
        await interaction.response.send_message("Bot có đang ở trong kênh nào đâu?")

# --- 4. MINI GAME ĐOÁN SỐ (/game) ---
@bot.tree.command(name="game", description="Trò chơi đoán số may mắn (1-10)")
async def game(interaction: discord.Interaction, guess: int):
    number = random.randint(1, 10)
    if guess == number:
        await interaction.response.send_message(f"🎉 Quá đỉnh! Số đúng là **{number}**. Bạn đã thắng!")
    else:
        await interaction.response.send_message(f"❌ Tiếc quá! Số đúng là **{number}**. Thử lại nhé!")

# --- 5. QUẢN TRỊ: XÓA TIN NHẮN (/clear) ---
@bot.tree.command(name="clear", description="Xóa tin nhắn số lượng lớn (Chỉ Admin)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Đã dọn dẹp sạch sẽ **{len(deleted)}** tin nhắn!")

bot.run(DISCORD_TOKEN)