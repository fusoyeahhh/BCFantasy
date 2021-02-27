import gspread
from gspread_dataframe import set_with_dataframe

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

def export_to_gsheet(season, ndoc=0):
    """
    Export a `pandas.DataFrame` to a google sheet. Used to synch the season leaderboard.

    :param season: `pandas.DataFrame` to synch
    :param ndoc: Identifier of the sheet to synch
    :return: None
    """

    gc = gspread.service_account()
    sh = gc.open('Season Leaderboard')
    worksheet = sh.get_worksheet(ndoc)
    worksheet.format ('1', {'textFormat': {'bold': True}})
    set_with_dataframe(worksheet, season)