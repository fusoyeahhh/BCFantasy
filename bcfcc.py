import functools
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
import read
import numpy


from ff6_flags import STATUS_FLAGS

def commit(fcn, addr):
    # decorator to commit changes to memory
    # read memory values into dictionary
    #mem = {a: val for a in addr}
    # send requested values to function
    #modify = fcn(**mem)
    # write out result
    #read.write_instructions()
    pass

class MemoryRegion(object):
    def __init__(self):
        self.mem = {}
        pass

    def __getitem__(self, addr):
        """
        Retrieve value at address. Supports two modes of addressing:

        reg[0xFF] => single 8 bit read
        reg[0xFF,2] => single 16 bit read
        reg[0xFF,4] => single 32 bit read
        """
        if not isinstance(addr, tuple):
            return self.mem[addr]
        else:
            addr, dep = addr
            # SNES is natively little endian
            return sum(self.mem[addr + i] * 0x100 ** (dep - 1 - i) for i in range(dep))

    def __setitem__(self, addr, val):
        """
        Set value at address. If addr is a list-like, expand to 8 bit sets at addresses.
        """
        # FIXME: translate aliases
        try:
            addr, dep = addr
            for i in range(dep):
                # SNES is natively little endian
                self.mem[addr + i] = (val >> (8 * (dep - i))) & 0xFF
        # We get a ValueError if the array doesn't align with the assignment
        # We get a TypeError if the addr is just an int
        except (ValueError, TypeError):
            pass

        self.mem[addr] = val

    def _from_memory_range(self, memfile):
        """
        Read in a binary file with address => memory chunk and memory map.
        """
        mem = read.read_memory(memfile)
        logging.debug(f"_from_memory_range | chunk addrs: {','.join(map(str, mem.keys()))}")
        assert len(mem) == 1, "bad memory read"

        start_addr = [*mem.keys()][0]
        # splay data into addresses
        self.mem = {start_addr + i: m for i, m in enumerate(mem[start_addr])}

        return

    def _expand_assign(self, addr, val):
        """
        Expand out complex addresses to their single 8 bit writes.
        """
        if isinstance(addr, complex):
            dep = int(addr.imag)
            val = [(val >> 8 * i) & 0xFF for i in range(dep)]
            addr = [int(addr.real) + i for i in range(dep)]
            return list(functools.reduce(tuple.__add__, zip(addr, val)))
        return [addr, val]

