"""
Adri — Main entry point.
Runs the voice assistant conversation loop with voice/text input support.
"""

import signal
import sys
import threading
import time
import random

from config import logger


# ── Banner ──────────────────────────────────────────────────────────────────
BANNER = r"""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║       आद्री  —  Aadri Voice Assistant              ║
    ║       ─────────────────────────────                ║
    ║       Your personal assistant for                  ║
    ║       English & Nepali                             ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
"""

GREETINGS_EN = [
    "Hey! Aadri here, ready when you are.",
    "Hi there! Aadri at your service.",
    "Hello! Aadri here — what can I help with?",
    "Aadri here! What's up?",
]

GREETINGS_NE = [
    "नमस्ते! Aadri तयार छ, भन्नुहोस्।",
    "नमस्ते! Aadri यहाँ छ — कसरी मद्दत गर्न सक्छु?",
]

GOODBYES_EN = [
    "See you later! Take care.",
    "Bye! Aadri signing off.",
    "Catch you later!",
]

GOODBYES_NE = [
    "फेरि भेटौंला!",
    "बिदा! ख्याल राख्नुहोस्।",
]


def _startup_greeting() -> tuple[str, str]:
    """Pick a random startup greeting."""
    if random.random() < 0.3:
        return random.choice(GREETINGS_NE), "ne"
    return random.choice(GREETINGS_EN), "en"


def _goodbye_message() -> tuple[str, str]:
    """Pick a random goodbye message."""
    if random.random() < 0.3:
        return random.choice(GOODBYES_NE), "ne"
    return random.choice(GOODBYES_EN), "en"


# ── Reminder background thread ─────────────────────────────────────────────
_reminder_thread: threading.Thread | None = None
_reminder_stop_event = threading.Event()


def _reminder_checker():
    """Background loop that checks for due reminders every 30 seconds."""
    from tools.reminders import check_due_reminders
    from tts import speak_async_compatible

    logger.info("Reminder checker started (checking every 30s).")

    while not _reminder_stop_event.is_set():
        try:
            due = check_due_reminders()
            for reminder in due:
                msg = reminder.get("message", "Reminder!")
                notification = f"⏰ Reminder: {msg}"
                print(f"\n  {notification}")
                logger.info("Reminder triggered: %s", msg)
                try:
                    speak_async_compatible(f"Reminder: {msg}", "en")
                except Exception as e:
                    logger.error("Failed to speak reminder: %s", e)
        except Exception as e:
            logger.error("Reminder checker error: %s", e)

        # Wait 30 seconds, but check the stop event frequently
        _reminder_stop_event.wait(timeout=30)

    logger.info("Reminder checker stopped.")


def _start_reminder_thread():
    """Start the background reminder checker thread."""
    global _reminder_thread
    _reminder_thread = threading.Thread(target=_reminder_checker, daemon=True)
    _reminder_thread.start()


def _stop_reminder_thread():
    """Signal the reminder thread to stop."""
    _reminder_stop_event.set()
    if _reminder_thread:
        _reminder_thread.join(timeout=5)


# ── Input handling ──────────────────────────────────────────────────────────
def _get_input_mode() -> str:
    """Ask the user for input mode."""
    while True:
        try:
            choice = input("\n  [V]oice  [T]ext  [Q]uit → ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "q"

        if choice in ("v", "voice"):
            return "v"
        elif choice in ("t", "text"):
            return "t"
        elif choice in ("q", "quit", "exit"):
            return "q"
        else:
            print("  Please type V, T, or Q.")


def _get_voice_input() -> tuple[str, str]:
    """Record and transcribe voice input."""
    from stt import listen

    text, lang = listen()
    if text:
        print(f"  📝 You said: {text}")
    return text, lang


def _get_text_input() -> tuple[str, str]:
    """Read text input from stdin."""
    try:
        text = input("  You: ").strip()
    except (EOFError, KeyboardInterrupt):
        return "", "en"

    if not text:
        return "", "en"

    # Simple heuristic: check for Devanagari characters
    devanagari_count = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    lang = "ne" if devanagari_count > len(text) * 0.2 else "en"

    return text, lang


# ── Main loop ──────────────────────────────────────────────────────────────
def main():
    """Run the Adri voice assistant."""
    from tts import speak
    from brain import chat

    # Print banner
    print(BANNER)

    # Validate config
    from config import GEMINI_API_KEY

    if not GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY not found!")
        print("  Please copy .env.example to .env and add your API key.")
        print("  Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    # Start reminder background thread
    _start_reminder_thread()

    # Startup greeting
    greeting, greeting_lang = _startup_greeting()
    print(f"\n  🤖 {greeting}\n")
    try:
        speak(greeting, greeting_lang)
    except Exception as e:
        logger.warning("Could not speak greeting: %s", e)

    # Main conversation loop
    try:
        while True:
            mode = _get_input_mode()

            if mode == "q":
                break

            # Get user input
            if mode == "v":
                user_text, detected_lang = _get_voice_input()
            else:
                user_text, detected_lang = _get_text_input()

            if not user_text:
                print("  (No input detected — try again.)")
                continue

            # Send to brain
            print("  ⏳ Thinking…")
            try:
                response_text, response_lang = chat(user_text, detected_lang)
            except Exception as e:
                logger.error("Brain error: %s", e)
                response_text = "Sorry, I ran into a problem. Could you try again?"
                response_lang = "en"

            if not response_text:
                response_text = "Hmm, I don't have a response for that. Could you rephrase?"
                response_lang = "en"

            # Display and speak response
            print(f"\n  🤖 Aadri: {response_text}\n")
            try:
                speak(response_text, response_lang)
            except Exception as e:
                logger.warning("TTS failed: %s (response was printed above)", e)

    except KeyboardInterrupt:
        print("\n")

    # Shutdown
    _stop_reminder_thread()

    goodbye, goodbye_lang = _goodbye_message()
    print(f"\n  🤖 {goodbye}\n")
    try:
        speak(goodbye, goodbye_lang)
    except Exception:
        pass

    logger.info("Adri shut down.")


# ── Handle Ctrl+C gracefully ───────────────────────────────────────────────
def _signal_handler(sig, frame):
    """Handle SIGINT gracefully."""
    print("\n  (Caught Ctrl+C — shutting down…)")
    _stop_reminder_thread()

    from tts import speak

    goodbye, lang = _goodbye_message()
    print(f"\n  🤖 {goodbye}\n")
    try:
        speak(goodbye, lang)
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)


if __name__ == "__main__":
    main()
