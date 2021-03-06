import logging
import random

from bcf import read
from ff6_flags import NEGATIVE_STATUSES, ALL_STATUSES, UNUSABLE_STATUSES, _validate_elems, ELEM_FLAGS


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


_add_gp = {
    # No constraints
}
_MAX_GP = 2**24 - 1


def add_gp(amnt=1000, **kwargs):
    """
    !cc add_gp
    Add 1000 GP to total.

    Precondition: None
    """
    logging.info(f"add_gp | amount {amnt}, kwargs {[*kwargs.keys()]}")
    total_gp = sum([v << (8 * i) for i, v in enumerate(kwargs["field_ram"][0x1860:0x1863])])
    new_total = max(0, min(total_gp + amnt, _MAX_GP))
    logging.info(f"add_gp | GP change {total_gp} -> {new_total}")
    # FIXME: Do we need to reverse this?
    return write_arbitrary(*map(hex, [(new_total >> 8 * i) & 0xFF for i in range(3)]))


def cant_run(toggle=None, **kwargs):
    mask = 1 << 2
    logging.info(f"cant_run | toggle ({toggle}), kwargs {[*kwargs.keys()]}")

    # FIXME: do raw read here instead?
    val = kwargs["bf"]["cant_run"]
    logging.info(f"cant_run | toggle ({toggle}), pre toggle value {val}")
    if toggle is not None:
        val ^= mask
    else:
        val |= mask

    return write_arbitrary(*["0x00B1", hex(val)])


def moogle_charm(toggle=True, **kwargs):
    # $11DF t-s---mc Field Equipment Effects
    #       t: tintinabar effect (doesn't work)
    #       s: sprint shoes effect (1.5x walk speed)
    #       m: moogle charm effect (no random battles)
    #       c: charm bangle effect (50% less random battles)
    mask = 1 << 1
    logging.info(f"moogle_charm | toggle ({toggle}), kwargs {[*kwargs.keys()]}")

    # FIXME: do raw read here instead?
    val = kwargs["bf"]["field_relics"]
    logging.info(f"moogle_charm | toggle ({toggle}), pre toggle value {val}")
    if toggle is not None:
        val ^= mask
    else:
        val |= mask

    return write_arbitrary(*["0x11DF", hex(val)])


def activate_golem(hp_val=1000, **kwargs):
    logging.info(f"activate_golem | hp_val {hp_val}")
    # Other flags to set?
    # $3A81 - (used when $3A82 is loaded in 16-bit mode)
    # $3A82 Golem block targets (disabled if negative)
    # $AA Character 1 Block Type (-> $2C78) (0 = none, 1 = knife, 2 = sword, 3 = shield, 4 = zephyr cape, 5 = hand up, 6 = golem, 7 = dog)
    # $AB Character 2 Block Type (-> $2C79)
    # $AC Character 3 Block Type (-> $2C7A)
    # $AD Character 4 Block Type (-> $2C7B)

    # FIXME: don't do this manually
    hp_val = int(hp_val)
    lowbyte, highbyte = hp_val & 0xFF, (hp_val >> 8)
    return write_arbitrary(*["0x3A36", hex(lowbyte), "0x3A37", hex(highbyte)])


def ole_cape(**kwargs):
    logging.info(f"ole_cape |")
    # by default, we do all?
    out, mask = [], 1 << 6
    for byt in range(0xAA, 0xAE):
        out.extend([byt, 1 << 6])

    return write_arbitrary(*map(hex, out))


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


_remedy = {
    #"precondition": (targ_valid, bool.__and__, not has_status("wounded")),
    "status": "battle"
}
_REMEDY_CLEAR = NEGATIVE_STATUSES - {"wounded"}


def remedy(*args, **kwargs):
    """
    !cc remedy [slot #]
    Remedy-like effect, remove all "negative" statuses (except wounded).

    Precondition: must be in battle, target must be valid and not dead
    """
    logging.info(f"remedy | args {args}, kwargs {[*kwargs.keys()]}")
    # FIXME: ensure slot is filled
    slot = args[0] if len(args) > 0 else random.randint(0, 3)
    logging.info(f"remedy | clearing statuses for slot {slot}")

    # FIXME: need to not affect other statuses
    if slot < 0 or slot >= 4:
        raise IndexError(f"Invalid party slot {slot}.")

    c = kwargs["party"][slot]
    c.set_status(*list(_REMEDY_CLEAR), clear=True)
    return write_arbitrary(*map(hex, c.flush()))


