"""Persistent Telegram animation file IDs for Nika's awakened World Boss moves."""
import json
import os
import re
import tempfile

from config import DATA_DIR

NIKA_MOVE_GIFS_PATH = os.path.join(DATA_DIR, "nika_move_gifs.json")
NIKA_MOVE_KEYS = {"bajranggun", "kaminari"}


def normalize_nika_move(value):
    key = re.sub(r"[^a-z0-9]", "", str(value or "").casefold())
    aliases = {
        "bajrang": "bajranggun",
        "bajranggun": "bajranggun",
        "gomugomunobajranggun": "bajranggun",
        "kaminari": "kaminari",
        "gomugomunokaminari": "kaminari",
    }
    return aliases.get(key)


def get_nika_move_gifs():
    try:
        with open(NIKA_MOVE_GIFS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value.strip()
        for key, value in raw.items()
        if key in NIKA_MOVE_KEYS and isinstance(value, str) and value.strip()
    }


def get_nika_move_gif(move):
    key = normalize_nika_move(move)
    return get_nika_move_gifs().get(key) if key else None


def _write_gifs(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="nika_move_gifs_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, NIKA_MOVE_GIFS_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def set_nika_move_gif(move, file_id):
    key = normalize_nika_move(move)
    value = str(file_id or "").strip()
    if not key:
        raise ValueError("Unknown Nika move")
    if not value:
        raise ValueError("A Telegram animation file ID is required")
    data = get_nika_move_gifs()
    data[key] = value
    _write_gifs(data)
    return key


def clear_nika_move_gif(move):
    key = normalize_nika_move(move)
    if not key:
        raise ValueError("Unknown Nika move")
    data = get_nika_move_gifs()
    existed = data.pop(key, None) is not None
    _write_gifs(data)
    return key, existed
