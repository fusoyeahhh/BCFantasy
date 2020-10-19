import os

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")
