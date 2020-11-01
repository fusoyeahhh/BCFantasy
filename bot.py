import os
import errno
import time
import numpy
import pandas
import json
from twitchio.ext import commands

import read

with open("config.json") as fin:
    opts = json.load(fin)

bot = commands.Bot(**opts)
bot._last_status = {}

_ROOT = {"fusoyeahhh"}
# add additional admin names here
_AUTHORIZED = _ROOT | {"fusoyeahhh"}

def _write(ctx, strn, prefix="BCFBot>"):
    pass

def _debug_authenticate(ctx):
    ctx.author.name in _ROOT

def _authenticate(ctx):
    print(ctx.author.name, _AUTHORIZED)
    print(ctx.author.name in _AUTHORIZED)
    return ctx.author.name in _AUTHORIZED

_AREA_INFO = pandas.read_csv("data/bc_fantasy_data_areas.csv")
_BOSS_INFO = pandas.read_csv("data/bc_fantasy_data_bosses.csv")
_CHAR_INFO = pandas.read_csv("data/bc_fantasy_data_chars.csv")
_MAP_INFO = pandas.read_csv("data/map_ids.csv", names=["id", "name"])
_MAP_INFO["id"] = [int(n, 16) for n in _MAP_INFO["id"]]

COMMANDS = {}

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
    #"skill": None,
    #"character": None
}

#
# Utils
#

def _set_context(content):
    try:
        selection = " ".join(content.split(" ")[1:])
        cat, item = selection.split("=")
        print(cat, item)

        lookup, info = LOOKUPS[cat]
        # FIXME: zozo vs. mt. zozo
        item = _check_term(item, lookup, info)

        print(cat, item, _CONTEXT)
        if cat in _CONTEXT:
            _CONTEXT[cat] = item

    except Exception as e:
        print(type(e))
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

def _check_term(term, lookup, info, full=False):
    _term = term.replace("(", r"\(").replace(")", r"\)")
    found = info[lookup].str.lower().str.contains(_term.lower())
    found = info.loc[found]

    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    if len(found) != 1:
        raise KeyError()
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

#
# Bot commands
#

@bot.event
async def event_ready():
    print("HELLO HUMAN, I AM BCFANTASYBOT. FEAR AND LOVE ME.")
    ws = bot._ws
    #await ws.send_privmsg("#darkslash88",
            #"/me (BCBOT) HELLO HUMAN, I AM BCFANTASYBOT. FEAR AND LOVE ME.")

@bot.command(name='doarena')
async def _arena(ctx):
    await ctx.send('!arena')

@bot.event
async def event_message(ctx):
    #if (ctx.author.name.lower() == "crackboombot" and
        #"Type !arena to start" in ctx.content):
        #ctx.content = '!doarena' + " " + ctx.content

    if ctx.content.startswith("!"):
        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands:
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content

            await bot.handle_commands(ctx)

    # Trigger a check of the local buffer
    buff = []
    try:
        buff = read.read_local_queue()
    except AttributeError:
        pass

    # Read in emulator log
    try:
        cmds, last = read.parse_log_file(last_status=bot._last_status)
        bot._last_status = last
        buff += cmds
    except Exception as e:
        print(e)
        print("Couldn't read logfile")

    for line in filter(lambda l: l, buff):
        # Co-op ctx
        ctx.content = line

        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands:
            # HACKZORS
            #ctx.author.name = 'fusoyeahhh'
            _AUTHORIZED.add(ctx.author.name)
            # FIXME: disable error reporting
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content
            await bot.handle_commands(ctx)
            _AUTHORIZED.discard(ctx.author.name)

    print(ctx.content)

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
                   f"{_USERS[user]['score']} points to use. "
                    "Choose a character (char), area, and boss with "
                    "!select [category]=[item]")
COMMANDS["register"] = register

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

