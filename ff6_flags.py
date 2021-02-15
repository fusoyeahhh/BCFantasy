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

def _validate_status(statuses):
    return set(statuses).issubset(set.union(*map(set, STATUS_FLAGS)))

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
ELEM_FLAGS = {e: 1 << (i + 1) for i, e in
                    enumerate(["fire", "ice", "lighting", "poison", "wind", "pearl", "earth", "water"])}

def _validate_elems(*elems):
    return set(elems).issubset(set(ELEM_FLAGS))