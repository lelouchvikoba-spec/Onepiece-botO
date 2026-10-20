# shop.py
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, SHOP_IMAGE, VAULT_CAPS,
    FRUIT_SELL_REFUNDS, DEVIL_FRUITS, FRUIT_CATEGORIES,
    get_fruit_tier, get_fruit_icon, normalize_fruit_name,
    get_fruit_category, get_fruit_display_category,
)
from data_manager import get_player, save_data
from utils import parse_amount
from pricing import get_fruit_refund
from fruit_skills import (
    get_fruit_skill, get_pvp_fruit_skills, get_fruit_awakening_key,
    FRUIT_AWAKENED_WORLD_BOSS_SKILLS, FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS,
    get_extra_fruit_spell_map,
)


def _sans_italic(text):
    out = []
    for ch in str(text):
        code = ord(ch)
        if "A" <= ch <= "Z":
            out.append(chr(0x1D608 + code - ord("A")))
        elif "a" <= ch <= "z":
            out.append(chr(0x1D622 + code - ord("a")))
        else:
            out.append(ch)
    return "".join(out)


def _sans_regular(text):
    out = []
    for ch in str(text):
        code = ord(ch)
        if "A" <= ch <= "Z":
            out.append(chr(0x1D5A0 + code - ord("A")))
        elif "a" <= ch <= "z":
            out.append(chr(0x1D5BA + code - ord("a")))
        else:
            out.append(ch)
    return "".join(out)


