import discord
from discord.ext import commands
import asyncio
import random
import json
import os
import re
import yt_dlp
from keep_alive import keep_alive
from datetime import datetime

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== CONFIG ====================
STAFF_ROLES = ["Owner", "Co-owner", "Co own", "Mod", "Admin", "Lễ tân", "Ticket Admin", "Ticket Support"]
GIVEAWAY_ROLES = ["Owner", "Co-owner", "Mod", "Admin"]  

TASK_FILE = "tasks.json"

if not os.path.exists(TASK_FILE):
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

def load_tasks():
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(tasks):
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

def parse_time(time_str):
    time_str = time_str.lower().replace(" ", "")
    total_seconds = 0
    matches = re.findall(r'(\d+)([hms])', time_str)
    for value, unit in matches:
        value = int(value)
        if unit == 'h': total_seconds += value * 3600
        elif unit == 'm': total_seconds += value * 60
        elif unit == 's': total_seconds += value
    return total_seconds

@bot.event
async def on_ready():
    print(f'{bot.user} đã online!')
    await bot.change_presence(activity=discord.Game(name="Đang làm việc chăm chỉ ^^"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# Giveaway
@bot.command()
@commands.has_any_role(*GIVEAWAY_ROLES)
async def ga(ctx, time_str: str, winners: int, *, prize: str):
    seconds = parse_time(time_str)
    if seconds <= 0:
        await ctx.send("**Thời gian không hợp lệ! Ví dụ: 24h, 30m, 1h30m**")
        return

    embed = discord.Embed(title="🎉 **GIVEAWAY** 🎉", description=f"**Phần thưởng:** {prize}\n**Số người thắng:** {winners}\n**Thời gian:** {time_str}", color=0x00ff00)
    embed.set_footer(text=f"Kết thúc sau {time_str} • Hosted by {ctx.author}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(seconds)

    msg = await ctx.channel.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if not reaction or reaction.count - 1 < winners:
        await ctx.send("**Không đủ người tham gia giveaway!**")
        return

    users = [user async for user in reaction.users()]
    users.pop(0)
    winners_list = random.sample(users, k=min(winners, len(users)))
    winner_mentions = ", ".join([winner.mention for winner in winners_list])
    await ctx.send(f"**🎉 Chúc mừng {winner_mentions} đã thắng {prize}!**")

# Task system
@bot.command()
@commands.has_any_role(*STAFF_ROLES)
async def task(ctx, role: str, *, description: str):
    role = role.capitalize()
    if role not in [r.capitalize() for r in STAFF_ROLES]:
        await ctx.send("**Role không hợp lệ!**")
        return

    tasks = load_tasks()
    task_id = len(tasks) + 1
    task_data = {
        "id": task_id,
        "role": role,
        "description": description,
        "created_by": ctx.author.name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Chưa hoàn thành"
    }
    tasks.append(task_data)
    save_tasks(tasks)
    await ctx.send(f"**✅ Task #{task_id} đã được tạo cho {role}**\n**Nội dung:** {description}")

@bot.command()
async def tasks(ctx):
    tasks = load_tasks()
    if not tasks:
        await ctx.send("**Hiện không có task nào.**")
        return
    embed = discord.Embed(title="📋 Danh sách Task", color=0x3498db)
    for t in tasks:
        embed.add_field(name=f"Task #{t['id']} - {t['role']}", value=f"{t['description']}\n**Trạng thái:** {t['status']}\n**Tạo bởi:** {t['created_by']}", inline=False)
    await ctx.send(embed=embed)

# Music
@bot.command()
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("**Bạn phải vào voice channel trước!**")
        return
    channel = ctx.author.voice.channel
    try:
        if ctx.voice_client is None:
            await channel.connect()
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)

        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']

        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        ctx.voice_client.play(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS))
        await ctx.send(f"**🎵 Đang phát:** {info.get('title', url)}")
    except Exception as e:
        await ctx.send(f"**Lỗi phát nhạc:** {str(e)}")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("**Đã dừng nhạc và rời voice channel.**")
    else:
        await ctx.send("**Bot không đang trong voice channel.**")

# Run
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("Vui lòng thêm TOKEN vào Secrets!")