def random_status(*args, **kwargs):
    logging.info(f"random_status | args {args}, kwargs {[*kwargs.keys()]}")
    # FIXME: ensure slot is filled
    targ = args[0] if len(args) > 0 else random.randint(0, 3)
    status = random.choice(list(ALL_STATUSES - UNUSABLE_STATUSES))
    logging.info(f"random_status | selected {status} status, inflicting on {targ}")
    return set_status(status, slot=targ, **kwargs)


_life_1 = {
    #"precondition": (targ_valid, bool.__and__, has_status("wounded")),
    "status": "battle"
}


def life_1(*args, **kwargs):
    """
    !cc life_1 [slot #]
    Life-like effect, remove wounded status and restore some HP.

    Precondition: must be in battle, target must be valid and dead
    """
    logging.info(f"life_1 | args {args}, kwargs {[*kwargs.keys()]}")
    targ = args[0]
    pmem = kwargs["party"][targ]
    # FIXME: move to Character class
    return set_status("-wounded", slot=targ, **kwargs) \
           + set_stat("cur_hp", val=pmem.max_hp / 16, slot=targ, **kwargs)


_life_2 = {
    # "precondition": (targ_valid, bool.__and__, has_status("wounded")),
    "status": "battle"
}


def life_2(*args, **kwargs):
    """
    !cc life_2 [slot #]
    Life2-like effect, remove wounded status and restore all HP.

    Precondition: must be in battle, target must be valid and dead
    """
    logging.info(f"life_2 | args {args}, kwargs {[*kwargs.keys()]}")
    targ = args[0]
    pmem = kwargs["party"][targ]
    # FIXME: move to Character class
    return set_status("-wounded", slot=targ, **kwargs) \
           + set_stat("cur_hp", val=pmem.max_hp, slot=targ, **kwargs)


_life_3 = {
    #"precondition": (targ_valid,),
    "status": "battle"
}


def life_3(*args, **kwargs):
    """
    !cc life_3 [slot #]
    Life3-like effect, adds life3 status to target.

    Precondition: must be in battle, target must be valid
    """
    logging.info(f"life_3 | args {args}, kwargs {[*kwargs.keys()]}")
    targ = args[0] if len(args) > 0 else random.randint(0, 3)
    return set_status("life3", slot=targ, **kwargs)


def set_stat(stat, val, slot=0, **kwargs):
    logging.info(f"set_stat | stat / val ({stat} / {val}), kwargs {[*kwargs.keys()]}")
    slot = int(slot)
    if slot < 0 or slot >= 4:
        raise IndexError(f"Invalid party slot {slot}.")

    c = kwargs["party"][slot]
    c.change_stat(stat, int(val))
    return write_arbitrary(*map(hex, c.flush()))


def set_name(name, actor=0, **kwargs):
    logging.info(f"set_name | name {name}, actor ({actor})")

    actor = int(actor)
    if actor < 0 or actor >= 16:
        raise IndexError(f"Invalid party index {actor}.")

    # FIXME: Automatically truncates
    _name = read.transcode(name)[:6]
    name = [255] * 6
    name[:len(_name)] = _name

    write = []
    off = actor * 37
    for byt, chr in zip(range(0x1602, 0x1608), name):
        write.extend([hex(byt + off), hex(chr)])
    return write_arbitrary(*write)


def nullify_element(elem, toggle=True, **kwargs):
    null_elems = kwargs["bf"]["null_elems"]
    logging.info(f"nullify_element | elem ({elem}), toggle: {toggle}, current value {hex(null_elems)}")
    if not _validate_elems(elem):
        raise ValueError(f"Invalid element {elem}")

    mask = ELEM_FLAGS[elem]
    if toggle is not None:
        null_elems ^= mask
    else:
        null_elems |= mask

    return write_arbitrary(*["0x3EC8", hex(null_elems)])


def fallen_one(**kwargs):
    logging.info(f"fallen_one | kwargs {[*kwargs.keys()]}")
    write = []
    for c in kwargs["party"]:
        # FIXME: check to make sure the character actually exists
        c.change_stat("cur_hp", 1)
        write.extend(list(map(hex, c.flush())))
    return write_arbitrary(*write)


def trigger_battle(**kwargs):
    # set 16-bit value at 0x1F6E to max
    to_write = ["0x1F6E", "0xFF", "0x1F6F", "0xFF"]
    return write_arbitrary(*to_write)