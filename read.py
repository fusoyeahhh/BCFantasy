import os
import json

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")

def parse_log_file(path="logfile.txt", last_frame=-1):

    if not os.path.exists(os.path.join(os.getcwd(), path)):
        return {}

    #last_frame = last_status.get("frame", None) or last_frame
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
    return logf