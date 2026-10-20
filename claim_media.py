"""Persistent sticker, emoji, and animation settings for successful /claim rewards."""
import json
import os
import tempfile

from config import DATA_DIR

CLAIM_GIF_PATH = os.path.join(DATA_DIR, "claim_reward_gif.json")


def get_claim_reward_media():
    try:
        with open(CLAIM_GIF_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "file_id": str(raw.get("file_id") or "").strip(),
        "sticker_file_id": str(raw.get("sticker_file_id") or "").strip(),
        "emoji": str(raw.get("emoji") or "").strip(),
    }


def _save_media(**updates):
    settings = get_claim_reward_media()
    settings.update(updates)
    settings = {key: value for key, value in settings.items() if value}
    os.makedirs(DATA_DIR, exist_ok=True)
    if not settings:
        try:
            os.remove(CLAIM_GIF_PATH)
        except FileNotFoundError:
            pass
        return
    fd, temp_path = tempfile.mkstemp(prefix="claim_reward_media_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, CLAIM_GIF_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_claim_reward_gif():
    return get_claim_reward_media().get("file_id") or None


def set_claim_reward_gif(file_id):
    value = str(file_id or "").strip()
    if not value:
        raise ValueError("A Telegram animation file ID is required")
    _save_media(file_id=value)


def clear_claim_reward_gif():
    existed = bool(get_claim_reward_gif())
    _save_media(file_id="")
    return existed


def get_claim_reward_sticker():
    return get_claim_reward_media().get("sticker_file_id") or None


def set_claim_reward_sticker(file_id):
    value = str(file_id or "").strip()
    if not value:
        raise ValueError("A Telegram sticker file ID is required")
    _save_media(sticker_file_id=value)


def clear_claim_reward_sticker():
    existed = bool(get_claim_reward_sticker())
    _save_media(sticker_file_id="")
    return existed


def get_claim_reward_emoji():
    return get_claim_reward_media().get("emoji") or ""


def set_claim_reward_emoji(emoji):
    value = str(emoji or "").strip()
    if not value:
        raise ValueError("An emoji is required")
    _save_media(emoji=value)


def clear_claim_reward_emoji():
    existed = bool(get_claim_reward_emoji())
    _save_media(emoji="")
    return existed


async def send_claim_reward_sticker(client, chat_id, reply_to_message_id=None):
    """Send the configured claim sticker; return False when unset or unavailable."""
    file_id = get_claim_reward_sticker()
    if not file_id:
        return False
    try:
        await client.send_sticker(
            chat_id,
            file_id,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as exc:
        print(f"[claim reward sticker] failed to send: {exc}")
        return False
    return True


async def send_claim_reward_animation(client, chat_id, caption, reply_to_message_id=None):
    """Send the configured claim animation; return False when unset or unavailable."""
    file_id = get_claim_reward_gif()
    if not file_id:
        return False
    try:
        await client.send_animation(
            chat_id,
            file_id,
            caption=caption,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as exc:
        print(f"[claim reward GIF] failed to send: {exc}")
        return False
    return True
