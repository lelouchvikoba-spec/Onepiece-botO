# admin.py
import asyncio
import json
import os
import re
import time
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, OWNER_ID, MAIN_GROUP_ID, UPDATE_CHANNEL_ID, BOT_VERSION,
    TIMEZONE,
)
from data_manager import (
    get_player, save_data, user_data, ADMINS, GBANNED, TEMP_BANNED,
    save_admins, save_banned, save_temp_banned, check_temp_bans,
    normal_characters, mythical_characters, exalted_characters, custom_rarities,
    save_normal_chars, save_mythical_chars, save_exalted_chars,
    bot_groups, save_bot_groups, add_banned_player_info, remove_banned_player_info,
    get_banned_player_info, set_pending_forward, set_pending_broadcast, get_bot_groups, add_bot_group,
    get_group_drop_count, set_group_drop_count, ALLOWED_DROP_COUNTS,
    get_group_next_drop_rarity, set_group_next_drop_rarity, clear_group_next_drop_rarity,
    get_command_lock_user_id, set_command_lock_user_id,
    add_normal_character, add_mythical_character, add_exalted_character, add_custom_character,
    character_media_exists,
    delete_normal_character, delete_mythical_character, delete_exalted_character, delete_character_by_id,
    update_character,
    get_character_by_id, get_character_by_name, is_admin_or_owner,
    add_custom_rarity, delete_custom_rarity, get_character_rarities, get_rarity_emoji, get_rarity_reward_range, save_rarities,
    rarity_settings, set_rarity_emoji, set_rarity_chance, set_rarity_reward_range,
    get_rarity_spoiler, set_rarity_spoiler,
    rename_custom_rarity, set_character_win_chance, get_quiz_rarities,
    active_challenges, create_json_backup, PLAYER_DATA_FILES, get_player_data_snapshots,
)
from utils import parse_amount, get_xp_needed, get_rank
from models import Player


PENDING_UPLOAD_RESTORES = {}
UPLOAD_JSON_NAMES = {
    "users.json", "normal_chars.json", "mythical_chars.json", "exalted_chars.json", "rarities.json",
    "gbanned.json", "temp_banned.json", "admins.json",
    "bot_groups.json", "group_settings.json", "crews.json",
    "fishing_sticker.json", "fail_fish_sticker.json", "price_overrides.json", "giveaway.json", "nika_move_gifs.json", "ope_ope_gif.json",
    "fruit_awakening_gifs.json", "claim_reward_gif.json", "quiz_drop_media.json", "bonus_media.json",
    *PLAYER_DATA_FILES,
}


def _character_uploader(user):
    if not user:
        return {}
    return {
        "id": getattr(user, "id", None),
        "username": getattr(user, "username", None) or "",
        "name": " ".join(filter(None, [getattr(user, "first_name", None), getattr(user, "last_name", None)])),
    }


def _character_upload_caption(character):
    rarity = " ".join(str(character.get("rarity", "NORMAL")).strip().upper().split())
    uploader = character.get("uploader") or {}
    if isinstance(uploader, dict) and uploader.get("username"):
        uploader_label = "@" + str(uploader["username"]).lstrip("@")
    elif isinstance(uploader, dict) and (uploader.get("name") or uploader.get("id")):
        uploader_label = str(uploader.get("name") or "User")
        if uploader.get("id"):
            uploader_label += f" (ID: {uploader['id']})"
    else:
        uploader_label = "Unknown (legacy character)"
    return (
        "🆕 NEW CHARACTER\n\n"
        f"🎭 Name: {character.get('name', 'Unknown')}\n"
        f"🆔 ID: #{character.get('id', '?')}\n"
        f"✨ Rarity: {get_rarity_emoji(rarity)} {rarity.title()}\n"
        f"👤 Uploader: {uploader_label}"
    )


def _save_character_upload_reference(character):
    """Persist the upload-channel message reference with its character record."""
    for records, save_records in (
        (normal_characters, save_normal_chars),
        (mythical_characters, save_mythical_chars),
        (exalted_characters, save_exalted_chars),
    ):
        if any(record is character for record in records):
            save_records()
            return


async def _send_character_to_upload_channel(client, character):
    try:
        from config import CHARACTER_UPLOAD_CHANNEL_ID, CHARACTER_UPLOAD_CHANNEL_USERNAME
        target = CHARACTER_UPLOAD_CHANNEL_USERNAME or CHARACTER_UPLOAD_CHANNEL_ID
    except Exception as exc:
        print(f"[character upload channel] channel lookup failed: {exc}")
        return False
    if not target:
        print("[character upload channel] no character upload channel configured")
        return False
    image = character.get("image")
    if not image:
        return False
    caption = _character_upload_caption(character)
    method = "send_video" if character.get("media_type") == "video" else "send_photo"
    posted = None
    try:
        posted = await getattr(client, method)(target, image, caption=caption, parse_mode=None)
    except Exception as first_error:
        try:
            posted = await client.send_document(target, image, caption=caption, parse_mode=None)
        except Exception as second_error:
            print(
                f"[character upload channel] failed for #{character.get('id')}: "
                f"{first_error}; fallback: {second_error}"
            )
            return False
    character["upload_channel_id"] = getattr(getattr(posted, "chat", None), "id", target)
    character["upload_message_id"] = getattr(posted, "id", None)
    _save_character_upload_reference(character)
    return True


async def _update_character_upload_post(client, character, edit_result):
    """Edit a tracked channel post, or publish the updated character if untracked."""
    chat_id = character.get("upload_channel_id")
    message_id = character.get("upload_message_id")
    if not chat_id or not message_id:
        return "posted the updated character (the previous channel post was not linked)" if await _send_character_to_upload_channel(client, character) else "couldn't update the upload-channel post"

    caption = _character_upload_caption(character)
    try:
        if edit_result.get("new_image") != edit_result.get("old_image"):
            from pyrogram.types import InputMediaPhoto, InputMediaVideo
            media_class = InputMediaVideo if character.get("media_type") == "video" else InputMediaPhoto
            await client.edit_message_media(
                chat_id,
                message_id,
                media_class(character["image"], caption=caption, parse_mode=None),
            )
        else:
            await client.edit_message_caption(chat_id, message_id, caption, parse_mode=None)
        return "updated the existing channel post"
    except Exception as exc:
        print(f"[character upload channel] edit failed for #{character.get('id')}: {exc}")
        # If Telegram cannot edit the existing post, keep the channel current by
        # publishing the updated version and tracking that new message instead.
        if await _send_character_to_upload_channel(client, character):
            return "posted an updated copy (Telegram would not edit the previous post)"
        return "couldn't update the upload-channel post"


async def _post_new_character(client, image, message=None):
    character = character_media_exists(image)
    if not character:
        return False
    posted = await _send_character_to_upload_channel(client, character)
    if not posted and message is not None:
        await message.reply(
            "⚠️ Character was saved, but couldn't be posted to the upload channel. "
            "Check that the bot can post there."
        )
    return posted


CHARACTER_RESEND_ACTIVE = False


