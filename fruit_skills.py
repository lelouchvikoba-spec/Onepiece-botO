"""World Boss active skills for the catalogued Devil Fruits.

Each multiplier is applied to the player's normal calculated /battle damage.
The resulting skill attack replaces the normal hit and is greater than it.
"""

FRUIT_SKILLS = {
    # Good fruits
    "Hito Hito no Mi, Model: Nika": {"name": "Bajrang Gun", "multiplier": 2.40},
    "Gura Gura no Mi": {"name": "Quake Punch", "multiplier": 2.30},
    "Yami Yami no Mi": {"name": "Black Hole", "multiplier": 2.20},
    "Ope Ope no Mi": {"name": "Gamma Knife", "multiplier": 2.15},
    "Magu Magu no Mi": {"name": "Great Eruption", "multiplier": 2.20},
    "Pika Pika no Mi": {"name": "Yata Mirror Barrage", "multiplier": 2.15},
    "Uo Uo no Mi, Model: Seiryu": {"name": "Blast Breath", "multiplier": 2.10},
    "Goro Goro no Mi": {"name": "El Thor", "multiplier": 2.00},
    "Mori Mori no Mi": {"name": "Forest Vines", "multiplier": 1.90},
    "Hie Hie no Mi": {"name": "Ice Age", "multiplier": 1.90},
    "Zushi Zushi no Mi": {"name": "Meteor Press", "multiplier": 2.10},
    "Nikyu Nikyu no Mi": {"name": "Ursus Shock", "multiplier": 2.10},
    "Tori Tori no Mi, Model: Phoenix": {"name": "Phoenix Flame Claw", "multiplier": 2.00},
    "Soru Soru no Mi": {"name": "Soul Pocus", "multiplier": 1.95},
    "Hito Hito no Mi, Model: Daibutsu": {"name": "Golden Shockwave", "multiplier": 2.15},
    "Doku Doku no Mi": {"name": "Venom Demon", "multiplier": 2.30},
    "Ito Ito no Mi": {"name": "God Thread", "multiplier": 2.00},
    "Mochi Mochi no Mi": {"name": "Mochi Thrust", "multiplier": 1.95},
    "Toshi Toshi no Mi": {"name": "Age Breaker", "multiplier": 1.90},
    "Gasu Gasu no Mi": {"name": "Gas Robe Burst", "multiplier": 2.00},
    "Inu Inu no Mi, Model: Okuchi no Makami": {"name": "Ice Fang", "multiplier": 2.00},
    "Hebi Hebi no Mi, Model: Yamata no Orochi": {"name": "Eight-Headed Strike", "multiplier": 2.10},
    "Zou Zou no Mi, Model: Mammoth": {"name": "Mammoth Stampede", "multiplier": 2.00},
    "Ryu Ryu no Mi, Model: Pteranodon": {"name": "Pteranodon Dive Bomb", "multiplier": 1.90},
    "Ryu Ryu no Mi, Model: Brachiosaurus": {"name": "Brachio Bomber", "multiplier": 2.00},
    "Kumo Kumo no Mi, Model: Rosamygale Grauvogeli": {"name": "Spider Web Crush", "multiplier": 1.85},

    # Medium fruits
    "Gomu Gomu no Mi": {"name": "Gum-Gum Gatling", "multiplier": 2.00},
    "Mera Mera no Mi": {"name": "Fire Fist", "multiplier": 2.05},
    "Hana Hana no Mi": {"name": "Gigantesco Mano", "multiplier": 1.85},
    "Bari Bari no Mi": {"name": "Barrier Smash", "multiplier": 1.80},
    "Jiki Jiki no Mi": {"name": "Punk Rotten Strike", "multiplier": 2.00},
    "Kage Kage no Mi": {"name": "Shadow Asgard", "multiplier": 2.05},
    "Horu Horu no Mi": {"name": "Hormone Burst", "multiplier": 1.80},
    "Mero Mero no Mi": {"name": "Slave Arrow", "multiplier": 2.05},
    "Buki Buki no Mi": {"name": "Missile Barrage", "multiplier": 1.95},
    "Suna Suna no Mi": {"name": "Desert Spada", "multiplier": 2.00},
    "Noro Noro no Mi": {"name": "Slow Beam Burst", "multiplier": 1.85},
    "Suke Suke no Mi": {"name": "Invisible Ambush", "multiplier": 1.80},
    "Doa Doa no Mi": {"name": "Air Door Assault", "multiplier": 1.85},
    "Fuwa Fuwa no Mi": {"name": "Thousand-Brick Fist", "multiplier": 2.00},
    "Hobi Hobi no Mi": {"name": "Toy Soldier Onslaught", "multiplier": 1.80},
    "Mira Mira no Mi": {"name": "Mirror World Counter", "multiplier": 1.90},
    "Bisu Bisu no Mi": {"name": "Biscuit Soldier Barrage", "multiplier": 2.00},
    "Pero Pero no Mi": {"name": "Candy Wall Crush", "multiplier": 1.95},
    "Chiyu Chiyu no Mi": {"name": "Healing Shock", "multiplier": 1.80},
    "Wara Wara no Mi": {"name": "Straw Doll Curse", "multiplier": 1.90},
    "Guru Guru no Mi": {"name": "Spin Drill", "multiplier": 1.85},
    "Bomu Bomu no Mi": {"name": "Bomu Bomu Burst", "multiplier": 2.00},
    "Kilo Kilo no Mi": {"name": "Thousand-Kilo Drop", "multiplier": 1.85},
    "Moku Moku no Mi": {"name": "White Blow", "multiplier": 1.95},
    "Yomi Yomi no Mi": {"name": "Soul Solid", "multiplier": 1.95},
    "Kira Kira no Mi": {"name": "Diamond Fist", "multiplier": 1.85},
    "Mato Mato no Mi": {"name": "Homing Shot", "multiplier": 1.90},
    "Oto Oto no Mi": {"name": "Symphony Strike", "multiplier": 2.00},
    "Awa Awa no Mi": {"name": "Soap Sheep", "multiplier": 1.80},
    "Kama Kama no Mi": {"name": "Razor Wind", "multiplier": 1.95},

    # Bad fruits
    "Jake Jake no Mi": {"name": "Jacket Kick", "multiplier": 1.65},
    "Pamu Pamu no Mi": {"name": "Pop Grenade", "multiplier": 1.70},
    "Ton Ton no Mi": {"name": "Heavy Press", "multiplier": 1.70},
    "Hira Hira no Mi": {"name": "Fluttering Blade", "multiplier": 1.65},
    "Ishi Ishi no Mi": {"name": "Stone Breaker", "multiplier": 1.70},
    "Fude Fude no Mi": {"name": "Ink Dragon", "multiplier": 1.75},
    "Nagi Nagi no Mi": {"name": "Silent Burst", "multiplier": 1.65},
    "Kuri Kuri no Mi": {"name": "Cream Cannon", "multiplier": 1.60},
    "Bata Bata no Mi": {"name": "Butter Bomb", "multiplier": 1.60},
    "Buku Buku no Mi": {"name": "Book Prison", "multiplier": 1.65},
    "Kuku Kuku no Mi": {"name": "Cooking Skewer", "multiplier": 1.60},
    "Gocha Gocha no Mi": {"name": "Mega Combo", "multiplier": 1.75},
    "Shiku Shiku no Mi": {"name": "Sickly Curse", "multiplier": 1.65},
    "Wapu Wapu no Mi": {"name": "Warp Strike", "multiplier": 1.75},
    "Riki Riki no Mi": {"name": "Muscle Punch", "multiplier": 1.70},
    "Nomi Nomi no Mi": {"name": "Brain Surge", "multiplier": 1.70},
    "Gabu Gabu no Mi": {"name": "Drink-Fueled Smash", "multiplier": 1.60},
    "Tsutsu Tsutsu no Mi": {"name": "Cannon Blast", "multiplier": 1.70},
    "Muchi Muchi no Mi": {"name": "Whip Lash", "multiplier": 1.65},
    "Nori Nori no Mi": {"name": "Sailboard Ram", "multiplier": 1.60},
}