@bot.command(name='select')
async def select(ctx):
    """
    !select [area|boss|char]=[selection] set the selection for a given category. Must have enough points to pay the cost.
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
COMMANDS["select"] = select

#
# Context commands
#

# Areas
@bot.command(name='listareas')
async def listareas(ctx):
    """
    !listareas --> no arguments, list all available areas
    """
    info = [f"{i[0]} ({i[1]})"
                for _, i in _AREA_INFO[["Area", "Cost"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
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

# Bosses
@bot.command(name='listbosses')
async def listbosses(ctx):
    """
    !listbosses --> no arguments, list all available bosses
    """
    info = [f"{i[0]} ({i[1]})"
                for _, i in _BOSS_INFO[["Boss", "Cost"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
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
    !listchars --> no arguments, list all available characters
    """
    info = [f"{i[0]} ({i[1]})"
                for _, i in _CHAR_INFO[["Character", "Cost"]].iterrows()]
    for outstr in _chunk_string(info):
        await ctx.send(outstr)
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

@bot.command(name='nextarea')
async def nextarea(ctx):
    user = ctx.author.name
    if not _authenticate(ctx):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    area = _CONTEXT["area"] or "Narshe (WoB)"
    # FIXME: catch OOB
    idx = numpy.roll(_AREA_INFO["Area"] == area, 1)
    new_area = str(_AREA_INFO["Area"][idx].iloc[0])
    if _set_context(f"!set area={new_area}"):
        return

    await ctx.send(f"Sorry @{user}, that didn't work.")

@bot.command(name='nextboss')
async def nextboss(ctx):
    user = ctx.author.name
    if not _authenticate(ctx):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    boss = _CONTEXT["boss"] or "Whelk"
    # FIXME: catch OOB
    idx = numpy.roll(_BOSS_INFO["Boss"] == boss, 1)
    new_area = str(_BOSS_INFO["Boss"][idx].iloc[0])
    if _set_context(f"!set boss={new_area}"):
        return

    await ctx.send(f"Sorry @{user}, that didn't work.")

@bot.command(name='set')
async def _set(ctx):
    user = ctx.author.name
    if not _authenticate(ctx):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    if _set_context(ctx.content):
        return

    await ctx.send(f"Sorry @{user}, that didn't work.")

# FIXME: these are the columns of the individual files
_EVENTS = {
    frozenset({"gameover", "chardeath", "miab", "backattack", "cantrun"}): "area",
    frozenset({"gameover", "bchardeath"}): "boss",
    frozenset({"enemykill", "bosskill", "buff", "debuff"}): "char"
}
@bot.command(name='event')
async def event(ctx):
    user = ctx.author.name
    if not _authenticate(ctx):
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
        await ctx.send("Invalid event command.")
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
                item = _check_term(item, lookup, info, full=True)
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
        await ctx.send(f"Available commands: {' '.join(COMMANDS.keys())}. Use '!help cmd' (no excl. point on 'cmd) to get more help.")
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
                     "You'll start with 1000 points to spend.",
                     "You will !select a character (!listchars), boss (!listbosses), and area (!listareas).",
                     "The chosen character will accrue points for killing enemies and bosses.",
                     "Bosses get points for kills and gameovers.",
                     "Areas get points for MIAB, character kills, and gameovers."],
                     joiner=' '):
        await ctx.send(outstr)
COMMANDS["bcf"] = explain

if __name__ == "__main__":
    import time
    import glob
    import json

    # find latest
    try:
        latest = sorted(glob.glob("user_data*.json"),
                        key=lambda f: os.path.getmtime(f))[-1]
        with open(latest, "r") as fin:
            _USERS = json.load(fin)
        print(_USERS)
    except IndexError:
        pass

    if os.path.exists("context.json"):
        with open("context.json", "r") as fin:
            _CONTEXT = json.load(fin)
        print(_CONTEXT)

    # for local stuff
    try:
        os.mkfifo("local")
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise
    except AttributeError:
        pass

    bot.run()

    os.remove("local")

    with open("context.json", "w") as fout:
        json.dump(_CONTEXT, fout, indent=2)

    with open("history.json", "w") as fout:
        json.dump(HISTORY, fout, indent=2)

    time = int(time.time())
    with open(f"user_data_{time}.json", "w") as fout:
        json.dump(_USERS, fout, indent=2)
