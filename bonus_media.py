"""Persistent emoji, sticker, and animation settings for weekly bonus rewards."""
import json
import os
import tempfile

from config import DATA_DIR

BONUS_MEDIA_PATH = os.path.join(DATA_DIR, "bonus_media.json")


def get_bonus_media():
    try:
        with open(BONUS_MEDIA_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "gif": str(raw.get("gif") or "").strip(),
        "sticker": str(raw.get("sticker") or "").strip(),
        "emoji": str(raw.get("emoji") or "").strip(),
    }


def _save_media(**updates):
    settings = get_bonus_media()
    settings.update(updates)
    settings = {key: value for key, value in settings.items() if value}
    os.makedirs(DATA_DIR, exist_ok=True)
    if not settings:
        try:
            os.remove(BONUS_MEDIA_PATH)
        except FileNotFoundError:
            pass
        return
    fd, temp_path = tempfile.mkstemp(prefix="bonus_media_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, BONUS_MEDIA_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def set_bonus_gif(file_id):
    value = str(file_id or "").strip()
    if not value:
        raise ValueError("A Telegram animation file ID is required")
    _save_media(gif=value)


def clear_bonus_gif():
    existed = bool(get_bonus_media().get("gif"))
    _save_media(gif="")
    return existed


def set_bonus_sticker(file_id):
    value = str(file_id or "").strip()
    if not value:
        raise ValueError("A Telegram sticker file ID is required")
    _save_media(sticker=value)


def clear_bonus_sticker():
    existed = bool(get_bonus_media().get("sticker"))
    _save_media(sticker="")
    return existed


def set_bonus_emoji(value):
    value = str(value or "").strip()
    if not value:
        raise ValueError("An emoji is required")
    _save_media(emoji=value)


def clear_bonus_emoji():
    existed = bool(get_bonus_media().get("emoji"))
    _save_media(emoji="")
    return existed
