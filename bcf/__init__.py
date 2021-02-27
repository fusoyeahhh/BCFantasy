import logging
from bcf import read

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

def convert_buffer_to_commands(logf, gamestate, **kwargs):
    """
    Translate an array of JSON-formatted status updates to equivalent BCF events and context updates.

    :param logf: List of dictionaries containing status updates.
    :param kwargs: Optional keyword arguments
        :param last_status: dictionary corresponding to last status update processed by bot. Used to disregard updates which are already processed.
    :return: tuple of list of twitch-style string commands and the last status processed
    """
    # FIXME: get this from gamestate
    last_status = kwargs.get("last_status", {})

    cmds = []
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
        music_id, _music_id = status.get("music_id", None), gamestate._context.get("music", None)
        # If we have a music mapping, the current music id is known, and the music has changed
        if len(gamestate) > 0 and music_id is not None and music_id != _music_id:
            # If we don't know the music look up, it's probably a vanilla song that's not listed in the spoiler
            gamestate._context["music"] = gamestate.set_index("song_id")["new"].get(music_id, "Unknown (probably vanilla)")
            logging.info(f"Setting music context to {music_id} => {gamestate._context['music']}")

        # Special check for Veldt area
        if status.get("music_id", None) == 0x19 and int(status["map_id"]) not in {0x161}:
            cmds.append(f"!set area=Veldt")
            logging.info("emu> " + cmds[-1])
        # check for map change
        elif status["map_id"] != last_status.get("map_id", None):
            cmds.append(f"!set area={status['map_id']}")
            logging.info("emu> " + cmds[-1])

        # check for boss encounter
        # FIXME: go by enemy id, rather than formation id
        logging.info(f"Checking formation, this: {status.get('eform_id', None)} "
                     f"last: {last_status.get('eform_id', None)} "
                     f"(in battle: {status.get('in_battle', None)})")
        if status["in_battle"] and status["eform_id"] != last_status.get("eform_id", None):
            logging.info(f"New encounter: {status['eform_id']}, is miab? {status['is_miab']}")
            if int(status["eform_id"]) in gamestate.boss_info["Id"].values:
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
                etype = "boss" if int(status["eform_id"]) in gamestate.boss_info["Id"].values else "enemy"
                cmds.append(f"!event {etype}kill {char} {diff}")
                logging.info("emu> " + cmds[-1])

        # check for deaths
        ldeaths = last_status.get("deaths", {})
        for char, k in status.get("deaths", {}).items():
            # Check for a *difference* from the last known death count for this character
            diff = k - ldeaths.get(char, 0)
            # Is this a boss or an enemy death?
            etype = "b" if int(status["eform_id"]) in gamestate.boss_info["Id"].values else ""
            if diff > 0 and char not in {"EXTRA1", "EXTRA2", "NIL_lookup"}:
                cmds.append(f"!event {etype}chardeath {char} {diff}")
                logging.info("emu> " + cmds[-1])

        # check for gameover
        # Detect only a "flip on" where we went from not gameover to gameover, and nothing after
        if status.get("is_gameover") and not last_status.get("is_gameover"):
            # Is this a boss or enemy induced?
            etype = "b" if int(status["eform_id"]) in gamestate.boss_info["Id"].values else ""
            cmds.append(f"!event {etype}gameover")
            logging.info("emu> " + cmds[-1])

        # Save the last status to return to the bot
        last_status = status

    # If we did nontrivial processing, log the last status
    if len(logf) > 0:
        logging.debug("Last status: " + str(last_status))

    return cmds, last_status

def _check_term(term, lookup, info, space_suppress=True, full=False, allow_multiple=False):
    """
    Generic function to check and look up a term in a given lookup table. Assumes there is exactly one match for the term.

    In general, the matching is lenient in so far as partial matches are allowed:
        "Katana" and "KatanaSoul" will match "Katana Soul" when `space_supress` is True and `full` is False (default)

    :param term: (str) term to match against lookup table
    :param lookup: (str) column in lookup table to perform match on
    :param info: (pandas.DataFrame) lookup table to match against
    :param space_suppress: whether to check variations of the term which do not contain spaces
    :param full: require a full match
    :param allow_multiple: allow (and return) multiple matches
    :return: value in column `lookup` matching key `term` from table `info`
    """
    _term = str(term).replace("(", r"\(").replace(")", r"\)")
    found = info[lookup].str.lower().str.contains(_term.lower())
    found = info.loc[found]

    if space_suppress and len(found) == 0:
        found = info[lookup].str.lower().str.replace(" ", "") == _term.lower().replace(" ", "")
        found = info.loc[found]

    if len(found) > 1:
        found = info[lookup].str.lower() == _term.lower()
        found = info.loc[found]

    logging.debug(f"check_term | Found {len(found)} matches for {term} in {lookup}")
    if len(found) == 0:
        raise KeyError(f"No matches found for {term} in {lookup}")
    if len(found) != 1:
        if allow_multiple:
            return [*map(str, found[lookup])]
        else:
            raise KeyError(f"Too many matches found for {term}:\n" + str(found))
    if full:
        return found
    return str(found[lookup].iloc[0])

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