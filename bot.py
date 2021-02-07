import sys
import os
import time
import datetime
import shutil
import numpy
import pandas
import json
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from twitchio.ext import commands
import glob

import read

#
# Configuration
#
with open("config.json") as fin:
    opts = json.load(fin)

# add additional admin names here
# These users can execute admin commands
_AUTHORIZED = opts.pop("admins", {})
# If true-like, will enable Crowd Control
_ENABLE_CC = opts.pop("crowd_control", None)
# Base URL for data listings (such as area, characters, bosses...)
_GITHUB_DOC_BASE = opts.pop("doc_url", "https://github.com/fusoyeahhh/BCFantasy/blob/main/data/")

#
# Seed / Spoiler metadata
#

# Optional mappings derived from spoiler
MUSIC_INFO, CHAR_MAP = {}, {}
_FLAGS, _SEED = None, None
_SPOILER_LOG = opts.pop("spoiler", None)

if _SPOILER_LOG and os.path.isdir(_SPOILER_LOG):
    try:
        _SPOILER_LOG = glob.glob(os.path.join(_SPOILER_LOG, "*.txt"))[0]
    except IndexError:
        logging.warning(f"Directory of spoiler log is not valid, no spoiler texts found: {_SPOILER_LOG}")

if _SPOILER_LOG and os.path.exists(_SPOILER_LOG):
    _FLAGS, _SEED, maps = read.read_spoiler(_SPOILER_LOG)
    mmaps, cmaps = maps
    MUSIC_INFO = pandas.DataFrame(mmaps).dropna()
    CHAR_MAP = pandas.DataFrame(cmaps).dropna()
else:
    logging.warning(f"Path to spoiler log is not valid and was not read: {_SPOILER_LOG}")

# If the flags are listed in the configuration file, they override all else
_FLAGS = opts.pop("flags", _FLAGS)
# Same for seed
_SEED = opts.pop("seed", _SEED)
# Season label is used for archival and tracking purposes
_SEASON_LABEL = opts.pop("season", None)
# Where we keep our checkpointed user and game data
_CHKPT_DIR = opts.pop("checkpoint_directory", "./checkpoint/")

# The bot, initialized from the configuration data
bot = commands.Bot(**opts)

# Channel chat will be emitted if True
_CHAT_READBACK = False

# If this is a path-like, periodic updates will be written to this file. Ignored if None
_STREAM_STATUS = "./stream_status.txt"
_STREAM_COOLDOWN = int(opts.pop("stream_status_cooldown", 20))

# FIXME: Move to library
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
    #0xE: "Guest actor 1",
    #0xF: "Guest actor 2"
}

def _authenticate(ctx):
    """
    Checks if ctx.user is in the administrator list.

    :param ctx: Twitch chat context
    :return: (bool) whether or not user is authorized to use admin commands
    """
    logging.debug(f"Checking auth status for {ctx.author.name}: {ctx.author.name in _AUTHORIZED}")
    return ctx.author.name in _AUTHORIZED

#
# Game / Scoring data
#
# FIXME: do this in function for easier reloading
_AREA_INFO = pandas.read_csv("data/bc_fantasy_data_areas.csv")
_BOSS_INFO = pandas.read_csv("data/bc_fantasy_data_bosses.csv")
_CHAR_INFO = pandas.read_csv("data/bc_fantasy_data_chars.csv")
_MAP_INFO = pandas.read_csv("data/map_ids.csv")
_MAP_INFO["id"] = [int(n, 16) for n in _MAP_INFO["id"]]
_MAP_INFO = _MAP_INFO.set_index("id")

# Internal mapping for user and admin commands
COMMANDS = {}
ADMIN_COMMANDS = {}

# event history
HISTORY = {}

# Given a category, what column should be used to look up a selection against which table
LOOKUPS = {
    "area": ("Area", _AREA_INFO),
    "char": ("Character", _CHAR_INFO),
    "boss": ("Boss", _BOSS_INFO),
}

# User data
_USERS = {}

# Current game context
_CONTEXT = {
    "area": None,
    "boss": None,
    "music": None
}

