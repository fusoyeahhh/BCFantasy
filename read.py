import os
import json
import time

_QUIET = True

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")

def parse_log_file(path="logfile.txt", last_frame=-1):

    if not os.path.exists(os.path.join(os.getcwd(), path)):
        return {}

    nerrors = 0
    #last_frame = last_status.get("frame", None) or last_frame
    with open(os.path.join(os.getcwd(), path), "r") as fin:
        logf = []
        for line in fin.readlines():
            try:
                # FIXME: this actually needs fixed on the Lua side
                line = line.replace(",}", "}").replace(", }", "}")
                line = json.loads(line or "{}")
                if line.get("frame", -float("inf")) > last_frame:
                    logf.append(line)
            except Exception as e:
                if not _QUIET:
                    print("JSON reading failed:", e)
                    print(line)
                nerrors += 1

    if len(logf) > 0:
        print(f"{time.time()}: Read {len(logf)} new lines, with {nerrors} errors.")
    return logf

def read_memory(fname="memfile"):
    with open(fname, "rb") as fin:
        bytes = fin.read()

    mem = {}
    while len(bytes) > 0:
        addr = bytes[1] + bytes[0] * 0x100
        size = bytes[3] + bytes[2] * 0x100
        # Find out why this is being reported one smaller than normal
        size += 1
        #print(hex(addr), hex(size), len(bytes))
        mem[addr] = bytes[4:4 + size]
        bytes = bytes[4 + size:]
        #print(bytes)

    return mem