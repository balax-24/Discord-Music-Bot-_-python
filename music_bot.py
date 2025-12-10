import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import time
import random
import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- CONFIGURATION ---
TOKEN = ''
SPOTIFY_ID = ''
SPOTIFY_SECRET = ''

# --- SETUP ---
sp = None
if SPOTIFY_ID and SPOTIFY_SECRET:
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET))
        print("✅ Spotify Connected!")
    except:
        print("⚠️ Spotify Keys Invalid.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- DATA STORAGE ---
server_data = {}

def get_data(guild_id):
    if guild_id not in server_data:
        server_data[guild_id] = {
            'queue': [], 
            'loop': 'off',
            'volume': 1.0,
            'now_playing': None,
            'start_time': 0,
            'seek_offset': 0,
            'manual_stop': False
        }
    return server_data[guild_id]

# --- HELPER: TIME FORMATTER ---
def format_duration(seconds):
    if not seconds: return "Live"
    return str(datetime.timedelta(seconds=int(seconds)))

# --- CORE FUNCTIONS ---

async def resolve_song_audio(song_data):
    if song_data.get('url'): return song_data 
    search_query = f"{song_data['title']} {song_data.get('artist', '')} audio"
    ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            if 'entries' in info: info = info['entries'][0]
            
            # --- FORCE UPDATE TITLE (Restored) ---
            song_data['url'] = info['url']
            song_data['title'] = info['title'] 
            song_data['duration'] = info.get('duration')
            song_data['webpage_url'] = info.get('webpage_url')
            if not song_data.get('thumbnail'): song_data['thumbnail'] = info.get('thumbnail')
            
            return song_data
    except: return None

async def play_next(interaction):
    guild_id = interaction.guild_id
    data = get_data(guild_id)
    vc = interaction.guild.voice_client
    if not vc: return

    if data['now_playing'] and data['loop'] == 'song':
        song = data['now_playing']
    elif data['now_playing'] and data['loop'] == 'queue':
        data['queue'].append(data['now_playing'])
        song = data['queue'].pop(0) if data['queue'] else None
    elif data['queue']:
        song = data['queue'].pop(0)
    else:
        data['now_playing'] = None
        await asyncio.sleep(300)
        if not vc.is_playing() and not data['queue']: await vc.disconnect()
        return

    if not song.get('url'): song = await resolve_song_audio(song)
    if not song or not song.get('url'):
        await play_next(interaction)
        return

    data['now_playing'] = song
    data['start_time'] = time.time()
    data['seek_offset'] = 0
    
    await start_playing_ffmpeg(interaction, song['url'])

    # Send Dashboard
    embed = create_embed(data, interaction.guild)
    view = MusicDashboard(interaction)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
    except: pass

async def start_playing_ffmpeg(interaction, url, start_sec=0):
    vc = interaction.guild.voice_client
    data = get_data(interaction.guild_id)
    
    opts = f'-vn -ss {time.strftime("%H:%M:%S", time.gmtime(start_sec))}'
    ffmpeg_final = FFMPEG_OPTIONS.copy()
    ffmpeg_final['options'] = opts

    source = discord.FFmpegPCMAudio(url, **ffmpeg_final)
    source = discord.PCMVolumeTransformer(source, volume=data['volume'])

    def after(e):
        if not data.get('manual_stop', False):
            coro = play_next(interaction)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)
        data['manual_stop'] = False 

    if vc.is_playing(): vc.stop()
    vc.play(source, after=after)

# --- EMBED (NO PROGRESS BAR) ---
def create_embed(data, guild):
    song = data['now_playing']
    if not song: return discord.Embed(title="Nothing Playing")
    
    duration = song.get('duration', 0)
    total_time = format_duration(duration)
    
    loop_icon = {"off": "➡️ Off", "song": "🔂 Song", "queue": "🔁 Queue"}
    
    # --- HEADER RESTORED ---
    embed = discord.Embed(title="🎵 Now Playing", color=discord.Color.from_rgb(29, 185, 84))
    
    # --- DESCRIPTION (BAR REMOVED) ---
    description = f"**[{song['title']}]({song.get('webpage_url', '')})**\n"
    description += f"{song.get('artist', '')}\n\n"
    description += f"**Duration:** {total_time}" # Only Text, No Bar
    
    embed.description = description
    
    if song.get('thumbnail'): embed.set_thumbnail(url=song['thumbnail'])
    
    # Stats Row
    embed.add_field(name="🔊 Volume", value=f"**{int(data['volume']*100)}%**", inline=True)
    embed.add_field(name="🌀 Loop", value=f"**{loop_icon[data['loop']]}**", inline=True)
    embed.add_field(name="⏳ Queue", value=f"**{len(data['queue'])}**", inline=True)
    
    requester = song.get('requester', 'Unknown')
    embed.set_footer(text=f"Requested by {requester}", icon_url=guild.icon.url if guild.icon else None)
    
    return embed

