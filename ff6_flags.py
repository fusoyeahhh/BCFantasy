STATUS_FLAGS = [None] * 4

# Byte 1
# bit 0: Blind
# bit 1: Zombie
# bit 2: Poison
# bit 3: MagiTek
# bit 4: Vanish
# bit 5: Imp
# bit 6: Petrify
# bit 7: Wounded
STATUS_FLAGS[0] = {k: 1 << i for i, k in
                   enumerate(["blind", "zombie", "poison", "magitek", "vanish", "imp", "petrify", "wounded"])}

# Byte 2
# bit 0: Condemned
# bit 1: Near Fatal
# bit 2: Image
# bit 3: Mute
# bit 4: Berserk
# bit 5: Muddle
# bit 6: Seizure
# bit 7: Sleep
STATUS_FLAGS[1] = {k: 1 << i for i, k in
                   enumerate(["condemned", "nearfatal", "image", "mute", "berserk", "muddle", "seizure", "sleep"])}

# Byte 3
# bit 0: Dance
# bit 1: Regen
# bit 2: Slow
# bit 3: Haste
# bit 4: Stop
# bit 5: Shell
# bit 6: Safe
# bit 7: Wall
STATUS_FLAGS[2] = {k: 1 << i for i, k in
                   enumerate(["dance", "regen", "slow", "haste", "stop", "shell", "safe", "wall"])}

# Byte 4
# bit 0: Rage
# bit 1: Freeze
# bit 2: Life 3
# bit 3: Morph
# bit 4: Spell
# bit 5: Hide
# bit 6: Interceptor
# bit 7: Float
STATUS_FLAGS[3] = {k: 1 << i for i, k in
                   enumerate(["rage", "freeze", "life3", "morph", "spell", "hide", "interceptor", "float"])}

NEGATIVE_STATUSES = {"blind", "zombie", "poison", "vanish", "imp", "petrify", "wounded",
                     "condemned", "mute", "berserk", "muddle", "seizure", "sleep", "slow", "stop"}
POSITIVE_STATUSES = {"image", "regen", "haste", "shell", "safe", "wall", "life3", "morph", "float"}
UNUSABLE_STATUSES = {"magitek", "nearfatal", "dance", "rage", "freeze",  "spell", "hide", "interceptor"}
ALL_STATUSES = NEGATIVE_STATUSES | POSITIVE_STATUSES | UNUSABLE_STATUSES

def _validate_status(statuses):
    return set(statuses).issubset(ALL_STATUSES)

# Elemental Flags
# From https://www.tales-cless.org/ff6hack/#elem
# 1: Fire
# 2: Ice
# 3: Lightning
# 4: Poison
# 5: Wind
# 6: Pearl
# 7: Earth
# 8: Water
ELEM_FLAGS = {e: 1 << i for i, e in
                    enumerate(["fire", "ice", "lighting", "poison", "wind", "pearl", "earth", "water"])}

def _validate_elems(*elems):
    return set(elems).issubset(set(ELEM_FLAGS))

