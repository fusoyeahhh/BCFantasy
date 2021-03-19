from bcfcc import MemoryRegion
from common.ff6_flags import ITEMS


class Inventory(MemoryRegion):

    _rev_lookup = {v: k  for k, v in ITEMS.items()}

    def __init__(self):
        super().__init__()
        # Battle inventory
        self._inv = {}
        # Field inventory
        self._finv = {}
        self.empty_slots = []
        self.item_slots = {}

        # Outgoing write instructions
        self._queue = []

    def _from_memory_range(self, memfile):
        super()._from_memory_range(memfile)

        # Field inventory
        for menu_slot, iaddr in enumerate(range(0x1869, 0x1968)):
            if self.mem[iaddr] == 0xFF:
                self.empty_slots.append(menu_slot)
                # NOTE: The assumption here is that the empty slots in field and battle are equivalent
                continue

            # map index to quantity
            self._finv[menu_slot] = self.mem[iaddr + 256]

            # For faster cross-referencing later
            # NOTE that the last item iterated over will be the one recorded if there are duplicates
            self.item_slots[self.mem[iaddr]] = menu_slot

            # Battle inventory
            qty = self.mem[0x2689 + 5 * menu_slot]

            # $2686 Item Index
            self._inv[menu_slot] = item = {}
            item["index"] = self.mem[0x2686 + 5 * menu_slot]
            # $2687 u?tjws??
            #       u: not usable in battle
            #       t: can be thrown
            #       j: can be used with jump
            #       w: is a weapon
            #       s: is a shield
            item["battle_flags"] = self.mem[0x2687 + 5 * menu_slot]
            # $2688 abcdefgh Item Targetting Flags
            #       a: random target
            #       b: enemy target by default
            #       c: multi-target possible
            #       d: auto-accept default target
            #       e: target all enemies or all allies
            #       f: target all enemies and all allies
            #       g: target can't switch between enemies and allies
            #       h: target single ally or enemy
            item["targ_flags"] = self.mem[0x2688 + 5 * menu_slot]
            # $2689 Item Quantity
            item["qty"] = qty
            # $268A ----4321 Item Equippability (set if character can't equip the item)
            item["equip_flags"] = self.mem[0x268A + 5 * menu_slot]

    def change_qty(self, item, new_qty, skip_binv=False):
        # respect byte values
        new_qty = max(0, min(new_qty, 255))
        # get item index
        item_id = self._rev_lookup[item] if isinstance(item, str) else int(item)

        # find if the item is already in the inventory
        if item_id in self.item_slots:
            menu_slot = self.item_slots[item_id]
            # change quantity --- internal bookkeeping
            self._finv[menu_slot] = new_qty
            # Change qty of indexed item slot
            self._queue += [menu_slot + 0x1969, new_qty]

            if not skip_binv:
                # change quantity --- internal bookkeeping
                self._inv[menu_slot]["qty"] = new_qty
                # write to queue
                _item = 5 * menu_slot + 0x2689
                # Change qty of indexed item slot
                self._queue += [_item, new_qty]
            return

        # Not in inventory, find open spot and add
        # FIXME: account for completely full inventory
        empty_slot = self.empty_slots.pop(0)

        self.item_slots[item_id] = empty_slot
        self._finv[empty_slot] = new_qty
        self._queue += [empty_slot + 0x1869, item_id, empty_slot + 0x1969, new_qty]
        
        if not skip_binv:
            _item = self._inv[empty_slot] = self._create_item(item_id, qty=new_qty)
            # Write full item to new slot
            idx = 5 * empty_slot + 0x2686
            self._queue += [idx, _item["index"],
                            idx + 1, _item["battle_flags"],
                            idx + 2, _item["targ_flags"],
                            idx + 3, _item["qty"],
                            idx + 4, _item["equip_flags"]]

    def _create_item(self, item, **kwargs):
        _item = {
            "index": item,
            # FIXME: other flags, we don't really know them unless they're already present
            # Not usable in battle, nor a piece of equipment
            "battle_flags": 0x20,
            # Default: ???
            "targ_flags": 0x0,
            # Default: equippable by all
            "equip_flags": 0x0
        }
        _item.update(kwargs)
        return _item

    def print(self):
        for itm, slot in self.item_slots.items():
            qty = self._finv[slot]
            print(slot, itm, ITEMS[itm], qty, "|", str(self._inv[slot]))

    def commit(self):
        for i in range(len(self._queue) // 2):
            addr, val = self._queue[2 * i], self._queue[2 * i + 1]
            self[addr] = val

    def flush(self, commit=False):
        if commit:
            self.commit()

        q, self._queue = self._queue[:], []
        return q