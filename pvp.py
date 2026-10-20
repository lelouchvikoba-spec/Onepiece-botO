# pvp.py
import asyncio
import random
import time
import uuid
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, OWNER_ID, MAIN_GROUP_ID, WORLD_BOSSES, WORLD_BOSS_HP,
    UPDATE_CHANNEL_USERNAME, UPDATE_CHANNEL_ID,
    WIN_GIF, WIN_IMAGE, LOSE_GIF, LOSE_IMAGE,
    LEVEL_UP_IMAGE, LEVEL_UP_GIF, LEVEL_UP_GROUP_IMAGE, LEVEL_UP_GROUP_GIF,
    LEVEL_DOWN_IMAGE, LEVEL_DOWN_GIF, LEVEL_DOWN_GROUP_IMAGE, LEVEL_DOWN_GROUP_GIF,
    PVP_VICTORY_GIF, PVP_VICTORY_IMAGE, PVP_DEFEAT_GIF, PVP_DEFEAT_IMAGE,
    SHIELD_NAMES, ROB_COOLDOWN, NIKA_GIF,
)
from data_manager import (
    get_player, save_data, user_data, active_challenges, ADMINS,
    add_trade, get_trade, remove_trade, pending_trades, get_character_by_id,
    get_rarity_emoji, get_rarity_reward_range,
    set_world_boss_active, get_world_boss_active,
    set_world_boss_hp, get_world_boss_hp,
    add_world_boss_damage, get_world_boss_damage, clear_world_boss_damage,
    reset_world_boss_raid_state, register_world_boss_participant,
    eliminate_random_world_boss_participant,
)
from utils import (
    check_cooldown, parse_amount, get_xp_needed, get_rank,
    can_rob_by_level, can_penetrate_shield, calc_rob_percent,
    get_conq_level, get_rob_level_range, can_bypass_pvp_off,
    can_bypass_level_restriction,
    get_armament_multiplier, get_armament_shield_ignore,
    get_conq_autowin_chance, get_haki_level, get_observation_win_rate, build_mention,
)
from fruit_skills import (
    FRUIT_SKILLS, get_fruit_skill, get_pvp_fruit_skills, get_fruit_awakening_key,
    get_awakened_world_boss_skill, FRUIT_AWAKENED_WORLD_BOSS_SKILLS,
    get_pre_awakened_world_boss_skill, FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS,
    get_extra_fruit_spell_map,
)
from nika_media import get_nika_move_gif
from ope_media import get_ope_awakening_gif

PVP_CHALLENGE_TTL = 120
PVP_MOVE_TTL = 120
PVP_DUEL_ROUNDS = 3
PVP_DUEL_STARTING_HP = 100
pending_pvp_challenges = {}


# ==================== LEVEL UP / DOWN NOTIFICATIONS ====================
async def send_level_up_notification(app, user_id, old_level, new_level, source="game"):
    try:
        if new_level >= 200:
            medal, title = "👑🔥", "PIRATE KING!"
        elif new_level >= 180:
            medal, title = "🌊", "ADMIRAL!"
        elif new_level >= 150:
            medal, title = "👑", "YONKO COMMANDER!"
        elif new_level >= 125:
            medal, title = "⚔️", "WARLORD!"
        elif new_level >= 100:
            medal, title = "💥", "SUPERNOVA!"
        elif new_level >= 80:
            medal, title = "🗺️", "GRAND LINE TRAVELER!"
        elif new_level >= 60:
            medal, title = "🎯", "BOUNTY HUNTER!"
        elif new_level >= 40:
            medal, title = "⚓", "PIRATE APPRENTICE!"
        elif new_level >= 25:
            medal, title = "🧹", "CABIN BOY!"
        else:
            medal, title = "🏴‍☠️", "ROOKIE!"

        rank = get_rank(new_level)

        source_map = {
            "pvp_win": "PVP VICTORY",
            "pvp_loss": "PVP REVENGE",
            "game": "GAME WIN",
            "daily": "DAILY REWARD",
            "weekly": "WEEKLY REWARD",
            "claim": "CLAIM REWARD",
            "challenge": "CHARACTER DEFEATED",
            "world_boss": "WORLD BOSS",
        }
        source_label = source_map.get(source, "LEVEL UP")

        player = get_player(user_id)
        player_name = player.name or f"User {user_id}"

        caption = (
            f"{medal} **LEVEL UP!** {medal}\n\n"
            f"**{old_level}** ➜ **{new_level}**\n"
            f"Rank: {rank}\n"
            f"Title: {title}\n\n"
            f"Keep going, {player_name}!\n\n"
            f"{BOT_NAME}"
        )

        # Try static image first
        if LEVEL_UP_IMAGE:
            try:
                await app.send_photo(user_id, LEVEL_UP_IMAGE, caption=caption)
                return
            except Exception as e:
                print(f"[level up image] {e}")

        if LEVEL_UP_GIF:
            try:
                await app.send_animation(user_id, LEVEL_UP_GIF, caption=caption)
                return
            except Exception as e:
                print(f"[level up gif] {e}")

        await app.send_message(user_id, caption)
    except Exception as e:
        print(f"[level up DM] {e}")


async def send_level_up_group_notification(app, chat_id, user_name, old_level, new_level):
    try:
        caption = (
            f"🎉 **{user_name}** reached **Lv.{new_level}**! 🎉\n\n"
            f"{old_level} ➜ {new_level}"
        )

        if LEVEL_UP_GROUP_IMAGE:
            try:
                await app.send_photo(chat_id, LEVEL_UP_GROUP_IMAGE, caption=caption)
                return
            except Exception:
                pass

        if LEVEL_UP_GROUP_GIF:
            try:
                await app.send_animation(chat_id, LEVEL_UP_GROUP_GIF, caption=caption)
                return
            except Exception:
                pass
    except Exception:
        pass


async def send_level_down_notification(app, user_id, old_level, new_level, source="pvp_loss"):
    try:
        if new_level >= 180:
            medal = "🌊"
        elif new_level >= 150:
            medal = "👑"
        elif new_level >= 125:
            medal = "⚔️"
        elif new_level >= 100:
            medal = "💥"
        elif new_level >= 80:
            medal = "🗺️"
        elif new_level >= 60:
            medal = "🎯"
        elif new_level >= 40:
            medal = "⚓"
        elif new_level >= 25:
            medal = "🧹"
        else:
            medal = "🏴‍☠️"

        rank = get_rank(new_level)
        source_map = {
            "pvp_loss": "PVP DEFEAT",
            "game": "GAME LOSS",
            "challenge": "CHARACTER DEFEATED YOU",
        }
        source_label = source_map.get(source, "LEVEL DOWN")

        player = get_player(user_id)
        player_name = player.name or f"User {user_id}"

        caption = (
            f"💀 **LEVEL DOWN!** 💀\n\n"
            f"**{old_level}** ➜ **{new_level}**\n"
            f"Rank: {rank}\n\n"
            f"Train harder, {player_name}!\n\n"
            f"{BOT_NAME}"
        )

        if LEVEL_DOWN_IMAGE:
            try:
                await app.send_photo(user_id, LEVEL_DOWN_IMAGE, caption=caption)
                return
            except Exception:
                pass

        if LEVEL_DOWN_GIF:
            try:
                await app.send_animation(user_id, LEVEL_DOWN_GIF, caption=caption)
                return
            except Exception:
                pass

        await app.send_message(user_id, caption)
    except Exception as e:
        print(f"[level down DM] {e}")


async def send_level_down_group_notification(app, chat_id, user_name, old_level, new_level):
    try:
        caption = (
            f"💀 **{user_name}** dropped to **Lv.{new_level}**! 💀\n\n"
            f"{old_level} ➜ {new_level}"
        )

        if LEVEL_DOWN_GROUP_IMAGE:
            try:
                await app.send_photo(chat_id, LEVEL_DOWN_GROUP_IMAGE, caption=caption)
                return
            except Exception:
                pass

        if LEVEL_DOWN_GROUP_GIF:
            try:
                await app.send_animation(chat_id, LEVEL_DOWN_GROUP_GIF, caption=caption)
                return
            except Exception:
                pass
    except Exception:
        pass


# ==================== WORLD BOSS ====================
current_world_boss = None
current_world_boss_chat_id = None
world_boss_elimination_task = None
world_boss_despawn_task = None
world_boss_ope_room_users = set()
WORLD_BOSS_DURATION = 30 * 60
NIKA_FRUIT_NAME = "Hito Hito no Mi, Model: Nika"
GEAR5_DURATION = 5 * 60
GEAR5_COOLDOWN = 5 * 60
OPE_AWAKENING_DURATION = 5 * 60
OPE_AWAKENING_COOLDOWN = 5 * 60
FRUIT_AWAKENING_DURATION = 5 * 60
FRUIT_AWAKENING_COOLDOWN = 5 * 60
FRUIT_AWAKENING_FRUITS = {
    "ito": "Ito Ito no Mi",
    "mochi": "Mochi Mochi no Mi",
    "jiki": "Jiki Jiki no Mi",
    "gomu": "Gomu Gomu no Mi",
}
FRUIT_AWAKENING_TITLES = {
    "ito": "Ito Awakening",
    "mochi": "Mochi Awakening",
    "jiki": "Jiki Awakening",
    "gomu": "Gear 4 Snakeman",
}
FRUIT_AWAKENING_COMMANDS = {
    "itoawake": "ito",
    "mochiawake": "mochi",
    "jikawake": "jiki",
    "gear4": "gomu",
    "snakeman": "gomu",
}
FRUIT_AWAKENING_OFF_COMMANDS = {
    "itoawakeoff": "ito",
    "mochiawakeoff": "mochi",
    "jikawakeoff": "jiki",
    "gear4off": "gomu",
    "snakemanoff": "gomu",
}
AWAKENED_SPELL_COMMANDS = {
    move_key: get_fruit_awakening_key(fruit_name)
    for fruit_name, moves in FRUIT_AWAKENED_WORLD_BOSS_SKILLS.items()
    for move_key in moves
}
GOMU_PRE_AWAKENED_SPELL_COMMANDS = {
    move_key: "gomu"
    for fruit_name, moves in FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS.items()
    for move_key in moves
}
NIKA_MOVES = {
    "redhawk": ("Gomu Gomu no Red Hawk", 30.0),
    "elephantgatling": ("Gomu Gomu no Elephant Gatling", 50.0),
    "bajranggun": ("Gomu Gomu no Bajrang Gun", 150.0),
    "kaminari": ("Gomu Gomu no Kaminari", 100.0),
}
OPE_MOVES = {
    "shambles": ("Shambles", 1.5),
    "gammaknife": ("Gamma Knife", 2.15),
    "kroomtact": ("K-Room (Tact)", 3.0),
    "shockwille": ("Shock Wille", 4.0),
}
FRUIT_BASE_SPELL_COMMANDS = {
    "".join(ch for ch in skill["name"].casefold() if ch.isalnum()): fruit_name
    for fruit_name, skill in FRUIT_SKILLS.items()
    if "nika" not in fruit_name.casefold() and "ope ope no mi" not in fruit_name.casefold()
}
FRUIT_EXTRA_SPELL_COMMANDS = get_extra_fruit_spell_map()


def _is_nika_fruit(fruit_name):
    name = str(fruit_name or "").casefold()
    return "nika" in name and "hito hito" in name


def _is_ope_ope_fruit(fruit_name):
    return "ope ope no mi" in str(fruit_name or "").casefold()


async def _check_world_boss_raid_player(message):
    allowed, eliminated_user_id = register_world_boss_participant(message.from_user.id)
    if not allowed:
        await message.reply(
            "☠️ You were eliminated from this World Boss raid and cannot attack again."
        )
        return False
    return True


