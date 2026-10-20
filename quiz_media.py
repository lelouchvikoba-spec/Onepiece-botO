"""Persistent media configuration for automatic quiz announcements."""
import json
import os
import tempfile

from config import DATA_DIR

QUIZ_MEDIA_PATH = os.path.join(DATA_DIR, "quiz_drop_media.json")
_ALLOWED = {"sticker", "gif", "emoji"}


def get_quiz_drop_media():
    try:
        with open(QUIZ_MEDIA_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        key: value.strip()
        for key, value in data.items()
        if key in _ALLOWED and isinstance(value, str) and value.strip()
    }


def set_quiz_drop_media(kind, value):
    kind = str(kind or "").casefold()
    value = str(value or "").strip()
    if kind not in _ALLOWED:
        raise ValueError("Media type needs to be sticker, gif, or emoji")
    if not value:
        raise ValueError("Value can't be empty")
    data = get_quiz_drop_media()
    data[kind] = value
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="quiz_drop_media_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, QUIZ_MEDIA_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def clear_quiz_drop_media(kind):
    kind = str(kind or "").casefold()
    if kind not in _ALLOWED:
        raise ValueError("Media type needs to be sticker, gif, or emoji")
    data = get_quiz_drop_media()
    existed = data.pop(kind, None) is not None
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="quiz_drop_media_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, QUIZ_MEDIA_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return existed