# Item Descriptions
ITEMS = """00 Dirk
01 MithrilKnife
02 Guardian
03 Air Lancet
04 ThiefKnife
05 Assassin
06 Man Eater
07 SwordBreaker
08 Graedus
09 ValiantKnife
0A MithrilBlade
0B RegalCutlass
0C Rune Edge
0D Flame Sabre
0E Blizzard
0F ThunderBlade
10 Epee
11 Break Blade
12 Drainer
13 Enhancer
14 Crystal
15 Falchion
16 Soul Sabre
17 Ogre Nix
18 Excalibur
19 Scimitar
1A Illumina
1B Ragnarok
1C Atma Weapon
1D Mithril Pike
1E Trident
1F Stout Spear
20 Partisan
21 Pearl Lance
22 Gold Lance
23 Aura Lance
24 Imp Halberd
25 Imperial
26 Kodachi
27 Blossom
28 Hardened
29 Striker
2A Stunner
2B Ashura
2C Kotetsu
2D Forged
2E Tempest
2F Murasame
30 Aura
31 Strato
32 Sky Render
33 Heal Rod
34 Mithril Rod
35 Fire Rod
36 Ice Rod
37 Thunder Rod
38 Poison Rod
39 Pearl Rod
3A Gravity Rod
3B Punisher
3C Magus Rod
3D Chocobo Brsh
3E DaVinci Brsh
3F Magical Brsh
40 Rainbow Brsh
41 Shuriken
42 Ninja Star
43 Tack Star
44 Flail
45 Full Moon
46 Morning Star
47 Boomerang
48 Rising Sun
49 Hawk Eye
4A Bone Club
4B Sniper
4C Wing Edge
4D Cards
4E Darts
4F Doom Darts
50 Trump
51 Dice
52 Fixed Dice
53 MetalKnuckle
54 Mithril Claw
55 Kaiser
56 Poison Claw
57 Fire Knuckle
58 Dragon Claw
59 Tiger Fangs
5A Buckler
5B Heavy Shld
5C Mithril Shld
5D Gold Shld
5E Aegis Shld
5F Diamond Shld
60 Flame Shld
61 Ice Shld
62 Thunder Shld
63 Crystal Shld
64 Genji Shld
65 TortoiseShld
66 Cursed Shld
67 Paladin Shld
68 Force Shield
69 Leather Hat
6A Hair Band
6B Plumed Hat
6C Beret
6D Magus Hat
6E Bandana
6F Iron Helmet
70 Coronet
71 Bard's Hat
72 Green Beret
73 Heaad Band
74 Mithril Helm
75 Tiara
76 Gold Helmet
77 Tiger Mask
78 Red Cap
79 Mystery Veil
7A Circlet
7B Regal Crown
7C Diamond Helm
7D Dark Hood
7E Crystal Helm
7F Oath Veil
80 Cat Hood
81 Genji Helmet
82 Thornlet
83 Titanium
84 LeatherArmor
85 Cotton Robe
86 Kung Fu Suit
87 Iron Armor
88 Silk Robe
89 Mithril Vest
8A Ninja Gear
8B White Dress
8C Mithril Mail
8D Gaia Gear
8E Mirage Vest
8F Gold Armor
90 Power Sash
91 Light Robe
92 Diamond Vest
93 Red Jacket
94 Force Armor
95 DiamondArmor
96 Dark Gear
97 Tao Robe
98 Crystal Mail
99 Czarina Gown
9A Genji Armor
9B Imp's Armor
9C Minerva
9D Tabby Suit
9E Chocobo Suit
9F Moogle Suit
A0 Nutkin Suit
A1 BehemothSuit
A2 Snow Muffler
A3 NoiseBlaster
A4 Bio Blaster
A5 Flash
A6 Chain Saw
A7 Debilitator
A8 Drill
A9 Air Anchor
AA AutoCrossbow
AB Fire Skean
AC Water Edge
AD Bolt Edge
AE Inviz Edge
AF Shadow Edge
B0 Goggles
B1 Star Pendant
B2 Peace Ring
B3 Amulet
B4 White Cape
B5 Jewel Ring
B6 Fairy Ring
B7 Barrier Ring
B8 MithrilGlove
B9 Guard Ring
BA RunningShoes
BB Wall Ring
BC Cherub Down
BD Cure Ring
BE True Knight
BF DragoonBoots
C0 Zephyr Cape
C1 Czarina Ring
C2 Cursed Ring
C3 Earrings
C4 Atlas Armlet
C5 Blizzard Orb
C6 Rage Ring
C7 Sneak Ring
C8 Pod Bracelet
C9 Hero Ring
CA Ribbon
CB Muscle Belt
CC Crystal Orb
CD Gold Hairpin
CE Economizer
CF Thief Glove
D0 Gauntlet
D1 Genji Glove
D2 Hyper Wrist
D3 Offering
D4 Beads
D5 Black Belt
D6 Coin Toss
D7 FakeMustache
D8 Gem Box
D9 Dragon Horn
DA Merit Award
DB Memento Ring
DC Safety Bit
DD Relic Ring
DE Moogle Charm
DF Charm Bangle
E0 Marvel Shoes
E1 Back Guard
E2 Gale Hairpin
E3 Sniper Sight
E4 Exp. Egg
E5 Tintinabar
E6 Sprint Shoes
E7 Rename Card
E8 Tonic
E9 Potion
EA X-Potion
EB Tincture
EC Ether
ED X-Ether
EE Elixir
EF Megalixir
F0 Fenix Down
F1 Revivify
F2 Antidote
F3 Eyedrop
F4 Soft
F5 Remedy
F6 Sleeping Bag
F7 Tent
F8 Green Cherry
F9 Magicite
FA Super Ball
FB Echo Screen
FC Smoke Bomb
FD Warp Stone
FE Dried Meat
FF -Blank-"""
ITEMS = [i.split(" ") for i in ITEMS.split('\n')]
ITEMS = dict([(int(i[0], 16), ''.join(i[1:]).lower()) for i in ITEMS])