async def _can_challenge_character(client, message):
    """Require membership in both communities before a character challenge."""
    uid = message.from_user.id
    if uid == OWNER_ID or uid in ADMINS:
        return True

    required = [MAIN_GROUP_ID, UPDATE_CHANNEL_USERNAME or UPDATE_CHANNEL_ID]
    for chat_id in required:
        if not chat_id:
            return False
        try:
            member = await client.get_chat_member(chat_id, uid)
            status = str(member.status).split(".")[-1].upper()
            if status not in {"MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"}:
                return False
        except Exception as exc:
            print(f"[character challenge membership] {chat_id}: {exc}")
            return False
    return True


async def _world_boss_elimination_loop(app, main_group_id):
    """Every five active minutes, eliminate one random raid participant."""
    try:
        while get_world_boss_active():
            await asyncio.sleep(5 * 60)
            if not get_world_boss_active():
                break
            eliminated_user_id = eliminate_random_world_boss_participant()
            if eliminated_user_id is not None:
                await app.send_message(
                    main_group_id,
                    "☠️ **WORLD BOSS RAID ELIMINATION**\n\n"
                    "The unluckiest participant was randomly eliminated:\n"
                    f"`{eliminated_user_id}`\n\n"
                    "They can no longer attack this World Boss."
                )
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(f"[world boss elimination] {exc}")


async def _world_boss_despawn_loop(app, main_group_id):
    """End any raid that has remained active for the full raid duration."""
    try:
        await asyncio.sleep(WORLD_BOSS_DURATION)
        if get_world_boss_active():
            await end_world_boss(app, main_group_id)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(f"[world boss despawn] {exc}")


async def start_world_boss(app, main_group_id):
    global current_world_boss, current_world_boss_chat_id
    global world_boss_elimination_task, world_boss_despawn_task
    if get_world_boss_active():
        return False
    current_world_boss = random.choice(WORLD_BOSSES)
    current_world_boss_chat_id = main_group_id
    world_boss_ope_room_users.clear()
    boss_name = current_world_boss["name"]
    set_world_boss_active(True)
    set_world_boss_hp(WORLD_BOSS_HP)
    clear_world_boss_damage()
    reset_world_boss_raid_state()
    world_boss_elimination_task = asyncio.create_task(
        _world_boss_elimination_loop(app, main_group_id)
    )
    world_boss_despawn_task = asyncio.create_task(
        _world_boss_despawn_loop(app, main_group_id)
    )

    msg = (
        "🌑 WORLD BOSS APPEARED! 🌑\n\n"
        f"👑 {boss_name} HAS AWAKENED! 👑\n\n"
        f"💀 HP: {WORLD_BOSS_HP:,}\n"
        "🏆 If defeated: Top 3 damage dealers get +1 Advanced Coin each\n"
        "⏳ Raid despawns after 30 minutes if not defeated.\n"
        "You can attack the Boss using /battle to attack the Boss and you can also use fruit skills.\n"
        "To check Fruit skills - /fruits"
    )
    boss_image = current_world_boss.get("image", "")
    if boss_image:
        try:
            await app.send_photo(main_group_id, boss_image, caption=msg)
            return True
        except Exception:
            pass
    try:
        await app.send_message(main_group_id, msg)
        return True
    except Exception:
        set_world_boss_active(False)
        if world_boss_elimination_task:
            world_boss_elimination_task.cancel()
            world_boss_elimination_task = None
        if world_boss_despawn_task:
            world_boss_despawn_task.cancel()
            world_boss_despawn_task = None
        current_world_boss = None
        current_world_boss_chat_id = None
        world_boss_ope_room_users.clear()
        raise


async def end_world_boss(app, main_group_id):
    global current_world_boss, current_world_boss_chat_id
    global world_boss_elimination_task, world_boss_despawn_task
    if not get_world_boss_active():
        return
    set_world_boss_active(False)
    if world_boss_elimination_task:
        world_boss_elimination_task.cancel()
        world_boss_elimination_task = None
    current_task = asyncio.current_task()
    if world_boss_despawn_task and world_boss_despawn_task is not current_task:
        world_boss_despawn_task.cancel()
    world_boss_despawn_task = None
    main_group_id = current_world_boss_chat_id or main_group_id

    boss_name = current_world_boss.get("name", "World Boss") if current_world_boss else "World Boss"
    hp = get_world_boss_hp()
    damage = get_world_boss_damage()

    if hp <= 0:
        top = sorted(damage.items(), key=lambda x: x[1], reverse=True)[:3]
        text = f"🎉 **{boss_name.upper()} DEFEATED!** 🎉\n\n**Top Damage Dealers:**\n"
        for i, (uid, dmg) in enumerate(top, 1):
            p = get_player(uid)
            p.advanced_token += 1
            text += f"{i}. `{uid}` — {dmg:,} damage +1 Advanced Coin\n"
        save_data()
        await app.send_message(main_group_id, text)
    else:
        await app.send_message(main_group_id, f"🌑 **{boss_name} escaped!** No defeat rewards this raid.")
    current_world_boss = None
    current_world_boss_chat_id = None
    world_boss_ope_room_users.clear()


# ==================== DM HELPERS ====================
async def _send_dm_with_gif(app, user_id, text, kind):
    if kind == "win":
        gif = PVP_VICTORY_GIF
        img = PVP_VICTORY_IMAGE
    else:
        gif = PVP_DEFEAT_GIF
        img = PVP_DEFEAT_IMAGE

    if gif:
        try:
            await app.send_animation(user_id, gif, caption=text)
            return True
        except Exception:
            pass
    if img:
        try:
            await app.send_photo(user_id, img, caption=text)
            return True
        except Exception:
            pass
    try:
        await app.send_message(user_id, text)
        return True
    except Exception:
        return False


async def send_pvp_victory_dm(app, user_id, attacker_name, target_name, steal_amount,
                              new_bounty, old_level, new_level, target_id=None,
                              target_username=None):
    try:
        target_mention = (
            build_mention(target_id, target_name, target_username)
            if target_id else target_name
        )
        text = (
            f"⚔️ **VICTORY!** ⚔️\n\n"
            f"You defeated {target_mention}! 💥\n\n"
            f"Stolen: ฿{steal_amount:,}\n"
            f"Your Bounty: ฿{new_bounty:,}\n\n"
            f"Keep going!\n\n"
            f"{BOT_NAME}"
        )
        await _send_dm_with_gif(app, user_id, text, "win")
    except Exception as e:
        print(f"[pvp victory DM] {e}")


async def send_pvp_defeat_dm(app, user_id, attacker_name, target_name, lost_amount,
                             new_bounty, old_level, new_level, attacker_id=None,
                             attacker_username=None):
    try:
        attacker_mention = (
            build_mention(attacker_id, attacker_name, attacker_username)
            if attacker_id else attacker_name
        )
        text = (
            f"💀 **DEFEAT!** 💀\n\n"
            f"You were defeated by {attacker_mention}! 💀\n\n"
            f"Lost: ฿{lost_amount:,}\n"
            f"Your Bounty: ฿{new_bounty:,}\n\n"
            f"Train harder!\n\n"
            f"{BOT_NAME}"
        )
        await _send_dm_with_gif(app, user_id, text, "lose")
    except Exception as e:
        print(f"[pvp defeat DM] {e}")


async def send_rob_attacker_dm(app, user_id, victim_id, victim_name, victim_username,
                               steal_amount, new_bounty, was_full_steal=True):
    try:
        victim_mention = build_mention(victim_id, victim_name, victim_username)
        text = (
            f"💰 **ROBBERY SUCCESSFUL!** 💰\n\n"
            f"You robbed {victim_mention}! 🏴‍☠️\n\n"
            f"Stolen: ฿{steal_amount:,}\n"
            f"Your Bounty: ฿{new_bounty:,}\n"
        )
        if not was_full_steal:
            text += f"\n*Their shield absorbed some of the blow.*"
        text += f"\n\nKeep going!\n\n{BOT_NAME}"
        await _send_dm_with_gif(app, user_id, text, "win")
    except Exception as e:
        print(f"[rob attacker DM] {e}")


async def send_rob_failed_dm(app, user_id, victim_id, victim_name, victim_username,
                             lost_amount, new_bounty):
    try:
        victim_mention = build_mention(victim_id, victim_name, victim_username)
        text = (
            f"💀 **ROBBERY FAILED!** 💀\n\n"
            f"{victim_mention} defended themselves! 🛡️\n\n"
            f"Lost: ฿{lost_amount:,}\n"
            f"Your Bounty: ฿{new_bounty:,}\n\n"
            f"Regroup and try again!\n\n"
            f"{BOT_NAME}"
        )
        await _send_dm_with_gif(app, user_id, text, "lose")
    except Exception as e:
        print(f"[rob failed DM] {e}")


async def send_rob_victim_dm(app, user_id, attacker_id, attacker_name, attacker_username,
                             steal_amount, new_bounty, pvp_was_off=False, conq_level=0):
    try:
        attacker_mention = build_mention(attacker_id, attacker_name, attacker_username)
        text = (
            f"💸 **YOU WERE ROBBED!** 💸\n\n"
            f"🏴‍☠️ {attacker_mention} **stole ฿{steal_amount:,}** from you!\n\n"
            f"Lost: ฿{steal_amount:,}\n"
            f"New Bounty: ฿{new_bounty:,}\n"
        )
        if pvp_was_off and conq_level >= 2:
            text += (
                f"\n👑 Their **Conqueror's Haki Lv.{conq_level}** "
                f"bypassed your PVP-OFF protection!"
            )
        text += f"\n\nRebuild and get revenge!\n\n{BOT_NAME}"
        await _send_dm_with_gif(app, user_id, text, "lose")
    except Exception as e:
        print(f"[rob victim DM] {e}")


async def send_defended_dm(app, user_id, attacker_id, attacker_name, attacker_username,
                           amount_won, new_bounty):
    try:
        attacker_mention = build_mention(attacker_id, attacker_name, attacker_username)
        text = (
            f"🛡️ **YOU DEFENDED YOURSELF!** 🛡️\n\n"
            f"{attacker_mention} tried to rob you — and failed!\n\n"
            f"Won: ฿{amount_won:,}\n"
            f"New Bounty: ฿{new_bounty:,}\n\n"
            f"Well defended!\n\n"
            f"{BOT_NAME}"
        )
        await _send_dm_with_gif(app, user_id, text, "win")
    except Exception as e:
        print(f"[defended DM] {e}")


