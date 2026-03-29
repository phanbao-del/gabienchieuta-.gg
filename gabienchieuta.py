import discord
from discord.ext import commands
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
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}
afk_users = {}
xp = {}

# ================= EVENTS =================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        await channel.send(f"🎉 Welcome {member.mention}!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id

    # XP system (đơn giản)
    xp[user_id] = xp.get(user_id, 0) + 1

    # auto chào
    if message.content.lower() in ["hi", "hello"]:
        await message.reply("Chào bro 😎")

    # anti @everyone
    if "@everyone" in message.content:
        await message.reply("Đừng ping everyone 😡")

    # AFK check
    if user_id in afk_users:
        afk_users.pop(user_id)
        await message.reply("Welcome back 😏")

    for user in message.mentions:
        if user.id in afk_users:
            await message.reply(f"{user.name} đang AFK: {afk_users[user.id]}")

    await bot.process_commands(message)

# ================= MOD =================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("Không thể kick người này 😭")

    await member.kick()
    await ctx.send(f"Đã kick {member}")

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Bạn không có quyền 😡")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("Không thể ban người này 😭")

    await member.ban()
    await ctx.send(f"Đã ban {member}")

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Bạn không có quyền 😡")

@bot.command()
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)

# ================= AFK =================

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send("😴 Đã AFK")

# ================= FUN =================

@bot.command()
async def random(ctx, a: int, b: int):
    if a > b:
        return await ctx.send("Sai khoảng 😭")
    await ctx.send(f"🎲 {random.randint(a, b)}")

@bot.command()
async def coinflip(ctx):
    await ctx.send(random.choice(["Heads", "Tails"]))

# ================= GIVEAWAY =================

@bot.command()
async def giveaway(ctx, time: int, *, prize):
    msg = await ctx.send(f"🎉 Giveaway: {prize}\nReact 🎉 để tham gia!\n⏳ {time}s")

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
        await ctx.send(f"🏆 {winner.mention} thắng {prize}!")
    else:
        await ctx.send("Không ai tham gia 😭")

# ================= MUSIC =================

FFMPEG_OPTIONS = {'options': '-vn'}
YDL_OPTIONS = {'format': 'bestaudio/best', 'quiet': True}

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.guild.voice_client

    if guild_id in queues and queues[guild_id]:
        url = queues[guild_id].pop(0)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
            link = info['url']

        vc.play(
            discord.FFmpegPCMAudio(link, executable="ffmpeg", **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop)
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
        await ctx.send(f"🎵 {url}")
    else:
        await ctx.send("📥 Đã thêm")

@bot.command()
async def stop(ctx):
    vc = ctx.guild.voice_client
    if vc:
        queues[ctx.guild.id] = []
        await vc.disconnect()

# ================= RUN =================

keep_alive()
bot.run(TOKEN)
