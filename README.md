# 🎵 Buzzard Music Bot

A high-performance, feature-rich Discord Music Bot built with Python.
It supports playing music from YouTube and Spotify (Tracks & Playlists) with a beautiful interactive Dashboard UI.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0%2B-blurple)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Static-green)

---

## ✨ Features

- 🎶 Hybrid Search – YouTube Search, YouTube Links, Spotify Tracks & Playlists
- 🎛️ Interactive Dashboard – 5×2 Button Grid (Pause, Resume, Skip, Stop, Volume, Loop, Shuffle, Seek)
- 🧠 Smart Queue – Lazy-loading for large playlists (100+ songs instantly)
- ⏩ Seek Control – Rewind / Forward 10 seconds
- 🔁 Loop Modes – Song Loop, Queue Loop, or Loop Off
- 🖼️ Visual Interface – Thumbnail, requester, duration & volume display
- 🔌 Auto Disconnect – Leaves when alone or queue is empty

---

## 🚀 Installation & Setup

### ✅ 1. Prerequisites
- Python 3.8+
- FFmpeg (Static Build)
- Discord Bot Token
- Spotify Client ID & Client Secret

---

### 📥 2. Clone the Repository
git clone https://github.com/yourusername/buzzard-music-bot.git
cd buzzard-music-bot

---

### 📦 3. Install Dependencies
pip install discord.py yt-dlp spotipy PyNaCl

---

### 🎧 4. FFmpeg Setup (IMPORTANT)
1. Download Static Build (Essentials) from https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip
3. Open bin folder
4. Copy ffmpeg.exe
5. Paste ffmpeg.exe into the same folder as main.py
Do NOT use shared builds

---

### 🔧 5. Configuration
Open main.py and set:

TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
SPOTIFY_ID = 'YOUR_SPOTIFY_CLIENT_ID'
SPOTIFY_SECRET = 'YOUR_SPOTIFY_CLIENT_SECRET'

---

## ▶️ Usage
python main.py

---

## 🎮 Slash Commands

/play [query]      → Play music from YouTube or Spotify
/link [url]        → Load YouTube / Spotify playlist
/stop              → Stop playback and clear queue
/skip              → Skip current song
/pause             → Pause music
/resume            → Resume playback
/volume [0-100]    → Adjust volume
/loop [off/song/queue] → Set loop mode
/shuffle           → Shuffle the queue
/queue             → Show upcoming songs
/seek [seconds]    → Jump to timestamp

---

## 🛠️ Troubleshooting

avformat-62.dll was not found
→ You are using a shared FFmpeg build
→ Download Static FFmpeg (Essentials):
https://www.gyan.dev/ffmpeg/builds/

---

## 📜 License
MIT License

⭐ Star the repo if you love music bots
EOF

---

## 👤 Author

<div align="center">

Made with ❤️ by [Balaharish](https://balaharish.netlify.app)  
🔗 GitHub: [Balax-24](https://github.com/balax-24)

</div>
