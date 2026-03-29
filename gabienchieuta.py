import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Gemini setup ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

chat_sessions = {}

# --- Discord setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- FFmpeg ---
FFMPEG_OPTIONS = {
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True
}

# --- Music Queue ---
queues = {}

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Chỉ trả lời khi bị tag (tránh spam API)
    if bot.user in message.mentions:
        chat_id = message.channel.id

        if chat_id not in chat_sessions:
            chat_sessions[chat_id] = model.start_chat(history=[])

        async with message.channel.typing():
            try:
                response = await asyncio.to_thread(
                    chat_sessions[chat_id].send_message,
                    message.content
                )
                await message.reply(response.text[:2000])
            except Exception as e:
                print(e)
                await message.reply("Gemini lỗi rồi 💀")

    await bot.process_commands(message)

# ===================== MUSIC =====================

async def play_next(interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    if queues[guild_id]:
        url = queues[guild_id].pop(0)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
            link = info['url']
            title = info['title']

        vc.play(
            discord.FFmpegPCMAudio(link, executable="ffmpeg", **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(interaction), bot.loop)
        )

# --- PLAY ---
@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
@app_commands.describe(url="Link hoặc tên bài hát")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("Vào voice trước đi 😭")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    guild_id = interaction.guild.id

    if guild_id not in queues:
        queues[guild_id] = []

    queues[guild_id].append(url)

    if not vc.is_playing():
        await play_next(interaction)
        await interaction.followup.send(f"🎵 Đang phát: {url}")
    else:
        await interaction.followup.send(f"📥 Đã thêm vào queue: {url}")

# --- STOP ---
@bot.tree.command(name="stop", description="Dừng nhạc")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queues[interaction.guild.id] = []
        await vc.disconnect()
        await interaction.response.send_message("👋 Nghỉ khỏe")
    else:
        await interaction.response.send_message("Bot chưa vào voice")

# ===================== RUN =====================

bot.run(TOKEN)