_SKILL_LOOKUP = {name.casefold(): profile for name, profile in FRUIT_SKILLS.items()}


def get_fruit_skill(fruit_name):
    """Return a fruit-specific World Boss skill, or None for an unknown fruit."""
    if not fruit_name:
        return None
    normalized = " ".join(str(fruit_name).split()).casefold()
    return _SKILL_LOOKUP.get(normalized)


# PvP-only selectable attacks are kept separate from the once-per-raid World
# Boss skill above. The catalog is populated with three moves per fruit except
# Nika and Ope, whose bespoke move systems remain unchanged.
PVP_FRUIT_SKILLS = {'Gura Gura no Mi': [{'name': 'Quake Punch', 'multiplier': 2.3},
                     {'name': 'Gekishin (Quake)', 'multiplier': 2.18},
                     {'name': 'Shima Yurashi (Island Shake)', 'multiplier': 2.53}],
 'Yami Yami no Mi': [{'name': 'Black Hole', 'multiplier': 2.2},
                     {'name': 'Liberation', 'multiplier': 2.09},
                     {'name': 'Kurouzu', 'multiplier': 2.42}],
 'Magu Magu no Mi': [{'name': 'Great Eruption', 'multiplier': 2.2},
                     {'name': 'Ryusei Kazan', 'multiplier': 2.09},
                     {'name': 'Meigo', 'multiplier': 2.42}],
 'Pika Pika no Mi': [{'name': 'Yata Mirror Barrage', 'multiplier': 2.15},
                     {'name': 'Ama no Murakumo', 'multiplier': 2.04},
                     {'name': 'Yasakani no Magatama', 'multiplier': 2.37}],
 'Uo Uo no Mi, Model: Seiryu': [{'name': 'Blast Breath', 'multiplier': 2.1},
                                {'name': 'Karyū: Kaen Hakke', 'multiplier': 1.99},
                                {'name': 'Ragnaraku', 'multiplier': 2.31}],
 'Goro Goro no Mi': [{'name': 'El Thor', 'multiplier': 2.0},
                     {'name': '30,000,000 Volt Hino', 'multiplier': 1.9},
                     {'name': '200,000,000 Volt Amaru', 'multiplier': 2.2}],
 'Mori Mori no Mi': [{'name': 'Forest Vines', 'multiplier': 1.9},
                     {'name': 'Mori no Mi: Mori no Kyojin', 'multiplier': 1.8},
                     {'name': 'Sakuranman: Kenzan no Mori', 'multiplier': 2.09}],
 'Hie Hie no Mi': [{'name': 'Ice Age', 'multiplier': 1.9},
                   {'name': 'Ice Block: Partisan', 'multiplier': 1.8},
                   {'name': 'Ice Time', 'multiplier': 2.09}],
 'Zushi Zushi no Mi': [{'name': 'Meteor Press', 'multiplier': 2.1},
                       {'name': 'Gravity Blade: Raging Tiger', 'multiplier': 1.99},
                       {'name': 'Gravity Press', 'multiplier': 2.31}],
 'Nikyu Nikyu no Mi': [{'name': 'Ursus Shock', 'multiplier': 2.1},
                       {'name': 'Pad Ho (Pressure Cannon)', 'multiplier': 1.99},
                       {'name': 'Tartarus', 'multiplier': 2.31}],
 'Tori Tori no Mi, Model: Phoenix': [{'name': 'Phoenix Flame Claw', 'multiplier': 2.0},
                                     {'name': 'Bluebird Strike', 'multiplier': 1.9},
                                     {'name': 'Phoenix Brand', 'multiplier': 2.2}],
 'Soru Soru no Mi': [{'name': 'Soul Pocus', 'multiplier': 1.95},
                     {'name': 'Heavenly Fire: Prometheus', 'multiplier': 1.85},
                     {'name': 'Ikoku Sovereignty', 'multiplier': 2.15}],
 'Hito Hito no Mi, Model: Daibutsu': [{'name': 'Golden Shockwave', 'multiplier': 2.15},
                                      {'name': 'Shockwave Palm', 'multiplier': 2.04},
                                      {'name': 'Golden Buddha Stomp', 'multiplier': 2.37}],
 'Doku Doku no Mi': [{'name': 'Venom Demon', 'multiplier': 2.3},
                     {'name': 'Venom Road', 'multiplier': 2.18},
                     {'name': 'Venom Demon: Jigoku no Shinpan', 'multiplier': 2.53}],
 'Ito Ito no Mi': [{'name': 'God Thread', 'multiplier': 2.0},
                   {'name': 'Parasite', 'multiplier': 1.9},
                   {'name': 'Black Knight', 'multiplier': 2.2}],
 'Mochi Mochi no Mi': [{'name': 'Mochi Thrust', 'multiplier': 1.95},
                       {'name': 'Kagami Mochi', 'multiplier': 1.85},
                       {'name': 'Mochi Tsuki', 'multiplier': 2.15}],
 'Toshi Toshi no Mi': [{'name': 'Age Breaker', 'multiplier': 1.9},
                       {'name': 'Youthful Impact', 'multiplier': 1.8},
                       {'name': 'Distorted Future: Giant Form', 'multiplier': 2.09}],
 'Gasu Gasu no Mi': [{'name': 'Gas Robe Burst', 'multiplier': 2.0},
                     {'name': 'Shinokuni', 'multiplier': 1.9},
                     {'name': 'Gastanet', 'multiplier': 2.2}],
 'Inu Inu no Mi, Model: Okuchi no Makami': [{'name': 'Ice Fang', 'multiplier': 2.0},
                                            {'name': 'Narikabura Arrow', 'multiplier': 1.9},
                                            {'name': 'Divine Switchover', 'multiplier': 2.2}],
 'Hebi Hebi no Mi, Model: Yamata no Orochi': [{'name': 'Eight-Headed Strike', 'multiplier': 2.1},
                                              {'name': 'Yamata no Orochi: Eight-Headed Bite',
                                               'multiplier': 1.99},
                                              {'name': 'Orochi Serpent Coil', 'multiplier': 2.31}],
 'Zou Zou no Mi, Model: Mammoth': [{'name': 'Mammoth Stampede', 'multiplier': 2.0},
                                   {'name': 'Karyudon', 'multiplier': 1.9},
                                   {'name': 'Elephant Gun', 'multiplier': 2.2}],
 'Ryu Ryu no Mi, Model: Pteranodon': [{'name': 'Pteranodon Dive Bomb', 'multiplier': 1.9},
                                      {'name': 'Pteranodon Wing Guillotine', 'multiplier': 1.8},
                                      {'name': 'Pteranodon Talon Rake', 'multiplier': 2.09}],
 'Ryu Ryu no Mi, Model: Brachiosaurus': [{'name': 'Brachio Bomber', 'multiplier': 2.0},
                                         {'name': 'Brachio Snake', 'multiplier': 1.9},
                                         {'name': 'Brachio Bomber Feint', 'multiplier': 2.2}],
 'Kumo Kumo no Mi, Model: Rosamygale Grauvogeli': [{'name': 'Spider Web Crush', 'multiplier': 1.85},
                                                   {'name': 'Grauvogeli Venomous Pounce',
                                                    'multiplier': 1.76},
                                                   {'name': 'Spider Net Trap', 'multiplier': 2.04}],
 'Gomu Gomu no Mi': [{'name': 'Gum-Gum Gatling', 'multiplier': 1.75},
                     {'name': 'Gum-Gum Bazooka', 'multiplier': 1.66},
                     {'name': 'Gum-Gum Battle Axe', 'multiplier': 1.93},
                     {'name': 'Gomu Gomu no Thor Elephant Gun', 'multiplier': 2.15},
                     {'name': 'Gomu Gomu no Jet Gatling', 'multiplier': 2.05}],
 'Mera Mera no Mi': [{'name': 'Fire Fist', 'multiplier': 1.8},
                     {'name': 'Hiken: Homurasaki', 'multiplier': 1.71},
                     {'name': 'Flame Emperor', 'multiplier': 1.98}],
 'Hana Hana no Mi': [{'name': 'Gigantesco Mano', 'multiplier': 1.6},
                     {'name': 'Cien Fleur: Delphinium', 'multiplier': 1.52},
                     {'name': 'Seis Fleur: Slap', 'multiplier': 1.76}],
 'Bari Bari no Mi': [{'name': 'Barrier Smash', 'multiplier': 1.55},
                     {'name': 'Barrier Ball', 'multiplier': 1.47},
                     {'name': 'Barrier Crash', 'multiplier': 1.71}],
 'Jiki Jiki no Mi': [{'name': 'Punk Rotten Strike', 'multiplier': 1.75},
                     {'name': 'Punk Gibson', 'multiplier': 1.66},
                     {'name': 'Punk Clash', 'multiplier': 1.93}],
 'Kage Kage no Mi': [{'name': 'Shadow Asgard', 'multiplier': 1.8},
                     {'name': 'Brick Bat Swarm', 'multiplier': 1.71},
                     {'name': "Shadow's Asgardian Grip", 'multiplier': 1.98}],
 'Horu Horu no Mi': [{'name': 'Hormone Burst', 'multiplier': 1.55},
                     {'name': 'Hormone Shot: Adrenaline', 'multiplier': 1.47},
                     {'name': 'Death Wink', 'multiplier': 1.71}],
 'Mero Mero no Mi': [{'name': 'Slave Arrow', 'multiplier': 1.8},
                     {'name': 'Pistol Kiss', 'multiplier': 1.71},
                     {'name': 'Mero Mero Mellow', 'multiplier': 1.98}],
 'Buki Buki no Mi': [{'name': 'Missile Barrage', 'multiplier': 1.7},
                     {'name': 'Arms Shield', 'multiplier': 1.61},
                     {'name': 'Missile Kick', 'multiplier': 1.87}],
 'Suna Suna no Mi': [{'name': 'Desert Spada', 'multiplier': 1.75},
                     {'name': 'Sables: Pesado Espada', 'multiplier': 1.66},
                     {'name': 'Ground Secco', 'multiplier': 1.93}],
 'Noro Noro no Mi': [{'name': 'Slow Beam Burst', 'multiplier': 1.6},
                     {'name': 'Noro Noro Beam Sword', 'multiplier': 1.52},
                     {'name': 'Noroma Photon Net', 'multiplier': 1.76}],
 'Suke Suke no Mi': [{'name': 'Invisible Ambush', 'multiplier': 1.55},
                     {'name': 'Transparent Black Knight', 'multiplier': 1.47},
                     {'name': 'Vanishing Blade Feint', 'multiplier': 1.71}],
 'Doa Doa no Mi': [{'name': 'Air Door Assault', 'multiplier': 1.6},
                   {'name': 'Door Door: Air Door', 'multiplier': 1.52},
                   {'name': 'Door Door: Doorway Feint', 'multiplier': 1.76}],
 'Fuwa Fuwa no Mi': [{'name': 'Thousand-Brick Fist', 'multiplier': 1.75},
                     {'name': 'Fuwwa-Fuwa: Skywalk Slam', 'multiplier': 1.66},
                     {'name': 'Floating Island: Debris Barrage', 'multiplier': 1.93}],
 'Hobi Hobi no Mi': [{'name': 'Toy Soldier Onslaught', 'multiplier': 1.55},
                     {'name': 'Hobby-Hobby Fruit: Toy Transformation', 'multiplier': 1.47},
                     {'name': 'Hobby-Hobby Fruit: Forgotten Contract', 'multiplier': 1.71}],
 'Mira Mira no Mi': [{'name': 'Mirror World Counter', 'multiplier': 1.65},
                     {'name': 'Mirror Doppelgänger', 'multiplier': 1.57},
                     {'name': 'Mirror Road Ambush', 'multiplier': 1.81}],
 'Bisu Bisu no Mi': [{'name': 'Biscuit Soldier Barrage', 'multiplier': 1.75},
                     {'name': 'Cracker Cracker — Pretzel Roll', 'multiplier': 1.66},
                     {'name': 'Biscuit Soldier Shield Bash', 'multiplier': 1.93}],
 'Pero Pero no Mi': [{'name': 'Candy Wall Crush', 'multiplier': 1.7},
                     {'name': 'Candy Maiden', 'multiplier': 1.61},
                     {'name': 'Candy Escalator: Candy Slug', 'multiplier': 1.87}],
 'Chiyu Chiyu no Mi': [{'name': 'Healing Shock', 'multiplier': 1.55},
                       {'name': 'Tact: Green Room', 'multiplier': 1.47},
                       {'name': 'Healing Water Whip', 'multiplier': 1.71}],
 'Wara Wara no Mi': [{'name': 'Straw Doll Curse', 'multiplier': 1.65},
                     {'name': "Straw Man's Curse", 'multiplier': 1.57},
                     {'name': 'Mil Fleurs: Straw Reaper', 'multiplier': 1.81}],
 'Guru Guru no Mi': [{'name': 'Spin Drill', 'multiplier': 1.6},
                     {'name': 'Rotor Whirlwind', 'multiplier': 1.52},
                     {'name': 'Cyclone Corkscrew Rush', 'multiplier': 1.76}],
 'Bomu Bomu no Mi': [{'name': 'Bomu Bomu Burst', 'multiplier': 1.75},
                     {'name': "Kaneshiro's Nose Fancy Cannon", 'multiplier': 1.66},
                     {'name': 'Bomu Bomu no Mi: Exploding Fist', 'multiplier': 1.93}],
 'Kilo Kilo no Mi': [{'name': 'Thousand-Kilo Drop', 'multiplier': 1.6},
                     {'name': 'Ten-Thousand-Kilo Guillotine', 'multiplier': 1.52},
                     {'name': 'Kilo-Kilo Sky Step', 'multiplier': 1.76}],
 'Moku Moku no Mi': [{'name': 'White Blow', 'multiplier': 1.7},
                     {'name': 'White Launcher', 'multiplier': 1.61},
                     {'name': 'White Out', 'multiplier': 1.87}],
 'Yomi Yomi no Mi': [{'name': 'Soul Solid', 'multiplier': 1.7},
                     {'name': 'Soul Parade: Ice Burn', 'multiplier': 1.61},
                     {'name': 'Soul King’s Requiem', 'multiplier': 1.87}],
 'Kira Kira no Mi': [{'name': 'Diamond Fist', 'multiplier': 1.6},
                     {'name': 'Diamond Jozu: Brilliant Punk', 'multiplier': 1.52},
                     {'name': 'Diamond Guard Counter', 'multiplier': 1.76}],
 'Mato Mato no Mi': [{'name': 'Homing Shot', 'multiplier': 1.65},
                     {'name': 'Marking Shot', 'multiplier': 1.57},
                     {'name': 'Homing Spear Volley', 'multiplier': 1.81}],
 'Oto Oto no Mi': [{'name': 'Symphony Strike', 'multiplier': 1.75},
                   {'name': 'Impact Dial Symphony', 'multiplier': 1.66},
                   {'name': 'Sound World: Resonance Cage', 'multiplier': 1.93}],
 'Awa Awa no Mi': [{'name': 'Soap Sheep', 'multiplier': 1.55},
                   {'name': 'Golden Hour', 'multiplier': 1.47},
                   {'name': 'Bubble Cycle', 'multiplier': 1.71}],
 'Kama Kama no Mi': [{'name': 'Razor Wind', 'multiplier': 1.7},
                     {'name': 'Kamakiri (Sickle Wind)', 'multiplier': 1.61},
                     {'name': 'Crescent Reaper Gale', 'multiplier': 1.87}],
 'Jake Jake no Mi': [{'name': 'Jacket Kick', 'multiplier': 1.4},
                     {'name': 'Jacket Possession: Iron Fist', 'multiplier': 1.33},
                     {'name': 'Jacket Possession: Suplex', 'multiplier': 1.54}],
 'Pamu Pamu no Mi': [{'name': 'Pop Grenade', 'multiplier': 1.45},
                     {'name': 'Pamu Pamu no Mi: Renketsu Bakudan', 'multiplier': 1.38},
                     {'name': 'Pamu Pamu no Mi: Bakuretsu Palm', 'multiplier': 1.59}],
 'Ton Ton no Mi': [{'name': 'Heavy Press', 'multiplier': 1.45},
                   {'name': '10,000-Ton Guillotine', 'multiplier': 1.38},
                   {'name': 'Weight-Shift Meteor Drop', 'multiplier': 1.59}],
 'Hira Hira no Mi': [{'name': 'Fluttering Blade', 'multiplier': 1.4},
                     {'name': 'Fold-Fold Crescent', 'multiplier': 1.33},
                     {'name': 'Iron Flag Snare', 'multiplier': 1.54}],
 'Ishi Ishi no Mi': [{'name': 'Stone Breaker', 'multiplier': 1.45},
                     {'name': 'Stone Swallow', 'multiplier': 1.38},
                     {'name': 'Stone Giant Fist', 'multiplier': 1.59}],
 'Fude Fude no Mi': [{'name': 'Ink Dragon', 'multiplier': 1.5},
                     {'name': 'Ink Bird', 'multiplier': 1.42},
                     {'name': 'Ink Tiger', 'multiplier': 1.65}],
 'Nagi Nagi no Mi': [{'name': 'Silent Burst', 'multiplier': 1.4},
                     {'name': 'Silent Scythe', 'multiplier': 1.33},
                     {'name': 'Silent Room: Ambush', 'multiplier': 1.54}],
 'Kuri Kuri no Mi': [{'name': 'Cream Cannon', 'multiplier': 1.35},
                     {'name': 'Creamy Net', 'multiplier': 1.28},
                     {'name': 'Cream Drill', 'multiplier': 1.49}],
 'Bata Bata no Mi': [{'name': 'Butter Bomb', 'multiplier': 1.35},
                     {'name': 'Butter Cutter', 'multiplier': 1.28},
                     {'name': 'Butter Slide Slam', 'multiplier': 1.49}],
 'Buku Buku no Mi': [{'name': 'Book Prison', 'multiplier': 1.4},
                     {'name': 'Book World: Fortress of Fiction', 'multiplier': 1.33},
                     {'name': 'Illustrated Page Barrage', 'multiplier': 1.54}],
 'Kuku Kuku no Mi': [{'name': 'Cooking Skewer', 'multiplier': 1.35},
                     {'name': 'Gourmet Cooking: Roast Feast', 'multiplier': 1.28},
                     {'name': 'Food Chain: Banquet Barrage', 'multiplier': 1.49}],
 'Gocha Gocha no Mi': [{'name': 'Mega Combo', 'multiplier': 1.5},
                       {'name': 'Gocha Fusion: Iron Fist', 'multiplier': 1.42},
                       {'name': 'Gocha Fusion: Cannon Volley', 'multiplier': 1.65}],
 'Shiku Shiku no Mi': [{'name': 'Sickly Curse', 'multiplier': 1.4},
                       {'name': 'Disease Spread', 'multiplier': 1.33},
                       {'name': 'Contagion Cloud', 'multiplier': 1.54}],
 'Wapu Wapu no Mi': [{'name': 'Warp Strike', 'multiplier': 1.5},
                     {'name': 'Warp Gate Feint', 'multiplier': 1.42},
                     {'name': 'Warp-Swapped Slam', 'multiplier': 1.65}],
 'Riki Riki no Mi': [{'name': 'Muscle Punch', 'multiplier': 1.45},
                     {'name': 'Muscle Crush', 'multiplier': 1.38},
                     {'name': 'Champion Suplex', 'multiplier': 1.59}],
 'Nomi Nomi no Mi': [{'name': 'Brain Surge', 'multiplier': 1.45},
                     {'name': 'Memory Cache Counter', 'multiplier': 1.38},
                     {'name': 'Punk Records Pulse', 'multiplier': 1.59}],
 'Gabu Gabu no Mi': [{'name': 'Drink-Fueled Smash', 'multiplier': 1.35},
                     {'name': "Drunken Brawler's Flurry", 'multiplier': 1.28},
                     {'name': 'Sake-Foam Blast', 'multiplier': 1.49}],
 'Tsutsu Tsutsu no Mi': [{'name': 'Cannon Blast', 'multiplier': 1.45},
                         {'name': 'Cannon Blast Barrage', 'multiplier': 1.38},
                         {'name': 'Grapeshot Salvo', 'multiplier': 1.59}],
 'Muchi Muchi no Mi': [{'name': 'Whip Lash', 'multiplier': 1.4},
                       {'name': 'Muchi Muchi no Mi: Muchi Goyō (Whip Five Leaves)',
                        'multiplier': 1.33},
                       {'name': 'Seraphim Lash Snare', 'multiplier': 1.54}],
 'Nori Nori no Mi': [{'name': 'Sailboard Ram', 'multiplier': 1.35},
                     {'name': 'Deckside Drift Crash', 'multiplier': 1.28},
                     {'name': 'Boarding Run-Down', 'multiplier': 1.49}],
 'Hito Hito no Mi, Model: Nika': [{'name': 'Red Hawk', 'multiplier': 1.65},
                                {'name': 'Elephant Gatling', 'multiplier': 1.90}],
 'Ope Ope no Mi': [{'name': 'Shambles', 'multiplier': 1.45},
                   {'name': 'Gamma Knife', 'multiplier': 1.95}]}
