import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai

# ===== KEEP ALIVE =====
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_web).start()

# ======================

load_dotenv()

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🔥 DEBUG ENV
print("TOKEN:", "OK" if TOKEN else "MISSING")
print("GEMINI:", "OK" if GEMINI_API_KEY else "MISSING")

# ===== GEMINI FIX =====
genai.configure(api_key=GEMINI_API_KEY)

# ⚠️ MODEL MỚI (QUAN TRỌNG)
model = genai.GenerativeModel("gemini-1.0-pro")

chat_sessions = {}

# ===== DISCORD =====
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== MUSIC =====
FFMPEG_OPTIONS = {'options': '-vn'}
YDL_OPTIONS = {'format': 'bestaudio/best', 'quiet': True}
queues = {}

# ================= EVENTS =================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # chat khi tag
    if bot.user in message.mentions:
        await handle_chat(message, message.content)

    await bot.process_commands(message)

# ================= CHAT =================

async def handle_chat(ctx, content):
    chat_id = ctx.channel.id

    if chat_id not in chat_sessions:
        chat_sessions[chat_id] = model.start_chat(history=[])

    try:
        response = await asyncio.to_thread(
            chat_sessions[chat_id].send_message,
            content
        )

        await ctx.reply(response.text[:2000])

    except Exception as e:
        print("Gemini ERROR:", e)
        await ctx.reply(f"Lỗi Gemini 💀\n```{e}```")

# 👉 lệnh !chat
@bot.command()
async def chat(ctx, *, message):
    await handle_chat(ctx, message)

# 👉 reset chat
@bot.command()
async def reset(ctx):
    chat_sessions.pop(ctx.channel.id, None)
    await ctx.reply("🔄 Reset chat!")

# ================= MUSIC =================

async def play_next(interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    if guild_id in queues and queues[guild_id]:
        url = queues[guild_id].pop(0)

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
                link = info['url']
        except Exception as e:
            print("YTDLP ERROR:", e)
            return await play_next(interaction)

        vc.play(
            discord.FFmpegPCMAudio(link, executable="ffmpeg", **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(interaction), bot.loop)
        )

@bot.tree.command(name="play", description="Phát nhạc")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("Vào voice trước 😭")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    guild_id = interaction.guild.id
    queues.setdefault(guild_id, []).append(url)

    if not vc.is_playing():
        await play_next(interaction)
        await interaction.followup.send(f"🎵 Đang phát: {url}")
    else:
        await interaction.followup.send(f"📥 Đã thêm: {url}")

@bot.tree.command(name="stop", description="Dừng nhạc")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queues[interaction.guild.id] = []
        await vc.disconnect()
        await interaction.response.send_message("👋 Nghỉ khỏe")
    else:
        await interaction.response.send_message("Bot chưa vào voice")

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
