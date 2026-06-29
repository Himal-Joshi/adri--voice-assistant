"""
Adri — Text-to-Speech module.
Generates speech audio using edge-tts and plays it with pygame.
"""

import asyncio
import os
import tempfile
import time

from config import (
    logger,
    TTS_ENGINE,
    TTS_GEMINI_MODEL,
    TTS_GEMINI_VOICE,
    GEMINI_API_KEY,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL_ID,
    TTS_VOICE_EN,
    TTS_VOICE_NE,
    TTS_VOICE_FALLBACK,
)



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


async def _generate_audio_gemini(text: str, output_path: str) -> bool:
    """Generate audio file using Gemini TTS API and save it as a WAV file."""
    try:
        from google import genai
        from google.genai import types
        import wave

        client = genai.Client(api_key=GEMINI_API_KEY)
        
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_GEMINI_VOICE)
                )
            ),
        )

        import asyncio
        loop = asyncio.get_running_loop()
        
        def call_gemini():
            return client.models.generate_content(
                model=TTS_GEMINI_MODEL,
                contents=text,
                config=config
            )
            
        response = await loop.run_in_executor(None, call_gemini)
        
        if not response.candidates:
            logger.error("Gemini TTS returned no candidates.")
            return False
            
        part = response.candidates[0].content.parts[0]
        if not part.inline_data:
            logger.error("Gemini TTS response did not contain inline audio data.")
            return False
            
        audio_bytes = part.inline_data.data
        
        # Write WAV format (16-bit, 24kHz, mono PCM)
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2) # 16-bit
            wav_file.setframerate(24000)
            wav_file.writeframes(audio_bytes)
            
        return True
    except Exception as e:
        logger.error("Gemini TTS failed: %s", e)
        return False


async def _generate_audio_elevenlabs(text: str, output_path: str) -> bool:
    """Generate audio file using ElevenLabs REST API."""
    try:
        import requests
        import asyncio

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        loop = asyncio.get_running_loop()
        def call_elevenlabs():
            return requests.post(url, json=data, headers=headers, timeout=30)

        response = await loop.run_in_executor(None, call_elevenlabs)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            logger.error("ElevenLabs API returned status %d: %s", response.status_code, response.text)
            return False
    except Exception as e:
        logger.error("ElevenLabs TTS failed: %s", e)
        return False


async def _generate_audio(text: str, voice: str) -> str | None:
    """
    Generate audio file using Gemini TTS, ElevenLabs, or edge-tts fallback.
    Returns the path to the generated file, or None on failure.
    The returned file is in the appropriate format (.wav or .mp3).
    """
    # 1. Try Gemini
    if TTS_ENGINE == "gemini" and GEMINI_API_KEY:
        logger.info("Generating voice audio using Gemini TTS (%s)...", TTS_GEMINI_VOICE)
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="adri_tts_")
            os.close(fd)
            success = await _generate_audio_gemini(text, temp_path)
            if success:
                return temp_path
            
            # If Gemini failed, clean up the WAV temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.warning("Gemini TTS failed. Trying fallback engines...")
        except Exception as e:
            logger.warning("Gemini TTS setup failed: %s.", e)

    # 2. Try ElevenLabs
    if (TTS_ENGINE == "elevenlabs" or TTS_ENGINE == "gemini") and ELEVENLABS_API_KEY:
        logger.info("Generating voice audio using ElevenLabs TTS (%s)...", ELEVENLABS_VOICE_ID)
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="adri_tts_")
            os.close(fd)
            success = await _generate_audio_elevenlabs(text, temp_path)
            if success:
                return temp_path
            
            # If ElevenLabs failed, clean up the MP3 temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.warning("ElevenLabs TTS failed. Trying fallback engines...")
        except Exception as e:
            logger.warning("ElevenLabs TTS setup failed: %s.", e)

    # 3. edge-tts fallback / default
    temp_path = None
    try:
        import edge_tts
        fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="adri_tts_")
        os.close(fd)

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_path)
        return temp_path
    except Exception as e:
        logger.warning("edge-tts failed with voice '%s': %s", voice, e)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
                
        # Try fallback voice for Nepali
        if voice == TTS_VOICE_NE:
            try:
                logger.info("Trying fallback voice: %s", TTS_VOICE_FALLBACK)
                fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="adri_tts_")
                os.close(fd)
                communicate = edge_tts.Communicate(text, TTS_VOICE_FALLBACK)
                await communicate.save(temp_path)
                return temp_path
            except Exception as e2:
                logger.error("Fallback voice also failed: %s", e2)
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
        return None



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
    Speak the given text aloud using the configured engine.

    Args:
        text: The text to speak.
        language: Language code (e.g., 'en', 'ne') for voice selection.
    """
    if not text or not text.strip():
        return

    voice = _pick_voice(language)
    logger.info("TTS — voice=%s, text='%s'", voice, text[:80] + ("…" if len(text) > 80 else ""))

    temp_path = None
    try:
        # Run the async generation (internally creates the correctly formatted temp file)
        temp_path = asyncio.run(_generate_audio(text, voice))

        if temp_path and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            _play_audio(temp_path)
        else:
            logger.warning("TTS audio generation failed — printing text instead.")
            print(f"  [Aadri says]: {text}")

    except Exception as e:
        logger.error("TTS error: %s", e)
        print(f"  [Aadri says]: {text}")

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
        # Try to get running loop; if none, create one
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context — run in a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run, _generate_audio(text, voice)
                )
                temp_path = future.result(timeout=30)
        except RuntimeError:
            # No running loop — safe to use asyncio.run
            temp_path = asyncio.run(_generate_audio(text, voice))

        if temp_path and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            _play_audio(temp_path)
        else:
            print(f"  [Aadri says]: {text}")

    except Exception as e:
        logger.error("TTS error: %s", e)
        print(f"  [Aadri says]: {text}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Aadri TTS Test ===")
    speak("Hello! Aadri here, ready to help you out.", language="en")
    print()
    speak("नमस्ते! म Aadri, तपाईंको सहायक।", language="ne")
    print("\nDone.")