#
# Parsing
#
def convert_buffer_to_commands(logf, **kwargs):
    """
    Translate an array of JSON-formatted status updates to equivalent BCF events and context updates.

    :param logf: List of dictionaries containing status updates.
    :param kwargs: Optional keyword arguments
        :param last_status: dictionary corresponding to last status update processed by bot. Used to disregard updates which are already processed.
    :return: tuple of list of twitch-style string commands and the last status processed
    """
    cmds = []
    last_status = kwargs.get("last_status", {})

    for status in sorted(logf, key=lambda l: l["frame"]):
        # parse current party
        if "party" in status:
            try:
                # Iterate over all the entries in the 'party'
                # Since JSON only knows strings, the string is converted back into an integer value
                # Then overwrite the entry with a new dictionary mapping actor id (also integer converted)
                # to the sequence of int values to be translated into characters.
                status["party"] = {_ACTOR_MAP[int(act)]: [max(int(c), 0) for c in name.strip().split()]
                                                     for act, name in status["party"].items()
                                                                        if int(act) in _ACTOR_MAP}

                # This is the user-given names for the characters in the party
                cparty = [s.lower() for s in status.get("cparty", [])]
                logging.info("Current party from status update: " + ", ".join(cparty))

                # Since the current party entries are indicated by the canonical names, we check this here before
                # the names are translated
                in_cparty = []
                for act in status["party"]:
                    # The actor is in the current party
                    if act.lower() in cparty:
                        in_cparty.append(act)

                    # Translate the integer sequence to an ASCII string
                    status["party"][act] = read.translate(status["party"][act])

                # Add parens around names of characters in the current party for easy identification
                last_party = last_status.get("parsed_cparty", [])
                for act in (in_cparty if status["in_battle"] else last_party):
                    status["party"][f"({act})"] = status["party"].pop(act)
                # Save the party status
                status["parsed_cparty"] = in_cparty if status["in_battle"] else last_party

            except Exception as e:
                # This isn't a fatal problem, so we persevere
                logging.error("Couldn't parse party: " + str(status["party"]))

        # music id lookup
        # FIXME: do this the same way as other contexts
        # Get the current music id and the emulator identified id (if available)
        music_id, _music_id = status.get("music_id", None), _CONTEXT.get("music", None)
        # If we have a music mapping, the current music id is known, and the music has changed
        if len(MUSIC_INFO) > 0 and music_id is not None and music_id != _music_id:
            # If we don't know the music look up, it's probably a vanilla song that's not listed in the spoiler
            _CONTEXT["music"] = MUSIC_INFO.set_index("song_id")["new"].get(music_id, "Unknown (probably vanilla)")
            logging.info(f"Setting music context to {music_id} => {_CONTEXT['music']}")

        # Special check for Veldt area
        if status.get("music_id", None) == 0x19 and int(status["map_id"]) not in {0x15E}:
            cmds.append(f"!set area=Veldt")
            logging.info("emu> " + cmds[-1])
        # check for map change
        elif status["map_id"] != last_status.get("map_id", None):
            cmds.append(f"!set area={status['map_id']}")
            logging.info("emu> " + cmds[-1])

        # check for boss encounter
        # FIXME: go by enemy id, rather than formation id
        if status["in_battle"] and status["eform_id"] != last_status.get("eform_id", None):
            logging.info(f"New encounter: {status['eform_id']}, is miab? {status['is_miab']}")
            if int(status["eform_id"]) in _BOSS_INFO["Id"].values:
                cmds.append(f"!set boss={status['eform_id']}")
                logging.info("emu> " + cmds[-1])

            # Check for miab
            if status.get("is_miab", False):
                cmds.append(f"!event miab")
                logging.info("emu> " + cmds[-1])

        # check for kills
        lkills = last_status.get("kills", {})
        for char, k in status.get("kills", {}).items():
            # Check for a *difference* from the last known kill count for this character
            diff = k - lkills.get(char, 0)
            # Colosseum is exception, we don't count kills here
            if status.get("map_id", None) == 0x19D:
                logging.info("Colosseum detected, no character kills will be recorded.")
                break
            elif diff > 0 and char not in {"EXTRA1", "EXTRA2", "NIL_lookup"}:
                # FIXME: should probably in_check battle status
                # Is this a boss or an enemy kill?
                etype = "boss" if int(status["eform_id"]) in _BOSS_INFO["Id"].values else "enemy"
                cmds.append(f"!event {etype}kill {char} {diff}")
                logging.info("emu> " + cmds[-1])

        # check for deaths
        ldeaths = last_status.get("deaths", {})
        for char, k in status.get("deaths", {}).items():
            # Check for a *difference* from the last known death count for this character
            diff = k - ldeaths.get(char, 0)
            # Is this a boss or an enemy death?
            etype = "b" if int(status["eform_id"]) in _BOSS_INFO["Id"].values else ""
            if diff > 0 and char not in {"EXTRA1", "EXTRA2", "NIL_lookup"}:
                cmds.append(f"!event {etype}chardeath {char} {diff}")
                logging.info("emu> " + cmds[-1])

        # check for gameover
        # Detect only a "flip on" where we went from not gameover to gameover, and nothing after
        if status.get("is_gameover") and not last_status.get("is_gameover"):
            # Is this a boss or enemy induced?
            etype = "b" if int(status["eform_id"]) in _BOSS_INFO["Id"].values else ""
            cmds.append(f"!event {etype}gameover")
            logging.info("emu> " + cmds[-1])

        # Save the last status to return to the bot
        last_status = status

    # If we did nontrivial processing, log the last status
    if len(logf) > 0:
        logging.debug("Last status: " + str(last_status))

    return cmds, last_status

#
# Utils
#

