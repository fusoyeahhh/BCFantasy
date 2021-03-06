from bcfcc import MemoryRegion
from ff6_flags import ITEMS


class Inventory(MemoryRegion):

    _rev_lookup = {v: k  for k, v in ITEMS.items()}

    def __init__(self):
        super().__init__()
        self._inv = {}
        self.empty_slots = []
        self.item_slots = {}

        # Outgoing write instructions
        self._queue = []

    def _from_memory_range(self, memfile):
        super()._from_memory_range(memfile)

        for i in range(255):
            qty = self.mem[0x2689 + 5 * i]
            if qty == 0:
                self.empty_slots.append(i)
                continue

            # $2686 Item Index
            self._inv[i] = item = {}
            item["index"] = self.mem[0x2686 + 5 * i]
            # $2687 u?tjws??
            #       u: not usable in battle
            #       t: can be thrown
            #       j: can be used with jump
            #       w: is a weapon
            #       s: is a shield
            item["battle_flags"] = self.mem[0x2687 + 5 * i]
            # $2688 abcdefgh Item Targetting Flags
            #       a: random target
            #       b: enemy target by default
            #       c: multi-target possible
            #       d: auto-accept default target
            #       e: target all enemies or all allies
            #       f: target all enemies and all allies
            #       g: target can't switch between enemies and allies
            #       h: target single ally or enemy
            item["targ_flags"] = self.mem[0x2688 + 5 * i]
            # $2689 Item Quantity
            item["qty"] = qty
            # $268A ----4321 Item Equippability (set if character can't equip the item)
            item["equip_flags"] = self.mem[0x268A + 5 * i]

            # For faster cross-referencing later
            # NOTE that the last item iterated over will be the one recorded if there are duplicates
            self.item_slots[item["index"]] = i

    def change_qty(self, item, new_qty):
        # get item index
        _item = self._rev_lookup[item]

        # find if the item is already in the inventory
        if _item in self.item_slots:
            idx = self.item_slots[_item]
            # change quantity --- internal bookkeeping
            self._inv[idx]["qty"] = new_qty
            # write to queue
            _item = 5 * idx + 0x2689
            # Change qty of indexed item slot
            self._queue += [_item, new_qty]
            return

        # Not in inventory, find open spot and add
        # FIXME: account for completely full inventory
        idx = self.empty_slots.pop(0)
        _item = self._inv[idx] = self._create_item(_item, qty=new_qty)
        # Write full item to new slot
        idx = 5 * idx + 0x2686
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
            "battle_flags": 0x0,
            # Default: ???
            "targ_flags": 0x0,
            # Default: equippable by all
            "equip_flags": 0x0
        }
        _item.update(kwargs)
        return _item

    def commit(self):
        for i in range(len(self._queue) // 2):
            addr, val = self._queue[2 * i], self._queue[2 * i + 1]
            self[addr] = val

    def flush(self, commit=False):
        if commit:
            self.commit()

        q, self._queue = self._queue[:], []
        return q