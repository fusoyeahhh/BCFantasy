import os
from bcf import read
#from bcfcc import Character
import bcfcc

if __name__ == "__main__":

    # Do testing
    # Must have a memfile to work with
    memfile = "../memfile"
    assert os.path.exists(memfile)

    party = [bcfcc.Character() for i in range(4)]
    for i in range(4):
        # FIXME: make one-step initialization
        party[i]._from_memory_range(memfile, slot=i)

    eparty = [bcfcc.Character() for i in range(6)]
    for i in range(6):
        # FIXME: make one-step initialization
        eparty[i]._from_memory_range(memfile, slot=i + 4)

    gctx = {"party": party, "eparty": eparty}
    gctx["bf"] = {"cant_run": read.read_memory(memfile)[0xB1][0]}

    #
    # Can't run
    #
    print("--- Can't run (no toggle)")
    print("!cc cant_run")
    print(bcfcc.cant_run(**gctx))

    print("--- Can't run (with toggle)")
    # FIXME: no user argument for this yet
    print("!cc cant_run")
    print(bcfcc.cant_run(True, **gctx))

    #
    # Set status
    #
    print("--- Set status (set poison, slot 0)")
    print("!cc set_status poison 0")
    print(bcfcc.set_status("poison", 0, **gctx))

    print("--- Set status (remove poison, slot 0)")
    print("!cc set_status -poison 0")
    print(bcfcc.set_status("-poison", 0, **gctx))

    print("--- Set status (set poison, slot 3)")
    print("!cc set_status poison 3")
    print(bcfcc.set_status("poison", 3, **gctx))

    #
    # Set stats
    #
    print("--- Set stat (evade=0, slot 0)")
    print("!cc set_stat evade 0 0")
    print(bcfcc.set_stat("evade", 0, 0, **gctx))

    print("--- Set stat (evade=0, slot 3)")
    print("!cc set_stat evade 0 3")
    print(bcfcc.set_stat("evade", 0, 3, **gctx))

    print("--- Set stat (vigor=1, slot 1)")
    print("!cc set_stat vigor 1 1")
    # Should be multiplied by 2
    print(bcfcc.set_stat("vigor", 1, 1, **gctx))

    #
    # Fallen One
    #
    print("--- Fallen One")
    print("!cc fallen_one")
    print(bcfcc.fallen_one(**gctx))

    #
    # Activate Golem
    #
    print("--- Activate Golem (default HP)")
    print("!cc activate_golem")
    print(bcfcc.activate_golem(**gctx))

    # FIXME: no user setting for this yet
    print("--- Activate Golem (custom HP)")
    print("!cc activate_golem")
    print(bcfcc.activate_golem(1234, **gctx))

    #
    # OLE!
    #
    print("--- Ole Cape")
    print("!cc ole_cape")
    print(bcfcc.ole_cape(**gctx))

    #
    # Nullify element
    #
    print("--- Nullify Element (fire)")
    print("!cc null_elem")
    gctx["bf"]["null_elems"] = 0x0
    print(bcfcc.nullify_element("fire", **gctx))

    print("--- Nullify Element (poison)")
    print("!cc null_elem")
    print(bcfcc.nullify_element("poison", **gctx))

    #
    # Change name
    #
    print("--- Change name (normal)")
    print("!cc change_name Test 0")
    print(bcfcc.set_name("Test", slot=0, **gctx))

    print("--- Change name (too long, bad chars, slot 3)")
    print("!cc change_name T#esting 3")
    print(bcfcc.set_name("T#esting", actor=3, **gctx))

    #
    # Trigger battle
    #
    print("--- Trigger battle")
    print("!cc pick_fight")
    print(bcfcc.trigger_battle(**gctx))

    #
    # Moogle charm
    #
    print("--- Moogle charm (toggle on)")
    print("!cc moogle_charm")
    gctx["bf"]["field_relics"] = 0x0
    print(bcfcc.moogle_charm(**gctx))

    print("--- Moogle charm (toggle off)")
    print("!cc moogle_charm")
    gctx["bf"]["field_relics"] = 0x2
    print(bcfcc.moogle_charm(**gctx))

    #
    # Random status
    #
    print("--- Random status")
    print("!cc random_status")
    print(bcfcc.random_status(0, **gctx))

    #
    # Life / revive spells
    #
    print("--- Life spells")
    print("!cc life1 0")
    print(bcfcc.life_1(0, **gctx))
    print("!cc life2 0")
    print(bcfcc.life_2(0, **gctx))
    print("!cc life3 0")
    print(bcfcc.life_3(0, **gctx))

    #
    # Add GP
    #
    print("--- add_gp (default)")
    print("!cc add_gp")
    print(bcfcc.add_gp(**gctx))

    print("--- add_gp (with value, not enabled for CC)")
    print("!cc add_gp 10")
    print(bcfcc.add_gp(10, **gctx))
    print("!cc add_gp -10")
    print(bcfcc.add_gp(-10, **gctx))

    #
    # Remedy
    #
    print("--- Remedy")
    print("!cc remedy 0")
    print(bcfcc.remedy(0, **gctx))