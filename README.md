<p align="center">
  <h1 align="center">आद्री (Adri) — Personal Voice Assistant</h1>
  <p align="center">
    🎤 A Python-based personal voice assistant that runs <strong>locally on Windows</strong> (8 GB RAM, CPU-only).<br>
    Supports <strong>voice and text input</strong> in English and Nepali, powered by Gemini for reasoning,<br>
    with web search, system commands, Google Classroom integration, class routine lookup, and reminders.
  </p>
</p>

---

## ✨ Features

- 🎤 **Voice & Text Input** — Talk to Adri or type; press Enter to toggle between modes
- 🌐 **Bilingual** — Understands and responds in both **English** and **Nepali** (नेपाली)
- 🔍 **Web Search** — Real-time search via Tavily ("What's the weather in Kathmandu?")
- 💻 **System Commands** — Open apps, URLs, and files ("Open Chrome", "Open google.com")
- 📚 **Google Classroom** — Check assignments, announcements, and deadlines (read-only)
- 📅 **Class Routine** — Know your next class, today's schedule, or any day's timetable
- ⏰ **Reminders** — Set, list, and delete reminders with natural language ("Remind me at 5pm…")
- 💬 **Natural Conversation** — Context-aware chat with memory within a session
- 🔒 **Privacy-Focused** — Runs locally; only API calls leave your machine

---