def _set_context(content):
    """
    Set a value in the current game context.

    :param content: (string) twitch-style command, likely from the 'set' command.
    :return: (bool) whether or not the attempted context set was completed.
    """

    try:
        selection = " ".join(content.split(" ")[1:])
        cat, item = selection.split("=")
        logging.debug(f"Attempting to set {cat} to {item}.")

        # Preliminary mapid to area setting
        # These almost always come from the emulator indicating a map change
        if cat == "area" and item.isdigit():
            _item = int(item)
            if _item in _MAP_INFO.index:
                # FIXME: need to move this to a special handler function
                # We don't change the context if on this map, since it can indicate a gameover
                if _item == 5:
                    logging.info("Map id 5 detected, not changing area.")
                    return True

                # South Figaro basement split map
                # FIXME: There is assuredly more of these, so they should be captured in a function
                elif _item == 89:
                    logging.info("Map id 89 (SF basement) detected, not changing area.")
                    return True

                # Translate integer map id to the area to set in the context
                item = _MAP_INFO.loc[_item]["scoring_area"]

                # This map id exists, but is not mapped to an area
                # FIXME: This shouldn't be needed once we're set on the area mappings
                if pandas.isna(item):
                    return True

                logging.info(f"Area: {_item} => {item}")
            else:
                # Log that the map id didn't have an entry in the lookup tables
                # FIXME: raise an exception when we're more confident about the map => area lookup
                logging.error(f"No valid area mapping for id {item}")
                return True

        if cat == "boss" and item.isdigit():
            _item = int(item)
            if _item in set(_BOSS_INFO["Id"]):
                # Look up numeric id and get canonical boss name
                item = _BOSS_INFO.set_index("Id").loc[_item]["Boss"]
                logging.info(f"Boss: {_item} => {item}")
            else:
                # We raise this, but it's possible it's intended, so the caller will just get False instead
                raise ValueError(f"No valid boss mapping for id {_item} (this may be intended)")

        lookup, info = LOOKUPS[cat]
        item = _check_term(item, lookup, info)

        # Actually set the item in the context
        logging.debug((cat, item, _CONTEXT))
        if cat in _CONTEXT:
            _CONTEXT[cat] = item

        # Serialize the change, note that this doesn't seem to get picked up in restarts
        with open("context.json", "w") as fout:
            json.dump(_CONTEXT, fout, indent=2)

    except Exception as e:
        # There's lots of reasons why this may not work, and it's not necessarily fatal, so we just log it and
        # let the caller know
        logging.error(e)
        return False

    # Indicate success
    return True

def _chunk_string(inlist, joiner=", "):
    """
    Given a list of strings to (ultimately) concatenate and send to twitch chat.

    The list of strings is concatenated (via 'joiner') into strings of lengths that are allowed by twitch chat.

    :param inlist: (list) list of strings to emit
    :param joiner: (str) character to use a joiner
    :return: None
    """

    # Nothing to do here
    if len(inlist) == 0:
        return

    # There's a string in the list which is larger than the allowed count
    # FIXME: we can break up this string too, if needed, possibly by calling this recursively
    assert max([*map(len, inlist)]) < 500, \
                                "Can't fit all messages to buffer length"

    outstr = str(inlist.pop(0))
    # While we have strings to send
    while len(inlist) >= 0:
        # We've reached the end of the input list, drain the remaining buffer and end
        if len(inlist) == 0:
            yield outstr
            return
        # If the next concat would put us over the limit, then we emit, reset, and continue
        elif len(outstr) + len(joiner) + len(inlist[0]) >= 500:
            yield outstr
            outstr = inlist.pop(0)
            continue

        # continue concatenating
        outstr += joiner + str(inlist.pop(0))

def _check_term(term, lookup, info, space_suppress=True, full=False):
    """
    Generic function to check and look up a term in a given lookup table. Assumes there is exactly one match for the term.

    In general, the matching is lenient in so far as partial matches are allowed:
        "Katana" and "KatanaSoul" will match "Katana Soul" when `space_supress` is True and `full` is False (default)

    :param term: (str) term to match against lookup table
    :param lookup: (str) column in lookup table to perform match on
    :param info: (pandas.DataFrame) lookup table to match against
    :param space_suppress: whether to check variations of the term which do not contain spaces
    :param full: require a full match
    :return: value in column `lookup` matching key `term` from table `info`
    """
    _term = str(term).replace("(", r"\(").replace(")", r"\)")
    found = info[lookup].str.lower().str.contains(_term.lower())
    found = info.loc[found]

    if space_suppress and len(found) == 0:
        found = info[lookup].str.lower().str.replace(" ", "") == _term.lower()
        found = info.loc[found]

    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    if len(found) == 0:
        raise KeyError(f"No matches found for {term} in {lookup}")
    if len(found) != 1:
        raise KeyError(f"Too many matches found for {term}:\n" + str(found))
    if full:
        return found
    return str(found[lookup].iloc[0])

def _check_user(user):
    """
    Check if a user is already registered in the user database.

    :param user: (str) user
    :return: (bool) whether or not the user is in `_USERS`
    """
    return user in _USERS

def _sell_all(users):
    """
    Iterate through the user database and sell all salable items. Generally invoked at the end of a seed.

    :param users: (unused)
    :return: None
    """
    for user, inv in _USERS.items():
        for cat, item in inv.items():
            # Omit categories that don't have salable items (e.g. score)
            if cat not in LOOKUPS:
                continue
            try:
                # We assume the user hasn't somehow managed to buy an item not in the lookup table
                lookup, info = LOOKUPS[cat]
                # Add the sale price back to the score
                inv["score"] += int(info.set_index(lookup).loc[item]["Sell"])
            except Exception as e:
                logging.error("Problem in sell_all:\n" + str(e) + "\nUser table:\n" + str(_USERS))

        # Clear out the user selections, drop all categories which aren't the score
        _USERS[user] = {k: max(v, 1000) for k, v in inv.items() if k == "score"}
        logging.info(f"Sold {user}'s items. Current score {_USERS[user]['score']}")
    logging.info("Sold all users items.")

