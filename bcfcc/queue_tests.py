import time
from bcfcc import activate_golem, add_gp
from bcfcc.cmdimpl import AddGP, MoogleCharm, Remedy, RandomRelicEffect, MirrorButtons, GiveItem, \
                          GiveRareRelic, RandomStatus, CantRun
from bcfcc.queue import CCQueue

if __name__ == '__main__':
    ccq = CCQueue(memfile="memfile")

    game_state = {"in_battle": True}

    # With actual CC commands
    # This one is convenient because it has no arguments to preserve
    # ccq.make_task(activate_golem, name='activate_golem', user="test", state="battle")
    # print("[activate_golem] Checking state logic")
    # ccq.check(game_state, ignore_completion=True)
    # ccq.check({"in_battle": True}, ignore_completion=True)
    #
    # ccq.make_task(add_gp, name="add_gp", user="test")
    # print("[add_gp] Checking queue execution logic")
    # ccq.check(game_state, ignore_completion=True)
    # ccq.reset()

    # Generate game context
    gctx = ccq.construct_game_context()

    # Generate a new instance of CC command
    print("[AddGP] Checking queue execution logic")
    req = AddGP("test")
    req._add_to_queue(ccq)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[CantRun] Checking can't run execution logic")
    req = CantRun("test")
    req._add_to_queue(ccq)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[RandomStatus] Checking random status logic")
    req = RandomStatus("test")
    inv = ccq.construct_game_context()["inv"]
    req._add_to_queue(ccq, 1)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[GiveItem] Checking inventory logic")
    req = GiveItem("test")
    inv = ccq.construct_game_context()["inv"]
    req._add_to_queue(ccq, [*inv.item_slots.keys()][0], 1)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[GiveRandomRelic] Checking random relic logic")
    req = GiveRareRelic("test")
    req._add_to_queue(ccq)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[Remedy] Checking in_battle logic")
    req = Remedy("test")
    req._add_to_queue(ccq, 1)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[RandomRelicEffect] Checking random relic effects")
    req = RandomRelicEffect("test")
    req._add_to_queue(ccq)
    print(ccq.write())
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    ccq.reset()

    print("[MoogleCharm] Checking queue delay and effect duration extension logic")
    req = MoogleCharm("test", duration=10)
    req._add_to_queue(ccq)
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    print("Sleeping for 2 seconds to check duration logic")
    time.sleep(2)
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    print("Increasing duration by 10 seconds.")
    req._add_to_queue(ccq)
    print(ccq.write())

    print("[MirrorButtons] Checking button trans / inverse trans")
    req = MirrorButtons("test", duration=1)
    req._add_to_queue(ccq)
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())
    print("Sleeping for 2 seconds to check duration logic")
    time.sleep(2)
    ccq.check(game_state, ignore_completion=True)
    print(ccq.write())