# --- BUTTONS (5x2 GRID) ---
class MusicDashboard(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.original_interaction = interaction

    async def refresh_ui(self, interaction):
        data = get_data(interaction.guild_id)
        if data['now_playing']:
            await interaction.response.edit_message(embed=create_embed(data, interaction.guild), view=self)

    # ROW 1
    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, row=0) 
    async def btn_rewind(self, interaction, button): await seek_audio(interaction, -10)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0) 
    async def btn_pause(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing(): 
            vc.pause()
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.green
        else: 
            vc.resume()
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.primary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0) 
    async def btn_stop(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc:
            get_data(interaction.guild_id)['queue'] = []
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("Stopped.", ephemeral=False)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0) 
    async def btn_skip(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc: vc.stop()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, row=0) 
    async def btn_forward(self, interaction, button): await seek_audio(interaction, 10)

    # ROW 2
    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.gray, row=1)
    async def btn_voldown(self, interaction, button):
        data = get_data(interaction.guild_id)
        data['volume'] = max(0.0, data['volume'] - 0.1)
        if interaction.guild.voice_client.source: interaction.guild.voice_client.source.volume = data['volume']
        await self.refresh_ui(interaction)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.gray, row=1)
    async def btn_volup(self, interaction, button):
        data = get_data(interaction.guild_id)
        data['volume'] = min(2.0, data['volume'] + 0.1)
        if interaction.guild.voice_client.source: interaction.guild.voice_client.source.volume = data['volume']
        await self.refresh_ui(interaction)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def btn_loop(self, interaction, button):
        data = get_data(interaction.guild_id)
        modes = ['off', 'song', 'queue']
        data['loop'] = modes[(modes.index(data['loop']) + 1) % 3]
        button.style = discord.ButtonStyle.green if data['loop'] != 'off' else discord.ButtonStyle.secondary
        await self.refresh_ui(interaction)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def btn_shuffle(self, interaction, button):
        random.shuffle(get_data(interaction.guild_id)['queue'])
        await interaction.response.send_message("🔀 Shuffled!", ephemeral=True)

    @discord.ui.button(emoji="📜", style=discord.ButtonStyle.gray, row=1)
    async def btn_queue(self, interaction, button):
        data = get_data(interaction.guild_id)
        q_text = "\n".join([f"`{i+1}.` {s['title'][:40]}..." for i, s in enumerate(data['queue'][:10])]) or "Empty"
        embed = discord.Embed(title="Current Queue", description=q_text, color=discord.Color.dark_gray())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def seek_audio(interaction, seconds):
    vc = interaction.guild.voice_client
    data = get_data(interaction.guild_id)
    if not vc or not data['now_playing']: return
    await interaction.response.defer()
    current_play_time = time.time() - data['start_time'] + data['seek_offset']
    new_pos = max(0, current_play_time + seconds)
    data['seek_offset'] = new_pos
    data['start_time'] = time.time()
    data['manual_stop'] = True
    vc.pause()
    await start_playing_ffmpeg(interaction, data['now_playing']['url'], start_sec=new_pos)

# --- COMMANDS ---

@bot.tree.command(name="play", description="Play Song")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        await interaction.followup.send("❌ Join Voice Channel!")
        return
    
    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if vc and vc.channel != channel: await vc.move_to(channel)
    elif not vc: vc = await channel.connect()

    song = {'title': query, 'artist': '', 'url': None, 'thumbnail': None, 'requester': interaction.user.name}
    
    # Try resolve immediately (For Real Title)
    resolved_song = await resolve_song_audio(song)
    if resolved_song: song = resolved_song
    else:
        await interaction.followup.send("❌ Song not found.")
        return

    data = get_data(interaction.guild_id)
    if vc.is_playing() or vc.is_paused():
        data['queue'].append(song)
        embed = discord.Embed(description=f"✅ Added **{song['title']}** to queue.", color=discord.Color.green())
        await interaction.followup.send(embed=embed)
    else:
        data['queue'].insert(0, song)
        await play_next(interaction)

@play.autocomplete('query')
async def play_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current or not sp: return []
    try:
        results = sp.search(q=current, limit=5, type='track')
        return [app_commands.Choice(name=f"{t['name']} - {t['artists'][0]['name']}"[:100], value=f"{t['name']} {t['artists'][0]['name']}") for t in results['tracks']['items']]
    except: return []

@bot.tree.command(name="link", description="Play Playlist")
async def link(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        await interaction.followup.send("❌ Join Voice Channel!")
        return

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if vc and vc.channel != channel: await vc.move_to(channel)
    elif not vc: vc = await channel.connect()

    data = get_data(interaction.guild_id)
    songs_added = []
    requester = interaction.user.name

    if "spotify.com" in url and "playlist" in url and sp:
        try:
            pid = url.split("/")[-1].split("?")[0]
            tracks = sp.playlist_tracks(pid)['items']
            for item in tracks:
                t = item['track']
                songs_added.append({'title': t['name'], 'artist': t['artists'][0]['name'], 'thumbnail': t['album']['images'][0]['url'], 'url': None, 'requester': requester})
            await interaction.followup.send(f"✅ Added {len(songs_added)} songs from Spotify!")
        except: pass
    elif "youtube.com" in url and "list=" in url:
        try:
            with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    for e in info['entries']:
                        songs_added.append({'title': e['title'], 'url': e['url'], 'artist': '', 'thumbnail': None, 'requester': requester})
            await interaction.followup.send(f"✅ Added {len(songs_added)} songs from YouTube!")
        except: pass
    else:
        await play(interaction, query=url)
        return

    if songs_added:
        data['queue'].extend(songs_added)
        if not vc.is_playing() and not vc.is_paused(): await play_next(interaction)

@bot.tree.command(name="stop", description="Stop")
async def stop_cmd(interaction): await MusicDashboard(interaction).btn_stop(interaction, None)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🔥 {bot.user} Ready!")

bot.run(TOKEN)