def register_admin(app):

    @app.on_message(filters.command(["prices", "shopprices"]))
    async def show_prices_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from pricing import list_prices
        lines = ["💰 **CONFIGURABLE ECONOMY PRICES**", ""]
        for key, label, amount in list_prices():
            lines.append(f"• `{key}` — {label}: ฿{amount:,}")
        lines += ["", "Set one with `/setprice [key] [amount]` (examples: `25M`, `1.5B`)."]
        await message.reply("\n".join(lines))

    @app.on_message(filters.command("setprice"))
    async def set_price_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from pricing import PRICE_DEFAULTS, get_price, normalize_price_key, parse_price_amount, set_price
        args = (message.text or "").split(maxsplit=2)
        if len(args) != 3:
            await message.reply("⚠️ Usage: `/setprice [key] [amount]`\nSee `/prices` for valid keys. Amounts accept K/M/B/T (for example `2.5B`).")
            return
        key = normalize_price_key(args[1])
        if key not in PRICE_DEFAULTS:
            await message.reply("Unknown price key. Use `/prices` to see every valid key.")
            return
        amount = parse_price_amount(args[2])
        if amount is None:
            await message.reply("⚠️ That amount is invalid. Use a non-negative number, optionally with K/M/B/T.")
            return
        previous = get_price(key)
        if not set_price(key, amount):
            if key.endswith("_min") or key.endswith("_max"):
                await message.reply("Fish sale minimum must not exceed its maximum, and maximum must not be below its minimum.")
            else:
                await message.reply("Couldn't save the new price. Check that the bot can write to its data folder.")
            return
        await message.reply(f"✅ `{key}` updated: ฿{previous:,} → ฿{amount:,}.")

    @app.on_message(filters.command("setclaimgif"))
    async def set_claim_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import set_claim_reward_gif
        args = (message.text or message.caption or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            await message.reply(
                "Reply to a Telegram GIF/animation with `/setclaimgif`, "
                "or use `/setclaimgif [file_id]`."
            )
            return
        set_claim_reward_gif(file_id)
        await message.reply("✅ Saved the claim reward GIF. It will be shown after a successful `/claim`.")

    @app.on_message(filters.command("claimgif"))
    async def claim_gif_status_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import get_claim_reward_gif
        await message.reply(
            "🎁 **CLAIM REWARD GIF**\n\n"
            + ("✅ Configured" if get_claim_reward_gif() else "Not configured")
        )

    @app.on_message(filters.command("clearclaimgif"))
    async def clear_claim_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import clear_claim_reward_gif
        if clear_claim_reward_gif():
            await message.reply("✅ Cleared the claim reward GIF.")
        else:
            await message.reply("ℹ️ No claim reward GIF was configured.")

    @app.on_message(filters.command("setclaimsticker"))
    async def set_claim_sticker_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import set_claim_reward_sticker
        args = (message.text or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message and message.reply_to_message.sticker:
            file_id = message.reply_to_message.sticker.file_id
        if not file_id:
            await message.reply("⚠️ Reply to a sticker with `/setclaimsticker`, or pass a sticker file ID.")
            return
        set_claim_reward_sticker(file_id)
        await message.reply("✅ Saved the claim reward sticker.")

    @app.on_message(filters.command("clearclaimsticker"))
    async def clear_claim_sticker_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import clear_claim_reward_sticker
        await message.reply(
            "✅ Claim reward sticker cleared."
            if clear_claim_reward_sticker() else "ℹ️ No claim reward sticker was configured."
        )

    @app.on_message(filters.command("setclaimemoji"))
    async def set_claim_emoji_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split(maxsplit=1)
        if len(args) != 2 or not args[1].strip():
            await message.reply("⚠️ Usage: `/setclaimemoji [emoji]`\nExample: `/setclaimemoji 🎁`\nUse `/clearclaimemoji` to remove it.")
            return
        from claim_media import set_claim_reward_emoji
        set_claim_reward_emoji(args[1].strip())
        await message.reply(f"✅ Claim reward emoji set to {args[1].strip()}.")

    @app.on_message(filters.command("clearclaimemoji"))
    async def clear_claim_emoji_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import clear_claim_reward_emoji
        await message.reply(
            "✅ Claim reward emoji cleared."
            if clear_claim_reward_emoji() else "ℹ️ No claim reward emoji was configured."
        )

    @app.on_message(filters.command("claimmedia"))
    async def claim_media_status_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from claim_media import get_claim_reward_emoji, get_claim_reward_gif, get_claim_reward_sticker
        await message.reply(
            "🎁 **CLAIM REWARD MEDIA**\n\n"
            f"Sticker: {'✅ Set' if get_claim_reward_sticker() else 'Not set'}\n"
            f"Emoji: {get_claim_reward_emoji() or 'Not set'}\n"
            f"GIF: {'✅ Set' if get_claim_reward_gif() else 'Not set'}"
        )

    @app.on_message(filters.command("setbonusgif"))
    async def set_bonus_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from bonus_media import set_bonus_gif
        args = (message.text or message.caption or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            await message.reply("⚠️ Reply to a GIF/animation with `/setbonusgif`, or pass its file ID.")
            return
        set_bonus_gif(file_id)
        await message.reply("✅ Weekly bonus GIF saved.")

    @app.on_message(filters.command("setbonussticker"))
    async def set_bonus_sticker_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from bonus_media import set_bonus_sticker
        args = (message.text or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message and message.reply_to_message.sticker:
            file_id = message.reply_to_message.sticker.file_id
        if not file_id:
            await message.reply("⚠️ Reply to a sticker with `/setbonussticker`, or pass its file ID.")
            return
        set_bonus_sticker(file_id)
        await message.reply("✅ Weekly bonus sticker saved.")

    @app.on_message(filters.command("setbonusemoji"))
    async def set_bonus_emoji_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split(maxsplit=1)
        if len(args) != 2 or not args[1].strip():
            await message.reply("⚠️ Usage: `/setbonusemoji [emoji]`\nExample: `/setbonusemoji 🎁`")
            return
        from bonus_media import set_bonus_emoji
        set_bonus_emoji(args[1].strip())
        await message.reply(f"✅ Weekly bonus emoji set to {args[1].strip()}.")

    @app.on_message(filters.command("bonusmedia"))
    async def bonus_media_status_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from bonus_media import get_bonus_media
        media = get_bonus_media()
        await message.reply(
            "🎁 **WEEKLY BONUS MEDIA**\n\n"
            f"Sticker: {'✅ Set' if media.get('sticker') else 'Not set'}\n"
            f"Emoji: {media.get('emoji') or 'Not set'}\n"
            f"GIF: {'✅ Set' if media.get('gif') else 'Not set'}"
        )

    @app.on_message(filters.command(["clearbonusgif", "clearbonussticker", "clearbonusemoji"]))
    async def clear_bonus_media_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        command = (message.command[0] if getattr(message, "command", None) else "").split("@", 1)[0]
        if command == "clearbonusgif":
            from bonus_media import clear_bonus_gif
            existed = clear_bonus_gif()
            label = "GIF"
        elif command == "clearbonussticker":
            from bonus_media import clear_bonus_sticker
            existed = clear_bonus_sticker()
            label = "sticker"
        else:
            from bonus_media import clear_bonus_emoji
            existed = clear_bonus_emoji()
            label = "emoji"
        await message.reply(
            f"✅ Weekly bonus {label} cleared." if existed
            else f"ℹ️ No weekly bonus {label} was configured."
        )

    @app.on_message(filters.command("setadvancedhakigif"))
    async def set_advanced_haki_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from haki_media import normalize_haki_type, set_advanced_haki_gif
        args = (message.text or message.caption or "").split(maxsplit=2)
        if len(args) < 2:
            await message.reply(
                "Usage: reply to a GIF with `/setadvancedhakigif [observation|armament|conqueror]`\n"
                "Or provide its Telegram file ID: `/setadvancedhakigif [type] [file_id]`"
            )
            return
        haki_type = normalize_haki_type(args[1])
        if not haki_type:
            await message.reply("Choose `observation`, `armament`, or `conqueror`.")
            return

        file_id = args[2].strip() if len(args) > 2 else ""
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            await message.reply("⚠️ Reply to a Telegram GIF/animation, or include its file ID.")
            return

        set_advanced_haki_gif(haki_type, file_id)
        await message.reply(
            f"✅ Saved the Advanced **{haki_type.title()} Haki** unlock GIF.\n"
            "It will be sent when a player enchants that Haki."
        )

    @app.on_message(filters.command("advancedhakigifs"))
    async def advanced_haki_gifs_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from haki_media import get_advanced_haki_gif
        rows = []
        for key in ("observation", "armament", "conqueror"):
            rows.append(f"• **{key.title()}:** {'✅ Set' if get_advanced_haki_gif(key) else 'Not set'}")
        await message.reply("**ADVANCED HAKI UNLOCK GIFS**\n\n" + "\n".join(rows))

    @app.on_message(filters.command("clearadvancedhakigif"))
    async def clear_advanced_haki_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from haki_media import clear_advanced_haki_gif, normalize_haki_type
        args = (message.text or message.caption or "").split(maxsplit=1)
        haki_type = normalize_haki_type(args[1]) if len(args) > 1 else None
        if not haki_type:
            await message.reply("⚠️ Usage: `/clearadvancedhakigif [observation|armament|conqueror]`")
            return
        _, existed = clear_advanced_haki_gif(haki_type)
        await message.reply(
            f"✅ Cleared the **{haki_type.title()} Haki** unlock GIF."
            if existed else f"ℹ️ No **{haki_type.title()} Haki** GIF was configured."
        )

    @app.on_message(filters.command(["setbajranggungif", "setkaminarigif"]))
    async def set_nika_move_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        command_name = (
            str((getattr(message, "command", []) or [""])[0])
            .split("@", 1)[0].casefold()
        )
        move = "bajranggun" if command_name == "setbajranggungif" else "kaminari"
        args = (message.text or message.caption or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            command = "/setbajranggungif" if move == "bajranggun" else "/setkaminarigif"
            await message.reply(
                f"Reply to a Telegram GIF/animation with `{command}`,\n"
                f"or set its file ID with `{command} [file_id]`."
            )
            return
        from nika_media import set_nika_move_gif
        set_nika_move_gif(move, file_id)
        spell = "Gomu Gomu no Bajrang Gun" if move == "bajranggun" else "Gomu Gomu no Kaminari"
        await message.reply(f"✅ Saved the **{spell}** GIF. It will play when the spell is used.")

    @app.on_message(filters.command("nikagifs"))
    async def nika_move_gifs_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from nika_media import get_nika_move_gif
        rows = [
            f"• **Gomu Gomu no Bajrang Gun:** {'✅ Set' if get_nika_move_gif('bajranggun') else 'Not set'}",
            f"• **Gomu Gomu no Kaminari:** {'✅ Set' if get_nika_move_gif('kaminari') else 'Not set'}",
        ]
        await message.reply("**NIKA AWAKENED SPELL GIFS**\n\n" + "\n".join(rows))

    @app.on_message(filters.command("clearnikagif"))
    async def clear_nika_move_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or message.caption or "").split(maxsplit=1)
        from nika_media import clear_nika_move_gif, normalize_nika_move
        move = normalize_nika_move(args[1]) if len(args) > 1 else None
        if not move:
            await message.reply("⚠️ Usage: `/clearnikagif [bajranggun|kaminari]`")
            return
        _, existed = clear_nika_move_gif(move)
        spell = "Bajrang Gun" if move == "bajranggun" else "Kaminari"
        await message.reply(
            f"✅ Cleared the **{spell}** GIF." if existed
            else f"ℹ️ No **{spell}** GIF was configured."
        )

    @app.on_message(filters.command(["setopeawakeninggif", "setopeopegif"]))
    async def set_ope_awakening_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or message.caption or "").split(maxsplit=2)
        from ope_media import normalize_ope_move, set_ope_awakening_gif
        move = normalize_ope_move(args[1]) if len(args) > 1 else None
        file_id = args[2].strip() if len(args) > 2 else ""
        if not move:
            await message.reply(
                "GIFs are only for the awakened moves. Reply to a GIF with "
                "`/setopeawakeninggif [kroom|shockwille]`, or include a file ID as a third argument."
            )
            return
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            await message.reply(
                "Reply to a Telegram GIF/animation with `/setopeawakeninggif [kroom|shockwille]`,\n"
                "or use `/setopeawakeninggif [move] [file_id]`."
            )
            return
        set_ope_awakening_gif(move, file_id)
        spell = "K-Room (Tact)" if move == "kroomtact" else "Shock Wille"
        await message.reply(f"✅ Saved the awakened **{spell}** GIF. It will play when that move is used.")

    @app.on_message(filters.command(["opeawakeninggifs", "opeopegif"]))
    async def ope_awakening_gifs_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from ope_media import get_ope_awakening_gif
        rows = [
            f"• **K-Room (Tact):** {'✅ Set' if get_ope_awakening_gif('kroomtact') else 'Not set'}",
            f"• **Shock Wille:** {'✅ Set' if get_ope_awakening_gif('shockwille') else 'Not set'}",
        ]
        await message.reply("**OPE OPE AWAKENED SPELL GIFS**\n\n" + "\n".join(rows))

    @app.on_message(filters.command(["clearopeawakeninggif", "clearopeopegif"]))
    async def clear_ope_awakening_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or message.caption or "").split(maxsplit=1)
        from ope_media import clear_ope_awakening_gif, normalize_ope_move
        move = normalize_ope_move(args[1]) if len(args) > 1 else None
        if not move:
            await message.reply("⚠️ Usage: `/clearopeawakeninggif [kroom|shockwille]`")
            return
        _, existed = clear_ope_awakening_gif(move)
        spell = "K-Room (Tact)" if move == "kroomtact" else "Shock Wille"
        await message.reply(
            f"✅ Cleared the awakened **{spell}** GIF."
            if existed else f"ℹ️ No awakened **{spell}** GIF was configured."
        )

    @app.on_message(filters.command([
        "setitoawakeninggif", "setmochiawakeninggif", "setjikiawakeninggif", "setsnakemangif"
    ]))
    async def set_fruit_awakening_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        command_name = str((getattr(message, "command", []) or [""])[0]).split("@", 1)[0].casefold()
        state_key = {
            "setitoawakeninggif": "ito",
            "setmochiawakeninggif": "mochi",
            "setjikiawakeninggif": "jiki",
            "setsnakemangif": "gomu",
        }.get(command_name)
        args = (message.text or message.caption or "").split(maxsplit=1)
        file_id = args[1].strip() if len(args) > 1 else ""
        if not file_id and message.reply_to_message:
            media = message.reply_to_message
            if media.animation:
                file_id = media.animation.file_id
            elif media.document and (
                (media.document.mime_type or "").lower() == "image/gif"
                or (media.document.file_name or "").lower().endswith(".gif")
            ):
                file_id = media.document.file_id
        if not file_id:
            await message.reply(
                f"Reply to a Telegram GIF/animation with `/{command_name}`, "
                f"or use `/{command_name} [file_id]`."
            )
            return
        from fruit_awakening_media import set_fruit_awakening_gif
        set_fruit_awakening_gif(state_key, file_id)
        title = {"ito": "Ito Awakening", "mochi": "Mochi Awakening", "jiki": "Jiki Awakening", "gomu": "Gear 4 Snakeman"}[state_key]
        await message.reply(f"✅ Saved the **{title}** activation GIF. It will play when that awakening is activated.")

    @app.on_message(filters.command("fruitawakeninggifs"))
    async def fruit_awakening_gifs_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        from fruit_awakening_media import get_fruit_awakening_gif
        titles = {"ito": "Ito Awakening", "mochi": "Mochi Awakening", "jiki": "Jiki Awakening", "gomu": "Gomu Gear 4 Snakeman"}
        rows = [f"• **{title}:** {'✅ Set' if get_fruit_awakening_gif(key) else 'Not set'}" for key, title in titles.items()]
        await message.reply("**FRUIT AWAKENING ACTIVATION GIFS**\n\n" + "\n".join(rows))

    @app.on_message(filters.command("clearfruitawakeninggif"))
    async def clear_fruit_awakening_gif_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or message.caption or "").split(maxsplit=1)
        from fruit_awakening_media import clear_fruit_awakening_gif, normalize_awakening
        state_key = normalize_awakening(args[1]) if len(args) > 1 else None
        if not state_key:
            await message.reply("⚠️ Usage: `/clearfruitawakeninggif [ito|mochi|jiki|snakeman]`")
            return
        _, existed = clear_fruit_awakening_gif(state_key)
        title = {"ito": "Ito Awakening", "mochi": "Mochi Awakening", "jiki": "Jiki Awakening", "gomu": "Gomu Gear 4 Snakeman"}[state_key]
        await message.reply(
            f"✅ Cleared the **{title}** activation GIF." if existed
            else f"ℹ️ No **{title}** activation GIF was configured."
        )

    def _admin_target_and_value(message, args, value_label):
        """Return (player, value) from a reply or `<user_id> <value>`."""
        if message.reply_to_message and message.reply_to_message.from_user:
            if len(args) != 2:
                return None, None, f"Usage: `/{message.command[0]} [{value_label}]` (reply to a user)"
            target_id = message.reply_to_message.from_user.id
            raw_value = args[1]
        else:
            if len(args) != 3:
                return None, None, f"Usage: `/{message.command[0]} [user_id] [{value_label}]`"
            try:
                target_id = int(args[1])
            except ValueError:
                return None, None, "That user ID is invalid."
            raw_value = args[2]
        return get_player(target_id), raw_value, None

    # ==================== CUSTOM RARITIES ====================
    @app.on_message(filters.command("addrarity"))
    async def add_rarity_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("⚠️ Usage: `/addrarity [rarity name]`\nExample: `/addrarity Celestial`")
            return
        value = add_custom_rarity(args[1])
        if not value:
            await message.reply("⚠️ Invalid or reserved rarity. Use a new name other than NORMAL, MYTHICAL, or EXALTED.")
            return
        command_key = re.sub(r"[^a-z0-9]", "", value.lower())
        await message.reply(
            f"✅ Rarity **{value}** is now available.\n"
            f"Use `/{command_key}add Character Name` (reply to a photo/video) to add a character.\n"
            f"Use `/{command_key}delete [id]` to delete one.\n"
            f"Use `/edit [id] rarity {value}` to assign an existing character."
        )

    @app.on_message(filters.command(["deleterarity", "raritydelete"]))
    async def delete_rarity_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("⚠️ Usage: `/deleterarity [rarity]`")
            return
        value = delete_custom_rarity(args[1])
        if not value:
            await message.reply("Custom rarity not found. Built-in rarities can't be deleted.")
            return
        await message.reply(f"✅ Deleted rarity **{value}**. Characters using it were changed to NORMAL.")

    def _resolve_dynamic_rarity_command(message):
        """Return (command, suffix, rarity) for a custom-rarity command."""
        try:
            parsed = getattr(message, "command", None)
            text = getattr(message, "text", None) or getattr(message, "caption", None) or ""
            raw = parsed[0] if parsed else text.split(maxsplit=1)[0]
            command = str(raw).strip().lstrip("/").split("@", 1)[0].lower()
            if command.endswith("add"):
                suffix = "add"
            elif command.endswith("delete"):
                suffix = "delete"
            else:
                return None
            key = re.sub(r"[^A-Z0-9]", "", command[:-len(suffix)].upper())
            rarity = next((
                rarity for rarity in get_character_rarities()
                if rarity not in {"NORMAL", "MYTHICAL", "EXALTED"}
                and re.sub(r"[^A-Z0-9]", "", str(rarity).upper()) == key
            ), None)
            if not rarity:
                return None
            return command, suffix, rarity
        except (AttributeError, IndexError, TypeError, ValueError):
            return None

    def _is_dynamic_rarity_command(_, __, message):
        """Match /<custom-rarity>add and /<custom-rarity>delete at runtime."""
        return _resolve_dynamic_rarity_command(message) is not None

    @app.on_message(filters.all, group=-50)
    async def dynamic_rarity_character_cmd(client, message):
        """Handle /<customrarity>add and /<customrarity>delete without a restart."""
        resolved = _resolve_dynamic_rarity_command(message)
        if not resolved:
            message.continue_propagation()
            return
        command, suffix, rarity = resolved
        if not message.from_user or not is_admin_or_owner(message.from_user.id):
            return

        if suffix == "delete":
            text = getattr(message, "text", None) or ""
            args = text.split()
            if len(args) != 2 or not args[1].isdigit():
                await message.reply(f"⚠️ Usage: `/{command} [id]`")
                return
            target = get_character_by_id(int(args[1]))
            if not target or str(target.get("rarity", "")).strip().upper() != rarity:
                await message.reply(f"No **{rarity}** character with that ID.")
                return
            deleted = delete_character_by_id(int(args[1]))
            if not deleted:
                await message.reply("Delete failed: character was not found.")
                return
            await message.reply(f"✅ Deleted **{deleted.get('name', '?')}** ({rarity}, ID: {args[1]})")
            return

        text = getattr(message, "text", None) or ""
        args = text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(f"⚠️ Usage: `/{command} Character Name` (reply to a photo/video)")
            return
        name = args[1].strip()
        reply = message.reply_to_message
        image = None
        media_type = "photo"
        if reply and reply.photo:
            image = reply.photo.file_id
        elif reply and reply.video:
            image, media_type = reply.video.file_id, "video"
        elif reply and reply.document:
            image = reply.document.file_id
        if not image:
            await message.reply("⚠️ Reply to a photo or video when adding a character.")
            return
        duplicate = character_media_exists(image)
        if duplicate:
            await message.reply(
                f"This media is already used by **{duplicate.get('name', 'another character')}** "
                f"(ID: `{duplicate.get('id')}`)."
            )
            return
        if not add_custom_character(
            name, image, rarity, media_type,
            uploader=_character_uploader(message.from_user),
        ):
            await message.reply("Couldn't add the character.")
            return
        await _post_new_character(client, image, message)
        await message.reply(f"✅ Added **{name}** ({rarity}, {media_type})")

    @app.on_message(filters.command("sent"))
    async def resend_all_characters_cmd(client, message):
        global CHARACTER_RESEND_ACTIVE
        if not message.from_user or not is_admin_or_owner(message.from_user.id):
            return
        if CHARACTER_RESEND_ACTIVE:
            await message.reply("⏳ A character channel backfill is already running.")
            return
        characters = sorted(
            normal_characters + mythical_characters + exalted_characters,
            key=lambda item: int(item.get("id", 0) or 0)
            if str(item.get("id", "0")).isdigit() else 0,
        )
        if not characters:
            await message.reply("ℹ️ There are no saved characters to send.")
            return
        try:
            from config import CHARACTER_UPLOAD_CHANNEL_ID, CHARACTER_UPLOAD_CHANNEL_USERNAME
            character_upload_channel = CHARACTER_UPLOAD_CHANNEL_USERNAME or CHARACTER_UPLOAD_CHANNEL_ID
        except Exception:
            character_upload_channel = None
        if not character_upload_channel:
            await message.reply("No character upload channel is configured.")
            return

        CHARACTER_RESEND_ACTIVE = True
        sent = 0
        failed_ids = []
        try:
            status = await message.reply(
                f"⏳ Sending {len(characters)} characters to the upload channel; this may take a while."
            )
            for index, character in enumerate(characters, 1):
                if await _send_character_to_upload_channel(client, character):
                    sent += 1
                else:
                    failed_ids.append(str(character.get("id", "?")))
                if index < len(characters):
                    await asyncio.sleep(3.2)
            summary = f"✅ Backfill complete: sent {sent}/{len(characters)} characters."
            if failed_ids:
                shown = ", ".join(f"#{char_id}" for char_id in failed_ids[:30])
                summary += f"\n⚠️ Failed: {len(failed_ids)} ({shown}"
                summary += ", …" if len(failed_ids) > 30 else ""
                summary += ")."
            await status.edit_text(summary)
        finally:
            CHARACTER_RESEND_ACTIVE = False

    @app.on_message(filters.command("rarities"))
    async def rarities_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        await message.reply("🏷️ **CHARACTER RARITIES**\n\n" + "\n".join(
            f"• {rarity_settings.get(rarity, {}).get('emoji', '💠')} {rarity} — "
            f"{rarity_settings.get(rarity, {}).get('chance', 0):g}% — "
            f"฿{get_rarity_reward_range(rarity)[0]:,}–฿{get_rarity_reward_range(rarity)[1]:,} — "
            f"Spoiler {'ON' if get_rarity_spoiler(rarity) else 'OFF'}"
            for rarity in get_character_rarities()
        ))

    @app.on_message(filters.command(["raritypercent", "raritychance"]))
    async def rarity_percent_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        lines = [
            f"{rarity_settings.get(rarity, {}).get('emoji', '💠')} **{rarity}**: "
            f"{rarity_settings.get(rarity, {}).get('chance', 0):g}% | "
            f"Win: ฿{get_rarity_reward_range(rarity)[0]:,}–฿{get_rarity_reward_range(rarity)[1]:,}"
            for rarity in get_character_rarities()
        ]
        await message.reply("📊 **RARITY DROP CHANCES**\n\n" + "\n".join(lines))

    @app.on_message(filters.command(["setrarityreward", "setwinprice"]))
    async def set_rarity_reward_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        parts = (message.text or "").split()
        if len(parts) < 4:
            await message.reply(
                "Usage: `/setrarityreward [rarity] [minimum] [maximum]`\n"
                "Example: `/setrarityreward MYTHIC NOIR 2000000 9000000`"
            )
            return
        # Parse numeric bounds from the tail while keeping a multiword rarity.
        tail = " ".join(parts[1:])
        matches = list(re.finditer(r"\d[\d,]*", tail))
        rarity_name = tail[:matches[0].start()].strip() if matches else ""
        values = [match.group(0) for match in matches]
        if len(values) != 2:
            await message.reply("⚠️ Provide two valid bounty values.")
            return
        result = set_rarity_reward_range(rarity_name, values[0].replace(",", ""), values[1].replace(",", ""))
        if result is False:
            await message.reply("Use an existing rarity and valid values where minimum ≤ maximum.")
            return
        low, high = result
        await message.reply(f"✅ {rarity_name.upper()} winning bounty set to ฿{low:,}–฿{high:,}.")

    @app.on_message(filters.command("setrarityemoji"))
    async def set_rarity_emoji_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split(maxsplit=1)
        if len(args) != 2:
            await message.reply(
                "Usage: `/setrarityemoji [rarity name] [emoji]`\n"
                "Example: `/setrarityemoji ANCIENT LEGEND 🌟`"
            )
            return
        try:
            rarity_name, emoji_value = args[1].rsplit(maxsplit=1)
        except ValueError:
            await message.reply(
                "Usage: `/setrarityemoji [rarity name] [emoji]`\n"
                "Example: `/setrarityemoji ANCIENT LEGEND 🌟`"
            )
            return
        emoji = set_rarity_emoji(rarity_name, emoji_value)
        if not emoji:
            await message.reply("⚠️ Rarity not found. Create it first with `/addrarity [name]`.")
            return
        await message.reply(f"✅ {rarity_name.upper()} emoji set to {emoji}")

    @app.on_message(filters.command("setrarityspoiler"))
    async def set_rarity_spoiler_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split(maxsplit=1)
        payload = args[1].strip() if len(args) == 2 else ""
        try:
            rarity_name, state = payload.rsplit(maxsplit=1)
        except ValueError:
            rarity_name, state = "", ""
        rarity_name = rarity_name.strip().strip('"\'')
        if not rarity_name or state.casefold() not in {"on", "off"}:
            await message.reply(
                "Usage: `/setrarityspoiler [rarity name] [on|off]`\n"
                "Example: `/setrarityspoiler MYTHIC NOIR on`"
            )
            return
        enabled = state.casefold() == "on"
        result = set_rarity_spoiler(rarity_name, enabled)
        normalized_name = " ".join(rarity_name.upper().split())
        if normalized_name not in get_character_rarities():
            await message.reply("Unknown rarity. Check `/rarities` for the available names.")
            return
        await message.reply(
            f"✅ Spoiler-hidden character photos for **{normalized_name}** are "
            f"{'ON' if get_rarity_spoiler(normalized_name) else 'OFF'}."
        )

    @app.on_message(filters.command("setraritychance"))
    async def set_rarity_chance_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split()
        if len(args) < 3:
            await message.reply("⚠️ Usage: `/setraritychance [rarity name] [percent]`\nExample: `/setraritychance Mythic Noir 5`")
            return
        rarity_name, percentage = " ".join(args[1:-1]), args[-1]
        chance = set_rarity_chance(rarity_name, percentage)
        if chance is False:
            await message.reply("⚠️ Use a valid rarity and a percentage from 0 to 100.")
            return
        await message.reply(f"✅ {rarity_name.upper()} drop chance set to {chance:g}%")

    @app.on_message(filters.command(["renamerarity", "rarityrename"]))
    async def rename_rarity_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        text = (message.text or "").split(maxsplit=1)
        if len(text) != 2 or "->" not in text[1]:
            await message.reply(
                "Usage: `/renamerarity [old rarity] -> [new rarity]`\n"
                "Example: `/renamerarity Limited -> Mythic Limited`"
            )
            return
        old_name, new_name = (part.strip() for part in text[1].split("->", 1))
        renamed = rename_custom_rarity(old_name, new_name)
        if not renamed:
            await message.reply(
                "Couldn't rename that rarity. It needs to be an existing custom rarity, "
                "and the new name needs to be unused."
            )
            return
        await message.reply(
            f"✅ Rarity **{old_name.upper()}** renamed to **{renamed}**. "
            "Character records, collections, active challenges, and rarity settings were updated."
        )

    @app.on_message(filters.command(["setcharwin", "setwinchance", "setcharchance"]))
    async def set_character_win_chance_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split()
        if len(args) != 3 or not args[1].isdigit():
            await message.reply(
                "Usage: `/setcharwin [character ID] [percent]`\n"
                "Example: `/setcharwin 123 65` (0–100; overrides the default challenge formula)"
            )
            return
        result = set_character_win_chance(int(args[1]), args[2])
        if result is False:
            await message.reply("⚠️ Character not found, or chance needs to be from 0 to 100.")
            return
        character = get_character_by_id(int(args[1]))
        await message.reply(
            f"✅ **{character.get('name', 'Character')}** (ID `{args[1]}`) "
            f"challenge win chance set to **{result:g}%**."
        )

    # ==================== ADD NORMAL CHARACTER ====================
    @app.on_message(filters.command("ncradd"))
    async def add_normal_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📸 **Add Normal Character**\n\n"
                "Usage:\n"
                "1. `/ncradd Zoro` (then reply to photo)\n"
                "2. `/ncradd Monkey D. Luffy https://i.imgur.com/xxx.jpg`\n"
                "3. `/ncradd Roronoa Zoro <file_id>`"
            )
            return

        name_part = args[1].strip()
        parts = name_part.split()

        if len(parts) >= 2 and (
            parts[-1].startswith(("http://", "https://")) or len(parts[-1]) > 30
        ):
            name = " ".join(parts[:-1])
            photo_input = parts[-1]
        else:
            name = name_part
            photo_input = None

        if not photo_input:
            if message.reply_to_message and message.reply_to_message.video:
                added = add_normal_character(name, message.reply_to_message.video.file_id, "video", uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This media is already used by another character.")
                    return
                await _post_new_character(client, message.reply_to_message.video.file_id, message)
                await message.reply(f"✅ Added **{name}** (video file_id)")
                return
            if message.reply_to_message and message.reply_to_message.photo:
                file_id = message.reply_to_message.photo.file_id
                added = add_normal_character(name, file_id, uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This photo is already used by another character.")
                    return
                await _post_new_character(client, file_id, message)
                await message.reply(f"✅ Added **{name}** (photo file_id)")
                return
            await message.reply(
                f"Provide an image!\n\n**Name:** {name}\n\n"
                f"Reply to a photo, or:\n"
                f"`/ncradd {name} https://...`"
            )
            return

        if photo_input.startswith(("http://", "https://")):
            if photo_input.lower().endswith((".png", ".jpg", ".jpeg")):
                added = add_normal_character(name, photo_input, uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This image is already used by another character.")
                    return
                await _post_new_character(client, photo_input, message)
                await message.reply(f"✅ Added **{name}** (URL)")
                return
            if photo_input.lower().endswith((".gif", ".webp")):
                await message.reply("Animated images not supported.")
                return
            await message.reply("⚠️ Invalid image URL!")
            return

        added = add_normal_character(name, photo_input, uploader=_character_uploader(message.from_user))
        if not added:
            await message.reply("⚠️ This media is already used by another character.")
            return
        await _post_new_character(client, photo_input, message)
        await message.reply(f"✅ Added **{name}** (file_id)")

    # ==================== ADD MYTHICAL CHARACTER ====================
    @app.on_message(filters.command("mcradd"))
    async def add_mythical_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📸 **Add Mythical Character**\n\n"
                "Usage: `/mcradd Kaido` (then reply with photo)\n"
                "Or: `/mcradd Monkey D. Luffy <url_or_file_id>`"
            )
            return

        name_part = args[1].strip()
        parts = name_part.split()

        if len(parts) >= 2 and (
            parts[-1].startswith(("http://", "https://")) or len(parts[-1]) > 30
        ):
            name = " ".join(parts[:-1])
            photo_input = parts[-1]
        else:
            name = name_part
            photo_input = None

        if not photo_input:
            if message.reply_to_message and message.reply_to_message.video:
                added = add_mythical_character(name, message.reply_to_message.video.file_id, "video", uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This media is already used by another character.")
                    return
                await _post_new_character(client, message.reply_to_message.video.file_id, message)
                await message.reply(f"✅ Added **{name}** (mythical, video file_id)")
                return
            if message.reply_to_message and message.reply_to_message.photo:
                file_id = message.reply_to_message.photo.file_id
                added = add_mythical_character(name, file_id, uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This photo is already used by another character.")
                    return
                await _post_new_character(client, file_id, message)
                await message.reply(f"✅ Added **{name}** (mythical, photo file_id)")
                return
            await message.reply(f"⚠️ Provide an image for **{name}**!")
            return

        if photo_input.startswith(("http://", "https://")):
            if photo_input.lower().endswith((".png", ".jpg", ".jpeg")):
                added = add_mythical_character(name, photo_input, uploader=_character_uploader(message.from_user))
                if not added:
                    await message.reply("⚠️ This image is already used by another character.")
                    return
                await _post_new_character(client, photo_input, message)
                await message.reply(f"✅ Added **{name}** (mythical, URL)")
                return
            await message.reply("⚠️ Invalid image URL!")
            return

        added = add_mythical_character(name, photo_input, uploader=_character_uploader(message.from_user))
        if not added:
            await message.reply("⚠️ This media is already used by another character.")
            return
        await _post_new_character(client, photo_input, message)
        await message.reply(f"✅ Added **{name}** (mythical, file_id)")

    # ==================== DELETE CHARACTER ====================
    @app.on_message(filters.command("ecradd"))
    async def add_exalted_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📸 **Add Exalted Character**\n\n"
                "Usage: `/ecradd Character Name` (then reply with a photo)\n"
                "Or: `/ecradd Character Name <url_or_file_id>`"
            )
            return
        parts = args[1].strip().split()
        if len(parts) >= 2 and (parts[-1].startswith(("http://", "https://")) or len(parts[-1]) > 30):
            name, photo_input = " ".join(parts[:-1]), parts[-1]
        else:
            name, photo_input = args[1].strip(), None
        if not photo_input and message.reply_to_message and message.reply_to_message.video:
            added = add_exalted_character(name, message.reply_to_message.video.file_id, "video", uploader=_character_uploader(message.from_user))
            if not added:
                await message.reply("⚠️ This media is already used by another character.")
                return
            await _post_new_character(client, message.reply_to_message.video.file_id, message)
            await message.reply(f"✅ Added **{name}** (exalted, video file_id)")
            return
        if not photo_input and message.reply_to_message and message.reply_to_message.photo:
            added = add_exalted_character(name, message.reply_to_message.photo.file_id, uploader=_character_uploader(message.from_user))
            if not added:
                await message.reply("⚠️ This photo is already used by another character.")
                return
            await _post_new_character(client, message.reply_to_message.photo.file_id, message)
            await message.reply(f"✅ Added **{name}** (exalted, photo file_id)")
            return
        if not photo_input:
            await message.reply(f"⚠️ Provide an image for **{name}**!")
            return
        if photo_input.startswith(("http://", "https://")) and not photo_input.lower().endswith((".png", ".jpg", ".jpeg")):
            await message.reply("⚠️ Invalid image URL!")
            return
        added = add_exalted_character(name, photo_input, uploader=_character_uploader(message.from_user))
        if not added:
            await message.reply("⚠️ This media is already used by another character.")
            return
        await _post_new_character(client, photo_input, message)
        await message.reply(f"✅ Added **{name}** (exalted)")

    @app.on_message(filters.command("ncrdelete"))
    async def delete_normal_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/ncrdelete [id]`\nUse `/charslist` to see IDs")
            return

        try:
            char_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return

        deleted = delete_normal_character(char_id)
        if deleted:
            await message.reply(f"✅ Deleted **{deleted['name']}** (ID: {char_id})")
        else:
            await message.reply(f"No normal character with ID `{char_id}`!")

    @app.on_message(filters.command("mcrdelete"))
    async def delete_mythical_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/mcrdelete [id]`")
            return

        try:
            char_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return

        deleted = delete_mythical_character(char_id)
        if deleted:
            await message.reply(f"✅ Deleted **{deleted['name']}** (ID: {char_id})")
        else:
            await message.reply(f"No mythical character with ID `{char_id}`!")

    @app.on_message(filters.command("ecrdelete"))
    async def delete_exalted_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/ecrdelete [id]`")
            return
        try:
            char_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return
        deleted = delete_exalted_character(char_id)
        if deleted:
            await message.reply(f"✅ Deleted **{deleted['name']}** (ID: {char_id})")
        else:
            await message.reply(f"No exalted character with ID `{char_id}`!")

    @app.on_message(filters.command(["giftcard", "givecard"]))
    async def owner_gift_card_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or message.caption or "").split()
        replied_user = getattr(getattr(message, "reply_to_message", None), "from_user", None)
        if replied_user:
            if len(args) != 2:
                await message.reply("Usage (reply to player): `/giftcard [character_id]`")
                return
            recipient_id = replied_user.id
            raw_char_id = args[1]
        else:
            if len(args) != 3:
                await message.reply("⚠️ Usage: `/giftcard [user_id] [character_id]`\nUse `/charslist` to find a card ID.")
                return
            try:
                recipient_id = int(args[1])
            except ValueError:
                await message.reply("⚠️ Invalid recipient user ID.")
                return
            raw_char_id = args[2]
        try:
            char_id = int(raw_char_id)
        except ValueError:
            await message.reply("⚠️ That character ID is invalid. Use `/charslist` to find card IDs.")
            return
        character = get_character_by_id(char_id)
        if not character:
            await message.reply(f"No card found with ID `{char_id}`.")
            return

        recipient = get_player(recipient_id)
        gifted = {
            "id": character.get("id"),
            "name": character.get("name", "Unknown"),
            "image": character.get("image"),
            "media_type": character.get("media_type", "photo"),
            "rarity": character.get("rarity", "NORMAL"),
            "captured_at": time.time(),
        }
        recipient.captured_chars.append(gifted)
        save_data()
        recipient_name = recipient.name or f"User_{recipient_id}"
        await message.reply(
            f"🎁 Gifted **{gifted['name']}** (ID `{char_id}`) to **{recipient_name}** (`{recipient_id}`).\n"
            "The recipient now has the card in their collection."
        )
        try:
            await client.send_message(
                recipient_id,
                f"🎁 The owner gifted you **{gifted['name']}**! Check your collection with `/mychars`."
            )
        except Exception:
            pass

    # ==================== LIST CHARACTERS ====================
    @app.on_message(filters.command("charslist"))
    async def chars_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        all_characters = normal_characters + mythical_characters + exalted_characters
        grouped = {rarity: [] for rarity in get_character_rarities()}
        for character in all_characters:
            rarity = str(character.get("rarity", "NORMAL")).upper()
            grouped.setdefault(rarity, []).append(character)

        text = f"**CHARACTERS (Total: {len(all_characters)})**\n\n"
        for rarity in get_character_rarities():
            entries = grouped.get(rarity, [])
            emoji = get_rarity_emoji(rarity)
            text += f"{emoji} **{rarity.title()} ({len(entries)}):**\n"
            if entries:
                for character in entries:
                    text += f"`{character.get('id')}` — {character.get('name', 'Unknown')}\n"
            else:
                text += "_No characters._\n"
            text += "\n"

        if not all_characters:
            text += "\n*No characters yet.*"

        if len(text) > 4000:
            for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                await message.reply(chunk)
        else:
            await message.reply(text)

    # ==================== ADMIN MANAGEMENT ====================
    @app.on_message(filters.command("adda"))
    async def add_admin_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/adda [user_id]`")
            return
        try:
            admin_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return
        ADMINS.add(admin_id)
        save_admins()
        await message.reply(f"✅ Added admin: `{admin_id}`")

    @app.on_message(filters.command("removeadmin"))
    async def remove_admin_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/removeadmin [user_id]`")
            return
        try:
            admin_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return
        if admin_id in ADMINS:
            ADMINS.remove(admin_id)
            save_admins()
            await message.reply(f"✅ Removed admin: `{admin_id}`")
        else:
            await message.reply("⚠️ Not an admin!")

    @app.on_message(filters.command("admins"))
    async def list_admins_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        text = "👑 **ADMIN LIST** 👑\n\n"
        try:
            owner = await client.get_users(OWNER_ID)
            text += f"👑 **{owner.first_name}**\n   🆔 `{OWNER_ID}`\n\n"
        except Exception:
            text += f"👑 **Owner**\n   🆔 `{OWNER_ID}`\n\n"

        if ADMINS:
            for i, aid in enumerate(ADMINS, 1):
                try:
                    a = await client.get_users(aid)
                    text += f"{i}. **{a.first_name}** — `{aid}`\n"
                except Exception:
                    text += f"{i}. **User {aid}**\n"
        else:
            text += "No admins yet."
        await message.reply(text)

    # ==================== SET BOUNTY / FRUIT ====================
    @app.on_message(filters.command("setb"))
    async def set_bounty_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/setb [amount]`")
            return
        amount = parse_amount(args[1])
        if amount is None or amount < 0:
            await message.reply("⚠️ That amount is invalid.")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.bounty = amount
        save_data()
        await message.reply(f"✅ Set {p.name}'s bounty to ฿{amount:,}")

    @app.on_message(filters.command("setf"))
    async def set_fruit_cmd(client, message):
        from config import DEVIL_FRUITS
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("⚠️ Usage: `/setf [fruit name]`")
            return

        fruit_name = args[1].strip().lower()
        matched_name = None
        matched_category = None

        for cat, fruits in DEVIL_FRUITS.items():
            for f in fruits:
                if f["full"].lower() == fruit_name:
                    matched_name = f["full"]
                    matched_category = cat
                    break
                if f["name"].lower() == fruit_name:
                    matched_name = f["full"]
                    matched_category = cat
                    break
            if matched_name:
                break

        if not matched_name:
            await message.reply(f"**Fruit not found: `{args[1]}`**")
            return

        p = get_player(message.reply_to_message.from_user.id)
        p.devil_fruit = matched_name
        p.fruit_category = matched_category
        p.nika_awakened = False
        p.nika_active_until = 0
        p.nika_cooldown_until = 0
        p.ope_active_until = 0
        p.ope_cooldown_until = 0
        p.ito_active_until = p.ito_cooldown_until = 0
        p.mochi_active_until = p.mochi_cooldown_until = 0
        p.jiki_active_until = p.jiki_cooldown_until = 0
        p.gomu_active_until = p.gomu_cooldown_until = 0
        save_data()
        await message.reply(f"✅ Gave **{p.name}**: {matched_name} ({matched_category})")

    # ==================== GLOBAL BAN ====================
    @app.on_message(filters.command("gban"))
    async def global_ban_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "**GLOBAL BAN**\n\n"
                "Usage: `/gban [user_id] [reason]`\n\n"
                "Announces to every group the bot is in."
            )
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ Invalid User ID!")
            return

        reason = " ".join(args[2:]) if len(args) > 2 else "No reason provided"

        if user_id in GBANNED:
            await message.reply(f"User `{user_id}` is already globally banned!")
            return
        if user_id == OWNER_ID:
            await message.reply("You can't ban yourself!")
            return

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name or "Unknown"
            user_username = f"@{user.username}" if user.username else "No username"
        except Exception:
            user_name = f"User {user_id}"
            user_username = "Unknown"

        GBANNED.add(user_id)
        save_banned()
        add_banned_player_info(
            user_id=user_id,
            user_name=user_name,
            user_username=user_username,
            reason=reason,
            banned_by=message.from_user.id,
            banned_by_name=message.from_user.first_name,
        )

        ban_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        announcement = (
            f"**GLOBAL BAN**\n\n"
            f"User: {user_name}\n"
            f"ID: `{user_id}`\n"
            f"Reason: {reason}\n"
            f"Banned by: {message.from_user.first_name}\n"
            f"Date: {ban_time}\n\n"
            f"This user is banned from ALL groups."
        )

        status_msg = await message.reply(
            f"Broadcasting ban...\n\n"
            f"{user_name} (`{user_id}`)\n\n"
            f"Groups: {len(bot_groups)}"
        )

        targets = set(bot_groups)
        targets.add(MAIN_GROUP_ID)
        targets.discard(message.chat.id)

        asyncio.create_task(
            _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name)
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN GLOBALLY BANNED!**\n\n"
                f"Reason: {reason}\n"
                f"By: {message.from_user.first_name}"
            )
        except Exception:
            pass

    @app.on_message(filters.command("ungban"))
    async def global_unban_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/ungban [user_id]`")
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return

        if user_id not in GBANNED:
            await message.reply(f"`{user_id}` is not globally banned!")
            return

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name or "Unknown"
        except Exception:
            user_name = f"User {user_id}"

        GBANNED.discard(user_id)
        save_banned()
        remove_banned_player_info(user_id)

        unban_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        announcement = (
            f"**GLOBAL UNBAN**\n\n"
            f"User: {user_name}\n"
            f"ID: `{user_id}`\n"
            f"Unbanned by: {message.from_user.first_name}\n"
            f"Date: {unban_time}"
        )

        status_msg = await message.reply(
            f"Broadcasting unban...\n\n"
            f"{user_name} (`{user_id}`)\n\n"
            f"Groups: {len(bot_groups)}"
        )

        targets = set(bot_groups)
        targets.add(MAIN_GROUP_ID)
        targets.discard(message.chat.id)

        asyncio.create_task(
            _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name)
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN UNBANNED!**\n\n"
                f"By: {message.from_user.first_name}"
            )
        except Exception:
            pass

    # ==================== COMMAND LOCK ====================
    @app.on_message(filters.command(["lock", "unlock"]))
    async def command_lock_cmd(client, message):
        if not message.from_user or not is_admin_or_owner(message.from_user.id):
            return

        command = (message.command[0] if message.command else "lock").split("@", 1)[0].lower()
        args = (message.text or "").split()
        if command == "unlock" or (len(args) > 1 and args[1].casefold() in {"off", "none", "clear"}):
            previous = get_command_lock_user_id()
            set_command_lock_user_id(None)
            await message.reply(
                "🔓 **COMMAND LOCK CLEARED**\n"
                + (f"Previously allowed player: `{previous}`" if previous else "No command lock was active.")
            )
            return

        target = message.reply_to_message.from_user if message.reply_to_message else None
        raw_id = args[1] if len(args) > 1 else None
        if command == "lock" and (raw_id is None or raw_id.casefold() == "all") and not target:
            set_command_lock_user_id(-1)
            await message.reply(
                "🔒 **ALL COMMANDS LOCKED**\n\n"
                "Only admins and the owner can use bot commands now.\n"
                "Use `/unlock` or `/lock off` to clear it."
            )
            return
        if raw_id:
            try:
                target_id = int(raw_id)
            except ValueError:
                await message.reply("⚠️ That user ID is invalid. Reply to a player or use `/lock [user_id]`.")
                return
        elif target:
            target_id = target.id
        else:
            await message.reply(
                "Use `/lock all` to allow commands only for admins/owner, or reply to a player with `/lock`.\n"
                "Clear it with `/unlock` or `/lock off`."
            )
            return

        if target_id in {OWNER_ID} or target_id in ADMINS:
            await message.reply("⚠️ That user is already an admin/owner and does not need the lock.")
            return
        set_command_lock_user_id(target_id)
        try:
            target_user = target or await client.get_users(target_id)
            target_name = target_user.first_name or str(target_id)
        except Exception:
            target_name = str(target_id)
        await message.reply(
            f"🔒 **COMMAND LOCK ENABLED**\n\n"
            f"Allowed player: **{target_name}** (`{target_id}`)\n"
            "All bot commands are now restricted to this player and admins/owner.\n"
            "Use `/unlock` or `/lock off` to clear it."
        )

    # ==================== TEMP BAN ====================
    @app.on_message(filters.command("ban"))
    async def temp_ban_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split()
        if len(args) < 3:
            await message.reply(
                "**TEMP BAN**\n\n"
                "Usage: `/ban [user_id] [time] [reason]`\n"
                "Time: `30s`, `5m`, `2h`, `1d`, `1w`"
            )
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return

        time_str = args[2].lower()
        reason = " ".join(args[3:]) if len(args) > 3 else "No reason"

        time_map = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        unit = time_str[-1]
        if unit not in time_map:
            await message.reply("⚠️ That time format is invalid.")
            return
        try:
            value = int(time_str[:-1])
        except ValueError:
            await message.reply("⚠️ That time value is invalid.")
            return

        duration = value * time_map[unit]
        if duration > 2_592_000:
            await message.reply("⚠️ Max 30 days!")
            return

        unban_time = time.time() + duration
        TEMP_BANNED[user_id] = unban_time
        save_temp_banned()

        unit_names = {"s": "second", "m": "minute", "h": "hour", "d": "day", "w": "week"}
        time_text = f"{value} {unit_names[unit]}{'s' if value != 1 else ''}"

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name
        except Exception:
            user_name = f"User {user_id}"

        await message.reply(
            f"**USER BANNED**\n\n"
            f"{user_name}\n"
            f"Duration: {time_text}\n"
            f"Reason: {reason}"
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN BANNED!**\n\n"
                f"Reason: {reason}\n"
                f"Duration: {time_text}"
            )
        except Exception:
            pass

    @app.on_message(filters.command("unban"))
    async def temp_unban_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/unban [user_id]`")
            return
        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return
        if user_id in TEMP_BANNED:
            del TEMP_BANNED[user_id]
            save_temp_banned()
            await message.reply(f"✅ Unbanned: `{user_id}`")
            try:
                await client.send_message(user_id, "**You have been unbanned!**")
            except Exception:
                pass
        else:
            await message.reply(f"`{user_id}` is not temp-banned!")

    @app.on_message(filters.command("banlist"))
    async def banlist_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        check_temp_bans()
        text = "**BANS**\n\n**Global:**\n"
        for uid in GBANNED:
            info = get_banned_player_info(uid)
            text += f"• {info.get('user_name', uid)} (`{uid}`) — {info.get('reason', 'N/A')}\n"
        text += "\n**Temp:**\n"
        for uid, t in TEMP_BANNED.items():
            rem = int(t - time.time())
            text += f"• `{uid}` — {rem // 3600}h left\n"
        await message.reply(text)

    @app.on_message(filters.command("bannedlist"))
    async def banned_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not GBANNED:
            await message.reply("📭 No globally banned users!")
            return
        text = "**GLOBALLY BANNED**\n\n"
        for i, uid in enumerate(GBANNED, 1):
            info = get_banned_player_info(uid)
            text += (
                f"{i}. **{info.get('user_name', uid)}**\n"
                f"   ID: `{uid}`\n"
                f"   Reason: {info.get('reason', 'N/A')}\n"
                f"   By: {info.get('banned_by_name', 'Unknown')}\n"
                f"   At: {info.get('banned_at_str', 'Unknown')}\n\n"
            )
        await message.reply(text)

    # ==================== SPAWN / DESPAWN / RESET ====================
    @app.on_message(filters.command("spawn"))
    async def spawn_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if message.chat.id in active_challenges:
            await message.reply("⚠️ Already active. Use `/despawn`.")
            return
        args = (message.text or "").split(maxsplit=1)
        requested_rarity = " ".join(args[1].strip().upper().split()) if len(args) > 1 else None
        if requested_rarity and requested_rarity not in get_character_rarities():
            await message.reply(
                f"Unknown rarity: `{requested_rarity}`\n"
                f"Available: {', '.join(get_character_rarities())}"
            )
            return
        from admin import spawn_character
        await spawn_character(app, message.chat.id, "Chat", requested_rarity=requested_rarity)
        await message.reply(
            f"✅ {requested_rarity or 'Random'} character spawned! Despawns in 5 min."
        )

    @app.on_message(filters.command("removechar"))
    async def remove_player_character_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split()
        target_user = message.reply_to_message.from_user if message.reply_to_message else None

        if target_user:
            if len(args) < 2:
                await message.reply("⚠️ Usage: reply to a player with `/removechar [character_id]`.")
                return
            user_id = target_user.id
            char_arg = args[1]
            remove_all = len(args) > 2 and args[2].casefold() == "all"
        elif len(args) >= 3:
            try:
                user_id = int(args[1])
            except ValueError:
                await message.reply("⚠️ That user ID is invalid.")
                return
            char_arg = args[2]
            remove_all = len(args) > 3 and args[3].casefold() == "all"
        else:
            await message.reply(
                "Usage: reply to a player with `/removechar [character_id]`, or use "
                "`/removechar [user_id] [character_id] [all]`."
            )
            return

        try:
            char_id = int(char_arg)
        except ValueError:
            await message.reply("⚠️ That character ID is invalid.")
            return

        player = get_player(user_id)
        matches = [
            index for index, captured in enumerate(player.captured_chars)
            if captured.get("id") is not None and str(captured.get("id")) == str(char_id)
        ]
        if not matches:
            await message.reply(f"⚠️ Player `{user_id}` does not own character `{char_id}`.")
            return

        remove_count = len(matches) if remove_all else 1
        if remove_all:
            player.captured_chars = [
                captured for captured in player.captured_chars
                if not (captured.get("id") is not None and str(captured.get("id")) == str(char_id))
            ]
        else:
            del player.captured_chars[matches[0]]
        if not any(str(captured.get("id")) == str(char_id) for captured in player.captured_chars):
            player.favorite_characters = [
                value for value in player.favorite_characters
                if str(value) != str(char_id)
            ]
        save_data()
        await message.reply(
            f"✅ Removed character `{char_id}` from player `{user_id}`.\n"
            f"Copies removed: **{remove_count}**"
        )

    @app.on_message(filters.command("despawn"))
    async def despawn_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if message.chat.id in active_challenges:
            name = active_challenges[message.chat.id]["char"].get("name", "?")
            del active_challenges[message.chat.id]
            await message.reply(f"✅ **{name}** despawned!")
        else:
            await message.reply("⚠️ No character is active right now.")

    @app.on_message(filters.command("reset"))
    async def reset_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if message.chat.id in active_challenges:
            del active_challenges[message.chat.id]
            await message.reply("✅ Reset!")
        else:
            await message.reply("⚠️ No character is active right now.")

    # ==================== PLAYER MANAGEMENT ====================
    @app.on_message(filters.command("setlevel"))
    async def set_level_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!\nUsage: `/setlevel [level]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/setlevel [level]`")
            return
        try:
            level = int(args[1])
        except ValueError:
            await message.reply("⚠️ Invalid level!")
            return
        if level < 1 or level > 200:
            await message.reply("Level needs to be 1-200!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        old = p.level
        p.level = level
        p.xp = 0
        save_data()
        await message.reply(f"✅ **{p.name}**: Lv.{old} → Lv.{level}")

    @app.on_message(filters.command("setxp"))
    async def set_xp_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!\nUsage: `/setxp [xp]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/setxp [xp]`")
            return
        try:
            xp = int(args[1])
        except ValueError:
            await message.reply("⚠️ Invalid XP!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.xp = max(0, xp)
        save_data()
        await message.reply(f"✅ **{p.name}** XP: {p.xp}")

    @app.on_message(filters.command("setbounty"))
    async def set_bounty_value_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!\nUsage: `/setbounty [amount]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/setbounty [amount]`")
            return
        amount = parse_amount(args[1])
        if amount is None or amount < 0:
            await message.reply("⚠️ That amount is invalid.")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.bounty = amount
        save_data()
        await message.reply(f"✅ **{p.name}** bounty: ฿{amount:,}")

    @app.on_message(filters.command("addbounty"))
    async def add_bounty_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        p, raw_amount, error = _admin_target_and_value(message, args, "amount")
        if error:
            await message.reply(error)
            return
        amount = parse_amount(raw_amount)
        if amount is None:
            await message.reply("⚠️ That amount is invalid.")
            return
        p.bounty = max(0, p.bounty + amount)
        save_data()
        await message.reply(f"✅ **{p.name}** new bounty: ฿{p.bounty:,}")

    @app.on_message(filters.command("addxp"))
    async def add_xp_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        p, raw_xp, error = _admin_target_and_value(message, args, "xp")
        if error:
            await message.reply(error)
            return
        try:
            amount = int(raw_xp)
        except (TypeError, ValueError):
            await message.reply("⚠️ Invalid XP amount!")
            return
        if amount < 0:
            await message.reply("XP amount can't be negative!")
            return

        p.xp += amount
        old_level = p.level
        while p.level < 200 and p.xp >= get_xp_needed(p.level):
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        save_data()
        level_note = f"\n📈 Level: {old_level} → {p.level}" if p.level != old_level else ""
        await message.reply(
            f"✅ **{p.name}** received **{amount:,} XP**.\n"
            f"Current XP: {p.xp:,}{level_note}"
        )

    @app.on_message(filters.command("addtoken"))
    async def add_token_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a user!\nUsage: `/addtoken [count]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/addtoken [count]`")
            return
        try:
            count = int(args[1])
        except ValueError:
            await message.reply("⚠️ Invalid count!")
            return
        if abs(count) > 1000:
            await message.reply("⚠️ Max 1000 tokens per command.")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.advanced_token = max(0, p.advanced_token + count)
        save_data()
        await message.reply(f"✅ **{p.name}** tokens: {p.advanced_token}")

    @app.on_message(filters.command("resetplayer"))
    async def reset_player_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        if len(args) != 3 or args[2].casefold() != "confirm":
            suffix = f"{args[1]} confirm" if len(args) > 1 else "[user_id] confirm"
            await message.reply(f"⚠️ This resets the player's full account. To proceed, send `/resetplayer {suffix}`.")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply("⚠️ That ID is invalid.")
            return
        key = str(target_id)
        if key not in user_data:
            await message.reply(f"⚠️ Player `{target_id}` wasn't found.")
            return

        old_player = user_data[key]
        old_name = old_player.name
        old_username = old_player.username
        old_bounty = old_player.bounty
        old_level = old_player.level

        fresh = Player(target_id)
        fresh.name = old_name
        fresh.username = old_username
        user_data[key] = fresh
        save_data()

        await message.reply(
            f"**PLAYER RESET**\n\n"
            f"{old_name} (`{target_id}`)\n"
            f"Before: ฿{old_bounty:,} Lv.{old_level}\n"
            f"After: ฿0 Lv.1"
        )
        try:
            await client.send_message(target_id, "Your account has been reset!")
        except Exception:
            pass

    @app.on_message(filters.command(["resetbounty", "resetlv", "resethaki", "resetcharacter"]))
    async def reset_player_category_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return

        words = (message.text or message.caption or "").split()
        command = (message.command[0] if getattr(message, "command", None) else "").split("@", 1)[0].casefold()
        if command not in {"resetbounty", "resetlv", "resethaki", "resetcharacter"}:
            command = words[0].split("@", 1)[0].lstrip("/").casefold() if words else ""
        usage = (
            f"Usage: `/{command} [user_id] confirm`, reply with `/{command} confirm`, "
            f"or use `/{command} all confirm` for everyone."
        )
        descriptions = {
            "resetbounty": "bounty (set to 0)",
            "resetlv": "level and XP (set to Level 1, 0 XP)",
            "resethaki": "Haki progress and state",
            "resetcharacter": "owned character collection (Devil Fruit is unchanged)",
        }
        if command not in descriptions:
            await message.reply("Unknown reset command.")
            return

        if len(words) >= 2 and words[1].casefold() == "all":
            if len(words) != 3 or words[2].casefold() != "confirm":
                await message.reply(
                    f"⚠️ This will reset {descriptions[command]} for **all {len(user_data)} players**.\n"
                    f"To proceed, send `/{command} all confirm`."
                )
                return
            backup_result = create_json_backup(f"{command}_all")
            if backup_result["failed"]:
                await message.reply(
                    "Backup failed; reset cancelled. Failed files: "
                    + ", ".join(backup_result["failed"])
                )
                return
            targets = list(user_data.values())
            backup_path = os.path.join(
                backup_result["directory"], f"{backup_result['timestamp']}_*.json"
            )
        else:
            target_id = None
            confirmed = False
            if message.reply_to_message and message.reply_to_message.from_user and len(words) == 2 and words[1].casefold() == "confirm":
                target_id = int(message.reply_to_message.from_user.id)
                confirmed = True
            elif message.reply_to_message and message.reply_to_message.from_user and len(words) == 1:
                await message.reply(f"⚠️ This will reset {descriptions[command]} for the replied-to player. To proceed, send `/{command} confirm`.")
                return
            elif len(words) in {2, 3}:
                try:
                    target_id = int(words[1])
                except ValueError:
                    await message.reply("⚠️ That user ID is invalid.\n" + usage)
                    return
                confirmed = len(words) == 3 and words[2].casefold() == "confirm"
            else:
                await message.reply(usage)
                return
            if not confirmed:
                await message.reply(f"⚠️ This will reset {descriptions[command]} for player `{target_id}`. To proceed, send `/{command} {target_id} confirm`.")
                return
            key = str(target_id)
            if key not in user_data and target_id not in user_data:
                await message.reply(f"⚠️ Player `{target_id}` not found.")
                return
            targets = [user_data.get(key, user_data.get(target_id))]
            backup_path = None

        if command == "resetbounty":
            for player in targets:
                player.bounty = 0
        elif command == "resetlv":
            for player in targets:
                player.level = 1
                player.xp = 0
        elif command == "resethaki":
            from config import HAKI_BAR_MAX
            for player in targets:
                player.haki = None
                player.haki_level = 0
                player.haki_active = False
                player.haki_bar = HAKI_BAR_MAX
                player.haki_bar_updated = 0
                player.haki_is_advanced = False
                player.advanced_haki = False
        else:  # resetcharacter
            for player in targets:
                player.captured_chars = []

        save_data()
        if backup_path:
            await message.reply(
                f"✅ Reset {descriptions[command]} for **{len(targets)} players**.\n"
                f"Backup: `{os.path.relpath(backup_path)}`"
            )
        else:
            player = targets[0]
            await message.reply(
                f"✅ Reset {descriptions[command]} for **{player.name or 'Player'}** "
                f"(`{player.user_id}`)."
            )

    @app.on_message(filters.command("refreshclaim"))
    async def refresh_claim_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return

        args = (message.text or message.caption or "").split()
        if len(args) != 3 or args[1].casefold() != "all" or args[2].casefold() != "confirm":
            await message.reply(
                f"⚠️ This will let all **{len(user_data)} players** claim the main-group reward again.\n"
                "Only their claim eligibility will be reset; their existing rewards stay unchanged.\n\n"
                "To proceed, send `/refreshclaim all confirm`."
            )
            return

        refreshed = 0
        for player in user_data.values():
            if getattr(player, "claimed_main", False):
                player.claimed_main = False
                refreshed += 1
        save_data()
        await message.reply(
            f"✅ Refreshed `/claim` eligibility for **{refreshed} players**. "
            "They can claim the main-group reward again. Existing balances and rewards were not changed."
        )

    @app.on_message(filters.command("resetall"))
    async def reset_all_players_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        args = message.text.split()
        if len(args) != 2 or args[1].lower() != "confirm":
            await message.reply(
                f"**RESET ALL PLAYERS**\n\n"
                f"Total Players: {len(user_data)}\n\n"
                f"Type `/resetall confirm` to proceed."
            )
            return

        backup_result = create_json_backup("resetall")
        if backup_result["failed"]:
            await message.reply(
                "Backup failed; reset cancelled. Failed files: "
                + ", ".join(backup_result["failed"])
            )
            return
        ts = backup_result["timestamp"]
        backup_path = os.path.join(backup_result["directory"], f"{ts}_*.json")

        total = len(user_data)
        new_data = {}
        for uid, old in user_data.items():
            fresh = Player(uid)
            fresh.name = old.name
            fresh.username = old.username
            new_data[uid] = fresh

        user_data.clear()
        user_data.update(new_data)
        save_data()

        await message.reply(
            f"**ALL PLAYERS RESET**\n\n"
            f"Players: **{total}**\n"
            f"Backup: `{os.path.relpath(backup_path)}`"
        )

    # ==================== SYSTEM ====================
    @app.on_message(filters.command("check"))
    async def check_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        rarity_lines = "\n".join(
            f"{get_rarity_emoji(rarity)} {rarity}: "
            f"{sum(1 for c in normal_characters + mythical_characters + exalted_characters if str(c.get('rarity', 'NORMAL')).upper() == rarity)}"
            for rarity in get_character_rarities()
        )
        await message.reply(
            f"**SYSTEM CHECK**\n\n"
            f"Users: {len(user_data)}\n"
            f"Admins: {len(ADMINS)}\n"
            f"Global bans: {len(GBANNED)}\n"
            f"Temp bans: {len(TEMP_BANNED)}\n"
            f"Active challenges: {len(active_challenges)}\n"
            f"Characters by rarity:\n{rarity_lines}"
        )

    @app.on_message(filters.command("gstats"))
    async def global_stats_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        total_b = sum(p.bounty for p in user_data.values())
        total_v = sum(p.vault for p in user_data.values())
        total_c = sum(len(p.captured_chars) for p in user_data.values())
        rarity_lines = "\n".join(
            f"{rarity}: {sum(1 for c in normal_characters + mythical_characters + exalted_characters if str(c.get('rarity', 'NORMAL')).upper() == rarity)}"
            for rarity in get_character_rarities()
        )
        await message.reply(
            f"**GLOBAL STATS**\n\n"
            f"Players: {len(user_data)}\n"
            f"Total bounty: ฿{total_b:,}\n"
            f"Total vault: ฿{total_v:,}\n"
            f"Total chars: {total_c}\n"
            f"Characters by rarity:\n{rarity_lines}\n"
            f"Bans: {len(GBANNED)} global, {len(TEMP_BANNED)} temp\n"
            f"Admins: {len(ADMINS)}\n"
            f"Groups: {len(bot_groups)}"
        )

    @app.on_message(filters.command("resetcd"))
    async def reset_cd_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        from utils import last_command_time
        last_command_time.clear()
        for p in user_data.values():
            if hasattr(p, "pay_cd"):
                p.pay_cd = 0
            if hasattr(p, "rob_cd"):
                p.rob_cd = 0
        save_data()
        await message.reply("✅ All cooldowns reset!")

    @app.on_message(filters.command("checkgroup"))
    async def check_group_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        try:
            member = await client.get_chat_member(MAIN_GROUP_ID, client.me.id)
            chat = await client.get_chat(MAIN_GROUP_ID)
            status = str(member.status).split(".")[-1].upper()
            await message.reply(
                f"**Group Check**\n\n"
                f"Config ID: `{MAIN_GROUP_ID}`\n"
                f"Actual ID: `{chat.id}`\n"
                f"Title: {chat.title}\n"
                f"Bot Status: {status}\n"
                f"Match: {'Yes' if chat.id == MAIN_GROUP_ID else 'No'}"
            )
        except Exception as e:
            await message.reply(f"Error: {e}")

    @app.on_message(filters.command("id"))
    async def get_id_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            await message.reply(f"**User ID:** `{u.id}`\n**Name:** {u.first_name}")
        else:
            await message.reply(f"**Chat ID:** `{message.chat.id}`")

    # ==================== BROADCAST ====================
    @app.on_message(filters.command("broadcast"))
    async def broadcast_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not message.reply_to_message:
            await message.reply(
                "**BROADCAST**\n\n"
                "Reply to a message with:\n"
                "`/broadcast groups`\n"
                "`/broadcast users`\n"
                "`/broadcast all`"
            )
            return
        args = message.text.split()
        target = args[1].lower() if len(args) > 1 else "all"
        if target not in ("groups", "users", "all"):
            await message.reply("Use: groups, users, all")
            return
        set_pending_broadcast(message.from_user.id, {
            "chat_id": message.reply_to_message.chat.id,
            "message_id": message.reply_to_message.id,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data=f"confirm_broadcast_{target}_{message.from_user.id}")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_broadcast")],
        ])
        await message.reply(
            f"**CONFIRM BROADCAST**\n\n"
            f"Target: **{target.upper()}**\n\n"
            f"Click confirm to proceed.",
            reply_markup=kb,
        )

    @app.on_message(filters.command("forwardall"))
    async def forward_all_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a message with `/forwardall`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id,
            "message_id": orig.id,
            "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardall")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply("**CONFIRM FORWARD**\n\nForward to ALL groups and users?", reply_markup=kb)

    @app.on_message(filters.command("forwardgroups"))
    async def forward_groups_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a message with `/forwardgroups`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id, "message_id": orig.id, "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardgroups")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply("**CONFIRM FORWARD TO GROUPS**", reply_markup=kb)

    @app.on_message(filters.command("forwardusers"))
    async def forward_users_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not message.reply_to_message:
            await message.reply("⚠️ Reply to a message with `/forwardusers`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id, "message_id": orig.id, "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardusers")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply(f"**CONFIRM FORWARD TO USERS**\n\nTotal: {len(user_data)}", reply_markup=kb)

    # ==================== UPDATE ANNOUNCEMENT ====================
    @app.on_message(filters.command("sendupdate"))
    async def send_update_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        if not UPDATE_CHANNEL_ID:
            await message.reply("UPDATE_CHANNEL_ID not set!")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("⚠️ Usage: `/sendupdate [message]`")
            return
        try:
            await client.send_message(
                UPDATE_CHANNEL_ID,
                f"**UPDATE ANNOUNCEMENT**\n\n"
                f"Version: `{BOT_VERSION}`\n"
                f"{datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"{args[1]}\n\n"
                f"@Grand_Line_Sentinel_bot"
            )
            await message.reply("✅ Sent!")
        except Exception as e:
            await message.reply(f"Failed: {e}")

    # ==================== PATTERN ====================
    @app.on_message(filters.command("pattern"))
    async def pattern_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        from config import PATTERNS, PATTERN_OVERRIDE_HOURS
        from data_manager import (
            get_current_pattern, set_current_pattern,
            clear_pattern_override, reset_sequence,
        )

        args = message.text.split()

        if len(args) == 1:
            current = get_current_pattern()
            info = PATTERNS.get(current, PATTERNS["pattern2"])
            await message.reply(
                f"**CURRENT PATTERN**\n\n"
                f"{info['emoji']} **{info['name']}**\n\n"
                f"Use `/currentpattern` for full status."
            )
            return

        if args[1].lower() == "auto":
            clear_pattern_override()
            await message.reply("✅ Override cleared. Auto mode resumed.")
            return

        if args[1].lower() == "reset":
            reset_sequence()
            await message.reply("✅ Sequence positions reset.")
            return

        mapping = {"1": "pattern1", "2": "pattern2", "3": "pattern3", "4": "pattern4"}
        if args[1] not in mapping:
            await message.reply("⚠️ Usage: `/pattern [1/2/3/4|auto|reset]`")
            return

        chosen = mapping[args[1]]
        set_current_pattern(chosen, manual=True)
        info = PATTERNS[chosen]

        await message.reply(
            f"✅ **Pattern overridden!**\n\n"
            f"{info['emoji']} **{info['name']}**\n\n"
            f"Expires in {PATTERN_OVERRIDE_HOURS}h"
        )

    @app.on_message(filters.command("currentpattern"))
    async def current_pattern_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        from config import (
            PATTERNS, TIME_SCHEDULE, AUTO_SWITCH_ENABLED, DEFAULT_PATTERN,
        )
        from data_manager import get_current_pattern, get_override_status

        effective = get_current_pattern()
        info = PATTERNS.get(effective, PATTERNS.get(DEFAULT_PATTERN, {}))

        now = datetime.now(TIMEZONE)
        hour, minute = now.hour, now.minute
        auto = TIME_SCHEDULE.get(hour, "—")

        override = get_override_status()
        if override.get("active"):
            rem = override["remaining_seconds"]
            h, m = rem // 3600, (rem % 3600) // 60
            override_status = f"Active — `{override['pattern']}` (expires in {h}h {m}m)"
        else:
            override_status = "None (auto mode)"

        auto_status = "Enabled" if AUTO_SWITCH_ENABLED else "Disabled"
        next_hour = (hour + 1) % 24
        next_auto = TIME_SCHEDULE.get(next_hour, "—")

        text = (
            f"**PATTERN STATUS**\n"
            f"──────────────────\n\n"
            f"**Active:** {info.get('emoji', '?')} {info.get('name', '?')}\n\n"
            f"**Time:**\n"
            f"• Now: `{hour:02d}:{minute:02d}`\n"
            f"• Auto now: `{auto}`\n"
            f"• Next hour: `{next_auto}`\n\n"
            f"**Override:** {override_status}\n"
            f"**Auto:** {auto_status}\n"
            f"──────────────────\n\n"
            f"**Schedule:**\n"
        )

        for h in range(24):
            p = TIME_SCHEDULE.get(h, "—")
            p_info = PATTERNS.get(p, {})
            emoji = p_info.get("emoji", "?")
            marker = "▶️ " if h == hour else "   "
            text += f"{marker}`{h:02d}:00` {emoji} {p}\n"

        text += f"\n──────────────────\n@Grand_Line_Sentinel_bot"

        await message.reply(text)

    # ==================== STATS ====================
    @app.on_message(filters.command("stats"))
    async def stats_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        try:
            total_players = len(user_data)
            total_groups = len(bot_groups)
            now = time.time()

            def is_active(p, days):
                d = getattr(p, "daily", 0)
                if isinstance(d, (int, float)) and d:
                    return (now - d) < days * 86400
                return False

            active_24h = sum(1 for p in user_data.values() if is_active(p, 1))
            active_7d = sum(1 for p in user_data.values() if is_active(p, 7))

            total_bounty = sum(getattr(p, "bounty", 0) for p in user_data.values())
            total_vault = sum(getattr(p, "vault", 0) for p in user_data.values())

            now_local = datetime.now(TIMEZONE)

            text = (
                f"**BOT STATISTICS**\n"
                f"──────────────────\n"
                f"{now_local.strftime('%Y-%m-%d %H:%M')}\n"
                f"──────────────────\n\n"
                f"**USERS**\n"
                f"Total: {total_players:,}\n"
                f"Active (24h): {active_24h:,}\n"
                f"Active (7d): {active_7d:,}\n\n"
                f"**GROUPS**\n"
                f"Total: {total_groups:,}\n\n"
                f"**MODERATION**\n"
                f"Global bans: {len(GBANNED):,}\n"
                f"Temp bans: {len(TEMP_BANNED):,}\n"
                f"Admins: {len(ADMINS):,}\n\n"
                f"**ECONOMY**\n"
                f"Total bounty: ฿{total_bounty:,}\n"
                f"Total vault: ฿{total_vault:,}\n\n"
                f"**CHARACTERS**\n"
                f"Normal: {len(normal_characters):,}\n"
                f"Mythical: {len(mythical_characters):,}\n\n"
                f"──────────────────\n@Grand_Line_Sentinel_bot"
            )

            if len(text) > 4000:
                for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                    await message.reply(chunk)
            else:
                await message.reply(text)

        except Exception as e:
            print(f"[stats] {e}")
            await message.reply(f"Error: `{e}`")

    # ==================== GROUPS ====================
    @app.on_message(filters.command("groups"))
    async def groups_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        if not bot_groups:
            await message.reply("📭 **No groups tracked yet.**")
            return

        # Reconcile with Telegram first: pull every group chat the bot is in.
        try:
            from pyrogram.enums import ChatType
            async for dialog in client.get_dialogs():
                dchat = getattr(dialog, "chat", None)
                if dchat and dchat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    if dchat.id not in bot_groups:
                        bot_groups.add(dchat.id)
            save_bot_groups()
        except Exception as e:
            print(f"[groups] dialog scan skipped: {e}")

        groups_list = list(bot_groups)

        status = await message.reply(f"Loading {len(groups_list)} groups...")

        text = f"**BOT GROUPS** ({len(bot_groups)} total)\n"
        text += "──────────────────\n\n"

        dead = []

        for i, gid in enumerate(groups_list, 1):
            try:
                try:
                    gid_int = int(gid)
                except (ValueError, TypeError):
                    gid_int = gid

                chat = await client.get_chat(gid_int)
                await asyncio.sleep(0.05)

                title = chat.title or "Untitled"
                if len(title) > 30:
                    title = title[:27] + "…"

                text += f"{i}. **{title}**\n"

                if chat.username:
                    text += f"   @{chat.username}\n"
                text += f"   `{gid}`\n\n"

            except Exception:
                dead.append(gid)
                text += f"{i}. Inaccessible\n   `{gid}`\n\n"

        # Drop groups the bot is no longer part of.
        for _gid in dead:
            bot_groups.discard(_gid)
        if dead:
            try:
                save_bot_groups()
            except Exception:
                pass

        text += f"──────────────────\n@Grand_Line_Sentinel_bot"

        try:
            await status.delete()
        except Exception:
            pass

        if len(text) > 4000:
            for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                await message.reply(chunk)
        else:
            await message.reply(text)

    # ==================== CHANGE DROP TIME ====================
    @app.on_message(filters.command("changetime"))
    async def change_time_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split()
        if len(args) != 2:
            current = get_group_drop_count(message.chat.id)
            await message.reply(
                "**CHANGE DROP TIME**\n\n"
                f"Current setting: **{current}** messages per drop\n\n"
                "Usage: `/changetime [50|100|150|200]`\n"
                "Sets how many messages are needed before a character drops "
                "in this group."
            )
            return

        try:
            n = int(args[1])
        except ValueError:
            await message.reply("⚠️ That number is invalid. Use 50, 100, 150 or 200.")
            return

        if not set_group_drop_count(message.chat.id, n):
            await message.reply("Allowed values: **50, 100, 150** or **200**.")
            return

        await message.reply(
            f"✅ Character drop set to **{n}** messages in this group."
        )

    @app.on_message(filters.command("setnextdrop"))
    async def set_next_drop_rarity_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        args = (message.text or "").split(maxsplit=2)
        if message.chat.id > 0:
            if len(args) < 2:
                await message.reply("Usage in private chat: `/setnextdrop [group_id] [rarity|off]`")
                return
            try:
                target_chat_id = int(args[1])
            except ValueError:
                await message.reply("Put the target group ID first, for example `/setnextdrop -1001234567890 MYTHICAL`.")
                return
            if target_chat_id >= 0:
                await message.reply("The target needs to be a group/supergroup ID (usually starts with `-100`).")
                return
            try:
                target_chat = await client.get_chat(target_chat_id)
            except Exception as exc:
                print(f"[setnextdrop target] {target_chat_id}: {exc}")
                await message.reply("Can't access that group. Check its ID and check the bot is a member.")
                return
            rarity_input = args[2] if len(args) > 2 else None
            target_label = getattr(target_chat, "title", None) or str(target_chat_id)
        else:
            target_chat_id = message.chat.id
            rarity_input = args[1] if len(args) > 1 else None
            target_label = message.chat.title or "this group"

        current = get_group_next_drop_rarity(target_chat_id)
        if rarity_input is None:
            status = f"Queued rarity: **{current}**" if current else "Queued rarity: **none** (normal random selection)"
            await message.reply(
                f"**NEXT CHARACTER DROP RARITY**\n{status}\n\n"
                "In this group: `/setnextdrop [rarity|off]`\n"
                "From private chat: `/setnextdrop [group_id] [rarity|off]`\n"
                "The queued rarity affects only the selected group’s next spawn."
            )
            return
        rarity = " ".join(rarity_input.strip().upper().split())
        if rarity in {"OFF", "CLEAR", "NONE", "RANDOM"}:
            clear_group_next_drop_rarity(target_chat_id)
            await message.reply(f"✅ Cleared the queued rarity for **{target_label}**. Its next spawn will be random.")
            return
        known_rarities = get_character_rarities()
        if rarity not in known_rarities:
            await message.reply(
                "Unknown rarity. Available: " + ", ".join(f"`{r}`" for r in known_rarities)
            )
            return
        all_characters = normal_characters + mythical_characters + exalted_characters
        if not any(" ".join(str(c.get("rarity", "NORMAL")).upper().split()) == rarity for c in all_characters):
            await message.reply(f"There are no characters in the **{rarity}** pool to drop.")
            return
        if not set_group_next_drop_rarity(target_chat_id, rarity):
            await message.reply("Couldn't save the next-drop rarity.")
            return
        await message.reply(
            f"✅ The next character spawn in **{target_label}** will be **{rarity}**.\n"
            "This setting applies to this group only and clears after that spawn."
        )

    @app.on_message(filters.command("removegroup"))
    async def remove_group_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/removegroup [group_id]`")
            return
        try:
            gid = int(args[1])
        except ValueError:
            await message.reply("⚠️ Invalid group ID!")
            return
        if gid not in bot_groups:
            await message.reply(f"`{gid}` is not tracked!")
            return
        bot_groups.discard(gid)
        save_bot_groups()
        await message.reply(f"✅ Removed `{gid}`.")

    @app.on_message(filters.command("addgroup"))
    async def add_group_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/addgroup [group_id]`")
            return
        try:
            gid = int(args[1])
            add_bot_group(gid)
            await message.reply(f"✅ Added group: `{gid}`")
        except Exception as e:
            await message.reply(f"Error: {e}")

    @app.on_message(filters.command("listgroups"))
    async def list_groups_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return
        if not bot_groups:
            await message.reply("📭 No groups saved!")
            return
        text = "**BOT GROUPS**\n\n"
        for i, gid in enumerate(bot_groups, 1):
            text += f"{i}. `{gid}`\n"
        await message.reply(text)

    # ==================== UPLOADED JSON RESTORE ====================
    @app.on_message(filters.command("restorejson"))
    async def restore_json_upload_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        replied = message.reply_to_message
        document = replied.document if replied else None
        filename = (document.file_name or "") if document else ""
        if not document or not filename.lower().endswith(".json"):
            await message.reply(
                "Reply to a `.json` document with `/restorejson`.\n\n"
                "Supported files: split player data (bounty, progress, characters, Haki, inventory, profile), "
                "legacy users.json, characters, bans, groups, crews, price overrides, and awakening spell GIF settings."
            )
            return

        base = os.path.basename(filename)
        live_name = next(
            (candidate for candidate in UPLOAD_JSON_NAMES
             if base == candidate or base.endswith(f"_{candidate}")),
            None,
        )
        if not live_name:
            await message.reply(
                "Unsupported JSON filename. Use one of: "
                + ", ".join(sorted(UPLOAD_JSON_NAMES))
            )
            return

        from config import DATA_DIR
        import uuid
        import json as _json
        import_path = os.path.join(DATA_DIR, "imports")
        os.makedirs(import_path, exist_ok=True)
        token = f"{datetime.now(TIMEZONE).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        stored_path = os.path.join(import_path, f"{token}_{live_name}")
        try:
            downloaded = await client.download_media(replied, file_name=stored_path)
            if not downloaded or not os.path.exists(stored_path):
                raise ValueError("Telegram did not return the downloaded file")
            with open(stored_path, "r", encoding="utf-8") as fh:
                payload = _json.load(fh)
            if live_name == "users.json" and not isinstance(payload, dict):
                raise ValueError("users.json must contain a JSON object")
            if live_name in PLAYER_DATA_FILES and not isinstance(payload, dict):
                raise ValueError(f"{live_name} must contain a JSON object")
            if live_name != "users.json" and live_name != "crews.json" and not isinstance(payload, (dict, list)):
                raise ValueError("JSON has an invalid top-level format")
        except Exception as exc:
            try:
                os.remove(stored_path)
            except OSError:
                pass
            await message.reply(f"JSON download/validation failed: `{exc}`")
            return

        PENDING_UPLOAD_RESTORES[token] = {
            "path": stored_path,
            "live_name": live_name,
        }
        await message.reply(
            f"📥 **JSON DOWNLOADED**\n\n"
            f"File: `{live_name}`\n"
            f"Stored safely in the bot imports folder.\n\n"
                f"Restoring this file will replace the current `{live_name}`. Legacy `users.json` is converted into the split player files. Confirm?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚠️ Confirm Restore", callback_data=f"restore_upload_confirm_{token}")],
                [InlineKeyboardButton("Cancel", callback_data="noop")],
            ]),
        )

    # ==================== BACKUP ====================
    @app.on_message(filters.command("backup"))
    async def backup_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        save_data()
        result = create_json_backup("manual")
        ts = result["timestamp"]
        saved = len(result["saved"])
        failed = len(result["failed"])

        await message.reply(
            f"💾 **BACKUP COMPLETE**\n\n"
            f"📁 `data/backups/`\n"
            f"📊 {saved} saved, {failed} failed\n"
            f"⏰ `{ts}`\n"
            f"📦 Files: {', '.join(result['saved'])}"
        )

    @app.on_message(filters.command("backups"))
    async def list_backups_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        from config import DATA_DIR
        from collections import defaultdict

        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir):
            await message.reply("📭 No backups yet. Use `/backup`.")
            return

        snaps = defaultdict(list)
        for fname in os.listdir(backup_dir):
            if "_" in fname and fname.endswith(".json"):
                parts = fname.split("_", 2)
                if len(parts) >= 3:
                    ts = f"{parts[0]}_{parts[1]}"
                    snaps[ts].append(fname)

        if not snaps:
            await message.reply("📭 No backups found.")
            return

        sorted_ts = sorted(snaps.keys(), reverse=True)[:15]
        text = f"💾 **BACKUPS** ({len(snaps)} total)\n──────────────────\n\n"

        for i, ts in enumerate(sorted_ts, 1):
            files = snaps[ts]
            try:
                dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=TIMEZONE)
                friendly = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                friendly = ts

            total = 0
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(backup_dir, f))
                except Exception:
                    pass

            text += f"**{i}.** `{ts}`\n   📅 {friendly}\n   📊 {len(files)} files • {total // 1024} KB\n\n"

        text += f"──────────────────\n💡 `/restore [timestamp]`\n\n@Grand_Line_Sentinel_bot"
        await message.reply(text)

    @app.on_message(filters.command("restore"))
    async def restore_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        from config import DATA_DIR
        args = message.text.split()
        if len(args) != 2:
            await message.reply(
                "**RESTORE**\n\n"
                "Usage: `/restore [timestamp]`\n\n"
                "Use `/backups` to list timestamps."
            )
            return

        ts = args[1]
        backup_dir = os.path.join(DATA_DIR, "backups")
        player_snapshot_exists = any(
            os.path.exists(os.path.join(backup_dir, f"{ts}_{filename}"))
            for filename in ("users.json", *PLAYER_DATA_FILES)
        )

        if not player_snapshot_exists:
            await message.reply(f"No backup found for `{ts}`!")
            return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Confirm Restore", callback_data=f"restore_confirm_{ts}")],
            [InlineKeyboardButton("Cancel", callback_data="noop")],
        ])

        await message.reply(
            f"⚠️ **RESTORE FROM `{ts}`?**\n\n"
            f"This will **overwrite** current data!\n\n"
            f"Are you sure?",
            reply_markup=kb,
        )

    @app.on_message(filters.command("delbackup"))
    async def del_backup_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        from config import DATA_DIR
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/delbackup [timestamp]`")
            return

        ts = args[1]
        backup_dir = os.path.join(DATA_DIR, "backups")

        deleted = 0
        try:
            for fname in os.listdir(backup_dir):
                if fname.startswith(ts + "_"):
                    try:
                        os.remove(os.path.join(backup_dir, fname))
                        deleted += 1
                    except Exception:
                        pass
        except Exception:
            pass

        if deleted:
            await message.reply(f"✅ Deleted {deleted} files from `{ts}`")
        else:
            await message.reply(f"No backup found for `{ts}`")

    # ==================== EDIT CHARACTER (owner + admin) ====================
    @app.on_message(filters.command("edit") | filters.command("editchar") | filters.command("cedit"))
    async def edit_char_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "✏️ **EDIT CHARACTER**\n\n"
                "**Usage:**\n"
                "• `/edit <id> <new_name>` — rename only\n"
                "• `/edit <id>` + reply to a photo — change photo only\n"
                "• `/edit <id> <new_name>` + reply to a photo — rename + photo\n"
                "• `/edit <id> <new_name> rarity [name]` — change rarity\n\n"
                "💡 Use `/charslist` to find the character ID."
            )
            return

        parts = args[1].split()
        if not parts:
            await message.reply("⚠️ Usage: `/edit <id> [new_name]`")
            return

        try:
            cid = int(parts[0])
        except ValueError:
            await message.reply("⚠️ That character ID is invalid.")
            return

        # Parse: id [name words...] rarity [built-in or owner-created name]
        new_name = None
        new_rarity = None
        body = parts[1:]
        rarity_indexes = [i for i, word in enumerate(body) if word.lower() == "rarity"]
        if rarity_indexes and rarity_indexes[-1] < len(body) - 1:
            rarity_index = rarity_indexes[-1]
            candidate = " ".join(body[rarity_index + 1:]).strip().upper()
            if candidate in get_character_rarities():
                new_rarity = candidate
                name_words = body[:rarity_index]
            else:
                name_words = body
        else:
            name_words = body
        if name_words:
            new_name = " ".join(name_words).strip()

        target = get_character_by_id(cid)
        if not target:
            await message.reply(f"No character with ID `{cid}`!")
            return

        new_image = None
        if message.reply_to_message:
            rep = message.reply_to_message
            if rep.photo:
                new_image = rep.photo.file_id
            elif rep.document and getattr(rep.document, "mime_type", None):
                if rep.document.mime_type.startswith("image"):
                    new_image = rep.document.file_id

        if new_name is None and not new_image and new_rarity is None:
            await message.reply(
                f"Nothing to update!\n\n"
                f"Current: **{target.get('name')}** (ID: `{cid}`, {target.get('rarity','NORMAL')})\n\n"
                f"Provide a new name, reply to an image, or include `rarity NORMAL|MYTHICAL|EXALTED`."
            )
            return

        result = update_character(
            cid,
            new_name=new_name,
            new_image=new_image,
            new_rarity=new_rarity,
            new_media_type="photo" if new_image else None,
        )
        if not result:
            await message.reply("Failed to update (character disappeared?).")
            return

        name_changed = result["new_name"] != result["old_name"]
        image_changed = result["new_image"] != result["old_image"]
        rarity_changed = result["new_rarity"] != result["old_rarity"]
        upload_status = await _update_character_upload_post(client, target, result)

        lines = [f"✅ **CHARACTER UPDATED**\n", f"ID: `{cid}`"]
        if name_changed:
            lines.append(f"Name: {result['old_name']} → **{result['new_name']}**")
        if image_changed:
            lines.append("Photo: ✅ updated")
        else:
            lines.append("Photo: — unchanged")
        if rarity_changed:
            lines.append(f"Rarity: {result['old_rarity']} → **{result['new_rarity']}**")
        lines.append(f"Upload channel: {upload_status}.")
        lines.append("")
        lines.append("All copies in users' collections have been synced.\n\n🤖 @Grand_Line_Sentinel_bot")
        await message.reply("\n".join(lines))

    # ==================== ADMINHELP (admin-only) ====================
    @app.on_message(filters.command("adminhelp"))
    async def admin_help_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            return

        await message.reply(
            f"👑 **ADMIN COMMANDS** 👑\n\n"
            f"🚫 **Bans:**\n"
            f"• `/ban [id] [time] [reason]`\n"
            f"• `/unban [id]`\n"
            f"• `/banlist`\n"
            f"• `/bannedlist`\n\n"
            f"🎮 **Characters:**\n"
            f"• `/sent` — resend all character images to the upload channel\n"
            f"• `/ncradd`\n"
            f"• `/mcradd`\n"
            f"• `/ncrdelete [id]`\n"
            f"• `/mcrdelete [id]`\n"
            f"• `/ecradd`, `/ecrdelete [id]` — manage Exalted characters\n"
            f"• `/edit <id> [new_name] rarity [name]` — change name / photo / rarity\n"
            f"• `/rarities` — view available rarities\n"
            f"• `/raritypercent` — check rarity percentages\n"
            f"• `/setrarityemoji [rarity] [emoji]` — set rarity emoji\n"
            f"• `/setrarityspoiler [rarity] [on|off]` — hide photos for selected rarity\n"
            f"• `/lock` or `/lock all` — restrict all commands to admins/owner; reply to a player to restrict to that player\n"
            f"• `/unlock` or `/lock off` — clear command lock\n"
            f"• `/setraritychance [rarity] [percent]` — set drop chance\n"
            f"• `/setrarityreward [rarity] [min] [max]` — set winning bounty range\n"
            f"• `/charslist`\n\n"
            f"📊 **Stats:**\n"
            f"• `/stats`\n"
            f"• `/groups`\n"
            f"• `/id` — check a user ID (reply) or chat ID\n\n"
            f"📢 **Broadcast:**\n"
            f"• `/broadcast [groups|users|all]`\n"
            f"• `/forwardall`, `/forwardgroups`, `/forwardusers`\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )

    # ==================== OWNERHELP (owner-only) ====================
    @app.on_message(filters.command("ownerhelp"))
    async def owner_help_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            return

        help_text = (
            f"👑 **OWNER COMMANDS** 👑\n\n"
            f"👥 **Admins:**\n"
            f"• `/adda [id]`\n"
            f"• `/removeadmin [id]`\n"
            f"• `/admins`\n\n"
            f"🌍 **Global Bans:**\n"
            f"• `/gban [id] [reason]`\n"
            f"• `/ungban [id]`\n"
            f"• `/bannedlist`\n\n"
            f"👤 **Players:**\n"
            f"• `/resetall confirm`\n"
            f"• `/resetplayer [user_id] confirm` — reset one full account\n"
            f"• `/refreshclaim all confirm` — let all players claim the main-group reward again\n"
            f"• `/resetbounty [user_id] confirm` or reply + `/resetbounty confirm`\n"
            f"• `/resetlv [user_id] confirm` or reply + `/resetlv confirm`\n"
            f"• `/resethaki [user_id] confirm` or reply + `/resethaki confirm`\n"
            f"• `/resetcharacter [user_id] confirm` or reply + `/resetcharacter confirm`\n"
            f"  Add `all confirm` after any category reset to apply it to everyone.\n"
            f"• `/setbounty [amt]`\n"
            f"• `/setb`, `/setf`, `/setlevel`, `/setxp`\n"
            f"• `/addbounty [id] [amt]` or reply + `[amt]`\n"
            f"• `/addxp [id] [xp]` or reply + `[xp]`\n"
            f"• `/addtoken`\n"
            f"• `/giftcard [user_id] [character_id]` or reply + `[character_id]` — gift directly from the catalog\n\n"
            f"💰 **Economy Prices:**\n"
            f"• `/prices` — show every configurable shop price and fish sale value\n"
            f"• `/setprice [key] [amount]` — change a price; supports K/M/B/T amounts\n\n"
            f"🎣 **Fishing:**\n"
            f"• Reply to a sticker with `/setfish`; `/setfailfish` sets the fish-escape sticker\n"
            f"• `/clearfailfish` clears the fail sticker; fishing gives 100 base XP and can fail\n\n"
            f"🎁 **Claim Reward Media:**\n"
            f"• Reply to a GIF with `/setclaimgif` (or pass its file ID)\n"
            f"• Reply to a sticker with `/setclaimsticker`; `/setclaimemoji [emoji]` sets the reward emoji\n"
            f"• `/claimmedia` — check; `/clearclaimgif`, `/clearclaimsticker`, `/clearclaimemoji` — clear\n\n"
            f"• `/setbonusgif`, `/setbonussticker`, `/setbonusemoji` — configure weekly bonus media\n"
            f"• `/bonusmedia` — check; `/clearbonusgif`, `/clearbonussticker`, `/clearbonusemoji` — clear\n\n"
            f"🎞 **Advanced Haki GIFs:**\n"
            f"• Reply to a GIF: `/setadvancedhakigif [observation|armament|conqueror]`\n"
            f"• `/advancedhakigifs` — check configured GIFs\n"
            f"• `/clearadvancedhakigif [type]` — clear one\n\n"
            f"☀️ **Nika Spell GIFs:**\n"
            f"• Reply to a GIF: `/setbajranggungif` or `/setkaminarigif`\n"
            f"• Or pass a Telegram file ID to either command\n"
            f"• `/nikagifs` — check configured spell GIFs\n"
            f"• `/clearnikagif [bajranggun|kaminari]` — clear one\n\n"
            f"🗡️ **Ope Awakening GIFs (awakened moves only):**\n"
            f"• Reply to a GIF: `/setopeawakeninggif [kroom|shockwille]`\n"
            f"• Or pass the move and file ID: `/setopeawakeninggif [move] [file_id]`\n"
            f"• `/opeawakeninggifs` — check; `/clearopeawakeninggif [move]` — clear one\n\n"
            f"✨ **Ito/Mochi/Jiki/Gear 4 Snakeman Activation GIFs:**\n"
            f"• Reply to a GIF with `/setitoawakeninggif`, `/setmochiawakeninggif`, `/setjikiawakeninggif`, or `/setsnakemangif`\n"
            f"• `/fruitawakeninggifs` — check; `/clearfruitawakeninggif [ito|mochi|jiki|snakeman]` — clear one\n\n"
            f"🎮 **Characters:**\n"
            f"• `/spawn [rarity]`, `/reset`, `/spawnraid` — spawn a character by rarity or a World Boss raid (owner only)\n"
            f"• `/removechar [character_id]` (reply to player), or `/removechar [user_id] [character_id] [all]` — remove from a player's collection\n"
            f"• `/raidspawn [group_id]` — spawn in a target group from private chat\n"
            f"• Owner-only `/quiz` or `/question` — manually start a random 3-choice anime/math question\n"
            f"• Owner `/quiz on|off|stop` — control continuous automatic quizzes; each quiz lasts 5 minutes (30% easy / 70% hard)\n"
            f"• `/quickquiz` or `/manualquiz` — shared repeating quiz; everyone can answer, with random bounty, 2x XP boost, or shield rewards\n"
            f"• `/quickquiz stop` — stop the repeating quickquiz in this chat\n"
            f"• `/setquizsticker` (reply to sticker), `/setquizemoji [emoji]`, `/setquizgif` (reply to GIF) — set auto-quiz drop media\n"
            f"• `/quizdropmedia` — check; `/clearquizsticker`, `/clearquizgif`, `/setquizemoji off` — clear settings\n"
            f"• `/quizrarities` — view the quiz reward rarity pool\n"
            f"• `/setquizrarities [rarities]`, `/addquizrarity [rarity]`, `/removequizrarity [rarity]` — owner quiz pool controls\n"
            f"• `/addrarity [name]` — create a new character rarity\n"
            f"• `/sent` — resend all character images to the upload channel\n"
            f"• `/<rarity>add [name]` — add a character to that custom rarity\n"
            f"• `/<rarity>delete [id]` — delete a custom-rarity character\n"
            f"• `/deleterarity [name]` — delete a custom rarity\n"
            f"• `/renamerarity [old] -> [new]` — rename a custom rarity globally\n"
            f"• `/setrarityemoji [rarity] [emoji]`\n"
            f"• `/setrarityspoiler [rarity] [on|off]`\n"
            f"• `/setraritychance [rarity] [percent]`\n"
            f"• `/setrarityreward [rarity] [min] [max]`\n"
            f"• `/setnextdrop [rarity|off]` in a group; from DM use `/setnextdrop [group_id] [rarity|off]`\n"
            f"• `/setcharwin [character_id] [percent]` — override a character's challenge win chance\n"
            f"• `/resetcd`\n"
            f"• `/pattern [1/2/3/4]`, `/pattern auto`\n"
            f"• `/currentpattern`\n\n"
            f"📊 **System:**\n"
            f"• `/check`, `/gstats`, `/checkgroup`\n"
            f"• `/stats`, `/groups`\n"
            f"• `/addgroup`, `/removegroup`, `/listgroups`\n\n"
            f"📢 **Announcements:**\n"
            f"• `/broadcast [groups|users|all]`\n"
            f"• `/forwardall`, `/forwardgroups`, `/forwardusers`\n"
            f"• `/sendupdate [msg]`\n\n"
            f"🎁 **Global Giveaway:**\n"
            f"• `/agiveaway [time] [prize] [winners] [reason]`\n"
            f"• `/charitygiveaway [rarity] [players] [duration]` — owner-only; one random character per winner\n"
            f"• `/bgiveaway [time] [total bounty] [winners] [reason]` — current group\n"
            f"• `/bgiveaway [group_id] [time] [total bounty] [winners] [reason]` — choose target from DM\n"
            f"• `/cancelagiveaway`\n\n"
            f"💾 **Backup:**\n"
            f"• `/backup`, `/sendbackup`, `/downloadjson` — includes separate bounty, progress, characters, Haki, inventory, and profile JSON files\n"
            f"• Reply to a JSON with `/restorejson`\n"
            f"• `/backups`\n"
            f"• `/restore [timestamp]`\n"
            f"• `/delbackup [timestamp]`\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )
        chunks = []
        current = ""
        for line in help_text.splitlines(keepends=True):
            if current and len(current) + len(line) > 3500:
                chunks.append(current)
                current = ""
            current += line
        if current:
            chunks.append(current)
        for chunk in chunks:
            await message.reply(chunk)


# ==================== /sendbackup (owner DM every JSON) ====================
    @app.on_message(filters.command(["sendbackup", "downloadjson"]))
    async def send_backup_cmd(client, message):
        """Owner-only: dump every data file and send each as a Telegram document."""
        if message.from_user.id != OWNER_ID:
            return
        from io import BytesIO
        from config import DATA_DIR

        status = await message.reply("📦 Packaging backups...")
        sent = 0
        total_kb = 0
        try:
            payload_files = {
                **get_player_data_snapshots(),
                "normal_chars.json": list(normal_characters),
                "mythical_chars.json": list(mythical_characters),
                "exalted_chars.json": list(exalted_characters),
                "rarities.json": {"rarities": list(custom_rarities), "quiz_rarities": list(get_quiz_rarities()), "settings": rarity_settings},
                "gbanned.json": list(GBANNED),
                "temp_banned.json": {str(k): v for k, v in TEMP_BANNED.items()},
                "admins.json": list(ADMINS),
                "bot_groups.json": list(bot_groups),
            }
            from nika_media import get_nika_move_gifs
            payload_files["nika_move_gifs.json"] = get_nika_move_gifs()
            from ope_media import get_ope_awakening_gifs
            payload_files["ope_ope_gif.json"] = get_ope_awakening_gifs()
            from fruit_awakening_media import get_fruit_awakening_gifs
            payload_files["fruit_awakening_gifs.json"] = get_fruit_awakening_gifs()
            from claim_media import get_claim_reward_media
            payload_files["claim_reward_gif.json"] = get_claim_reward_media()
            from quiz_media import get_quiz_drop_media
            payload_files["quiz_drop_media.json"] = get_quiz_drop_media()
            for extra_name in ("group_settings.json", "pattern_state.json", "price_overrides.json", "giveaway.json"):
                extra_path = os.path.join(DATA_DIR, extra_name)
                if os.path.exists(extra_path):
                    try:
                        with open(extra_path, "r", encoding="utf-8") as fh:
                            payload_files[extra_name] = json.load(fh)
                    except (OSError, ValueError) as exc:
                        print(f"[sendbackup] {extra_name}: {exc}")
            for sticker_name in ("fishing_sticker.json", "fail_fish_sticker.json"):
                sticker_path = os.path.join(DATA_DIR, sticker_name)
                if os.path.exists(sticker_path):
                    try:
                        with open(sticker_path, "r", encoding="utf-8") as fh:
                            payload_files[sticker_name] = json.load(fh)
                    except (OSError, ValueError) as exc:
                        print(f"[sendbackup] {sticker_name}: {exc}")
            try:
                from crew import CREW_STORE
                payload_files["crews.json"] = CREW_STORE
            except Exception:
                pass
            for fname, payload in payload_files.items():
                raw = json.dumps(payload, indent=2, ensure_ascii=False).encode()
                total_kb += len(raw) // 1024
                buf = BytesIO()
                buf.write(raw)
                buf.seek(0)
                buf.name = fname
                try:
                    await client.send_document(
                        message.from_user.id,
                        document=buf,
                        caption=f"💾 `{fname}` — {len(raw) // 1024} KB",
                    )
                except Exception as e:
                    print(f"[sendbackup] {fname}: {e}")
                    continue
                sent += 1
                await asyncio.sleep(0.2)
            await status.edit_text(
                f"✅ Sent **{sent}** backup files.\n💽 Total: {total_kb} KB"
            )
        except Exception as e:
            try:
                await status.edit_text(f"Failed: `{e}`")
            except Exception:
                pass


# ==================== AUTO + MANUAL SCHEDULED BACKUP HELPER ====================
async def run_scheduled_backup(client, hour_label):
    """Dumps every data file to data/backups/<ts>_*.json and DMs the owner."""
    try:
        from config import DATA_DIR, OWNER_ID
        ts = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        files = {
            **get_player_data_snapshots(),
            "normal_chars.json": list(normal_characters),
            "mythical_chars.json": list(mythical_characters),
            "exalted_chars.json": list(exalted_characters),
            "rarities.json": {"rarities": list(custom_rarities), "settings": rarity_settings},
            "gbanned.json": list(GBANNED),
            "temp_banned.json": {str(k): v for k, v in TEMP_BANNED.items()},
            "admins.json": list(ADMINS),
            "bot_groups.json": list(bot_groups),
        }
        from nika_media import get_nika_move_gifs
        files["nika_move_gifs.json"] = get_nika_move_gifs()
        from ope_media import get_ope_awakening_gifs
        files["ope_ope_gif.json"] = get_ope_awakening_gifs()
        from fruit_awakening_media import get_fruit_awakening_gifs
        files["fruit_awakening_gifs.json"] = get_fruit_awakening_gifs()
        price_path = os.path.join(DATA_DIR, "price_overrides.json")
        try:
            with open(price_path, "r", encoding="utf-8") as fh:
                files["price_overrides.json"] = json.load(fh)
        except FileNotFoundError:
            files["price_overrides.json"] = {}
        except (OSError, ValueError) as exc:
            print(f"[auto_backup] price_overrides.json: {exc}")
        sticker_path = os.path.join(DATA_DIR, "fishing_sticker.json")
        if os.path.exists(sticker_path):
            try:
                with open(sticker_path, "r", encoding="utf-8") as fh:
                    files["fishing_sticker.json"] = json.load(fh)
            except (OSError, ValueError) as exc:
                print(f"[auto_backup] fishing_sticker.json: {exc}")
        try:
            from crew import CREW_STORE  # type: ignore
            files["crews.json"] = CREW_STORE
        except Exception:
            pass

        saved = 0
        for fname, payload in files.items():
            try:
                path = os.path.join(backup_dir, f"{ts}_{fname}")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                saved += 1
            except Exception as e:
                print(f"[auto_backup] {fname}: {e}")

        try:
            await client.send_message(
                OWNER_ID,
                f"💾 **AUTO BACKUP** ({hour_label})\n\n"
                f"📁 `data/backups/{ts}_*`\n"
                f"📊 {saved} files saved\n"
                f"⏰ `{ts}`",
            )
            for fname in (*PLAYER_DATA_FILES, "normal_chars.json", "mythical_chars.json", "rarities.json", "nika_move_gifs.json", "ope_ope_gif.json", "fruit_awakening_gifs.json"):
                path = os.path.join(backup_dir, f"{ts}_{fname}")
                if os.path.exists(path):
                    try:
                        await client.send_document(
                            OWNER_ID,
                            document=path,
                            caption=f"💾 {fname}",
                        )
                    except Exception:
                        pass
        except Exception as e:
            print(f"[auto_backup] DM failed: {e}")
    except Exception as e:
        print(f"[auto_backup] error: {e}")


# ==================== BAN BROADCAST HELPER ====================
async def _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name):
    sent = 0
    failed = 0
    removed = []
    total = len(targets)

    sem = asyncio.Semaphore(8)

    async def _one(gid):
        nonlocal sent, failed
        async with sem:
            try:
                await client.send_message(gid, announcement)
                sent += 1
            except Exception as e:
                failed += 1
                err = str(e).lower()
                if any(k in err for k in (
                    "chat not found", "bot was kicked",
                    "bot is not a member", "peer id invalid",
                )):
                    removed.append(gid)
                await asyncio.sleep(0.05)

    await asyncio.gather(*(_one(gid) for gid in targets))

    for gid in removed:
        bot_groups.discard(gid)
    if removed:
        save_bot_groups()

    try:
        await status_msg.edit_text(
            f"**BROADCAST COMPLETE**\n\n"
            f"{user_name}\n"
            f"ID: `{user_id}`\n\n"
            f"Sent: **{sent}**\n"
            f"Failed: **{failed}**\n"
            f"Total: **{total}**"
        )
    except Exception as e:
        print(f"[broadcast_ban] status edit failed: {e}")


# ==================== SPAWN FUNCTION ====================
async def spawn_character(app, chat_id, chat_name, requested_rarity=None):
    import random
    from data_manager import (
        active_challenges, normal_characters, mythical_characters, exalted_characters,
        get_character_rarities, get_rarity_chance, get_rarity_emoji, get_rarity_reward_range,
        get_group_next_drop_rarity, clear_group_next_drop_rarity,
    )

    if chat_id in active_challenges:
        return

    pools = {rarity: [c for c in normal_characters + mythical_characters + exalted_characters
                      if str(c.get("rarity", "NORMAL")).upper() == rarity]
             for rarity in get_character_rarities()}
    available = [(rarity, pool) for rarity, pool in pools.items() if pool]
    if not available:
        return

    rarities, candidates = zip(*available)
    requested_rarity = " ".join(str(requested_rarity or "").strip().upper().split()) or None
    forced_rarity = get_group_next_drop_rarity(chat_id)
    if requested_rarity and requested_rarity in pools and pools[requested_rarity]:
        selected_rarity = requested_rarity
    elif forced_rarity and forced_rarity in pools and pools[forced_rarity]:
        selected_rarity = forced_rarity
        clear_group_next_drop_rarity(chat_id)
    else:
        if forced_rarity:
            clear_group_next_drop_rarity(chat_id)
        weights = [get_rarity_chance(rarity) for rarity in rarities]
        if not any(weights):
            weights = [1] * len(rarities)
        selected_rarity = random.choices(rarities, weights=weights, k=1)[0]
    char = random.choice(pools[selected_rarity])
    is_mythical = selected_rarity == "MYTHICAL"
    emoji = get_rarity_emoji(selected_rarity)
    reward_low, reward_high = get_rarity_reward_range(selected_rarity)
    reward = f"฿{reward_low:,}–฿{reward_high:,} + XP"
    if is_mythical:
        reward += " + 1 Token"
    msg = (
        f"{emoji} **A {selected_rarity.title()} Character Appeared!**\n\n"
        f"Character: ???\n"
        f"Type: {selected_rarity}\n"
        f"Reward: {reward}\n\n"
        f"Despawns in 5 min\n"
        f"Type /challenge to fight!"
    )

    active_challenges[chat_id] = {
        "char": char,
        "is_mythical": is_mythical,
        "rarity": selected_rarity,
        "challenger": None,
        "spawn_time": time.time(),
        "chat_name": chat_name,
    }

    if char.get("image"):
        spoiler_enabled = get_rarity_spoiler(selected_rarity)
        print(
            f"[spawn] rarity={selected_rarity!r} spoiler={spoiler_enabled!r} "
            f"setting={rarity_settings.get(selected_rarity, {}).get('spoiler')!r} "
            f"media_type={char.get('media_type', 'photo')!r}"
        )
        if char.get("media_type") == "video":
            try:
                await app.send_video(
                    chat_id, char["image"], caption=msg,
                    has_spoiler=spoiler_enabled,
                )
                return
            except Exception as e:
                print(f"[spawn] video send failed for {selected_rarity}: {e}")
                if spoiler_enabled:
                    await app.send_message(chat_id, msg)
                    return
        try:
            await app.send_photo(
                chat_id, char["image"], caption=msg,
                has_spoiler=spoiler_enabled,
            )
            return
        except Exception as e:
            print(f"[spawn] photo send failed for {selected_rarity}: {e}")
            if spoiler_enabled:
                await app.send_message(chat_id, msg)
                return
            try:
                await app.send_photo(chat_id, char["image"], caption=msg)
                return
            except Exception:
                pass
        try:
            await app.send_document(chat_id, char["image"], caption=msg)
            return
        except Exception:
            pass
    try:
        await app.send_message(chat_id, msg)
    except Exception as e:
        # Do not leave a challenge active if every media/text send failed;
        # players must not be able to capture a character they never saw.
        active_challenges.pop(chat_id, None)
        print(f"[spawn] couldn't post character in {chat_id}: {e}")
