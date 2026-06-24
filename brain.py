"""
Adri — Brain module.
Handles Gemini API integration, tool orchestration, and conversation management.
"""

import json
import time
from typing import Any, Callable

from config import logger, GEMINI_API_KEY, GEMINI_MODEL

# ── System prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are आद्री (Adri), a personal voice assistant built for a student in Nepal.

IDENTITY:
- Your name is Adri (आद्री). Use it naturally in conversation, not robotically.
- You are warm, friendly, concise, and efficient — like a capable personal assistant who knows the user well.
- You have a light sense of personality and warmth, but you stay efficient and on-point.

LANGUAGE:
- You speak both English and Nepali fluently.
- ALWAYS reply in the same language the user spoke to you. If they speak Nepali, reply in Nepali. If English, reply in English. If mixed, match their mix.
- Keep responses concise since they will be spoken aloud — avoid long paragraphs.

TOOLS:
- You have access to several tools: web search, system commands (open apps/URLs/files), Google Classroom, class routine lookup, and reminders.
- Use tools ONLY when the user's request genuinely needs them. For general conversation, just respond normally.
- When using web_search, formulate a clear search query.
- For system commands, identify the app/URL/file the user wants to open.
- For reminders, extract the message and time from the user's request.
- When the user asks to "send" a file to someone via WhatsApp/Telegram/etc., use open_for_manual_send — do NOT claim you can send it automatically. Be honest that you'll open the app and file for them to send manually.

PERSONALITY GUIDELINES:
- Don't start every response with "Hey!" or greetings — only greet at the start of a conversation.
- Be natural. Vary your responses. Don't be repetitive.
- If you don't know something and web search doesn't help, say so honestly.
- For class routine and Classroom queries, present information clearly and briefly.
- When setting reminders, confirm the exact time you understood.
"""

# ── Tool registry ───────────────────────────────────────────────────────────
# Maps function names to their actual Python callables
_tool_functions: dict[str, Callable] = {}
_tool_list: list[Callable] = []


def _register_tools() -> None:
    """Import and register all tool functions."""
    global _tool_functions, _tool_list

    if _tool_functions:
        return  # Already registered

    from tools.web_search import web_search
    from tools.system_commands import (
        open_application,
        open_url,
        open_file,
        open_for_manual_send,
    )
    from tools.classroom import get_classroom_updates
    from tools.routine import get_routine, get_next_class
    from tools.reminders import set_reminder, list_reminders, delete_reminder

    tools = [
        web_search,
        open_application,
        open_url,
        open_file,
        open_for_manual_send,
        get_classroom_updates,
        get_routine,
        get_next_class,
        set_reminder,
        list_reminders,
        delete_reminder,
    ]

    for func in tools:
        _tool_functions[func.__name__] = func
        _tool_list.append(func)
        logger.info("Registered tool: %s", func.__name__)


# ── Gemini client ───────────────────────────────────────────────────────────
_client = None


def _get_client():
    """Initialize the Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not set. Please add it to your .env file."
            )

        from google import genai

        _client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialized (model: %s).", GEMINI_MODEL)
    return _client


# ── Conversation state ─────────────────────────────────────────────────────
_conversation_history: list = []


def clear_history() -> None:
    """Reset conversation history."""
    global _conversation_history
    _conversation_history = []
    logger.info("Conversation history cleared.")


def _execute_tool(function_name: str, function_args: dict[str, Any]) -> Any:
    """Execute a registered tool function and return its result."""
    if function_name not in _tool_functions:
        error_msg = f"Unknown tool: {function_name}"
        logger.error(error_msg)
        return {"error": error_msg}

    func = _tool_functions[function_name]
    logger.info("Calling tool: %s(%s)", function_name, json.dumps(function_args, ensure_ascii=False))

    try:
        result = func(**function_args)
        logger.info("Tool %s returned: %s", function_name, str(result)[:200])
        return result
    except Exception as e:
        error_msg = f"Tool '{function_name}' failed: {e}"
        logger.error(error_msg)
        return {"error": error_msg}


def chat(user_message: str, detected_language: str = "en") -> tuple[str, str]:
    """
    Send a message to Gemini and get a response, handling tool calls.

    Args:
        user_message: The user's text input.
        detected_language: Language detected from STT (for context).

    Returns:
        (response_text, response_language) tuple.
    """
    from google import genai
    from google.genai import types

    _register_tools()
    client = _get_client()

    # Build user content
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )
    _conversation_history.append(user_content)

    # Configure the request
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=_tool_list,
        temperature=0.7,
    )

    max_tool_rounds = 5  # Safety limit for chained tool calls
    retry_count = 0
    max_retries = 2

    while retry_count <= max_retries:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=_conversation_history,
                config=config,
            )
            break
        except Exception as e:
            retry_count += 1
            error_str = str(e).lower()

            if "rate" in error_str or "429" in error_str:
                wait_time = 5 * retry_count
                logger.warning(
                    "Rate limited. Waiting %ds before retry %d/%d…",
                    wait_time,
                    retry_count,
                    max_retries,
                )
                time.sleep(wait_time)
                continue
            elif "network" in error_str or "connection" in error_str:
                logger.error("Network error: %s", e)
                _conversation_history.pop()  # Remove the failed user message
                return (
                    "I'm having trouble connecting to the internet. Please check your connection.",
                    "en",
                )
            else:
                logger.error("Gemini API error: %s", e)
                if retry_count > max_retries:
                    _conversation_history.pop()
                    return (
                        "Sorry, I ran into an issue. Could you try again?",
                        "en",
                    )
                time.sleep(2)
                continue

    # Handle tool calls in a loop
    tool_round = 0
    while tool_round < max_tool_rounds:
        # Check if the response has function calls
        if not response.function_calls:
            break

        tool_round += 1

        # Append the model's response (with function calls) to history
        _conversation_history.append(response.candidates[0].content)

        # Execute each function call and collect results
        tool_response_parts = []
        for call in response.function_calls:
            result = _execute_tool(call.name, dict(call.args))

            # Ensure result is a dict for from_function_response
            if not isinstance(result, dict):
                result = {"result": str(result)}

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response=result,
                )
            )

        # Append tool results to history
        tool_content = types.Content(role="tool", parts=tool_response_parts)
        _conversation_history.append(tool_content)

        # Get the next response from Gemini
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=_conversation_history,
                config=config,
            )
        except Exception as e:
            logger.error("Gemini API error during tool follow-up: %s", e)
            return ("Sorry, something went wrong while processing. Try again?", "en")

    # Extract final text response
    final_text = ""
    if response.text:
        final_text = response.text.strip()

    # Append the final model response to history
    if response.candidates:
        _conversation_history.append(response.candidates[0].content)

    # Determine response language
    response_lang = _detect_response_language(final_text, detected_language)

    # Trim history if it gets too long (keep last 30 turns)
    if len(_conversation_history) > 60:
        _conversation_history[:] = _conversation_history[-30:]
        logger.info("Trimmed conversation history to last 30 entries.")

    return final_text, response_lang


def _detect_response_language(text: str, input_language: str) -> str:
    """
    Simple heuristic to detect if the response is in Nepali or English.
    Falls back to the input language if uncertain.
    """
    if not text:
        return input_language

    # Check for Devanagari characters (Nepali)
    devanagari_count = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha == 0:
        return input_language

    devanagari_ratio = devanagari_count / total_alpha

    if devanagari_ratio > 0.3:
        return "ne"
    return "en"


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Adri Brain Test ===")
    print("Type messages to chat with Adri. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        response, lang = chat(user_input)
        print(f"Adri [{lang}]: {response}\n")