def search(term, lookup, info):
    """
    Do a look up for a given term in the lookup column against a lookup table.

    FIXME: Should we merge this with `check_term`?

    :param term: (str) item to match
    :param lookup: (str) column in lookup table to match against
    :param info: (pandas.DataFrame) look up table to match against
    :return: Result of search in English, or the exact match (in the case of one)
    """

    # escape parens
    _term = term.replace("(", r"\(").replace(")", r"\)")
    # Lower case searched column and term, then get partial match against term
    found = info[lookup].str.lower().str.contains(_term.lower())
    # retrieve partial matches
    found = info.loc[found]

    # Narrow to exact matches, if there is one
    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    # Still have more than one match, concatenate
    if len(found) > 1:
        found = ", ".join(found[lookup])
        return f"Found more than one entry ({found}) for {term}"
    # No matches at all
    elif len(found) == 0:
        return f"Found nothing matching {term}"
    # Exactly one match
    else:
        return str(found.to_dict(orient='records')[0])[1:-1]

def export_to_gsheet(season, ndoc=0):
    """
    Export a `pandas.DataFrame` to a google sheet. Used to synch the season leaderboard.

    :param season: `pandas.DataFrame` to synch
    :param ndoc: Identifier of the sheet to synch
    :return: None
    """
    import gspread
    from gspread_dataframe import set_with_dataframe

    gc = gspread.service_account()
    sh = gc.open('Season Leaderboard')
    worksheet = sh.get_worksheet(ndoc)
    worksheet.format ('1', {'textFormat': {'bold': True}})
    set_with_dataframe(worksheet, season)



def serialize(pth="./", reset=False, archive=None, season_update=False):
    """
    Serialize (write to file) several of the vital bookkeeping structures attached to the bot.

    Optionally archive the entire information set to a directory (usually the seed).
    Optionally send checkpoint to trash and reset the bot state.
    Optionally update a season-tracking file with user scores.

    :param pth: path to checkpoint information to
    :param reset: whether or not to reset bot state (default is False)
    :param archive: path to archive the checkpoint (default is None)
    :param season_update: whether or not to update the season scores (default is False)
    :return: None
    """

    # Create the serialization directory if it doesn't already exist
    if not os.path.exists(pth):
        logging.info(f"Creating serialization path {pth}")
        os.makedirs(pth)

    # Save the current history to a JSON file in the serialization path
    logging.info(f"Serializing path {pth}/history.json")
    with open(os.path.join(pth, "history.json"), "w") as fout:
        json.dump(HISTORY, fout, indent=2)

    # Save the current user data to a JSON file in the serialization path
    logging.info(f"Serializing path {pth}/user_data.json")
    with open(os.path.join(pth, "user_data.json"), "w") as fout:
        json.dump(_USERS, fout, indent=2)

    # Save the last know game status to a JSON file in the serialization path
    logging.info(f"Serializing path {pth}/_last_status.json")
    # If we're paused, we probably stopped the bot, so the frame counter should be zero
    # This is more of a debug check than anything
    if bot._status == "paused" and bot._last_status.get("frame") != 0:
        logging.warning("Warning, the frame counter is not zero, but it *probably* should be.")
    with open(os.path.join(pth, "_last_status.json"), "w") as fout:
        json.dump(bot._last_status, fout, indent=2)

    # The seed has likely ended one way or another, and the user has requested an archive
    # operation, probably for a season.
    if archive is not None:
        spath = os.path.join("./", archive)
        # Create the archive path if it doesn't already exist
        if not os.path.exists(spath):
            logging.info(f"Creating archive path {spath}")
            os.makedirs(spath)

        # Move the checkpoint path to the archive path
        logging.info(f"Archiving {pth} to {spath}")
        shutil.move(pth, spath + "/")

        # We also update the season tracker
        sfile = os.path.join("./", archive, "season.csv")
        if season_update:
            logging.info(f"Adding season tracking information to {sfile}")
            try:
                # Convert the user data into rows of a CSV table
                this_seed = pandas.DataFrame(_USERS)
                logging.debug(f"Users: {_USERS},\nseed database: {this_seed.T}")
                # Drop everything but the score (the other purchase information is extraneous)
                this_seed = this_seed.T[["score"]].T
                # We alias the score to a unique identifier for each seed
                this_seed.index = [_SEED + "." + _FLAGS]
            except KeyError as e:
                logging.error("Encountered error in serializing user scores to update season-long scores. "
                              f"Current user table:\n{_USERS}")
                raise e

            if os.path.exists(sfile):
                logging.info(f"Concatenating new table to {sfile}")
                prev = pandas.read_csv(sfile).set_index("index")
                logging.debug(f"Current season has {len(prev)} (possibly including totals) entries.")
                # If the season CSV already exists, we concatenate this seed data to it
                season = pandas.concat((prev, this_seed))
            else:
                logging.info(f"Creating new table at {sfile}")
                # Otherwise, we create a new table
                season = this_seed

            if "Total" in season.index:
                season.drop("Total", inplace=True)
            season.loc["Total"] = season.fillna(0).sum()
            # FIXME: We should convert this to JSON instead
            season.reset_index().to_csv(sfile, index=False)
            season.index.name = "Seed Number"
            logging.info("Synching season scores to Google sheet...")
            export_to_gsheet(season.reset_index())
            logging.info("...done")

            logging.info("Synching overall leaderboard to Google sheet...")
            overall = season.loc["Total"].sort_values()[::-1].T
            export_to_gsheet(overall.reset_index(), ndoc=1)
            logging.info("...done")

    if reset:
        os.makedirs("TRASH")
        # Renames instead of deleting to make sure user data integrity is only minimally threatened
        # Mark the checkpoint directory as trash by naming it as such
        if os.path.exists(_CHKPT_DIR):
            shutil.move(_CHKPT_DIR, "TRASH")
        # Move the logfile into the trash too, just in case it needs to be restored
        if os.path.exists("TRASH/"):
            shutil.move("logfile.txt", "TRASH/")

        # reset bot status
        bot._last_status = {}
        bot._last_state_drop = -1
 