_PVP_SKILL_LOOKUP = {" ".join(name.split()).casefold(): moves for name, moves in PVP_FRUIT_SKILLS.items()}


FRUIT_AWAKENED_PVP_SKILLS = {
    "Ito Ito no Mi": [
        {"name": "Off White", "multiplier": 2.30},
        {"name": "Flap Thread", "multiplier": 2.55},
    ],
    "Mochi Mochi no Mi": [
        {"name": "Chikara Mochi", "multiplier": 2.25},
        {"name": "Mochi Ginkaku", "multiplier": 2.50},
    ],
    "Jiki Jiki no Mi": [
        {"name": "Punk Corna Dio", "multiplier": 2.30},
        {"name": "Damned Punk", "multiplier": 2.55},
    ],
    # This catalog entry is intentionally separate from Hito Hito no Mi, Model: Nika.
    "Gomu Gomu no Mi": [
        {"name": "Gomu Gomu no King Cobra", "multiplier": 2.40},
        {"name": "Gomu Gomu no Black Mamba", "multiplier": 2.50},
        {"name": "Gomu Gomu no Jet Culverin", "multiplier": 2.35},
    ],
    "Hito Hito no Mi, Model: Nika": [
        {"name": "Bajrang Gun", "multiplier": 2.45},
        {"name": "Kaminari", "multiplier": 2.30},
    ],
    "Ope Ope no Mi": [
        {"name": "K-Room (Tact)", "multiplier": 2.25},
        {"name": "Shock Wille", "multiplier": 2.50},
    ],
}

