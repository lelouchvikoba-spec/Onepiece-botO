"""Persistent owner-configurable economy prices.

The current values below are defaults. Owner overrides are saved separately in
``data/price_overrides.json`` so changing a price never requires editing source.
"""
import json
import os
import re
import tempfile
import threading
from decimal import Decimal, InvalidOperation

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PRICE_FILE = os.path.join(DATA_DIR, "price_overrides.json")

PRICE_DEFAULTS = {
    # Haki
    "haki_purchase": 25_000_000,
    "haki_switch": 5_000_000,
    "haki_upgrade_2": 50_000_000,
    "haki_upgrade_3": 100_000_000,
    "haki_sell_refund": 12_500_000,
    "advanced_haki": 500_000_000_000,
    # Devil fruits and sell refunds
    "fruit_bad": 25_000_000,
    "fruit_medium": 250_000_000,
    "fruit_good": 25_000_000_000,
    "fruit_refund_bad": 12_500_000,
    "fruit_refund_medium": 125_000_000,
    "fruit_refund_good": 12_500_000_000,
    # Shields, vault, and XP boost
    "shield_1": 25_000_000,
    "shield_2": 250_000_000,
    "shield_3": 25_000_000_000,
    "vault_2": 25_000_000_000,
    "vault_3": 500_000_000_000,
    "xp_boost": 50_000_000,
    # Fishing equipment
    "rod_wooden": 5_000_000,
    "rod_steel": 25_000_000,
    "rod_diamond": 150_000_000,
    "rod_mythical": 1_000_000_000,
    "bait_basic": 1_000_000,
    "bait_steel": 5_000_000,
    "bait_diamond": 30_000_000,
    "bait_mythical": 200_000_000,
    # Crew costs and ship tiers
    "crew_create": 50_000_000,
    "crew_image_change": 10_000_000,
    "ship_1": 0,
    "ship_2": 100_000_000,
    "ship_3": 500_000_000,
    "ship_4": 2_000_000_000,
    "ship_5": 10_000_000_000,
    "ship_6": 50_000_000_000,
    # Fish sale values (minimum and maximum roll for each catch)
    "fish_sardine_min": 699_999,
    "fish_sardine_max": 1_888_888,
    "fish_blue_tang_min": 850_000,
    "fish_blue_tang_max": 1_050_000,
    "fish_tuna_min": 950_000,
    "fish_tuna_max": 1_250_000,
    "fish_salmon_min": 1_050_000,
    "fish_salmon_max": 1_400_000,
    "fish_swordfish_min": 1_200_000,
    "fish_swordfish_max": 1_650_000,
    "fish_golden_koi_min": 1_400_000,
    "fish_golden_koi_max": 1_888_888,
    "fish_sea_king_fish_min": 1_600_000,
    "fish_sea_king_fish_max": 2_500_000,
}

PRICE_LABELS = {
    "haki_purchase": "Haki purchase",
    "haki_switch": "Haki switch",
    "haki_upgrade_2": "Haki upgrade to Lv.2",
    "haki_upgrade_3": "Haki upgrade to Lv.3",
    "haki_sell_refund": "Haki sell refund",
    "advanced_haki": "Advanced Haki bounty cost",
    "fruit_bad": "Bad fruit purchase",
    "fruit_medium": "Medium fruit purchase",
    "fruit_good": "Good fruit purchase",
    "fruit_refund_bad": "Bad fruit sell refund",
    "fruit_refund_medium": "Medium fruit sell refund",
    "fruit_refund_good": "Good fruit sell refund",
    "shield_1": "Shield Lv.1",
    "shield_2": "Shield Lv.2",
    "shield_3": "Shield Lv.3",
    "vault_2": "Vault Lv.2 upgrade",
    "vault_3": "Vault Lv.3 upgrade",
    "xp_boost": "2x XP boost",
    "rod_wooden": "Wooden fishing rod",
    "rod_steel": "Steel fishing rod",
    "rod_diamond": "Diamond fishing rod",
    "rod_mythical": "Mythical fishing rod",
    "bait_basic": "Basic bait",
    "bait_steel": "Steel bait",
    "bait_diamond": "Diamond bait",
    "bait_mythical": "Mythical bait",
    "crew_create": "Crew creation",
    "crew_image_change": "Crew image change",
    "ship_1": "Dinghy (Tier 1)",
    "ship_2": "Caravel (Tier 2)",
    "ship_3": "Brigantine (Tier 3)",
    "ship_4": "Galleon (Tier 4)",
    "ship_5": "Man-o'-War (Tier 5)",
    "ship_6": "Thousand Sunny (Tier 6)",
    "fish_sardine_min": "Sardine sale minimum",
    "fish_sardine_max": "Sardine sale maximum",
    "fish_blue_tang_min": "Blue Tang sale minimum",
    "fish_blue_tang_max": "Blue Tang sale maximum",
    "fish_tuna_min": "Tuna sale minimum",
    "fish_tuna_max": "Tuna sale maximum",
    "fish_salmon_min": "Salmon sale minimum",
    "fish_salmon_max": "Salmon sale maximum",
    "fish_swordfish_min": "Swordfish sale minimum",
    "fish_swordfish_max": "Swordfish sale maximum",
    "fish_golden_koi_min": "Golden Koi sale minimum",
    "fish_golden_koi_max": "Golden Koi sale maximum",
    "fish_sea_king_fish_min": "Sea King Fish sale minimum",
    "fish_sea_king_fish_max": "Sea King Fish sale maximum",
}

