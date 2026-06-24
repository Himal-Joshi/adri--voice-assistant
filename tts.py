"""
Adri — Text-to-Speech module.
Generates speech audio using edge-tts and plays it with pygame.
"""

import asyncio
import os
import tempfile
import time

from config import logger, TTS_VOICE_EN, TTS_VOICE_NE, TTS_VOICE_FALLBACK

# ── Pygame mixer (lazy init) ───────────────────────────────────────────────
_mixer_initialized = False


def _ensure_mixer():
    """Initialize pygame mixer once."""
    global _mixer_initialized
    if not _mixer_initialized:
        try:
            import pygame

            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
            _mixer_initialized = True
            logger.info("Audio playback initialized.")
        except Exception as e:
            logger.error("Failed to initialize audio playback: %s", e)
            raise


def _pick_voice(language: str) -> str:
    """Select the appropriate TTS voice based on detected language."""
    lang = language.lower().strip()
    if lang in ("ne", "nep", "nepali", "hi", "hin", "hindi"):
        return TTS_VOICE_NE
    return TTS_VOICE_EN


async def _generate_audio(text: str, voice: str, output_path: str) -> bool:
    """Generate audio file using edge-tts."""
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logger.warning("edge-tts failed with voice '%s': %s", voice, e)
        # Try fallback voice for Nepali
        if voice == TTS_VOICE_NE:
            try:
                logger.info("Trying fallback voice: %s", TTS_VOICE_FALLBACK)
                communicate = edge_tts.Communicate(text, TTS_VOICE_FALLBACK)
                await communicate.save(output_path)
                return True
            except Exception as e2:
                logger.error("Fallback voice also failed: %s", e2)
        return False


def _play_audio(file_path: str) -> None:
    """Play an audio file using pygame mixer."""
    import pygame

    _ensure_mixer()
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        logger.error("Audio playback failed: %s", e)
    finally:
        pygame.mixer.music.unload()


def speak(text: str, language: str = "en") -> None:
    """
    Speak the given text aloud using edge-tts.

    Args:
        text: The text to speak.
        language: Language code (e.g., 'en', 'ne') for voice selection.
    """
    if not text or not text.strip():
        return

    voice = _pick_voice(language)
    logger.info("TTS — voice=%s, text='%s'", voice, text[:80] + ("…" if len(text) > 80 else ""))

    # Generate audio to a temp file
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="adri_tts_")
        os.close(fd)

        # Run the async generation
        success = asyncio.run(_generate_audio(text, voice, temp_path))

        if success and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            _play_audio(temp_path)
        else:
            logger.warning("TTS audio generation failed — printing text instead.")
            print(f"  [Adri says]: {text}")

    except Exception as e:
        logger.error("TTS error: %s", e)
        print(f"  [Adri says]: {text}")

    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def speak_async_compatible(text: str, language: str = "en") -> None:
    """
    Same as speak(), but safe to call from within an existing async context.
    Uses a new event loop in a thread if needed.
    """
    if not text or not text.strip():
        return

    voice = _pick_voice(language)
    logger.info("TTS — voice=%s, text='%s'", voice, text[:80] + ("…" if len(text) > 80 else ""))

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="adri_tts_")
        os.close(fd)

        # Try to get running loop; if none, create one
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context — run in a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run, _generate_audio(text, voice, temp_path)
                )
                success = future.result(timeout=30)
        except RuntimeError:
            # No running loop — safe to use asyncio.run
            success = asyncio.run(_generate_audio(text, voice, temp_path))

        if success and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            _play_audio(temp_path)
        else:
            print(f"  [Adri says]: {text}")

    except Exception as e:
        logger.error("TTS error: %s", e)
        print(f"  [Adri says]: {text}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Adri TTS Test ===")
    speak("Hello! Adri here, ready to help you out.", language="en")
    print()
    speak("नमस्ते! म Adri, तपाईंको सहायक।", language="ne")
    print("\nDone.")