#
# Bot commands
#

@bot.event
async def event_ready():
    logging.warning("HELLO HUMAN, I AM BCFANTASYBOT. FEAR AND LOVE ME.")

    # FIXME: these should just live inside the bot
    global _USERS
    global _CONTEXT
    ctx_file = os.path.join(_CHKPT_DIR, "context.json")
    if os.path.exists(ctx_file):
        with open(ctx_file, "r") as fin:
            _CONTEXT = json.load(fin)
    logging.debug(_CONTEXT)

    # find latest
    try:
        udata_file = os.path.join(_CHKPT_DIR, "user_data*.json")
        latest = sorted(glob.glob(udata_file),
                        key=lambda f: os.path.getmtime(f))[-1]
        with open(latest, "r") as fin:
            _USERS = json.load(fin)
        logging.debug(_USERS)
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

    logging.debug(f"Init'd: {bot._last_state_drop}, {bot._last_status}\nUsers: {len(_USERS)}")

@bot.event
async def event_message(ctx):
    #if (ctx.author.name.lower() == "crackboombot" and
        #"Type !arena to start" in ctx.content):
        #ctx.content = '!doarena' + " " + ctx.content


    if _CHAT_READBACK:
        # This throws weird errors with string decoding issues
        logging.info(ctx.content)

    # Trigger a check of the local buffer
    buff = []

    if bot._status == "paused":
        logging.warning("Bot is paused; ignoring log.")
    else:
        try:
            # Read in emulator log
            cmds = read.parse_log_file(last_frame=bot._last_status.get("frame", -1))
            logging.debug(f"Logfile read with {len(cmds)} commands.")
            cmds, last = convert_buffer_to_commands(cmds, last_status=bot._last_status)
            bot._last_status = last
            buff += cmds
            logging.debug(f"emu buffer length: {len(cmds)}")
        except Exception as e:
            logging.error(e)
            logging.error("Couldn't read logfile")

    logging.debug(f"Processing command buffer... status: {bot._status}")
    orig_author = ctx.author._name
    orig_content = ctx.content
    for line in filter(lambda l: l, buff):
        # Co-op ctx
        ctx.content = line
        # HACKZORS
        ctx.author._name = "crackboombot"
        #ctx.author = User(bot._ws, name="crackboombot")

        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands:
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content
            """
            if _STREAM_STATUS and line.startswith("!event"):
                last_frame = bot._last_status.get("frame", 'unknown')
                with open(_STREAM_STATUS, "a") as f:
                    f.write(f"{last_frame}: {line}\n")
                    f.flush()
            """
            bot._skip_auth = True
            logging.debug(f"Auth state: {bot._skip_auth} | Internally sending command as {ctx.author.name}: '{ctx.content}'")
            await bot.handle_commands(ctx)
    bot._skip_auth = False

    # restore original message
    ctx.author._name = orig_author
    ctx.content = orig_content
    # We do this after the emulator updates to prevent area / boss sniping
    if ctx.content.startswith("!"):
        command = ctx.content.split(" ")[0][1:]
        if command in bot.commands and (bot._status != "paused" or _authenticate(ctx)):
            logging.debug("Processing user command...")
            current_time = int(time.time() * 1e3)
            HISTORY[current_time] = ctx.content

            await bot.handle_commands(ctx)

    curtime = int(time.time())

    # Only every minute
    if curtime - bot._last_state_drop > _STREAM_COOLDOWN:
        logging.debug("Serializing state...")
        serialize(pth=_CHKPT_DIR)
        bot._last_state_drop = curtime

        # Send the current game status to a file for streaming
        if _STREAM_STATUS:
            status = " | ".join([f"{cat.capitalize()}: {val}" for cat, val in _CONTEXT.items()])
            # rename to last enc. boss
            status = status.replace("Boss: ", "Last enc. boss: ")
            map_id = bot._last_status.get("map_id", None)
            # Append map info
            if map_id in _MAP_INFO.index:
                status += f" | Map: ({map_id}), {_MAP_INFO.loc[map_id]['name']}"
            # Append party info
            party = [f"{name[1:-1]}: {alias}"
                     for name, alias in bot._last_status.get("party", {}).items() if name.startswith("(")]
            if party:
                status += " | Party: " + ", ".join(party)
            # Append leaderboard
            leaderboard = " | ".join([f"{user}: {inv.get('score', None)}"
                                      for user, inv in sorted(_USERS.items(), key=lambda kv: -kv[1].get("score", 0))])

            events = [str(v) for v in HISTORY.values() if v.startswith("!event")][-3:]
            last_3 = "--- Last three events:\n" + "\n".join(events)
            # truncate file
            with open(_STREAM_STATUS, "w") as f:
                print(status + "\n\n" + leaderboard + "\n\n" + last_3 + "\n", file=f, flush=True)