_VALID_ITEMS = set(ITEMS.values())
def _validate_item(item_name):
    return item_name.replace(" ", "").lower() in _VALID_ITEMS

# Apply reverse lookup as well
ITEMS.update({v: k for k, v in ITEMS.items()})

# Relic effects
RELIC_EFFECTS = {}

#       $11D5 76543210 relic effects 1
RELIC_EFFECTS[0x11D5] = {}
#             7: MP +12.5% (bard's hat)
RELIC_EFFECTS[0x11D5][1 << 7] = "MP +12.5% (bard's hat)"
#             6: MP +50% (crystal orb)
RELIC_EFFECTS[0x11D5][1 << 6] = "MP +50% (crystal orb)"
#             5: MP +25% (minerva)
RELIC_EFFECTS[0x11D5][1 << 5] = "MP +25% (minerva)"
#             4: HP +12.5% (green beret)
RELIC_EFFECTS[0x11D5][1 << 4] = "HP +12.5% (green beret)"
#             3: HP +50% (muscle belt)
RELIC_EFFECTS[0x11D5][1 << 3] = "HP +50% (muscle belt)"
#             2: HP +25% (red cap)
RELIC_EFFECTS[0x11D5][1 << 2] = "HP +25% (red cap)"
#             1: raise magic damage (double earrings or hero ring)
RELIC_EFFECTS[0x11D5][1 << 1] = "raise magic damage (earrings / hero ring)"
#             0: raise fight damage (atlas armlet, hero ring)
RELIC_EFFECTS[0x11D5][1 << 0] = "raise fight damage (atlas armlet / hero ring)"

#       $11D6 76543210 relic effects 2
RELIC_EFFECTS[0x11D6] = {}
#             7: jump continuously (dragon horn)
RELIC_EFFECTS[0x11D6][1 << 7] = "jump continuously (dragon horn)"
#             6: steal -> capture (thief glove)
RELIC_EFFECTS[0x11D6][1 << 6] = "steal -> capture (thief glove)"
#             5: slot -> gp rain (coin toss)
RELIC_EFFECTS[0x11D6][1 << 5] = "slot -> gp rain (coin toss)"
#             4: sketch -> control (fakemustache)
RELIC_EFFECTS[0x11D6][1 << 4] = "sketch -> control (fakemustache)"
#             3: magic -> x-magic (gem box)
RELIC_EFFECTS[0x11D6][1 << 3] = "magic -> x-magic (gem box)"
#             2: fight -> jump (dragoonboots)
RELIC_EFFECTS[0x11D6][1 << 2] = "fight -> jump (dragoonboots)"
#             1: prevent back/pincer attacks (back guard)
RELIC_EFFECTS[0x11D6][1 << 1] = "prevent back/pincer attacks (back guard)"
#             0: increase pre-emptive attack rate (gale hairpin)
RELIC_EFFECTS[0x11D6][1 << 0] = "increase pre-emptive attack rate (gale hairpin)"

