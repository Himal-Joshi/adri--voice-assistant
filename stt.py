"""
Adri — Speech-to-Text module.
Records audio from the microphone and transcribes it using faster-whisper.
"""

import io
import tempfile
import numpy as np
from pathlib import Path

from config import (
    logger,
    WHISPER_MODEL_SIZE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    SAMPLE_RATE,
    CHANNELS,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MAX_RECORD_SECONDS,
)

# ── Lazy-loaded Whisper model ───────────────────────────────────────────────
_model = None


def _get_model():
    """Load the Whisper model on first use and cache it."""
    global _model
    if _model is None:
        logger.info(
            "Loading Whisper '%s' model (compute_type=%s) — this may take a moment…",
            WHISPER_MODEL_SIZE,
            WHISPER_COMPUTE_TYPE,
        )
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded successfully.")
    return _model


def record_audio() -> np.ndarray | None:
    """
    Record audio from the default microphone until silence is detected.

    Returns:
        numpy array of recorded audio (int16, 16kHz mono), or None on failure.
    """
    try:
        import sounddevice as sd
    except Exception as e:
        logger.error("Could not import sounddevice: %s", e)
        return None

    try:
        # Verify a microphone is available
        device_info = sd.query_devices(kind="input")
        logger.info("Using input device: %s", device_info["name"])
    except Exception:
        logger.error(
            "No microphone found. Please connect a microphone or use text input."
        )
        return None

    chunk_duration = 0.1  # 100ms chunks
    chunk_samples = int(SAMPLE_RATE * chunk_duration)
    max_chunks = int(MAX_RECORD_SECONDS / chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)

    recorded_chunks: list[np.ndarray] = []
    silence_counter = 0
    has_speech = False

    print("  🎤 Listening… (speak now, silence stops recording)")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_samples,
        ) as stream:
            for _ in range(max_chunks):
                chunk, _overflowed = stream.read(chunk_samples)
                recorded_chunks.append(chunk.copy())

                # Calculate RMS energy
                energy = np.sqrt(np.mean(chunk**2))

                if energy > SILENCE_THRESHOLD:
                    silence_counter = 0
                    has_speech = True
                else:
                    silence_counter += 1

                # Stop after enough silence ONLY if we've heard speech
                if has_speech and silence_counter >= silence_chunks_needed:
                    break

    except Exception as e:
        logger.error("Error during audio recording: %s", e)
        return None

    if not has_speech:
        logger.warning("No speech detected in recording.")
        return None

    # Concatenate and convert to int16
    audio = np.concatenate(recorded_chunks, axis=0).flatten()
    audio_int16 = (audio * 32767).astype(np.int16)

    duration = len(audio_int16) / SAMPLE_RATE
    print(f"  ✓ Recorded {duration:.1f}s of audio.")
    return audio_int16


def transcribe(audio: np.ndarray) -> tuple[str, str]:
    """
    Transcribe audio using faster-whisper.

    Args:
        audio: numpy array of int16 audio at 16kHz.

    Returns:
        (transcribed_text, detected_language) tuple.
        Returns ("", "unknown") on failure.
    """
    model = _get_model()

    # Convert int16 to float32 for whisper
    audio_float = audio.astype(np.float32) / 32768.0

    try:
        segments, info = model.transcribe(
            audio_float,
            language=None,  # auto-detect
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        text = " ".join(text_parts).strip()
        lang = info.language if info.language else "unknown"
        prob = info.language_probability

        logger.info("STT result — lang=%s (%.0f%%), text='%s'", lang, prob * 100, text)
        return text, lang

    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return "", "unknown"


def listen() -> tuple[str, str]:
    """
    Full pipeline: record from microphone → transcribe.

    Returns:
        (transcribed_text, detected_language) tuple.
        Returns ("", "unknown") if anything fails.
    """
    audio = record_audio()
    if audio is None:
        return "", "unknown"

    return transcribe(audio)


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Adri STT Test ===")
    print("Press Enter to start recording, then speak…")
    input()
    text, lang = listen()
    if text:
        print(f"\nDetected language: {lang}")
        print(f"Transcription: {text}")
    else:
        print("\nNo speech detected or transcription failed.")