@bot.command(name='hi')
async def hi(ctx):
    await ctx.send("/me Hi. I'm BC Fantasy Bot. You may remember me from such seeds as the dumpster fire from last time and OHGODNOTHATCLOCKNOOOOOOO.")

#
# User-based commands
#
@bot.command(name='bcfflags')
async def bcfflags(ctx):
    """
    !bcfflags -> no argument, print flags and seed
    """

    if _FLAGS is not None:
        await ctx.send(f"Flags: {_FLAGS} | Seed: {_SEED}")
        return
    await ctx.send("No flag information.")
COMMANDS["bcfflags"] = bcfflags

@bot.command(name='music')
async def music(ctx):
    """
    !music -> with no arguments, lists curent music. With 'list' lists all conversions, with an argument looks up info on mapping.
    """
    cmds = ctx.content.split(" ")
    logging.debug(f"Querying music.")

    if len(cmds) == 1:
        if _CONTEXT["music"] is not None and not _CONTEXT["music"].startswith("Unknown"):
            song = MUSIC_INFO.loc[MUSIC_INFO["new"] == _CONTEXT["music"]].iloc[0]
            await ctx.send(f"{song['orig']} -> {song['new']} | {song['descr']}")
        else:
            await ctx.send("No known music currently.")
        return

    orig = cmds[1].strip()
    logging.debug(f"Querying music, argument {orig}")

    if orig.lower() == "list":
        for outstr in _chunk_string(["Known music: "] + MUSIC_INFO["orig"].to_list(),
                                    joiner=' '):
            await ctx.send(outstr)
        return

    try:
        song = MUSIC_INFO.set_index("song_id")[orig]
    except KeyError:
        song = MUSIC_INFO.loc[MUSIC_INFO["orig"] == orig]

    if len(song) != 1:
        logging.error(f"Problem finding {orig}")
        # Do nothing for now
        return

    song = song.iloc[0]
    await ctx.send(f"{song['orig']} -> {song['new']} | {song['descr']}")
COMMANDS["music"] = music

@bot.command(name='sprite')
async def sprite(ctx):
    """
    !sprite -> with no arguments, lists all characters, with an argument looks up info on mapping.
    """
    cmds = ctx.content.split(" ")
    logging.debug(f"Querying character sprite.")

    if len(CHAR_MAP) == 0:
        await ctx.send("No character sprite mapping data available.")
        return

    if len(cmds) == 1:
        for outstr in _chunk_string(["Known chars: "] + CHAR_MAP["orig"].to_list(),
                                    joiner=' '):
            await ctx.send(outstr)

    orig = cmds[1].strip().lower()
    logging.debug(f"Querying character sprite, argument {orig}")
    char = CHAR_MAP.loc[CHAR_MAP["orig"] == orig]

    if len(char) != 1:
        logging.error(f"Problem finding {orig}")
        # Do nothing for now
        return

    char = char.iloc[0]
    await ctx.send(f"{char['orig']} -> {char['cname']} | {char['appearance']}")
COMMANDS["sprite"] = sprite

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
            if _user.get(cat, None) is not None:
                await ctx.send(f"@{user}: sell your current {cat} selection first.")
                return

            if cost <= _user["score"]:
                _user["score"] -= int(cost)
            else:
                await ctx.send(f"@{user}: insufficient funds.")
                return

        else:
            await ctx.send(f"@{user}: {cat} is an invalid category")
            return

        _USERS[user][cat] = item
        await ctx.send(f"@{user}: got it. Your selection for {cat} is {item}")
        return

    except Exception as e:
        logging.error("Badness: " + str(e))

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
    if _authenticate(ctx):
        info = [f"{i[0]} ({i[1]})"
                    for _, i in _AREA_INFO[["Area", "Cost"]].iterrows()]
        for outstr in _chunk_string(info):
            await ctx.send(outstr)
        return

    # Users get a link to the list so as not to spam chat
    await ctx.send("Use !bcfinfo, please. This command will go away soon.")
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_areas.csv")
    return
COMMANDS["listareas"] = listareas

@bot.command(name='areainfo')
async def areainfo(ctx):
    """
    !areainfo [area] list information about given area
    """
    area = " ".join(ctx.content.split(" ")[1:]).lower()
    #print(area)
    await ctx.send(search(area, "Area", _AREA_INFO))
COMMANDS["areainfo"] = areainfo

@bot.command(name='mapinfo')
async def mapinfo(ctx):
    """
    !mapinfo [map ID] list description of map id
    """
    map_id = int(ctx.content.split()[1])
    if map_id in _MAP_INFO.index:
        await ctx.send(f"{map_id}: {_MAP_INFO.loc[map_id]['name']} (Area: {_MAP_INFO.loc[map_id]['scoring_area']})")
        return

    idx = _MAP_INFO.index.searchsorted(map_id)
    if idx < len(_MAP_INFO):
        left = _MAP_INFO.iloc[idx-1]["name"]
        right = _MAP_INFO.iloc[idx]["name"]
    else:
        left, right = None, None

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
    if _authenticate(ctx):
        info = [f"{i[0]} ({i[1]})"
                for _, i in _BOSS_INFO[["Boss", "Cost"]].iterrows()]
        for outstr in _chunk_string(info):
            await ctx.send(outstr)
        return

    await ctx.send("Use !bcfinfo, please. This command will go away soon.")
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_bosses.csv")
    return
