"""
Adri — System commands tool.
Provides functions to open applications, URLs, and files on Windows.
"""

import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

from config import logger

# ── Common Windows application mappings ─────────────────────────────────────
# Each entry maps a normalised name to a list of possible executable paths
# or names.  The first one that exists (or is found via shutil.which) wins.
APP_MAP: dict[str, list[str]] = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        "firefox",
    ],
    "spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "spotify",
    ],
    "vs code": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "code",
    ],
    "vscode": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "code",
    ],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "file explorer": ["explorer.exe"],
    "word": [
        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
        "winword",
    ],
    "excel": [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        "excel",
    ],
    "powerpoint": [
        r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
        "powerpnt",
    ],
    "task manager": ["taskmgr.exe"],
    "settings": ["ms-settings:"],
    "discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
        "discord",
    ],
    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
        "steam",
    ],
    "telegram": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        "telegram",
    ],
    "obs": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
        "obs64",
    ],
}

# ── Messaging-app URLs for manual send ──────────────────────────────────────
MESSAGING_APP_URLS: dict[str, str] = {
    "whatsapp": "https://web.whatsapp.com/",
    "telegram": "https://web.telegram.org/",
    "discord": "https://discord.com/channels/@me",
    "messenger": "https://www.messenger.com/",
}


def open_application(app_name: str) -> str:
    """Open a desktop application by name on Windows.

    Supports common apps like Chrome, Firefox, Spotify, VS Code, Notepad,
    Calculator, File Explorer, Word, Excel, PowerPoint, Task Manager,
    Settings, Discord, Steam, Telegram, and OBS.

    Args:
        app_name: The human-readable name of the application to open
                  (e.g. 'Chrome', 'VS Code', 'Spotify').

    Returns:
        A confirmation message if the app was opened, or an error message
        if it could not be found or launched.
    """
    key = app_name.strip().lower()
    logger.info("Opening application: '%s'", app_name)

    candidates = APP_MAP.get(key)
    if candidates is None:
        logger.warning("Unknown application: '%s'", app_name)
        return (
            f"I don't know how to open '{app_name}'. "
            "You could tell me the executable name or path instead."
        )

    # --- Attempt 1: os.startfile (handles UWP URIs like ms-settings:) -------
    for path in candidates:
        if path.endswith(":") or os.path.isfile(path):
            try:
                os.startfile(path)
                logger.info("Opened '%s' via os.startfile('%s')", app_name, path)
                return f"Done — {app_name} is opening."
            except OSError as e:
                logger.debug("os.startfile failed for '%s': %s", path, e)

    # --- Attempt 2: subprocess.Popen with known paths -----------------------
    for path in candidates:
        if os.path.isfile(path):
            try:
                subprocess.Popen([path])
                logger.info("Opened '%s' via subprocess ('%s')", app_name, path)
                return f"Done — {app_name} is opening."
            except OSError as e:
                logger.debug("subprocess.Popen failed for '%s': %s", path, e)

    # --- Attempt 3: shutil.which (PATH look-up) -----------------------------
    for name in candidates:
        resolved = shutil.which(name)
        if resolved:
            try:
                subprocess.Popen([resolved])
                logger.info("Opened '%s' via PATH ('%s')", app_name, resolved)
                return f"Done — {app_name} is opening."
            except OSError as e:
                logger.debug("PATH launch failed for '%s': %s", resolved, e)

    logger.error("Could not open '%s' — all candidates exhausted", app_name)
    return (
        f"Sorry, I couldn't open {app_name}. "
        "It may not be installed, or it's in a non-standard location."
    )


def open_url(url: str) -> str:
    """Open a URL in the default web browser.

    Args:
        url: The URL to open (e.g. 'https://google.com').

    Returns:
        A confirmation message indicating the URL was opened.
    """
    logger.info("Opening URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Done — opened {url} in your browser."
    except Exception as e:
        logger.error("Failed to open URL '%s': %s", url, e)
        return f"Error: Could not open the URL — {e}"


def open_file(file_path: str) -> str:
    """Open a file using the system's default application.

    Args:
        file_path: The absolute or relative path to the file to open.

    Returns:
        A confirmation message if the file was opened, or an error message
        if the file does not exist or cannot be opened.
    """
    logger.info("Opening file: %s", file_path)

    path = Path(file_path)
    if not path.exists():
        logger.warning("File not found: %s", file_path)
        return f"Error: The file '{file_path}' does not exist."
    if not path.is_file():
        logger.warning("Path is not a file: %s", file_path)
        return f"Error: '{file_path}' is not a file."

    try:
        os.startfile(str(path.resolve()))
        return f"Done — opened {path.name}."
    except OSError as e:
        logger.error("Failed to open file '%s': %s", file_path, e)
        return f"Error: Could not open the file — {e}"


def open_for_manual_send(app_name: str, file_path: str, recipient: str) -> str:
    """Open a messaging app and the file's directory so the user can manually
    attach and send the file.

    Supported messaging apps: WhatsApp (web), Telegram (web), Discord (web),
    Messenger (web).

    Args:
        app_name: Name of the messaging app (e.g. 'WhatsApp', 'Telegram').
        file_path: Path to the file the user wants to send.
        recipient: Name of the person or group to send the file to.

    Returns:
        A step-by-step instruction message telling the user how to complete
        the send, or an error message if something went wrong.
    """
    logger.info(
        "Manual send setup — app: '%s', file: '%s', recipient: '%s'",
        app_name, file_path, recipient,
    )

    key = app_name.strip().lower()
    url = MESSAGING_APP_URLS.get(key)

    # Validate the file
    path = Path(file_path)
    if not path.exists():
        return f"Error: The file '{file_path}' does not exist."
    if not path.is_file():
        return f"Error: '{file_path}' is not a file."

    # Open the messaging app (web or desktop)
    if url:
        webbrowser.open(url)
        app_label = f"{app_name} (web)"
    else:
        result = open_application(app_name)
        if result.startswith("Sorry") or result.startswith("I don't know"):
            return result
        app_label = app_name

    # Open File Explorer highlighting the file
    try:
        subprocess.Popen(["explorer", "/select,", str(path.resolve())])
    except OSError as e:
        logger.error("Failed to open File Explorer: %s", e)
        return f"I opened {app_label}, but couldn't open the file location — {e}"

    return (
        f"I've opened {app_label} and highlighted the file in File Explorer.\n"
        f"Please send '{path.name}' to {recipient} manually:\n"
        f"  1. Go to your chat with {recipient} in {app_name}.\n"
        f"  2. Drag the file from Explorer into the chat (or use the attach button).\n"
        f"  3. Hit send!"
    )


if __name__ == "__main__":
    print(open_application("notepad"))
    print(open_url("https://example.com"))
    print(open_file(__file__))
