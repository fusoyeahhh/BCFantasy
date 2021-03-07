import time
import logging
import sys
from bcf import read
from bcfcc import Character, Inventory

class _Queue(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self._q = []

    def make_task(self, cmd, name=None, user=None, state=None,
                             duration=None, delay=None, callback=None,
                             retries=3, enqueue=True):
        task = {
            "cmd": cmd,
            "user": user,
            "name": name,
            "delay": delay,
            "duration": duration,
            "state": state,
            "callback": callback,
            "retries": retries
        }
        if enqueue:
            self.enqueue(task)
        return task

    def enqueue(self, task):
        task["submitted"] = time.time()
        logging.info(f"enqueue | {task['user']} {task['name']} | Enqueued task at {task['submitted']}")
        self._q.append(task)

    def check(self, status=None):
        status = status or {}
        logging.debug(f"check | Checking queue with number of tasks {len(self._q)}")
        for _ in range(len(self._q)):
            task = self._q.pop(0)
            ctime = time.time()
            logging.debug(f"check | {task['user']} {task['name']} | Checking task at {ctime}")

            # Is this a delayed task?
            delay = task.get("delay", None)
            start = task.get("submitted", ctime)
            if delay is not None and ctime - start < delay:
                self._q.append(task)
                logging.debug(f"check | {task['user']} {task['name']} | Task unready | delay: {ctime} < {start + delay}")
                continue

            # pop task
            logging.info(f"check | {task['user']} {task['name']} | Task ready, firing...")
            yield task
            # FIXME: make exec state system
            if task["_exe_state"] == False:
                # Task was determined to be unready by caller
                self._q.append(task)
                continue
            elif task["_exe_state"] != True:
                # Task failed, provide reasoning
                logging.info(f"check | {task['user']} {task['name']} | Task failed, reason {task['_exe_state']}")
                continue
            logging.info(f"check | {task['user']} {task['name']} | Task completed successfully")

            # Check if there's an associated callback to enqueue
            if task["callback"] is not None:
                ctime = time.time()
                logging.info(f"check | {task['user']} {task['name']} | Task has callback, enqueueing at {ctime}")
                cback = task["callback"]
                cback["delay"] = task["duration"] or 0
                self.enqueue(cback)

        logging.debug(f"check | Done checking queue, tasks remaining: {len(self._q)}")

    def write(self, fname=None):
        ctime = time.time()
        status = []
        for t in self._q:
            status.append(f"{t['name']} ({t['user']})")
            if t['delay'] is not None:
                rem = int(t['submitted'] + t['delay'] - ctime)
                status[-1] += f" {rem} sec. remain"
            status = "\n".join(status)
        if fname is not None:
            with open(fname, "w") as fout:
                print(status, file=fout)

        return status

class CCQueue(_Queue):
    def __init__(self, memfile="memfile"):
        super().__init__()
        self.memfile = memfile

    # FIXME: we might need this to be its own state at some point
    def construct_game_context(self):
        # Construct game context
        party = [Character() for i in range(4)]
        for i in range(4):
            # FIXME: make one-step initialization
            party[i]._from_memory_range(self.memfile, slot=i)
        logging.info(f"cc | Read and init'd {len(party)} characters in party")

        eparty = [Character() for i in range(6)]
        for i in range(6):
            # FIXME: make one-step initialization
            eparty[i]._from_memory_range(self.memfile, slot=i + 4)
        logging.info(f"cc | Read and init'd {len(eparty)} entities in enemy party")

        mem = read.read_memory(self.memfile)
        bf = {"cant_run": mem[0xB1][0],
              "field_relics": mem[0x11DF][0],
              "null_elems": mem[0x3EC8][0]}

        inv = Inventory()
        inv._from_memory_range(self.memfile)
        logging.info(f"cc | Read and init'd {len(inv._inv)} inventory items")

        return {"party": party, "eparty": eparty, "bf": bf, "inv": inv, "field_ram": mem[0x1600]}

    def check(self, game_status=None, ignore_completion=False):
        # Avoid doing a check if we don't need to
        if len(self._q) == 0:
            return
        try:
            gctx = self.construct_game_context() if game_status else {}
        except Exception as e:
            logging.error(
                f"check | Couldn't construct game context. Exception information follows.")
            logging.error(str(type(e)) + " " + str(e))

        game_status = game_status or {}

        for cmdctx in super().check():
            cmd, name, user = cmdctx["cmd"], cmdctx.get("name", None), cmdctx.get("user", None)

            # State check
            in_battle = game_status.get("in_battle", None)
            if (cmdctx["state"] == "battle" and not in_battle) or (cmdctx["state"] == "field" and in_battle):
                logging.debug(f"check | {user} {name} | Task unready | "
                              f"status: {cmdctx['state']} != {in_battle}")
                cmdctx["_exe_state"] = False
                continue

            # Execute command
            try:
                logging.info(f"check | Calling into cc subcommand {cmd} ({name}) "
                             f"| ignoring_completion: {ignore_completion}")
                if ignore_completion:
                    read.write_instructions(cmd(**gctx), check_compl=False)
                else:
                    read.write_instructions(cmd(**gctx))
                logging.info(f"check | Finished {name}")
                cmdctx["_exe_state"] = True
            except Exception as e:
                retries = cmdctx["retries"] = cmdctx.get("retries", 0) - 1
                if retries > 0:
                    logging.error(f"check | {user} {name} | Task execution unsuccessful. "
                                  f"Will retry ({retries} tries left) on next check. Last exception:")
                    logging.error(str(e))
                    cmdctx["_exe_state"] = False
                else:
                    logging.error(f"check | {user} {name} | Task execution unsuccessful. Task details:\n" +
                                  str(cmdctx) +
                                  "\nNo more retries left, dropping. Last exception:")
                    logging.error(str(e))
                    cmdctx["_exe_state"] = "NOADDTLRETRIES"


if __name__ == "__main__":
    ccq = CCQueue(memfile="../memfile")

    ccq.reset()
    ccq.check(None)

    def task(*args, **kwargs):
        print(args, kwargs)
        return []

    t = ccq.make_task(task, name="basic", user="user")
    print(ccq.write())
    ccq.check()

    t = ccq.make_task(task, name="statecheck", user="user", state="battle")
    ccq.check()
    ccq.check({"in_battle": False})
    ccq.check({"in_battle": True})

    t = ccq.make_task(task, name="delaycheck", user="user", delay=2)
    print("Checking delay logic")
    ccq.check()
    print("Sleeping")
    time.sleep(2)
    ccq.check()

    t2 = ccq.make_task(task, name="callback", user="user", enqueue=False)
    t1 = ccq.make_task(task, name="initial", user="user", duration=3, callback=t2)
    print("Triggering initial event")
    ccq.check()
    time.sleep(2)
    print("Checking duration logic")
    ccq.check()
    time.sleep(1)
    print("Waking to fire followup")
    ccq.check()

    def raise_problem():
        raise ValueError("Testing bad behavior")

    t = ccq.make_task(raise_problem, name="retrycheck", user="user")
    for _ in range(t["retries"] + 1):
        ccq.check()

    # With actual CC commands
    from bcfcc import activate_golem
    # This one is convenient because it has no arguments to preserve
    ccq.make_task(activate_golem, name='activate_golem', user="test", state="battle")
    print("[activate_golem] Checking state logic")
    ccq.check()
    ccq.check({"in_battle": True})