COMMANDS["listbosses"] = listbosses

@bot.command(name='bossinfo')
async def bossinfo(ctx):
    """
    !bossinfo [boss] list information about given boss
    """
    boss = " ".join(ctx.content.split(" ")[1:]).lower()
    #print(boss)
    await ctx.send(search(boss, "Boss", _BOSS_INFO))
COMMANDS["bossinfo"] = bossinfo

# Characters
@bot.command(name='listchars')
async def listchars(ctx):
    """
    !listchars --> no arguments, link to all available characters
    """
    if _authenticate(ctx):
        info = [f"{i[0]} ({i[1]}, kills: {i[2]})"
                for _, i in _CHAR_INFO[["Character", "Cost", "Kills Enemy"]].iterrows()]
        for outstr in _chunk_string(info):
            await ctx.send(outstr)
        return

    await ctx.send("Use !bcfinfo, please. This command will go away soon.")
    await ctx.send(f"{_GITHUB_DOC_BASE}bc_fantasy_data_areas.csv")
    return
COMMANDS["listchars"] = listchars

@bot.command(name='charinfo')
async def charinfo(ctx):
    """
    !charinfo [char] list information about given char
    """
    char = " ".join(ctx.content.split(" ")[1:]).lower()
    #print(char)
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

@bot.command(name='remap')
async def remap(ctx):
    """
    !remap -> area [description] Reset the map -> area link and optionally update the description
    """
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    map_id = bot._last_status.get("map_id", None)
    if map_id is None:
        await ctx.send(f"Current map ID is undefined.")
        return

    if map_id not in _MAP_INFO.index:
        await ctx.send(f"Current map ID {map_id} (hex: {hex(map_id)}) is not in the listings.")
        return

    new_area = " ".join(ctx.content.split(" ")[1:]).split("|")
    if len(new_area) == 3:
        map_id, new_area, new_descr = new_area
        map_id = int(map_id)
    elif len(new_area) == 2:
        new_area, new_descr = new_area
    elif len(new_area) == 1:
        new_area, new_descr = new_area[0], _MAP_INFO.loc[map_id]["name"]
    elif len(new_area) > 2:
        logging.error("remap: Could not parse command properly, aborting.")
        return

    # FIXME: does not check if area is valid
    _MAP_INFO.loc[map_id]["scoring_area"] = new_area.strip()
    _MAP_INFO.loc[map_id]["name"] = new_descr.strip()

    await ctx.send(f"Map ID {map_id} set to area {new_area}")

    # write out new mappings
    _tmp = _MAP_INFO.reset_index()
    _tmp["id"] = [*map(hex, _tmp["id"])]
    _tmp.to_csv("data/map_ids.csv", index=False)
ADMIN_COMMANDS["remap"] = remap

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
    # Last area
    if area != _AREA_INFO["Area"].iloc[-1]:
        return

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
    # Last boss
    if boss == _BOSS_INFO["Boss"].iloc[-1]:
        return

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
    #print(f"_set | checking auth: {bot._skip_auth}")
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    #print(f"_set | attempting set: {bot._skip_auth}")
    if _set_context(ctx.content):
        return
    #print(f"_set | attempt failed: {bot._skip_auth}")
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
            logging.debug(f"Adding {val} to {user} Fantasy Points")
            scr["score"] += val
    elif len(cmd) >= 1:
        # Give specified chatters points
        for user in map(str.lower, cmd):
            if user in _USERS:
                logging.debug(f"Adding {val} to {user} Fantasy Points")
                _USERS[user]["score"] += val
ADMIN_COMMANDS["give"] = give

# FIXME: these are the columns of the individual files
_EVENTS = {
    frozenset({"gameover", "chardeath", "miab", "backattack", "cantrun"}): "area",
    frozenset({"bgameover", "bchardeath"}): "boss",
    frozenset({"enemykill", "bosskill", "buff", "debuff"}): "char"
}

@bot.command(name='event')
async def event(ctx):
    user = ctx.author.name
    if not (bot._skip_auth or _authenticate(ctx)):
        await ctx.send(f"I'm sorry, @{user}, I can't do that...")
        return

    try:
        event = ctx.content.lower().split(" ")[1:]
        event, args = event[0], event[1:]
        cats = {v for k, v in _EVENTS.items() if event in k}
        if len(cats) == 0:
            raise IndexError()
    except IndexError:
        await ctx.send(f"Invalid event command: {event}, {'.'.join(args)}")
        return

    status_string = ""
    if _STREAM_STATUS:
        logging.debug("Attempting to write specifics to stream status.")
        status_string += f"{event}: " + " ".join(args) + " "

    did_error = False
    logging.debug((event, args, cats))
    for cat in cats:
        for user, sel in _USERS.items():
            #logging.info(user, sel.get("area", "").lower(), _CONTEXT["area"].lower())

            lookup, info = LOOKUPS[cat]
            multi = 1
            try:
                if cat in {"boss", "area"}:
                    has_item = sel.get(cat, "").lower() == (_CONTEXT[cat] or "").lower()
                    item = _check_term(_CONTEXT[cat], lookup, info, full=True)
                elif cat == "char":
                    has_item = sel.get(cat, "").lower() == args[0].lower()
                    item = args[0]
                    if len(args) > 1:
                        multi = int(args[1])
                        item = _check_term(item, lookup, info, full=True)
            except Exception as e:
                if not did_error:
                    did_error = True
                    logging.error(f"Failed lookup for {cat}: " + str(e))
                continue
            #print(item, user)

            _score = sel["score"]
            # FIXME, just map to appropriate column in row
            if event in {"gameover", "bgameover"} and has_item:
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
            if _STREAM_STATUS:
                score_diff = sel['score'] - _score
                did_score = score_diff > 0
                if did_score:
                    status_string += f"{user} +{score_diff} "
                    logging.debug("Wrote an item to stream status.")
            else:
                logging.info(f"\t{event}, {user} {sel['score'] - _score}")

    if _STREAM_STATUS:
        with open(_STREAM_STATUS, "a") as f:
            print(status_string, file=f, flush=True)
            logging.debug("Wrote specifics to stream status.")
        # Let the message persist for a bit longer
        bot._last_state_drop = int(time.time())


