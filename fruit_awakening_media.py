"""Persistent Telegram activation GIFs for fruit awakenings."""
import json
import os
import tempfile

from config import DATA_DIR

FRUIT_AWAKENING_GIFS_PATH = os.path.join(DATA_DIR, "fruit_awakening_gifs.json")
AWAKENING_KEYS = {"ito", "mochi", "jiki", "gomu"}
AWAKENING_ALIASES = {
    "ito": "ito", "itoito": "ito", "itoitonomi": "ito",
    "mochi": "mochi", "mochimochi": "mochi", "mochimochinomi": "mochi",
    "jiki": "jiki", "jikijiki": "jiki", "jikijikinomi": "jiki",
    "gomu": "gomu", "snakeman": "gomu", "gomugomu": "gomu", "gomugomunomi": "gomu",
}


def normalize_awakening(value):
    normalized = "".join(ch for ch in str(value or "").casefold() if ch.isalnum())
    return AWAKENING_ALIASES.get(normalized)


def get_fruit_awakening_gifs():
    try:
        with open(FRUIT_AWAKENING_GIFS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value.strip()
        for key, value in raw.items()
        if key in AWAKENING_KEYS and isinstance(value, str) and value.strip()
    }


def get_fruit_awakening_gif(awakening):
    key = normalize_awakening(awakening)
    return get_fruit_awakening_gifs().get(key) if key else None


def _write_gifs(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="fruit_awakening_gifs_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, FRUIT_AWAKENING_GIFS_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def set_fruit_awakening_gif(awakening, file_id):
    key = normalize_awakening(awakening)
    value = str(file_id or "").strip()
    if not key:
        raise ValueError("Choose ito, mochi, jiki, or gomu/snakeman")
    if not value:
        raise ValueError("A Telegram animation file ID is required")
    data = get_fruit_awakening_gifs()
    data[key] = value
    _write_gifs(data)
    return key


def clear_fruit_awakening_gif(awakening):
    key = normalize_awakening(awakening)
    if not key:
        raise ValueError("Choose ito, mochi, jiki, or gomu/snakeman")
    data = get_fruit_awakening_gifs()
    existed = data.pop(key, None) is not None
    _write_gifs(data)
    return key, existed
