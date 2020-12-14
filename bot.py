import os
import errno
import time
import datetime
import shutil
import numpy
import pandas
import json
from twitchio.ext import commands
from twitchio.dataclasses import User
import glob

import read

with open("config.json") as fin:
    opts = json.load(fin)

# add additional admin names here
_AUTHORIZED = opts.pop("admins", {})
_ENABLE_CC = opts.pop("crowd_control", None)
_GITHUB_DOC_BASE = opts.pop("doc_url", "https://github.com/fusoyeahhh/BCFantasy/blob/main/data/")

MUSIC_INFO, CHAR_MAP = {}, {}
_FLAGS, _SEED = None, None
_SPOILER_LOG = opts.pop("spoiler", None)
if _SPOILER_LOG is not None:
    _FLAGS, _SEED, maps = read.read_spoiler(_SPOILER_LOG)
    mmaps, cmaps = maps
    MUSIC_INFO = pandas.DataFrame(mmaps).dropna()
    CHAR_MAP = pandas.DataFrame(cmaps).dropna()
_FLAGS = opts.pop("flags", _FLAGS)
_SEED = opts.pop("seed", _SEED)
_SEASON_LABEL = opts.pop("season", None)
_CHKPT_DIR = opts.pop("checkpoint_directory", "./checkpoint/")

bot = commands.Bot(**opts)

_CHAT_READBACK = True

_ACTOR_MAP = {
    0x0: "Terra",
    0x1: "Locke",
    0x2: "Cyan",
    0x3: "Shadow",
    0x4: "Edgar",
    0x5: "Sabin",
    0x6: "Celes",
    0x7: "Strago",
    0x8: "Relm",
    0x9: "Setzer",
    0xA: "Mog",
    0xB: "Gau",
    0xC: "Gogo",
    0xD: "Umaro",
    0xE: "Guest actor 1",
    0xF: "Guest actor 2"
}

def _write(ctx, strn, prefix="BCFBot>"):
    pass

def _authenticate(ctx):
    print(ctx.author.name, _AUTHORIZED)
    print(ctx.author.name in _AUTHORIZED)
    return ctx.author.name in _AUTHORIZED

_AREA_INFO = pandas.read_csv("data/bc_fantasy_data_areas.csv")
_BOSS_INFO = pandas.read_csv("data/bc_fantasy_data_bosses.csv")
_CHAR_INFO = pandas.read_csv("data/bc_fantasy_data_chars.csv")
_MAP_INFO = pandas.read_csv("data/map_ids.csv")
_MAP_INFO["id"] = [int(n, 16) for n in _MAP_INFO["id"]]
_MAP_INFO = _MAP_INFO.set_index("id")

COMMANDS = {}
ADMIN_COMMANDS = {}

HISTORY = {}

LOOKUPS = {
    "area": ("Area", _AREA_INFO),
    "char": ("Character", _CHAR_INFO),
    "boss": ("Boss", _BOSS_INFO),
}

_USERS = {}

_CONTEXT = {
    "area": None,
    "boss": None,
    "song": None
}

