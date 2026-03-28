import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import yt_dlp
import asyncio
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
chat_sessions = {}

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

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🚀 {bot.user.name} is online")

@bot.event
async def on_message(message):
    if message.author == bot.user or message.mention_everyone:
        return

    if not message.content.startswith('!'):
        user_id = message.author.id
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])
        
        async with message.channel.typing():
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: chat_sessions[user_id].send_message(message.content))
                msg = response.text
                for i in range(0, len(msg), 1900):
                    await message.reply(msg[i:i+1900])
            except:
                pass 

    await bot.process_commands(message)

@bot.tree.command(name="chat", description="Chat voi AI Gemini")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    user_id = interaction.user.id
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: chat_sessions[user_id].send_message(message))
        await interaction.followup.send(response.text[:1900])
    except:
        await interaction.followup.send("⚠️ AI dang ban, thu lai sau nhe!")

@bot.tree.command(name="play", description="Phat nhac YouTube")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Vao Voice Channel truoc da!")
    
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
        await interaction.followup.send(f"🎵 Dang phat: **{info['title']}**")
    except Exception as e:
        await interaction.followup.send(f"⚠️ Loi: {str(e)}")

@bot.tree.command(name="stop", description="Dung nhac")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Bye!")
    else:
        await interaction.response.send_message("Bot khong trong Voice Channel")

if __name__ == "__main__":
    keep_alive()
    bot.run(DISCORD_TOKEN)
