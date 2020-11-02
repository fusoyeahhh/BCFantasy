import os
import json

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")

def parse_log_file(path="logfile.txt", last_status={}, last_frame=-1):

    if not os.path.exists(os.path.join(os.getcwd(), path)):
        return {}

    last_frame = last_status.get("frame", None) or last_frame
    with open(os.path.join(os.getcwd(), path), "r") as fin:
        logf = []
        for line in fin.readlines():
            try:
                # FIXME: this actually needs fixed on the Lua side
                line = line.replace(",}", "}").replace(", }", "}")
                line = json.loads(line or "{}")
                if line.get("frame", -float("inf")) >= last_frame:
                    logf.append(line)
            except Exception as e:
                print("JSON reading failed:", e)
                print(line)

    print(f"Read {len(logf)} new lines.")

    cmds = []
    for status in sorted(logf, key=lambda l: l["frame"]):
        # check for map change
        if status["map_id"] != last_status.get("map_id", None):
            cmds.append(f"!set area={status['map_id']}")
            print("emu>", cmds[-1])

        # check for kills
        lkills = last_status.get("kills", {})
        for char, k in status.get("kills", {}).items():
            diff = k - lkills.get(char, 0)
            if diff > 0:
                cmds.append(f"!event enemykill {char} {diff}")
                print("emu>", cmds[-1])

        last_status = status

    print("Last status:", last_status)

    return cmds, last_status