_lock = threading.RLock()
_loaded = False
_overrides = {}


def _load():
    global _loaded, _overrides
    with _lock:
        if _loaded:
            return
        try:
            with open(PRICE_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                _overrides = {
                    str(k).strip().lower(): int(v)
                    for k, v in data.items()
                    if str(k).strip().lower() in PRICE_DEFAULTS
                    and isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0
                }
        except (FileNotFoundError, OSError, ValueError, TypeError):
            _overrides = {}
        _loaded = True


def _save():
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".price_overrides_", suffix=".tmp", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(_overrides, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(temp_path, PRICE_FILE)
        return True
    except OSError:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        return False


def normalize_price_key(key):
    return re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")


def get_price(key, default=None):
    normalized = normalize_price_key(key)
    if normalized not in PRICE_DEFAULTS:
        return default
    _load()
    return int(_overrides.get(normalized, PRICE_DEFAULTS[normalized] if default is None else default))


def set_price(key, amount):
    normalized = normalize_price_key(key)
    if normalized not in PRICE_DEFAULTS:
        return False
    try:
        amount = int(amount)
    except (TypeError, ValueError, OverflowError):
        return False
    if amount < 0:
        return False
    _load()
    with _lock:
        if normalized.endswith("_min"):
            companion = normalized[:-4] + "_max"
            if amount > get_price(companion):
                return False
        elif normalized.endswith("_max"):
            companion = normalized[:-4] + "_min"
            if amount < get_price(companion):
                return False
        old = _overrides.get(normalized)
        _overrides[normalized] = amount
        if _save():
            return True
        if old is None:
            _overrides.pop(normalized, None)
        else:
            _overrides[normalized] = old
        return False


def list_prices():
    _load()
    return [(key, PRICE_LABELS.get(key, key.replace("_", " ").title()), get_price(key)) for key in PRICE_DEFAULTS]


def reload_prices():
    """Reload overrides after a JSON restore operation."""
    global _loaded, _overrides
    with _lock:
        _loaded = False
        _overrides = {}
    _load()


def get_fruit_price(category):
    key = {"bad": "fruit_bad", "medium": "fruit_medium", "good": "fruit_good"}.get(str(category).strip().lower())
    return get_price(key) if key else 0


def get_fruit_refund(category):
    key = {"bad": "fruit_refund_bad", "medium": "fruit_refund_medium", "good": "fruit_refund_good"}.get(str(category).strip().lower())
    return get_price(key) if key else 0


def get_fishing_price(kind, item_key):
    return get_price(f"{str(kind).strip().lower()}_{str(item_key).strip().lower()}")


def get_fish_price_range(name):
    base = normalize_price_key(f"fish_{name}")
    return get_price(f"{base}_min"), get_price(f"{base}_max")


def get_ship_price(tier, default=None):
    return get_price(f"ship_{int(tier)}", default)


def parse_price_amount(text):
    value = str(text or "").strip().replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmbt]?)", value, re.IGNORECASE)
    if not match:
        return None
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000}
    try:
        result = int(Decimal(match.group(1)) * multiplier[match.group(2).lower()])
    except (InvalidOperation, ValueError, OverflowError):
        return None
    return result if result >= 0 else None
