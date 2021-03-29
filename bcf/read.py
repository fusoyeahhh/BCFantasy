import sys
import os
import json
import time
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Upper case
_CHARS = {128 + i: chr(j) for i, j in enumerate(range(65, 65 + 26))}
# Lower case
_CHARS.update({154 + i: chr(j) for i, j in enumerate(range(97, 97 + 26))})
# Numbers
_CHARS.update({180 + i: chr(j) for i, j in enumerate(range(48, 48 + 10))})
# FIXME: Will probably need symbols at some point
_CHARS[191] = "?"
_CHARS[197] = "."
_CHARS[255] = ""

def translate(word):
    """
    Translate integer values to the FF6 character equivalents. Drops any value which does not have a character mapping.

    Numbers from https://github.com/subtractionsoup/beyondchaos/blob/master/tables/dialoguetext.txt

    :param word: list of integers to convert
    :return: string translation
    """
    return "".join([_CHARS.get(i, "?") for i in word])

def transcode(word):
    """
    Transcode ASCII characters to the FF6 integer code equivalents. Drops any value which does not have a character mapping.

    This is, roughly, the inverse of `translate`.

    :param word: (str) characters to convert
    :return: list of integers corresponding to characters
    """
    rmap = {v: k for k, v in _CHARS.items()}
    return [rmap[c] for c in word if c in rmap]

def parse_log_file(path="logfile.txt", last_frame=-1):
    """
    Parse the emulator / lua create log file. This file is assumed to have one JSON-type string on each line.

    :param path: Path to the emulator logfile, default is 'logfile.txt'
    :param last_frame: (int) Last frame that was processed by the bot. Lines which have a frame count smaller than this are discarded.
    :return: An array of JSON-parsed dictionary-style status updates.
    """

    logf = []
    logpath = os.path.join(os.getcwd(), path)
    if not os.path.exists(logpath):
        logging.error(f"Could not find logfile, expected at {logpath}")
        return logf

    nerrors, skipped = 0, 0
    with open(logpath, "r") as fin:
        lines = fin.readlines()
        logging.debug(f"{logpath} opened for reading, {len(lines)} to process.\nLast frame processed {last_frame}.")
        for line in lines:
            try:
                # FIXME: this actually needs fixed on the Lua side
                line = json.loads(line.replace(",}", "}").replace(", }", "}") or {})
                if line.get("frame", -float("inf")) > last_frame:
                    logf.append(line)
                else:
                    skipped += 1
            except Exception as e:
                logging.error("JSON reading failed:\n" + str(e))
                logging.debug(line)
                nerrors += 1

    # Emit some information if there's nontrivial information to process
    if len(logf) > 0:
        logging.debug(f"{time.time()}: Read {len(logf)} new lines, with {nerrors} errors. Skipped {skipped} entries.")
    return logf

def read_spoiler(spoilerf):
    """
    Read and parse the spoiler file generated by BC. Generates a mapping of sprite / character as well as music information.

    :param spoilerf: Path to the spoiler file.
    :return: A tuple of three items: the flags (string), the seed (string), and a tuple of the character sprite and music maps.
    """
    with open(spoilerf) as fout:
        lines = fout.readlines()

    # Get seed
    _, _, flags, seed = lines[0].split()[-1].strip().split(".")

    # Skip to characters section
    line = lines.pop(0)
    while "CHARACTERS" not in line:
        line = lines.pop(0)
    # Drop two blank lines
    lines = lines[2:]

    # Parse character information
    char_map = []
    while True:
        # Mapping information for a single character
        _map = {}
        # Line to parse
        line = lines.pop(0)

        # This is our stopping condition. The line contains no index number to parse
        try:
            id, _map["cname"] = line.split(" ")
            # If this doesn't parse, it throws an exception and we break out
            int(id.replace(".", ""))
        except ValueError:
            break

        # New character name
        _map["cname"] = _map["cname"].strip()
        lines.pop(0)
        # New sprite
        _map["appearance"] = lines.pop(0).replace("Looks like: ", "").strip()
        # Original character name
        _map["orig"] = lines.pop(0).split(" ")[-1].strip().lower()
        char_map.append(_map)
        # Skip empty lines until the next processable line
        while line.strip() != "":
            line = lines.pop(0)

    # Skip to music section
    line = lines.pop(0)
    while "MUSIC" not in line:
        line = lines.pop(0)
    lines = lines[2:]

    music_map = []
    while True:
        # Mapping information for a single song
        _map = {}
        music_map.append(_map)
        line = lines.pop(0)

        # This is the indicator that there's a mapping to process
        if "->" not in line:
            break

        line, mapped = line.split("->")
        mapped = mapped.strip()
        sid, mapping = map(str.strip, line.split(":"))
        # Integer song ID (hex)
        _map["song_id"] = int(sid, 16)
        # New song name
        _map["new"] = mapped
        # Original song name
        _map["orig"] = mapping

        # Song arranger / composer information
        line = lines.pop(0).strip()
        _map["descr"] = line

        # If there is no additional information do not generate a description
        if line == "":
            continue

        _map["descr"] += " | " + lines.pop(0).strip()
        # Skip blank line
        lines.pop(0)

    return flags, seed, (music_map, char_map)


def read_memory(fname="memfile", ntries=3):
    """
    Read a binary memory file generated from copying a section of the SNES emulator RAM. Assumed to be composed of an address, length, and array corresponding to that length.

    :param fname: Path to the memory file. Default is 'memfile'
    :return: A dictionary of address / memory chunk pairs
    """
    for _ in range(ntries):
        # This is here because Lua is garbage.
        try:
            with open(fname, "rb") as fin:
                bytes = fin.read()
            break
        except:
            time.sleep(0.1)
    else:
        raise ValueError(f"Could not read file {fname} after {ntries} tries.")

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

        # FIXME: This is to work around the fact that Lua doesn't understand zero index arrays
        # It iterates from 1, then gets to the end of the region, and *then* processes the zero
        # index
        mem[addr] = mem[addr][-1:] + mem[addr][:-1]


    return mem

def write_instructions(byte_arr, fname="instr", check_compl=3):
    """
    Write a set of instructions for the Lua script to write to the SNES RAM. The format is assumed to be address / value pairings.

    :param byte_arr: bytearray to be written to the file
    :param fname: The file to be written to, default is 'instr'.
    :param check_compl: (Unnused)
    :return: None
    """
    with open(fname, "wb") as fout:
        fout.write(bytearray(byte_arr))

    if not check_compl:
        return

    for _ in range(int(check_compl)):
        time.sleep(0.1)
        if os.path.getsize(fname) == 0:
            break
    else:
        raise ValueError("Lua script did not seem to consume instruction file.")