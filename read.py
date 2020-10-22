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
        try:
            logf = [json.loads(line) for line in fin.readlines() if line]
        except Exception as e:
            print(e)
    logf = [l for l in logf if l["frame"] >= last_frame]

    cmds = []
    for status in sorted(logf, key=lambda l: l["frame"]):
        # check for map change
        # FIXME: need the mapid to area map
        if status["map_id"] != last_status.get("map_id", None):
            cmds.append("!nextarea")

        # check for kills
        lkills = last_status.get("kills", {})
        for char, k in status.get("kills", {}).items():
            diff = k - lkills.get(char, 0)
            if diff > 0:
                cmds.append(f"!event enemykill {char} {diff}")

        print("emu>", cmds[-1])

        last_status = status

    return cmds, last_status