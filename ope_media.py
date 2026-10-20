"""Persistent Telegram animation file IDs for Ope Ope awakened World Boss moves."""
import json
import os
import re
import tempfile

from config import DATA_DIR

OPE_GIFS_PATH = os.path.join(DATA_DIR, "ope_ope_gif.json")
OPE_AWAKENED_MOVES = {"kroomtact", "shockwille"}


def normalize_ope_move(value):
    key = re.sub(r"[^a-z0-9]", "", str(value or "").casefold())
    aliases = {
        "kroom": "kroomtact",
        "tact": "kroomtact",
        "kroomtact": "kroomtact",
        "kroomtactics": "kroomtact",
        "shockwille": "shockwille",
        "shockwill": "shockwille",
    }
    return aliases.get(key)


def get_ope_awakening_gifs():
    try:
        with open(OPE_GIFS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value.strip()
        for key, value in raw.items()
        if key in OPE_AWAKENED_MOVES and isinstance(value, str) and value.strip()
    }


def get_ope_awakening_gif(move):
    key = normalize_ope_move(move)
    return get_ope_awakening_gifs().get(key) if key else None


def _write_gifs(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="ope_ope_gif_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, OPE_GIFS_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def set_ope_awakening_gif(move, file_id):
    key = normalize_ope_move(move)
    value = str(file_id or "").strip()
    if not key:
        raise ValueError("Only K-Room (Tact) and Shock Wille have configurable GIFs")
    if not value:
        raise ValueError("A Telegram animation file ID is required")
    data = get_ope_awakening_gifs()
    data[key] = value
    _write_gifs(data)
    return key


def clear_ope_awakening_gif(move):
    key = normalize_ope_move(move)
    if not key:
        raise ValueError("Unknown Ope Ope awakened move")
    data = get_ope_awakening_gifs()
    existed = data.pop(key, None) is not None
    _write_gifs(data)
    return key, existed