_EVENT_TYPES = set().union(*_EVENTS.keys())
event._callback.__doc__ = f"""
    !event eventtype [arguments] -- Manually trigger an event

    valid eventtypes: {', '.join(_EVENT_TYPES)}    
"""
ADMIN_COMMANDS["event"] = event

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

    # Have to reset frame counter for next emulator log restart
    logging.info("Resetting frame counter to 0 for emulator restart.")
    bot._last_status["frame"] = 0

    # Just stopping for the moment, checkpoint and move on.
    serialize(pth=_CHKPT_DIR)
    if len(cmd) == 0:
        await ctx.send("Checkpointing complete.")
        return

    pth = os.path.join("./", _SEED or datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    if cmd[0] == "annihilated":
        _sell_all(_USERS)
        await ctx.send("Sold all users items.")
        # Possibly do a report?
        serialize(pth, archive=_SEASON_LABEL, season_update=True, reset=True)
        await ctx.send("!wompwomp")
    elif cmd[0] == "kefkadown":
        _sell_all(_USERS)
        serialize(pth, archive=_SEASON_LABEL, season_update=True, reset=True)
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
    #print(COMMANDS[arg])
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
                     "You will !buy a character, boss, and area (see !bcfinfo for listings).",
                     "The chosen character will accrue Fantasy Points for killing enemies and bosses.",
                     "Bosses get Fantasy Points for kills and gameovers.",
                     "Areas get Fantasy Points for MIAB, character kills, and gameovers."],
                     joiner=' '):
        await ctx.send(outstr)
COMMANDS["bcf"] = explain

#
# Crowd Control
#

if _ENABLE_CC is not None:
    import bcfcc

    CC_CMDS = {
        "arb_write": bcfcc.write_arbitrary,
        "set_status": bcfcc.set_status,
        "set_stat": bcfcc.set_stat,
        "cant_run": bcfcc.cant_run,
        "fallen_one": bcfcc.fallen_one,
        #"change_name": change_name,
        #"modify_item": modify_item,
        #"activate_golem": activate_golem (0x3A36)
        #"nullify_element": nullify_element (0x3EC8)
        #"swap_chars": swap_chars,
        #"give_doggo": give_interceptor, # enemy or player
        #"ole_cape": ole_cape # only ever use cape animation to dodge
    }

    @bot.command(name='cc')
    async def cc(ctx):
        """
        cc [subcmd] [args] Execute crowd control subcmd, with possibly optional arguments.
        """
        user = ctx.author.name
        auth_user = bot._skip_auth or _authenticate(ctx)

        args = ctx.content.split(" ")[1:]
        if len(args) == 0:
            await ctx.send(f"@{user}: !cc needs additional arguments.")
            return
        if args[0].lower() == "help":
            await ctx.send(f"Known CC commands: {', '.join(CC_CMDS.keys())}")
            return
        if args[0].lower() not in CC_CMDS:
            await ctx.send(f"@{user}: the crowd control command {args[0]} is not recognized.")
            return
        # admin only command
        if args[0].lower() == "arb_write" and not auth_user:
            await ctx.send(f"I'm sorry, @{user}, I can't do that...")
            return
        cmd = args.pop(0)

        try:
            # Construct game context
            party = [bcfcc.Character() for i in range(4)]
            for i in range(4):
                # FIXME: make one-step initialization
                party[i]._from_memory_range("memfile", slot=i)
            logging.info(f"cc | Read and init'd {len(party)} characters in party")

            eparty = [bcfcc.Character() for i in range(6)]
            for i in range(6):
                # FIXME: make one-step initialization
                eparty[i]._from_memory_range("memfile", slot=i + 4)
            logging.info(f"cc | Read and init'd {len(eparty)} entities in enemy party")

            gctx = {"party": party, "eparty": eparty}

            logging.info(f"cc | Calling into cc subcommand {CC_CMDS[cmd]} ({cmd})")
            read.write_instructions(CC_CMDS[cmd](*args, **gctx))
            logging.info(f"cc | Finished {cmd}")
        except Exception as e:
            logging.error(f"Couldn't execute crowd control command {cmd} with args {' '.join(args)}. Exception information follows.")
            logging.error(str(type(e)) + " " + str(e))
    COMMANDS["cc"] = cc


if __name__ == "__main__":
    bot._last_state_drop = -1
    bot.run()
