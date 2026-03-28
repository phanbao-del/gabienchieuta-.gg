import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

# ================== LOAD ENV ==================
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

if not DISCORD_TOKEN or not GEMINI_KEY:
    print("❌ Thiếu DISCORD_TOKEN hoặc GEMINI_KEY trong .env")
    exit()

# ================== GEMINI SETUP ==================
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')   # hoặc 'gemini-2.0-flash-exp'

chat_sessions = {}

# ================== YT-DLP CONFIG ==================
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# ================== BOT SETUP ==================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands đã sync")

bot = MyBot()

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"🚀 Bot {bot.user} đã online và chạy 24/7!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Chat bình thường (không cần lệnh !)
    if not message.content.startswith('!'):
        user_id = message.author.id
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])

        try:
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: chat_sessions[user_id].send_message(message.content)
                )
                msg = response.text

                # Cắt tin nhắn nếu quá dài
                for i in range(0, len(msg), 1900):
                    await message.reply(msg[i:i+1900])
        except Exception as e:
            print(f"Lỗi chat Gemini: {e}")
            # Không reply lỗi để tránh spam

    await bot.process_commands(message)

# ================== SLASH COMMANDS ==================
@bot.tree.command(name="chat", description="Chat với Gemini AI")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()

    user_id = interaction.user.id
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: chat_sessions[user_id].send_message(message)
        )
        await interaction.followup.send(response.text[:1900])
    except Exception as e:
        await interaction.followup.send("⚠️ AI đang bận, thử lại sau nhé!")

@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Bạn phải vào Voice Channel trước!")

    await interaction.response.defer()

    try:
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            url = info['url']

        if vc.is_playing():
            vc.stop()

        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        await interaction.followup.send(f"🎵 Đang phát: **{info['title']}**")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Lỗi: {str(e)[:500]}")

@bot.tree.command(name="stop", description="Dừng nhạc và rời voice")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Đã rời voice channel!")
    else:
        await interaction.response.send_message("Bot hiện không ở trong voice channel nào.")

# ================== CHẠY BOT ==================
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
