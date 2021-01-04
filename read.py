import sys
import os
import json
import time
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

_QUIET = False

# Numbers from
# https://github.com/subtractionsoup/beyondchaos/blob/master/tables/dialoguetext.txt
# Upper case
_CHARS = {128 + i: chr(j) for i, j in enumerate(range(65, 65 + 26))}
# Lower case
_CHARS.update({154 + i: chr(j) for i, j in enumerate(range(97, 97 + 26))})
# Numbers
_CHARS.update({180 + i: chr(j) for i, j in enumerate(range(48, 48 + 10))})
# FIXME: Will probably need symbols at some point
_CHARS[191] = "?"
_CHARS[255] = ""

def translate(word):
    #return "".join(map(chr, [(c - 63) if c < 154 else (c - 57)
                              #for c in word if c != 255]))
    return "".join([_CHARS[i] for i in word])

def read_local_queue(path='local'):
    fifo = os.open(path, os.O_NONBLOCK)
    data = os.read(fifo, 1024)
    os.close(fifo)
    return data.decode().split("\n")

def parse_log_file(path="logfile.txt", last_frame=-1):

    logf = []
    logpath = os.path.join(os.getcwd(), path)
    if not os.path.exists(logpath):
        logging.error(f"Could not find logfile, expected at {logpath}")
        return logf

    nerrors, skipped = 0, 0
    #last_frame = last_status.get("frame", None) or last_frame
    with open(logpath, "r") as fin:
        lines = fin.readlines()
        logging.debug(f"{logpath} opened for reading, {len(lines)} to process.\nLast frame processed {last_frame}.")
        for line in lines:
            try:
                # FIXME: this actually needs fixed on the Lua side
                line = line.replace(",}", "}").replace(", }", "}")
                line = json.loads(line or "{}")
                if line.get("frame", -float("inf")) > last_frame:
                    logf.append(line)
                else:
                    skipped += 1
            except Exception as e:
                if not _QUIET:
                    print("JSON reading failed:", e)
                    print(line)
                nerrors += 1

    if len(logf) > 0:
        logging.debug(f"{time.time()}: Read {len(logf)} new lines, with {nerrors} errors. Skipped {skipped} entries.")
    return logf

def read_spoiler(spoilerf):
    with open(spoilerf) as fout:
        lines = fout.readlines()

    # Get seed
    _, _, flags, seed = lines[0].split()[-1].strip().split(".")

    # Skip to characters section
    line = lines.pop(0)
    while "CHARACTERS" not in line:
        line = lines.pop(0)
    lines = lines[2:]

    char_map = []
    while True:
        _map = {}
        line = lines.pop(0)

        # This is our stopping condition. The line contains no index number to parse
        try:
            id, _map["cname"] = line.split(" ")
            int(id.replace(".", ""))
        except ValueError:
            break

        _map["cname"] = _map["cname"].strip()
        lines.pop(0)
        _map["appearance"] = lines.pop(0).replace("Looks like: ", "").strip()
        _map["orig"] = lines.pop(0).split(" ")[-1].strip().lower()
        char_map.append(_map)
        while line.strip() != "":
            line = lines.pop(0)

    # Skip to music section
    line = lines.pop(0)
    while "MUSIC" not in line:
        line = lines.pop(0)
    lines = lines[2:]

    music_map = []
    while True:
        _map = {}
        music_map.append(_map)
        line = lines.pop(0)
        if "->" not in line:
            break
        line, mapped = line.split("->")
        mapped = mapped.strip()
        sid, mapping = map(str.strip, line.split(":"))
        _map["song_id"] = int(sid, 16)
        _map["new"] = mapped
        _map["orig"] = mapping
        line = lines.pop(0).strip()
        _map["descr"] = line
        if line == "":
            continue

        _map["descr"] += " | " + lines.pop(0).strip()
        lines.pop(0)

    return flags, seed, (music_map, char_map)


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

def write_instructions(byte_arr, fname="instr", check_compl=3):
    with open(fname, "wb") as fout:
        fout.write(bytearray(byte_arr))

    for _ in range(int(3)):
        time.sleep(1)
        if os.path.getsize(fname) == 0:
            break
    else:
        raise ValueError("Lua script did not seem to consume instruction file.")