FRUIT_AWAKENED_WORLD_BOSS_SKILLS = {
    "Ito Ito no Mi": {
        "offwhite": {"name": "Off White", "multiplier": 5.0},
        "flapthread": {"name": "Flap Thread", "multiplier": 6.0},
    },
    "Mochi Mochi no Mi": {
        "chikaramochi": {"name": "Chikara Mochi", "multiplier": 5.0},
        "mochiginkaku": {"name": "Mochi Ginkaku", "multiplier": 6.0},
    },
    "Jiki Jiki no Mi": {
        "punkcornadio": {"name": "Assign: Punk Corna Dio", "multiplier": 5.0},
        "damnedpunk": {"name": "Assign: Damned Punk", "multiplier": 6.0},
    },
    "Gomu Gomu no Mi": {
        "kingcobra": {"name": "Gomu Gomu no King Cobra", "multiplier": 6.0},
        "blackmamba": {"name": "Gomu Gomu no Black Mamba", "multiplier": 5.5},
        "jetculverin": {"name": "Gomu Gomu no Jet Culverin", "multiplier": 5.0},
    },
}

FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS = {
    "Gomu Gomu no Mi": {
        "thorelephantgun": {"name": "Gomu Gomu no Thor Elephant Gun", "multiplier": 2.75},
        "jetgatling": {"name": "Gomu Gomu no Jet Gatling", "multiplier": 2.4},
    },
}