#
# Parsing
#
def convert_buffer_to_commands(logf, **kwargs):
    cmds = []
    last_status = kwargs.get("last_status", {})
    for status in sorted(logf, key=lambda l: l["frame"]):
        # parse current party
        if "party" in status:
            try:
                status["party"] = {_ACTOR_MAP[int(act)]: [max(int(c), 0) for c in name.strip().split()]
                                                     for act, name in status["party"].items()
                                                                        if int(act) in _ACTOR_MAP}

                cparty = [s.lower() for s in status.get("cparty", [])]
                in_cparty = []
                for act in status["party"]:
                    if act.lower() in cparty:
                        in_cparty.append(act)
                    status["party"][act] = \
                        "".join(map(chr, [(c - 63) if c < 154 else (c - 57)
                                                       for c in status["party"][act]
                                                            if c != 255]))
                for act in (in_cparty if status["in_battle"] else []):
                    status["party"][f"({act})"] = status["party"].pop(act)

            except Exception as e:
                print("Couldn't parse party: ", status["party"])

        # music id lookup
        # FIXME: do this the same way as other contexts
        music_id = status.get("music_id", None)
        if music_id is not None and len(MUSIC_INFO) > 0:
            print(f"Setting music context to {music_id}")
            _CONTEXT["music"] = MUSIC_INFO.set_index("song_id")["new"].get(music_id, "Unknown")

        # check for map change
        if status["map_id"] != last_status.get("map_id", None):
            cmds.append(f"!set area={status['map_id']}")
            print("emu>", cmds[-1])

        # check for boss encounter
        if status["in_battle"] and status["eform_id"] != last_status.get("eform_id", None):
            print(f"New encounter: {status['eform_id']}, is miab? {status['is_miab']}")
            if int(status["eform_id"]) in _BOSS_INFO["Id"].values:
                cmds.append(f"!set boss={status['eform_id']}")
                print("emu>", cmds[-1])

            # Check for miab
            if status.get("is_miab", False):
                cmds.append(f"!event miab")
                print("emu>", cmds[-1])

        # check for kills
        lkills = last_status.get("kills", {})
        for char, k in status.get("kills", {}).items():
            diff = k - lkills.get(char, 0)
            if diff > 0 and char != "NIL_lookup":
                # FIXME: should probably in_check battle status
                etype = "boss" if int(status["eform_id"]) in _BOSS_INFO["Id"].values else "enemy"
                cmds.append(f"!event {etype}kill {char} {diff}")
                print("emu>", cmds[-1])

        # check for deaths
        ldeaths = last_status.get("deaths", {})
        for char, k in status.get("deaths", {}).items():
            diff = k - ldeaths.get(char, 0)
            etype = "b" if int(status["eform_id"]) in _BOSS_INFO["Id"].values else ""
            if diff > 0 and char != "NIL_lookup":
                cmds.append(f"!event {etype}chardeath {char} {diff}")
                print("emu>", cmds[-1])

        last_status = status

    if len(logf) > 0:
        print("Last status:", last_status)

    return cmds, last_status

#
# Utils
#

def _set_context(content):
    try:
        selection = " ".join(content.split(" ")[1:])
        cat, item = selection.split("=")
        print(cat, item)

        # Preliminary mapid to area setting
        if cat == "area" and item.isdigit():
            item = int(item)
            if item in _MAP_INFO.index:
                item = _MAP_INFO.loc[item]["scoring_area"]
                # This map id exists, but is not mapped to an area
                if pandas.isna(item):
                    # FIXME: probably gonna break something
                    _CONTEXT["area"] = None
                    return True
            else:
                #raise ValueError(f"No valid area mapping for id {item}")
                print(f"No valid area mapping for id {item}")
                return True

        if cat == "boss" and item.isdigit():
            item = int(item)
            if item in set(_BOSS_INFO["Id"]):
                item = _BOSS_INFO.set_index("Id").loc[item]["Boss"]
            else:
                raise ValueError(f"No valid boss mapping for id {item} (this may be intended)")

        lookup, info = LOOKUPS[cat]
        # FIXME: zozo vs. mt. zozo
        item = _check_term(item, lookup, info)

        print(cat, item, _CONTEXT)
        if cat in _CONTEXT:
            _CONTEXT[cat] = item

        with open("context.json", "w") as fout:
            json.dump(_CONTEXT, fout, indent=2)

    except Exception as e:
        print(e)
        return False

    return True

def _chunk_string(inlist, joiner=", "):
    if len(inlist) == 0:
        return
    assert max([*map(len, inlist)]) < 500, \
                                "Can't fit all messages to buffer length"

    outstr = str(inlist.pop(0))
    while len(inlist) >= 0:
        if len(inlist) == 0:
            yield outstr
            return
        elif len(outstr) + len(joiner) + len(inlist[0]) >= 500:
            yield outstr
            outstr = inlist.pop(0)
            continue

        outstr += joiner + str(inlist.pop(0))

def _check_term(term, lookup, info, space_suppress=True, full=False):
    _term = str(term).replace("(", r"\(").replace(")", r"\)")
    found = info[lookup].str.lower().str.contains(_term.lower())
    found = info.loc[found]

    if space_suppress and len(found) == 0:
        found = info[lookup].str.lower().str.replace(" ", "") == _term.lower()
        found = info.loc[found]

    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    if len(found) != 1:
        raise KeyError(f"Too many matches found for {term}")
    if full:
        return found
    return str(found[lookup].iloc[0])

def _check_user(user):
    return user in _USERS

def search(term, lookup, info):
    _term = term.replace("(", r"\(").replace(")", r"\)")
    found = info[lookup].str.lower().str.contains(_term.lower())
    found = info.loc[found]
    print(found)
    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    if len(found) > 1:
        found = ", ".join(found[lookup])
        return f"Found more than one entry ({found}) for {term}"
    elif len(found) == 0:
        return f"Found nothing matching {term}"
    else:
        return str(found.to_dict(orient='records')[0])[1:-1]

