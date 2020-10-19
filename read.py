import os
import json

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")

def parse_log_file(path="logfile.txt"):

    if not os.path.exists(os.path.join(os.getcwd(), path)):
        return {}

    with open(os.path.join(os.getcwd(), path), "r") as fin:
        return json.load(fin)