_FRUIT_AWAKENING_STATE_KEYS = {
    "ito ito no mi": "ito",
    "mochi mochi no mi": "mochi",
    "jiki jiki no mi": "jiki",
    "gomu gomu no mi": "gomu",
}
_AWAKENED_PVP_SKILL_LOOKUP = {
    " ".join(name.split()).casefold(): moves
    for name, moves in FRUIT_AWAKENED_PVP_SKILLS.items()
}
_AWAKENED_BOSS_SKILL_LOOKUP = {
    " ".join(name.split()).casefold(): moves
    for name, moves in FRUIT_AWAKENED_WORLD_BOSS_SKILLS.items()
}
_PRE_AWAKENED_BOSS_SKILL_LOOKUP = {
    " ".join(name.split()).casefold(): moves
    for name, moves in FRUIT_PRE_AWAKENED_WORLD_BOSS_SKILLS.items()
}


def get_fruit_awakening_key(fruit_name):
    """Return the persistent timer prefix for a supported special awakening."""
    if not fruit_name:
        return None
    normalized = " ".join(str(fruit_name).split()).casefold()
    return _FRUIT_AWAKENING_STATE_KEYS.get(normalized)


def get_awakened_world_boss_skill(fruit_name, move_key):
    """Return an awakened World Boss spell for the matching fruit and command."""
    if not fruit_name or not move_key:
        return None
    normalized = " ".join(str(fruit_name).split()).casefold()
    skill = _AWAKENED_BOSS_SKILL_LOOKUP.get(normalized, {}).get(str(move_key).casefold())
    return dict(skill) if skill else None