## 📋 Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or higher |
| **ffmpeg** | Must be installed and on `PATH` ([see below](#installing-ffmpeg)) |
| **Microphone** | Required for voice input (optional if using text-only mode) |
| **Internet** | Required for Gemini API, Edge TTS, and web search |
| **OS** | Windows 10/11 (designed for Windows; may work on Linux/macOS with tweaks) |

### Installing ffmpeg

`faster-whisper` requires ffmpeg for audio processing.

1. Download ffmpeg from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)  
   → Choose **Windows builds** → download the `ffmpeg-release-essentials.zip`
2. Extract the zip to a permanent location, e.g. `C:\ffmpeg`
3. Add the `bin` folder to your system PATH:
   - Search **"Environment Variables"** in Start
   - Under **System variables**, select `Path` → **Edit** → **New**
   - Add `C:\ffmpeg\bin` (adjust to your actual path)
   - Click **OK** and restart your terminal
4. Verify: open a new terminal and run:
   ```bash
   ffmpeg -version
   ```

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/Himal-Joshi/adri--voice-assistant.git
cd adri--voice-assistant

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys (see next section)
```

> [!NOTE]
> The first time you run Adri, `faster-whisper` will download the Whisper model (~150 MB for `base`). This is a one-time download.

---

## 🔑 Getting API Keys

### 1. Gemini API Key (Free)

The Gemini API powers Adri's reasoning and conversation abilities.

1. Go to **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key
5. Paste it into your `.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```

### 2. Tavily API Key (Free — 1,000 searches/month)

Tavily powers Adri's web search capability.

1. Go to **[app.tavily.com](https://app.tavily.com/)**
2. Sign up for a free account
3. Copy your API key from the dashboard
4. Paste it into your `.env` file:
   ```
   TAVILY_API_KEY=your_key_here
   ```

### 3. Google Classroom Setup (Optional)

> [!IMPORTANT]
> This step is **only needed** if you want Adri to read your Google Classroom data. Skip this section if you don't use Google Classroom.

This guide assumes you've never used Google Cloud Console before.

#### Step 1 — Create a Google Cloud Project

1. Go to **[console.cloud.google.com](https://console.cloud.google.com/)**
2. Sign in with the **same Google account** you use for Google Classroom
3. Click the project dropdown (top-left, next to "Google Cloud") → **New Project**
4. Name it `Adri Assistant` (or anything you like) → **Create**
5. Make sure the new project is selected in the dropdown

#### Step 2 — Enable the Google Classroom API

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for **"Google Classroom API"**
3. Click on it → click **Enable**

#### Step 3 — Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type → **Create**
3. Fill in the required fields:
   - **App name**: `Adri Assistant`
   - **User support email**: your email
   - **Developer contact email**: your email
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes** and add:
   - `classroom.courses.readonly`
   - `classroom.coursework.me.readonly`
   - `classroom.announcements.readonly`
6. Click **Save and Continue**
7. On the **Test users** page, click **Add Users**
8. Add your Google email address → **Save**

#### Step 4 — Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Desktop app** as the application type
4. Name it `Adri Desktop`
5. Click **Create**
6. In the dialog, click **Download JSON**
7. Rename the downloaded file to `credentials.json`
8. Move it into the `credentials/` folder in this project

#### Step 5 — First Run

The first time Adri tries to access Classroom, it will:
1. Open your browser for Google sign-in
2. Ask you to grant read-only access to Classroom
3. Save the token locally to `credentials/token.json`

After this, you won't need to sign in again unless the token expires.

> [!TIP]
> If the token expires, simply delete `credentials/token.json` and re-run Adri to re-authenticate.

---

## 📅 Setting Up Your Routine

Adri can tell you your class schedule if you set up a `routine.json` file.

1. A default `data/routine.json` is included with sample data. Edit it with your actual schedule:
   ```bash
   # The file is at: data/routine.json
   # A template is also available at: routine_template.json
   ```

2. The format is straightforward — each day has a list of classes:
   ```json
   {
       "Sunday": [
           {"time": "08:00", "subject": "Mathematics", "room": "Room 101"},
           {"time": "10:00", "subject": "Physics", "room": "Room 203"}
       ],
       "Monday": [
           {"time": "08:00", "subject": "Computer Science", "room": "Lab 1"}
       ]
   }
   ```

3. **Use 24-hour format** for times (`HH:MM`)
4. Days: `Sunday` through `Friday` (add `Saturday` if needed)

---

## ▶️ Running

```bash
# Activate the virtual environment
venv\Scripts\activate

# Start Adri
python main.py
```

Adri will greet you and wait for input. Speak into your microphone or type a command.

---

## 💡 Usage & Example Commands

### 💬 General Conversation
```
"Hello!"
"नमस्ते, कस्तो छ?"
"Tell me a joke"
"What is the capital of Nepal?"
```

### 🔍 Web Search
```
"What's the weather in Kathmandu today?"
"Latest news about Nepal"
"Search for Python tutorials"
```

### 💻 System Commands
```
"Open Chrome"
"Open Spotify"
"Open google.com"
"Open my routine PDF"          # if the file path is known
```

### 📅 Class Routine
```
"What's my schedule for today?"
"What's my next class?"
"What do I have on Monday?"
"Am I free after 2pm?"
```

### 📚 Google Classroom
```
"Any updates in Classroom?"
"What assignments are due this week?"
"Check my Classroom announcements"
"What courses am I enrolled in?"
```

### ⏰ Reminders
```
"Remind me to submit the assignment at 5pm"
"Remind me in 30 minutes to check Classroom"
"What reminders do I have?"
"Delete reminder 3"
```

### 📎 File Sending (Manual Assist)
```
"Send the report to Ram on WhatsApp"
```
> Adri opens WhatsApp and the file location — you attach the file manually.

---

## 📁 Project Structure

```
adri--voice-assistant/
├── main.py                  # 🚀 Entry point — conversation loop
├── stt.py                   # 🎤 Speech-to-text (faster-whisper)
├── tts.py                   # 🔊 Text-to-speech (edge-tts)
├── brain.py                 # 🧠 Gemini API + tool orchestration
├── config.py                # ⚙️  Configuration, paths, constants
├── requirements.txt         # 📦 Python dependencies
├── .env.example             # 🔐 Template for API keys
├── .gitignore               # 🙈 Git ignore rules
├── LICENSE                  # 📄 MIT License
├── routine_template.json    # 📅 Sample routine template
│
├── tools/                   # 🔧 Tool modules (Gemini function-calling)
│   ├── __init__.py
│   ├── web_search.py        #    Tavily web search
│   ├── system_commands.py   #    Open apps, URLs, files
│   ├── classroom.py         #    Google Classroom API (read-only)
│   ├── routine.py           #    Class schedule lookup
│   └── reminders.py         #    Reminder system (set, check, persist)
│
├── data/                    # 💾 Runtime data (user-editable)
│   ├── routine.json         #    Your weekly class schedule
│   └── reminders.json       #    Active reminders (auto-managed)
│
└── credentials/             # 🔑 OAuth credentials (git-ignored)
    ├── credentials.json     #    Google OAuth client secret (you provide)
    └── token.json           #    Cached auth token (auto-generated)
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| **"No microphone found"** | Check Windows Sound Settings → ensure your mic is connected and set as the default input device. |
| **"ffmpeg not found"** | Make sure the ffmpeg `bin/` directory is in your system `PATH`. Restart your terminal after adding it. |
| **Gemini API error** | Verify your `GEMINI_API_KEY` in `.env` is correct. Check your internet connection. Ensure you haven't exceeded rate limits. |
| **Classroom token expired** | Delete `credentials/token.json` and re-run `python main.py` to re-authenticate. |
| **Edge TTS failed** | Edge TTS requires an internet connection. If it fails, Adri will print the response as text in the console as a fallback. |
| **Whisper model download fails** | Check internet connection. The model is downloaded once from Hugging Face on first run (~150 MB for `base`). |
| **High RAM usage** | In `config.py`, switch `WHISPER_MODEL_SIZE` to `"tiny"` (less accurate but uses ~1 GB less RAM). |
| **"Module not found" errors** | Make sure your virtual environment is activated (`venv\Scripts\activate`) and all dependencies are installed (`pip install -r requirements.txt`). |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Copyright © 2026 Himal Joshi

---

<p align="center">
  Made with ❤️ in Nepal 🇳🇵
</p>