class Character(MemoryRegion):
    def __init__(self):
        super().__init__()

        self._memmap = {
            # $3AA0 76543210
            #       7: allow battle menu to open (cleared when character/monster is seized)
            #       6: psyche was just cleared
            #       5: advance wait counter just triggered (never used ???)
            #       4: something with condemned
            #       3: action counter just triggered (ATB gauge is stopped)
            #       2: ogre nix can't break
            #       1: skip advance wait
            #       0: target is present
            0x3AA0: "battle_cond_1",
            # $3AA1 76543210
            #       7: something with regen/poison/seizure (DoT)
            #       6: pending action from run/control/psyche/seize (triggers subroutine at C2/0977)
            #       5: row (0 = front, 1 = back)
            #       4: target has a pending DoT action
            #       3:
            #       2: protection from instant death
            #       1: defense mode (used def. command)
            #       0: pending action goes directly to action queue
            0x3AA1: "battle_cond_2",

            # $3ADC Slow/Normal/Haste Counter (decrement status counters on overflow)
            0x3ADC: "speed_tick",
            # $3ADD Slow/Normal/Haste Constant (32/64/84)
            0x3ADD: "status_mult",
            # $3AF0 Counter for damage over time (poison, regen, seize, phantasm)
            0x3AF0: "status_tick",
            # $3AF1 Stop Counter
            0x3AF1: "stop_tick",
            # $3B04 Morph Gauge ($00 = not shown, $01 = empty, $FF = full)
            0x3B04: "morph_gauge",
            # $3B05 Condemned Number ($00 = not shown, $01 = 00 ... $64 = 99)
            0x3B05: "cond_tick",

            # $3B18 Level
            0x3B18: "level",
            # $3B19 Speed
            0x3B19: "speed",
            # $3B2C Vigor * 2
            0x3B2C: "vigor",
            # $3B2D Speed (dummy)
            0x3B2D: "_speed",
            # $3B40 Stamina
            0x3B40: "stamina",
            # $3B41 Mag.Pwr * 1.5
            0x3B41: "magpwr",
            # $3B54 255 - (Evade * 2) + 1
            0x3B54: "evade",
            # $3B55 255 - (MBlock * 2) + 1
            0x3B55: "mblk",
            # $3B68 Bat.Pwr (main hand)
            0x3B68: "batpwr_1",
            # $3B69 Bat.Pwr (off hand)
            0x3B69: "batpwr_2",
            # +$3B7C Hit Rate
            0x3B7C + 2j: "hit_rate",

            # +$3AB4 Advance Wait Counter
            0x3AB4 + 2j: "wait_cntr",
            # +$3AC8 ATB Gauge Constant (see C2/09D2)
            0x3AC8 + 2j: "atb_gauge",

            # $3B90 Attack Elemental
            0x3B90: "atk_elem",
            # $3B91 Attack Properties
            0x3B91: "atk_props",
            # $3BA4 Main Hand Weapon Properties (Defense for Monsters)
            0x3BA4: "wpn_prop_1",
            # $3BA5 Off Hand Weapon Properties (Magic Defense for Monsters)
            0x3BA5: "wpn_prop_2",
            # $3BCC Absorbed Elements
            0x3BCC: "abs_elem",
            # $3BCD Immune Elements
            0x3BCD: "imm_elem",
            # $3BE0 Weak Elements
            0x3BE0: "weak_elem",
            # $3BE1 Halved Elements
            0x3BE1: "half_elem",
            # +$3BF4 Current HP
            0x3BF4 + 2j: "cur_hp",
            # +$3C08 Current MP
            0x3C08 + 2j: "cur_mp",
            # +$3C1C Max HP
            0x3C1C + 2j: "max_hp",
            # +$3C30 Max MP
            0x3C30 + 2j: "max_mp",
            # $3C44 Relic Effects 1
            0x3C44: "rel_eff_1",
            # $3C45 Relic Effects 2
            0x3C45: "rel_eff_2",
            # $3C58 Relic Effects 3
            0x3C58: "rel_eff_3",
            # $3C59 Relic Effects 4
            0x3C59: "rel_eff_3",
            # $3C6C Equipment Status 2
            0x3C6C: "eqp_stat_2",
            # $3C6D Equipment Status 3
            0x3C6D: "eqp_stat_3",
            # $3C80 c?ksruph Special Status 2
            #       c: can't control
            #       ?: special event ???
            #       k: can't sketch
            #       s: can't scan
            #       r: can't run
            #       u: can't suplex
            #       p: first strike (has an action at the very beginning of battle)
            #       h: harder to run
            0x3C80: "cmd_imm",
            # $3C81 Special Attack Animation Index
            # $3C94 pppiiiii Metamorph Info
            #       p: metamorph probability (0 = 255/256, 1 = 3/4, 2 = 1/2, 3 = 1/4, 4 = 1/8, 5 = 1/16, 6 = 1/32, 7 = 0)
            #       i: metamorph item set
            # $3C95 ui-h-n-m
            #       u: undead
            #       i: imp critical ??
            #       h: human
            #       n: don't display name
            #       m: dies at 0 MP
            # $3CA8 Main Hand Item Index
            # $3CA9 Off Hand Item Index
            # $3CBC ssssmpbb Main Hand
            # $3CBD ssssmpbb Main Hand
            #       s: off hand special effect
            #       m: can block magic attacks
            #       p: can block physical attacks
            #       b: block graphic (0 = Dagger, 1 = Sword, 2 = Shield, 3 = Zephyr Cape)
            # $3CD0 Relic 1
            0x3CD0: "relic_1",
            # $3CD1 Relic 2
            0x3CD1: "relic_2",

            # $3DD4 Status to Set 1
            0x3DD4: "status_set_1",
            # $3DD5 Status to Set 2
            0x3DD5: "status_set_2",
            # $3DE8 Status to Set 3
            0x3DE8: "status_set_3",
            # $3DE9 Status to Set 4
            0x3DE9: "status_set_4",
            # $3DFC Status to Clear 1
            0x3DFC: "status_clear_1",
            # $3DFD Status to Clear 2
            0x3DFD: "status_clear_2",
            # $3E10 Status to Clear 3
            0x3E10: "status_clear_3",
            # $3E11 Status to Clear 4
            0x3E11: "status_clear_4"
        }

        self._set_aliases()

        # Stats which need special encoding
        self._enc_stats = {
            "vigor": lambda v: v * 2,
            "magpwr": lambda m: m * 3 // 2,
            "evade": lambda e: 255 - (e * 2) + 1,
            "mblk": lambda m: 255 - (m * 2) + 1,
        }

        # Outgoing write instructions
        self._queue = []

    def _set_aliases(self):
        # Reverse lookup
        self._rmap = {v: k for k, v in self._memmap.items()}

        # add groupings of flags like status and elements
        self.status_set_addr = {f: self._rmap[f]
                    for f in ["status_set_1", "status_set_2", "status_set_3", "status_set_4"]}

        self.status_clr_addr = {f: self._rmap[f]
                    for f in ["status_clear_1", "status_clear_2", "status_clear_3", "status_clear_4"]}

    def _shift_memmap(self, shift=0):
        addrs = sorted(self._memmap.keys(), key=lambda v: complex(v).real)
        # add bookend
        addrs.append(addrs[-1] + 1)

        seg = []
        for a1, a2 in zip(addrs[:-1], addrs[1:]):
            val, width = complex(a1).real, max(1, complex(a1).imag)
            v2, w2 = complex(a2).real, max(1, complex(a2).imag)

            # Identify consecutive addresses in segment
            seg.append(a1)
            # We also end the segment if the byte width changes
            if val + width == v2 and width == w2:
                continue

            # Compute overall segment shift value
            _shift = int(shift * (complex(seg[-1] - seg[0]).real + width))
            # Shift subsegment
            for a in seg:
                self._memmap[a + _shift] = self._memmap.pop(a)
            seg = []

        # reset pointer aliases to new values
        self._set_aliases()

    def _from_memory_range(self, memfile, slot=0):
        # FIXME: this is permanent, and probably shouldn't be
        self._shift_memmap(slot)
        start_addr = super()._from_memory_range(memfile)

        # FIXME: this only sets them once, I'm not sure that's what we want
        # iterate through memmap and set attributes
        for addr, attr in self._memmap.items():
            if isinstance(addr, int):
                setattr(self, attr, self.mem[addr])
            elif isinstance(addr, complex):
                addr, dep = int(addr.real), int(addr.imag)
                setattr(self, attr, self[addr, dep])
            else:
                raise ValueError(f"Can't parse address {addr}")

    def get_stat_values(self):
        pass

    def get_status_flags(self):
        return {f: self[a] for f, a in self.status_set_addr.items()}

    def set_status(self, *status, clear=False):
        # statuses and flags to set
        set_this, flags = set(status), self.status_clr_addr if clear else self.status_set_addr

        # Combine the flag with the statuses which that flag controls and set
        # value appropriately
        for stset, stflag in zip(flags, STATUS_FLAGS):
            addr = flags[stset]
            val = self[addr]
            for stat in set_this & set(stflag):
                val |= stflag[stat]
            self._queue += [addr, val]

        return

    def change_stat(self, stat, val):
        addr = self._rmap[stat]
        # read and write certain stats with encoded values (e.g. vigor)
        if stat in self._enc_stats:
            val = self._enc_stats[stat](val)
        self._queue += self._expand_assign(addr, val)

    def commit(self):
        for i in range(len(self._queue) // 2):
            addr, val = self._queue[2 * i], self._queue[2 * i + 1]
            self[addr] = val

    def flush(self, commit=False):
        if commit:
            self.commit()

        q, self._queue = self._queue[:], []
        return q

class Battlefield(MemoryRegion):
    def __init__(self):
        super().__init__()

class Inventory(MemoryRegion):
    def __init__(self):
        super().__init__()

def write_arbitrary(*args, **kwargs):
    """
    Write a sequence of one or more address / value pairs to memory.

    While this is used internally to send data to the emulator, it should be used (directly) only sparingly by admins as it can write arbitrary data to any location.
    """
    args = list(args)
    logging.info(f"write_arbitrary | input: {args}")
    # Need address value pairs
    assert len(args) % 2 == 0, f"write_arbitrary | arg len should be a multiple of 2, got {args}"

    instr = []
    while len(args) > 0:
        # assume hex
        addr = int(args.pop(0), 16)
        value = int(args.pop(0), 16) & 0xFF
        # Break into high byte, low byte, and value to write
        instr.extend(bytes([addr >> 8, addr & 0xFF, value]))

    logging.info(f"write_arbitrary | to write: {instr}")
    return instr

def modify_item(*args):
    args = list(args)
    # FIXME: This will overwrite any item in this position\
    # FIXME: convert string to hex
    item = int(args.pop(0), 16)
    instr = [0x2686 >> 8, 0x2686 & 0xFF, item,
             0x2689 >> 8, 0x2689 & 0xFF, 0x1]
    # FIXME: increment

    return instr

def cant_run(toggle=None, **kwargs):
    logging.info(f"cant_run | toggle ({toggle}), kwargs {[*kwargs.keys()]}")
    mask = 1 << 2
    mem = read.read_memory()
    # FIXME: need actual memory chunk to read from
    #val = mem[0x00B1]
    val = 0
    if toggle is not None:
        val ^= mask
    else:
        val |= mask

    #return write_arbitrary(*["0x00B1", hex(val)])
    return write_arbitrary(*["0x00B1", hex(mask)])

def set_status(status, slot=0, **kwargs):
    logging.info(f"set_status | status {status}, slot ({slot}), kwargs {[*kwargs.keys()]}")
    slot = int(slot)
    if slot < 0 or slot >= 4:
        raise IndexError(f"Invalid party slot {slot}.")

    c = kwargs["party"][slot]
    if status.startswith("-"):
        c.set_status(status[1:], clear=True)
    else:
        c.set_status(status)
    return write_arbitrary(*map(hex, c.flush()))

def set_stat(stat, val, slot=0, **kwargs):
    logging.info(f"set_stat | stat / val ({stat} / {val}), kwargs {[*kwargs.keys()]}")
    slot = int(slot)
    if slot < 0 or slot >= 4:
        raise IndexError(f"Invalid party slot {slot}.")

    c = kwargs["party"][slot]
    c.change_stat(stat, int(val))
    return write_arbitrary(*map(hex, c.flush()))

def fallen_one(**kwargs):
    logging.info(f"fallen_one | kwargs {[*kwargs.keys()]}")
    write = []
    for c in kwargs["party"]:
        # FIXME: check to make sure the character actually exists
        c.change_stat("cur_hp", 1)
        write.extend(list(map(hex, c.flush())))
    return write_arbitrary(*write)

def status(targ, *stats):
    for status in stats:
        if status.startswith("-"):
            targ.set_status(status[1:], clear=True)
        else:
            targ.set_status(status)
    return targ.flush()

if __name__ == "__main__":
    import os

    # Do testing
    # Must have a memfile to work with
    assert os.path.exists("memfile")

    party = [Character() for i in range(4)]
    for i in range(4):
        # FIXME: make one-step initialization
        party[i]._from_memory_range("memfile", slot=i)

    eparty = [Character() for i in range(6)]
    for i in range(6):
        # FIXME: make one-step initialization
        eparty[i]._from_memory_range("memfile", slot=i + 4)

    gctx = {"party": party, "eparty": eparty}

    #
    # Can't run
    #
    print("--- Can't run (no toggle)")
    print("!cc cant_run")
    print(cant_run(**gctx))

    #
    # Set status
    #
    print("--- Set status (set poison, slot 0)")
    print("!cc set_status poison 0")
    print(set_status("poison", 0, **gctx))

    print("--- Set status (remove poison, slot 0)")
    print("!cc set_status -poison 0")
    print(set_status("-poison", 0, **gctx))

    print("--- Set status (set poison, slot 3)")
    print("!cc set_status poison 3")
    print(set_status("poison", 3, **gctx))

    #
    # Set stats
    #
    print("--- Set stat (evade=0, slot 0)")
    print("!cc set_stat evade 0 0")
    print(set_stat("evade", 0, 0, **gctx))

    print("--- Set stat (evade=0, slot 3)")
    print("!cc set_stat evade 0 3")
    print(set_stat("evade", 0, 3, **gctx))

    print("--- Set stat (vigor=1, slot 1)")
    print("!cc set_stat vigor 1 1")
    # Should be multiplied by 2
    print(set_stat("vigor", 1, 1, **gctx))

    #
    # Fallen One
    #
    print("--- Fallen One")
    print("!cc fallen_one")
    print(fallen_one(**gctx))