#       $11D7 76543210 relic effects 3
RELIC_EFFECTS[0x11D7] = {}
#             7: raise vigor +50% (hyper wrist)
RELIC_EFFECTS[0x11D7][1 << 7] = "raise vigor +50% (hyper wrist)"
#             6: MP cost = 1 (economizer)
RELIC_EFFECTS[0x11D7][1 << 6] = "MP cost = 1 (economizer)"
#             5: MP cost = 50% (gold hairpin)
RELIC_EFFECTS[0x11D7][1 << 5] = "MP cost = 50% (gold hairpin)"
#             4: 100% Hit Rate, ignore target's MBlock (sniper sight)
RELIC_EFFECTS[0x11D7][1 << 4] = "100% Hit Rate (sniper sight)"
#             3: Increase Control Rate (coronet)
RELIC_EFFECTS[0x11D7][1 << 3] = "Increase Control Rate (coronet)"
#             2: Increase Sketch Rate (beret)
RELIC_EFFECTS[0x11D7][1 << 2] = "Increase Sketch Rate (beret)"
#             1: raise magic damage (single earring or hero ring)
RELIC_EFFECTS[0x11D7][1 << 1] = "raise magic damage (earring / hero ring)"
#             0: Increase Steal Rate (sneak ring)
RELIC_EFFECTS[0x11D7][1 << 0] = "Increase Steal Rate (sneak ring)"

#       $11D8 -thgaebo relic effects 4
RELIC_EFFECTS[0x11D8] = {}
#             t: protects weak allies (true knight)
RELIC_EFFECTS[0x11D8][1 << 6] = "protects weak allies (true knight)"
#             h: can equip heavy items (merit award)
RELIC_EFFECTS[0x11D8][1 << 5] = "can equip heavy items (merit award)"
#             g: can equip 2 weapons (genji glove)
RELIC_EFFECTS[0x11D8][1 << 4] = "can equip 2 weapons (genji glove)"
#             a: uses weapon 2-handed (gauntlet)
RELIC_EFFECTS[0x11D8][1 << 3] = "uses weapon 2-handed (gauntlet)"
#             e: randomly evade (beads)
RELIC_EFFECTS[0x11D8][1 << 2] = "randomly evade (beads)"
#             b: randomly counter (black belt)
RELIC_EFFECTS[0x11D8][1 << 1] = "randomly counter (black belt)"
#             o: fight -> x-fight (offering)
RELIC_EFFECTS[0x11D8][1 << 0] = "fight -> x-fight (offering)"

#       $11D9 7--43210 relic effects 5
RELIC_EFFECTS[0x11D9] = {}
#             7: make character undead (relic ring)
RELIC_EFFECTS[0x11D9][1 << 7] = "make character undead (relic ring)"
#             4: double GP (cat hood)
RELIC_EFFECTS[0x11D9][1 << 4] = "double GP (cat hood)"
#             3: double experience (exp. egg)
RELIC_EFFECTS[0x11D9][1 << 3] = "double experience (exp. egg)"
#             2: casts wall when HP is low
RELIC_EFFECTS[0x11D9][1 << 2] = "critical wall"
#             1: casts safe when HP is low (mithril glove, czarina ring)
RELIC_EFFECTS[0x11D9][1 << 1] = "critical safe (mithril glove / czarina ring)"
#             0: casts shell when HP is low (barrier ring, czarina ring)
RELIC_EFFECTS[0x11D9][1 << 0] = "critical shell (barrier ring / czarina ring)"