# ==================== SHARED EXECUTOR ====================
async def _execute_pvp(client, message, *, is_rob: bool):
    uid = message.from_user.id
    cmd_label = "rob" if is_rob else "attack"

    if is_rob:
        attacker_pre = get_player(uid, user=message.from_user)
        now = time.time()
        if now - (attacker_pre.rob_cd or 0) < ROB_COOLDOWN:
            remaining = ROB_COOLDOWN - (now - attacker_pre.rob_cd)
            await message.reply(
                f"⏰ **Rob cooldown!**\n\n"
                f"Wait **{int(remaining // 60)}m {int(remaining % 60)}s**."
            )
            return
    else:
        can, rem = check_cooldown(uid, 25)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

    if not message.reply_to_message:
        await message.reply(f"⚠️ Reply to someone to `/{cmd_label}`!")
        return

    attacker = get_player(uid, user=message.from_user)
    target = get_player(
        message.reply_to_message.from_user.id,
        user=message.reply_to_message.from_user,
    )

    if int(attacker.user_id) == int(target.user_id):
        await message.reply("Can't target yourself!")
        return

    if not attacker.pvp_enabled:
        await message.reply("**Your PVP is OFF!** Enable with `/pvp`.")
        return

    pvp_bypass = False
    if not target.pvp_enabled:
        if is_rob and can_bypass_pvp_off(attacker):
            pvp_bypass = True
        else:
            hint = (
                "Conqueror's Haki Lv.2+ can bypass this."
                if is_rob else "Use `/rob` with Conq Lv.2+ to bypass."
            )
            await message.reply(
                f"**{target.name or 'They'}** has PVP OFF.\n\n{hint}"
            )
            return

    if is_rob:
        if not can_rob_by_level(attacker.level, target.level):
            if not can_bypass_level_restriction(attacker):
                max_diff = get_rob_level_range(attacker.level)
                await message.reply(
                    f"**Level restriction!**\n\n"
                    f"You: Lv.{attacker.level}\n"
                    f"Target: Lv.{target.level}\n"
                    f"Allowed: ±{max_diff} levels "
                    f"(Lv.{max(1, attacker.level - max_diff)}–{attacker.level + max_diff})"
                )
                return

    was_full_steal = True
    if is_rob:
        shield_ok, shield_reason, was_full_steal = can_penetrate_shield(attacker, target)
        if not shield_ok:
            target_shield = target.shield_level or 0
            attacker_conq = get_conq_level(attacker)
            await message.reply(
                f"🛡️ **Shield Blocked!**\n\n"
                f"{target.name or 'Target'} has **Shield Lv.{target_shield}** "
                f"({SHIELD_NAMES.get(target_shield, 'Unknown')})\n"
                f"Your Conq Haki: **Lv.{attacker_conq}**\n\n"
                f"{shield_reason}\n\n"
                f"Conq Lv.3 or Armament Lv.3 can smash any shield."
            )
            return

    a_name = attacker.name or f"User_{attacker.user_id}"
    t_name = target.name or f"User_{target.user_id}"
    a_mention = build_mention(attacker.user_id, a_name, attacker.username)
    t_mention = build_mention(target.user_id, t_name, target.username)

    label = "ROBBERY" if is_rob else "BATTLE"
    emoji = "💰" if is_rob else "⚔️"

    fight_msg = await message.reply(
        f"{emoji} **{label} STARTED!** {emoji}\n\n"
        f"{a_mention} vs {t_mention}\n\n"
        f"Calculating...",
        disable_web_page_preview=True,
    )
    await asyncio.sleep(0.5)

    ap = attacker.level
    tp = target.level
    ap = int(ap * get_armament_multiplier(attacker))
    tp = int(tp * get_armament_multiplier(target))

    # Crew bonus
    try:
        from crew import get_player_crew, crew_level, crew_ship_bonus
        atk_crew = get_player_crew(attacker.user_id)
        if atk_crew:
            bonus = crew_level(atk_crew) * 0.05
            bonus += crew_ship_bonus(atk_crew, "pvp_damage_bonus")
            ap = int(ap * (1 + bonus))
    except Exception:
        pass

    # Conq auto-win
    conq_chance = get_conq_autowin_chance(attacker)
    conq_note = ""
    if conq_chance > 0 and random.random() < conq_chance:
        is_victory = True
        conq_note = (
            f"\n\n👑 **{a_name}'s Conqueror's Haki "
            f"Lv.{attacker.haki_level} flared!** 👑"
        )
    else:
        is_victory = ap > tp

    pvp_bypass_note = ""
    if pvp_bypass:
        pvp_bypass_note = (
            f"\n\n👑 **Conq Lv.{get_conq_level(attacker)}** "
            f"overwhelmed {t_name}'s PVP-OFF protection!"
        )

    a_old = attacker.level
    t_old = target.level

    # ============ WIN ============
    if is_victory:
        if is_rob:
            pct = calc_rob_percent(attacker, target)
            if not was_full_steal:
                pct = 0.02
        else:
            pct = 0.10

        shield_msg = ""
        if target.passive_enabled and target.shield_level > 0 and target.shield_uses > 0:
            target.shield_uses -= 1
            shield_ignore = get_armament_shield_ignore(attacker)
            if shield_ignore >= 0.5:
                pct = 0.10
                shield_msg = f"\n\n💥 **{a_name}'s Armament Lv.3 SHATTERED the shield!**"
            else:
                pct = max(0.02, pct - 0.05)
                shield_msg = f"\n\n🛡️ **{t_name}'s SHIELD absorbed part of the blow!**"
                if target.shield_uses == 0:
                    target.shield_level = 0
                    shield_msg += f"\n💔 **Shield broke!**"

        steal = int(target.bounty * pct) if target.bounty > 0 else 0
        if steal > target.bounty:
            steal = target.bounty

        attacker.bounty += steal
        target.bounty -= steal

        xp_gain = max(0, min(50, steal // (200_000 if is_rob else 100_000))) if steal > 0 else 0
        if attacker.boost_end > time.time() and xp_gain > 0:
            xp_gain = min(75, int(xp_gain * 1.5))
        attacker.xp += xp_gain
        while attacker.xp >= get_xp_needed(attacker.level) and attacker.level < 200:
            attacker.xp -= get_xp_needed(attacker.level)
            attacker.level += 1
        if attacker.level >= 200:
            attacker.xp = 0

        xp_loss = max(0, min(50, steal // 200_000)) if steal > 0 else 0
        target.xp -= xp_loss
        while target.xp < 0 and target.level > 1:
            target.level -= 1
            target.xp += get_xp_needed(target.level)
        if target.xp < 0:
            target.xp = 0
            target.level = 1

        if is_rob:
            attacker.rob_cd = time.time()

        save_data()

        a_lt = f"\n\nLEVEL UP! {a_old} → {attacker.level}" if attacker.level > a_old else ""
        t_lt = f"\n\n{t_name} LEVEL DOWN! {t_old} → {target.level}" if target.level < t_old else ""

        result = (
            f"🎉 **{'ROBBERY SUCCESSFUL' if is_rob else 'VICTORY'}!** "
            f"{'💰' if is_rob else '⚔️'}"
            f"{conq_note}{pvp_bypass_note}{shield_msg}\n\n"
            f"{a_mention} defeated {t_mention}!\n\n"
            f"Stolen: ฿{steal:,}\n"
            f"XP: +{xp_gain}\n"
            f"Your bounty: ฿{attacker.bounty:,}"
            f"{a_lt}{t_lt}"
        )

        await fight_msg.delete()
        sent = False
        if WIN_GIF:
            try:
                await message.reply_animation(WIN_GIF, caption=result)
                sent = True
            except Exception:
                pass
        if not sent and WIN_IMAGE:
            try:
                await message.reply_photo(WIN_IMAGE, caption=result)
                sent = True
            except Exception:
                pass
        if not sent:
            await message.reply(result)

        # DMs
        if is_rob:
            asyncio.create_task(send_rob_attacker_dm(
                client, attacker.user_id, target.user_id, t_name, target.username,
                steal, attacker.bounty, was_full_steal,
            ))
            asyncio.create_task(send_rob_victim_dm(
                client, target.user_id, attacker.user_id, a_name, attacker.username,
                steal, target.bounty, pvp_bypass, get_conq_level(attacker),
            ))
        else:
            asyncio.create_task(send_pvp_victory_dm(
                client, attacker.user_id, a_name, t_name, steal,
                attacker.bounty, a_old, attacker.level,
                target_id=target.user_id, target_username=target.username,
            ))
            asyncio.create_task(send_pvp_defeat_dm(
                client, target.user_id, a_name, t_name, steal,
                target.bounty, t_old, target.level,
                attacker_id=attacker.user_id, attacker_username=attacker.username,
            ))

        if attacker.level > a_old:
            asyncio.create_task(send_level_up_notification(
                client, attacker.user_id, a_old, attacker.level, "pvp_win"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, a_name, a_old, attacker.level
            ))
        if target.level < t_old:
            asyncio.create_task(send_level_down_notification(
                client, target.user_id, t_old, target.level, "pvp_loss"
            ))
            asyncio.create_task(send_level_down_group_notification(
                client, message.chat.id, t_name, t_old, target.level
            ))

    # ============ LOSS ============
    else:
        pct = 0.05 if is_rob else 0.10

        shield_msg = ""
        if attacker.passive_enabled and attacker.shield_level > 0 and attacker.shield_uses > 0:
            attacker.shield_uses -= 1
            shield_ignore = get_armament_shield_ignore(target)
            if shield_ignore >= 0.5:
                pct = 0.10
                shield_msg = f"\n\n💥 **{t_name}'s Armament Lv.3 SHATTERED your shield!**"
            else:
                pct = max(0.02, pct - 0.05)
                shield_msg = f"\n\n🛡️ **Your SHIELD absorbed part of the blow!**"
                if attacker.shield_uses == 0:
                    attacker.shield_level = 0
                    shield_msg += "\n💔 **Shield broke!**"

        steal = int(attacker.bounty * pct) if attacker.bounty > 0 else 0
        if steal > attacker.bounty:
            steal = attacker.bounty

        target.bounty += steal
        attacker.bounty -= steal

        xp_loss = max(0, min(50, steal // (200_000 if is_rob else 100_000))) if steal > 0 else 0
        attacker.xp -= xp_loss
        while attacker.xp < 0 and attacker.level > 1:
            attacker.level -= 1
            attacker.xp += get_xp_needed(attacker.level)
        if attacker.xp < 0:
            attacker.xp = 0
            attacker.level = 1

        xp_gain = max(0, min(50, steal // 200_000)) if steal > 0 else 0
        if target.boost_end > time.time() and xp_gain > 0:
            xp_gain = min(75, int(xp_gain * 1.5))
        target.xp += xp_gain
        while target.xp >= get_xp_needed(target.level) and target.level < 200:
            target.xp -= get_xp_needed(target.level)
            target.level += 1
        if target.level >= 200:
            target.xp = 0

        if is_rob:
            attacker.rob_cd = time.time()

        save_data()

        a_lt = f"\n\nLEVEL DOWN! {a_old} → {attacker.level}" if attacker.level < a_old else ""
        t_lt = f"\n\n{t_name} LEVEL UP! {t_old} → {target.level}" if target.level > t_old else ""

        result = (
            f"💀 **{'ROBBERY FAILED' if is_rob else 'DEFEAT'}!** 💀"
            f"{conq_note}{pvp_bypass_note}{shield_msg}\n\n"
            f"{a_mention} lost to {t_mention}!\n\n"
            f"Lost: ฿{steal:,}\n"
            f"XP lost: -{xp_loss}\n"
            f"Your bounty: ฿{attacker.bounty:,}"
            f"{a_lt}{t_lt}"
        )

        await fight_msg.delete()
        sent = False
        if LOSE_GIF:
            try:
                await message.reply_animation(LOSE_GIF, caption=result)
                sent = True
            except Exception:
                pass
        if not sent and LOSE_IMAGE:
            try:
                await message.reply_photo(LOSE_IMAGE, caption=result)
                sent = True
            except Exception:
                pass
        if not sent:
            await message.reply(result)

        if is_rob:
            asyncio.create_task(send_rob_failed_dm(
                client, attacker.user_id, target.user_id, t_name, target.username,
                steal, attacker.bounty,
            ))
            asyncio.create_task(send_defended_dm(
                client, target.user_id, attacker.user_id, a_name, attacker.username,
                steal, target.bounty,
            ))
        else:
            asyncio.create_task(send_pvp_defeat_dm(
                client, attacker.user_id, t_name, a_name, steal,
                attacker.bounty, a_old, attacker.level,
                attacker_id=target.user_id, attacker_username=target.username,
            ))
            asyncio.create_task(send_pvp_victory_dm(
                client, target.user_id, t_name, a_name, steal,
                target.bounty, t_old, target.level,
                target_id=attacker.user_id, target_username=attacker.username,
            ))

        if attacker.level < a_old:
            asyncio.create_task(send_level_down_notification(
                client, attacker.user_id, a_old, attacker.level, "pvp_loss"
            ))
            asyncio.create_task(send_level_down_group_notification(
                client, message.chat.id, a_name, a_old, attacker.level
            ))
        if target.level > t_old:
            asyncio.create_task(send_level_up_notification(
                client, target.user_id, t_old, target.level, "pvp_win"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, t_name, t_old, target.level
            ))


def _pvp_fruit_moves_for_player(player, now=None):
    if not player.devil_fruit:
        return []
    now = time.time() if now is None else now
    if _is_nika_fruit(player.devil_fruit):
        awakened = float(getattr(player, "nika_active_until", 0) or 0) > now
    elif _is_ope_ope_fruit(player.devil_fruit):
        awakened = float(getattr(player, "ope_active_until", 0) or 0) > now
    else:
        state_key = get_fruit_awakening_key(player.devil_fruit)
        awakened = bool(
            state_key
            and float(getattr(player, f"{state_key}_active_until", 0) or 0) > now
        )
    return get_pvp_fruit_skills(player.devil_fruit, awakened=awakened)


def _pvp_duel_profile(player):
    """Build a PvP score and display profile from active Haki and fruit move choices."""
    arm_level = get_haki_level(player, "arm")
    observation_level = get_haki_level(player, "obv")
    conqueror_level = get_haki_level(player, "conq")
    armament_multiplier = float(get_armament_multiplier(player) or 1.0)
    fruit_skills = _pvp_fruit_moves_for_player(player)
    power = max(1, int(player.level)) * 1000
    power = int(power * armament_multiplier)

    haki_parts = []
    if arm_level:
        haki_parts.append(f"Armament Lv.{arm_level} (x{armament_multiplier:g})")
    observation_dodge = float(get_observation_win_rate(player) or 0.0) if observation_level else 0.0
    if observation_level:
        haki_parts.append(f"Observation Lv.{observation_level} ({observation_dodge:.0%} dodge)")
    conqueror_chance = float(get_conq_autowin_chance(player) or 0.0) if conqueror_level else 0.0
    if conqueror_level:
        haki_parts.append(f"Conqueror's Lv.{conqueror_level} ({conqueror_chance:.0%} burst)")
    return {
        "power": power,
        "skills": fruit_skills,
        "haki_text": ", ".join(haki_parts) or "No active Haki",
        "observation_dodge": observation_dodge,
        "conqueror_chance": conqueror_chance,
    }


async def _send_pvp_challenge(client, message):
    """Challenge the replied-to player; combat only starts after that player accepts."""
    uid = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("⚠️ Reply to a player with `/attack` to challenge them to a PvP duel.")
        return
    target_user = message.reply_to_message.from_user
    if getattr(target_user, "is_bot", False):
        await message.reply("You can't challenge a bot to a PvP duel.")
        return
    attacker = get_player(uid, user=message.from_user)
    target = get_player(target_user.id, user=target_user)
    if int(attacker.user_id) == int(target.user_id):
        await message.reply("You can't challenge yourself!")
        return
    if not attacker.pvp_enabled:
        await message.reply("**Your PVP is OFF!** Enable it with `/pvp` before challenging anyone.")
        return
    if not target.pvp_enabled:
        await message.reply(f"**{target.name or 'That player'}** has PVP OFF and can't accept a duel.")
        return
    can, remaining = check_cooldown(uid, 25)
    if not can:
        await message.reply(f"⏰ Slow down! Wait {remaining}s before sending another PvP challenge.")
        return

    now = time.time()
    for old_id, old_challenge in list(pending_pvp_challenges.items()):
        if old_challenge.get("expires_at", 0) <= now:
            pending_pvp_challenges.pop(old_id, None)
    challenge_id = uuid.uuid4().hex[:20]
    pending_pvp_challenges[challenge_id] = {
        "attacker_id": uid,
        "target_id": target_user.id,
        "chat_id": message.chat.id,
        "expires_at": now + PVP_CHALLENGE_TTL,
        "status": "pending",
        "moves": {},
    }
    attacker_name = attacker.name or f"User_{attacker.user_id}"
    target_name = target.name or f"User_{target.user_id}"
    a_mention = build_mention(attacker.user_id, attacker_name, attacker.username)
    t_mention = build_mention(target.user_id, target_name, target.username)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Accept Duel", callback_data=f"pvpduel_accept_{challenge_id}"),
        InlineKeyboardButton("Decline", callback_data=f"pvpduel_decline_{challenge_id}"),
    ]])
    await message.reply(
        f"⚔️ **PvP DUEL CHALLENGE**\n\n{a_mention} challenges {t_mention}!\n"
        f"{t_mention}, accept within 2 minutes to fight. The duel lasts up to {PVP_DUEL_ROUNDS} rounds.\n"
        "Each round, both fighters secretly lock in Basic Strike, Guard, or one of their Fruit moves.\n"
        "Guard reduces incoming damage; fruit moves and active Haki affect each round.\n"
        "No bounty is transferred in `/attack`; use `/rob` for robbery.",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


def _challenge_fruit_moves(challenge, player):
    saved = challenge.get("fruit_moves", {})
    return saved.get(str(player.user_id), saved.get(player.user_id, []))


def _pvp_move_keyboard(challenge_id, attacker, target, challenge):
    rows = []
    round_number = challenge.get("round", 1)
    for player in (attacker, target):
        if player.user_id in challenge.get("moves", {}):
            continue
        label_name = (player.name or f"User_{player.user_id}")[:12]
        buttons = [InlineKeyboardButton(
            f"{label_name}: Basic",
            callback_data=f"pvpduel_move_{challenge_id}_{player.user_id}_{round_number}_basic",
        ), InlineKeyboardButton(
            f"{label_name}: Guard",
            callback_data=f"pvpduel_move_{challenge_id}_{player.user_id}_{round_number}_guard",
        )]
        for index, skill in enumerate(_challenge_fruit_moves(challenge, player), start=1):
            label = f"{label_name}: {index}. {skill['name']}"
            buttons.append(InlineKeyboardButton(
                label[:60],
                callback_data=f"pvpduel_move_{challenge_id}_{player.user_id}_{round_number}_fruit{index}",
            ))
        for start in range(0, len(buttons), 2):
            rows.append(buttons[start:start + 2])
    return InlineKeyboardMarkup(rows)


def _pvp_move_status(player, selected_move, fruit_moves):
    name = player.name or f"User_{player.user_id}"
    if selected_move == "basic":
        choice = "Basic Strike"
    elif selected_move == "guard":
        choice = "Guard"
    elif isinstance(selected_move, str) and selected_move.startswith("fruit"):
        try:
            index = int(selected_move[5:]) - 1
            choice = fruit_moves[index]["name"]
        except (ValueError, IndexError):
            choice = "Fruit Spell"
    else:
        return f"• {name}: choosing a move"
    return f"• {name}: selected **{choice}**"


async def _show_pvp_move_selection(client, message, challenge_id, challenge):
    attacker = get_player(challenge["attacker_id"])
    target = get_player(challenge["target_id"])
    moves = challenge.get("moves", {})
    attacker_name = attacker.name or f"User_{attacker.user_id}"
    target_name = target.name or f"User_{target.user_id}"
    a_skills = _challenge_fruit_moves(challenge, attacker)
    t_skills = _challenge_fruit_moves(challenge, target)
    hp = challenge.get("hp", {})
    a_hp = hp.get(attacker.user_id, PVP_DUEL_STARTING_HP)
    t_hp = hp.get(target.user_id, PVP_DUEL_STARTING_HP)
    round_number = challenge.get("round", 1)
    def _skill_choices(name, skills):
        if not skills:
            return f"{name}: no Fruit move"
        return f"{name}: " + " · ".join(
            f"{i}. {skill['name']} (x{skill['multiplier']:g})"
            for i, skill in enumerate(skills, start=1)
        )
    skill_details = _skill_choices(attacker_name, a_skills) + "\n" + _skill_choices(target_name, t_skills)
    text = (
        f"⚔️ **ROUND {round_number}/{PVP_DUEL_ROUNDS} — CHOOSE YOUR MOVE**\n\n"
        f"❤️ {attacker_name}: **{a_hp}/{PVP_DUEL_STARTING_HP} HP**   ·   "
        f"{target_name}: **{t_hp}/{PVP_DUEL_STARTING_HP} HP**\n\n"
        "Both fighters lock in one choice each round: Basic Strike, Guard, or a Fruit move.\n"
        "Guard halves the incoming hit and does not attack. Observation may dodge; Conqueror's may boost a hit.\n"
        "Use only your own button row. Selection closes in 2 minutes.\n\n"
        f"Fruit moves:\n{skill_details}\n\n"
        f"{challenge.pop('round_notice', '')}\n"
        f"{_pvp_move_status(attacker, moves.get(attacker.user_id), a_skills)}\n"
        f"{_pvp_move_status(target, moves.get(target.user_id), t_skills)}"
    )
    keyboard = _pvp_move_keyboard(challenge_id, attacker, target, challenge)
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await message.reply(text, reply_markup=keyboard)


def _pvp_skill_for_move(move_key, fruit_moves):
    if isinstance(move_key, str) and move_key.startswith("fruit"):
        try:
            index = int(move_key[5:]) - 1
            return fruit_moves[index] if 0 <= index < len(fruit_moves) else None
        except ValueError:
            return None
    return None


async def _resolve_pvp_duel(client, message, challenge):
    attacker = get_player(challenge["attacker_id"])
    target = get_player(challenge["target_id"])
    if not attacker.pvp_enabled or not target.pvp_enabled:
        await message.edit_text("🛡️ Duel cancelled because one player turned PVP off.", reply_markup=None)
        return True

    a_name = attacker.name or f"User_{attacker.user_id}"
    t_name = target.name or f"User_{target.user_id}"
    a_profile = _pvp_duel_profile(attacker)
    t_profile = _pvp_duel_profile(target)
    a_move_key = challenge.get("moves", {}).get(attacker.user_id, "basic")
    t_move_key = challenge.get("moves", {}).get(target.user_id, "basic")
    a_skill = _pvp_skill_for_move(a_move_key, _challenge_fruit_moves(challenge, attacker))
    t_skill = _pvp_skill_for_move(t_move_key, _challenge_fruit_moves(challenge, target))
    a_guard = a_move_key == "guard"
    t_guard = t_move_key == "guard"
    a_move_name = "Guard" if a_guard else (a_skill["name"] if a_skill else "Basic Strike")
    t_move_name = "Guard" if t_guard else (t_skill["name"] if t_skill else "Basic Strike")
    a_power = int(a_profile["power"] * (a_skill["multiplier"] if a_skill else 1.0)) if not a_guard else 0
    t_power = int(t_profile["power"] * (t_skill["multiplier"] if t_skill else 1.0)) if not t_guard else 0

    def _base_damage(player, profile, power, guarding):
        if guarding:
            return 0
        # A readable, capped HP-scale hit that still scales with Level and Armament.
        base = 15 + max(1, int(player.level)) * 0.1
        return max(1, min(80, int(round(base * power / max(1, int(player.level) * 1000)))))

    a_damage = _base_damage(attacker, a_profile, a_power, a_guard)
    t_damage = _base_damage(target, t_profile, t_power, t_guard)
    notes = []
    if a_damage and random.random() < a_profile["conqueror_chance"]:
        a_damage = min(80, int(round(a_damage * 1.5)))
        notes.append(f"{a_name}'s Conqueror's Haki burst!")
    if t_damage and random.random() < t_profile["conqueror_chance"]:
        t_damage = min(80, int(round(t_damage * 1.5)))
        notes.append(f"{t_name}'s Conqueror's Haki burst!")

    if a_damage and random.random() < t_profile["observation_dodge"]:
        a_damage = 0
        notes.append(f"{t_name} dodged with Observation Haki.")
    elif a_damage and t_guard:
        a_damage = (a_damage + 1) // 2
        notes.append(f"{t_name}'s Guard reduced the hit.")
    if t_damage and random.random() < a_profile["observation_dodge"]:
        t_damage = 0
        notes.append(f"{a_name} dodged with Observation Haki.")
    elif t_damage and a_guard:
        t_damage = (t_damage + 1) // 2
        notes.append(f"{a_name}'s Guard reduced the hit.")

    hp = challenge.setdefault("hp", {
        attacker.user_id: PVP_DUEL_STARTING_HP,
        target.user_id: PVP_DUEL_STARTING_HP,
    })
    hp[attacker.user_id] = max(0, hp.get(attacker.user_id, PVP_DUEL_STARTING_HP) - t_damage)
    hp[target.user_id] = max(0, hp.get(target.user_id, PVP_DUEL_STARTING_HP) - a_damage)
    challenge.setdefault("total_damage", {attacker.user_id: 0, target.user_id: 0})
    challenge["total_damage"][attacker.user_id] += t_damage
    challenge["total_damage"][target.user_id] += a_damage
    round_number = challenge.get("round", 1)
    a_hp, t_hp = hp[attacker.user_id], hp[target.user_id]
    round_log = (
        f"Round {round_number}: {a_name} — {a_move_name} (power {a_power:,}; hit {a_damage}); "
        f"{t_name} — {t_move_name} (power {t_power:,}; hit {t_damage}).\n"
        f"HP: {a_name} **{a_hp}/{PVP_DUEL_STARTING_HP}** · "
        f"{t_name} **{t_hp}/{PVP_DUEL_STARTING_HP}**"
    )
    if notes:
        round_log += "\n" + " ".join(notes)
    challenge.setdefault("round_history", []).append(round_log)

    winner = None
    reason = ""
    if a_hp == 0 and t_hp == 0:
        reason = "Both fighters were knocked out."
    elif a_hp == 0:
        winner, reason = target, "Knockout!"
    elif t_hp == 0:
        winner, reason = attacker, "Knockout!"
    elif round_number >= PVP_DUEL_ROUNDS:
        if a_hp != t_hp:
            winner = attacker if a_hp > t_hp else target
            reason = "Higher remaining HP after the final round."
        else:
            a_total = challenge["total_damage"][attacker.user_id]
            t_total = challenge["total_damage"][target.user_id]
            if a_total != t_total:
                winner = attacker if t_total > a_total else target
                reason = "Tiebreaker: higher total damage dealt."
            else:
                reason = "The duel ended in a draw."

    if winner is None and round_number < PVP_DUEL_ROUNDS and a_hp and t_hp:
        challenge["round"] = round_number + 1
        challenge["moves"] = {}
        challenge["resolving"] = False
        challenge["expires_at"] = time.time() + PVP_MOVE_TTL
        challenge["round_notice"] = round_log
        return False

    xp_gain = 0
    if winner is not None:
        old_level = winner.level
        xp_gain = 15 if winner.boost_end > time.time() else 10
        winner.xp += xp_gain
        while winner.xp >= get_xp_needed(winner.level) and winner.level < 200:
            winner.xp -= get_xp_needed(winner.level)
            winner.level += 1
        if winner.level >= 200:
            winner.xp = 0
    else:
        old_level = None
    save_data()
    a_mention = build_mention(attacker.user_id, a_name, attacker.username)
    t_mention = build_mention(target.user_id, t_name, target.username)
    history = "\n\n".join(challenge.get("round_history", []))
    outcome = f"🏆 **{winner.name or 'Winner'} wins!**\n{reason}" if winner else f"🤝 **DRAW**\n{reason}"
    reward = f"Reward: +{xp_gain} XP." if winner else "No XP awarded for a draw."
    result = (
        "⚔️ **PVP DUEL COMPLETE** ⚔️\n\n"
        f"{a_mention} (Lv.{attacker.level}) vs {t_mention} (Lv.{target.level})\n\n"
        f"{history}\n\n"
        f"🌀 {a_name}'s Haki: {a_profile['haki_text']}\n"
        f"🌀 {t_name}'s Haki: {t_profile['haki_text']}\n\n"
        f"{outcome}\n{reward} No bounty was transferred; use `/rob` to rob."
    )
    try:
        await message.edit_text(result, reply_markup=None)
    except Exception:
        await message.reply(result)
    if winner and winner.level > old_level:
        asyncio.create_task(send_level_up_notification(
            client, winner.user_id, old_level, winner.level, "pvp_win"
        ))
        asyncio.create_task(send_level_up_group_notification(
            client, message.chat.id, winner.name or f"User_{winner.user_id}", old_level, winner.level
        ))
    return True


async def handle_pvp_duel_callback(client, callback):
    """Handle target-only acceptance and both players' manual move selections."""
    data = callback.data or ""
    if not data.startswith("pvpduel_"):
        return False

    if data.startswith("pvpduel_move_"):
        parts = data.split("_", 5)
        if len(parts) not in {5, 6}:
            await callback.answer("⚠️ Invalid move button.", show_alert=True)
            return True
        action, challenge_id, button_owner = "move", parts[2], parts[3]
        button_round = None
        if len(parts) == 6:
            try:
                button_round = int(parts[4])
            except ValueError:
                await callback.answer("⚠️ Invalid move button.", show_alert=True)
                return True
            move_key = parts[5]
        else:  # Compatibility with buttons created before round numbers were added.
            move_key = parts[4]
        try:
            button_owner = int(button_owner)
        except ValueError:
            await callback.answer("⚠️ Invalid move button.", show_alert=True)
            return True
    else:
        parts = data.split("_", 2)
        if len(parts) != 3 or parts[1] not in {"accept", "decline"}:
            await callback.answer("⚠️ Invalid PvP challenge button.", show_alert=True)
            return True
        action, challenge_id = parts[1], parts[2]
        move_key = None

    challenge = pending_pvp_challenges.get(challenge_id)
    if not challenge:
        await callback.answer("PvP challenge expired.", show_alert=True)
        return True
    if action == "move" and button_round is not None and button_round != challenge.get("round", 1):
        await callback.answer("⚠️ That button belongs to an earlier round. Use the current round's buttons.", show_alert=True)
        return True
    uid = callback.from_user.id
    participants = {challenge["attacker_id"], challenge["target_id"]}
    if action == "move":
        if uid not in participants:
            await callback.answer("⚠️ Only the duelists can select moves.", show_alert=True)
            return True
        if uid != button_owner:
            await callback.answer("Choose from your own fighter row.", show_alert=True)
            return True
    elif uid != challenge["target_id"]:
        await callback.answer("⚠️ Only the challenged player can respond.", show_alert=True)
        return True
    if callback.message.chat.id != challenge["chat_id"]:
        await callback.answer("⚠️ This challenge belongs to another chat.", show_alert=True)
        return True
    if challenge["expires_at"] <= time.time():
        pending_pvp_challenges.pop(challenge_id, None)
        await callback.message.edit_text("⌛ PvP challenge expired.", reply_markup=None)
        await callback.answer("Challenge expired.", show_alert=True)
        return True

    attacker = get_player(challenge["attacker_id"])
    target = get_player(challenge["target_id"])
    if not attacker.pvp_enabled or not target.pvp_enabled:
        pending_pvp_challenges.pop(challenge_id, None)
        await callback.message.edit_text("🛡️ Duel cancelled because one player turned PVP off.", reply_markup=None)
        await callback.answer("PVP is off for one of the players.", show_alert=True)
        return True

    if action == "decline":
        if challenge.get("status") != "pending":
            await callback.answer("The duel is already in move selection.", show_alert=True)
            return True
        pending_pvp_challenges.pop(challenge_id, None)
        await callback.message.edit_text("PvP duel declined.", reply_markup=None)
        await callback.answer("Duel declined.")
        return True

    if action == "accept":
        if challenge.get("status") != "pending":
            await callback.answer("⚠️ This duel has already been accepted.", show_alert=True)
            return True
        challenge["status"] = "selecting"
        challenge["moves"] = {}
        challenge["round"] = 1
        challenge["hp"] = {
            attacker.user_id: PVP_DUEL_STARTING_HP,
            target.user_id: PVP_DUEL_STARTING_HP,
        }
        challenge["total_damage"] = {attacker.user_id: 0, target.user_id: 0}
        challenge["round_history"] = []
        challenge["fruit_moves"] = {
            str(attacker.user_id): _pvp_fruit_moves_for_player(attacker),
            str(target.user_id): _pvp_fruit_moves_for_player(target),
        }
        challenge["expires_at"] = time.time() + PVP_MOVE_TTL
        await callback.answer("Duel accepted. Choose your move.")
        await _show_pvp_move_selection(client, callback.message, challenge_id, challenge)
        return True

    if challenge.get("status") != "selecting":
        await callback.answer("Accept the duel before choosing a move.", show_alert=True)
        return True
    moves = challenge.setdefault("moves", {})
    if uid in moves:
        await callback.answer("You already locked in your move.", show_alert=True)
        return True
    player = attacker if uid == attacker.user_id else target
    fruit_moves = _challenge_fruit_moves(challenge, player)
    if move_key not in {"basic", "guard"} and not _pvp_skill_for_move(move_key, fruit_moves):
        await callback.answer("⚠️ That Fruit move isn't available to you; use your own move row.", show_alert=True)
        return True
    moves[uid] = move_key
    if participants.issubset(moves.keys()):
        if challenge.get("resolving"):
            await callback.answer("Both moves are already locked in.")
            return True
        challenge["resolving"] = True
        await callback.answer("Move locked. Both fighters have chosen.")
        finished = await _resolve_pvp_duel(client, callback.message, challenge)
        if finished:
            pending_pvp_challenges.pop(challenge_id, None)
        else:
            await _show_pvp_move_selection(client, callback.message, challenge_id, challenge)
        return True
    await callback.answer("Move locked. Waiting for the other duelist.")
    if not challenge.get("resolving"):
        await _show_pvp_move_selection(client, callback.message, challenge_id, challenge)
    return True


# ==================== REGISTER ====================
def register_pvp(app):
    @app.on_message(filters.command(["spawnraid", "raidspawn"]))
    async def spawn_raid_cmd(client, message):
        if not message.from_user or message.from_user.id != OWNER_ID:
            return
        if get_world_boss_active():
            active_chat = current_world_boss_chat_id
            destination = f" in chat `{active_chat}`" if active_chat else ""
            await message.reply(f"🌑 A World Boss raid is already active{destination}. End it before spawning another.")
            return
        args = (message.text or message.caption or "").split()
        chat_type = str(getattr(message.chat, "type", "")).split(".")[-1].upper()
        if len(args) > 2:
            await message.reply("⚠️ Usage: `/raidspawn` in a group, or `/raidspawn [group_id]` from a private chat.")
            return
        if len(args) == 2:
            try:
                target_chat_id = int(args[1])
            except ValueError:
                await message.reply("⚠️ Invalid group ID. Usage: `/raidspawn [group_id]`.")
                return
        elif chat_type in {"GROUP", "SUPERGROUP"}:
            target_chat_id = message.chat.id
        else:
            await message.reply("Use `/raidspawn` in the target group, or `/raidspawn [group_id]` here in private chat.")
            return
        try:
            started = await start_world_boss(client, target_chat_id)
            if not started:
                await message.reply("🌑 A World Boss raid is already active. End it before spawning another.")
                return
            await message.reply(f"✅ World Boss raid spawned in chat `{target_chat_id}`.")
        except Exception as exc:
            await message.reply(f"Couldn't spawn the raid boss here: {exc}")


    @app.on_message(filters.command("attack"))
    async def attack_cmd(client, message):
        await _send_pvp_challenge(client, message)

    @app.on_message(filters.command("rob"))
    async def rob_cmd(client, message):
        await _execute_pvp(client, message, is_rob=True)

    # ==================== /battle (World Boss) ====================
    @app.on_message(filters.command(["battle", "fruitskill", *FRUIT_BASE_SPELL_COMMANDS, *FRUIT_EXTRA_SPELL_COMMANDS]))
    async def battle_cmd(client, message):
        command_args = getattr(message, "command", []) or []
        command_name = str(command_args[0]).split("@", 1)[0].casefold() if command_args else "battle"
        direct_fruit_skill = command_name in FRUIT_BASE_SPELL_COMMANDS or command_name in FRUIT_EXTRA_SPELL_COMMANDS
        use_fruit_skill = command_name == "fruitskill" or direct_fruit_skill
        if command_name in {"battle", "fruitskill"} and len(command_args) > 1:
            await message.reply("Use `/battle` for a normal attack, `/fruitskill`, or your fruit's direct spell command.")
            return

        p = get_player(message.from_user.id, user=message.from_user)
        fruit_skill = None
        if use_fruit_skill and not p.devil_fruit:
            await message.reply("You need a Devil Fruit to use a fruit spell.")
            return
        if direct_fruit_skill:
            expected_name = (
                FRUIT_EXTRA_SPELL_COMMANDS[command_name]["fruit"]
                if command_name in FRUIT_EXTRA_SPELL_COMMANDS
                else FRUIT_BASE_SPELL_COMMANDS[command_name]
            )
            expected_fruit = " ".join(expected_name.split()).casefold()
            player_fruit = " ".join(str(p.devil_fruit or "").split()).casefold()
            if player_fruit != expected_fruit:
                await message.reply(
                    f"`/{command_name}` is only available to **{expected_name}** users."
                )
                return
        if use_fruit_skill and _is_nika_fruit(p.devil_fruit):
            await message.reply(
                "☀️ Nika has dedicated moves: `/redhawk`, `/elephantgatling`, "
                "`/bajranggun`, or `/kaminari`. Activate Gear 5 with `/gear5`."
            )
            return
        if use_fruit_skill and _is_ope_ope_fruit(p.devil_fruit):
            await message.reply(
                "⚕️ Ope Ope no Mi has a ROOM-gated spell sequence. Use `/room` first, "
                "then use `/shambles` or `/gammaknife`."
            )
            return
        if use_fruit_skill:
            awakening_key = get_fruit_awakening_key(p.devil_fruit)
            active_until = float(getattr(p, f"{awakening_key}_active_until", 0) or 0) if awakening_key else 0
            if awakening_key and active_until > time.time():
                fruit_name = FRUIT_AWAKENING_FRUITS[awakening_key]
                spell_commands = FRUIT_AWAKENED_WORLD_BOSS_SKILLS[fruit_name]
                commands_text = ", ".join(f"`/{name}`" for name in spell_commands)
                await message.reply(
                    f"✨ Your {FRUIT_AWAKENING_TITLES[awakening_key]} is active. "
                    f"Use an awakened spell instead: {commands_text}."
                )
                return
        if use_fruit_skill:
            fruit_skill = (
                FRUIT_EXTRA_SPELL_COMMANDS[command_name]["skill"]
                if command_name in FRUIT_EXTRA_SPELL_COMMANDS
                else get_fruit_skill(p.devil_fruit)
            )
            if not fruit_skill:
                await message.reply("⚠️ No World Boss skill is configured for your Devil Fruit yet.")
                return
        boss_active = get_world_boss_active() and get_world_boss_hp() > 0
        if not boss_active:
            if use_fruit_skill and fruit_skill:
                await message.reply(
                    f"🍎 **{p.name or 'Pirate'} used {fruit_skill['name']}!**\n"
                    "No World Boss or PvP target is active, so no damage or XP was applied."
                )
            await message.reply("🌑 No World Boss right now. Next raid: 10 PM.")
            return
        if not await _check_world_boss_raid_player(message):
            return
        # Normal /battle damage is a random 900k–1M base hit.
        # Active Haki and fruit skills then multiply this base hit.
        dmg = random.randint(900_000, 1_000_000)
        armament_level = get_haki_level(p, "arm")
        armament_multiplier = get_armament_multiplier(p) if armament_level else 1.0
        if armament_level:
            dmg = int(dmg * armament_multiplier)

        conqueror_level = get_conq_level(p)
        conqueror_burst = False
        if conqueror_level and random.random() < get_conq_autowin_chance(p):
            dmg = int(dmg * 1.5)
            conqueror_burst = True

        fruit_skill_bonus = 0
        if use_fruit_skill:
            normal_damage = dmg
            dmg = int(normal_damage * fruit_skill["multiplier"])
            fruit_skill_bonus = dmg - normal_damage

        new_hp = get_world_boss_hp() - dmg
        set_world_boss_hp(new_hp)
        add_world_boss_damage(message.from_user.id, dmg)

        old_lvl = p.level
        xp = max(1, min(50, dmg // 10_000))
        p.xp += xp
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0

        save_data()

        lt = f"\n\nLEVEL UP! {old_lvl} → {p.level}" if p.level > old_lvl else ""
        if p.level > old_lvl:
            asyncio.create_task(send_level_up_notification(
                client, message.from_user.id, old_lvl, p.level, "world_boss"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, p.name, old_lvl, p.level
            ))

        fruit_skill_note = (
            f"🍎 **{fruit_skill['name']}** — x{fruit_skill['multiplier']:g} damage "
            f"(+{fruit_skill_bonus:,} over normal)\n"
            if use_fruit_skill else ""
        )
        haki_note = ""
        if armament_level:
            haki_note += f"🛡️ Armament Haki — x{armament_multiplier:g}\n"
        if conqueror_level:
            haki_note += (
                "👑 Conqueror's Haki burst — x1.5\n"
                if conqueror_burst else
                "👑 Conqueror's Haki ready (no burst this attack)\n"
            )
        await message.reply(
            f"⚔️ **You attacked {(current_world_boss or {}).get('name', 'the World Boss')}!**\n"
            f"Damage: {dmg:,}\n"
            f"{haki_note}"
            f"{fruit_skill_note}"
            f"XP: +{xp}\n"
            f"Boss HP: {max(0, new_hp):,}{lt}"
        )

        if new_hp <= 0:
            await end_world_boss(client, MAIN_GROUP_ID)

    # ==================== OPE OPE / ROOM AWAKENING ====================
    @app.on_message(filters.command(["room", "shambles", "gammaknife", "kroom", "shockwille"]))
    async def ope_skill_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_ope_ope_fruit(p.devil_fruit):
            await message.reply("These spells are only for the Ope Ope no Mi.")
            return

        command_args = getattr(message, "command", []) or []
        if len(command_args) > 1:
            await message.reply("Use each Ope spell as its own command, with no extra argument.")
            return
        command_name = str(command_args[0]).split("@", 1)[0].casefold() if command_args else ""
        aliases = {"room": "room", "shambles": "shambles", "gammaknife": "gammaknife", "kroom": "kroomtact", "shockwille": "shockwille"}
        move_key = aliases.get(command_name)
        if not move_key:
            await message.reply("Use `/room`, `/shambles`, `/gammaknife`, `/kroom`, or `/shockwille`.")
            return

        uid = message.from_user.id
        now = time.time()
        active_until = float(getattr(p, "ope_active_until", 0) or 0)
        cooldown_until = float(getattr(p, "ope_cooldown_until", 0) or 0)
        awakened = active_until > now
        room_ready = uid in world_boss_ope_room_users

        if move_key == "room":
            if room_ready:
                await message.reply("⚕️ ROOM is already deployed for this raid; `/shambles` and `/gammaknife` are unlocked.")
                return
            world_boss_ope_room_users.add(uid)
            await message.reply(
                "⚕️ **ROOM!** Your operating space is open. You may now use `/shambles` "
                "or `/gammaknife`, or awaken with `/opeawake`."
            )
            return

        if not room_ready:
            await message.reply("Deploy ROOM first with `/room`; other Ope techniques are locked until then.")
            return

        base_moves = {"shambles", "gammaknife"}
        awakened_moves = {"kroomtact", "shockwille"}
        if awakened and move_key in base_moves:
            await message.reply("☀️ Awakening is active; use `/kroom` or `/shockwille` until it ends.")
            return
        if not awakened and move_key in awakened_moves:
            left = max(0, int(cooldown_until - now))
            if left:
                await message.reply(f"⏳ Ope awakening is cooling down for {left}s. Base moves are available.")
            else:
                await message.reply("Use `/opeawake` to awaken before using `/kroom` or `/shockwille`.")
            return
        if move_key not in base_moves | awakened_moves:
            await message.reply("Unknown Ope spell. Use `/room`, `/shambles`, `/gammaknife`, `/kroom`, or `/shockwille`.")
            return

        move_name, multiplier = OPE_MOVES[move_key]
        if not get_world_boss_active() or get_world_boss_hp() <= 0:
            if move_key in awakened_moves:
                move_gif = get_ope_awakening_gif(move_key)
                if move_gif:
                    try:
                        await message.reply_animation(move_gif, caption=f"⚕️ {move_name}!")
                    except Exception as exc:
                        print(f"[Ope Ope awakened GIF] {move_key}: {exc}")
            await message.reply(
                f"⚕️ **{p.name or 'Pirate'} used {move_name}!**\n"
                "No World Boss or PvP target is active, so no damage or XP was applied."
            )
            return
        if not await _check_world_boss_raid_player(message):
            return
        damage = p.level * 1000
        if p.haki == "arm":
            damage = int(damage * (1 + p.haki_level * 0.3))
        if p.devil_fruit and p.fruit_category == "Good":
            damage = int(damage * 1.5)
        damage = int(damage * multiplier)
        new_hp = get_world_boss_hp() - damage
        set_world_boss_hp(new_hp)
        add_world_boss_damage(uid, damage)

        old_level = p.level
        xp = max(1, min(50, damage // 10_000))
        p.xp += xp
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0
        save_data()
        if p.level > old_level:
            asyncio.create_task(send_level_up_notification(
                client, uid, old_level, p.level, "world_boss"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, p.name, old_level, p.level
            ))

        if move_key in awakened_moves:
            move_gif = get_ope_awakening_gif(move_key)
            if move_gif:
                try:
                    await message.reply_animation(move_gif, caption=f"⚕️ {move_name}!")
                except Exception as exc:
                    print(f"[Ope Ope awakened GIF] {move_key}: {exc}")
        active_note = f"\nAwakening: {max(0, int(active_until - now))}s left" if awakened else ""
        await message.reply(
            f"⚕️ **{p.name} used {move_name}!**\n"
            f"Damage: **{damage:,}** (x{multiplier:g})\n"
            f"XP: +{xp}\n"
            f"World Boss HP: {max(0, new_hp):,}{active_note}"
        )
        if new_hp <= 0:
            await end_world_boss(client, MAIN_GROUP_ID)

    @app.on_message(filters.command("opeawake"))
    async def ope_awake_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_ope_ope_fruit(p.devil_fruit):
            await message.reply("You need the Ope Ope no Mi to awaken its techniques.")
            return
        uid = message.from_user.id
        if uid not in world_boss_ope_room_users:
            await message.reply("Open ROOM first with `/room` before awakening.")
            return
        now = time.time()
        active_until = float(getattr(p, "ope_active_until", 0) or 0)
        if active_until > now:
            await message.reply(f"⚕️ Ope awakening is already active for {int(active_until - now)} more seconds.")
            return
        cooldown_until = float(getattr(p, "ope_cooldown_until", 0) or 0)
        if cooldown_until > now:
            await message.reply(f"⏳ Ope awakening cooldown: {int(cooldown_until - now)}s remaining.")
            return
        p.ope_active_until = now + OPE_AWAKENING_DURATION
        p.ope_cooldown_until = now + OPE_AWAKENING_DURATION + OPE_AWAKENING_COOLDOWN
        save_data()
        await message.reply(
            "⚕️ **OPE OPE AWAKENING!**\n"
            "For 5 minutes, use `/kroom` (K-Room (Tact), x3) or "
            "`/shockwille` (Shock Wille, x4).\n"
            "After awakening ends, it has a 5-minute cooldown. World Boss spells can be repeated while the boss is active."
        )

    @app.on_message(filters.command("opeawakeoff"))
    async def ope_awake_off_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_ope_ope_fruit(p.devil_fruit):
            await message.reply("You need the Ope Ope no Mi to use this command.")
            return
        now = time.time()
        if float(getattr(p, "ope_active_until", 0) or 0) <= now:
            await message.reply("Ope awakening is not active. Use `/opeawake` after deploying ROOM when cooldown is ready.")
            return
        p.ope_active_until = 0
        p.ope_cooldown_until = now + OPE_AWAKENING_COOLDOWN
        save_data()
        await message.reply("⚕️ Ope awakening ended. The Ope techniques need **5 minutes** to recover.")

    # ==================== NIKA / GEAR 5 ====================
    @app.on_message(filters.command(list(NIKA_MOVES)))
    async def nika_skill_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_nika_fruit(p.devil_fruit):
            await message.reply("These direct spell commands are only for the Hito Hito no Mi, Model: Nika.")
            return

        now = time.time()
        active_until = float(getattr(p, "nika_active_until", 0) or 0)
        active = active_until > now
        if not active and (p.nika_awakened or active_until):
            p.nika_awakened = False
            p.nika_active_until = 0
            save_data()

        args = getattr(message, "command", []) or []
        command_name = str(args[0]).split("@", 1)[0].casefold() if args else ""
        if len(args) > 1:
            await message.reply("Use each Nika spell as its own command with no extra argument.")
            return
        move_key = command_name
        allowed = ("bajranggun", "kaminari") if active else ("redhawk", "elephantgatling")
        if move_key not in allowed:
            if active:
                await message.reply("Gear 5 moves: `/bajranggun` or `/kaminari`.")
            else:
                await message.reply("Before awakening use `/redhawk` or `/elephantgatling`.")
            return
        move_name, multiplier = NIKA_MOVES[move_key]
        if not get_world_boss_active() or get_world_boss_hp() <= 0:
            move_gif = get_nika_move_gif(move_key)
            if move_gif:
                try:
                    await message.reply_animation(move_gif, caption=f"☀️ {move_name}!")
                except Exception as exc:
                    print(f"[Nika spell GIF] {move_key}: {exc}")
            await message.reply(
                f"☀️ **{p.name or 'Pirate'} used {move_name}!**\n"
                "No World Boss or PvP target is active, so no damage or XP was applied."
            )
            return
        if not await _check_world_boss_raid_player(message):
            return
        damage = p.level * 1000
        if p.haki == "arm":
            damage = int(damage * (1 + p.haki_level * 0.3))
        if p.devil_fruit and p.fruit_category == "Good":
            damage = int(damage * 1.5)
        damage = int(damage * multiplier)
        new_hp = get_world_boss_hp() - damage
        set_world_boss_hp(new_hp)
        add_world_boss_damage(message.from_user.id, damage)

        old_level = p.level
        xp = max(1, min(50, damage // 10_000))
        p.xp += xp
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0
        save_data()
        if p.level > old_level:
            asyncio.create_task(send_level_up_notification(
                client, message.from_user.id, old_level, p.level, "world_boss"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, p.name, old_level, p.level
            ))
        if move_key in ("bajranggun", "kaminari"):
            move_gif = get_nika_move_gif(move_key)
            if move_gif:
                try:
                    await message.reply_animation(move_gif, caption=f"☀️ {move_name}!")
                except Exception as exc:
                    print(f"[Nika spell GIF] {move_key}: {exc}")
        active_note = f"\nGear 5: **{max(0, int(active_until - now))}s left**" if active else ""
        await message.reply(
            f"☀️ **{p.name} used {move_name}!**\n"
            f"Damage: **{damage:,}** (x{multiplier:g})\n"
            f"XP: +{xp}\n"
            f"World Boss HP: {max(0, new_hp):,}{active_note}"
        )
        if new_hp <= 0:
            await end_world_boss(client, MAIN_GROUP_ID)

    @app.on_message(filters.command("gear5"))
    async def gear5_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_nika_fruit(p.devil_fruit):
            await message.reply("You need the Hito Hito no Mi, Model: Nika to hear the Drums of Liberation.")
            return
        now = time.time()
        active_until = float(getattr(p, "nika_active_until", 0) or 0)
        if active_until > now:
            await message.reply(f"☀️ Gear 5 is already active for {int(active_until - now)} more seconds.")
            return
        cooldown_until = float(getattr(p, "nika_cooldown_until", 0) or 0)
        if cooldown_until > now:
            await message.reply(f"⏳ The drums are resting. Try again in {int(cooldown_until - now)} seconds.")
            return
        p.nika_active_until = now + GEAR5_DURATION
        p.nika_cooldown_until = now + GEAR5_DURATION + GEAR5_COOLDOWN
        p.nika_awakened = True
        save_data()
        if NIKA_GIF:
            try:
                await message.reply_animation(
                    NIKA_GIF,
                    caption=(
                        "🥁 DRUMS OF LIBERATION — GEAR 5!\n\n"
                        "Awakened techniques:\n"
            "1. Gomu Gomu no Bajrang Gun — `/bajranggun` (x150)\n"
            "2. Gomu Gomu no Kaminari — `/kaminari` (x100)\n"
                        "3. Return to base — `/gear5off`"
                    ),
                )
            except Exception:
                pass
        await message.reply(
            "🥁 **DRUMS OF LIBERATION! GEAR 5!**\n"
            "Your awakening lasts **5 minutes**. After it ends, Gear 5 has a **5-minute cooldown**.\n\n"
            "Use `/bajranggun` or `/kaminari`.\n"
            "Return to base form early with `/gear5off`."
        )

    @app.on_message(filters.command("gear5off"))
    async def gear5off_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not _is_nika_fruit(p.devil_fruit):
            await message.reply("You need the Hito Hito no Mi, Model: Nika to use this command.")
            return
        now = time.time()
        if float(getattr(p, "nika_active_until", 0) or 0) <= now:
            p.nika_awakened = False
            p.nika_active_until = 0
            save_data()
            await message.reply("Gear 5 is not active. Use `/gear5` when its cooldown is ready.")
            return
        p.nika_awakened = False
        p.nika_active_until = 0
        p.nika_cooldown_until = now + GEAR5_COOLDOWN
        save_data()
        await message.reply("☀️ Gear 5 deactivated. The drums need **5 minutes** to rest before you can awaken again.")

    # ==================== ITO / MOCHI / JIKI / GOMU AWAKENINGS ====================
    @app.on_message(filters.command(list(FRUIT_AWAKENING_COMMANDS) + list(FRUIT_AWAKENING_OFF_COMMANDS)))
    async def fruit_awakening_cmd(client, message):
        command_args = getattr(message, "command", []) or []
        command_name = str(command_args[0]).split("@", 1)[0].casefold() if command_args else ""
        expected_key = FRUIT_AWAKENING_COMMANDS.get(command_name)
        is_off = expected_key is None
        expected_key = expected_key or FRUIT_AWAKENING_OFF_COMMANDS.get(command_name)
        if not expected_key:
            return
        p = get_player(message.from_user.id, user=message.from_user)
        valid_gear4_syntax = (
            command_name == "gear4"
            and len(command_args) == 2
            and str(command_args[1]).casefold() == "snakeman"
        )
        if len(command_args) > 1 and not valid_gear4_syntax:
            await message.reply("Use the awakening command by itself, with no extra arguments.")
            return
        state_key = get_fruit_awakening_key(p.devil_fruit)
        if state_key != expected_key:
            required_fruit = FRUIT_AWAKENING_FRUITS[expected_key]
            await message.reply(f"⚠️ This awakening command is only for **{required_fruit}**.")
            return

        now = time.time()
        active_field = f"{state_key}_active_until"
        cooldown_field = f"{state_key}_cooldown_until"
        active_until = float(getattr(p, active_field, 0) or 0)
        cooldown_until = float(getattr(p, cooldown_field, 0) or 0)
        title = FRUIT_AWAKENING_TITLES[state_key]
        if is_off:
            if active_until <= now:
                await message.reply(f"{title} is not active. Use `/{next(cmd for cmd, key in FRUIT_AWAKENING_COMMANDS.items() if key == state_key)}` when its cooldown is ready.")
                return
            setattr(p, active_field, 0)
            setattr(p, cooldown_field, now + FRUIT_AWAKENING_COOLDOWN)
            save_data()
            await message.reply(f"✨ {title} ended. Its moves need **5 minutes** to recover.")
            return

        if active_until > now:
            await message.reply(f"✨ {title} is already active for {int(active_until - now)} more seconds.")
            return
        if cooldown_until > now:
            await message.reply(f"⏳ {title} cooldown: **{int(cooldown_until - now)}s** remaining.")
            return

        pvp_fruit_name = FRUIT_AWAKENING_FRUITS[state_key]
        spell_map = FRUIT_AWAKENED_WORLD_BOSS_SKILLS[pvp_fruit_name]
        pvp_moves = get_pvp_fruit_skills(p.devil_fruit, awakened=True)
        setattr(p, active_field, now + FRUIT_AWAKENING_DURATION)
        setattr(p, cooldown_field, now + FRUIT_AWAKENING_DURATION + FRUIT_AWAKENING_COOLDOWN)
        save_data()
        try:
            from fruit_awakening_media import get_fruit_awakening_gif
            awakening_gif = get_fruit_awakening_gif(state_key)
            if awakening_gif:
                await message.reply_animation(awakening_gif, caption=f"✨ {title.upper()} ACTIVATED!")
        except Exception as exc:
            print(f"[fruit awakening GIF] {state_key}: {exc}")
        spell_text = "\n".join(
            f"• `{command}` — {skill['name']} (World Boss x{skill['multiplier']:g})"
            for command, skill in spell_map.items()
        )
        duel_text = " · ".join(
            f"{move['name']} (PvP x{move['multiplier']:g})" for move in pvp_moves
        )
        pre_snake_note = (
            "\nPre-Snakeman `/thorelephantgun` and `/jetgatling` are disabled while this mode is active."
            if state_key == "gomu" else ""
        )
        await message.reply(
            f"✨ **{title.upper()} ACTIVATED!**\n"
            "Active for **5 minutes**, followed by a **5-minute cooldown**.\n\n"
            f"World Boss spells (repeatable while the boss is active):\n{spell_text}\n\n"
            f"Accepted PvP move options: {duel_text}.{pre_snake_note}"
        )

    @app.on_message(filters.command(list(AWAKENED_SPELL_COMMANDS)))
    async def awakened_fruit_spell_cmd(client, message):
        command_args = getattr(message, "command", []) or []
        command_name = str(command_args[0]).split("@", 1)[0].casefold() if command_args else ""
        expected_key = AWAKENED_SPELL_COMMANDS.get(command_name)
        if not expected_key:
            return
        p = get_player(message.from_user.id, user=message.from_user)
        if len(command_args) > 1:
            await message.reply("Use each awakened spell as its own command, with no extra argument.")
            return
        state_key = get_fruit_awakening_key(p.devil_fruit)
        if state_key != expected_key:
            await message.reply(
                f"`/{command_name}` is only available to **{FRUIT_AWAKENING_FRUITS[expected_key]}** users."
            )
            return

        now = time.time()
        active_until = float(getattr(p, f"{state_key}_active_until", 0) or 0)
        if active_until <= now:
            cooldown_until = float(getattr(p, f"{state_key}_cooldown_until", 0) or 0)
            if cooldown_until > now:
                await message.reply(
                    f"⏳ {FRUIT_AWAKENING_TITLES[state_key]} is inactive; cooldown has "
                    f"{int(cooldown_until - now)}s left."
                )
            else:
                activation = next(cmd for cmd, key in FRUIT_AWAKENING_COMMANDS.items() if key == state_key)
                await message.reply(f"Activate first with `/{activation}`.")
            return
        skill = get_awakened_world_boss_skill(p.devil_fruit, command_name)
        if not skill:
            await message.reply("⚠️ That awakened spell is not available for your Devil Fruit.")
            return
        if not get_world_boss_active() or get_world_boss_hp() <= 0:
            await message.reply(
                f"✨ **{p.name or 'Pirate'} used {skill['name']}!**\n"
                "No World Boss or PvP target is active, so no damage or XP was applied."
            )
            return

        if not await _check_world_boss_raid_player(message):
            return

        damage = max(1, int(p.level)) * 1000
        if p.haki == "arm":
            damage = int(damage * (1 + p.haki_level * 0.3))
        if p.fruit_category == "Good":
            damage = int(damage * 1.5)
        damage = int(damage * skill["multiplier"])
        new_hp = get_world_boss_hp() - damage
        set_world_boss_hp(new_hp)
        add_world_boss_damage(message.from_user.id, damage)

        old_level = p.level
        xp = max(1, min(50, damage // 10_000))
        p.xp += xp
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0
        save_data()
        if p.level > old_level:
            asyncio.create_task(send_level_up_notification(
                client, message.from_user.id, old_level, p.level, "world_boss"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, p.name, old_level, p.level
            ))
        await message.reply(
            f"✨ **{p.name or 'Pirate'} used {skill['name']}!**\n"
            f"Damage: **{damage:,}** (x{skill['multiplier']:g})\n"
            f"XP: +{xp}\n"
            f"World Boss HP: {max(0, new_hp):,}\n"
            f"{FRUIT_AWAKENING_TITLES[state_key]}: {max(0, int(active_until - now))}s left"
        )
        if new_hp <= 0:
            await end_world_boss(client, MAIN_GROUP_ID)

    @app.on_message(filters.command(list(GOMU_PRE_AWAKENED_SPELL_COMMANDS)))
    async def gomu_pre_awakened_spell_cmd(client, message):
        command_args = getattr(message, "command", []) or []
        command_name = str(command_args[0]).split("@", 1)[0].casefold() if command_args else ""
        if command_name not in GOMU_PRE_AWAKENED_SPELL_COMMANDS:
            return
        p = get_player(message.from_user.id, user=message.from_user)
        if len(command_args) > 1:
            await message.reply("Use this Gomu spell as a standalone command, with no extra argument.")
            return
        if get_fruit_awakening_key(p.devil_fruit) != "gomu":
            await message.reply(f"`/{command_name}` is only for the separate **Gomu Gomu no Mi** fruit.")
            return
        now = time.time()
        if float(getattr(p, "gomu_active_until", 0) or 0) > now:
            await message.reply(
                "🐍 Snakeman is active. These two base-form spells are only available before Snakeman "
                "or after it ends; use `/kingcobra`, `/blackmamba`, or `/jetculverin` while transformed."
            )
            return
        skill = get_pre_awakened_world_boss_skill(p.devil_fruit, command_name)
        if not skill:
            await message.reply("⚠️ That spell is not set for your Devil Fruit.")
            return
        if not get_world_boss_active() or get_world_boss_hp() <= 0:
            await message.reply(
                f"🦍 **{p.name or 'Pirate'} used {skill['name']}!**\n"
                "No World Boss or PvP target is active, so no damage or XP was applied."
            )
            return

        if not await _check_world_boss_raid_player(message):
            return

        damage = max(1, int(p.level)) * 1000
        if p.haki == "arm":
            damage = int(damage * (1 + p.haki_level * 0.3))
        if p.fruit_category == "Good":
            damage = int(damage * 1.5)
        damage = int(damage * skill["multiplier"])
        new_hp = get_world_boss_hp() - damage
        set_world_boss_hp(new_hp)
        add_world_boss_damage(message.from_user.id, damage)

        old_level = p.level
        xp = max(1, min(50, damage // 10_000))
        p.xp += xp
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0
        save_data()
        if p.level > old_level:
            asyncio.create_task(send_level_up_notification(
                client, message.from_user.id, old_level, p.level, "world_boss"
            ))
            asyncio.create_task(send_level_up_group_notification(
                client, message.chat.id, p.name, old_level, p.level
            ))
        await message.reply(
            f"🦍 **{p.name or 'Pirate'} used {skill['name']}!**\n"
            f"Damage: **{damage:,}** (x{skill['multiplier']:g})\n"
            f"XP: +{xp}\n"
            f"World Boss HP: {max(0, new_hp):,}"
        )
        if new_hp <= 0:
            await end_world_boss(client, MAIN_GROUP_ID)

    # ==================== /challenge ====================
    @app.on_message(filters.command("challenge"))
    async def challenge_cmd(client, message):
        chat_id = message.chat.id
        uid = message.from_user.id

        if not await _can_challenge_character(client, message):
            await message.reply(
                "You must join the main group and update channel before "
                "challenging spawned characters."
            )
            return

        if chat_id not in active_challenges:
            await message.reply("**No character here!** Wait for one to spawn (every 150 messages).")
            return

        challenge = active_challenges[chat_id]
        if challenge.get("challenger") is not None:
            await message.reply("Someone is already challenging this character!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("Type `/challenge `[name]!")
            return

        guessed = " ".join(args[1:]).lower().strip()
        actual = challenge["char"].get("name", "").lower()
        parts = actual.split()

        is_match = False
        if guessed == actual:
            is_match = True
        elif guessed in parts:
            is_match = True
        elif len(guessed) >= 3 and (
            actual.startswith(guessed)
            or actual.endswith(guessed)
            or guessed in actual
        ):
            is_match = True

        if not is_match:
            time_left = max(0, 300 - (time.time() - challenge["spawn_time"]))
            await message.reply(
                f"**Wrong guess!**\n"
                f"{int(time_left // 60)}m {int(time_left % 60)}s left"
            )
            return

        challenge["challenger"] = uid

        p = get_player(uid, user=message.from_user)
        char_name = challenge["char"].get("name", "?")
        challenged_char = challenge.get("char", {})
        char_id = challenged_char.get("id")
        prior_count = sum(
            1 for c in p.captured_chars
            if (c.get("id") == char_id if char_id is not None else c.get("name") == char_name)
        )

        await message.reply(
            f"⚔️ **{message.from_user.first_name}** challenges **{char_name}**!\n"
            f"Fighting..."
        )
        await asyncio.sleep(1.5)

        challenge_rarity = str(challenge.get("rarity", "MYTHICAL" if challenge.get("is_mythical") else "NORMAL")).upper()
        configured_chance = challenged_char.get("win_chance")
        if configured_chance is not None:
            try:
                win_chance = max(0.0, min(1.0, float(configured_chance) / 100))
            except (TypeError, ValueError):
                configured_chance = None
        if configured_chance is None:
            if challenge_rarity == "MYTHICAL":
                win_chance = min(0.8, 0.1 + (p.level / 500) + (p.haki_level * 0.05))
            else:
                win_chance = min(0.95, 0.4 + (p.level / 200) + (p.haki_level * 0.05))
        if challenge_rarity == "MYTHICAL":
            reward_xp = 5000
            reward_token = 1
        else:
            reward_xp = random.randint(50, 500)
            reward_token = 0
        reward_min, reward_max = get_rarity_reward_range(challenge_rarity)
        reward_bounty = random.randint(reward_min, reward_max)

        win = random.random() < win_chance
        new_count = prior_count + (1 if win else 0)

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"Challenged {char_name} x{new_count}",
                callback_data="noop",
            )
        ]])

        if win:
            # The active challenge already holds the exact catalog record that
            # was posted. Do not resolve it again by ID: legacy duplicate IDs
            # or edits/deletions during the fight could return a different card.
            full = challenged_char.copy() if isinstance(challenged_char, dict) else None
            if not full or not full.get("name"):
                active_challenges.pop(chat_id, None)
                await message.reply(
                    f"**{char_name}** is no longer available, so it was not captured."
                )
                return
            char_name = full.get("name", char_name)
            challenge_rarity = str(full.get("rarity", challenge_rarity)).upper()
            p.captured_chars.append({
                "id": full.get("id"),
                "name": full["name"],
                "image": full.get("image"),
                "media_type": full.get("media_type", "photo"),
                "rarity": full.get("rarity", challenge_rarity),
                "captured_at": time.time(),
            })

            p.bounty += reward_bounty
            p.xp += min(50, reward_xp)
            p.advanced_token += reward_token

            old_lvl = p.level
            while p.xp >= get_xp_needed(p.level) and p.level < 200:
                p.xp -= get_xp_needed(p.level)
                p.level += 1
            if p.level >= 200:
                p.xp = 0

            save_data()

            if p.level > old_lvl:
                await send_level_up_notification(client, uid, old_lvl, p.level, "challenge")
                await send_level_up_group_notification(client, message.chat.id, p.name, old_lvl, p.level)

            reward_txt = f"Bounty: +฿{reward_bounty:,}\nXP: +{min(50, reward_xp)}"
            if reward_token:
                reward_txt += f"\nToken: +{reward_token}"
            lt = f"\n\nLEVEL UP! {old_lvl} → {p.level}" if p.level > old_lvl else ""

            await message.reply(
                f"🎉 **VICTORY!** 🎉\n\n"
                f"Defeated **{char_name}**!\n"
                f"🆔 Character ID: `{char_id}`\n\n"
                f"**Rewards:**\n{reward_txt}{lt}",
                reply_markup=kb,
            )
        else:
            xp_loss = max(1, min(50, reward_xp // 2))
            p.xp -= xp_loss
            old_lvl = p.level
            while p.xp < 0 and p.level > 1:
                p.level -= 1
                p.xp += get_xp_needed(p.level)
            if p.xp < 0:
                p.xp = 0
                p.level = 1
            save_data()

            if p.level < old_lvl:
                await send_level_down_notification(client, uid, old_lvl, p.level, "challenge")
                await send_level_down_group_notification(client, message.chat.id, p.name, old_lvl, p.level)

            lt = f"\n\nLEVEL DOWN! {old_lvl} → {p.level}" if p.level < old_lvl else ""
            await message.reply(
                f"💀 **DEFEAT!**\n\n"
                f"Defeated by **{char_name}**!\n"
                f"-{xp_loss} XP{lt}",
                reply_markup=kb,
            )

        active_challenges.pop(chat_id, None)

    # ==================== /timeleft ====================
    @app.on_message(filters.command("timeleft"))
    async def timeleft_cmd(client, message):
        chat_id = message.chat.id
        if chat_id not in active_challenges:
            await message.reply("⚠️ No character is active right now.")
            return

        ch = active_challenges[chat_id]
        left = max(0, 300 - (time.time() - ch["spawn_time"]))
        status_rarity = ch.get("rarity", "MYTHICAL" if ch.get("is_mythical") else "NORMAL")
        await message.reply(
            f"**Character Status**\n\n"
            f"{get_rarity_emoji(status_rarity)} {ch['char'].get('name', '?')}\n"
            f"{status_rarity}\n\n"
            f"{int(left // 60)}m {int(left % 60)}s left\n\n"
            f"`/challenge `[name]"
        )

   # ==================== /trade ====================
    @app.on_message(filters.command("trade"))
    async def trade_cmd(client, message):
        uid = message.from_user.id

        if not message.reply_to_message:
            await message.reply(
                "**TRADE**\n\n"
                "Buyer replies to a seller with `/trade [price]`\n\n"
                "1. Seller accepts or cancels\n"
                "2. Buyer chooses a character from the seller\n"
                "3. Seller reviews and confirms the final trade\n\n"
                f"{BOT_NAME}"
            )
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("⚠️ Usage: `/trade [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("⚠️ That amount is invalid.")
            return

        buyer = get_player(uid, user=message.from_user)
        seller = get_player(
            message.reply_to_message.from_user.id,
            user=message.reply_to_message.from_user,
        )

        if int(seller.user_id) == int(buyer.user_id):
            await message.reply("Can't trade with yourself!")
            return

        if not seller.captured_chars:
            await message.reply("⚠️ The seller doesn't have any characters to sell!")
            return

        if buyer.bounty < amount:
            await message.reply(
                f"Buyer needs ฿{amount:,}!\nThey have ฿{buyer.bounty:,}"
            )
            return

        trade_id = uuid.uuid4().hex[:12]

        for char in seller.captured_chars:
            if not char.get("id"):
                master = get_character_by_name(char.get("name", ""))
                if master:
                    char["id"] = master.get("id")

        trade_data = {
            "seller_id": seller.user_id,
            "buyer_id": buyer.user_id,
            "amount": amount,
            "chars": [],
            "selected_char": None,
            "selected_index": None,
            "seller_accepted": False,
            "timestamp": time.time(),
        }
        add_trade(trade_id, trade_data)

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Accept", callback_data=f"trade_accept_{trade_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"trade_cancel_{trade_id}"),
        ]])

        s_name = seller.name or f"User_{seller.user_id}"
        b_name = buyer.name or f"User_{buyer.user_id}"

        await message.reply(
            f"**TRADE OFFER**\n\n"
            f"Seller: {s_name}\n"
            f"Buyer: {b_name}\n"
            f"Price: ฿{amount:,}\n"
            f"Seller, accept or cancel this offer.\n\n"
            f"Expires in 2 min",
            reply_markup=kb,
        )