def serialize(pth="./", reset=False, archive=None):

    if not os.path.exists(pth):
        os.makedirs(pth)

    with open(os.path.join(pth, "history.json"), "w") as fout:
        json.dump(HISTORY, fout, indent=2)

    with open(os.path.join(pth, "user_data.json"), "w") as fout:
        json.dump(_USERS, fout, indent=2)

    with open(os.path.join(pth, "_last_status.json"), "w") as fout:
        json.dump(bot._last_status, fout, indent=2)

    if archive is not None:
        spath = os.path.join("./", archive)
        if not os.path.exists(spath):
            os.makedirs(spath)
        shutil.move(pth, spath)

    if reset:
        os.makedirs("TRASH")
        # FIXME: here?
        # Renames instead of deleting to make sure user data integrity is only minimally threatened
        if os.path.exists(_CHKPT_DIR):
            shutil.move(_CHKPT_DIR, "TRASH")
        if os.path.exists("TRASH/"):
            shutil.move("logfile.txt", "TRASH/")

#
# Bot commands
#

@bot.event
async def event_ready():
    print("HELLO HUMAN, I AM BCFANTASYBOT. FEAR AND LOVE ME.")

    # FIXME: these should just live inside the bot
    global _USERS
    global _CONTEXT
    ctx_file = os.path.join(_CHKPT_DIR, "context.json")
    if os.path.exists(ctx_file):
        with open(ctx_file, "r") as fin:
            _CONTEXT = json.load(fin)
    print(_CONTEXT)

    # find latest
    try:
        udata_file = os.path.join(_CHKPT_DIR, "user_data*.json")
        latest = sorted(glob.glob(udata_file),
                        key=lambda f: os.path.getmtime(f))[-1]
        with open(latest, "r") as fin:
            _USERS = json.load(fin)
        print(_USERS)
    except IndexError:
        pass

    bot._last_status = {}
    status_file = os.path.join(_CHKPT_DIR, "_last_status.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as fin:
            bot._last_status = json.load(fin)

    bot._skip_auth = False
    bot._status = None
    bot._last_state_drop = -1
    ws = bot._ws

    print(f"Init'd: {bot._last_state_drop}, {bot._last_status}\nUsers: {len(_USERS)}")

@bot.command(name='doarena')
async def _arena(ctx):
    await ctx.send('!arena')

@bot.event
async def event_message(ctx):
    #if (ctx.author.name.lower() == "crackboombot" and
        #"Type !arena to start" in ctx.content):
        #ctx.content = '!doarena' + " " + ctx.content

    if _CHAT_READBACK:
        print(ctx.content)

    # Trigger a check of the local buffer
    buff = []
    """
    try:
        buff = read.read_local_queue()
    except AttributeError:
        pass
    """
    print(f"Local buffer length: {len(buff)}")

    # Read in emulator log
    try:
        print("About reading logfile. Last status:")
        print(bot._last_status)
        cmds = read.parse_log_file(last_frame=bot._last_status.get("frame", -1))
        print(f"Logfile read with {len(cmds)} commands.")
        cmds, last = convert_buffer_to_commands(cmds, last_status=bot._last_status)
        print("Conversion done. Last status:")
        print(bot._last_status)
        bot._last_status = last
        buff += cmds
        print(f"emu buffer length: {len(cmds)}")
    except Exception as e:
        print(e)
        print("Couldn't read logfile")

    print(f"Processing command buffer... status: {bot._status}")
    orig_author = ctx.author._name
    orig_content = ctx.content
    for line in filter(lambda l: l, buff):
        if bot._status == "paused":
            print("Bot is paused; ignoring log.")
            break

        # Co-op ctx
        ctx.content = line
        # HACKZORS
        ctx.author._name = "crackboombot"
        #ctx.author = User(bot._ws, name="crackboombot")

        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands:
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content
            bot._skip_auth = True
            print(f"Auth state: {bot._skip_auth} | Internally sending command as {ctx.author.name}: '{ctx.content}'")
            await bot.handle_commands(ctx)
    bot._skip_auth = False

    # restore original message
    ctx.author._name = orig_author
    ctx.content = orig_content
    # We do this after the emulator updates to prevent area / boss sniping
    if ctx.content.startswith("!"):
        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands:
            print("Processing user command...")
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content

            await bot.handle_commands(ctx)

    curtime = int(time.time())

    # Only every minute
    if curtime - bot._last_state_drop > 60:
        print("Serializing state...")
        serialize(pth=_CHKPT_DIR)
        bot._last_state_drop = curtime

@bot.command(name='hi')
async def hi(ctx):
    await ctx.send('/me HELLO HUMAN, I AM BCFANTASYBOT. FEAR --- EXCEPT NEBEL AND CJ, WHO ARE PRETTY COOL PEOPLE --- AND LOVE ME.')

@bot.command(name='blame')
async def blame(ctx):
    blame = ctx.content
    name = blame.split(" ")[-1].lower()
    await ctx.send(f'/me #blame{name}')

#
# User-based commands
#
@bot.command(name='music')
async def music(ctx):
    """
    !music -> with no arguments, lists all conversions, with an argument looks up info on mapping.
    """
    cmds = ctx.content.split(" ")
    print(f"Querying music.")

    if len(cmds) == 1:
        for outstr in _chunk_string(["Known music: "] + MUSIC_INFO["orig"].to_list(),
                                    joiner=' '):
            await ctx.send(outstr)

    orig = cmds[1].strip()
    print(f"Querying music, argument {orig}")
    try:
        song = MUSIC_INFO.set_index("song_id")[orig]
    except KeyError:
        song = MUSIC_INFO.loc[MUSIC_INFO["orig"] == orig]

    if len(song) != 1:
        print(f"Problem finding {orig}")
        # Do nothing for now
        return

    song = song.iloc[0]
    await ctx.send(f"{song['orig']} -> {song['new']} | {song['descr']}")
COMMANDS["music"] = music

@bot.command(name='char')
async def char(ctx):
    """
    !char -> with no arguments, lists all characters, with an argument looks up info on mapping.
    """
    cmds = ctx.content.split(" ")
    print(f"Querying character.")

    if len(CHAR_MAP) == 0:
        await ctx.send("No character mapping data available.")
        return

    if len(cmds) == 1:
        for outstr in _chunk_string(["Known chars: "] + CHAR_MAP["orig"].to_list(),
                                    joiner=' '):
            await ctx.send(outstr)

    orig = cmds[1].strip().lower()
    print(f"Querying character, argument {orig}")
    char = CHAR_MAP.loc[CHAR_MAP["orig"] == orig]

    if len(char) != 1:
        print(f"Problem finding {orig}")
        # Do nothing for now
        return

    char = char.iloc[0]
    await ctx.send(f"{char['orig']} -> {char['cname']} | {char['appearance']}")
COMMANDS["char"] = char

@bot.command(name='register')
async def register(ctx):
    """
    !register -> no arguments, adds user to database
    """
    user = ctx.author.name
    if _check_user(user):
        await ctx.send(f"@{user}, you are already registered.")
        return

    # Init user
    _USERS[user] = {"score": 1000}
    await ctx.send(f"@{user}, you are now registered, and have "
                   f"{_USERS[user]['score']} Fantasy Points to use. "
                    "Choose a character (char), area, and boss with "
                    "!buy [category]=[item]")
COMMANDS["register"] = register

@bot.command(name='exploder')
async def exploder(ctx):
    """
    !exploder -> no arguments, deregisters user
    """
    user = ctx.author.name
    if not _check_user(user):
        await ctx.send(f"@{user}, you are not registered.")
        return

    # Remove user
    del _USERS[user]
    await ctx.send(f"Bye bye, @{user}")
COMMANDS["exploder"] = exploder

@bot.command(name='userinfo')
async def userinfo(ctx):
    """
    !userinfo --> no arguments, returns user selections
    """
    user = ctx.author.name
    if not _check_user(user):
        await ctx.send(f"@{user}, you are not registered, use !register first.")
        return

    # Return user selections
    info = " ".join([f"({k} | {v})" for k, v in _USERS[user].items()])
    await ctx.send(f"@{user}: {info}")
COMMANDS["userinfo"] = userinfo

@bot.command(name='userscore')
async def userscore(ctx):
    """
    !userscore --> no arguments, returns user score
    """
    user = ctx.author.name
    if not _check_user(user):
        await ctx.send(f"@{user}, you are not registered, use !register first.")
        return

    await ctx.send(f"@{user}, score: {_USERS[user]['score']}")
COMMANDS["userscore"] = userscore

@bot.command(name='sell')
async def sell(ctx):
    """
    !sell [area|boss|char] sell indicated category and recoup its sell value
    """
    user = ctx.author.name
    if user not in _USERS:
        await ctx.send(f"@{user}, you are not registered, use !register first.")
        return

    selection = ctx.content.lower().split(" ")[1:]
    cat = selection[0]

    if cat not in _USERS[user]:
        await ctx.send(f"@{user}, you have no selection for {cat}.")
        return

    item = _USERS[user].pop(cat)
    lookup, info = LOOKUPS[cat]
    value = int(info.set_index(lookup).loc[item]["Sell"])
    _USERS[user]["score"] += value

    await ctx.send(f"@{user}: sold {cat} / {item} for {value}")
COMMANDS["sell"] = sell

@bot.command(name='buy')
async def buy(ctx):
    """
    !buy [area|boss|char]=[selection] purchase a selection from a given category. Must have enough Fantasy Points to pay the cost.
    """
    await select._callback(ctx)

@bot.command(name='select')
async def select(ctx):
    """
    !select (DEPRECATED, use !buy)
    """
    user = ctx.author.name
    if user not in _USERS:
        await ctx.send(f"@{user}, you are not registered, use !register first.")
        return

    try:
        selection = " ".join(ctx.content.lower().split(" ")[1:])
        cat, item = selection.split("=")
        cat = cat.lower()

        if cat in LOOKUPS:
            lookup, info = LOOKUPS[cat]
            try:
                item = _check_term(item, lookup, info)
            except KeyError:
                await ctx.send(f"@{user}: that {cat} selection is invalid.")
                return
            cost = info.set_index(lookup).loc[item]["Cost"]

            if cat in _CONTEXT and _CONTEXT[cat] == item:
                await ctx.send(f"@{user}: you cannot buy the current area / boss.")
                return

            _user = _USERS[user]
            if cost <= _user["score"]:
                _user["score"] -= int(cost)
            else:
                await ctx.send(f"@{user}: insufficient funds.")
                return

        elif _authenticate(ctx) and cat == "score":
            item = int(item)
        else:
            await ctx.send(f"@{user}: {cat} is an invalid category")
            return

        _USERS[user][cat] = item
        await ctx.send(f"@{user}: got it. Your selection for {cat} is {item}")
        return

    except Exception as e:
        print("Badness: " + str(e))

    await ctx.send(f"Sorry @{user}, that didn't work.")
COMMANDS["buy"] = buy

#
# Context commands
#

# Areas
@bot.command(name='listareas')
async def listareas(ctx):
    """
    !listareas --> no arguments, link to all available areas
    """
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_areas.csv")
    return

    # FIXME: move to mod only command
    """
    info = [f"{i[0]} ({i[1]})"
                for _, i in _AREA_INFO[["Area", "Cost"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
    """
COMMANDS["listareas"] = listareas

@bot.command(name='areainfo')
async def areainfo(ctx):
    """
    !areainfo [area] list information about given area
    """
    area = " ".join(ctx.content.split(" ")[1:]).lower()
    print(area)
    await ctx.send(search(area, "Area", _AREA_INFO))
COMMANDS["areainfo"] = areainfo

@bot.command(name='mapinfo')
async def mapinfo(ctx):
    """
    !mapinfo [map ID] list description of map id
    """
    map_id = int(ctx.content.split()[1])
    if map_id in _MAP_INFO.index:
        await ctx.send(f"{map_id}: {_MAP_INFO.loc[map_id]['name']} (area: {_MAP_INFO.loc[map_id]['scoring_area']})")
        return

    idx = _MAP_INFO.index.searchsorted(map_id)
    left = _MAP_INFO.iloc[idx-1]["name"]
    right = _MAP_INFO.iloc[idx]["name"]

    with open("missing_maps.txt", "a") as fout:
        fout.write(f"{map_id} ")
    await ctx.send(f"Map ID {map_id} is not in the list; "
                   f"between: {left} | {right}")
COMMANDS["mapinfo"] = mapinfo

# Bosses
@bot.command(name='listbosses')
async def listbosses(ctx):
    """
    !listbosses --> no arguments, link to all available bosses
    """
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_bosses.csv")
    return

    # TODO: Move to mod only command
    """
    info = [f"{i[0]} ({i[1]})"
                for _, i in _BOSS_INFO[["Boss", "Cost"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
    """
COMMANDS["listbosses"] = listbosses

@bot.command(name='bossinfo')
async def bossinfo(ctx):
    """
    !bossinfo [boss] list information about given boss
    """
    boss = " ".join(ctx.content.split(" ")[1:]).lower()
    print(boss)
    await ctx.send(search(boss, "Boss", _BOSS_INFO))
COMMANDS["bossinfo"] = bossinfo

# Characters
@bot.command(name='listchars')
async def listchars(ctx):
    """
    !listchars --> no arguments, link to all available characters
    """
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_areas.csv")
    return

    # FIXME: move to mod only command
    """
    info = [f"{i[0]} ({i[1]}, kills: {i[2]})"
                for _, i in _CHAR_INFO[["Character", "Cost", "Kills Enemy"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
    """
COMMANDS["listchars"] = listchars

@bot.command(name='charinfo')
async def charinfo(ctx):
    """
    !charinfo [char] list information about given char
    """
    char = " ".join(ctx.content.split(" ")[1:]).lower()
    print(char)
    await ctx.send(search(char, "Character", _CHAR_INFO))
COMMANDS["charinfo"] = charinfo

@bot.command(name='partynames')
async def partynames(ctx):
    """
    !partynames -> no arguments, list the names of the party
    """
    if "party" not in bot._last_status:
        await ctx.send("No party name information available.")
        return

    s = [f"{name}: {alias}" for name, alias in bot._last_status["party"].items()]
    for os in _chunk_string(s, joiner=" | "):
        await ctx.send(os)
COMMANDS["partynames"] = partynames

# General
@bot.command(name='context')
async def context(ctx):
    """
    !context --> no arguments, list the currently active area and boss
    """
    await ctx.send(str(_CONTEXT).replace("'", "").replace("{", "").replace("}", ""))
COMMANDS["context"] = context

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """
    !context --> no arguments, list the current players and their scores.
    """
    s = [f"@{user}: {attr['score']}" for user, attr in
                    reversed(sorted(_USERS.items(),
                                    key=lambda kv: kv[1]['score']))]
    for os in _chunk_string(s, joiner=" | "):
        await ctx.send(os)
COMMANDS["context"] = context

#
# Admin commands
#

@bot.command(name='nextarea')
async def nextarea(ctx):
    """
    !nextarea -> no arguments, cycle to the next area in the sequence defined by the area table.
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    area = _CONTEXT["area"] or "Narshe (WoB)"
    # FIXME: catch OOB
    idx = numpy.roll(_AREA_INFO["Area"] == area, 1)
    new_area = str(_AREA_INFO["Area"][idx].iloc[0])
    if _set_context(f"!set area={new_area}"):
        return

    if not bot._skip_auth:
        await ctx.send(f"Sorry @{user}, that didn't work.")
ADMIN_COMMANDS["nextarea"] = nextarea

@bot.command(name='nextboss')
async def nextboss(ctx):
    """
    !nextboss -> no arguments, cycle to the next boss in the sequence defined by the boss table.
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    boss = _CONTEXT["boss"] or "Whelk"
    # FIXME: catch OOB
    idx = numpy.roll(_BOSS_INFO["Boss"] == boss, 1)
    new_area = str(_BOSS_INFO["Boss"][idx].iloc[0])
    if _set_context(f"!set boss={new_area}"):
        return

    if not bot._skip_auth:
        await ctx.send(f"Sorry @{user}, that didn't work.")
ADMIN_COMMANDS["nextboss"] = nextboss

@bot.command(name='set')
async def _set(ctx):
    """
    !set [boss|area]=value

    Manually set a context category to a value.
    """
    user = ctx.author.name
    print(f"_set | checking auth: {bot._skip_auth}")
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    print(f"_set | attempting set: {bot._skip_auth}")
    if _set_context(ctx.content):
        return
    print(f"_set | attempt failed: {bot._skip_auth}")
    if not bot._skip_auth:
        await ctx.send(f"Sorry @{user}, that didn't work.")
ADMIN_COMMANDS["set"] = _set

@bot.command(name='give')
async def give(ctx):
    """
    !give --> [list of people to give to] [amt]
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    cmd = ctx.content.split(" ")[1:]
    if len(cmd) == 0:
        await ctx.send("Invalid !give command")
        return

    val = int(cmd.pop())
    if len(cmd) == 0:
        # Give everyone points
        for user, scr in _USERS.items():
            print(f"Adding {val} to {user} Fantasy Points")
            scr["score"] += val
    elif len(cmd) >= 1:
        # Give specified chatters points
        for user in cmd:
            if user in _USERS:
                print(f"Adding {val} to {user} Fantasy Points")
                _USERS[user]["score"] += val
ADMIN_COMMANDS["give"] = give

# FIXME: these are the columns of the individual files
_EVENTS = {
    frozenset({"gameover", "chardeath", "miab", "backattack", "cantrun"}): "area",
    frozenset({"gameover", "bchardeath"}): "boss",
    frozenset({"enemykill", "bosskill", "buff", "debuff"}): "char"
}

@bot.command(name='event')
async def event(ctx):
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    """
    print(">>>", _CONTEXT["area"])
    print(">>>", set(_AREA_INFO["Area"]))
    if _CONTEXT["area"] is None or
       _CONTEXT["area"] not in set(_AREA_INFO["Area"]):
        await ctx.send("Invalid area in context. Please reset.")
    """

    try:
        event = ctx.content.lower().split(" ")[1:]
        event, args = event[0], event[1:]
        cats = {v for k, v in _EVENTS.items() if event in k}
        if len(cats) == 0:
            raise IndexError()
    except IndexError:
        await ctx.send(f"Invalid event command: {event}, {'.'.join(args)}")
        return

    print(event, args, cats)
    for cat in cats:
        for user, sel in _USERS.items():
            #print(user, sel.get("area", "").lower(), _CONTEXT["area"].lower())

            lookup, info = LOOKUPS[cat]
            multi = 1
            if cat in {"boss", "area"}:
                has_item = sel.get(cat, "").lower() == _CONTEXT[cat].lower()
                item = _check_term(_CONTEXT[cat], lookup, info, full=True)
            elif cat == "char":
                has_item = sel.get(cat, "").lower() == args[0].lower()
                item = args[0]
                if len(args) > 1:
                    multi = int(args[1])
                try:
                    item = _check_term(item, lookup, info, full=True)
                except Exception as e:
                    print(f"Failed lookup for {item}:", e)
                    continue
            #print(item, user)

            _score = sel["score"]
            # FIXME, just map to appropriate column in row
            if event == "gameover" and has_item:
                sel["score"] += int(item["Gameover"])
            elif event == "miab" and has_item:
                sel["score"] += int(item["MIAB"])
            elif event == "chardeath" and has_item:
                sel["score"] += int(item["Kills Character"])
            elif event == "bchardeath" and has_item:
                sel["score"] += int(item["Kills Character"])
            elif event == "enemykill" and has_item:
                sel["score"] += int(item["Kills Enemy"]) * multi
            elif event == "bosskill" and has_item:
                sel["score"] += int(item["Kills Boss"])
            elif event == "buff" and has_item:
                sel["score"] += int(item["Buff"])
            elif event == "debuff" and has_item:
                sel["score"] += int(item["Debuff"])
            #elif event == "backattack" and has_item:
                #sel["score"] += 1
            #elif event == "cantrun" and has_item:
                #sel["score"] += 2
            print(f"\t{event}, {user} {sel['score'] - _score}")

_EVENT_TYPES = set().union(*_EVENTS.keys())
event._callback.__doc__ = f"""
    !event eventtype [arguments] -- Manually trigger an event

    valid eventtypes: {', '.join(_EVENT_TYPES)}    
"""
ADMIN_COMMANDS["event"] = event

# TODO: is map id 5 the gameover screen?
@bot.command(name='stop')
async def stop(ctx):
    """
    !stop [|annihilated|kefkadown] Tell the bot to save its contents, possibly for a reason (game over, Kefka beaten).

    Will set the bot to 'paused' state.
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    # pause command processing
    bot._status = "paused"
    cmd = ctx.content.split()[1:]

    # Just stopping for the moment, checkpoint and move on.
    if len(cmd) == 0:
        serialize(pth=_CHKPT_DIR)
        await ctx.send("Checkpointing complete.")
        return

    pth = os.path.join("./", _SEED or datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    if cmd[0] == "annihilated":
        # Possibly do a report?
        serialize(pth, archive=_SEASON_LABEL, reset=True)
    elif cmd[0] == "kefkadown":
        serialize(pth, archive=_SEASON_LABEL, reset=True)
        await ctx.send("!cb darksl5GG darksl5Kitty ")
    elif len(cmd) > 0:
        await ctx.send(f"Urecognized stop reason {cmd[0]}")
ADMIN_COMMANDS["stop"] = stop

@bot.command(name='pause')
async def pause(ctx):
    """	
    !pause -> no argument, toggle pause for processing of log. Automatically invoked by !reset and !stop	
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    if bot._status == "paused":
        bot._status = None
        await ctx.send("Unpausing.")
    elif bot._status is None:
        bot._status = "paused"
        await ctx.send("Pausing.")
ADMIN_COMMANDS["pause"] = pause

@bot.command(name='reset')
async def reset(ctx):
    """
    !reset -> no arguments; reset all contextual and user stores
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    global _CONTEXT
    global _USERS
    bot._last_state_drop = -1
    bot._last_status = {}
    bot._status = "paused"
    # FIXME: to function
    _CONTEXT, _USERS = {"area": None, "boss": None}, {}
    # FIXME: delete log so as not to update any further
    await ctx.send("User and context info reset.")
ADMIN_COMMANDS["reset"] = reset

#
# Help commands
#
@bot.command(name='help')
async def _help(ctx):
    """
    This command.
    """
    user = ctx.author.name
    cnt = ctx.content.lower().split(" ")
    cnt.pop(0)
    if not cnt:
        await ctx.send(f"Available commands: {' '.join(COMMANDS.keys())}. Use '!help cmd' (no excl. point on cmd) to get more help.")
        return

    arg = cnt.pop(0)
    if arg not in COMMANDS:
        await ctx.send(f"@{user}, that's not a command I have help for. Available commands: {' '.join(COMMANDS.keys())}.")
        return

    doc = COMMANDS[arg]._callback.__doc__
    print(COMMANDS[arg])
    await ctx.send(f"help | {arg}: {doc}")
COMMANDS["help"] = _help

@bot.command(name='bcf')
async def explain(ctx):
    """
    Explain what do.
    """
    user = ctx.author.name
    for outstr in _chunk_string([f"@{user}: Use '!register' to get started.",
                     "You'll start with 1000 Fantasy Points to spend.",
                     "You will !buy a character (!listchars), boss (!listbosses), and area (!listareas).",
                     "The chosen character will accrue Fantasy Points for killing enemies and bosses.",
                     "Bosses get Fantasy Points for kills and gameovers.",
                     "Areas get Fantasy Points for MIAB, character kills, and gameovers."],
                     joiner=' '):
        await ctx.send(outstr)
COMMANDS["bcf"] = explain

#
# Crowd Control
#

def write_arbitrary(*args):
    """
    Write a sequence of one or more address / value pairs to memory.

    Should be used sparingly by admins as it can write arbitrary data to any location.
    """
    args = list(args)
    # Need address value pairs
    assert(len(args) % 2 == 0)

    instr = []
    while len(args) > 0:
        # assume hex
        addr = int(args.pop(0), 16)
        # FIXME: how to deal with 16 bit values
        value = int(args.pop(0), 16) & 0xFF
        # Break into high byte, low byte, and value to write
        instr.extend(bytes([addr >> 8, addr & 0xFF, value]))

    return instr

def modify_item(*args):
    args = list(args)
    # FIXME: This will overwrite any item in this position\
    # FIXME: convert string to hex
    item = int(args.pop(0), 16)
    instr = [0x2686 >> 8, 0x2686 & 0xFF, item,
             0x2689 >> 8, 0x2689 & 0xFF, 0x1]
    # FIXME: increment

    return instr

CC_CMDS = {
    "arb_write": write_arbitrary,
    "modify_item": modify_item,
    #"cant_run": cant_run (0x00B1)
    #"activate_golem": activate_golem (0x3A36)
    #"nullify_element": nullify_element (0x3EC8)
    #"fallen_one": fallen_one,
    #"change_name": change_name,
    #"swap_chars": swap_chars,
    #"give_doggo": give_interceptor # enemy or player
}


if _ENABLE_CC is not None:
    @bot.command(name='cc')
    async def cc(ctx):
        """
        cc [subcmd] [args] Execute crowd control subcmd, with possibly optional arguments.
        """
        user = ctx.author.name
        if not (bot._skip_auth or _authenticate(ctx)):
            await ctx.send(f"I'm sorry, @{user}, I can't do that...")
            return

        args = ctx.content.split(" ")[1:]
        if args[0].lower() not in CC_CMDS:
            await ctx.send(f"@{user}: the crowd control command {args[0]} is not recognized.")
            return

        cmd = args.pop(0)
        read.write_instructions(CC_CMDS[cmd](*args))
    COMMANDS["cc"] = cc


if __name__ == "__main__":

    # for local stuff
    try:
        os.mkfifo("local")
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    except AttributeError:
        pass

    bot._last_state_drop = -1
    bot.run()

    os.remove("local")