def get_pre_awakened_world_boss_skill(fruit_name, move_key):
    """Return a base-form World Boss spell (currently for Gomu Gomu no Mi)."""
    if not fruit_name or not move_key:
        return None
    normalized = " ".join(str(fruit_name).split()).casefold()
    skill = _PRE_AWAKENED_BOSS_SKILL_LOOKUP.get(normalized, {}).get(str(move_key).casefold())
    return dict(skill) if skill else None


def get_pvp_fruit_skills(fruit_name, awakened=False):
    """Return selectable PvP Fruit moves without altering the World Boss skill."""
    if not fruit_name:
        return []
    normalized = " ".join(str(fruit_name).split()).casefold()
    if awakened:
        awakened_moves = _AWAKENED_PVP_SKILL_LOOKUP.get(normalized)
        if awakened_moves:
            return [dict(move) for move in awakened_moves]
    return _PVP_SKILL_LOOKUP.get(normalized, [])


def get_extra_fruit_spell_map():
    """Build two extra direct-spell commands for fruits with a single base spell.

    Nika and Ope have bespoke multi-command systems, while Gomu already has
    two dedicated pre-Snakeman standalone commands, so those are excluded.
    """
    from config import DEVIL_FRUITS

    result = {}
    for tier in ("Good", "Medium", "Bad"):
        for fruit in DEVIL_FRUITS.get(tier, []):
            fruit_name = fruit.get("full") or fruit.get("name")
            normalized = " ".join(str(fruit_name or "").split()).casefold()
            if normalized in {
                "gomu gomu no mi",
                "hito hito no mi, model: nika",
                "ope ope no mi",
            }:
                continue
            base_skill = get_fruit_skill(fruit_name)
            moves = _PVP_SKILL_LOOKUP.get(normalized, [])
            if not base_skill:
                continue
            extra_moves = [
                dict(move) for move in moves
                if " ".join(str(move.get("name", "")).split()).casefold()
                != " ".join(str(base_skill.get("name", "")).split()).casefold()
            ][:2]
            if len(extra_moves) != 2:
                continue
            for skill in extra_moves:
                spell_name = skill["name"]
                command = "".join(
                    ch for ch in spell_name.casefold()
                    if ch in "abcdefghijklmnopqrstuvwxyz0123456789"
                )
                if len(command) > 32 and ":" in spell_name:
                    command = "".join(
                        ch for ch in spell_name.split(":", 1)[1].casefold()
                        if ch in "abcdefghijklmnopqrstuvwxyz0123456789"
                    )
                if not command or len(command) > 32:
                    raise ValueError(f"Invalid fruit spell command for {fruit_name}: {spell_name}")
                if command in result:
                    raise ValueError(f"Duplicate fruit spell command: /{command}")
                result[command] = {"fruit": fruit_name, "skill": skill}
    return result
