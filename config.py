"""
Adri — Configuration module.
Loads environment variables and defines app-wide constants.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CREDENTIALS_DIR = BASE_DIR / "credentials"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_DIR.mkdir(exist_ok=True)

# ── Load .env ───────────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env")

# Ensure ffmpeg is on PATH (especially if newly installed via winget in this session)
import shutil
if not shutil.which("ffmpeg"):
    winget_ffmpeg_root = Path(os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Packages"))
    if winget_ffmpeg_root.exists():
        for p in winget_ffmpeg_root.glob("Gyan.FFmpeg.Essentials_*/**/bin"):
            if (p / "ffmpeg.exe").exists():
                os.environ["PATH"] += os.pathsep + str(p)
                break

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")



# ── Gemini ──────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-2.5-flash"

# ── Whisper (STT) ──────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "base"          # "tiny", "base", or "small"
WHISPER_COMPUTE_TYPE: str = "int8"        # int8 halves RAM usage on CPU
WHISPER_DEVICE: str = "cpu"

# ── Audio recording ─────────────────────────────────────────────────────────
SAMPLE_RATE: int = 16000                  # 16 kHz — Whisper expects this
CHANNELS: int = 1                         # mono
SILENCE_THRESHOLD: float = 0.01          # energy threshold for silence detection
SILENCE_DURATION: float = 1.5            # seconds of silence before stopping
MAX_RECORD_SECONDS: int = 30             # safety cap for recording length

# ── TTS Settings ────────────────────────────────────────────────────────────
TTS_ENGINE: str = "gemini"               # "gemini" (high quality), "elevenlabs" (premium), or "edge" (free, local)
TTS_GEMINI_MODEL: str = "gemini-3.1-flash-tts-preview"
TTS_GEMINI_VOICE: str = "Aoede"          # Aoede, Kore, Puck, Fenrir, Charon

# ── ElevenLabs Settings ──────────────────────────────────────────────────────
ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM" # Rachel (natural female voice)

ELEVENLABS_MODEL_ID: str = "eleven_flash_v2_5"


# ── edge-tts voices (for fallback or "edge" engine) ────────────────────────
TTS_VOICE_EN: str = "en-US-AriaNeural"
TTS_VOICE_NE: str = "ne-NP-HemkalaNeural"
TTS_VOICE_FALLBACK: str = "ne-NP-SagarNeural"   # Male Nepali fallback for edge-tts



# ── Data files ──────────────────────────────────────────────────────────────
ROUTINE_FILE: Path = DATA_DIR / "routine.json"
REMINDERS_FILE: Path = DATA_DIR / "reminders.json"

# ── Google Classroom OAuth ──────────────────────────────────────────────────
CLASSROOM_CREDENTIALS_FILE: Path = CREDENTIALS_DIR / "credentials.json"
CLASSROOM_TOKEN_FILE: Path = CREDENTIALS_DIR / "token.json"
CLASSROOM_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
]

# ── Logging ─────────────────────────────────────────────────────────────────
LOG_FORMAT = "[Adri] %(asctime)s │ %(levelname)-7s │ %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure console logging with the Adri prefix."""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


# Auto-setup logging on import
setup_logging()
logger = logging.getLogger("adri")