def register_shop(app):

    # ==================== /shop ====================
    @app.on_message(filters.command("shop"))
    async def shop_cmd(client, message):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚔️ Haki", callback_data="shop_haki"),
                InlineKeyboardButton("🛡️ Shield", callback_data="shop_shield"),
                InlineKeyboardButton("🍎 Devil Fruit", callback_data="shop_fruit"),
            ],
            [
                InlineKeyboardButton("🏦 Vault", callback_data="shop_vault"),
                InlineKeyboardButton("⚡ 2x XP", callback_data="shop_boost"),
                InlineKeyboardButton("🔄 Switch Haki", callback_data="shop_switch_haki"),
            ],
            [InlineKeyboardButton("🎣 Fishing Rods & Bait", callback_data="shop_fishing")],
        ])
        text = f"**SHOP**\n\nSelect a category.\n\n{BOT_NAME}"

        if SHOP_IMAGE and isinstance(SHOP_IMAGE, str) and SHOP_IMAGE.strip():
            try:
                await message.reply_photo(SHOP_IMAGE, caption=text, reply_markup=kb)
                return
            except Exception as e:
                print(f"[shop] photo failed: {e}")
            try:
                await message.reply_document(SHOP_IMAGE, caption=text, reply_markup=kb)
                return
            except Exception as e:
                print(f"[shop] document failed: {e}")

        await message.reply(text, reply_markup=kb)

    # ==================== /fruits ====================
    @app.on_message(filters.command("fruits"))
    async def fruits_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not p.devil_fruit:
            await message.reply("You don't have a Devil Fruit yet.")
            return

        fruit_name = normalize_fruit_name(p.devil_fruit)
        category = "Unknown"
        for fruit_group in DEVIL_FRUITS.values():
            for fruit in fruit_group:
                if fruit.get("full") == p.devil_fruit or fruit.get("full") == fruit_name:
                    fruit_name = fruit.get("full", fruit_name)
                    category = get_fruit_display_category(fruit)
                    break

        if "nika" in fruit_name.casefold() and "hito hito" in fruit_name.casefold():
            now = time.time()
            active_until = float(getattr(p, "nika_active_until", 0) or 0)
            if active_until > now:
                skill_text = (
                    f"**Gear 5:** Active for {int(active_until - now)} seconds.\n"
                    "1. Gomu Gomu no Bajrang Gun (x150) `/bajranggun` · 2. Gomu Gomu no Kaminari (x100) `/kaminari`\n"
                    "3. `/gear5off` to return to base. Without a target, moves show an effect only.\n\n"
                )
            else:
                cooldown = max(0, int(float(getattr(p, "nika_cooldown_until", 0) or 0) - now))
                status = f"Gear 5 cooldown: {cooldown} seconds.\n" if cooldown else "Awaken with `/gear5` for 5 minutes.\n"
                skill_text = (
                    "**Nika Techniques:** 1. Gomu Gomu no Red Hawk (x30) `/redhawk` · 2. Gomu Gomu no Elephant Gatling (x50) `/elephantgatling`\n"
                    "3. `/gear5` to awaken.\n"
                    f"{status}Without a target, moves show an effect only.\n\n"
                )
        elif "ope ope no mi" in fruit_name.casefold():
            now = time.time()
            active_until = float(getattr(p, "ope_active_until", 0) or 0)
            if active_until > now:
                skill_text = (
                    f"**Ope Awakening:** Active for {int(active_until - now)} seconds.\n"
                    "1. K-Room (Tact) (x3) `/kroom` · 2. Shock Wille (x4) `/shockwille`\n"
                    "Deploy `/room` first. Use `/opeawakeoff` to end early; without a target, moves show an effect only.\n\n"
                )
            else:
                cooldown = max(0, int(float(getattr(p, "ope_cooldown_until", 0) or 0) - now))
                status = f"Awakening cooldown: {cooldown} seconds; base moves still work.\n" if cooldown else "Awakening lasts 5 minutes, then has a 5-minute cooldown.\n"
                skill_text = (
                    "**Ope Ope Techniques:** Use `/room` first; this unlocks `/shambles` and `/gammaknife` — Gamma Knife.\n"
                    "Then use `/opeawake` to switch to K-Room (Tact) and Shock Wille.\n"
                    f"{status}Without a target, moves show an effect only.\n\n"
                )
        elif get_fruit_awakening_key(fruit_name):
            now = time.time()
            state_key = get_fruit_awakening_key(fruit_name)
            active_until = float(getattr(p, f"{state_key}_active_until", 0) or 0)
            cooldown_until = float(getattr(p, f"{state_key}_cooldown_until", 0) or 0)
            titles = {
                "ito": "Ito Awakening",
                "mochi": "Mochi Awakening",
                "jiki": "Jiki Awakening",
                "gomu": "Gear 4 Snakeman",
            }
            activate = {
                "ito": "/itoawake",
                "mochi": "/mochiawake",
                "jiki": "/jikawake",
                "gomu": "/gear4 snakeman",
            }[state_key]
            deactivate = {
                "ito": "/itoawakeoff",
                "mochi": "/mochiawakeoff",
                "jiki": "/jikawakeoff",
                "gomu": "/gear4off",
            }[state_key]
            awakening_fruit = next(
                name for name in FRUIT_AWAKENED_WORLD_BOSS_SKILLS
                if get_fruit_awakening_key(name) == state_key
            )
            awakened_spells = FRUIT_AWAKENED_WORLD_BOSS_SKILLS[awakening_fruit]
            separation_note = (
                "In this bot, Gomu Gomu is separate from Hito Hito Model: Nika; Snakeman is not Gear 5.\n"
                if state_key == "gomu" else ""
            )
            if active_until > now:
                command_text = " · ".join(
                    f"`/{command}` {move['name']} (x{move['multiplier']:g})"
                    for command, move in awakened_spells.items()
                )
                skill_text = (
                    f"**{titles[state_key]}:** active for {int(active_until - now)}s.\n"
                    f"{separation_note}"
                    f"Awakened World Boss spells: {command_text}\n"
                    f"Use `{deactivate}` to end early; World Boss spells can be repeated while the boss is active.\n\n"
                )
            else:
                cooldown_text = (
                    f"Awakening cooldown: {int(cooldown_until - now)}s.\n"
                    if cooldown_until > now else
                    f"Awaken with `{activate}` for 5 minutes; cooldown is 5 minutes.\n"
                )
                spell_names = " · ".join(move["name"] for move in get_pvp_fruit_skills(fruit_name, awakened=True))
                locked_spell_text = " · ".join(
                    f"`/{command}` {move['name']} (x{move['multiplier']:g})"
                    for command, move in awakened_spells.items()
                )
                base_skill = get_fruit_skill(fruit_name)
                base_skill_text = (
                    f"Normal World Boss skill: {base_skill['name']} (x{base_skill['multiplier']:g}) via `/{''.join(ch for ch in base_skill['name'].casefold() if ch.isalnum())}`.\n"
                    if base_skill else ""
                )
                pre_snake_text = ""
                if state_key == "gomu":
                    pre_snake_spells = FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS["Gomu Gomu no Mi"]
                    pre_snake_text = "Repeatable pre-Snakeman World Boss spells: " + " · ".join(
                        f"`/{command}` {move['name']} (x{move['multiplier']:g})"
                        for command, move in pre_snake_spells.items()
                    ) + ".\n"
                skill_text = (
                    f"**{titles[state_key]}:** {cooldown_text}"
                    f"{separation_note}"
                    f"{base_skill_text}"
                    f"{pre_snake_text}"
                    f"Awakened PvP moves: {spell_names}.\n"
                    f"Awakened World Boss spells (unlock after `{activate}`): {locked_spell_text}.\n\n"
                )
        else:
            skill = get_fruit_skill(fruit_name)
            skill_text = (
                f"**World Boss Skill:** {skill['name']} (x{skill['multiplier']:g} damage)\n"
                    f"Use `/{''.join(ch for ch in skill['name'].casefold() if ch.isalnum())}` directly; with no target it shows an effect only.\n"
                if skill else ""
            )
        extra_spells = [
            (command, item["skill"])
            for command, item in get_extra_fruit_spell_map().items()
            if " ".join(item["fruit"].split()).casefold()
            == " ".join(fruit_name.split()).casefold()
        ]
        if extra_spells:
            skill_text += "**More standalone spells:** " + " · ".join(
                f"`/{command}` {move['name']}"
                for command, move in extra_spells
            ) + ".\n\n"
        awakening_key = get_fruit_awakening_key(fruit_name)
        if "nika" in fruit_name.casefold() and "hito hito" in fruit_name.casefold():
            awakened = float(getattr(p, "nika_active_until", 0) or 0) > time.time()
        elif "ope ope no mi" in fruit_name.casefold():
            awakened = float(getattr(p, "ope_active_until", 0) or 0) > time.time()
        else:
            awakened = bool(
                awakening_key
                and float(getattr(p, f"{awakening_key}_active_until", 0) or 0) > time.time()
            )
        pvp_skills = get_pvp_fruit_skills(fruit_name, awakened=awakened)
        if pvp_skills:
            choices = " · ".join(
                f"{index}. {move['name']} (x{move['multiplier']:g})"
                for index, move in enumerate(pvp_skills, start=1)
            )
            skill_text += f"**PvP Fruit moves:** {choices}\n\n"
        skill_text += "⚔️ After an accepted `/attack`, choose one move from your buttons; Fruit moves are optional, not automatic.\n\n"
        await message.reply(
            f"**Your Fruit:** {_sans_italic(fruit_name)}.\n"
            f"**Category:** {_sans_regular(category)}.\n\n"
            f"{skill_text}"
            f"You can return this Devil Fruit!\n"
            f"**NOTE:** Your current sell refund will be shown when you choose Sell Fruit.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Sell Fruit", callback_data="fruits_sell")]
            ]),
        )

    # ==================== /sell_fruit ====================
    @app.on_message(filters.command("sell_fruit"))
    async def sell_fruit_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not p.devil_fruit:
            await message.reply("You don't have a devil fruit!")
            return

        normalized = normalize_fruit_name(p.devil_fruit)
        tier = get_fruit_tier(normalized) or p.fruit_category or "Bad"
        refund = get_fruit_refund(tier)

        fruit_name = normalized
        icon = get_fruit_icon(fruit_name)

        await message.reply(
            f"**SELL DEVIL FRUIT**\n\n"
            f"{icon} **Fruit:** {fruit_name}\n"
            f"Refund: ฿{refund:,}\n\n"
            f"This will permanently remove your fruit. Confirm?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm Sell", callback_data="confirm_sell_fruit")],
                [InlineKeyboardButton("Cancel", callback_data="noop")],
            ]),
        )

    # ==================== /fruitlist ====================
    @app.on_message(filters.command("fruitlist"))
    async def fruit_list_cmd(client, message):
        text = "**ALL DEVIL FRUITS BY CANONICAL TYPE**\n"
        text += "────────────────────────────────\n\n"
        fruits_by_type = {}
        for fruit_group in DEVIL_FRUITS.values():
            for fruit in fruit_group:
                category = get_fruit_category(fruit)
                fruits_by_type.setdefault(category, []).append(fruit)
        for category in FRUIT_CATEGORIES:
            if category not in fruits_by_type:
                continue
            fruits = sorted(fruits_by_type[category], key=lambda f: f["full"].casefold())
            text += f"**{category}** ({len(fruits)}):\n"
            for fruit in fruits:
                icon = get_fruit_icon(fruit["full"])
                text += f"  {icon} {fruit['full']} — {get_fruit_display_category(fruit)}\n"
            text += "\n"

        text += f"{BOT_NAME}"

        def _split(t, limit=4000):
            lines = t.split("\n")
            out, buf = [], ""
            for line in lines:
                if len(buf) + len(line) + 1 > limit:
                    out.append(buf)
                    buf = line
                else:
                    buf = f"{buf}\n{line}" if buf else line
            if buf:
                out.append(buf)
            return out

        for chunk in _split(text):
            await message.reply(chunk)

    # ==================== /deposit ====================
    @app.on_message(filters.command("deposit"))
    async def deposit_cmd(client, message):
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/deposit [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("**That amount is invalid.** Needs to be positive.")
            return

        p = get_player(message.from_user.id, user=message.from_user)
        cap = VAULT_CAPS.get(p.vault_level, 25_000_000)
        if amount > p.bounty:
            await message.reply(f"⚠️ Not enough! You have ฿{p.bounty:,}")
            return
        if p.vault + amount > cap:
            await message.reply(f"Vault full! Capacity: ฿{cap:,}")
            return

        p.bounty -= amount
        p.vault += amount
        save_data()
        await message.reply(
            f"Deposited ฿{amount:,}!\n"
            f"Vault: ฿{p.vault:,}\n"
            f"Bounty: ฿{p.bounty:,}"
        )

    # ==================== /dig ====================
    @app.on_message(filters.command("dig"))
    async def dig_cmd(client, message):
        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/dig [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("**That amount is invalid.** Needs to be positive.")
            return

        p = get_player(message.from_user.id, user=message.from_user)
        if amount > p.vault:
            await message.reply(f"⚠️ Not enough! Vault: ฿{p.vault:,}")
            return

        p.vault -= amount
        p.bounty += amount
        save_data()
        await message.reply(
            f"Withdrew ฿{amount:,}!\n"
            f"Vault: ฿{p.vault:,}\n"
            f"Bounty: ฿{p.bounty:,}"
        )
