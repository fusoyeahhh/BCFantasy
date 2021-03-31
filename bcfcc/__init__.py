import functools
import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from .cmdimpl import *

_TEST_SUITE = {
    "cant_run": None,
    "fallen_one": None,
    "activate_golem": None,
    "null_elem": ("fire",),
    "set_name": ('TEST', 1),
    "pick_fight": None,
    "moogle_charm": None,
    "give_restorative": ("tonic",),
    "random_status": (2,),
    "remedy": (3,),
    "add_gp": None,
    "remove_gp": None,
    # "give_doggo": give_interceptor, # enemy or player
    "life_1": (1,),
    "life_2": (2,),
    "life_3": (3,),
    "bs1a": None,
    # "mirror_buttons": bcfcc.MirrorButtons,
    "give_rare_relic": None,
    "give_rare_equip": None,
    "power_overwhelming": (4,),
    "power_underwhelming": (4,),
}

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
            return sum(self.mem[addr + i] * 0x100 ** i for i in range(dep))

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
        #assert len(mem) == 1, f"bad memory read, found {len(mem)} pointers"

        self.mem = {}
        for start_addr in mem:
            # splay data into addresses
            self.mem.update({start_addr + i: m for i, m in enumerate(mem[start_addr])})

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

from ._char import Character
from ._inv import Inventory

class Battlefield(MemoryRegion):
    def __init__(self):
        super().__init__()

