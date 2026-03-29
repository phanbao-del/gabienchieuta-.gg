import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import random

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

TOKEN = "YOUR_DISCORD_TOKEN"

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

    # 🔥 auto chào
    if message.content.lower() in ["hi", "hello"]:
        await message.reply("Chào bro 😎")

    # 🔥 anti @everyone
    if "@everyone" in message.content:
        await message.reply("Đừng ping everyone bừa bãi 😡")

    await bot.process_commands(message)

# ================= GIVEAWAY =================

@bot.command()
async def giveaway(ctx, time: int, *, prize):
    msg = await ctx.send(f"🎉 GIVEAWAY: {prize}\nReact 🎉 để tham gia!\nKết thúc sau {time}s")

    await msg.add_reaction("🎉")

    await asyncio.sleep(time)

    msg = await ctx.channel.fetch_message(msg.id)
    users = []

    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)

    if users:
        winner = random.choice(users)
        await ctx.send(f"🏆 Chúc mừng {winner.mention} thắng {prize}!")
    else:
        await ctx.send("Không có ai tham gia 😭")

# ================= MUSIC =================

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.guild.voice_client

    if queues[guild_id]:
        url = queues[guild_id].pop(0)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
            link = info['url']

        vc.play(
            discord.FFmpegPCMAudio(link, executable="ffmpeg", **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )

@bot.command()
async def play(ctx, *, url):
    if not ctx.author.voice:
        return await ctx.send("Vào voice trước 😭")

    vc = ctx.guild.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()

    queues.setdefault(ctx.guild.id, []).append(url)

    if not vc.is_playing():
        await play_next(ctx)
        await ctx.send(f"🎵 Đang phát: {url}")
    else:
        await ctx.send(f"📥 Đã thêm: {url}")

@bot.command()
async def stop(ctx):
    vc = ctx.guild.voice_client
    if vc:
        queues[ctx.guild.id] = []
        await vc.disconnect()
        await ctx.send("👋 Dừng nhạc")

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
